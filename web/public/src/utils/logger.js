/**
 * Frontend logging utility with enhanced browser console logging
 * Provides comprehensive logging with timestamps, severity levels, file locations, and line numbers
 */
class Logger {
    constructor() {
        this.logContainer = null;
        this.maxMessages = 100;
        this.messages = [];
        this.logLevels = {
            DEBUG: 0,
            INFO: 1,
            WARNING: 2,
            ERROR: 3,
            SUCCESS: 4
        };
        this.currentLogLevel = this.logLevels.DEBUG; // Default to DEBUG for development
    }

    init(containerId = 'message-log') {
        this.logContainer = document.getElementById(containerId);
        if (!this.logContainer) {
            console.warn(`Logger: Container with ID '${containerId}' not found`);
        }

        // Log initialization with enhanced format
        this.info('Logger initialized', {
            containerId,
            maxMessages: this.maxMessages,
            logLevel: this.getLogLevelName(this.currentLogLevel)
        });
    }

    setLogLevel(level) {
        const levelName = level.toUpperCase();
        if (this.logLevels.hasOwnProperty(levelName)) {
            this.currentLogLevel = this.logLevels[levelName];
            this.info(`Log level changed to ${levelName}`);
        }
    }

    getLogLevelName(levelValue) {
        return Object.keys(this.logLevels).find(key => this.logLevels[key] === levelValue) || 'UNKNOWN';
    }

    formatTimestamp() {
        const now = new Date();
        return now.toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            fractionalSecondDigits: 3
        });
    }

    getCallerInfo() {
        // Extract caller information from stack trace
        const stack = new Error().stack;
        const stackLines = stack.split('\n');

        // Find the first line that's not from logger.js
        for (let i = 3; i < stackLines.length; i++) {
            const line = stackLines[i];
            if (line && !line.includes('logger.js')) {
                // Extract file name and line number from stack trace
                const match = line.match(/([^\/\\]+\.js):(\d+):(\d+)/);
                if (match) {
                    return {
                        file: match[1],
                        line: match[2],
                        column: match[3]
                    };
                }
            }
        }
        return { file: 'unknown', line: '0', column: '0' };
    }

    log(level, message, data = null) {
        // Check if we should log this level
        const levelValue = this.logLevels[level.toUpperCase()] || this.logLevels.INFO;
        if (levelValue < this.currentLogLevel) {
            return;
        }

        const timestamp = this.formatTimestamp();
        const callerInfo = this.getCallerInfo();
        const logEntry = {
            timestamp,
            level,
            message,
            data,
            file: callerInfo.file,
            line: callerInfo.line
        };

        // Add to internal storage
        this.messages.push(logEntry);

        // Keep only the latest messages
        if (this.messages.length > this.maxMessages) {
            this.messages.shift();
        }

        // Enhanced console logging with file location
        const consoleMessage = `[${timestamp}] ${level.toUpperCase()} [${callerInfo.file}:${callerInfo.line}] - ${message}`;

        // Use appropriate console method with styling
        const styles = {
            debug: 'color: #6c757d; font-style: italic;',
            info: 'color: #0066cc;',
            warning: 'color: #ff9800; font-weight: bold;',
            error: 'color: #dc3545; font-weight: bold;',
            success: 'color: #28a745; font-weight: bold;'
        };

        switch (level) {
            case 'error':
                console.error(`%c${consoleMessage}`, styles.error, data);
                if (data && data.stack) {
                    console.error('Stack trace:', data.stack);
                }
                break;
            case 'warning':
                console.warn(`%c${consoleMessage}`, styles.warning, data);
                break;
            case 'info':
                console.info(`%c${consoleMessage}`, styles.info, data);
                break;
            case 'debug':
                console.debug(`%c${consoleMessage}`, styles.debug, data);
                break;
            case 'success':
                console.log(`%c${consoleMessage}`, styles.success, data);
                break;
            default:
                console.log(consoleMessage, data);
        }

        // If data contains variables, log them in a table format for better visibility
        if (data && typeof data === 'object' && Object.keys(data).length > 0) {
            console.table(data);
        }

        // UI logging
        this.displayLog(logEntry);
    }

    displayLog(logEntry) {
        if (!this.logContainer) return;

        const messageElement = document.createElement('div');
        messageElement.className = `log-message log-${logEntry.level}`;

        // Enhanced UI display with file location
        let contentHtml = `
            <span class="log-timestamp">${logEntry.timestamp}</span>
            <span class="log-level ${logEntry.level}">${logEntry.level.toUpperCase()}</span>
            <span class="log-location">[${logEntry.file}:${logEntry.line}]</span>
            <span class="log-content">${this.escapeHtml(logEntry.message)}</span>
        `;

        // Add data display if present
        if (logEntry.data) {
            contentHtml += `<span class="log-data">${this.formatData(logEntry.data)}</span>`;
        }

        messageElement.innerHTML = contentHtml;
        this.logContainer.appendChild(messageElement);

        // Auto-scroll to bottom
        this.logContainer.scrollTop = this.logContainer.scrollHeight;

        // Remove old messages from DOM
        const messages = this.logContainer.querySelectorAll('.log-message');
        if (messages.length > this.maxMessages) {
            messages[0].remove();
        }
    }

    formatData(data) {
        if (data === null || data === undefined) {
            return '';
        }

        if (typeof data === 'object') {
            try {
                return ' | ' + JSON.stringify(data, null, 2);
            } catch (e) {
                return ' | [Complex Object]';
            }
        }

        return ' | ' + String(data);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    debug(message, data = null) {
        this.log('debug', message, data);
    }

    info(message, data = null) {
        this.log('info', message, data);
    }

    error(message, data = null) {
        this.log('error', message, data);
    }

    warning(message, data = null) {
        this.log('warning', message, data);
    }

    success(message, data = null) {
        this.log('success', message, data);
    }

    clear() {
        this.messages = [];
        if (this.logContainer) {
            this.logContainer.innerHTML = '';
        }
    }

    getMessages() {
        return [...this.messages];
    }
}

// Create global logger instance
window.logger = new Logger();
