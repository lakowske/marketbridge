"""
Playwright Browser Manager

Manages browser lifecycle with integration to session manager for persistent
browser contexts across script runs.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Page,
        Playwright,
        async_playwright,
    )
except ImportError:
    # Graceful fallback if playwright is not installed
    Playwright = Browser = BrowserContext = Page = None

from .session_manager import SessionManager

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages Playwright browser instances with persistent session support."""

    def __init__(self, session_manager: Optional[SessionManager] = None):
        """
        Initialize browser manager.

        Args:
            session_manager: SessionManager instance. If None, creates a new one.
        """
        self.session_manager = session_manager or SessionManager()
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.contexts: Dict[str, BrowserContext] = {}
        self._running = False

        logger.info("Browser manager initialized")

    async def start(
        self, browser_type: str = "chromium", headless: bool = False, **kwargs
    ) -> None:
        """
        Start the Playwright browser.

        Args:
            browser_type: Browser type ('chromium', 'firefox', 'webkit')
            headless: Whether to run in headless mode
            **kwargs: Additional browser launch options
        """
        if self._running:
            logger.warning("Browser already running")
            return

        if Playwright is None:
            raise ImportError(
                "Playwright not installed. Run: pip install playwright && playwright install"
            )

        self.playwright = await async_playwright().start()

        # Get browser launcher
        if browser_type == "chromium":
            browser_launcher = self.playwright.chromium
        elif browser_type == "firefox":
            browser_launcher = self.playwright.firefox
        elif browser_type == "webkit":
            browser_launcher = self.playwright.webkit
        else:
            raise ValueError(f"Unsupported browser type: {browser_type}")

        # Default launch options
        launch_options = {
            "headless": headless,
            "args": ["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        }
        launch_options.update(kwargs)

        self.browser = await browser_launcher.launch(**launch_options)
        self._running = True

        logger.info(f"Started {browser_type} browser (headless={headless})")

    async def stop(self) -> None:
        """Stop the browser and cleanup resources."""
        if not self._running:
            return

        # Close all contexts
        for context_name, context in self.contexts.items():
            try:
                await context.close()
                logger.debug(f"Closed context: {context_name}")
            except Exception as e:
                logger.warning(f"Error closing context {context_name}: {e}")

        self.contexts.clear()

        # Close browser
        if self.browser:
            await self.browser.close()
            self.browser = None

        # Stop playwright
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

        self._running = False
        logger.info("Browser stopped")

    async def create_session_context(
        self, session_name: str, **context_options
    ) -> BrowserContext:
        """
        Create or restore a browser context with persistent session.

        Args:
            session_name: Name of the session to create/restore
            **context_options: Additional context options

        Returns:
            BrowserContext instance
        """
        if not self._running:
            raise RuntimeError("Browser not started. Call start() first.")

        # Check if session already exists
        if not self.session_manager.session_exists(session_name):
            self.session_manager.create_session(
                session_name, description="Playwright browser session"
            )

        # Load session metadata
        session_metadata = self.session_manager.load_session(session_name)
        context_dir = session_metadata["browser_context_dir"]

        # Ensure context directory exists
        Path(context_dir).mkdir(parents=True, exist_ok=True)

        # Context options with session persistence
        default_options = {
            "storage_state": str(Path(context_dir) / "storage_state.json"),
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        default_options.update(context_options)

        # Try to load existing storage state
        storage_state_file = Path(str(default_options["storage_state"]))
        if not storage_state_file.exists():
            # Remove storage_state option if file doesn't exist
            default_options.pop("storage_state", None)

        # Create browser context
        if self.browser is None:
            raise RuntimeError("Browser is None")
        context = await self.browser.new_context(**default_options)
        self.contexts[session_name] = context

        # Save storage state on context close
        async def save_on_close():
            try:
                await context.storage_state(path=str(storage_state_file))
                logger.debug(f"Saved storage state for session: {session_name}")
            except Exception as e:
                logger.warning(f"Failed to save storage state for {session_name}: {e}")

        # Register cleanup handler
        context.on("close", lambda: asyncio.create_task(save_on_close()))

        logger.info(f"Created context for session: {session_name}")
        return context

    async def get_session_context(self, session_name: str) -> Optional[BrowserContext]:
        """
        Get existing browser context for a session.

        Args:
            session_name: Session name

        Returns:
            BrowserContext if exists, None otherwise
        """
        return self.contexts.get(session_name)

    async def close_session_context(self, session_name: str) -> None:
        """
        Close and save a session context.

        Args:
            session_name: Session name to close
        """
        context = self.contexts.get(session_name)
        if context:
            await context.close()
            del self.contexts[session_name]
            logger.info(f"Closed session context: {session_name}")

    async def new_page(self, session_name: str, **page_options) -> Page:
        """
        Create a new page in the specified session context.

        Args:
            session_name: Session name
            **page_options: Additional page options

        Returns:
            Page instance
        """
        context = self.contexts.get(session_name)
        if not context:
            context = await self.create_session_context(session_name)

        page = await context.new_page(**page_options)
        logger.debug(f"Created new page in session: {session_name}")
        return page

    async def navigate_to_marketbridge(
        self, session_name: str, base_url: str = "http://localhost:8080"
    ) -> Page:
        """
        Navigate to MarketBridge web interface.

        Args:
            session_name: Session name
            base_url: Base URL of MarketBridge web server

        Returns:
            Page instance at MarketBridge interface
        """
        page = await self.new_page(session_name)

        try:
            await page.goto(base_url, wait_until="networkidle")
            await page.wait_for_load_state("domcontentloaded")

            # Wait for the app to be ready
            await page.wait_for_selector("#app", timeout=10000)

            logger.info(f"Navigated to MarketBridge at {base_url}")
            return page

        except Exception as e:
            logger.error(f"Failed to navigate to MarketBridge: {e}")
            await page.close()
            raise

    def list_active_sessions(self) -> List[str]:
        """
        List currently active session names.

        Returns:
            List of active session names
        """
        return list(self.contexts.keys())

    async def save_all_sessions(self) -> None:
        """Save storage state for all active sessions."""
        for session_name, context in self.contexts.items():
            try:
                session_metadata = self.session_manager.load_session(session_name)
                storage_state_file = (
                    Path(session_metadata["browser_context_dir"]) / "storage_state.json"
                )
                await context.storage_state(path=str(storage_state_file))
                logger.debug(f"Saved storage state for session: {session_name}")
            except Exception as e:
                logger.warning(f"Failed to save storage state for {session_name}: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
