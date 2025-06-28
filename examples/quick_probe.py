#!/usr/bin/env python3
"""Quick Session Probe - Non-blocking session interaction"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

from marketbridge.browser_client import BrowserClient


async def quick_probe(action="status"):
    """Quick probe of existing session."""
    async with BrowserClient() as client:
        sessions = await client.list_sessions()
        if not sessions:
            print("❌ No active sessions")
            return

        session_id = sessions[0]["session_id"]

        if action == "status":
            script = """
            (() => {
                const inputs = Array.from(document.querySelectorAll('input'));
                const symbolInput = inputs.find(i => i.value.includes('AAPL') || i.placeholder?.toLowerCase().includes('symbol'));
                return {
                    url: window.location.href,
                    title: document.title,
                    symbolValue: symbolInput?.value || 'not found',
                    inputCount: inputs.length
                };
            })()
            """
        elif action.startswith("fill:"):
            symbol = action.split(":")[1]
            script = f"""
            (() => {{
                const input = document.querySelector('input[type="text"]');
                if (input) {{
                    input.value = '{symbol}';
                    input.dispatchEvent(new Event('input', {{bubbles: true}}));
                    return {{success: true, value: input.value}};
                }}
                return {{success: false}};
            }})()
            """

        result = await client._post(
            f"/sessions/{session_id}/execute", {"script": script, "args": []}
        )
        return result.get("result")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    result = asyncio.run(quick_probe(action))
    print(f"🔍 {result}")
