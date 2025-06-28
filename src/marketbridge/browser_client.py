"""
MarketBridge Browser Client

Programmatic client library for interacting with the MarketBridge browser session server.
Inspired by browser-bunny's browser_client.py but integrated with MarketBridge's architecture.
"""

import asyncio
import base64
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union

import aiohttp

logger = logging.getLogger(__name__)


class BrowserSessionError(Exception):
    """Exception raised for browser session errors."""

    pass


class BrowserSession:
    """
    Represents a browser session with convenience methods for automation.
    Similar to browser-bunny's session wrapper but designed for MarketBridge.
    """

    def __init__(
        self, client: "BrowserClient", session_id: str, session_data: Dict[str, Any]
    ):
        self.client = client
        self.session_id = session_id
        self.session_data = session_data
        self.pages: Dict[str, Any] = {}

    @property
    def session_name(self) -> str:
        """Get the session name."""
        return self.session_data.get("session_name", "")

    @property
    def current_url(self) -> Optional[str]:
        """Get the current URL."""
        return self.session_data.get("current_url")

    @property
    def is_active(self) -> bool:
        """Check if the session is active."""
        return self.session_data.get("active", False)

    async def navigate(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: int = 30000,
        page_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
            wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')
            timeout: Navigation timeout in milliseconds
            page_id: Optional page ID, creates new page if None

        Returns:
            Navigation result dictionary
        """
        payload = {
            "url": url,
            "wait_until": wait_until,
            "timeout": timeout,
        }

        if page_id:
            payload["page_id"] = page_id

        result = await self.client._post(
            f"/sessions/{self.session_id}/navigate", payload
        )

        # Update session data
        self.session_data["current_url"] = url

        logger.info(
            f"Navigated session {self.session_id} to {url} - "
            f"duration: {result.get('duration', 0)}ms"
        )

        return result

    async def navigate_to_marketbridge(
        self, base_url: str = "http://localhost:8080"
    ) -> Dict[str, Any]:
        """
        Navigate to MarketBridge web interface.

        Args:
            base_url: Base URL of MarketBridge web server

        Returns:
            Navigation result dictionary
        """
        return await self.navigate(base_url, wait_until="networkidle")

    async def screenshot(
        self,
        filename: Optional[str] = None,
        full_page: bool = False,
        quality: int = 90,
        page_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Take a screenshot.

        Args:
            filename: Optional filename, auto-generated if None
            full_page: Whether to capture full page
            quality: Image quality (1-100)
            page_id: Optional page ID

        Returns:
            Screenshot result with path and metadata
        """
        if filename is None:
            timestamp = int(time.time())
            filename = f"session_{self.session_id}_{timestamp}.png"

        payload = {
            "filename": filename,
            "full_page": full_page,
            "quality": quality,
        }

        if page_id:
            payload["page_id"] = page_id

        result = await self.client._post(
            f"/sessions/{self.session_id}/screenshot", payload
        )

        logger.debug(f"Screenshot taken for session {self.session_id}: {filename}")

        return result

    async def execute_js(
        self,
        script: str,
        await_promise: bool = True,
        page_id: Optional[str] = None,
    ) -> Any:
        """
        Execute JavaScript in the browser.

        Args:
            script: JavaScript code to execute
            await_promise: Whether to await promise results
            page_id: Optional page ID

        Returns:
            JavaScript execution result
        """
        payload = {
            "script": script,
            "await_promise": await_promise,
        }

        if page_id:
            payload["page_id"] = page_id

        result = await self.client._post(
            f"/sessions/{self.session_id}/execute", payload
        )

        logger.debug(f"Executed JavaScript in session {self.session_id}")

        return result.get("result")

    async def click(
        self,
        selector: str,
        timeout: int = 10000,
        page_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Click an element.

        Args:
            selector: CSS selector for the element
            timeout: Timeout in milliseconds
            page_id: Optional page ID

        Returns:
            Click result dictionary
        """
        payload = {
            "action": "click",
            "selector": selector,
            "timeout": timeout,
        }

        if page_id:
            payload["page_id"] = page_id

        result = await self.client._post(
            f"/sessions/{self.session_id}/interact", payload
        )

        logger.debug(f"Clicked element '{selector}' in session {self.session_id}")

        return result

    async def type_text(
        self,
        selector: str,
        text: str,
        clear_first: bool = True,
        timeout: int = 10000,
        page_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Type text into an element.

        Args:
            selector: CSS selector for the element
            text: Text to type
            clear_first: Whether to clear existing text first
            timeout: Timeout in milliseconds
            page_id: Optional page ID

        Returns:
            Type result dictionary
        """
        payload = {
            "action": "type",
            "selector": selector,
            "text": text,
            "clear_first": clear_first,
            "timeout": timeout,
        }

        if page_id:
            payload["page_id"] = page_id

        result = await self.client._post(
            f"/sessions/{self.session_id}/interact", payload
        )

        logger.debug(f"Typed text into '{selector}' in session {self.session_id}")

        return result

    async def wait_for_element(
        self,
        selector: str,
        timeout: int = 10000,
        state: str = "visible",
        page_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Wait for an element to appear.

        Args:
            selector: CSS selector for the element
            timeout: Timeout in milliseconds
            state: Element state to wait for ('visible', 'hidden', 'attached', 'detached')
            page_id: Optional page ID

        Returns:
            Wait result dictionary
        """
        payload = {
            "action": "wait_for_element",
            "selector": selector,
            "timeout": timeout,
            "state": state,
        }

        if page_id:
            payload["page_id"] = page_id

        result = await self.client._post(f"/sessions/{self.session_id}/wait", payload)

        logger.debug(f"Waited for element '{selector}' in session {self.session_id}")

        return result

    async def get_element_text(
        self,
        selector: str,
        timeout: int = 5000,
        page_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get text content of an element.

        Args:
            selector: CSS selector for the element
            timeout: Timeout in milliseconds
            page_id: Optional page ID

        Returns:
            Element text content or None
        """
        script = f"""
        (() => {{
            const element = document.querySelector('{selector}');
            return element ? element.textContent.trim() : null;
        }})()
        """

        return await self.execute_js(script, page_id=page_id)

    async def get_element_attribute(
        self,
        selector: str,
        attribute: str,
        timeout: int = 5000,
        page_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get attribute value of an element.

        Args:
            selector: CSS selector for the element
            attribute: Attribute name
            timeout: Timeout in milliseconds
            page_id: Optional page ID

        Returns:
            Attribute value or None
        """
        script = f"""
        (() => {{
            const element = document.querySelector('{selector}');
            return element ? element.getAttribute('{attribute}') : null;
        }})()
        """

        return await self.execute_js(script, page_id=page_id)

    async def refresh(self) -> None:
        """Refresh the session data from the server."""
        session_data = await self.client._get(f"/sessions/{self.session_id}")
        self.session_data = session_data

    async def close(self) -> None:
        """Close the browser session."""
        await self.client.delete_session(self.session_id)


class BrowserClient:
    """
    Client for interacting with the MarketBridge browser session server.
    Provides a high-level interface for browser automation similar to browser-bunny.
    """

    def __init__(self, base_url: str = "http://localhost:8766"):
        """
        Initialize the browser client.

        Args:
            base_url: Base URL of the browser session server
        """
        self.base_url = base_url.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None

        logger.info(f"Browser client initialized - base_url: {self.base_url}")

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the HTTP session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _get(self, endpoint: str) -> Dict[str, Any]:
        """Make a GET request."""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"

        async with session.get(url) as response:
            if response.status >= 400:
                text = await response.text()
                raise BrowserSessionError(
                    f"GET {endpoint} failed: {response.status} - {text}"
                )

            return await response.json()

    async def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request."""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"

        async with session.post(url, json=data) as response:
            if response.status >= 400:
                text = await response.text()
                raise BrowserSessionError(
                    f"POST {endpoint} failed: {response.status} - {text}"
                )

            return await response.json()

    async def _delete(self, endpoint: str) -> Dict[str, Any]:
        """Make a DELETE request."""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"

        async with session.delete(url) as response:
            if response.status >= 400:
                text = await response.text()
                raise BrowserSessionError(
                    f"DELETE {endpoint} failed: {response.status} - {text}"
                )

            return await response.json()

    async def create_session(
        self,
        session_name: str,
        headless: bool = False,
        viewport: Optional[Dict[str, int]] = None,
        browser_type: str = "chromium",
    ) -> BrowserSession:
        """
        Create a new browser session.

        Args:
            session_name: Human-readable session name
            headless: Whether to run in headless mode
            viewport: Viewport size dictionary with 'width' and 'height'
            browser_type: Browser type ('chromium', 'firefox', 'webkit')

        Returns:
            BrowserSession instance
        """
        if viewport is None:
            viewport = {"width": 1920, "height": 1080}

        payload = {
            "session_name": session_name,
            "config": {
                "headless": headless,
                "viewport": viewport,
                "browser_type": browser_type,
            },
        }

        result = await self._post("/sessions", payload)
        session_id = result["session_id"]
        session_data = result["session_data"]

        session = BrowserSession(self, session_id, session_data)

        logger.info(
            f"Created browser session - session_id: {session_id}, "
            f"session_name: {session_name}, headless: {headless}"
        )

        return session

    async def get_session(self, session_id: str) -> Optional[BrowserSession]:
        """
        Get an existing browser session.

        Args:
            session_id: Session ID to retrieve

        Returns:
            BrowserSession instance or None if not found
        """
        try:
            session_data = await self._get(f"/sessions/{session_id}")
            return BrowserSession(self, session_id, session_data)
        except BrowserSessionError:
            return None

    async def get_session_by_name(self, session_name: str) -> Optional[BrowserSession]:
        """
        Get an existing browser session by name.

        Args:
            session_name: Session name to retrieve

        Returns:
            BrowserSession instance or None if not found
        """
        sessions = await self.list_sessions()
        for session_data in sessions:
            if session_data.get("session_name") == session_name:
                session_id = session_data["session_id"]
                return BrowserSession(self, session_id, session_data)

        return None

    async def list_sessions(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """
        List all browser sessions.

        Args:
            active_only: If True, only return active sessions

        Returns:
            List of session data dictionaries
        """
        endpoint = "/sessions"
        if active_only:
            endpoint += "?active_only=true"

        result = await self._get(endpoint)
        return result.get("sessions", [])

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a browser session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if session was deleted, False if not found
        """
        try:
            await self._delete(f"/sessions/{session_id}")
            logger.info(f"Deleted browser session: {session_id}")
            return True
        except BrowserSessionError:
            return False

    async def server_health(self) -> Dict[str, Any]:
        """
        Check server health.

        Returns:
            Server health status dictionary
        """
        return await self._get("/health")

    async def server_stats(self) -> Dict[str, Any]:
        """
        Get server statistics.

        Returns:
            Server statistics dictionary
        """
        return await self._get("/stats")

    async def cleanup_sessions(self, max_age_hours: int = 24) -> List[str]:
        """
        Clean up old sessions.

        Args:
            max_age_hours: Maximum age in hours before sessions are cleaned up

        Returns:
            List of deleted session IDs
        """
        payload = {"max_age_hours": max_age_hours}
        result = await self._post("/cleanup", payload)

        deleted_sessions = result.get("deleted_sessions", [])
        logger.info(f"Cleaned up {len(deleted_sessions)} old sessions")

        return deleted_sessions


class BrowserController:
    """
    High-level controller for browser automation workflows.
    Provides convenience methods for common MarketBridge automation tasks.
    """

    def __init__(self, base_url: str = "http://localhost:8766"):
        """
        Initialize the browser controller.

        Args:
            base_url: Base URL of the browser session server
        """
        self.client = BrowserClient(base_url)
        self.current_session: Optional[BrowserSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.current_session:
            await self.current_session.close()
        await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def start_session(
        self,
        session_name: str = "marketbridge_session",
        headless: bool = False,
        auto_navigate: bool = True,
    ) -> BrowserSession:
        """
        Start a new browser session or reuse existing one.

        Args:
            session_name: Session name
            headless: Whether to run in headless mode
            auto_navigate: Whether to automatically navigate to MarketBridge

        Returns:
            BrowserSession instance
        """
        # Try to get existing session first
        session = await self.client.get_session_by_name(session_name)

        if session and session.is_active:
            logger.info(f"Reusing existing session: {session_name}")
            self.current_session = session
        else:
            # Create new session
            session = await self.client.create_session(session_name, headless=headless)
            self.current_session = session

            if auto_navigate:
                await session.navigate_to_marketbridge()

        return session

    async def navigate_to_marketbridge(
        self, base_url: str = "http://localhost:8080"
    ) -> Dict[str, Any]:
        """
        Navigate current session to MarketBridge.

        Args:
            base_url: Base URL of MarketBridge web server

        Returns:
            Navigation result dictionary
        """
        if not self.current_session:
            raise BrowserSessionError("No active session")

        return await self.current_session.navigate_to_marketbridge(base_url)

    async def wait_for_marketbridge_ready(self, timeout: int = 30000) -> bool:
        """
        Wait for MarketBridge interface to be ready.

        Args:
            timeout: Timeout in milliseconds

        Returns:
            True if ready, False if timeout
        """
        if not self.current_session:
            raise BrowserSessionError("No active session")

        try:
            await self.current_session.wait_for_element("#app", timeout=timeout)
            await self.current_session.wait_for_element("#status-text", timeout=5000)
            return True
        except Exception as e:
            logger.warning(f"MarketBridge not ready within timeout: {e}")
            return False

    async def subscribe_to_market_data(
        self,
        symbol: str,
        instrument_type: str = "stock",
        data_type: str = "market_data",
    ) -> bool:
        """
        Subscribe to market data for a symbol.

        Args:
            symbol: Trading symbol (e.g., 'AAPL')
            instrument_type: Instrument type ('stock', 'option', 'future')
            data_type: Data type ('market_data', 'level2')

        Returns:
            True if subscription successful, False otherwise
        """
        if not self.current_session:
            raise BrowserSessionError("No active session")

        try:
            # Fill in the symbol
            await self.current_session.type_text("#symbol", symbol)

            # Select instrument type
            await self.current_session.click(
                f"#instrument-type option[value='{instrument_type}']"
            )

            # Select data type
            await self.current_session.click(f"#data-type option[value='{data_type}']")

            # Click subscribe button
            await self.current_session.click("#subscribe-btn")

            # Wait for subscription to appear
            await self.current_session.wait_for_element(f"text={symbol}", timeout=5000)

            logger.info(f"Subscribed to market data: {symbol}")
            return True

        except Exception as e:
            logger.error(f"Failed to subscribe to market data for {symbol}: {e}")
            return False

    async def take_debug_screenshot(self, description: str = "") -> str:
        """
        Take a screenshot for debugging purposes.

        Args:
            description: Optional description for the screenshot

        Returns:
            Screenshot filename
        """
        if not self.current_session:
            raise BrowserSessionError("No active session")

        timestamp = int(time.time())
        if description:
            filename = f"debug_{description}_{timestamp}.png"
        else:
            filename = f"debug_{timestamp}.png"

        result = await self.current_session.screenshot(filename, full_page=True)

        logger.info(f"Debug screenshot taken: {filename}")
        return result["filename"]
