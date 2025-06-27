/**
 * Frontend logging utility
 */
class Logger {
    constructor() {
        this.logContainer = null;
        this.maxMessages = 100;
        this.messages = [];
    }

    init(containerId = 'message-log') {
        this.logContainer = document.getElementById(containerId);
        if (!this.logContainer) {
            console.warn(`Logger: Container with ID '${containerId}' not found`);
        }
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

    log(level, message, data = null) {
        const timestamp = this.formatTimestamp();
        const logEntry = {
            timestamp,
            level,
            message,
            data
        };

        // Add to internal storage
        this.messages.push(logEntry);

        // Keep only the latest messages
        if (this.messages.length > this.maxMessages) {
            this.messages.shift();
        }

        // Console logging
        const consoleMessage = `[${timestamp}] ${level.toUpperCase()}: ${message}`;
        switch (level) {
            case 'error':
                console.error(consoleMessage, data);
                break;
            case 'warning':
                console.warn(consoleMessage, data);
                break;
            case 'info':
                console.info(consoleMessage, data);
                break;
            default:
                console.log(consoleMessage, data);
        }

        // UI logging
        this.displayLog(logEntry);
    }

    displayLog(logEntry) {
        if (!this.logContainer) return;

        const messageElement = document.createElement('div');
        messageElement.className = 'log-message';

        messageElement.innerHTML = `
            <span class="log-timestamp">${logEntry.timestamp}</span>
            <span class="log-level ${logEntry.level}">${logEntry.level.toUpperCase()}</span>
            <span class="log-content">${this.escapeHtml(logEntry.message)}</span>
        `;

        this.logContainer.appendChild(messageElement);

        // Auto-scroll to bottom
        this.logContainer.scrollTop = this.logContainer.scrollHeight;

        // Remove old messages from DOM
        const messages = this.logContainer.querySelectorAll('.log-message');
        if (messages.length > this.maxMessages) {
            messages[0].remove();
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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
