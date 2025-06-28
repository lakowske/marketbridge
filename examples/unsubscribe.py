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

from marketbridge.browser_client import BrowserClient


async def unsubscribe_from_symbol(symbol: str):
    """Unsubscribe from market data for a given symbol."""
    async with BrowserClient() as client:
        sessions = await client.list_sessions()
        if not sessions:
            print("❌ No active sessions")
            return False

        session_id = sessions[0]["session_id"]

        print(f"📉 Unsubscribing from {symbol}...")

        # Look for and click Unsubscribe button for the specified symbol
        script = f"""
        (() => {{
            // Find all unsubscribe buttons
            const unsubscribeButtons = Array.from(document.querySelectorAll('button')).filter(btn =>
                btn.textContent.toLowerCase().includes('unsubscribe')
            );

            // Try to find the specific unsubscribe button for this symbol
            for (const btn of unsubscribeButtons) {{
                // Check if this button is associated with the symbol by looking at nearby text
                const parent = btn.closest('div, li, tr, td');
                if (parent && parent.textContent.includes('{symbol}')) {{
                    btn.click();
                    return {{success: true, message: 'Clicked Unsubscribe for {symbol}', method: 'symbol-specific'}};
                }}
            }}

            // Alternative: look in table rows for the symbol and find unsubscribe button
            const tableRows = Array.from(document.querySelectorAll('tr'));
            for (const row of tableRows) {{
                if (row.textContent.includes('{symbol}')) {{
                    const unsubBtn = row.querySelector('button:contains("Unsubscribe"), button[onclick*="unsubscribe"]') ||
                                   Array.from(row.querySelectorAll('button')).find(btn =>
                                       btn.textContent.toLowerCase().includes('unsubscribe')
                                   );
                    if (unsubBtn) {{
                        unsubBtn.click();
                        return {{success: true, message: 'Clicked Unsubscribe for {symbol} in table', method: 'table-row'}};
                    }}
                }}
            }}

            // List available subscriptions and unsubscribe buttons for debugging
            const subscriptions = [];
            const subscriptionsList = document.querySelector('.subscriptions, .active-subscriptions');
            if (subscriptionsList) {{
                const items = Array.from(subscriptionsList.querySelectorAll('li, div')).filter(el =>
                    el.textContent.trim() && (el.textContent.includes('•') || el.textContent.includes('Unsubscribe'))
                );
                subscriptions.push(...items.map(el => el.textContent.trim()));
            }}

            return {{
                success: false,
                message: 'No Unsubscribe button found for {symbol}',
                availableSubscriptions: subscriptions,
                unsubscribeButtonCount: unsubscribeButtons.length
            }};
        }})()
        """

        result = await client._post(
            f"/sessions/{session_id}/execute", {"script": script, "args": []}
        )
        response = result.get("result", {})

        if response.get("success"):
            print(
                f"✅ {response.get('message')} (method: {response.get('method', 'unknown')})"
            )
        else:
            print(f"❌ {response.get('message')}")
            if response.get("availableSubscriptions"):
                print("\n📋 Available subscriptions:")
                for sub in response.get("availableSubscriptions", [])[:10]:
                    if sub:
                        print(f"  • {sub}")
            print(
                f"\n🔘 Found {response.get('unsubscribeButtonCount', 0)} unsubscribe buttons"
            )
            return False

        # Wait and verify unsubscription
        await asyncio.sleep(2)

        # Check if unsubscription was successful
        check_script = f"""
        (() => {{
            const subscriptionsList = document.querySelector('.subscriptions, .active-subscriptions');
            const marketDataTable = document.querySelector('table');

            let stillInSubscriptions = false;
            let stillInTable = false;
            let subscriptionCount = 0;

            if (subscriptionsList) {{
                const text = subscriptionsList.textContent;
                stillInSubscriptions = text.includes('{symbol}');
                // Count remaining subscription items
                const items = Array.from(subscriptionsList.querySelectorAll('li, div')).filter(el =>
                    el.textContent.trim() && el.textContent.includes('•')
                );
                subscriptionCount = items.length;
            }}

            if (marketDataTable) {{
                const rows = Array.from(marketDataTable.querySelectorAll('tr'));
                stillInTable = rows.some(row => row.textContent.includes('{symbol}'));
            }}

            return {{
                stillInSubscriptions: stillInSubscriptions,
                stillInTable: stillInTable,
                subscriptionCount: subscriptionCount,
                timestamp: new Date().toISOString()
            }};
        }})()
        """

        check_result = await client._post(
            f"/sessions/{session_id}/execute", {"script": check_script, "args": []}
        )
        check_data = check_result.get("result", {})

        print("\n📊 Unsubscription Status:")
        print("=" * 30)

        if not check_data.get("stillInSubscriptions"):
            print(f"✅ {symbol} removed from subscriptions list")
        else:
            print(f"❌ {symbol} still in subscriptions list")

        if not check_data.get("stillInTable"):
            print(f"✅ {symbol} removed from market data table")
        else:
            print(f"❌ {symbol} still in market data table")

        print(
            f"📋 Remaining active subscriptions: {check_data.get('subscriptionCount', 0)}"
        )
        print(f"⏰ Checked at: {check_data.get('timestamp')}")

        success = not check_data.get("stillInSubscriptions") and not check_data.get(
            "stillInTable"
        )
        return success


def main():
    parser = argparse.ArgumentParser(description="Unsubscribe from market data")
    parser.add_argument("symbol", help="Symbol to unsubscribe from (e.g., AAPL, MNQ)")

    args = parser.parse_args()

    success = asyncio.run(unsubscribe_from_symbol(args.symbol.upper()))

    if success:
        print(f"\n🎉 Successfully unsubscribed from {args.symbol.upper()}")
    else:
        print(f"\n💥 Failed to unsubscribe from {args.symbol.upper()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
