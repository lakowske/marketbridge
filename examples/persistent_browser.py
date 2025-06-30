#!/usr/bin/env python3
"""
Persistent Browser Session

Opens a browser window that stays open for manual interaction.
Uses browser-bunny for persistent browser automation.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

from browser_bunny.persistent_session_manager import get_persistent_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)


async def create_persistent_session():
    """Create a persistent browser session that stays open."""
    logger.info("Creating persistent browser session")

    # Get or create persistent session
    manager = await get_persistent_session("persistent_marketbridge")

    try:
        print(f"\n🌐 Creating browser session: persistent_marketbridge")

        # Navigate to MarketBridge (this auto-creates the session)
        await manager.navigate_to(
            "http://localhost:8080", wait_until="domcontentloaded"
        )
        logger.info("Navigated to MarketBridge")

        # Take a screenshot to confirm it loaded
        await manager.screenshot("persistent_session_start.png")
        logger.info("Screenshot taken: persistent_session_start.png")

        print(f"\n🌐 Browser session created successfully!")
        print(f"🏷️  Session Name: persistent_marketbridge")
        print(f"🔗 URL: http://localhost:8080")
        print(f"📸 Screenshot: screenshots/persistent_session_start.png")
        print(f"\nThe browser window should now be visible and showing MarketBridge.")
        print(
            f"You can interact with it manually, or use other scripts to automate it."
        )

        print(f"\nTo use this session in other scripts:")
        print(
            "  from browser_bunny.persistent_session_manager import get_persistent_session"
        )
        print(f"  manager = await get_persistent_session('persistent_marketbridge')")
        print(f"  # Session will be automatically restored")

        print(f"\nTo cleanup this session later:")
        print("  await manager.cleanup()")

        # Keep the session alive for 10 minutes
        print(f"\nKeeping session alive for 10 minutes...")
        print(f"Press Ctrl+C to stop early and leave session running.")

        for i in range(600):  # 10 minutes = 600 seconds
            await asyncio.sleep(1)
            if i % 60 == 0:  # Every minute
                minutes_left = (600 - i) // 60
                print(f"⏱️  {minutes_left} minutes remaining...")

        print(
            "\n⏰ 10 minutes elapsed. Session will remain active until manually closed."
        )
        print("The session persists and can be reused in other scripts.")

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user. Session will remain active.")
        print("Browser session 'persistent_marketbridge' is still running.")
        print("Use 'await manager.cleanup()' to close it later.")
        logger.info("Session interrupted by user")
    except Exception as e:
        logger.error(f"Error creating persistent session: {e}", exc_info=True)
        # Don't cleanup on error - let user investigate
        raise


if __name__ == "__main__":
    print("MarketBridge Persistent Browser Session (using browser-bunny)")
    print("=" * 60)
    print("\nMake sure browser-bunny server is running:")
    print("  Option 1: browser-bunny start  (if installed globally)")
    print(
        "  Option 2: cd /home/seth/Software/dev/browser-bunny && source .venv/bin/activate && python3 -m browser_bunny.daemon start"
    )
    print("=" * 60)

    try:
        asyncio.run(create_persistent_session())
    except KeyboardInterrupt:
        print("\nSession creation cancelled by user")
    except Exception as e:
        print(f"\nSession creation failed: {e}")
        print("\nMake sure:")
        print("1. Browser-bunny server is running")
        print("2. MarketBridge is running on http://localhost:8080")
        sys.exit(1)
