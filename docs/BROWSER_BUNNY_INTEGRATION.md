# Browser-Bunny Integration Guide

MarketBridge now uses [browser-bunny](../../../browser-bunny/) as its browser automation library instead of maintaining its own playwright implementation. This provides a cleaner architecture and eliminates code duplication.

## Overview

Browser-bunny provides persistent browser automation with session management, making it perfect for MarketBridge's needs. The integration provides:

- **Persistent Sessions**: Browser sessions survive server restarts and maintain state
- **Session Registry**: Track sessions with metadata including creation time, last used, and activity status
- **Configurable Server**: Run on different ports and hosts as needed
- **Enhanced Storage**: Automatic browser context persistence (cookies, localStorage, etc.)
- **Clean API**: Simple, consistent interface for browser automation

## Architecture Changes

### Before (MarketBridge v1.x)

```
MarketBridge
├── src/marketbridge_playwright/     # Duplicate browser automation code
│   ├── browser_manager.py
│   ├── session_manager.py
│   └── ...
├── src/marketbridge/
│   ├── browser_session_server.py   # Duplicate server implementation
│   ├── session_registry.py         # Duplicate session tracking
│   └── browser_client.py           # MarketBridge-specific client
└── scripts/
    └── browser_session_daemon.py   # Duplicate daemon management
```

### After (MarketBridge v2.x)

```
MarketBridge
├── src/marketbridge/
│   └── browser_client.py           # Thin wrapper around browser-bunny
└── dependencies:
    └── browser-bunny/               # Single source of browser automation
        ├── browser_bunny/
        │   ├── server.py           # Enhanced server with session registry
        │   ├── session_registry.py # Session persistence and tracking
        │   ├── session_manager.py  # Self-sufficient session management
        │   ├── client.py           # Core browser client
        │   └── daemon.py           # Server daemon management
        └── ...
```

## Quick Start

### 1. Start Browser-Bunny Server

```bash
# Option 1: Install browser-bunny globally (recommended for development)
pip install -e /home/seth/Software/dev/browser-bunny
browser-bunny start
browser-bunny status

# Option 2: Use module from browser-bunny directory
cd /home/seth/Software/dev/browser-bunny
source .venv/bin/activate
python3 -m browser_bunny.daemon start
python3 -m browser_bunny.daemon status
```

### 2. Use in MarketBridge Code

```python
from marketbridge.browser_client import BrowserController
from browser_bunny import SessionManager

# High-level MarketBridge automation
async with BrowserController() as controller:
    session = await controller.start_session("my_session")
    await controller.wait_for_marketbridge_ready()
    await controller.subscribe_to_market_data("AAPL")
    await controller.take_debug_screenshot("subscribed")

# Or use browser-bunny directly for advanced use cases
async def advanced_automation():
    manager = SessionManager("advanced_session")
    try:
        await manager.navigate_to("http://localhost:8080")
        await manager.screenshot("marketbridge.png")
        data = await manager.execute_js("return document.title")
        return data
    finally:
        await manager.cleanup()
```

## API Reference

### MarketBridge Browser Client

MarketBridge provides a thin wrapper around browser-bunny with trading-specific convenience methods:

#### `BrowserController`

High-level controller for MarketBridge automation workflows.

```python
from marketbridge.browser_client import BrowserController

async with BrowserController("http://localhost:9247") as controller:
    # Start session with auto-navigation to MarketBridge
    session = await controller.start_session(
        session_name="trading_session",
        headless=False,
        auto_navigate=True
    )

    # MarketBridge-specific methods
    ready = await controller.wait_for_marketbridge_ready()
    success = await controller.subscribe_to_market_data("AAPL")
    screenshot = await controller.take_debug_screenshot("trading")
```

#### `BrowserClient`

Thin wrapper around browser-bunny's BrowserClient with MarketBridge defaults.

```python
from marketbridge.browser_client import BrowserClient

async with BrowserClient() as client:
    # Same API as browser-bunny but with MarketBridge-specific defaults
    session = await client.create_session("my_session", headless=False)
    # ... rest of browser-bunny API
```

### Browser-Bunny Direct Usage

For advanced use cases, import browser-bunny directly:

```python
from browser_bunny import SessionManager
from browser_bunny.client import BrowserClient
from browser_bunny.session_registry import SessionRegistry

# Self-sufficient session management
manager = SessionManager("session_name", "http://localhost:9247")
await manager.navigate_to("https://example.com")
await manager.screenshot("example.png")
await manager.cleanup()

# Advanced session management
async with BrowserClient("http://localhost:9247") as client:
    sessions = await client.list_sessions()
    stats = await client.server_stats()
    deleted = await client.cleanup_sessions(max_age_hours=24)
```

## Configuration

### Server Configuration

Browser-bunny server can be configured via command line:

