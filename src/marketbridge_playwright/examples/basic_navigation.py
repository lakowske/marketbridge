#!/usr/bin/env python3
"""
Basic Playwright Navigation Example

Demonstrates basic browser automation with MarketBridge using
persistent sessions and the browser manager.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from marketbridge_playwright.browser_manager import BrowserManager
from marketbridge_playwright.session_manager import SessionManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_navigation_example():
    """Example of basic navigation with persistent session."""
    # Create managers
    session_manager = SessionManager()
    browser_manager = BrowserManager(session_manager)

    session_name = "basic_example"

    try:
        # Start browser (non-headless so you can see what's happening)
        await browser_manager.start(headless=False)
        logger.info("Browser started")

        # Create or restore session
        context = await browser_manager.create_session_context(session_name)
        logger.info(f"Session context created: {session_name}")

        # Create a new page
        page = await browser_manager.new_page(session_name)
        logger.info("New page created")

        # Navigate to a website
        await page.goto("https://example.com")
        logger.info("Navigated to example.com")

        # Wait a bit and take a screenshot
        await asyncio.sleep(2)
        screenshot_path = Path(__file__).parent / "example_screenshot.png"
        await page.screenshot(path=str(screenshot_path))
        logger.info(f"Screenshot saved: {screenshot_path}")

        # Interact with the page
        title = await page.title()
        logger.info(f"Page title: {title}")

        # Wait for user to see the browser
        logger.info("Browser will remain open for 10 seconds...")
        await asyncio.sleep(10)

    except Exception as e:
        logger.error(f"Error during navigation: {e}")
        raise
    finally:
        # Clean up
        await browser_manager.stop()
        logger.info("Browser stopped")


async def marketbridge_navigation_example():
    """Example of navigating to MarketBridge interface."""
    session_manager = SessionManager()
    browser_manager = BrowserManager(session_manager)

    session_name = "marketbridge_example"

    try:
        # Start browser
        await browser_manager.start(headless=False)
        logger.info("Browser started")

        # Navigate to MarketBridge (assumes it's running on localhost:8080)
        try:
            page = await browser_manager.navigate_to_marketbridge(session_name)
            logger.info("Successfully navigated to MarketBridge")

            # Wait for the interface to load
            await page.wait_for_selector(".header", timeout=10000)
            logger.info("MarketBridge interface loaded")

            # Take a screenshot
            screenshot_path = Path(__file__).parent / "marketbridge_screenshot.png"
            await page.screenshot(path=str(screenshot_path))
            logger.info(f"MarketBridge screenshot saved: {screenshot_path}")

            # Check connection status
            status_text = await page.text_content("#status-text")
            logger.info(f"Connection status: {status_text}")

            # Wait for user to see the interface
            logger.info("MarketBridge interface will remain open for 15 seconds...")
            await asyncio.sleep(15)

        except Exception as e:
            logger.warning(f"Could not connect to MarketBridge: {e}")
            logger.info(
                "Make sure MarketBridge server is running on http://localhost:8080"
            )

    except Exception as e:
        logger.error(f"Error during MarketBridge navigation: {e}")
        raise
    finally:
        await browser_manager.stop()
        logger.info("Browser stopped")


async def main():
    """Run the examples."""
    print("Playwright Basic Navigation Examples")
    print("=" * 40)

    choice = input(
        "Choose example:\n1. Basic navigation (example.com)\n2. MarketBridge navigation\nChoice (1 or 2): "
    )

    if choice == "1":
        await basic_navigation_example()
    elif choice == "2":
        await marketbridge_navigation_example()
    else:
        print("Invalid choice. Running basic navigation example.")
        await basic_navigation_example()


if __name__ == "__main__":
    asyncio.run(main())
