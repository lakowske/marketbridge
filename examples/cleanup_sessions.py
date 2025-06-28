#!/usr/bin/env python3
"""Clean up all browser sessions"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

from marketbridge.browser_client import BrowserClient


async def cleanup_all_sessions():
    """Delete all existing browser sessions."""
    async with BrowserClient() as client:
        sessions = await client.list_sessions()
        print(f"🔍 Found {len(sessions)} sessions")

        for session in sessions:
            session_id = session["session_id"]
            session_name = session["session_name"]
            print(f"🗑️  Deleting session: {session_name} ({session_id})")
            await client.delete_session(session_id)

        print("✅ All sessions cleaned up")


if __name__ == "__main__":
    asyncio.run(cleanup_all_sessions())
