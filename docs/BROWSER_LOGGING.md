# MarketBridge Browser-Side Logging Guide

This document provides a comprehensive overview of all browser-side logging mechanisms in MarketBridge, including console logging, UI message logging, and server transmission.

## Table of Contents

1. [Overview](#overview)
1. [Logging Architecture](#logging-architecture)
1. [Console Logging](#console-logging)
1. [Message Log UI Component](#message-log-ui-component)
1. [Server-Side Log Transmission](#server-side-log-transmission)
1. [Component-Specific Logging](#component-specific-logging)
1. [Configuration and Usage](#configuration-and-usage)
1. [Best Practices](#best-practices)
1. [Troubleshooting](#troubleshooting)

## Overview

MarketBridge implements a comprehensive multi-layered logging system that captures, displays, and transmits browser-side events and messages. The system serves three primary purposes:

1. **Development Debugging** - Rich console logging with file locations and variable tracking
1. **User Interface Feedback** - Visual message log for users to see system status
1. **Server-Side Monitoring** - Automatic transmission of browser logs to server filesystem

## Logging Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser Logging Architecture             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User Action/Event → Component Method → Logger Call         │
│                           ↓                                │
│  ┌─────────────────┐    ┌──────────────────┐               │
│  │ Enhanced Logger │    │ Browser Logger   │               │
│  │ (logger.js)     │    │ (browser-logger. │               │
│  │                 │    │ js)              │               │
│  │ • Console Out   │    │ • Console        │               │
│  │ • UI Display    │    │   Interception   │               │
│  │ • File Tracking │    │ • Server Batch   │               │
│  │ • Variable Log  │    │   Transmission   │               │
│  └─────────────────┘    └──────────────────┘               │
│           ↓                       ↓                        │
│  ┌─────────────────┐    ┌──────────────────┐               │
│  │ Message Log UI  │    │ Server Log File  │               │
│  │ (HTML Element)  │    │ (logs/browser.   │               │
│  │                 │    │ log)             │               │
│  └─────────────────┘    └──────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### Logging Flow

1. **Application Event** occurs (user action, server message, error, etc.)
1. **Component Method** calls logger with appropriate level and context
1. **Enhanced Logger** processes the log entry:
   - Extracts caller file and line number from stack trace
   - Formats timestamp and message
   - Outputs to browser console with styling
   - Displays in Message Log UI
1. **Browser Logger** intercepts console output and:
   - Queues logs for batch transmission
   - Sends to server `/api/browser-log` endpoint
   - Stores in server `logs/browser.log` file

## Console Logging

### Enhanced Logger (`src/utils/logger.js`)

The Enhanced Logger provides sophisticated console logging for development and debugging.

#### Features

- **Severity Levels**: DEBUG, INFO, WARNING, ERROR, SUCCESS
- **Timestamps**: Precise timestamps with millisecond accuracy (`HH:MM:SS.mmm`)
- **File Location Tracking**: Automatic extraction of calling file and line number
- **Variable Tracking**: Structured logging of complex objects using `console.table()`
- **Styled Output**: Color-coded console messages for different log levels
- **Log Level Filtering**: Configurable minimum log level

#### Usage Examples

```javascript
// Basic logging
logger.info('WebSocket connection established');
logger.error('Failed to parse message');
logger.warning('Connection unstable');
logger.success('Subscription created successfully');
logger.debug('Processing market data update');

// Logging with data/variables
logger.info('Subscription details', {
    symbol: 'AAPL',
    instrumentType: 'stock',
    dataType: 'realtime',
    timestamp: Date.now()
});

// Error logging with context
logger.error('WebSocket error occurred', {
    error: error.message,
    readyState: ws.readyState,
    url: ws.url,
    reconnectAttempts: this.reconnectAttempts
});
```

#### Console Output Format

```
[14:32:15.123] INFO [websocket-client.js:45] - WebSocket connection established
┌─────────────────┬────────────────────────┐
│     (index)     │         Values         │
├─────────────────┼────────────────────────┤
│       url       │ 'ws://localhost:8765'  │
│ reconnectCount  │           0            │
│   maxRetries    │           5            │
└─────────────────┴────────────────────────┘
```

#### Log Level Configuration

```javascript
// Set minimum log level (filters out lower levels)
logger.setLogLevel('INFO');  // Shows INFO, WARNING, ERROR, SUCCESS
logger.setLogLevel('ERROR'); // Shows only ERROR messages
logger.setLogLevel('DEBUG'); // Shows all messages (default)
```

### Browser Logger (`src/services/browser-logger.js`)

The Browser Logger intercepts all console output and transmits it to the server.

#### Features

- **Console Interception**: Overrides native `console.log`, `console.info`, `console.warn`, `console.error`, `console.debug`
- **Automatic Error Capture**: Captures unhandled errors and promise rejections
- **Batch Transmission**: Queues logs and sends in efficient batches
- **Browser Context**: Includes user agent, URL, viewport, and platform information
- **Retry Logic**: Handles failed transmissions with queue management

#### Browser Logger Output

All console messages are automatically captured and sent to the server without requiring code changes:

```javascript
// These are automatically captured:
console.log('User clicked subscribe button');
console.warn('Market data delay detected');
console.error('Order placement failed');

// Unhandled errors are also captured:
throw new Error('Unexpected condition');
```

## Message Log UI Component

### Purpose and Functionality

The Message Log UI provides a visual display of system messages for end users. Located in the main interface, it shows real-time application status, errors, and important events.

#### HTML Structure

```html
<div class="message-log">
    <h2>Message Log</h2>
    <div id="message-log" class="log-container">
        <!-- System messages and errors displayed here -->
    </div>
</div>
```

#### UI Features

- **Auto-scrolling**: Automatically scrolls to show latest messages
- **Message Limiting**: Maintains only the latest 100 messages
- **Visual Hierarchy**: Color-coded levels with distinct styling
- **Persistent Display**: Messages remain visible until page refresh
- **Rich Formatting**: Displays timestamps, levels, file locations, and data

#### Message Display Format

```
14:32:15.123  INFO  [websocket-client.js:45]  WebSocket connection established
              { url: "ws://localhost:8765", attempts: 1, maxRetries: 5 }

14:32:20.456  ERROR [order-manager.js:89]    Order placement failed
              { symbol: "AAPL", quantity: 100, error: "Insufficient funds" }

14:32:25.789  SUCCESS [subscription-manager.js:123] Subscription created successfully
```

### Key Differences: Console vs Message Log

| Aspect            | Console Logging        | Message Log UI        |
| ----------------- | ---------------------- | --------------------- |
| **Audience**      | Developers/Debug       | End Users             |
| **Persistence**   | Session-only           | Until page refresh    |
| **Styling**       | Browser console colors | Custom CSS styling    |
| **Interactivity** | Collapsible objects    | Static display        |
| **Filtering**     | Browser dev tools      | Application log level |
| **Data Display**  | `console.table()`      | Formatted JSON        |
| **Performance**   | High overhead          | Optimized rendering   |
| **Visibility**    | Dev tools required     | Always visible in UI  |

## Server-Side Log Transmission

### Transmission Process

Browser logs are automatically transmitted to the MarketBridge server for persistent storage and monitoring.

#### Batch Processing

- **Batch Size**: 10 logs per batch or 5-second intervals
- **Endpoint**: `POST /api/browser-log`
- **Format**: JSON with log arrays and metadata
- **Retry Logic**: Failed batches are re-queued for transmission

#### Server Storage

Logs are stored in the server filesystem at `logs/browser.log` with rotating file management:

```
2025-07-01 08:08:47,350 - BROWSER - INFO - [browser-info] - unknown - Browser session started
2025-07-01 08:08:47,350 - BROWSER - INFO - [console.info] - unknown - WebSocket connection established
2025-07-01 08:08:49,467 - BROWSER - WARNING - [console.warn] - unknown - Market data delay detected
2025-07-01 08:08:52,341 - BROWSER - ERROR - [console.error] - unknown - Order placement failed
```

#### Log File Features

- **Rotating Files**: 10MB maximum file size, 5 backup files retained
- **Comprehensive Context**: User agent, URL, timestamp, caller information
- **Log Level Mapping**: Browser levels mapped to Python logging levels
- **Batch Tracking**: Batch IDs for transmission monitoring

## Component-Specific Logging

### WebSocket Client (`src/services/websocket-client.js`)

**Connection Management:**

```javascript
logger.info('Connecting to WebSocket server', { url: this.url });
logger.success('WebSocket connection established');
logger.warning('WebSocket connection lost, attempting reconnect');
logger.error('WebSocket connection failed', { error, attempts: this.reconnectAttempts });
```

**Message Processing:**

```javascript
logger.info('Received message', { type: data.type, timestamp: data.timestamp });
logger.debug('Raw WebSocket data', { dataPreview: event.data.substring(0, 100) });
```

### Subscription Manager (`src/components/subscription-manager.js`)

**Subscription Events:**

```javascript
logger.success('Subscription created successfully', { symbol, instrumentType, dataType });
logger.error('Subscription failed', { symbol, error: response.error });
logger.info('Resubscribing to active subscriptions', { count: this.activeSubscriptions.size });
```

**Form Validation:**

```javascript
logger.warning('Invalid symbol format', { symbol, expectedFormat: 'AAPL' });
logger.error('Required field missing', { field: 'instrumentType' });
```

### Order Manager (`src/components/order-manager.js`)

**Order Lifecycle:**

```javascript
logger.info('Placing order', { symbol, quantity, orderType, side });
logger.success('Order placed successfully', { orderId, symbol, status: 'submitted' });
logger.error('Order placement failed', { symbol, error: response.error });
logger.info('Order status update', { orderId, oldStatus, newStatus, filled: fillQty });
```

### Market Data Display (`src/components/market-data-display.js`)

**Data Processing:**

```javascript
logger.debug('Processing market data', { symbol, messageType, dataFields: Object.keys(data) });
logger.info('New symbol added to display', { symbol, instrumentType });
logger.warning('Malformed market data received', { symbol, missingFields: ['bid', 'ask'] });
```

### Application Level (`src/js/app.js`)

**System Events:**

```javascript
logger.info('Initializing MarketBridge application');
logger.success('MarketBridge application initialized successfully');
logger.info('Page visibility changed', { visibilityState: document.visibilityState });
logger.debug('Keyboard shortcut triggered', { key: event.key, ctrlKey: event.ctrlKey });
```

## Configuration and Usage

### Logger Initialization

```javascript
// Initialize logger (done automatically in app.js)
const logger = new Logger();
logger.init('message-log'); // Connects to Message Log UI element

// Set log level for filtering
logger.setLogLevel('INFO'); // Only INFO and above will be displayed
```

### Browser Logger Configuration

```javascript
// Browser logger starts automatically when browser-logger.js loads
// Access global instance for manual control:
window.browserLogger.enable();  // Enable transmission
window.browserLogger.disable(); // Disable transmission
window.browserLogger.flush();   // Force send queued logs
window.browserLogger.getQueueSize(); // Check queue status
```

### Manual Logging

```javascript
// Use browser logger directly for custom logging
browserLogger.logInfo('Custom info message', 'manual-source');
browserLogger.logWarning('Custom warning', 'validation');
browserLogger.logError('Custom error', 'api-failure');
```

### CSS Customization

Customize Message Log appearance in `assets/css/components.css`:

```css
.log-message.log-error {
    border-left: 4px solid #dc2626;
    background-color: #fef2f2;
}

.log-level.error {
    background: #dc2626;
    color: white;
    font-weight: bold;
}
```

## Best Practices

### Logging Guidelines

1. **Use Appropriate Levels**:

   - `DEBUG`: Detailed debugging information
   - `INFO`: General operational messages
   - `WARNING`: Important but non-critical issues
   - `ERROR`: Error conditions that affect functionality
   - `SUCCESS`: Positive confirmations of operations

1. **Include Context**:

   - Always provide relevant variables and state information
   - Include identifiers (symbols, order IDs, user IDs)
   - Log both input parameters and outcomes

1. **Meaningful Messages**:

   - Use clear, descriptive messages
   - Avoid technical jargon in user-facing logs
   - Include action context ("Attempting to...", "Successfully completed...")

1. **Performance Considerations**:

   - Use DEBUG level for high-frequency operations
   - Avoid logging large objects in production
   - Consider log level filtering for performance

### Example: Comprehensive Error Logging

```javascript
async function placeOrder(orderData) {
    logger.info('Starting order placement process', {
        symbol: orderData.symbol,
        quantity: orderData.quantity,
        orderType: orderData.orderType
    });

    try {
        const response = await api.placeOrder(orderData);

        if (response.success) {
            logger.success('Order placed successfully', {
                orderId: response.orderId,
                symbol: orderData.symbol,
                status: response.status,
                timestamp: response.timestamp
            });
            return response;
        } else {
            logger.error('Order placement rejected', {
                symbol: orderData.symbol,
                rejectionReason: response.error,
                errorCode: response.errorCode,
                orderData: orderData
            });
            throw new Error(response.error);
        }
    } catch (error) {
        logger.error('Order placement failed with exception', {
            symbol: orderData.symbol,
            error: error.message,
            stack: error.stack,
            orderData: orderData
        });
        throw error;
    }
}
```

## Troubleshooting

### Common Issues

#### 1. Logs Not Appearing in Message Log UI

**Symptoms**: Console logs work but Message Log UI is empty

**Solutions**:

- Check that logger is initialized: `logger.init('message-log')`
- Verify Message Log container exists in HTML: `<div id="message-log">`
- Check log level filtering: `logger.setLogLevel('DEBUG')`
- Inspect browser console for logger initialization errors

#### 2. Browser Logs Not Reaching Server

**Symptoms**: Console logs visible but not in `logs/browser.log`

**Solutions**:

- Verify browser-logger.js is loaded before other scripts
- Check network tab for failed `/api/browser-log` requests
- Test server endpoint: `curl -X POST http://localhost:8080/api/browser-log`
- Check server logs for browser logger initialization messages

#### 3. Poor Log Performance

**Symptoms**: Browser becomes slow with excessive logging

**Solutions**:

- Increase log level to reduce volume: `logger.setLogLevel('INFO')`
- Reduce browser logger batch size in browser-logger.js
- Avoid logging large objects or high-frequency events
- Use DEBUG level only for development

#### 4. Missing File Location Information

**Symptoms**: Logs show "unknown" for file locations

**Solutions**:

- Verify source maps are available for minified code
- Check that stack traces are not being modified by other tools
- Test with unminified code in development environment

### Debugging Commands

```javascript
// Check logger status
console.log('Logger status:', {
    initialized: !!logger.logContainer,
    currentLevel: logger.getLogLevelName(logger.currentLogLevel),
    messageCount: logger.messages.length
});

// Check browser logger status
console.log('Browser logger status:', {
    enabled: browserLogger.enabled,
    queueSize: browserLogger.getQueueSize(),
    batchSize: browserLogger.batchSize
});

// Test logging pipeline
logger.info('Test message', { testData: 'debugging' });
```

### Log File Monitoring

Monitor server-side logs in real-time:

```bash
# Watch browser logs
tail -f logs/browser.log

# Watch server logs for browser logging activity
tail -f logs/marketbridge.log | grep browser

# Check log file sizes
ls -lh logs/
```

## Conclusion

MarketBridge's browser-side logging system provides comprehensive visibility into application behavior through multiple complementary mechanisms. The combination of enhanced console logging, visual UI feedback, and server-side persistence ensures that developers, users, and system administrators have access to the information they need for debugging, monitoring, and troubleshooting.

Understanding the differences between console logging (developer-focused), Message Log UI (user-focused), and server transmission (monitoring-focused) is key to effectively using and maintaining the logging system.
