#!/usr/bin/env python3
"""Check for AAPL market data"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

from marketbridge.browser_client import BrowserClient


async def check_market_data():
    """Check for market data in the browser."""
    async with BrowserClient() as client:
        sessions = await client.list_sessions()
        if not sessions:
            print("❌ No active sessions")
            return

        session_id = sessions[0]["session_id"]

        script = """
        (() => {
            // Look for market data sections
            const marketDataTable = document.querySelector('table');
            const subscriptionsList = document.querySelector('.subscriptions, .active-subscriptions');

            // Get table data if exists
            let tableData = [];
            if (marketDataTable) {
                const rows = Array.from(marketDataTable.querySelectorAll('tr'));
                tableData = rows.map(row => {
                    const cells = Array.from(row.querySelectorAll('td, th'));
                    return cells.map(cell => cell.textContent?.trim()).filter(text => text);
                });
            }

            // Get subscription info
            let subscriptions = [];
            if (subscriptionsList) {
                const items = Array.from(subscriptionsList.querySelectorAll('li, div, span'));
                subscriptions = items.map(item => item.textContent?.trim()).filter(text => text);
            }

            // Get recent log messages
            const logEntries = Array.from(document.querySelectorAll('.log-entry')).slice(-10);
            const recentMessages = logEntries.map(entry => {
                const time = entry.querySelector('.timestamp')?.textContent;
                const level = entry.querySelector('.level')?.textContent;
                const message = entry.querySelector('.message')?.textContent;
                return `[${time}] ${level}: ${message}`;
            }).filter(msg => msg);

            return {
                hasMarketDataTable: !!marketDataTable,
                tableData: tableData.slice(0, 10), // Limit to first 10 rows
                hasSubscriptionsList: !!subscriptionsList,
                subscriptions: subscriptions.slice(0, 10),
                recentMessages: recentMessages,
                timestamp: new Date().toISOString()
            };
        })()
        """

        result = await client._post(
            f"/sessions/{session_id}/execute", {"script": script, "args": []}
        )
        data = result.get("result", {})

        print("📊 Market Data Status:")
        print("=" * 30)

        if data.get("hasMarketDataTable"):
            print("✅ Market Data Table: Found")
            table_data = data.get("tableData", [])
            if table_data:
                print("\n📈 Market Data:")
                for i, row in enumerate(table_data[:5]):  # Show first 5 rows
                    if row:  # Skip empty rows
                        print(f"  {i+1}. {' | '.join(row)}")
            else:
                print("   (Table exists but no data rows found)")
        else:
            print("❌ Market Data Table: Not found")

        if data.get("hasSubscriptionsList"):
            print("\n✅ Subscriptions List: Found")
            subs = data.get("subscriptions", [])
            if subs:
                print("📋 Active Subscriptions:")
                for sub in subs[:5]:  # Show first 5
                    if sub:
                        print(f"  • {sub}")
            else:
                print("   (List exists but no subscriptions shown)")
        else:
            print("\n❌ Subscriptions List: Not found")

        messages = data.get("recentMessages", [])
        if messages:
            print("\n📝 Recent Messages:")
            for msg in messages[-5:]:  # Show last 5 messages
                if msg and "undefined" not in msg:
                    print(f"  {msg}")

        print(f"\n⏰ Checked at: {data.get('timestamp')}")


if __name__ == "__main__":
    asyncio.run(check_market_data())
