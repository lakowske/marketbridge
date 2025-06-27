#!/usr/bin/env python3
"""
MarketBridge Server Runner
Simple script to run the combined server with default settings.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from marketbridge.combined_server import main

if __name__ == "__main__":
    print("Starting MarketBridge Combined Server...")
    print("Press Ctrl+C to stop")
    print("-" * 50)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)
