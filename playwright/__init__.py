"""
MarketBridge Playwright Integration

This module provides browser automation capabilities with persistent session management
for testing and interacting with the MarketBridge web interface.

Key features:
- Persistent browser sessions stored to disk
- Session management across script runs
- Browser lifecycle management
- Easy scripting interface for web UI automation
"""

from .browser_manager import BrowserManager
from .session_manager import SessionManager

__all__ = ["BrowserManager", "SessionManager"]
