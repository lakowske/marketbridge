#!/usr/bin/env python3
"""
Clean up all browser sessions

Uses browser-bunny client to clean up all browser sessions.
"""

import asyncio
import sys
from browser_bunny.client import BrowserClient


async def cleanup_all_sessions():
    """Delete all existing browser sessions."""
    async with BrowserClient("http://localhost:9247") as client:
        try:
            # Get all sessions
            sessions = await client.list_sessions()
            print(f"🔍 Found {len(sessions)} sessions")

            if not sessions:
                print("✅ No sessions to clean up")
                return

            # Show session details
            for session in sessions:
                session_id = session["session_id"]
                session_name = session["session_name"]
                created_at = session.get("created_at", "unknown")
                active = session.get("active", False)
                url = session.get("current_url", "N/A")

                print(f"📋 Session: {session_name}")
                print(f"   ID: {session_id[:12]}...")
                print(f"   Created: {created_at}")
                print(f"   Active: {active}")
                print(f"   URL: {url}")

            print(f"\n🗑️  Deleting {len(sessions)} sessions...")

            # Delete each session
            deleted_count = 0
            for session in sessions:
                session_id = session["session_id"]
                session_name = session["session_name"]
                try:
                    await client.delete_session(session_id)
                    print(f"✅ Deleted: {session_name}")
                    deleted_count += 1
                except Exception as e:
                    print(f"❌ Failed to delete {session_name}: {e}")

            print(
                f"\n🎉 Cleanup complete! Deleted {deleted_count}/{len(sessions)} sessions"
            )

            # Also trigger server-side cleanup for old sessions
            print(f"\n🧹 Running server-side cleanup for old sessions...")
            try:
                cleanup_result = await client.cleanup_sessions(max_age_hours=24)
                additional_deleted = cleanup_result.get("cleanup_count", 0)
                if additional_deleted > 0:
                    print(
                        f"✅ Server cleanup deleted {additional_deleted} additional old sessions"
                    )
                else:
                    print("✅ No additional old sessions found")
            except Exception as e:
                print(f"⚠️  Server-side cleanup failed: {e}")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            raise


async def cleanup_old_sessions_only(max_age_hours=24):
    """Clean up only old sessions, keeping recent ones."""
    async with BrowserClient("http://localhost:9247") as client:
        try:
            print(f"🧹 Cleaning up sessions older than {max_age_hours} hours...")

            cleanup_result = await client.cleanup_sessions(max_age_hours=max_age_hours)
            deleted_sessions = cleanup_result.get("deleted_sessions", [])
            cleanup_count = cleanup_result.get("cleanup_count", 0)

            if cleanup_count > 0:
                print(f"✅ Deleted {cleanup_count} old sessions:")
                for session_id in deleted_sessions:
                    print(f"   - {session_id[:12]}...")
            else:
                print("✅ No old sessions found to clean up")

        except Exception as e:
            print(f"❌ Error during old session cleanup: {e}")
            raise


if __name__ == "__main__":
    print("MarketBridge Browser Session Cleanup (using browser-bunny)")
    print("=" * 60)

    # Check if user wants to clean up only old sessions
    if len(sys.argv) > 1 and sys.argv[1] == "--old-only":
        hours = 24
        if len(sys.argv) > 2:
            try:
                hours = int(sys.argv[2])
            except ValueError:
                print("Invalid hours specified, using default of 24 hours")

        print(f"Mode: Clean up sessions older than {hours} hours only")
        print("=" * 60)
        asyncio.run(cleanup_old_sessions_only(hours))
    else:
        print("Mode: Clean up ALL sessions")
        print("Use --old-only [hours] to clean up only old sessions")
        print("=" * 60)
        asyncio.run(cleanup_all_sessions())
