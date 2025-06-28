# MarketBridge Browser Automation Examples

This directory contains example scripts for automating MarketBridge using browser sessions.

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

### Browser Session Example

```bash
python examples/browser_session_example.py
```

Comprehensive example showing browser session management and MarketBridge automation.

## Prerequisites

1. **Start MarketBridge Server:**

   ```bash
   python scripts/manage_server.py start
   ```

1. **Start Browser Session Server:**

   ```bash
   python scripts/browser_session_daemon.py start
   ```

1. **Ensure IB TWS/Gateway is running** and connected to MarketBridge.

## Features

- **Automatic form filling** - Scripts fill symbol and instrument type
- **Real-time verification** - Confirms subscriptions are active
- **Error handling** - Provides clear feedback on failures
- **Multiple instrument types** - Supports stocks, futures, options, etc.
- **Session management** - Uses persistent browser sessions

## Troubleshooting

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

## Notes

- Scripts automatically map IB instrument types (STK, FUT) to UI values (stock, future)
- Browser sessions persist across script runs for better performance
- Market data appears in both subscription list and data table when successful
- Futures contracts require specific contract specifications including exchange and expiration month
- The `subscribe_futures.py` script automatically tries multiple contract variations to find valid ones
