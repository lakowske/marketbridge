"""
MarketBridge Browser Session Server

FastAPI server for managing persistent browser sessions with Playwright integration.
Inspired by browser-bunny's architecture but designed specifically for MarketBridge.
"""

import asyncio
import json
import logging
import logging.handlers
import os
import signal
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import uvicorn
    from fastapi import BackgroundTasks, FastAPI, HTTPException
    from fastapi.responses import JSONResponse
except ImportError:
    FastAPI = HTTPException = JSONResponse = None
    uvicorn = None

from marketbridge_playwright.browser_manager import BrowserManager
from marketbridge_playwright.session_manager import SessionManager

from .session_registry import SessionRegistry

logger = logging.getLogger(__name__)


class BrowserSessionServer:
    """
    FastAPI server for browser session management.

    Provides RESTful API endpoints for creating, managing, and automating
    browser sessions with persistent state tracking.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8766,
        registry_file: Optional[str] = None,
        screenshots_dir: Optional[str] = None,
        log_dir: Optional[str] = None,
    ):
        """
        Initialize the browser session server.

        Args:
            host: Server host address
            port: Server port
            registry_file: Path to session registry file
            screenshots_dir: Directory for screenshots
            log_dir: Directory for logs
        """
        self.host = host
        self.port = port

        # Setup directories
        self.setup_directories(screenshots_dir, log_dir)

        # Initialize components
        self.session_manager = SessionManager()
        self.browser_manager = BrowserManager(self.session_manager)
        self.session_registry = SessionRegistry(registry_file)

        # Active browser sessions
        self.active_browsers: Dict[str, Any] = {}

        # Server state
        self.running = False
        self.startup_time = time.time()

        # Setup FastAPI app
        self.app = self.create_app()

        logger.info(
            f"Browser session server initialized - host: {self.host}, port: {self.port}, "
            f"screenshots_dir: {self.screenshots_dir}, log_dir: {self.log_dir}"
        )

    def setup_directories(
        self, screenshots_dir: Optional[str], log_dir: Optional[str]
    ) -> None:
        """Setup required directories."""
        if screenshots_dir is None:
            project_root = Path(__file__).parent.parent.parent
            self.screenshots_dir = project_root / "screenshots"
        else:
            self.screenshots_dir = Path(screenshots_dir)

        if log_dir is None:
            project_root = Path(__file__).parent.parent.parent
            self.log_dir = project_root / "logs"
        else:
            self.log_dir = Path(log_dir)

        # Create directories
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def setup_logging(self) -> None:
        """Setup comprehensive logging."""
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        root_logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler
        log_file = self.log_dir / "browser_session_server.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        logger.info(f"Logging configured - log_file: {log_file}")

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """FastAPI lifespan context manager."""
        # Startup
        logger.info("Starting browser session server...")
        await self.startup()

        try:
            yield
        finally:
            # Shutdown
            logger.info("Shutting down browser session server...")
            await self.shutdown()

    def create_app(self) -> FastAPI:
        """Create and configure FastAPI application."""
        if FastAPI is None:
            raise ImportError("FastAPI not installed. Run: pip install fastapi uvicorn")

        app = FastAPI(
            title="MarketBridge Browser Session Server",
            description="RESTful API for managing persistent browser sessions",
            version="1.0.0",
            lifespan=self.lifespan,
        )

        # Add routes
        self.add_routes(app)

        return app

    def add_routes(self, app: FastAPI) -> None:
        """Add API routes to the FastAPI app."""

        @app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "uptime": time.time() - self.startup_time,
                "active_sessions": len(self.active_browsers),
                "total_sessions": len(self.session_registry),
            }

        @app.get("/stats")
        async def get_stats():
            """Get server statistics."""
            stats = self.session_registry.get_registry_stats()
            stats.update(
                {
                    "server_uptime": time.time() - self.startup_time,
                    "active_browsers": len(self.active_browsers),
                    "screenshots_dir": str(self.screenshots_dir),
                }
            )
            return stats

        @app.post("/sessions")
        async def create_session(request: Dict[str, Any]):
            """Create a new browser session."""
            session_name = request.get("session_name")
            config = request.get("config", {})

            if not session_name:
                raise HTTPException(status_code=400, detail="session_name is required")

            try:
                # Check if session name already exists
                if self.session_registry.session_name_exists(session_name):
                    raise HTTPException(
                        status_code=409,
                        detail=f"Session name '{session_name}' already exists",
                    )

                # Create session in registry
                session_id = self.session_registry.create_session(
                    session_name=session_name, metadata=config
                )

                # Start browser if not already running
                if not self.browser_manager._running:
                    await self.browser_manager.start(
                        headless=config.get("headless", False),
                        browser_type=config.get("browser_type", "chromium"),
                    )

                # Create browser context
                context = await self.browser_manager.create_session_context(
                    session_name
                )

                # Store active browser session
                self.active_browsers[session_id] = {
                    "session_id": session_id,
                    "session_name": session_name,
                    "context": context,
                    "pages": {},
                    "created_at": time.time(),
                }

                # Update registry
                self.session_registry.update_session(session_id, active=True)

                session_data = self.session_registry.get_session(session_id)

                logger.info(
                    f"Created browser session - session_id: {session_id}, session_name: {session_name}"
                )

                return {
                    "session_id": session_id,
                    "session_data": session_data,
                    "status": "created",
                }

            except Exception as e:
                logger.error(f"Failed to create session '{session_name}': {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/sessions")
        async def list_sessions(active_only: bool = False):
            """List all browser sessions."""
            sessions = self.session_registry.list_sessions(active_only=active_only)
            return {"sessions": sessions}

        @app.get("/sessions/{session_id}")
        async def get_session(session_id: str):
            """Get session information."""
            session_data = self.session_registry.get_session(session_id)
            if not session_data:
                raise HTTPException(status_code=404, detail="Session not found")

            # Add runtime information
            if session_id in self.active_browsers:
                browser_session = self.active_browsers[session_id]
                session_data["runtime"] = {
                    "browser_active": True,
                    "page_count": len(browser_session["pages"]),
                    "uptime": time.time() - browser_session["created_at"],
                }
            else:
                session_data["runtime"] = {"browser_active": False}

            return session_data

        @app.delete("/sessions/{session_id}")
        async def delete_session(session_id: str):
            """Delete a browser session."""
            if session_id not in self.session_registry:
                raise HTTPException(status_code=404, detail="Session not found")

            try:
                # Close browser session if active
                if session_id in self.active_browsers:
                    browser_session = self.active_browsers[session_id]

                    # Close all pages
                    for page in browser_session["pages"].values():
                        try:
                            await page.close()
                        except Exception as e:
                            logger.warning(f"Error closing page: {e}")

                    # Close context
                    try:
                        await browser_session["context"].close()
                    except Exception as e:
                        logger.warning(f"Error closing context: {e}")

                    del self.active_browsers[session_id]

                # Remove from registry
                self.session_registry.delete_session(session_id)

                logger.info(f"Deleted browser session: {session_id}")

                return {"status": "deleted", "session_id": session_id}

            except Exception as e:
                logger.error(f"Failed to delete session {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/sessions/{session_id}/navigate")
        async def navigate_session(session_id: str, request: Dict[str, Any]):
            """Navigate a browser session to a URL."""
            if session_id not in self.active_browsers:
                raise HTTPException(status_code=404, detail="Active session not found")

            url = request.get("url")
            if not url:
                raise HTTPException(status_code=400, detail="url is required")

            wait_until = request.get("wait_until", "domcontentloaded")
            timeout = request.get("timeout", 30000)
            page_id = request.get("page_id")

            try:
                browser_session = self.active_browsers[session_id]

                # Get or create page
                if page_id and page_id in browser_session["pages"]:
                    page = browser_session["pages"][page_id]
                else:
                    page = await browser_session["context"].new_page()
                    page_id = str(uuid.uuid4())
                    browser_session["pages"][page_id] = page

                # Navigate
                start_time = time.time()
                response = await page.goto(url, wait_until=wait_until, timeout=timeout)
                duration = (time.time() - start_time) * 1000

                # Update session registry
                page_count = len(browser_session["pages"])
                self.session_registry.update_session(
                    session_id, url=url, page_count=page_count
                )

                logger.info(
                    f"Navigated session {session_id} to {url} - duration: {duration:.1f}ms"
                )

                return {
                    "session_id": session_id,
                    "page_id": page_id,
                    "url": url,
                    "status": "success",
                    "duration": duration,
                    "response_status": response.status if response else None,
                }

            except Exception as e:
                logger.error(f"Navigation failed for session {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/sessions/{session_id}/screenshot")
        async def take_screenshot(session_id: str, request: Dict[str, Any]):
            """Take a screenshot of a browser session."""
            if session_id not in self.active_browsers:
                raise HTTPException(status_code=404, detail="Active session not found")

            filename = request.get("filename")
            full_page = request.get("full_page", False)
            quality = request.get("quality", 90)
            page_id = request.get("page_id")

            try:
                browser_session = self.active_browsers[session_id]

                # Get page
                if page_id and page_id in browser_session["pages"]:
                    page = browser_session["pages"][page_id]
                else:
                    # Use first available page or create new one
                    if browser_session["pages"]:
                        page = next(iter(browser_session["pages"].values()))
                    else:
                        page = await browser_session["context"].new_page()
                        page_id = str(uuid.uuid4())
                        browser_session["pages"][page_id] = page

                # Generate filename if not provided
                if not filename:
                    timestamp = int(time.time())
                    filename = f"session_{session_id}_{timestamp}.png"

                screenshot_path = self.screenshots_dir / filename

                # Take screenshot
                await page.screenshot(
                    path=str(screenshot_path),
                    full_page=full_page,
                    quality=quality,
                )

                logger.info(f"Screenshot taken for session {session_id}: {filename}")

                return {
                    "session_id": session_id,
                    "filename": filename,
                    "path": str(screenshot_path),
                    "full_page": full_page,
                    "quality": quality,
                }

            except Exception as e:
                logger.error(f"Screenshot failed for session {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/sessions/{session_id}/execute")
        async def execute_javascript(session_id: str, request: Dict[str, Any]):
            """Execute JavaScript in a browser session."""
            if session_id not in self.active_browsers:
                raise HTTPException(status_code=404, detail="Active session not found")

            script = request.get("script")
            if not script:
                raise HTTPException(status_code=400, detail="script is required")

            await_promise = request.get("await_promise", True)
            page_id = request.get("page_id")

            try:
                browser_session = self.active_browsers[session_id]

                # Get page
                if page_id and page_id in browser_session["pages"]:
                    page = browser_session["pages"][page_id]
                else:
                    if not browser_session["pages"]:
                        raise HTTPException(
                            status_code=400, detail="No pages available"
                        )
                    page = next(iter(browser_session["pages"].values()))

                # Execute JavaScript
                if await_promise:
                    result = await page.evaluate(script)
                else:
                    result = await page.evaluate(f"() => {{ {script} }}")

                logger.debug(f"Executed JavaScript in session {session_id}")

                return {
                    "session_id": session_id,
                    "result": result,
                    "status": "success",
                }

            except Exception as e:
                logger.error(
                    f"JavaScript execution failed for session {session_id}: {e}"
                )
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/sessions/{session_id}/interact")
        async def interact_with_page(session_id: str, request: Dict[str, Any]):
            """Interact with page elements (click, type, etc.)."""
            if session_id not in self.active_browsers:
                raise HTTPException(status_code=404, detail="Active session not found")

            action = request.get("action")
            if not action:
                raise HTTPException(status_code=400, detail="action is required")

            selector = request.get("selector")
            timeout = request.get("timeout", 10000)
            page_id = request.get("page_id")

            try:
                browser_session = self.active_browsers[session_id]

                # Get page
                if page_id and page_id in browser_session["pages"]:
                    page = browser_session["pages"][page_id]
                else:
                    if not browser_session["pages"]:
                        raise HTTPException(
                            status_code=400, detail="No pages available"
                        )
                    page = next(iter(browser_session["pages"].values()))

                result = {
                    "session_id": session_id,
                    "action": action,
                    "status": "success",
                }

                if action == "click":
                    if not selector:
                        raise HTTPException(
                            status_code=400, detail="selector is required for click"
                        )
                    await page.click(selector, timeout=timeout)

                elif action == "type":
                    if not selector:
                        raise HTTPException(
                            status_code=400, detail="selector is required for type"
                        )
                    text = request.get("text", "")
                    clear_first = request.get("clear_first", True)

                    if clear_first:
                        await page.fill(selector, text)
                    else:
                        await page.type(selector, text)

                    result["text"] = text

                else:
                    raise HTTPException(
                        status_code=400, detail=f"Unsupported action: {action}"
                    )

                logger.debug(
                    f"Interaction '{action}' completed for session {session_id}"
                )

                return result

            except Exception as e:
                logger.error(f"Interaction failed for session {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/sessions/{session_id}/wait")
        async def wait_for_condition(session_id: str, request: Dict[str, Any]):
            """Wait for page conditions."""
            if session_id not in self.active_browsers:
                raise HTTPException(status_code=404, detail="Active session not found")

            action = request.get("action")
            if not action:
                raise HTTPException(status_code=400, detail="action is required")

            timeout = request.get("timeout", 10000)
            page_id = request.get("page_id")

            try:
                browser_session = self.active_browsers[session_id]

                # Get page
                if page_id and page_id in browser_session["pages"]:
                    page = browser_session["pages"][page_id]
                else:
                    if not browser_session["pages"]:
                        raise HTTPException(
                            status_code=400, detail="No pages available"
                        )
                    page = next(iter(browser_session["pages"].values()))

                if action == "wait_for_element":
                    selector = request.get("selector")
                    if not selector:
                        raise HTTPException(
                            status_code=400, detail="selector is required"
                        )
                    state = request.get("state", "visible")

                    await page.wait_for_selector(selector, state=state, timeout=timeout)

                else:
                    raise HTTPException(
                        status_code=400, detail=f"Unsupported wait action: {action}"
                    )

                logger.debug(
                    f"Wait condition '{action}' completed for session {session_id}"
                )

                return {
                    "session_id": session_id,
                    "action": action,
                    "status": "success",
                }

            except Exception as e:
                logger.error(f"Wait condition failed for session {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/cleanup")
        async def cleanup_sessions(request: Dict[str, Any]):
            """Clean up old sessions."""
            max_age_hours = request.get("max_age_hours", 24)

            try:
                deleted_sessions = self.session_registry.cleanup_inactive_sessions(
                    max_age_hours
                )

                # Also clean up active browsers for deleted sessions
                for session_id in deleted_sessions:
                    if session_id in self.active_browsers:
                        browser_session = self.active_browsers[session_id]
                        try:
                            await browser_session["context"].close()
                        except Exception as e:
                            logger.warning(f"Error closing context during cleanup: {e}")
                        del self.active_browsers[session_id]

                logger.info(f"Cleaned up {len(deleted_sessions)} sessions")

                return {
                    "deleted_sessions": deleted_sessions,
                    "cleanup_count": len(deleted_sessions),
                }

            except Exception as e:
                logger.error(f"Cleanup failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def startup(self) -> None:
        """Server startup tasks."""
        self.running = True

        # Setup logging
        self.setup_logging()

        # Start background cleanup task
        asyncio.create_task(self.background_cleanup_task())

        logger.info(f"Browser session server started on {self.host}:{self.port}")

    async def shutdown(self) -> None:
        """Server shutdown tasks."""
        self.running = False

        # Close all active browser sessions
        for session_id, browser_session in list(self.active_browsers.items()):
            try:
                # Close all pages
                for page in browser_session["pages"].values():
                    await page.close()

                # Close context
                await browser_session["context"].close()

                logger.debug(f"Closed browser session: {session_id}")

            except Exception as e:
                logger.warning(f"Error closing session {session_id}: {e}")

        # Stop browser manager
        await self.browser_manager.stop()

        logger.info("Browser session server shutdown complete")

    async def background_cleanup_task(self) -> None:
        """Background task for periodic cleanup."""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Run every hour

                if not self.running:
                    break

                # Clean up old sessions
                deleted_sessions = self.session_registry.cleanup_inactive_sessions(24)

                if deleted_sessions:
                    logger.info(
                        f"Background cleanup removed {len(deleted_sessions)} sessions"
                    )

            except Exception as e:
                logger.error(f"Background cleanup error: {e}")

    def run(self) -> None:
        """Run the server."""
        if uvicorn is None:
            raise ImportError("uvicorn not installed. Run: pip install uvicorn")

        # Setup signal handlers
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            # uvicorn will handle the shutdown gracefully

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Run server
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=True,
        )


def main():
    """Main entry point for the browser session server."""
    import argparse

    parser = argparse.ArgumentParser(description="MarketBridge Browser Session Server")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    parser.add_argument("--registry-file", help="Session registry file path")
    parser.add_argument("--screenshots-dir", help="Screenshots directory")
    parser.add_argument("--log-dir", help="Logs directory")

    args = parser.parse_args()

    server = BrowserSessionServer(
        host=args.host,
        port=args.port,
        registry_file=args.registry_file,
        screenshots_dir=args.screenshots_dir,
        log_dir=args.log_dir,
    )

    server.run()


if __name__ == "__main__":
    main()
