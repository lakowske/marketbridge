#!/usr/bin/env python3
"""General subscribe to market data script"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

from marketbridge.browser_client import BrowserClient


async def subscribe_to_symbol(symbol: str, instrument_type: str):
    """Subscribe to market data for a given symbol and instrument type."""
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

    async with BrowserClient() as client:
        sessions = await client.list_sessions()
        if not sessions:
            print("❌ No active sessions")
            return False

        session_id = sessions[0]["session_id"]

        print(f"📈 Subscribing to {symbol} ({instrument_type.upper()})...")

        # Fill the form and subscribe
        script = f"""
        (() => {{
            // Fill symbol field
            const symbolInput = document.querySelector('#symbol');
            if (symbolInput) {{
                symbolInput.value = '{symbol}';
                symbolInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                symbolInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }} else {{
                return {{success: false, message: 'Symbol input field not found'}};
            }}

            // Select instrument type
            const instrumentSelect = document.querySelector('#instrument-type');
            if (instrumentSelect) {{
                instrumentSelect.value = '{ui_instrument_type}';
                instrumentSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }} else {{
                return {{success: false, message: 'Instrument type selector not found'}};
            }}

            // Find and click Subscribe button
            const subscribeBtn = document.querySelector('#subscribe-btn');
            if (subscribeBtn) {{
                subscribeBtn.click();
                return {{success: true, message: 'Form filled and subscribe clicked'}};
            }} else {{
                return {{success: false, message: 'Subscribe button not found'}};
            }}
        }})()
        """

        result = await client._post(
            f"/sessions/{session_id}/execute", {"script": script, "args": []}
        )
        response = result.get("result", {})

        if not response.get("success"):
            print(f"❌ {response.get('message')}")
            return False

        # Wait and verify subscription
        await asyncio.sleep(3)

        # Check if subscription was successful
        check_script = f"""
        (() => {{
            // Look for the symbol in subscriptions list
            const subscriptionsList = document.querySelector('.subscriptions, .active-subscriptions');
            const marketDataTable = document.querySelector('table');

            let foundInSubscriptions = false;
            let foundInTable = false;
            let subscriptionCount = 0;

            if (subscriptionsList) {{
                const text = subscriptionsList.textContent;
                foundInSubscriptions = text.includes('{symbol}');
                // Count subscription items
                const items = Array.from(subscriptionsList.querySelectorAll('li, div')).filter(el =>
                    el.textContent.trim() && el.textContent.includes('•')
                );
                subscriptionCount = items.length;
            }}

            if (marketDataTable) {{
                const rows = Array.from(marketDataTable.querySelectorAll('tr'));
                foundInTable = rows.some(row => row.textContent.includes('{symbol}'));
            }}

            return {{
                foundInSubscriptions: foundInSubscriptions,
                foundInTable: foundInTable,
                subscriptionCount: subscriptionCount,
                timestamp: new Date().toISOString()
            }};
        }})()
        """

        check_result = await client._post(
            f"/sessions/{session_id}/execute", {"script": check_script, "args": []}
        )
        check_data = check_result.get("result", {})

        print("\n📊 Subscription Status:")
        print("=" * 30)

        if check_data.get("foundInSubscriptions"):
            print(f"✅ {symbol} added to subscriptions list")
        else:
            print(f"❌ {symbol} not found in subscriptions list")

        if check_data.get("foundInTable"):
            print(f"✅ {symbol} appears in market data table")
        else:
            print(f"❌ {symbol} not found in market data table")

        print(f"📋 Total active subscriptions: {check_data.get('subscriptionCount', 0)}")
        print(f"⏰ Checked at: {check_data.get('timestamp')}")

        success = check_data.get("foundInSubscriptions") or check_data.get(
            "foundInTable"
        )
        return success


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
