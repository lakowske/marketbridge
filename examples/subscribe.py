#!/usr/bin/env python3
"""General subscribe to market data script using browser-bunny persistent sessions"""

import argparse
import asyncio
import sys
from browser_bunny.persistent_session_manager import get_persistent_session


async def subscribe_to_symbol(symbol: str, instrument_type: str):
    """Subscribe to market data for a given symbol and instrument type using browser-bunny."""
    # Map IB instrument types to UI values
    instrument_mapping = {
        "STK": "stock",
        "FUT": "future",
        "OPT": "option",
        "CASH": "forex",
        "IND": "index",
        "CFD": "stock",  # CFDs might use stock type
        "BOND": "stock",  # Bonds might use stock type
        "CMDTY": "future",  # Commodities might use future type
    }

    ui_instrument_type = instrument_mapping.get(
        instrument_type.upper(), instrument_type.lower()
    )

    # Use persistent session for MarketBridge
    manager = await get_persistent_session("marketbridge")

    try:
        print(f"📈 Subscribing to {symbol} ({instrument_type.upper()})...")

        # Navigate to MarketBridge (this will reuse existing session if available)
        await manager.navigate_to("http://localhost:8080", wait_until="domcontentloaded")
        print(f"✅ Connected to MarketBridge UI")

        # Take a screenshot before subscription
        await manager.screenshot(f"before_subscribe_{symbol}.png")

        # Fill the symbol input
        print(f"📝 Filling symbol: {symbol}")
        await manager.execute_js(
            f"""
            const symbolInput = document.querySelector('#symbol');
            if (symbolInput) {{
                symbolInput.value = '{symbol}';
                symbolInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                symbolInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                console.log('Symbol input filled with {symbol}');
            }} else {{
                console.log('Symbol input field not found');
            }}
        """
        )
        print(f"✅ Symbol field filled")

        # Select instrument type
        print(f"📝 Setting instrument type: {ui_instrument_type}")
        await manager.execute_js(
            f"""
            const instrumentSelect = document.querySelector('#instrument-type');
            if (instrumentSelect) {{
                instrumentSelect.value = '{ui_instrument_type}';
                instrumentSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
                console.log('Instrument type set to {ui_instrument_type}');
            }} else {{
                console.log('Instrument type selector not found');
            }}
        """
        )
        print(f"✅ Instrument type set")

        # Click subscribe button
        print("📝 Clicking subscribe button...")
        await manager.execute_js(
            """
            const subscribeBtn = document.querySelector('#subscribe-btn');
            if (subscribeBtn) {
                subscribeBtn.click();
                console.log('Subscribe button clicked');
            } else {
                console.log('Subscribe button not found');
            }
        """
        )
        print(f"✅ Subscribe button clicked")

        # Wait for subscription to process
        print("⏳ Waiting for subscription to process...")
        await asyncio.sleep(3)

        # Take screenshot after subscription
        await manager.screenshot(f"after_subscribe_{symbol}.png")

        # Verify subscription was successful
        print("🔍 Checking subscription status...")
        verification_result = await manager.execute_js(
            f"""
            (() => {{
                try {{
                    // Check subscriptions list
                    const subscriptionsList = document.querySelector('#subscriptions-list');
                    const marketDataGrid = document.querySelector('#market-data-grid');

                    let foundInSubscriptions = false;
                    let foundInTable = false;
                    let subscriptionCount = 0;
                    let subscriptionsText = "";
                    let marketDataText = "";

                    if (subscriptionsList) {{
                        subscriptionsText = subscriptionsList.textContent || subscriptionsList.innerHTML || "";
                        foundInSubscriptions = subscriptionsText.includes('{symbol}');
                        // Count subscription items
                        const items = subscriptionsList.querySelectorAll('.subscription-item, li, div');
                        subscriptionCount = Array.from(items).filter(item =>
                            item.textContent && item.textContent.trim().length > 0
                        ).length;
                    }}

                    if (marketDataGrid) {{
                        marketDataText = marketDataGrid.textContent || marketDataGrid.innerHTML || "";
                        foundInTable = marketDataText.includes('{symbol}');
                    }}

                    return {{
                        success: true,
                        foundInSubscriptions: foundInSubscriptions,
                        foundInTable: foundInTable,
                        subscriptionCount: subscriptionCount,
                        subscriptionsText: subscriptionsText.substring(0, 200),
                        marketDataText: marketDataText.substring(0, 200),
                        timestamp: new Date().toISOString(),
                        pageTitle: document.title,
                        url: window.location.href
                    }};
                }} catch (error) {{
                    return {{
                        success: false,
                        error: error.message,
                        pageTitle: document.title,
                        url: window.location.href
                    }};
                }}
            }})()
        """
        )

        # Parse verification result
        print(f"🔍 Raw verification result: {verification_result}")

        if verification_result is None:
            print("⚠️ JavaScript execution returned None")
            check_data = {
                "success": False,
                "error": "JavaScript execution returned None",
            }
        elif isinstance(verification_result, dict):
            # Already parsed as dict
            check_data = verification_result
        elif isinstance(verification_result, str):
            # Try to parse as JSON
            try:
                import json

                check_data = json.loads(verification_result)
            except json.JSONDecodeError as e:
                print(f"⚠️ Could not parse JSON result: {e}")
                check_data = {
                    "success": False,
                    "error": f"JSON parse error: {e}",
                    "raw_result": verification_result,
                }
        else:
            # Handle other types
            check_data = {
                "success": False,
                "error": f"Unexpected result type: {type(verification_result)}",
                "raw_result": str(verification_result),
            }

        # Display results
        print("\n📊 Subscription Status:")
        print("=" * 40)
        print(f"🌐 Page: {check_data.get('pageTitle', 'Unknown')}")

        if check_data.get("foundInSubscriptions"):
            print(f"✅ {symbol} found in subscriptions list")
        else:
            print(f"❌ {symbol} not found in subscriptions list")

        if check_data.get("foundInTable"):
            print(f"✅ {symbol} appears in market data table")
        else:
            print(f"❌ {symbol} not found in market data table")

        print(f"📋 Active subscriptions: {check_data.get('subscriptionCount', 0)}")
        print(f"⏰ Checked at: {check_data.get('timestamp', 'Unknown')}")

        if check_data.get("subscriptionsText"):
            print(
                f"📄 Subscriptions content: {check_data['subscriptionsText'][:100]}..."
            )

        # Determine success
        success = check_data.get("foundInSubscriptions") or check_data.get(
            "foundInTable"
        )

        if success:
            print(f"\n🎉 Successfully subscribed to {symbol}!")
        else:
            print(
                f"\n⚠️ Subscription may not have completed. Check MarketBridge UI manually."
            )

        print(f"\n📷 Screenshots saved:")
        print(f"  - before_subscribe_{symbol}.png")
        print(f"  - after_subscribe_{symbol}.png")
        print(f"\n💻 Session 'marketbridge' remains open for debugging")

        return success

    except Exception as e:
        print(f"❌ Error during subscription: {e}")
        import traceback

        traceback.print_exc()

        # Take error screenshot
        try:
            await manager.screenshot(f"error_subscribe_{symbol}.png")
            print(f"Error screenshot saved: error_subscribe_{symbol}.png")
        except:
            pass

        return False
    finally:
        # Don't cleanup - leave persistent session open for reuse
        await manager.cleanup()


