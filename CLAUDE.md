# Clean Python Project Template

## Important Conventions

**BROWSER-BUNNY ALIAS**: Throughout this project and in all conversations, `bb` is an alias for `browser-bunny`. When the user references `bb`, they are referring to the browser-bunny automation server. All commands that use `browser-bunny` can also use `bb`.

## Project Purpose

This is a template for creating clean, professional Python projects that incorporate industry best practices from the start. It serves as a foundation for new Python projects with all the essential development tools and quality assurance measures pre-configured.

## Clean Code Practices Implemented

### Code Quality & Standards

- **Black** - Automatic code formatting with 88 character line length
- **Flake8** - Comprehensive linting with Google docstring conventions
- **mdformat** - Markdown formatting with GitHub Flavored Markdown support
- **Pre-commit hooks** - Automated quality checks before every commit

### Testing & Coverage

- **Pytest** - Modern testing framework with proper project structure
- **Coverage reporting** - Minimum 80% code coverage required
- **HTML coverage reports** - Generated in `htmlcov/` directory
- **Integration testing** - Structured test organization

### Git Workflow

- **Pre-commit configuration** - Ensures code quality on every commit
- **Automated checks** for:
  - Trailing whitespace removal
  - End-of-file fixing
  - YAML validation
  - Large file detection
  - Code formatting (Black)
  - Linting (Flake8)
  - Markdown formatting (mdformat with GFM support)
  - Test coverage (Pytest with 80% minimum)

## Project Structure

```text
clean-python/
├── actions/          # Project build and automation scripts
├── tests/           # Test suite with pytest configuration
├── build/           # Build artifacts (auto-generated)
├── htmlcov/         # HTML coverage reports
├── .pre-commit-config.yaml  # Pre-commit hook configuration
├── .flake8          # Flake8 linting configuration
├── setup.cfg        # Project metadata and configuration
└── requirements.txt # Project dependencies
```

## Setup Instructions

### Initial Setup

1. **Copy environment configuration:**

   ```bash
   cp .env.example .env
   # Edit .env to set BROWSER_BUNNY_PATH for your system
   ```

1. **Run development setup:**

   ```bash
   python scripts/setup_dev.py
   ```

This will automatically:

- Install MarketBridge dependencies
- Install browser-bunny from your configured path
- Validate the environment setup

### Manual Setup (Alternative)

If you prefer manual setup:

- `pip install -e .` - Install MarketBridge in development mode
- `pip install -e /path/to/browser-bunny` - Install browser-bunny dependency

## Development Commands

- `pytest --cov=. --cov-report=term-missing --cov-fail-under=80 --cov-report=html` - Run tests with coverage
- `black .` - Format code
- `flake8` - Run linting
- `pre-commit install` - Install pre-commit hooks
- `pre-commit run --all-files` - Run all pre-commit checks

## Server Management Commands

### MarketBridge Main Server

Use the professional CLI server management tool for running MarketBridge:

- `python scripts/manage_server.py start` - Start server in background
- `python scripts/manage_server.py stop` - Stop server gracefully
- `python scripts/manage_server.py restart` - Restart server
- `python scripts/manage_server.py status` - Show server status
- `python scripts/manage_server.py -v status` - Show detailed status with memory usage
- `python scripts/manage_server.py logs` - Show recent logs (last 50 lines)
- `python scripts/manage_server.py logs -n 100` - Show last 100 lines of logs
- `python scripts/manage_server.py logs --follow` - Follow logs in real-time
- `python scripts/manage_server.py logs --error` - Show error logs
- `python scripts/manage_server.py --help` - Show all available options

### Browser-Bunny Server (bb)

**IMPORTANT**: In all conversations, `bb` is an alias for `browser-bunny`. When the user references `bb`, they are referring to browser-bunny.

Use browser-bunny (bb) for persistent browser automation:

- `bb start` or `browser-bunny start` - Start browser automation server
- `bb stop` or `browser-bunny stop` - Stop browser automation server
- `bb restart` or `browser-bunny restart` - Restart browser automation server
- `bb status` or `browser-bunny status` - Show server status
- `bb logs -n 50` or `browser-bunny logs -n 50` - Show recent logs
- Alternative: `python3 -m browser_bunny.daemon start` - Start using module directly

**Session Management**: Use the existing scripts in the `examples/` directory:

