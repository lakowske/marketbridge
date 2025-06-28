#!/usr/bin/env python3
"""
MarketBridge Browser Session Example

Demonstrates using the browser-bunny inspired architecture for browser automation
with persistent sessions and server-based control.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

from marketbridge.browser_client import BrowserClient, BrowserController

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def basic_browser_session_example():
    """
    Basic example of using the browser session client.

    This demonstrates:
    - Creating a persistent browser session
    - Navigating to MarketBridge
    - Taking screenshots
    - Executing JavaScript
    - Session reuse across script runs
    """
    print("=== Basic Browser Session Example ===")

    # Create browser client
    async with BrowserClient("http://localhost:8766") as client:
        try:
            # Check server health
            health = await client.server_health()
            print(f"Server health: {health}")

            # Create or reuse a session
            session_name = "demo_session"

            # Try to get existing session first
            session = await client.get_session_by_name(session_name)

            if session:
                print(f"Reusing existing session: {session_name}")
            else:
                print(f"Creating new session: {session_name}")
                session = await client.create_session(
                    session_name=session_name,
                    headless=False,
                    viewport={"width": 1920, "height": 1080},
                )

            # Navigate to MarketBridge
            print("Navigating to MarketBridge...")
            nav_result = await session.navigate(
                "http://localhost:8080", wait_until="networkidle"
            )
            print(f"Navigation completed in {nav_result.get('duration', 0):.1f}ms")

            # Wait for app to load
            print("Waiting for MarketBridge app to load...")
            await session.wait_for_element("#app", timeout=10000)

            # Take a screenshot
            print("Taking screenshot...")
            screenshot_result = await session.screenshot(
                "marketbridge_demo.png", full_page=True
            )
            print(f"Screenshot saved: {screenshot_result['filename']}")

            # Execute JavaScript to get connection status
            print("Checking connection status...")
            status_text = await session.execute_js(
                """
                (() => {
                    const statusElement = document.querySelector('#status-text');
                    return statusElement ? statusElement.textContent : 'Status not found';
                })()
            """
            )
            print(f"Connection status: {status_text}")

            # Get active subscriptions count
            print("Checking active subscriptions...")
            subscriptions_count = await session.execute_js(
                """
                (() => {
                    const subscriptions = document.querySelectorAll('#subscriptions-list .subscription-item');
                    return subscriptions.length;
                })()
            """
            )
            print(f"Active subscriptions: {subscriptions_count}")

            # Session persists across script runs
            print(
                f"\nSession '{session_name}' will persist. Run this script again to reuse it!"
            )

        except Exception as e:
            logger.error(f"Error in basic example: {e}")
            raise


async def marketbridge_automation_example():
    """
    Advanced example showing MarketBridge-specific automation.

    This demonstrates:
    - Using the high-level BrowserController
    - Subscribing to market data
    - Monitoring real-time updates
    - Taking debug screenshots
    """
    print("\n=== MarketBridge Automation Example ===")

    async with BrowserController("http://localhost:8765") as controller:
        try:
            # Start or reuse session
            session = await controller.start_session(
                session_name="marketbridge_automation",
                headless=False,
                auto_navigate=True,
            )

            # Wait for MarketBridge to be ready
            print("Waiting for MarketBridge to be ready...")
            ready = await controller.wait_for_marketbridge_ready()

            if not ready:
                print("MarketBridge not ready, exiting...")
                return

            print("MarketBridge is ready!")

            # Subscribe to some symbols
            symbols = ["AAPL", "GOOGL", "MSFT"]

            for symbol in symbols:
                print(f"Subscribing to {symbol}...")
                success = await controller.subscribe_to_market_data(symbol)
                if success:
                    print(f"✓ Subscribed to {symbol}")
                else:
                    print(f"✗ Failed to subscribe to {symbol}")

                # Small delay between subscriptions
                await asyncio.sleep(1)

            # Take a screenshot of subscriptions
            print("\nTaking screenshot of active subscriptions...")
            screenshot_file = await controller.take_debug_screenshot("subscriptions")
            print(f"Screenshot saved: {screenshot_file}")

            # Monitor for a few seconds
            print("\nMonitoring market data for 10 seconds...")

            # Execute JavaScript to capture market data updates
            for i in range(10):
                await asyncio.sleep(1)

                # Get latest market data from the UI
                market_data = await session.execute_js(
                    """
                    (() => {
                        const dataRows = document.querySelectorAll('#market-data-table tbody tr');
                        const data = [];
                        dataRows.forEach(row => {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 4) {
                                data.push({
                                    symbol: cells[0].textContent,
                                    bid: cells[1].textContent,
                                    ask: cells[2].textContent,
                                    last: cells[3].textContent
                                });
                            }
                        });
                        return data;
                    })()
                """
                )

                if market_data:
                    print(f"\nMarket Data Update {i+1}:")
                    for item in market_data:
                        print(
                            f"  {item['symbol']}: Bid={item['bid']}, Ask={item['ask']}, Last={item['last']}"
                        )

            print("\n✓ Automation example completed!")

        except Exception as e:
            logger.error(f"Error in automation example: {e}")
            raise


async def session_management_example():
    """
    Example showing session management capabilities.

    This demonstrates:
    - Listing all sessions
    - Creating multiple sessions
    - Cleaning up old sessions
    - Server statistics
    """
    print("\n=== Session Management Example ===")

    async with BrowserClient("http://localhost:8766") as client:
        try:
            # Get server stats
            print("Server Statistics:")
            stats = await client.server_stats()
            print(f"  Total sessions: {stats.get('total_sessions', 0)}")
            print(f"  Active sessions: {stats.get('active_sessions', 0)}")
            print(f"  Server uptime: {stats.get('server_uptime', 0):.1f} seconds")

            # List all sessions
            print("\nExisting Sessions:")
            sessions = await client.list_sessions()
            for session_data in sessions:
                print(
                    f"  - {session_data['session_name']} (ID: {session_data['session_id'][:8]}...)"
                )
                print(f"    Created: {session_data['created_at']}")
                print(f"    Active: {session_data.get('active', False)}")
                print(f"    URL: {session_data.get('current_url', 'N/A')}")

            # Create multiple sessions for different purposes
            session_configs = [
                {"name": "market_monitor", "purpose": "Monitor market data"},
                {"name": "order_entry", "purpose": "Place orders"},
                {"name": "analytics", "purpose": "View analytics"},
            ]

            print("\nCreating specialized sessions:")
            for config in session_configs:
                try:
                    # Check if session already exists
                    existing = await client.get_session_by_name(config["name"])
                    if existing:
                        print(f"  ✓ Session '{config['name']}' already exists")
                    else:
                        session = await client.create_session(
                            session_name=config["name"],
                            headless=True,  # Run in headless mode for this example
                        )
                        print(
                            f"  ✓ Created session '{config['name']}' for {config['purpose']}"
                        )
                except Exception as e:
                    print(f"  ✗ Failed to create session '{config['name']}': {e}")

            # Clean up old sessions (older than 1 hour for demo)
            print("\nCleaning up old sessions (>1 hour)...")
            deleted_sessions = await client.cleanup_sessions(max_age_hours=1)
            if deleted_sessions:
                print(f"  Deleted {len(deleted_sessions)} old sessions")
                for session_id in deleted_sessions:
                    print(f"    - {session_id[:8]}...")
            else:
                print("  No old sessions to clean up")

            # Final session count
            final_sessions = await client.list_sessions()
            print(f"\nFinal session count: {len(final_sessions)}")

        except Exception as e:
            logger.error(f"Error in session management example: {e}")
            raise


async def main():
    """Run all examples."""
    print("MarketBridge Browser Session Examples")
    print("=====================================")
    print("\nMake sure the browser session server is running:")
    print("  python scripts/browser_session_daemon.py start")
    print("\nAnd MarketBridge is running on http://localhost:8080")
    print("=====================================\n")

    try:
        # Run basic example
        await basic_browser_session_example()

        # Small delay between examples
        await asyncio.sleep(2)

        # Run automation example
        await marketbridge_automation_example()

        # Small delay
        await asyncio.sleep(2)

        # Run session management example
        await session_management_example()

        print("\n✓ All examples completed successfully!")

    except Exception as e:
        logger.error(f"Example failed: {e}")
        print("\nMake sure:")
        print(
            "1. The browser session server is running (python scripts/browser_session_daemon.py start)"
        )
        print("2. MarketBridge is running on http://localhost:8080")
        print(
            "3. Playwright is installed (pip install playwright && playwright install)"
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