```bash
# Custom port and host
python3 -m browser_bunny.daemon start --port 8888 --host 0.0.0.0

# Custom registry file location
python3 -m browser_bunny.server --registry-file /path/to/registry.json
```

### Client Configuration

Configure clients to connect to custom server locations:

```python
# MarketBridge wrapper
controller = BrowserController("http://localhost:8888")

# Browser-bunny direct
manager = SessionManager("session", "http://localhost:8888")
client = BrowserClient("http://localhost:8888")
```

## Session Management

### Session Persistence

Browser sessions automatically persist their state:

- **Cookies**: Maintained across browser restarts
- **Local Storage**: Preserved between sessions
- **Session Storage**: Kept during browser session
- **Authentication**: Login states persist
- **Navigation History**: Available on session restoration

### Session Registry

All sessions are tracked in a persistent registry:

```python
from browser_bunny.session_registry import SessionRegistry

registry = SessionRegistry()

# Create session
session_id = registry.create_session("trading_session", metadata={
    "purpose": "Market data monitoring",
    "symbols": ["AAPL", "GOOGL"]
})

# Query sessions
session = registry.get_session_by_name("trading_session")
all_sessions = registry.list_sessions(active_only=True)

# Cleanup old sessions
deleted = registry.cleanup_inactive_sessions(max_age_hours=48)
```

### Session Lifecycle

1. **Create**: New session registered with metadata
1. **Active**: Browser running, regular activity updates
1. **Inactive**: Browser closed, session data preserved
1. **Cleanup**: Old inactive sessions automatically removed

## Migration Guide

### From MarketBridge v1.x

1. **Update Dependencies**: Browser-bunny is now automatically included via pyproject.toml
1. **Update Imports**: Change from `marketbridge_playwright` to `marketbridge.browser_client` or `browser_bunny`
1. **Server Management**: Use `browser_bunny.daemon` instead of `scripts/browser_session_daemon.py`
1. **Port Changes**: Default port changed from 8766 to 9247

#### Code Changes

**Before:**

```python
from marketbridge_playwright.browser_manager import BrowserManager
from marketbridge_playwright.session_manager import SessionManager

manager = BrowserManager()
await manager.start()
context = await manager.create_session_context("session")
```

**After:**

```python
from marketbridge.browser_client import BrowserController

async with BrowserController() as controller:
    session = await controller.start_session("session")
```

### Server Management

**Before:**

```bash
python scripts/browser_session_daemon.py start
python scripts/browser_session_daemon.py status
```

**After:**

```bash
cd /home/seth/Software/dev/browser-bunny
source .venv/bin/activate
python3 -m browser_bunny.daemon start
python3 -m browser_bunny.daemon status
```

## Development Workflow

### Running Examples

```bash
# Start browser-bunny server
browser-bunny start

# Run MarketBridge examples
python examples/browser_session_example.py
```

### Debugging

1. **Check Server Status**:

   ```bash
   python3 -m browser_bunny.daemon status
   ```

1. **View Server Logs**:

   ```bash
   python3 -m browser_bunny.daemon logs -n 50
   ```

1. **Test Server Connection**:

   ```bash
   curl http://localhost:9247/health
   ```

1. **List Active Sessions**:

   ```bash
   curl http://localhost:9247/sessions
   ```

## Troubleshooting

### Common Issues

1. **"Connection refused" errors**:

   - Ensure browser-bunny server is running
   - Check port configuration (9247 is default)
   - Verify no firewall blocking connections

1. **"Session not found" errors**:

   - Sessions may have been cleaned up due to inactivity
   - Check session registry: `curl http://localhost:9247/sessions`
   - Create new session if needed

1. **Browser fails to start**:

   - Ensure playwright browsers are installed: `playwright install`
   - Check system dependencies: `playwright install-deps`
   - Verify sufficient system resources

1. **Import errors**:

   - Ensure browser-bunny is properly installed as dependency
   - Check MarketBridge pyproject.toml includes browser-bunny
   - Verify Python path includes MarketBridge src directory

### Performance Tuning

1. **Session Cleanup**: Automatically clean old sessions to prevent resource buildup
1. **Headless Mode**: Use `headless=True` for production automation
1. **Resource Limits**: Monitor browser memory usage for long-running sessions
1. **Concurrent Sessions**: Limit concurrent browser instances based on system resources

## Contributing

Browser automation improvements should be made in the browser-bunny project, while MarketBridge-specific trading logic stays in MarketBridge. This separation keeps concerns clean and benefits both projects.

### Browser-Bunny Enhancements

Submit to: `/home/seth/Software/dev/browser-bunny/`

- Core browser automation features
- Session management improvements
- Server performance optimizations
- General-purpose browser utilities

### MarketBridge Enhancements

Submit to: `/home/seth/Software/dev/marketbridge/`

- Trading-specific browser interactions
- MarketBridge UI automation
- Market data subscription helpers
- Trading workflow automation