- `python examples/cleanup_sessions.py` - Clean up old browser sessions
- `python examples/cleanup_sessions.py --old-only 24` - Clean sessions older than 24 hours

### Server Management Features

- **Background process management** with PID file tracking
- **Graceful shutdown** handling (SIGTERM → SIGKILL if needed)
- **Comprehensive logging** to `logs/marketbridge.log`, `logs/marketbridge_error.log`, and browser-bunny logs
- **Colorized CLI output** for better user experience
- **Process monitoring** with memory usage and status information
- **Browser session persistence** via browser-bunny with automatic cleanup

## Logging Standards

All code should implement comprehensive logging with the following requirements:

- **Severity levels** - Use appropriate levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **File location** - Include `__name__` or explicit file path in logger configuration
- **Line numbers** - Use `%(lineno)d` in formatter to capture line numbers
- **Operation context** - Log the operation being performed with descriptive messages
- **Variable tracking** - Include relevant variable names and their values in log messages

### Example Logging Configuration

```python
import logging

# Configure logger with comprehensive formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Example usage
def process_data(data_id, data_content):
    logger.info(f"Starting data processing - data_id: {data_id}, content_length: {len(data_content)}")
    try:
        # Process data
        result = transform_data(data_content)
        logger.debug(f"Data transformation successful - result_type: {type(result)}, result_size: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"Data processing failed - data_id: {data_id}, error: {str(e)}", exc_info=True)
        raise
```

## Quality Gates

Every commit must pass:

1. Code formatting (Black)
1. Linting checks (Flake8)
1. Markdown formatting (mdformat)
1. All tests passing
1. Minimum 80% code coverage
1. No trailing whitespace
1. Proper file endings
1. Valid YAML syntax

This template ensures that code quality, testing, and documentation standards are maintained throughout the development lifecycle.

## Browser Automation with Browser-Bunny (bb)

**IMPORTANT**: Throughout this documentation and in all conversations, `bb` is an alias for `browser-bunny`. When the user references `bb`, they are referring to browser-bunny.

**SCRIPT LOCATION**: All browser-bunny (bb) scripts should be stored in and run from the `examples/` directory. When creating or modifying bb session scripts, always use the `examples/` directory.

MarketBridge uses **browser-bunny (bb)** for browser automation, providing persistent browser sessions and trading workflow automation. Browser-bunny (bb) is a FastAPI-based server that manages browser sessions using Playwright, enabling iterative development and session persistence.

### Architecture Overview

- **Browser-Bunny Server** - FastAPI server managing browser sessions via Playwright
- **Persistent Sessions** - Sessions survive script restarts and maintain state
- **Session Registry** - Centralized tracking with automatic cleanup
- **MarketBridge Integration** - Thin wrapper for trading-specific workflows
- **Clean Dependencies** - MarketBridge imports browser-bunny as a file dependency

### Quick Start

```bash
# Start the browser-bunny server (required for all automation)
bb start  # or browser-bunny start

# Check server status
bb status  # or browser-bunny status

# Run MarketBridge automation examples (from project root)
python examples/persistent_browser.py
python examples/marketbridge_parser.py
python examples/cleanup_sessions.py
```

**IMPORTANT**: Always use scripts from the `examples/` directory when working with browser-bunny (bb) sessions. Do not create new scripts outside this directory unless specifically requested.

### Core Development Patterns

#### 1. Persistent Session Pattern (Recommended)

Use the persistent session manager for sessions that survive script restarts:

```python
from browser_bunny.persistent_session_manager import get_persistent_session

async def parse_marketbridge_data():
    # Get or create persistent session - survives script restarts
    manager = await get_persistent_session("marketbridge_parser")

    try:
        # Navigate to MarketBridge
        await manager.navigate_to("http://localhost:8080")

        # Take screenshot for debugging
        await manager.screenshot("marketbridge_start.png")

        # Parse market data using JavaScript
        market_data = await manager.execute_js("""
            return Array.from(document.querySelectorAll('#market-data-table tbody tr')).map(row => ({
                symbol: row.cells[0]?.textContent.trim(),
                bid: row.cells[1]?.textContent.trim(),
                ask: row.cells[2]?.textContent.trim()
            }));
        """)

        return market_data

    finally:
        # Don't cleanup - leave persistent session open for reuse
        await manager.cleanup()
```

#### 2. MarketBridge Wrapper Pattern

