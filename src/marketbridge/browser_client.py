"""
MarketBridge Browser Client

Thin wrapper around browser-bunny with MarketBridge-specific convenience methods.
"""

import logging
from typing import Any, Dict, Optional

# Import everything from browser-bunny
from browser_bunny import SessionManager
from browser_bunny.client import BrowserClient as BunnyBrowserClient
from browser_bunny.session_registry import SessionRegistry

logger = logging.getLogger(__name__)


class BrowserClient(BunnyBrowserClient):
    """
    MarketBridge browser client - thin wrapper around browser-bunny's BrowserClient.

    Provides the same functionality as browser-bunny with MarketBridge-specific defaults.
    """

    def __init__(self, base_url: str = "http://localhost:9247"):
        """
        Initialize the MarketBridge browser client.

        Args:
            base_url: Base URL of the browser-bunny server (default port changed from 8766 to 9247)
        """
        super().__init__(base_url)
        logger.info(f"MarketBridge browser client initialized - base_url: {base_url}")


class BrowserController:
    """
    High-level controller for MarketBridge browser automation workflows.

    Provides convenience methods for common MarketBridge automation tasks.
    """

    def __init__(self, base_url: str = "http://localhost:9247"):
        """
        Initialize the browser controller.

        Args:
            base_url: Base URL of the browser-bunny server
        """
        self.session_manager = None
        self.base_url = base_url

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session_manager:
            await self.session_manager.cleanup()

    async def start_session(
        self,
        session_name: str = "marketbridge_session",
        headless: bool = False,
        auto_navigate: bool = True,
    ) -> SessionManager:
        """
        Start a new browser session or reuse existing one.

        Args:
            session_name: Session name
            headless: Whether to run in headless mode
            auto_navigate: Whether to automatically navigate to MarketBridge

        Returns:
            SessionManager instance
        """
        self.session_manager = SessionManager(
            session_name=session_name, server_url=self.base_url
        )

        if auto_navigate:
            await self.session_manager.navigate_to(
                "http://localhost:8080", wait_until="networkidle"
            )

        return self.session_manager

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
        if not self.session_manager:
            raise RuntimeError("No active session. Call start_session() first.")

        return await self.session_manager.navigate_to(
            base_url, wait_until="networkidle"
        )

    async def wait_for_marketbridge_ready(self, timeout: int = 30000) -> bool:
        """
        Wait for MarketBridge interface to be ready.

        Args:
            timeout: Timeout in milliseconds

        Returns:
            True if ready, False if timeout
        """
        if not self.session_manager:
            raise RuntimeError("No active session. Call start_session() first.")

        try:
            # Wait for app element
            await self.session_manager.execute_js(
                """
                return new Promise((resolve, reject) => {
                    const timeout = setTimeout(() => reject(new Error('Timeout')), %d);

                    function checkReady() {
                        const app = document.querySelector('#app');
                        const status = document.querySelector('#status-text');

                        if (app && status) {
                            clearTimeout(timeout);
                            resolve(true);
                        } else {
                            setTimeout(checkReady, 100);
                        }
                    }

                    checkReady();
                });
            """
                % timeout
            )
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
        if not self.session_manager:
            raise RuntimeError("No active session. Call start_session() first.")

        try:
            # Fill in the symbol
            await self.session_manager.execute_js(
                f"""
                const symbolInput = document.querySelector('#symbol');
                if (symbolInput) {{
                    symbolInput.value = '{symbol}';
                    symbolInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
            """
            )

            # Select instrument type
            await self.session_manager.execute_js(
                f"""
                const instrumentSelect = document.querySelector('#instrument-type');
                if (instrumentSelect) {{
                    instrumentSelect.value = '{instrument_type}';
                    instrumentSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            """
            )

            # Select data type
            await self.session_manager.execute_js(
                f"""
                const dataTypeSelect = document.querySelector('#data-type');
                if (dataTypeSelect) {{
                    dataTypeSelect.value = '{data_type}';
                    dataTypeSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            """
            )

            # Click subscribe button
            await self.session_manager.execute_js(
                """
                const subscribeBtn = document.querySelector('#subscribe-btn');
                if (subscribeBtn) {
                    subscribeBtn.click();
                }
            """
            )

            # Wait a moment for subscription to process
            import asyncio

            await asyncio.sleep(1)

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
        if not self.session_manager:
            raise RuntimeError("No active session. Call start_session() first.")

        import time

        timestamp = int(time.time())
        if description:
            filename = f"debug_{description}_{timestamp}.png"
        else:
            filename = f"debug_{timestamp}.png"

        await self.session_manager.screenshot(filename, full_page=True)

        logger.info(f"Debug screenshot taken: {filename}")
        return filename


# Convenience re-exports for compatibility
__all__ = ["BrowserClient", "BrowserController", "SessionManager", "SessionRegistry"]
