# Browser Logging Quick Reference

## Logging Methods

### Enhanced Logger (UI + Console)

```javascript
// Basic logging
logger.info('Message');
logger.warning('Warning message');
logger.error('Error message');
logger.success('Success message');
logger.debug('Debug message');

// Logging with data
logger.info('Event occurred', {
    symbol: 'AAPL',
    price: 150.25,
    timestamp: Date.now()
});
```

### Browser Logger (Server Transmission)

```javascript
// Direct browser logger methods
browserLogger.logInfo('Info to server', 'source-id');
browserLogger.logWarning('Warning to server', 'validation');
browserLogger.logError('Error to server', 'api-failure');
browserLogger.logDebug('Debug to server', 'performance');

// Control browser logger
browserLogger.enable();   // Start transmission
browserLogger.disable();  // Stop transmission
browserLogger.flush();    // Send queued logs immediately
```

## Configuration

### Set Log Levels

```javascript
logger.setLogLevel('DEBUG');   // Show all logs
logger.setLogLevel('INFO');    // Show INFO, WARNING, ERROR, SUCCESS
logger.setLogLevel('WARNING'); // Show WARNING, ERROR
logger.setLogLevel('ERROR');   // Show ERROR only
```

### Initialize Logger

```javascript
const logger = new Logger();
logger.init('message-log'); // Connect to UI element
```

## Log Locations

### Console Output

- **Browser Dev Tools Console** - Styled, color-coded messages with file locations
- **Format**: `[14:32:15.123] INFO [file.js:45] - Message`

### Message Log UI

- **HTML Element**: `<div id="message-log">` in main interface
- **User-visible** logs with timestamps and context
- **Auto-scrolling** with 100 message limit

### Server Log File

- **File**: `logs/browser.log`
- **Format**: `2025-07-01 08:08:47,350 - BROWSER - INFO - [source] - caller - Message`
- **Automatic** transmission in batches

## Best Practices

### Logging Levels

- **DEBUG**: High-frequency, detailed debugging info
- **INFO**: General operational messages, status updates
- **WARNING**: Important non-critical issues, degraded performance
- **ERROR**: Failures that affect functionality
- **SUCCESS**: Positive confirmations, completed operations

### Include Context

```javascript
// Good: Provides context and variables
logger.error('WebSocket connection failed', {
    url: this.url,
    readyState: ws.readyState,
    reconnectAttempts: this.reconnectAttempts,
    error: error.message
});

// Poor: Minimal context
logger.error('Connection failed');
```

### Performance Considerations

```javascript
// Use DEBUG for high-frequency logs
logger.debug('Processing tick data', { symbol, price });

// Filter logs in production
if (environment === 'development') {
    logger.setLogLevel('DEBUG');
} else {
    logger.setLogLevel('INFO');
}
```

## Component Examples

### WebSocket Events

```javascript
logger.info('Connecting to WebSocket server', { url: this.url });
logger.success('WebSocket connection established');
logger.warning('Connection unstable, reconnecting');
logger.error('WebSocket error', { error: event.error, readyState: ws.readyState });
```

### Order Management

```javascript
logger.info('Placing order', { symbol, quantity, orderType, side });
logger.success('Order placed', { orderId, status: 'submitted' });
logger.error('Order failed', { symbol, error: response.error });
```

### Market Data

```javascript
logger.debug('Market data update', { symbol, bid, ask, timestamp });
logger.info('New subscription', { symbol, instrumentType });
logger.warning('Data delay detected', { symbol, delayMs: 5000 });
```

## Monitoring

### Check Status

```javascript
// Logger status
console.log({
    initialized: !!logger.logContainer,
    level: logger.getLogLevelName(logger.currentLogLevel),
    messageCount: logger.messages.length
});

// Browser logger status
console.log({
    enabled: browserLogger.enabled,
    queueSize: browserLogger.getQueueSize()
});
```

### Watch Server Logs

```bash
# Real-time browser logs
tail -f logs/browser.log

# Filter by level
tail -f logs/browser.log | grep ERROR

# Server logging activity
tail -f logs/marketbridge.log | grep browser
```

## Troubleshooting

### Common Issues

**Logs not in UI**: Check `logger.init('message-log')` called
**Logs not reaching server**: Verify `browser-logger.js` loaded first
**Performance issues**: Increase log level, reduce DEBUG usage
**Missing file info**: Check source maps, use unminified code

### Debug Commands

```javascript
// Test logging pipeline
logger.info('Test message', { testData: Date.now() });

// Force log transmission
browserLogger.flush();

// Check element exists
console.log('Log container:', document.getElementById('message-log'));
```
