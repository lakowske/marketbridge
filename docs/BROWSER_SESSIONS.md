# MarketBridge Browser Sessions

This document describes the browser-bunny inspired persistent browser session architecture integrated into MarketBridge.

## Overview

MarketBridge now includes a powerful browser automation system that provides:

- **Persistent Browser Sessions**: Browser instances that survive script restarts
- **Server-Based Control**: RESTful API for browser automation
- **Session Registry**: Centralized tracking of all browser sessions
- **Remote Debugging**: Live screenshots and interactive control
- **MarketBridge Integration**: Specialized automation for trading workflows

## Architecture

The system consists of several key components:

```
┌─────────────────┐    HTTP API     ┌──────────────────┐    Playwright    ┌─────────────────┐
│  Browser Client │◀──────────────▶│ Session Server   │◀───────────────▶│ Browser Manager │
│  (Python SDK)   │                │  (FastAPI)       │                 │  (Playwright)   │
└─────────────────┘                └──────────────────┘                 └─────────────────┘
         │                                    │                                    │
         ▼                                    ▼                                    ▼
┌─────────────────┐                ┌──────────────────┐                 ┌─────────────────┐
│ Session Scripts │                │ Session Registry │                 │ Browser Contexts│
│ & Automation    │                │ (Persistent)     │                 │ & Pages         │
└─────────────────┘                └──────────────────┘                 └─────────────────┘
```

### Key Components

1. **Browser Session Server** (`src/marketbridge/browser_session_server.py`)

   - FastAPI server managing browser sessions
   - RESTful endpoints for session control
   - Background cleanup and health monitoring

1. **Browser Client Library** (`src/marketbridge/browser_client.py`)

   - Python SDK for programmatic browser control
   - High-level `BrowserController` for MarketBridge workflows
   - Low-level `BrowserClient` for direct API access

1. **Session Registry** (`src/marketbridge/session_registry.py`)

   - Persistent storage of session metadata
   - Automatic cleanup and health tracking
   - JSON-based registry with atomic updates

1. **Session Daemon** (`scripts/browser_session_daemon.py`)

   - Process management for the session server
   - Start/stop/restart/status operations
   - PID file management and graceful shutdown

## Quick Start

### 1. Install Dependencies

```bash
# Install FastAPI and browser automation dependencies
pip install -e ".[dev]"

# Install Playwright browsers
playwright install
```

### 2. Start the Session Server

```bash
# Start in background
python scripts/browser_session_daemon.py start

# Check status
python scripts/browser_session_daemon.py status

# View logs
python scripts/browser_session_daemon.py logs
```

### 3. Use Browser Sessions

```python
import asyncio
from marketbridge.browser_client import BrowserController

async def automate_marketbridge():
    async with BrowserController() as controller:
        # Start or reuse session
        session = await controller.start_session(
            session_name="trading_session",
            headless=False,
            auto_navigate=True
        )

        # Wait for MarketBridge to load
        await controller.wait_for_marketbridge_ready()

        # Subscribe to market data
        await controller.subscribe_to_market_data("AAPL")

        # Take debug screenshot
        await controller.take_debug_screenshot("after_subscription")

asyncio.run(automate_marketbridge())
```

## API Reference

### Session Management Endpoints

- `POST /sessions` - Create new browser session
- `GET /sessions` - List all sessions
- `GET /sessions/{id}` - Get session details
- `DELETE /sessions/{id}` - Delete session
- `GET /health` - Server health check
- `GET /stats` - Server statistics

### Browser Control Endpoints

- `POST /sessions/{id}/navigate` - Navigate to URL
- `POST /sessions/{id}/screenshot` - Take screenshot
- `POST /sessions/{id}/execute` - Execute JavaScript
- `POST /sessions/{id}/interact` - Interact with elements
- `POST /sessions/{id}/wait` - Wait for conditions

### Python Client Classes

#### BrowserClient

Low-level client for direct API access:

```python
async with BrowserClient("http://localhost:8765") as client:
    # Create session
    session = await client.create_session("my_session")

    # Navigate
    await session.navigate("http://localhost:8080")

    # Take screenshot
    await session.screenshot("debug.png")

    # Execute JavaScript
    result = await session.execute_js("document.title")
```

#### BrowserController

High-level controller for MarketBridge workflows:

```python
async with BrowserController() as controller:
    # Start session with auto-navigation
    session = await controller.start_session("trading")

    # Wait for app ready
    await controller.wait_for_marketbridge_ready()

    # Subscribe to market data
    await controller.subscribe_to_market_data("AAPL")
```

## Session Persistence

Sessions are stored in `~/.marketbridge/browser_sessions_registry.json` with the following structure:

```json
{
  "sessions": {
    "session-uuid": {
      "session_id": "session-uuid",
      "session_name": "trading_session",
      "created_at": "2025-06-27T10:30:00",
      "last_activity": "2025-06-27T10:35:00",
      "current_url": "http://localhost:8080",
      "active": true,
      "page_count": 1,
      "metadata": {}
    }
  },
  "active_sessions": ["session-uuid"],
  "last_updated": "2025-06-27T10:35:00"
}
```

Browser contexts and storage state are persisted using the existing Playwright SessionManager in `~/.marketbridge/playwright_sessions/`.

