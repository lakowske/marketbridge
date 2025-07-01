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
            response = await client.get("/sessions")
            sessions = response.get("sessions", [])
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
                    await client.delete(f"/sessions/{session_id}")
                    print(f"✅ Deleted: {session_name}")
                    deleted_count += 1
                except Exception as e:
                    print(f"❌ Failed to delete {session_name}: {e}")

            print(
                f"\n🎉 Cleanup complete! Deleted {deleted_count}/{len(sessions)} sessions"
            )

            # Server-side cleanup is automatic, no need to trigger manually
            print(f"\n✅ Cleanup complete!")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            raise


async def cleanup_old_sessions_only(max_age_hours=24):
    """Clean up only old sessions, keeping recent ones."""
    async with BrowserClient("http://localhost:9247") as client:
        try:
            from datetime import datetime, timedelta

            print(f"🧹 Cleaning up sessions older than {max_age_hours} hours...")

            # Get all sessions
            response = await client.get("/sessions")
            sessions = response.get("sessions", [])

            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            old_sessions = []

            for session in sessions:
                created_at = session.get("created_at", "")
                # Parse the ISO timestamp
                try:
                    session_time = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                    if session_time.replace(tzinfo=None) < cutoff_time:
                        old_sessions.append(session)
                except ValueError:
                    pass

            if old_sessions:
                print(f"✅ Found {len(old_sessions)} old sessions to delete")
                for session in old_sessions:
                    session_id = session["session_id"]
                    session_name = session["session_name"]
                    try:
                        await client.delete(f"/sessions/{session_id}")
                        print(f"   ✅ Deleted: {session_name} ({session_id[:12]}...)")
                    except Exception as e:
                        print(f"   ❌ Failed to delete {session_name}: {e}")
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
