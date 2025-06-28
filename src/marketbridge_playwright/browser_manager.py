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

    # Remote Control Capabilities for API Integration
    async def get_session_pages(self, session_name: str) -> List[Dict[str, Any]]:
        """
        Get all pages in a session for remote control.

        Args:
            session_name: Session name

        Returns:
            List of page information dictionaries
        """
        context = self.contexts.get(session_name)
        if not context:
            return []

        pages_info = []
        for page in context.pages:
            try:
                pages_info.append(
                    {
                        "url": page.url,
                        "title": await page.title(),
                        "viewport": page.viewport_size,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to get page info: {e}")
                pages_info.append(
                    {
                        "url": "unknown",
                        "title": "unknown",
                        "viewport": None,
                        "error": str(e),
                    }
                )

        return pages_info

    async def take_session_screenshot(
        self, session_name: str, path: str, full_page: bool = False, quality: int = 90
    ) -> bool:
        """
        Take a screenshot of the first page in a session.

        Args:
            session_name: Session name
            path: Screenshot file path
            full_page: Whether to capture full page
            quality: Image quality (1-100)

        Returns:
            True if screenshot was taken successfully, False otherwise
        """
        context = self.contexts.get(session_name)
        if not context or not context.pages:
            return False

        try:
            page = context.pages[0]
            await page.screenshot(path=path, full_page=full_page, quality=quality)
            logger.debug(f"Screenshot taken for session {session_name}: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to take screenshot for session {session_name}: {e}")
            return False

    async def execute_javascript_in_session(
        self, session_name: str, script: str, await_promise: bool = True
    ) -> Any:
        """
        Execute JavaScript in the first page of a session.

        Args:
            session_name: Session name
            script: JavaScript code to execute
            await_promise: Whether to await promise results

        Returns:
            JavaScript execution result

        Raises:
            RuntimeError: If session or page not found
        """
        context = self.contexts.get(session_name)
        if not context or not context.pages:
            raise RuntimeError(f"No active pages in session: {session_name}")

        page = context.pages[0]

        if await_promise:
            result = await page.evaluate(script)
        else:
            result = await page.evaluate(f"() => {{ {script} }}")

        logger.debug(f"Executed JavaScript in session {session_name}")
        return result

    async def navigate_session_page(
        self,
        session_name: str,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: int = 30000,
    ) -> Dict[str, Any]:
        """
        Navigate the first page of a session to a URL.

        Args:
            session_name: Session name
            url: URL to navigate to
            wait_until: Wait condition
            timeout: Navigation timeout

        Returns:
            Navigation result dictionary

        Raises:
            RuntimeError: If session not found
        """
        import time

        context = self.contexts.get(session_name)
        if not context:
            raise RuntimeError(f"Session not found: {session_name}")

        # Get or create page
        if context.pages:
            page = context.pages[0]
        else:
            page = await context.new_page()

        start_time = time.time()
        response = await page.goto(url, wait_until=wait_until, timeout=timeout)
        duration = (time.time() - start_time) * 1000

        logger.info(
            f"Navigated session {session_name} to {url} - duration: {duration:.1f}ms"
        )

        return {
            "url": url,
            "status": response.status if response else None,
            "duration": duration,
            "final_url": page.url,
            "title": await page.title(),
        }

    async def interact_with_session_page(
        self, session_name: str, action: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Interact with elements in the first page of a session.

        Args:
            session_name: Session name
            action: Action to perform ('click', 'type', 'select', etc.)
            **kwargs: Action-specific parameters

        Returns:
            Interaction result dictionary

        Raises:
            RuntimeError: If session or page not found
            ValueError: If action is not supported
        """
        context = self.contexts.get(session_name)
        if not context or not context.pages:
            raise RuntimeError(f"No active pages in session: {session_name}")

        page = context.pages[0]
        selector = kwargs.get("selector")
        timeout = kwargs.get("timeout", 10000)

        if action == "click":
            if not selector:
                raise ValueError("selector is required for click action")
            await page.click(selector, timeout=timeout)
            result = {"action": "click", "selector": selector, "status": "success"}

        elif action == "type":
            if not selector:
                raise ValueError("selector is required for type action")
            text = kwargs.get("text", "")
            clear_first = kwargs.get("clear_first", True)

            if clear_first:
                await page.fill(selector, text)
            else:
                await page.type(selector, text)

            result = {
                "action": "type",
                "selector": selector,
                "text": text,
                "status": "success",
            }

        elif action == "select":
            if not selector:
                raise ValueError("selector is required for select action")
            value = kwargs.get("value", "")
            await page.select_option(selector, value)
            result = {
                "action": "select",
                "selector": selector,
                "value": value,
                "status": "success",
            }

        elif action == "wait_for_element":
            if not selector:
                raise ValueError("selector is required for wait_for_element action")
            state = kwargs.get("state", "visible")
            await page.wait_for_selector(selector, state=state, timeout=timeout)
            result = {
                "action": "wait_for_element",
                "selector": selector,
                "state": state,
                "status": "success",
            }

        else:
            raise ValueError(f"Unsupported action: {action}")

        logger.debug(f"Interaction '{action}' completed for session {session_name}")
        return result

    async def get_session_element_text(
        self, session_name: str, selector: str
    ) -> Optional[str]:
        """
        Get text content of an element in the first page of a session.

        Args:
            session_name: Session name
            selector: CSS selector for the element

        Returns:
            Element text content or None

        Raises:
            RuntimeError: If session or page not found
        """
        context = self.contexts.get(session_name)
        if not context or not context.pages:
            raise RuntimeError(f"No active pages in session: {session_name}")

        page = context.pages[0]

        try:
            element = await page.query_selector(selector)
            if element:
                return await element.text_content()
            return None
        except Exception as e:
            logger.warning(f"Failed to get element text for {selector}: {e}")
            return None

    async def get_session_element_attribute(
        self, session_name: str, selector: str, attribute: str
    ) -> Optional[str]:
        """
        Get attribute value of an element in the first page of a session.

        Args:
            session_name: Session name
            selector: CSS selector for the element
            attribute: Attribute name

        Returns:
            Attribute value or None

        Raises:
            RuntimeError: If session or page not found
        """
        context = self.contexts.get(session_name)
        if not context or not context.pages:
            raise RuntimeError(f"No active pages in session: {session_name}")

        page = context.pages[0]

        try:
            element = await page.query_selector(selector)
            if element:
                return await element.get_attribute(attribute)
            return None
        except Exception as e:
            logger.warning(
                f"Failed to get element attribute {attribute} for {selector}: {e}"
            )
            return None

    async def get_session_runtime_info(self, session_name: str) -> Dict[str, Any]:
        """
        Get runtime information about a session.

        Args:
            session_name: Session name

        Returns:
            Dictionary with runtime information
        """
        context = self.contexts.get(session_name)
        if not context:
            return {"active": False, "pages": 0}

        pages_info = await self.get_session_pages(session_name)

        return {
            "active": True,
            "page_count": len(context.pages),
            "pages": pages_info,
            "context_options": {
                "viewport": context.pages[0].viewport_size if context.pages else None,
                "user_agent": await context.pages[0].evaluate("navigator.userAgent")
                if context.pages
                else None,
            },
        }

    def get_all_session_names(self) -> List[str]:
        """
        Get names of all active browser sessions.

        Returns:
            List of session names
        """
        return list(self.contexts.keys())

    async def health_check_session(self, session_name: str) -> bool:
        """
        Perform a health check on a browser session.

        Args:
            session_name: Session name

        Returns:
            True if session is healthy, False otherwise
        """
        context = self.contexts.get(session_name)
        if not context:
            return False

        try:
            # Try to get context info
            pages = context.pages
            if pages:
                # Try to get title of first page
                await pages[0].title()
            return True
        except Exception as e:
            logger.warning(f"Health check failed for session {session_name}: {e}")
            return False
