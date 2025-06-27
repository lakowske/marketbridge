# MarketBridge Playwright Integration

This document describes the Playwright browser automation integration for MarketBridge, which provides persistent browser sessions and easy scripting capabilities for web interface testing and automation.

## Features

- **Persistent Sessions**: Browser sessions are saved to disk and can be restored across script runs
- **Session Management**: CLI tools for creating, listing, and managing sessions
- **Browser Lifecycle Management**: Easy start/stop of browser instances with session integration
- **MarketBridge Integration**: Specialized functions for interacting with MarketBridge web interface
- **Temporary Snippets**: Git-ignored directory for experimental scripts

## Installation

1. Install Playwright dependency:

   ```bash
   pip install -e ".[dev]"
   ```

1. Install Playwright browsers:

   ```bash
   playwright install
   ```

## Directory Structure

```
marketbridge/
├── playwright/                    # Core Playwright modules
│   ├── __init__.py               # Package initialization
│   ├── session_manager.py        # Session persistence management
│   ├── browser_manager.py        # Browser lifecycle management
│   └── examples/                 # Example scripts
│       ├── basic_navigation.py   # Basic browser automation
│       └── marketbridge_interaction.py  # MarketBridge-specific automation
├── playwright_snippets/          # Temporary scripts (git-ignored)
│   ├── .gitkeep                 # Keeps directory in git
│   └── template.py              # Template for new scripts
└── scripts/
    └── playwright_session.py     # CLI for session management
```

## Session Management CLI

The `scripts/playwright_session.py` script provides comprehensive session management:

### Create a Session

```bash
python scripts/playwright_session.py create my_session -d "My test session"
```

### List Sessions

```bash
python scripts/playwright_session.py list
```

### Start Browser Session

```bash
# Start browser with session
python scripts/playwright_session.py start my_session

# Start and navigate to MarketBridge
python scripts/playwright_session.py start my_session --marketbridge

# Start in headless mode
python scripts/playwright_session.py start my_session --headless

# Navigate to custom URL
python scripts/playwright_session.py start my_session --url https://example.com
```

### Delete Session

```bash
python scripts/playwright_session.py delete my_session
```

### Cleanup Old Sessions

```bash
# Clean up sessions older than 7 days
python scripts/playwright_session.py cleanup --days 7
```

## Programming Interface

### Basic Usage

```python
import asyncio
from playwright.browser_manager import BrowserManager
from playwright.session_manager import SessionManager

async def example():
    # Create managers
    session_manager = SessionManager()
    browser_manager = BrowserManager(session_manager)

    try:
        # Start browser
        await browser_manager.start(headless=False)

        # Create or restore session
        context = await browser_manager.create_session_context("my_session")

        # Create page and navigate
        page = await browser_manager.new_page("my_session")
        await page.goto("https://example.com")

        # Your automation code here...

    finally:
        await browser_manager.stop()

asyncio.run(example())
```

### MarketBridge-Specific Usage

```python
async def marketbridge_example():
    browser_manager = BrowserManager()

    try:
        await browser_manager.start(headless=False)

        # Navigate directly to MarketBridge
        page = await browser_manager.navigate_to_marketbridge("mb_session")

        # Subscribe to market data
        await page.fill("#symbol", "AAPL")
        await page.select_option("#instrument-type", "stock")
        await page.select_option("#data-type", "market_data")
        await page.click("#subscribe-btn")

        # Monitor for updates
        await asyncio.sleep(10)

    finally:
        await browser_manager.stop()
```

## Session Storage

Sessions are stored in `~/.marketbridge/playwright_sessions/` with the following structure:

```
~/.marketbridge/playwright_sessions/
└── session_name/
    ├── metadata.json          # Session metadata
    ├── state.json            # Custom state data
    └── browser_context/      # Browser context data
        └── storage_state.json # Cookies, localStorage, etc.
```

## Temporary Snippets Workflow

The `playwright_snippets/` directory is perfect for iterative development:

1. Copy the template:

   ```bash
   cp playwright_snippets/template.py playwright_snippets/my_test.py
   ```

1. Edit your script:

   ```python
   # Modify the script_logic() function
   async def script_logic(browser_manager, session_name="snippet_session"):
       page = await browser_manager.navigate_to_marketbridge(session_name)

       # Your experimental code here
       await page.fill("#symbol", "TSLA")
       await page.click("#subscribe-btn")
       await asyncio.sleep(5)
   ```

1. Run your script:

   ```bash
   python playwright_snippets/my_test.py
   ```

1. The script will automatically maintain session state between runs

## Common Patterns

### Wait for MarketBridge to Load

```python
# Wait for the app container
await page.wait_for_selector("#app", timeout=10000)

# Wait for connection status
await page.wait_for_selector("#status-text", timeout=5000)
```

### Subscribe to Market Data

```python
async def subscribe_symbol(page, symbol, instrument_type="stock", data_type="market_data"):
    await page.fill("#symbol", symbol)
    await page.select_option("#instrument-type", instrument_type)
    await page.select_option("#data-type", data_type)
    await page.click("#subscribe-btn")

    # Wait for subscription to appear
    await page.wait_for_selector(f"text={symbol}", timeout=5000)
```

### Monitor Market Data

```python
# Set up console message monitoring
def on_console_message(msg):
    if "market_data" in msg.text.lower():
        print(f"Market data update: {msg.text}")

page.on("console", on_console_message)
```

### Take Screenshots

```python
# Take full page screenshot
await page.screenshot(path="marketbridge.png", full_page=True)

# Take screenshot of specific element
element = await page.query_selector("#market-data-grid")
await element.screenshot(path="data_grid.png")
```

## Best Practices

1. **Always Use Session Names**: This enables session persistence across runs
1. **Handle Exceptions**: Wrap browser operations in try/catch blocks
1. **Clean Up Resources**: Always call `browser_manager.stop()` in finally blocks
1. **Use Context Managers**: Consider using `async with BrowserManager() as browser:`
1. **Test Connectivity**: Check MarketBridge connection status before automation
1. **Use Headless for CI**: Set `headless=True` for automated testing

## Troubleshooting

### Playwright Not Installed

```bash
pip install playwright
playwright install
```

### MarketBridge Connection Issues

- Ensure MarketBridge server is running on http://localhost:8080
- Check WebSocket connection status in browser console
- Verify no firewall blocking connections

### Session Persistence Issues

- Check permissions on `~/.marketbridge/` directory
- Verify session directory structure is intact
- Use `python scripts/playwright_session.py list` to check session status

### Browser Launch Issues

- Try different browser types: `--browser firefox` or `--browser webkit`
- Check if running in headless mode works: `--headless`
- Verify system has required dependencies for GUI browser

## Examples

See the `playwright/examples/` directory for complete working examples:

- `basic_navigation.py`: Basic browser automation concepts
- `marketbridge_interaction.py`: Advanced MarketBridge automation

Run examples with:

```bash
python playwright/examples/basic_navigation.py
python playwright/examples/marketbridge_interaction.py
```
