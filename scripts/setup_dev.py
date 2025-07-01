#!/usr/bin/env python3
"""
Development setup script for MarketBridge

This script handles environment-specific dependencies like browser-bunny.
"""

import subprocess
import sys
from pathlib import Path


def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent.parent / ".env"
    env_vars = {}

    if env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()

    return env_vars


def install_browser_bunny(browser_bunny_path):
    """Install browser-bunny from the specified path"""
    if not Path(browser_bunny_path).exists():
        print(f"❌ Browser-bunny path does not exist: {browser_bunny_path}")
        print("Please update the BROWSER_BUNNY_PATH in your .env file")
        return False

    print(f"📦 Installing browser-bunny from: {browser_bunny_path}")

    try:
        # Install browser-bunny as editable
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", browser_bunny_path],
            check=True,
            capture_output=True,
            text=True,
        )

        print("✅ Browser-bunny installed successfully")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install browser-bunny: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False


def main():
    """Main setup function"""
    print("🚀 Setting up MarketBridge development environment...")

    # Check if .env file exists
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        print("❌ .env file not found!")
        print("Please copy .env.example to .env and configure your paths:")
        print("  cp .env.example .env")
        print("  # Edit .env to set BROWSER_BUNNY_PATH")
        return 1

    # Load environment variables
    env_vars = load_env_file()
    browser_bunny_path = env_vars.get("BROWSER_BUNNY_PATH")

    if not browser_bunny_path:
        print("❌ BROWSER_BUNNY_PATH not set in .env file")
        print("Please add BROWSER_BUNNY_PATH to your .env file")
        return 1

    # Install main dependencies first
    print("📦 Installing main dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=True)
        print("✅ Main dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install main dependencies: {e}")
        return 1

    # Install browser-bunny
    if not install_browser_bunny(browser_bunny_path):
        return 1

    print("\n🎉 Development environment setup complete!")
    print("\nNext steps:")
    print("  1. Start MarketBridge: python scripts/manage_server.py start")
    print("  2. Start browser-bunny: browser-bunny start")
    print("  3. Open browser: http://localhost:8080")

    return 0


if __name__ == "__main__":
    sys.exit(main())
