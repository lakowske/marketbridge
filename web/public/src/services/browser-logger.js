/**
 * Browser Logger Service
 * Captures browser console messages and sends them to the MarketBridge server
 */

class BrowserLogger {
    constructor() {
        this.serverEndpoint = '/api/browser-log';
        this.enabled = true;
        this.batchSize = 10;
        this.batchTimeout = 5000; // 5 seconds
        this.logQueue = [];
        this.batchTimer = null;

        // Store original console methods
        this.originalConsole = {
            log: console.log.bind(console),
            info: console.info.bind(console),
            warn: console.warn.bind(console),
            error: console.error.bind(console),
            debug: console.debug.bind(console)
        };

        this.init();
    }

    init() {
        // Intercept console methods
        this.interceptConsole();

        // Log browser initialization
        this.logToBrowser('info', 'Browser logger initialized', 'browser-logger');

        // Set up periodic batch sending
        this.startBatchTimer();

        // Listen for page unload to send remaining logs
        window.addEventListener('beforeunload', () => {
            this.sendBatch(true); // Send synchronously
        });

        // Send initial browser info
        this.logBrowserInfo();
    }

    interceptConsole() {
        const self = this;

        // Override console.log
        console.log = function(...args) {
            self.originalConsole.log.apply(console, args);
            self.captureLog('info', args, 'console.log');
        };

        // Override console.info
        console.info = function(...args) {
            self.originalConsole.info.apply(console, args);
            self.captureLog('info', args, 'console.info');
        };

        // Override console.warn
        console.warn = function(...args) {
            self.originalConsole.warn.apply(console, args);
            self.captureLog('warn', args, 'console.warn');
        };

        // Override console.error
        console.error = function(...args) {
            self.originalConsole.error.apply(console, args);
            self.captureLog('error', args, 'console.error');
        };

        // Override console.debug
        console.debug = function(...args) {
            self.originalConsole.debug.apply(console, args);
            self.captureLog('debug', args, 'console.debug');
        };

        // Capture unhandled errors
        window.addEventListener('error', (event) => {
            self.captureLog('error', [
                `Unhandled Error: ${event.message}`,
                `File: ${event.filename}:${event.lineno}:${event.colno}`,
                `Stack: ${event.error?.stack || 'No stack trace'}`
            ], 'window.error');
        });

        // Capture unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            self.captureLog('error', [
                `Unhandled Promise Rejection: ${event.reason}`,
                `Stack: ${event.reason?.stack || 'No stack trace'}`
            ], 'window.unhandledrejection');
        });
    }

    captureLog(level, args, source) {
        if (!this.enabled) return;

        try {
            // Convert arguments to strings
            const message = args.map(arg => {
                if (typeof arg === 'object') {
                    try {
                        return JSON.stringify(arg, null, 2);
                    } catch (e) {
                        return String(arg);
                    }
                }
                return String(arg);
            }).join(' ');

            // Get stack trace to identify calling location
            const stack = new Error().stack;
            const caller = this.extractCaller(stack);

            // Create log entry
            const logEntry = {
                level: level,
                message: message,
                source: source,
                timestamp: new Date().toISOString(),
                caller: caller,
                url: window.location.href,
                userAgent: navigator.userAgent
            };

            // Add to queue
            this.logQueue.push(logEntry);

            // Send batch if queue is full
            if (this.logQueue.length >= this.batchSize) {
                this.sendBatch();
            }

        } catch (error) {
            // Fallback to original console to avoid infinite loops
            this.originalConsole.error('BrowserLogger error:', error);
        }
    }

    extractCaller(stack) {
        try {
            const lines = stack.split('\\n');
            // Skip BrowserLogger methods and find first external caller
            for (let i = 3; i < lines.length; i++) {
                const line = lines[i];
                if (line.includes('.js:') && !line.includes('browser-logger.js')) {
                    // Extract filename and line number
                    const match = line.match(/([^/\\\\]+\\.js):(\\d+):(\\d+)/);
                    if (match) {
                        return `${match[1]}:${match[2]}`;
                    }
                }
            }
            return 'unknown';
        } catch (e) {
            return 'error-extracting-caller';
        }
    }

    logToBrowser(level, message, source = 'browser-logger') {
        // Log directly to browser without server transmission to avoid loops
        const timestamp = new Date().toISOString();
        const formattedMessage = `[${timestamp}] ${level.toUpperCase()} [${source}] ${message}`;

        switch (level) {
            case 'error':
                this.originalConsole.error(formattedMessage);
                break;
            case 'warn':
                this.originalConsole.warn(formattedMessage);
                break;
            case 'debug':
                this.originalConsole.debug(formattedMessage);
                break;
            default:
                this.originalConsole.info(formattedMessage);
        }
    }

    logBrowserInfo() {
        const info = {
            userAgent: navigator.userAgent,
            url: window.location.href,
            timestamp: new Date().toISOString(),
            viewport: `${window.innerWidth}x${window.innerHeight}`,
            screen: `${screen.width}x${screen.height}`,
            language: navigator.language,
            platform: navigator.platform,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine
        };

        this.captureLog('info', [`Browser session started with info:`, info], 'browser-info');
    }

    startBatchTimer() {
        if (this.batchTimer) {
            clearTimeout(this.batchTimer);
        }

        this.batchTimer = setTimeout(() => {
            if (this.logQueue.length > 0) {
                this.sendBatch();
            }
            this.startBatchTimer(); // Restart timer
        }, this.batchTimeout);
    }

    async sendBatch(synchronous = false) {
        if (this.logQueue.length === 0) return;

        const batch = [...this.logQueue];
        this.logQueue = [];

        try {
            const payload = {
                logs: batch,
                batchId: Date.now(),
                totalLogs: batch.length
            };

            if (synchronous) {
                // Use sendBeacon for synchronous sending during page unload
                const data = JSON.stringify(payload);
                navigator.sendBeacon(this.serverEndpoint, data);
            } else {
                // Use fetch for normal async sending
                const response = await fetch(this.serverEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();
                this.logToBrowser('debug', `Sent ${batch.length} logs to server (batch ${payload.batchId})`, 'browser-logger');
            }

        } catch (error) {
            // Re-add failed logs to queue for retry
            this.logQueue.unshift(...batch);
            this.logToBrowser('warn', `Failed to send logs to server: ${error.message}`, 'browser-logger');
        }
    }

    // Public methods for manual logging
    logInfo(message, source = 'manual') {
        this.captureLog('info', [message], source);
    }

    logWarning(message, source = 'manual') {
        this.captureLog('warn', [message], source);
    }

    logError(message, source = 'manual') {
        this.captureLog('error', [message], source);
    }

    logDebug(message, source = 'manual') {
        this.captureLog('debug', [message], source);
    }

    // Control methods
    enable() {
        this.enabled = true;
        this.logToBrowser('info', 'Browser logging enabled', 'browser-logger');
    }

    disable() {
        this.enabled = false;
        this.logToBrowser('info', 'Browser logging disabled', 'browser-logger');
    }

    flush() {
        this.sendBatch();
    }

    getQueueSize() {
        return this.logQueue.length;
    }
}

// Initialize browser logger
const browserLogger = new BrowserLogger();

// Make it available globally for debugging
window.browserLogger = browserLogger;
