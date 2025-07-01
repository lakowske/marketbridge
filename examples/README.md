# MarketBridge Examples

Essential scripts for MarketBridge automation using browser-bunny persistent sessions.

## Quick Start

1. **Start servers:**
   ```bash
   python scripts/manage_server.py start    # MarketBridge server
   browser-bunny start                      # Browser automation server
   ```

2. **Check connection:**
   ```bash
   python examples/quick_ib_check.py
   ```

3. **Subscribe to market data:**
   ```bash
   python examples/subscribe.py AAPL STK    # Apple stock
   python examples/subscribe.py MNQ FUT     # Micro Nasdaq futures
   ```

4. **Unsubscribe:**
   ```bash
   python examples/unsubscribe.py AAPL
   ```

## Core Examples

### Connection Status
```bash
python examples/quick_ib_check.py
```
Quick check of WebSocket and IB connection status with real-time feedback.

### Subscribe to Market Data
```bash
python examples/subscribe.py <SYMBOL> <INSTRUMENT_TYPE>
```

**Examples:**
```bash
python examples/subscribe.py AAPL STK     # Apple stock
python examples/subscribe.py MNQ FUT      # Micro Nasdaq futures
python examples/subscribe.py TSLA STK     # Tesla stock
```

**Supported Instrument Types:**
- `STK` - Stocks
- `FUT` - Futures  
- `OPT` - Options
- `CASH` - Forex
- `IND` - Indices

### Unsubscribe from Market Data
```bash
python examples/unsubscribe.py <SYMBOL>
```

**Examples:**
```bash
python examples/unsubscribe.py AAPL      # Unsubscribe from Apple
python examples/unsubscribe.py MNQ       # Unsubscribe from Micro Nasdaq
```

## Utility Scripts

### Session Management
```bash
python examples/cleanup_sessions.py      # Clean up all browser sessions
```

### Complete Workflow Test
```bash
python examples/complete_workflow_test.py AAPL STK    # Test full subscribe/unsubscribe cycle
python examples/complete_workflow_test.py MNQ FUT     # Test with futures
```

Comprehensive test that performs subscribe → verify → unsubscribe → verify cycle.

## Browser Automation Features

- **Persistent Sessions** - Single `"marketbridge"` session shared across all scripts
- **Session Reuse** - Browser stays open between script runs for faster execution
- **Visual Debugging** - Screenshots taken at key steps for troubleshooting
- **Proper UI Integration** - Correct checkbox selection and form interaction
- **WebSocket Monitoring** - Verify backend communication for unsubscribe operations

## Usage Patterns

### Basic Session Usage
```python
from browser_bunny.persistent_session_manager import get_persistent_session

async def my_automation():
    # All examples use the same session name for consistency
    manager = await get_persistent_session("marketbridge")
    try:
        await manager.navigate_to("http://localhost:8080")
        # Your automation code here
    finally:
        await manager.cleanup()  # Leaves session open for reuse
```

### Subscribe/Unsubscribe Workflow
1. **Subscribe** - Fill form, click subscribe button
2. **Verify** - Check subscription appears in UI with checkbox
3. **Unsubscribe** - Select checkbox, click unsubscribe button  
4. **Verify** - Confirm WebSocket message sent and subscription removed

## Troubleshooting

### Connection Issues
```bash
python examples/quick_ib_check.py    # Check WebSocket and IB status
```

Expected output:
```
✅ All systems connected
  WS: WebSocket: Connected
  IB: IB: Connected
```

### Session Issues
```bash
python examples/cleanup_sessions.py    # Clean up stuck sessions
```

### Server Issues
```bash
python scripts/manage_server.py status    # Check MarketBridge server
browser-bunny status                      # Check browser automation server
```

## Prerequisites

1. **MarketBridge server running**: `python scripts/manage_server.py start`
2. **Browser-bunny server running**: `browser-bunny start`  
3. **IB TWS/Gateway connected** to MarketBridge
4. **Market data permissions** for the instruments you want to subscribe to

## Notes

- All scripts use the consistent session name `"marketbridge"` for seamless workflow
- Browser session persists between script runs for better performance
- Unsubscribe requires proper checkbox selection before clicking unsubscribe button
- WebSocket messages are monitored to ensure backend receives unsubscribe commands
- Screenshots are saved for debugging at key workflow steps