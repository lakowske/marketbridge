#!/usr/bin/env python3
"""Subscribe to futures with proper contract specification"""

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


async def subscribe_to_futures(symbol: str, exchange: str = "CME", expiry: str = ""):
    """Subscribe to futures with proper contract specification."""

    # Common futures exchanges and symbols
    futures_info = {
        "MNQ": {"exchange": "CME", "description": "Micro E-mini Nasdaq-100"},
        "MES": {"exchange": "CME", "description": "Micro E-mini S&P 500"},
        "ES": {"exchange": "CME", "description": "E-mini S&P 500"},
        "NQ": {"exchange": "CME", "description": "E-mini Nasdaq-100"},
        "CL": {"exchange": "NYMEX", "description": "Crude Oil"},
        "GC": {"exchange": "COMEX", "description": "Gold"},
        "SI": {"exchange": "COMEX", "description": "Silver"},
    }

    symbol_upper = symbol.upper()
    if symbol_upper in futures_info:
        default_exchange = futures_info[symbol_upper]["exchange"]
        description = futures_info[symbol_upper]["description"]
        print(
            f"📈 Subscribing to {symbol_upper} ({description}) on {exchange or default_exchange}"
        )
    else:
        print(f"📈 Subscribing to {symbol_upper} futures on {exchange}")

    async with BrowserClient() as client:
        sessions = await client.list_sessions()
        if not sessions:
            print("❌ No active sessions")
            return False

        session_id = sessions[0]["session_id"]

        # Create a more specific symbol for futures
        # For most US futures, we can try the front month or continuous contract
        futures_symbols_to_try = [
            symbol_upper,  # Try base symbol first
            f"{symbol_upper}M25",  # June 2025
            f"{symbol_upper}H25",  # March 2025
            f"{symbol_upper}Z24",  # December 2024
            f"{symbol_upper}1!",  # Continuous contract (some platforms)
        ]

        if expiry:
            futures_symbols_to_try.insert(0, f"{symbol_upper}{expiry}")

        success = False
        for try_symbol in futures_symbols_to_try:
            print(f"  Trying symbol: {try_symbol}")

            # Fill the form and subscribe
            script = f"""
            (() => {{
                // Fill symbol field
                const symbolInput = document.querySelector('#symbol');
                if (symbolInput) {{
                    symbolInput.value = '{try_symbol}';
                    symbolInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    symbolInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }} else {{
                    return {{success: false, message: 'Symbol input field not found'}};
                }}

                // Select future instrument type
                const instrumentSelect = document.querySelector('#instrument-type');
                if (instrumentSelect) {{
                    instrumentSelect.value = 'future';
                    instrumentSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }} else {{
                    return {{success: false, message: 'Instrument type selector not found'}};
                }}

                // Click Subscribe button
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
                print(f"    ❌ Form error: {response.get('message')}")
                continue

            # Wait for subscription to process
            await asyncio.sleep(4)

            # Check if subscription was successful
            check_script = f"""
            (() => {{
                const subscriptionsList = document.querySelector('.subscriptions, .active-subscriptions');
                const marketDataTable = document.querySelector('table');

                let foundInSubscriptions = false;
                let foundInTable = false;
                let subscriptionCount = 0;
                let hasError = false;

                // Look for the symbol in subscriptions
                if (subscriptionsList) {{
                    const text = subscriptionsList.textContent;
                    foundInSubscriptions = text.includes('{try_symbol}') || text.includes('{symbol_upper}');
                    const items = Array.from(subscriptionsList.querySelectorAll('li, div')).filter(el =>
                        el.textContent.trim() && el.textContent.includes('•')
                    );
                    subscriptionCount = items.length;
                }}

                // Look for symbol in market data table
                if (marketDataTable) {{
                    const rows = Array.from(marketDataTable.querySelectorAll('tr'));
                    foundInTable = rows.some(row =>
                        row.textContent.includes('{try_symbol}') || row.textContent.includes('{symbol_upper}')
                    );
                }}

                // Check for error messages
                const errorElements = Array.from(document.querySelectorAll('.error, .alert-danger, [class*="error"]'));
                const errors = errorElements.map(el => el.textContent?.trim()).filter(text =>
                    text && (text.includes('No security definition') || text.includes('not found') || text.includes('invalid'))
                );
                hasError = errors.length > 0;

                return {{
                    foundInSubscriptions: foundInSubscriptions,
                    foundInTable: foundInTable,
                    subscriptionCount: subscriptionCount,
                    hasError: hasError,
                    errors: errors,
                    timestamp: new Date().toISOString()
                }};
            }})()
            """

            check_result = await client._post(
                f"/sessions/{session_id}/execute", {"script": check_script, "args": []}
            )
            check_data = check_result.get("result", {})

            if check_data.get("hasError"):
                print(f"    ❌ IB Error for {try_symbol}")
                for error in check_data.get("errors", []):
                    print(f"        {error}")
                continue

            if check_data.get("foundInSubscriptions") or check_data.get("foundInTable"):
                print(f"    ✅ Success with {try_symbol}!")
                print(
                    f"       In subscriptions: {check_data.get('foundInSubscriptions')}"
                )
                print(f"       In data table: {check_data.get('foundInTable')}")
                print(
                    f"       Total subscriptions: {check_data.get('subscriptionCount', 0)}"
                )
                success = True
                break
            else:
                print(f"    ❌ No subscription found for {try_symbol}")

        if not success:
            print(
                f"\n💥 Failed to subscribe to {symbol_upper} with any contract specification"
            )
            print("\n💡 Suggestions:")
            print("   1. Check if the symbol is correct")
            print(
                "   2. Ensure IB TWS/Gateway has market data permissions for this contract"
            )
            print(
                "   3. Try specifying an expiry month: python subscribe_futures.py MNQ --expiry H25"
            )
            print(
                "   4. Check that the futures exchange is available in your market data subscriptions"
            )

        return success


def main():
    parser = argparse.ArgumentParser(description="Subscribe to futures contracts")
    parser.add_argument("symbol", help="Futures symbol (e.g., MNQ, ES, CL)")
    parser.add_argument(
        "--exchange", help="Exchange (default: auto-detect)", default=""
    )
    parser.add_argument(
        "--expiry", help="Expiry month code (e.g., H25 for March 2025)", default=""
    )

    args = parser.parse_args()

    success = asyncio.run(subscribe_to_futures(args.symbol, args.exchange, args.expiry))

    if success:
        print(f"\n🎉 Successfully subscribed to {args.symbol.upper()} futures")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
