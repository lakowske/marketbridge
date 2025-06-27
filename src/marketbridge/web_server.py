"""
MarketBridge Web Server
Serves the web frontend and handles HTTP requests with comprehensive logging.
"""

import asyncio
import logging
import logging.handlers
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles  # type: ignore[import-untyped]
from aiohttp import WSMsgType, web
from aiohttp.web_middlewares import middleware
from aiohttp.web_request import Request
from aiohttp.web_response import Response


class WebServer:
    """Web server for MarketBridge frontend with comprehensive logging."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        web_root: Optional[str] = None,
        log_dir: Optional[str] = None,
        enable_cors: bool = True,
    ):
        self.host = host
        self.port = port
        self.enable_cors = enable_cors

        # Set web root - default to web/public in project directory
        if web_root is None:
            project_root = Path(__file__).parent.parent.parent
            self.web_root = project_root / "web" / "public"
        else:
            self.web_root = Path(web_root)

        # Set log directory - default to logs/ in project directory
        if log_dir is None:
            project_root = Path(__file__).parent.parent.parent
            self.log_dir = project_root / "logs"
        else:
            self.log_dir = Path(log_dir)

        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None

        # Setup logging
        self.setup_logging()

        # Stats tracking
        self.stats = {
            "requests_total": 0,
            "requests_by_method": {},
            "requests_by_status": {},
            "bytes_served": 0,
            "start_time": time.time(),
            "active_connections": 0,
        }

    def setup_logging(self):
        """Setup comprehensive logging to both file and console."""
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create logger
        self.logger = logging.getLogger("marketbridge.webserver")
        self.logger.setLevel(logging.DEBUG)

        # Clear any existing handlers
        self.logger.handlers.clear()

        # Console handler (stdout/stderr)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler - main log
        log_file = self.log_dir / "webserver.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Access log handler
        access_log_file = self.log_dir / "access.log"
        self.access_logger = logging.getLogger("marketbridge.webserver.access")
        self.access_logger.setLevel(logging.INFO)
        self.access_logger.handlers.clear()

        access_handler = logging.handlers.RotatingFileHandler(
            access_log_file,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10,
            encoding="utf-8",
        )
        access_formatter = logging.Formatter("%(asctime)s - %(message)s")
        access_handler.setFormatter(access_formatter)
        self.access_logger.addHandler(access_handler)

        # Error log handler
        error_log_file = self.log_dir / "error.log"
        self.error_logger = logging.getLogger("marketbridge.webserver.error")
        self.error_logger.setLevel(logging.WARNING)
        self.error_logger.handlers.clear()

        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        error_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        )
        error_handler.setFormatter(error_formatter)
        self.error_logger.addHandler(error_handler)

        self.logger.info(f"Logging initialized - Log directory: {self.log_dir}")
        self.logger.info(f"Web root directory: {self.web_root}")
        self.logger.info(f"Log level set to: {logging.getLevelName(self.logger.level)}")

    @middleware
    async def logging_middleware(self, request: Request, handler):
        """Middleware for request/response logging and stats."""
        start_time = time.time()
        self.stats["active_connections"] += 1  # type: ignore[operator]

        # Log incoming request
        self.logger.debug(
            f"Incoming request: {request.method} {request.path} from {request.remote}"
        )

        try:
            response = await handler(request)

            # Calculate response time
            response_time = (time.time() - start_time) * 1000  # milliseconds

            # Update stats
            self.stats["requests_total"] += 1  # type: ignore[operator]
            self.stats["requests_by_method"][request.method] = (  # type: ignore[index]
                self.stats["requests_by_method"].get(request.method, 0) + 1  # type: ignore[attr-defined]
            )
            self.stats["requests_by_status"][response.status] = (  # type: ignore[index]
                self.stats["requests_by_status"].get(response.status, 0) + 1  # type: ignore[attr-defined]
            )

            if hasattr(response, "content_length") and response.content_length:
                self.stats["bytes_served"] += response.content_length

            # Access log entry
            access_msg = (
                f"{request.remote} - {request.method} {request.path} "
                f"{response.status} {response.content_length or '-'} "
                f"{response_time:.2f}ms \"{request.headers.get('User-Agent', '-')}\""
            )
            self.access_logger.info(access_msg)

            # Log slow requests
            if response_time > 1000:  # > 1 second
                self.logger.warning(
                    f"Slow request: {request.method} {request.path} took {response_time:.2f}ms"
                )

            return response

        except Exception as e:
            # Log error
            error_msg = (
                f"Error handling request {request.method} {request.path}: {str(e)}"
            )
            self.error_logger.error(error_msg, exc_info=True)
            self.logger.error(error_msg)

            # Return 500 error
            return web.Response(text="Internal Server Error", status=500)

        finally:
            self.stats["active_connections"] -= 1  # type: ignore[operator]

    @middleware
    async def cors_middleware(self, request: Request, handler):
        """CORS middleware for cross-origin requests."""
        if not self.enable_cors:
            return await handler(request)

        # Handle preflight requests
        if request.method == "OPTIONS":
            response = web.Response()
        else:
            response = await handler(request)

        # Add CORS headers
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers[
            "Access-Control-Allow-Methods"
        ] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours

        return response

    async def handle_static_file(self, request: Request) -> Response:
        """Handle static file requests."""
        # Get file path from request
        file_path = request.path.lstrip("/")

        # Default to index.html for root requests
        if not file_path or file_path == "/":
            file_path = "index.html"

        # Resolve full file path
        full_path = self.web_root / file_path

        # Security check - ensure path is within web root
        try:
            full_path.resolve().relative_to(self.web_root.resolve())
        except ValueError:
            self.logger.warning(f"Attempted path traversal: {request.path}")
            return web.Response(text="Forbidden", status=403)

        # Check if file exists
        if not full_path.exists():
            self.logger.debug(f"File not found: {full_path}")
            return web.Response(text="Not Found", status=404)

        # Check if it's a file (not directory)
        if not full_path.is_file():
            self.logger.debug(f"Path is not a file: {full_path}")
            return web.Response(text="Not Found", status=404)

        try:
            # Read file content
            async with aiofiles.open(full_path, "rb") as f:
                content = await f.read()

            # Determine content type
            content_type = self.get_content_type(full_path.suffix)

            # Create response
            response = web.Response(body=content, content_type=content_type)

            # Add caching headers for static assets
            if full_path.suffix in [".css", ".js", ".png", ".jpg", ".gif", ".ico"]:
                response.headers["Cache-Control"] = "public, max-age=3600"  # 1 hour

            return response

        except Exception as e:
            self.error_logger.error(
                f"Error serving file {full_path}: {str(e)}", exc_info=True
            )
            return web.Response(text="Internal Server Error", status=500)

    def get_content_type(self, suffix: str) -> str:
        """Get content type based on file extension."""
        content_types = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".ico": "image/x-icon",
            ".svg": "image/svg+xml",
            ".woff": "font/woff",
            ".woff2": "font/woff2",
            ".ttf": "font/ttf",
            ".eot": "application/vnd.ms-fontobject",
        }
        return content_types.get(suffix.lower(), "application/octet-stream")

    async def handle_health(self, request: Request) -> Response:
        """Health check endpoint."""
        uptime = time.time() - self.stats["start_time"]  # type: ignore[operator]
        health_data = {
            "status": "healthy",
            "uptime_seconds": uptime,
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats.copy(),
        }

        return web.json_response(health_data)

    async def handle_stats(self, request: Request) -> Response:
        """Statistics endpoint."""
        uptime = time.time() - self.stats["start_time"]  # type: ignore[operator]
        stats_data = {
            "uptime_seconds": uptime,
            "uptime_human": self.format_uptime(uptime),
            "timestamp": datetime.now().isoformat(),
            **self.stats,
        }

        return web.json_response(stats_data)

    def format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format."""
        days, remainder = divmod(int(seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, secs = divmod(remainder, 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m {secs}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    async def setup_app(self):
        """Setup the aiohttp application."""
        # Create middlewares list
        middlewares = [self.logging_middleware]
        if self.enable_cors:
            middlewares.append(self.cors_middleware)

        # Create application
        self.app = web.Application(middlewares=middlewares)

        # Add routes
        self.app.router.add_get("/health", self.handle_health)
        self.app.router.add_get("/stats", self.handle_stats)

        # Catch-all route for static files (must be last)
        self.app.router.add_route("*", "/{path:.*}", self.handle_static_file)

        self.logger.info("Web application configured")

    async def start(self):
        """Start the web server."""
        if not self.web_root.exists():
            raise FileNotFoundError(f"Web root directory not found: {self.web_root}")

        self.logger.info(f"Starting web server on {self.host}:{self.port}")
        self.logger.info(f"Serving content from: {self.web_root}")

        # Setup application
        await self.setup_app()

        # Create runner
        if self.app is not None:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            # Create site
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()

        self.logger.info(f"Web server started successfully")
        self.logger.info(f"Frontend available at: http://{self.host}:{self.port}")
        self.logger.info(f"Health check: http://{self.host}:{self.port}/health")
        self.logger.info(f"Statistics: http://{self.host}:{self.port}/stats")

    async def stop(self):
        """Stop the web server."""
        self.logger.info("Stopping web server...")

        if self.site:
            try:
                await self.site.stop()
                self.site = None
            except Exception as e:
                self.logger.debug(f"Site stop error (may be normal): {e}")

        if self.runner:
            try:
                await self.runner.cleanup()
                self.runner = None
            except Exception as e:
                self.logger.debug(f"Runner cleanup error (may be normal): {e}")

        self.logger.info("Web server stopped")

    async def run_forever(self):
        """Run the web server indefinitely."""
        try:
            await self.start()

            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.error_logger.error(f"Web server error: {str(e)}", exc_info=True)
            self.logger.error(f"Web server error: {str(e)}")
        finally:
            await self.stop()


async def main():
    """Main function to run the web server."""
    import argparse

    parser = argparse.ArgumentParser(description="MarketBridge Web Server")
    parser.add_argument(
        "--host", default="localhost", help="Host to bind to (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port to bind to (default: 8080)"
    )
    parser.add_argument("--web-root", help="Web root directory (default: web/public)")
    parser.add_argument("--log-dir", help="Log directory (default: logs)")
    parser.add_argument("--no-cors", action="store_true", help="Disable CORS headers")

    args = parser.parse_args()

    # Create and run server
    server = WebServer(
        host=args.host,
        port=args.port,
        web_root=args.web_root,
        log_dir=args.log_dir,
        enable_cors=not args.no_cors,
    )

    await server.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
