#!/usr/bin/env python3
"""
Playwright Session Management CLI

Command-line interface for managing persistent Playwright browser sessions.
Provides easy access to create, list, delete, and manage browser sessions
for MarketBridge automation.
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from marketbridge_playwright.browser_manager import BrowserManager
    from marketbridge_playwright.session_manager import SessionManager
except ImportError as e:
    print(f"Error importing Playwright modules: {e}")
    print("Make sure you're running from the project root and Playwright is installed.")
    sys.exit(1)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def list_sessions(args):
    """List all available sessions."""
    session_manager = SessionManager()
    sessions = session_manager.list_sessions()

    if not sessions:
        print("No sessions found.")
        return

    print(f"Found {len(sessions)} session(s):\n")

    for session in sessions:
        print(f"Name: {session['name']}")
        print(f"Description: {session.get('description', 'No description')}")
        print(f"Created: {session['created_at']}")
        print(f"Last Used: {session['last_used']}")
        print(f"Session Dir: {session['session_dir']}")
        print("-" * 50)


def create_session(args):
    """Create a new session."""
    session_manager = SessionManager()

    try:
        session = session_manager.create_session(args.name, args.description or "")
        print(f"Created session '{args.name}' successfully.")
        print(f"Session directory: {session['session_dir']}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def delete_session(args):
    """Delete a session."""
    session_manager = SessionManager()

    if not args.force:
        response = input(
            f"Are you sure you want to delete session '{args.name}'? (y/N): "
        )
        if response.lower() != "y":
            print("Cancelled.")
            return

    try:
        session_manager.delete_session(args.name)
        print(f"Deleted session '{args.name}' successfully.")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


async def start_browser_session(args):
    """Start a browser session."""
    session_manager = SessionManager()
    browser_manager = BrowserManager(session_manager)

    try:
        # Start browser
        await browser_manager.start(browser_type=args.browser, headless=args.headless)

        # Create or load session context
        context = await browser_manager.create_session_context(args.name)

        if args.url:
            # Navigate to specified URL
            page = await browser_manager.new_page(args.name)
            await page.goto(args.url)
            print(f"Navigated to: {args.url}")
        elif args.marketbridge:
            # Navigate to MarketBridge
            page = await browser_manager.navigate_to_marketbridge(
                args.name, args.marketbridge_url
            )
            print(f"Navigated to MarketBridge at: {args.marketbridge_url}")

        print(f"Browser session '{args.name}' started successfully.")
        print("The browser will remain open. Close it manually or use Ctrl+C to stop.")

        # Keep the session alive
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down browser session...")

    except Exception as e:
        print(f"Error starting browser session: {e}")
        sys.exit(1)
    finally:
        await browser_manager.stop()


def cleanup_sessions(args):
    """Clean up old sessions."""
    session_manager = SessionManager()

    deleted = session_manager.cleanup_old_sessions(args.days)

    if deleted:
        print(f"Cleaned up {len(deleted)} old sessions:")
        for session_name in deleted:
            print(f"  - {session_name}")
    else:
        print("No old sessions to clean up.")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Manage Playwright browser sessions for MarketBridge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all sessions
  python scripts/playwright_session.py list

  # Create a new session
  python scripts/playwright_session.py create my_session -d "My test session"

  # Start a browser session
  python scripts/playwright_session.py start my_session

  # Start browser and navigate to MarketBridge
  python scripts/playwright_session.py start my_session --marketbridge

  # Delete a session
  python scripts/playwright_session.py delete my_session

  # Clean up sessions older than 7 days
  python scripts/playwright_session.py cleanup --days 7
        """,
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List all sessions")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new session")
    create_parser.add_argument("name", help="Session name")
    create_parser.add_argument("-d", "--description", help="Session description")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a session")
    delete_parser.add_argument("name", help="Session name to delete")
    delete_parser.add_argument(
        "-f", "--force", action="store_true", help="Force delete without confirmation"
    )

    # Start command
    start_parser = subparsers.add_parser("start", help="Start a browser session")
    start_parser.add_argument("name", help="Session name")
    start_parser.add_argument(
        "--browser",
        default="chromium",
        choices=["chromium", "firefox", "webkit"],
        help="Browser type",
    )
    start_parser.add_argument(
        "--headless", action="store_true", help="Run in headless mode"
    )
    start_parser.add_argument("--url", help="URL to navigate to")
    start_parser.add_argument(
        "--marketbridge", action="store_true", help="Navigate to MarketBridge"
    )
    start_parser.add_argument(
        "--marketbridge-url", default="http://localhost:8080", help="MarketBridge URL"
    )

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old sessions")
    cleanup_parser.add_argument(
        "--days", type=int, default=30, help="Maximum age in days (default: 30)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    setup_logging(args.verbose)

    # Route to appropriate handler
    if args.command == "list":
        list_sessions(args)
    elif args.command == "create":
        create_session(args)
    elif args.command == "delete":
        delete_session(args)
    elif args.command == "start":
        asyncio.run(start_browser_session(args))
    elif args.command == "cleanup":
        cleanup_sessions(args)


if __name__ == "__main__":
    main()