Use the MarketBridge-specific wrapper for convenience methods:

```python
from marketbridge.browser_client import BrowserController

async def automate_trading():
    async with BrowserController() as controller:
        # Start persistent session with auto-navigation to MarketBridge
        session = await controller.start_session("trading", auto_navigate=True)

        # Wait for MarketBridge UI to be ready
        await controller.wait_for_marketbridge_ready()

        # MarketBridge-specific automation
        await controller.subscribe_to_market_data("AAPL")
        await controller.take_debug_screenshot("subscribed")
```

#### 3. Session Management Pattern

```python
# List all active sessions
from browser_bunny.client import BrowserClient

async def list_sessions():
    async with BrowserClient("http://localhost:9247") as client:
        response = await client.get("/sessions")
        sessions = response.get("sessions", [])

        for session in sessions:
            print(f"Session: {session['session_name']} ({session['session_id']})")
            print(f"  Created: {session.get('created_at', 'Unknown')}")
            print(f"  Pages: {len(session.get('pages', []))}")

# Cleanup old sessions
async def cleanup_old_sessions():
    async with BrowserClient("http://localhost:9247") as client:
        response = await client.get("/sessions")
        sessions = response.get("sessions", [])

        for session in sessions:
            # Clean up sessions older than 24 hours
            if is_session_old(session, hours=24):
                await client.delete(f"/sessions/{session['session_id']}")
                print(f"Cleaned up old session: {session['session_name']}")
```

### Development Workflow

#### 1. Iterative Parser Development

```python
# Step 1: Inspect DOM structure
async def inspect_marketbridge_dom():
    manager = await get_persistent_session("dom_inspector")
    await manager.navigate_to("http://localhost:8080")

    # Debug DOM structure
    structure = await manager.execute_js("""
        return {
            market_table: !!document.querySelector('#market-data-table'),
            status_element: !!document.querySelector('#status-text'),
            available_ids: Array.from(document.querySelectorAll('[id]')).map(el => el.id),
            table_headers: Array.from(document.querySelectorAll('#market-data-table th')).map(th => th.textContent.trim())
        };
    """)
    print(json.dumps(structure, indent=2))

# Step 2: Build parser incrementally
async def build_parser():
    manager = await get_persistent_session("parser_dev")

    # Test each component separately
    connection_status = await manager.execute_js(
        "return document.querySelector('#status-text')?.textContent.trim()"
    )

    market_data = await manager.execute_js("""
        return Array.from(document.querySelectorAll('#market-data-table tbody tr')).map((row, index) => ({
            rank: index + 1,
            symbol: row.cells[0]?.textContent.trim() || '',
            bid: row.cells[1]?.textContent.trim() || '',
            ask: row.cells[2]?.textContent.trim() || ''
        }));
    """)

    return {"status": connection_status, "data": market_data}
```

#### 2. Screenshot-Driven Development

```python
async def debug_with_screenshots():
    manager = await get_persistent_session("debug_session")

    # Take screenshot at each step
    await manager.navigate_to("http://localhost:8080")
    await manager.screenshot("01_initial_load.png")

    # Wait for data to load
    await asyncio.sleep(2)
    await manager.screenshot("02_data_loaded.png")

    # Execute parsing
    result = await manager.execute_js("/* parsing code */")
    await manager.screenshot("03_after_parsing.png")

    print(f"Screenshots saved to: screenshots/")
```

### Session Lifecycle Management

#### Session Naming Conventions

```python
# Use descriptive session names for different purposes
manager = await get_persistent_session("marketbridge_parser")      # For UI parsing
manager = await get_persistent_session("trading_automation")       # For trading workflows
manager = await get_persistent_session("dom_inspector")           # For development/debugging
manager = await get_persistent_session("performance_test")        # For testing
```

#### Session Cleanup Strategies

```python
# Manual cleanup when completely done
from browser_bunny.persistent_session_manager import cleanup_persistent_session

# Clean up specific session
await cleanup_persistent_session("marketbridge_parser")

# Or use the cleanup script
# python examples/cleanup_sessions.py --old-only 24  # Clean sessions older than 24 hours
```

### Error Handling and Debugging

