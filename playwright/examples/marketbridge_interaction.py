#!/usr/bin/env python3
"""
MarketBridge Interaction Example

Demonstrates advanced interaction with the MarketBridge web interface
including subscribing to market data, placing orders, and monitoring
the interface state.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.browser_manager import BrowserManager
from playwright.session_manager import SessionManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def subscribe_to_market_data(
    page,
    symbol: str = "AAPL",
    instrument_type: str = "stock",
    data_type: str = "market_data",
):
    """Subscribe to market data for a symbol."""
    try:
        # Fill in the subscription form
        await page.fill("#symbol", symbol)
        await page.select_option("#instrument-type", instrument_type)
        await page.select_option("#data-type", data_type)

        # Submit the form
        await page.click("#subscribe-btn")
        logger.info(f"Subscribed to {symbol} {data_type}")

        # Wait for subscription to appear in the list
        await page.wait_for_selector(f"text={symbol}", timeout=5000)
        logger.info("Subscription appeared in active subscriptions list")

        return True

    except Exception as e:
        logger.error(f"Failed to subscribe to {symbol}: {e}")
        return False


async def check_connection_status(page):
    """Check the WebSocket connection status."""
    try:
        status_element = await page.wait_for_selector("#status-text", timeout=5000)
        status_text = await status_element.text_content()

        status_indicator = await page.query_selector("#status-indicator")
        status_class = await status_indicator.get_attribute("class")

        logger.info(f"Connection status: {status_text}")
        logger.info(f"Status indicator class: {status_class}")

        return "connected" in status_class.lower()

    except Exception as e:
        logger.error(f"Failed to check connection status: {e}")
        return False


async def monitor_market_data(page, duration_seconds: int = 30):
    """Monitor incoming market data for a specified duration."""
    logger.info(f"Monitoring market data for {duration_seconds} seconds...")

    start_time = asyncio.get_event_loop().time()
    message_count = 0

    # Set up console message monitoring
    def on_console_message(msg):
        nonlocal message_count
        if "market_data" in msg.text.lower() or "price" in msg.text.lower():
            message_count += 1
            logger.info(f"Market data update #{message_count}: {msg.text}")

    page.on("console", on_console_message)

    # Monitor for the specified duration
    while (asyncio.get_event_loop().time() - start_time) < duration_seconds:
        # Check for new data in the market data grid
        try:
            data_grid = await page.query_selector("#market-data-grid")
            if data_grid:
                content = await data_grid.text_content()
                if content and content.strip():
                    logger.debug("Market data grid has content")
        except Exception:
            pass

        await asyncio.sleep(1)

    logger.info(f"Monitoring complete. Received {message_count} market data messages.")
    return message_count


async def place_test_order(
    page, symbol: str = "AAPL", action: str = "BUY", quantity: int = 1
):
    """Place a test order (be careful with this!)."""
    logger.warning(
        "PLACING TEST ORDER - Make sure you're connected to a paper trading account!"
    )

    try:
        # Fill in the order form
        await page.fill("#order-symbol", symbol)
        await page.select_option("#order-action", action)
        await page.fill("#order-quantity", str(quantity))
        await page.select_option("#order-type", "MKT")

        # Submit the order
        await page.click("#place-order-btn")
        logger.info(f"Placed {action} order for {quantity} shares of {symbol}")

        # Wait for order status update
        await asyncio.sleep(2)

        # Check order status
        orders_list = await page.query_selector("#orders-list")
        if orders_list:
            content = await orders_list.text_content()
            logger.info(f"Order status: {content}")

        return True

    except Exception as e:
        logger.error(f"Failed to place order: {e}")
        return False


async def marketbridge_interaction_example():
    """Complete example of MarketBridge interaction."""
    session_manager = SessionManager()
    browser_manager = BrowserManager(session_manager)

    session_name = "marketbridge_interaction"

    try:
        # Start browser
        await browser_manager.start(headless=False)
        logger.info("Browser started")

        # Navigate to MarketBridge
        page = await browser_manager.navigate_to_marketbridge(session_name)
        logger.info("Navigated to MarketBridge")

        # Wait for interface to fully load
        await asyncio.sleep(3)

        # Check connection status
        is_connected = await check_connection_status(page)
        if not is_connected:
            logger.warning("WebSocket not connected. Some features may not work.")

        # Take initial screenshot
        await page.screenshot(path="marketbridge_initial.png")
        logger.info("Initial screenshot saved")

        # Subscribe to market data
        symbols = ["AAPL", "GOOGL", "MSFT"]
        for symbol in symbols:
            success = await subscribe_to_market_data(page, symbol)
            if success:
                await asyncio.sleep(1)  # Brief pause between subscriptions

        # Monitor market data for a while
        if is_connected:
            await monitor_market_data(page, duration_seconds=20)
        else:
            logger.info("Skipping market data monitoring due to connection issues")

        # Take final screenshot
        await page.screenshot(path="marketbridge_with_data.png")
        logger.info("Final screenshot saved")

        # Optional: Place a test order (uncomment if you want to test)
        # WARNING: Only use with paper trading accounts!
        # await place_test_order(page, "AAPL", "BUY", 1)

        logger.info("Example completed successfully!")
        logger.info("Browser will remain open for 10 more seconds...")
        await asyncio.sleep(10)

    except Exception as e:
        logger.error(f"Error during MarketBridge interaction: {e}")
        raise
    finally:
        await browser_manager.stop()
        logger.info("Browser stopped")


async def main():
    """Run the MarketBridge interaction example."""
    print("MarketBridge Interaction Example")
    print("=" * 35)
    print()
    print("This example will:")
    print("1. Connect to MarketBridge web interface")
    print("2. Subscribe to market data for AAPL, GOOGL, MSFT")
    print("3. Monitor incoming data")
    print("4. Take screenshots")
    print()

    response = input("Make sure MarketBridge server is running. Continue? (y/N): ")
    if response.lower() != "y":
        print("Cancelled.")
        return

    await marketbridge_interaction_example()


if __name__ == "__main__":
    asyncio.run(main())
