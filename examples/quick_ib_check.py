#!/usr/bin/env python3
"""Quick IB status check - no blocking"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

from marketbridge.browser_client import BrowserClient


async def quick_ib_check():
    """Quick check of IB status - no blocking."""
    async with BrowserClient() as client:
        sessions = await client.list_sessions()
        if not sessions:
            # Create new session
            session = await client.create_session("ib_test", headless=False)
            await session.navigate("http://localhost:8080")
            await asyncio.sleep(2)  # Brief wait for page load
            session_id = session.session_id
        else:
            session_id = sessions[0]["session_id"]

        # Check status
        script = """
        (() => {
            return {
                wsStatus: document.getElementById('ws-status-text')?.textContent,
                ibStatus: document.getElementById('ib-status-text')?.textContent,
                wsClass: document.getElementById('ws-status-indicator')?.className,
                ibClass: document.getElementById('ib-status-indicator')?.className
            };
        })()
        """

        result = await client._post(
            f"/sessions/{session_id}/execute", {"script": script, "args": []}
        )
        status = result.get("result", {})

        print("🔌 Connection Status:")
        print(f"  WS: {status.get('wsStatus')} [{status.get('wsClass')}]")
        print(f"  IB: {status.get('ibStatus')} [{status.get('ibClass')}]")


if __name__ == "__main__":
    asyncio.run(quick_ib_check())