## Daemon Management

The session daemon provides process lifecycle management:

```bash
# Start daemon
python scripts/browser_session_daemon.py start

# Stop daemon
python scripts/browser_session_daemon.py stop

# Restart daemon
python scripts/browser_session_daemon.py restart

# Check status
python scripts/browser_session_daemon.py status -v

# View logs
python scripts/browser_session_daemon.py logs -n 100

# Follow logs
python scripts/browser_session_daemon.py logs --follow

# Clean up
python scripts/browser_session_daemon.py cleanup
```

## MarketBridge Integration

The system includes specialized methods for MarketBridge automation:

### Market Data Subscription

```python
# Subscribe to a symbol
success = await controller.subscribe_to_market_data(
    symbol="AAPL",
    instrument_type="stock",
    data_type="market_data"
)
```

### Connection Monitoring

```python
# Wait for MarketBridge to be ready
ready = await controller.wait_for_marketbridge_ready(timeout=30000)

# Check connection status
status = await session.execute_js("""
    document.querySelector('#status-text')?.textContent
""")
```

### Debug Screenshots

```python
# Take timestamped debug screenshots
filename = await controller.take_debug_screenshot("subscription_test")
```

## Development Workflow

### 1. Interactive Development

Use existing Playwright tools for iterative development:

```bash
# Create/manage sessions via CLI
python scripts/playwright_session.py create my_session
python scripts/playwright_session.py start my_session --marketbridge

# Develop scripts in playwright_snippets/
cp playwright_snippets/template.py playwright_snippets/my_test.py
```

### 2. Server-Based Automation

Use the browser session server for production automation:

```python
# Create persistent automation scripts
from marketbridge.browser_client import BrowserController

async def trading_automation():
    async with BrowserController() as controller:
        session = await controller.start_session("production")
        # Automation logic here...
```

### 3. Testing Integration

Browser sessions integrate with existing test frameworks:

```python
import pytest
from marketbridge.browser_client import BrowserClient

@pytest.mark.asyncio
async def test_marketbridge_subscription():
    async with BrowserClient() as client:
        session = await client.create_session("test_session")
        # Test automation...
```

## Configuration

### Server Configuration

The session server can be configured via command line arguments:

```bash
python -m marketbridge.browser_session_server \
    --host localhost \
    --port 8765 \
    --registry-file /path/to/registry.json \
    --screenshots-dir /path/to/screenshots \
    --log-dir /path/to/logs
```

### Session Configuration

Browser sessions support various configuration options:

```python
session = await client.create_session(
    session_name="my_session",
    headless=False,
    viewport={"width": 1920, "height": 1080},
    browser_type="chromium"  # or "firefox", "webkit"
)
```

## Error Handling

The system includes comprehensive error handling:

### Session Recovery

```python
# Sessions automatically recover from browser crashes
session = await client.get_session_by_name("my_session")
if not session or not session.is_active:
    session = await client.create_session("my_session")
```

### Health Monitoring

```python
# Check session health
health = await client.server_health()
if health["status"] != "healthy":
    # Handle server issues
    pass
```

### Automatic Cleanup

```python
# Clean up old sessions automatically
deleted = await client.cleanup_sessions(max_age_hours=24)
```

## Performance Considerations

### Session Reuse

- Sessions persist across script runs, reducing startup overhead
- Browser contexts maintain state (cookies, localStorage, etc.)
- Automatic cleanup prevents resource accumulation

### Concurrent Sessions

- Multiple sessions can run simultaneously
- Each session has isolated browser context
- Server manages resource allocation automatically

### Monitoring

```bash
# Monitor server resource usage
python scripts/browser_session_daemon.py status -v

# View server statistics
curl http://localhost:8765/stats
```

## Troubleshooting

### Common Issues

1. **Server not starting**

   ```bash
   # Check if port is available
   netstat -an | grep 8765

   # View detailed logs
   python scripts/browser_session_daemon.py logs --follow
   ```

1. **Session creation failures**

   ```bash
   # Verify Playwright installation
   playwright install

   # Check server health
   curl http://localhost:8765/health
   ```

1. **Browser not responding**

   ```python
   # Force session recreation
   await client.delete_session(session_id)
   session = await client.create_session("new_session")
   ```

### Log Files

- Server logs: `logs/browser_session_server.log`
- Daemon logs: `logs/browser_session_daemon.log`
- Session storage: `~/.marketbridge/browser_sessions_registry.json`

## Examples

See `examples/browser_session_example.py` for comprehensive usage examples:

```bash
# Run all examples
python examples/browser_session_example.py

# Make sure servers are running first:
python scripts/browser_session_daemon.py start
python run_server.py  # MarketBridge server
```

## Integration with Existing Tools

The browser session system complements existing MarketBridge tools:

- **CLI Tools**: Session daemon works alongside existing scripts
- **Web Interface**: Browser sessions can control the web UI
- **Testing**: Integrates with pytest and existing test infrastructure
- **Logging**: Uses MarketBridge logging standards and formats

This architecture provides a powerful foundation for browser-based trading automation while maintaining the flexibility and interactivity that developers need for rapid prototyping and debugging.
