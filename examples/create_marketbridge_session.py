#!/usr/bin/env python3
"""Create a browser-bunny session pointing to MarketBridge UI."""
import asyncio

from browser_bunny.persistent_session_manager import get_persistent_session


async def main():
    print("Starting browser-bunny session for MarketBridge UI...")

    # Get or create persistent session
    manager = await get_persistent_session("marketbridge_ui")

    try:
        # Navigate to MarketBridge
        await manager.navigate_to("http://localhost:8080")
        print("✅ Browser session started and navigated to MarketBridge UI")

        # Take a screenshot to confirm
        await manager.screenshot("marketbridge_ui_session.png")
        print("📸 Screenshot saved to: screenshots/marketbridge_ui_session.png")

        # Get current page title
        title = await manager.execute_js("(() => { return document.title; })()")
        print(f"📄 Page title: {title}")

        # Check connection status
        status = await manager.execute_js(
            """
            (() => {
                return document.querySelector('#status-text')?.textContent || 'Status element not found';
            })()
        """
        )
        print(f"🔌 Connection status: {status}")

    finally:
        # Keep session alive - don't close it
        await manager.cleanup()
        print("\n✅ Session 'marketbridge_ui' is ready and will persist")
        print("ℹ️  You can reuse this session in other scripts or examples")


if __name__ == "__main__":
    asyncio.run(main())
