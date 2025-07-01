#!/usr/bin/env python3
"""
MarketBridge UI Parser

Demonstrates parsing MarketBridge web interface data using browser-bunny.
Inspired by browser-bunny's parser patterns.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

from browser_bunny.persistent_session_manager import get_persistent_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)


async def parse_marketbridge_ui():
    """Parse MarketBridge UI data following browser-bunny parser patterns."""
    print("🔍 Parsing MarketBridge UI data...")

    # Get or create persistent session
    manager = await get_persistent_session("marketbridge_parser")

    try:
        # Navigate to MarketBridge
        await manager.navigate_to(
            "http://localhost:8080", wait_until="domcontentloaded"
        )

        # Take screenshot for debugging
        await manager.screenshot("marketbridge_parse_start.png")
        logger.info("Screenshot taken: marketbridge_parse_start.png")

        # Wait for the UI to fully load
        await asyncio.sleep(2)

        # Parse market data table
        market_data = await parse_market_data_table(manager)

        # Parse connection status
        connection_status = await parse_connection_status(manager)

        # Parse subscription list
        subscriptions = await parse_subscription_list(manager)

        # Combine all parsed data
        parsed_data = {
            "timestamp": datetime.now().isoformat(),
            "source": "marketbridge",
            "connection_status": connection_status,
            "market_data": market_data,
            "subscriptions": subscriptions,
            "data_count": len(market_data) if market_data else 0,
            "subscription_count": len(subscriptions) if subscriptions else 0,
        }

        # Save results
        results_file = project_root / "results" / "marketbridge_parse_results.json"
        results_file.parent.mkdir(exist_ok=True)

        with open(results_file, "w") as f:
            json.dump(parsed_data, f, indent=2)

        print(f"✅ Parsing complete!")
        print(f"📊 Found {parsed_data['data_count']} market data items")
        print(f"📋 Found {parsed_data['subscription_count']} subscriptions")
        print(f"🔗 Connection: {connection_status}")
        print(f"💾 Results saved to: {results_file}")

        # Take final screenshot
        await manager.screenshot("marketbridge_parse_complete.png")

        return parsed_data

    except Exception as e:
        logger.error(f"Error parsing MarketBridge UI: {e}", exc_info=True)
        # Take error screenshot for debugging
        await manager.screenshot("marketbridge_parse_error.png")
        raise
    finally:
        # Don't cleanup - leave persistent session open for reuse
        await manager.cleanup()


async def parse_market_data_table(manager):
    """Parse the market data table."""
    print("📊 Parsing market data table...")

    js_code = """
    (() => {
        const marketData = [];
        const dataRows = document.querySelectorAll('#market-data-table tbody tr');

        dataRows.forEach((row, index) => {
            const cells = row.querySelectorAll('td');

            if (cells.length >= 4) {
                const dataItem = {
                    rank: index + 1,
                    symbol: cells[0]?.textContent?.trim() || '',
                    bid: cells[1]?.textContent?.trim() || '',
                    ask: cells[2]?.textContent?.trim() || '',
                    last: cells[3]?.textContent?.trim() || '',
                    timestamp: new Date().toISOString()
                };

                // Parse additional columns if they exist
                if (cells.length > 4) {
                    dataItem.volume = cells[4]?.textContent?.trim() || '';
                }
                if (cells.length > 5) {
                    dataItem.change = cells[5]?.textContent?.trim() || '';
                }

                marketData.push(dataItem);
            }
        });

        return marketData;
    })()
    """

    try:
        market_data = await manager.execute_js(js_code)
        logger.info(
            f"Parsed {len(market_data) if market_data else 0} market data items"
        )
        return market_data or []
    except Exception as e:
        logger.warning(f"Failed to parse market data table: {e}")
        return []


async def parse_connection_status(manager):
    """Parse the connection status."""
    print("🔗 Parsing connection status...")

    js_code = """
    (() => {
        const statusElement = document.querySelector('#status-text');
        return statusElement ? statusElement.textContent.trim() : 'Unknown';
    })()
    """

    try:
        status = await manager.execute_js(js_code)
        logger.info(f"Connection status: {status}")
        return status
    except Exception as e:
        logger.warning(f"Failed to parse connection status: {e}")
        return "Error parsing status"


async def parse_subscription_list(manager):
    """Parse the subscription list."""
    print("📋 Parsing subscription list...")

    js_code = """
    (() => {
        const subscriptions = [];
        const subItems = document.querySelectorAll('#subscriptions-list .subscription-item');

        subItems.forEach((item, index) => {
            const subscription = {
                rank: index + 1,
                symbol: '',
                type: '',
                status: 'active'
            };

            // Try to extract symbol
            const symbolElement = item.querySelector('.symbol') ||
                                 item.querySelector('[data-symbol]') ||
                                 item;

            if (symbolElement) {
                subscription.symbol = symbolElement.textContent?.trim() ||
                                    symbolElement.dataset?.symbol ||
                                    `subscription_${index + 1}`;
            }

            // Try to extract type
            const typeElement = item.querySelector('.type') ||
                               item.querySelector('[data-type]');
            if (typeElement) {
                subscription.type = typeElement.textContent?.trim() ||
                                  typeElement.dataset?.type ||
                                  'market_data';
            }

            subscriptions.push(subscription);
        });

        return subscriptions;
    })()
    """

    try:
        subscriptions = await manager.execute_js(js_code)
        logger.info(
            f"Parsed {len(subscriptions) if subscriptions else 0} subscriptions"
        )
        return subscriptions or []
    except Exception as e:
        logger.warning(f"Failed to parse subscription list: {e}")
        return []


async def debug_dom_structure(manager):
    """Debug DOM structure for development."""
    print("🔍 Debugging DOM structure...")

    # Take screenshot first
    await manager.screenshot("marketbridge_dom_debug.png")

    js_code = """
    (() => {
        const structure = {
            app_element: !!document.querySelector('#app'),
            status_element: !!document.querySelector('#status-text'),
            market_table: !!document.querySelector('#market-data-table'),
            subscription_list: !!document.querySelector('#subscriptions-list'),
            available_ids: Array.from(document.querySelectorAll('[id]')).map(el => el.id),
            available_classes: Array.from(new Set(
                Array.from(document.querySelectorAll('[class]'))
                .flatMap(el => Array.from(el.classList))
            )),
            table_structure: {
                headers: Array.from(document.querySelectorAll('#market-data-table th')).map(th => th.textContent.trim()),
                row_count: document.querySelectorAll('#market-data-table tbody tr').length
            }
        };

        return structure;
    })()
    """

    try:
        structure = await manager.execute_js(js_code)
        print("📋 DOM Structure:")
        print(json.dumps(structure, indent=2))
        return structure
    except Exception as e:
        logger.error(f"Failed to debug DOM structure: {e}")
        return {}


if __name__ == "__main__":
    print("MarketBridge UI Parser (using browser-bunny)")
    print("=" * 50)
    print("This script parses data from the MarketBridge web interface.")
    print("\nMake sure:")
    print("1. Browser-bunny server is running:")
    print("   Option 1: browser-bunny start")
    print(
        "   Option 2: cd /home/seth/Software/dev/browser-bunny && source .venv/bin/activate && python3 -m browser_bunny.daemon start"
    )
    print("2. MarketBridge is running on http://localhost:8080")
    print("=" * 50)

    # Check for debug mode
    debug_mode = "--debug" in sys.argv

    try:
        if debug_mode:
            print("\n🔍 Running in DEBUG mode - will inspect DOM structure")

            async def debug_run():
                manager = await get_persistent_session("marketbridge_debug")
                try:
                    await manager.navigate_to(
                        "http://localhost:8080", wait_until="domcontentloaded"
                    )
                    await debug_dom_structure(manager)
                finally:
                    # Don't cleanup - leave persistent session open for reuse
                    await manager.cleanup()

            asyncio.run(debug_run())
        else:
            # Normal parsing mode
            result = asyncio.run(parse_marketbridge_ui())

    except KeyboardInterrupt:
        print("\n🛑 Parsing cancelled by user")
    except Exception as e:
        print(f"\n❌ Parsing failed: {e}")
        print("\nTroubleshooting:")
        print("- Check that MarketBridge web UI is accessible")
        print("- Try running with --debug to inspect DOM structure")
        print("- Check browser-bunny server logs")
        sys.exit(1)
