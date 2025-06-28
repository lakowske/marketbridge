#!/usr/bin/env python3
"""
Persistent Browser Session

Opens a browser window that stays open for manual interaction.
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

from marketbridge.browser_client import BrowserClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)


async def create_persistent_session():
    """Create a persistent browser session that stays open."""
    logger.info("Creating persistent browser session")

    async with BrowserClient() as client:
        try:
            # Create a new session (non-headless = visible browser)
            session = await client.create_session(
                session_name="persistent_marketbridge",
                headless=False,
                viewport={"width": 1920, "height": 1080},
            )

            logger.info(f"Created session - session_id: {session.session_id}")
            logger.info(f"Session name: {session.session_name}")

            # Navigate to MarketBridge
            await session.navigate("http://localhost:8080")
            logger.info("Navigated to MarketBridge")

            # Wait for the page to load
            await asyncio.sleep(3)

            print(f"\n🌐 Browser session created successfully!")
            print(f"📋 Session ID: {session.session_id}")
            print(f"🏷️  Session Name: {session.session_name}")
            print(f"🔗 URL: http://localhost:8080")
            print(
                f"\nThe browser window should now be visible and showing MarketBridge."
            )
            print(
                f"You can interact with it manually, or use other scripts to automate it."
            )
            print(f"\nTo close this session later, run:")
            print(
                f"python -c \"import asyncio; from src.marketbridge.browser_client import BrowserClient; asyncio.run(BrowserClient().delete_session('{session.session_id}'))\""
            )

            # Keep the session alive for 10 minutes
            print(f"\nKeeping session alive for 10 minutes...")
            print(f"Press Ctrl+C to stop early.")

            for i in range(600):  # 10 minutes = 600 seconds
                await asyncio.sleep(1)
                if i % 60 == 0:  # Every minute
                    minutes_left = (600 - i) // 60
                    print(f"⏱️  {minutes_left} minutes remaining...")

            print(
                "\n⏰ 10 minutes elapsed. Session will remain active until manually closed."
            )

        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user. Session will remain active.")
            logger.info("Session interrupted by user")
        except Exception as e:
            logger.error(f"Error creating persistent session: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    print("MarketBridge Persistent Browser Session")
    print("=" * 40)

    try:
        asyncio.run(create_persistent_session())
    except KeyboardInterrupt:
        print("\nSession creation cancelled by user")
    except Exception as e:
        print(f"\nSession creation failed: {e}")
        sys.exit(1)
