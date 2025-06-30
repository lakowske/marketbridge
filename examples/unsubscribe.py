#!/usr/bin/env python3
"""General unsubscribe from market data script"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

import os
import sys

# Add browser-bunny to Python path
sys.path.insert(0, "/home/seth/Software/dev/browser-bunny")
from browser_bunny import SessionManager


async def unsubscribe_from_symbol(symbol: str):
    """Unsubscribe from market data for a given symbol using browser-bunny."""
    # Use existing browser session or create new one with timestamp
    import time

    session_name = f"marketbridge_unsubscribe_{int(time.time())}"
    manager = SessionManager(session_name)

    try:
        print(f"📉 Unsubscribing from {symbol}...")

        # Navigate to MarketBridge
        await manager.navigate_to("http://localhost:8080")
        print(f"✅ Connected to MarketBridge UI")

        # Take a screenshot before unsubscription
        await manager.screenshot(f"before_unsubscribe_{symbol}.png")

        # Try using the unsubscribe button in the subscription form
        print("📝 Filling unsubscribe form...")
        unsubscribe_result = await manager.execute_js(
            f"""
            (() => {{
                try {{
                    // Fill symbol field
                    const symbolInput = document.querySelector('#symbol');
                    if (symbolInput) {{
                        symbolInput.value = '{symbol}';
                        symbolInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        symbolInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}

                    // Click unsubscribe button
                    const unsubscribeBtn = document.querySelector('#unsubscribe-btn');
                    if (unsubscribeBtn) {{
                        unsubscribeBtn.click();
                        return {{
                            success: true,
                            message: 'Clicked unsubscribe button for {symbol}'
                        }};
                    }} else {{
                        return {{
                            success: false,
                            message: 'Unsubscribe button not found'
                        }};
                    }}
                }} catch (error) {{
                    return {{
                        success: false,
                        error: error.message
                    }};
                }}
            }})()
        """
        )

        print(f"🔍 Unsubscribe result: {unsubscribe_result}")

        if not unsubscribe_result or not unsubscribe_result.get("success"):
            print(f"❌ Failed to unsubscribe: {unsubscribe_result}")
            return False

        # Wait for unsubscription to process
        print("⏳ Waiting for unsubscription to process...")
        await asyncio.sleep(3)

        # Take screenshot after unsubscription
        await manager.screenshot(f"after_unsubscribe_{symbol}.png")

        # Verify unsubscription was successful
        print("🔍 Checking unsubscription status...")
        verification_result = await manager.execute_js(
            f"""
            (() => {{
                try {{
                    const subscriptionsList = document.querySelector('#subscriptions-list');
                    const marketDataGrid = document.querySelector('#market-data-grid');

                    let foundInSubscriptions = false;
                    let foundInTable = false;
                    let subscriptionCount = 0;
                    let subscriptionsText = "";

                    if (subscriptionsList) {{
                        subscriptionsText = subscriptionsList.textContent || subscriptionsList.innerHTML || "";
                        foundInSubscriptions = subscriptionsText.includes('{symbol}');
                        const items = subscriptionsList.querySelectorAll('.subscription-item, li, div');
                        subscriptionCount = Array.from(items).filter(item =>
                            item.textContent && item.textContent.trim().length > 0
                        ).length;
                    }}

                    if (marketDataGrid) {{
                        const marketDataText = marketDataGrid.textContent || marketDataGrid.innerHTML || "";
                        foundInTable = marketDataText.includes('{symbol}');
                    }}

                    return {{
                        success: true,
                        foundInSubscriptions: foundInSubscriptions,
                        foundInTable: foundInTable,
                        subscriptionCount: subscriptionCount,
                        subscriptionsText: subscriptionsText.substring(0, 200),
                        timestamp: new Date().toISOString(),
                        pageTitle: document.title
                    }};
                }} catch (error) {{
                    return {{
                        success: false,
                        error: error.message
                    }};
                }}
            }})()
        """
        )

        print(f"🔍 Raw verification result: {verification_result}")

        if verification_result is None:
            check_data = {
                "success": False,
                "error": "JavaScript execution returned None",
            }
        elif isinstance(verification_result, dict):
            check_data = verification_result
        else:
            check_data = {
                "success": False,
                "error": f"Unexpected result type: {type(verification_result)}",
            }

        print("\n📉 Unsubscription Status:")
        print("=" * 40)
        print(f"🌐 Page: {check_data.get('pageTitle', 'Unknown')}")

        if not check_data.get("foundInSubscriptions"):
            print(f"✅ {symbol} removed from subscriptions list")
        else:
            print(f"❌ {symbol} still found in subscriptions list")

        if not check_data.get("foundInTable"):
            print(f"✅ {symbol} removed from market data table")
        else:
            print(f"❌ {symbol} still found in market data table")

        print(f"📋 Active subscriptions: {check_data.get('subscriptionCount', 0)}")
        print(f"⏰ Checked at: {check_data.get('timestamp', 'Unknown')}")

        success = not (
            check_data.get("foundInSubscriptions") or check_data.get("foundInTable")
        )

        if success:
            print(f"\n🎉 Successfully unsubscribed from {symbol}!")
        else:
            print(f"\n⚠️ Unsubscription may not have completed.")

        print(f"\n📷 Screenshots saved:")
        print(f"  - before_unsubscribe_{symbol}.png")
        print(f"  - after_unsubscribe_{symbol}.png")

        return success

    except Exception as e:
        print(f"❌ Error during unsubscription: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Unsubscribe from market data")
    parser.add_argument("symbol", help="Symbol to unsubscribe from (e.g., AAPL, MNQ)")
    parser.add_argument(
        "instrument_type",
        nargs="?",
        default="STK",
        help="Instrument type (STK, FUT, OPT, etc.)",
    )

    args = parser.parse_args()

    success = asyncio.run(unsubscribe_from_symbol(args.symbol.upper()))

    if success:
        print(f"\n🎉 Successfully unsubscribed from {args.symbol.upper()}")
    else:
        print(f"\n💥 Failed to unsubscribe from {args.symbol.upper()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