def main():
    parser = argparse.ArgumentParser(description="Subscribe to market data")
    parser.add_argument("symbol", help="Symbol to subscribe to (e.g., AAPL, MNQ)")
    parser.add_argument("instrument_type", help="Instrument type (STK, FUT, OPT, etc.)")

    args = parser.parse_args()

    # Validate instrument type
    valid_types = ["STK", "FUT", "OPT", "CASH", "IND", "CFD", "BOND", "CMDTY"]
    if args.instrument_type.upper() not in valid_types:
        print(f"❌ Invalid instrument type: {args.instrument_type}")
        print(f"Valid types: {', '.join(valid_types)}")
        sys.exit(1)

    # Special handling for futures
    if args.instrument_type.upper() == "FUT":
        print(f"⚠️  Futures require specific contract details.")
        print(
            f"💡 For better futures support, use: python examples/subscribe_futures.py {args.symbol}"
        )
        print(f"   This will try multiple contract specifications automatically.")
        print(f"\nTrying basic futures subscription anyway...")

    success = asyncio.run(
        subscribe_to_symbol(args.symbol.upper(), args.instrument_type.upper())
    )

    if success:
        print(
            f"\n🎉 Successfully subscribed to {args.symbol.upper()} ({args.instrument_type.upper()})"
        )
    else:
        if args.instrument_type.upper() == "FUT":
            print(f"\n💥 Failed to subscribe to {args.symbol.upper()} futures")
            print(f"💡 Try: python examples/subscribe_futures.py {args.symbol}")
            print(f"   This script handles contract specifications automatically.")
        else:
            print(
                f"\n💥 Failed to subscribe to {args.symbol.upper()} ({args.instrument_type.upper()})"
            )
        sys.exit(1)


if __name__ == "__main__":
    main()
