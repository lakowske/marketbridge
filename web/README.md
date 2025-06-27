# MarketBridge Web Frontend

A real-time market data and trading interface that connects to the MarketBridge WebSocket backend.

## Features

- **Real-time Market Data**: Live prices, bid/ask spreads, and volume data
- **Multiple Data Types**: Level 1 market data, time & sales, and bid/ask ticks
- **Order Management**: Place, track, and cancel orders with real-time status updates
- **Multi-Instrument Support**: Stocks, options, futures, forex, indices, and crypto
- **WebSocket Connection**: Persistent connection with automatic reconnection
- **Responsive Design**: Works on desktop and mobile devices

## Project Structure

```
web/
├── public/
│   ├── index.html              # Main HTML file
│   └── assets/
│       └── css/
│           ├── main.css        # Main stylesheet
│           └── components.css  # Component-specific styles
├── src/
│   ├── js/
│   │   └── app.js             # Main application logic
│   ├── components/
│   │   ├── market-data-display.js    # Market data table component
│   │   ├── subscription-manager.js   # Subscription management
│   │   └── order-manager.js          # Order placement and tracking
│   ├── services/
│   │   └── websocket-client.js       # WebSocket client service
│   └── utils/
│       └── logger.js                 # Logging utility
└── README.md
```

## Getting Started

### Prerequisites

- MarketBridge backend server running on port 8765
- Modern web browser with WebSocket support

### Running the Frontend

1. **Simple HTTP Server** (recommended for development):

   ```bash
   cd web/public
   python -m http.server 8080
   ```

   Then open http://localhost:8080

1. **Or use any static file server**:

   ```bash
   # Using Node.js serve
   npx serve public -l 8080

   # Using Python 3
   cd public && python -m http.server 8080

   # Using PHP
   cd public && php -S localhost:8080
   ```

### Configuration

The WebSocket connection URL can be modified in `src/services/websocket-client.js`:

```javascript
// Default connection
const wsClient = new WebSocketClient('ws://localhost:8765');

// For different host/port
const wsClient = new WebSocketClient('ws://your-server:8765');
```

## Usage

### Market Data Subscriptions

1. **Subscribe to Market Data**:

   - Enter symbol (e.g., AAPL, MSFT)
   - Select instrument type (stock, option, future, etc.)
   - Choose data type (Market Data, Time & Sales, Bid/Ask)
   - Click "Subscribe"

1. **View Real-time Data**:

   - Market data appears in the data grid
   - Prices flash green/red on changes
   - Volume and timestamp information included

1. **Unsubscribe**:

   - Select subscriptions in the list
   - Click "Unsubscribe" button

### Order Management

1. **Place Orders**:

   - Enter symbol and quantity
   - Select Buy/Sell action
   - Choose order type (Market, Limit, Stop)
   - Enter price for limit/stop orders
   - Click "Place Order"

1. **Track Orders**:

   - Order status updates in real-time
   - Shows fill information and timestamps
   - Cancel pending orders if needed

### Connection Status

- **Green**: Connected to backend
- **Yellow (pulsing)**: Connecting/reconnecting
- **Red**: Disconnected

## API Integration

The frontend connects to the MarketBridge backend via WebSocket and supports all backend commands:

### Subscription Commands

```javascript
// Market data subscription
{
  "command": "subscribe_market_data",
  "symbol": "AAPL",
  "instrument_type": "stock",
  "exchange": "SMART",
  "currency": "USD"
}

// Time and sales
{
  "command": "subscribe_time_and_sales",
  "symbol": "AAPL",
  "instrument_type": "stock"
}

// Bid/ask ticks
{
  "command": "subscribe_bid_ask",
  "symbol": "AAPL",
  "instrument_type": "stock"
}
```

### Order Commands

```javascript
// Place order
{
  "command": "place_order",
  "symbol": "AAPL",
  "action": "BUY",
  "quantity": 100,
  "order_type": "MKT",
  "instrument_type": "stock"
}

// Cancel order
{
  "command": "cancel_order",
  "order_id": 1001
}
```

## Message Types

The frontend handles these message types from the backend:

- `connection_status`: IB connection status
- `market_data`: Level 1 market data updates
- `time_and_sales`: Trade tick data
- `bid_ask_tick`: Bid/ask updates
- `order_status`: Order status changes
- `contract_details`: Instrument contract information
- `error`: Error messages and warnings

## Development

### Keyboard Shortcuts

- **Ctrl/Cmd + K**: Clear message logs
- **Ctrl/Cmd + Shift + R**: Force reconnect to server

### Debugging

The application exposes several objects for debugging:

```javascript
// Application state
console.log(app.getApplicationState());

// Connection status
console.log(app.getConnectionStatus());

// Simulate market data (for testing)
app.simulateMarketData('TEST', 10);

// Clear all data
app.clearAllData();
```

### Browser Console

All components are available in the browser console:

- `window.app` - Main application
- `window.wsClient` - WebSocket client
- `window.logger` - Logger utility
- `window.marketDataDisplay` - Market data component
- `window.subscriptionManager` - Subscription management
- `window.orderManager` - Order management

## Browser Compatibility

- Chrome 58+
- Firefox 55+
- Safari 11+
- Edge 79+

## Security Considerations

- Uses WebSocket connections (ws://) - upgrade to WSS for production
- Input validation on all user inputs
- No sensitive data stored in localStorage
- CORS headers may need configuration for production deployment

## Performance

- Efficient DOM updates using document fragments
- Message throttling for high-frequency updates
- Automatic cleanup of old orders and logs
- Responsive design with CSS Grid and Flexbox

## Troubleshooting

### Connection Issues

1. Verify backend server is running on port 8765
1. Check browser console for WebSocket errors
1. Ensure no firewall blocking connections
1. Try manual reconnection with Ctrl+Shift+R

### Market Data Not Updating

1. Check subscription status in Active Subscriptions
1. Verify IB connection status in backend logs
1. Check for error messages in Message Log
1. Try unsubscribing and re-subscribing

### Order Issues

1. Verify valid order ID is available (check connection status)
1. Check order requirements (price for limit orders)
1. Monitor order status updates in Order Status section
1. Check backend logs for IB API errors