```python
async def robust_parsing():
    manager = await get_persistent_session("robust_parser")

    try:
        await manager.navigate_to("http://localhost:8080", wait_until="domcontentloaded")

        # Verify page loaded correctly
        page_title = await manager.execute_js("return document.title")
        if "MarketBridge" not in page_title:
            await manager.screenshot("error_wrong_page.png")
            raise Exception(f"Wrong page loaded: {page_title}")

        # Parse with error handling
        market_data = await manager.execute_js("""
            try {
                const rows = document.querySelectorAll('#market-data-table tbody tr');
                if (rows.length === 0) {
                    return {error: "No market data rows found"};
                }

                return Array.from(rows).map(row => ({
                    symbol: row.cells[0]?.textContent.trim() || 'UNKNOWN',
                    bid: row.cells[1]?.textContent.trim() || '0',
                    ask: row.cells[2]?.textContent.trim() || '0'
                }));
            } catch (e) {
                return {error: e.message};
            }
        """)

        if market_data.get('error'):
            await manager.screenshot("error_parsing_failed.png")
            raise Exception(f"Parsing failed: {market_data['error']}")

        return market_data

    except Exception as e:
        # Always take error screenshot for debugging
        await manager.screenshot("error_exception.png")
        logger.error(f"Parsing failed: {e}", exc_info=True)
        raise
    finally:
        # Leave session open for investigation/reuse
        await manager.cleanup()
```

### Integration with MarketBridge Workflows

#### Market Data Subscription Automation

```python
async def automate_subscription(symbol: str, instrument_type: str):
    manager = await get_persistent_session("subscription_automation")

    await manager.navigate_to("http://localhost:8080")

    # Fill subscription form
    await manager.execute_js(f"""
        document.querySelector('#symbol-input').value = '{symbol}';
        document.querySelector('#instrument-select').value = '{instrument_type}';
        document.querySelector('#subscribe-button').click();
    """)

    # Wait for subscription to appear
    await asyncio.sleep(1)

    # Verify subscription was added
    subscriptions = await manager.execute_js("""
        return Array.from(document.querySelectorAll('#subscriptions-list .subscription-item')).map(item => ({
            symbol: item.querySelector('.symbol')?.textContent.trim(),
            type: item.querySelector('.type')?.textContent.trim()
        }));
    """)

    # Take confirmation screenshot
    await manager.screenshot(f"subscription_{symbol}_{instrument_type}.png")

    return subscriptions
```

### Best Practices

1. **Use Persistent Sessions** - Always use `get_persistent_session()` for development
1. **Screenshot Everything** - Take screenshots at each step for visual debugging
1. **Incremental Development** - Build parsers step by step, test each component
1. **Error Screenshots** - Always take screenshots on errors for debugging
1. **Descriptive Session Names** - Use clear, descriptive session names
1. **Clean JavaScript** - Use proper JavaScript with error handling
1. **Wait Appropriately** - Use `domcontentloaded` for most cases, add manual waits when needed
1. **Verify Results** - Always verify parsed data matches what's visible on page
1. **Use bb alias** - In commands and conversations, `bb` is equivalent to `browser-bunny`
1. **Use examples/ directory** - All bb scripts should be in the `examples/` directory

### Available Examples

**IMPORTANT**: All browser-bunny (bb) scripts are located in the `examples/` directory. Always look for and use existing scripts before creating new ones.

- **`examples/persistent_browser.py`** - Create a persistent browser session
- **`examples/marketbridge_parser.py`** - Parse MarketBridge UI data
- **`examples/cleanup_sessions.py`** - Session management and cleanup (USE THIS for cleaning sessions)
- **`examples/complete_workflow_test.py`** - Complete MarketBridge workflow automation

When working with bb sessions:

1. First check if an existing script in `examples/` meets your needs
1. Modify existing scripts rather than creating new ones when possible
1. Always run scripts from the project root: `python examples/script_name.py`

### Documentation References

- **[docs/BROWSER_BUNNY_INTEGRATION.md](docs/BROWSER_BUNNY_INTEGRATION.md)** - Complete integration guide
- **[examples/README.md](examples/README.md)** - Example usage and patterns
- **[Browser-Bunny Documentation](../browser-bunny/docs/)** - Core automation library docs

**Remember**:

- `bb` = `browser-bunny` in all commands and conversations
- All bb scripts are in the `examples/` directory
- Use existing scripts like `examples/cleanup_sessions.py` rather than creating new ones

MarketBridge leverages browser-bunny's (bb's) persistent session architecture for robust, iterative browser automation that survives script restarts and enables faster development cycles.
