# MarketBridge Browser Automation Examples

This directory contains example scripts for automating MarketBridge using browser-bunny for persistent browser sessions.

## Browser Automation Examples

### Browser Session Management

```bash
# Comprehensive browser automation example
python examples/browser_session_example.py
```

Shows complete browser session management, MarketBridge automation, and session persistence using browser-bunny.

### Persistent Browser Session

```bash
# Create a persistent browser session for manual interaction
python examples/persistent_browser.py
```

Opens a browser window that stays open for manual interaction. The session persists and can be reused by other scripts.

### MarketBridge UI Parser

```bash
# Parse data from MarketBridge web interface
python examples/marketbridge_parser.py

# Debug DOM structure
python examples/marketbridge_parser.py --debug
```

Demonstrates parsing MarketBridge UI data using browser-bunny patterns, similar to news site parsers.

### Session Cleanup

```bash
# Clean up all browser sessions
python examples/cleanup_sessions.py

# Clean up only old sessions (24+ hours)
python examples/cleanup_sessions.py --old-only

# Clean up sessions older than specific hours
python examples/cleanup_sessions.py --old-only 48
```

Browser session management and cleanup utilities.

## General Market Data Scripts

### Subscribe to Market Data

```bash
python examples/subscribe.py <SYMBOL> <INSTRUMENT_TYPE>
```

**Examples:**

```bash
# Subscribe to Apple stock
python examples/subscribe.py AAPL STK

# Subscribe to SPY options (if supported)
python examples/subscribe.py SPY OPT

# For futures, use the specialized script below
```

### Subscribe to Futures (Recommended)

```bash
python examples/subscribe_futures.py <SYMBOL> [--expiry EXPIRY]
```

**Examples:**

```bash
# Subscribe to Micro Nasdaq futures (auto-detects contract)
python examples/subscribe_futures.py MNQ

# Subscribe to specific expiry
python examples/subscribe_futures.py MNQ --expiry H25

# Other popular futures
python examples/subscribe_futures.py ES    # S&P 500 futures
python examples/subscribe_futures.py CL    # Crude Oil futures
python examples/subscribe_futures.py GC    # Gold futures
```

**Supported Instrument Types:**

- `STK` - Stocks
- `FUT` - Futures
- `OPT` - Options
- `CASH` - Forex
- `IND` - Indices
- `CFD` - CFDs
- `BOND` - Bonds
- `CMDTY` - Commodities

### Unsubscribe from Market Data

```bash
python examples/unsubscribe.py <SYMBOL>
```

**Examples:**

```bash
# Unsubscribe from Apple stock
python examples/unsubscribe.py AAPL

# Unsubscribe from Micro Nasdaq futures
python examples/unsubscribe.py MNQ
```

## Utility Scripts

### Check Market Data Status

```bash
python examples/check_market_data.py
```

Shows current market data subscriptions and live data.

### Quick Connectivity Tests

```bash
# Quick IB connectivity check
python examples/quick_ib_check.py

# Quick MarketBridge probe
python examples/quick_probe.py
```

## Prerequisites

1. **Start MarketBridge Server:**

   ```bash
   python scripts/manage_server.py start
   ```

1. **Start Browser-Bunny Server:**

   ```bash
   # Option 1: If browser-bunny installed globally
   browser-bunny start

   # Option 2: Using module from source
   cd /home/seth/Software/dev/browser-bunny
   source .venv/bin/activate
   python3 -m browser_bunny.daemon start
   ```

1. **Ensure IB TWS/Gateway is running** and connected to MarketBridge.

## Browser Automation Features

- **Browser-Bunny Integration** - Uses browser-bunny for robust browser automation
- **Persistent Sessions** - Browser sessions survive script restarts and maintain state
- **Session Registry** - Centralized tracking with automatic cleanup
- **MarketBridge Integration** - Specialized methods for trading workflows
- **Developer Tools** - Screenshots, debugging, and session management
- **Clean Architecture** - No code duplication, leverages browser-bunny capabilities

## Browser Session Patterns

### Basic Persistent Session Usage

```python
from browser_bunny.persistent_session_manager import get_persistent_session

async def automate_marketbridge():
    # Get or create persistent session that survives script restarts
    manager = await get_persistent_session("my_session")
    try:
        await manager.navigate_to("http://localhost:8080")
        await manager.screenshot("marketbridge.png")
        data = await manager.execute_js("return document.title")
        return data
    finally:
        # Don't cleanup - leave persistent session open for reuse
        await manager.cleanup()
```

### MarketBridge-Specific Automation

```python
from marketbridge.browser_client import BrowserController
from browser_bunny.persistent_session_manager import get_persistent_session

async def trading_automation():
    # Option 1: Use MarketBridge wrapper (convenience methods)
    async with BrowserController() as controller:
        session = await controller.start_session("trading", auto_navigate=True)
        await controller.wait_for_marketbridge_ready()
        await controller.subscribe_to_market_data("AAPL")
        await controller.take_debug_screenshot("subscribed")

    # Option 2: Use persistent session directly (more control)
    manager = await get_persistent_session("trading_session")
    await manager.navigate_to("http://localhost:8080")
    await manager.screenshot("trading_start.png")
    # Session stays alive for reuse
```

## Troubleshooting

### Browser Automation Issues

**Problem**: "Connection refused" or browser automation fails

**Solutions**:

1. **Check browser-bunny server**: `browser-bunny status`
1. **Start browser-bunny**: `browser-bunny start`
1. **Check logs**: `browser-bunny logs -n 50`
1. **Test server**: `curl http://localhost:9247/health`

### MNQ/Futures Subscription Errors

**Problem**: "No security definition has been found for the request"

**Cause**: Futures require specific contract details (exchange, expiration month)

**Solutions**:

1. **Use the futures script**: `python examples/subscribe_futures.py MNQ`
1. **Check IB permissions**: Ensure you have CME market data subscriptions
1. **Try specific expiry**: `python examples/subscribe_futures.py MNQ --expiry H25`

### Common Expiry Codes

- `H25` = March 2025
- `M25` = June 2025
- `U25` = September 2025
- `Z25` = December 2025

### Session Management Issues

**Problem**: Sessions not persisting or conflicting

**Solutions**:

1. **Clean up old sessions**: `python examples/cleanup_sessions.py --old-only`
1. **Check session registry**: Use browser-bunny's session listing
1. **Use unique session names**: Avoid conflicts with descriptive names

## Development Patterns

Following browser-bunny's development patterns:

1. **Persistent Session Management** - Use `get_persistent_session()` for sessions that survive script restarts
1. **Screenshots** - Take screenshots at each step for debugging
1. **DOM Inspection** - Use JavaScript to inspect and parse page structure
1. **Error Handling** - Always use try/finally blocks with cleanup
1. **Iterative Development** - Build parsers incrementally, test each component
1. **Session Reuse** - Sessions stay alive between parser runs for faster development

## Notes

- Scripts automatically map IB instrument types (STK, FUT) to UI values (stock, future)
- Browser sessions persist across script runs for better performance using browser-bunny
- Market data appears in both subscription list and data table when successful
- Futures contracts require specific contract specifications including exchange and expiration month
- The `subscribe_futures.py` script automatically tries multiple contract variations to find valid ones
- Browser automation now uses browser-bunny for enhanced features and persistence
