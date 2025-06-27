/**
 * Main Application
 * Coordinates all components and handles WebSocket events
 */
class MarketBridgeApp {
    constructor() {
        this.isInitialized = false;
        this.init();
    }

    async init() {
        try {
            logger.info('Initializing MarketBridge application...');

            // Initialize logger UI
            logger.init('message-log');

            // Setup WebSocket event handlers
            this.setupWebSocketHandlers();

            // Setup application event handlers
            this.setupAppHandlers();

            // Connect to WebSocket server
            this.connectToServer();

            this.isInitialized = true;
            logger.success('MarketBridge application initialized successfully');

        } catch (error) {
            logger.error('Failed to initialize application', error);
        }
    }

    setupWebSocketHandlers() {
        // Connection events
        window.wsClient.onConnect = (event) => {
            logger.success('Connected to MarketBridge server');

            // Resubscribe to active subscriptions if any
            if (window.subscriptionManager) {
                window.subscriptionManager.resubscribeAll();
            }
        };

        window.wsClient.onDisconnect = (event) => {
            if (event.code === 1000) {
                logger.info('Disconnected from server (normal closure)');
            } else {
                logger.warning(`Disconnected from server: ${event.code} - ${event.reason}`);
            }
        };

        window.wsClient.onError = (event) => {
            logger.error('WebSocket connection error occurred');
        };

        // Message handling
        window.wsClient.onMessage = (message) => {
            this.handleServerMessage(message);
        };
    }

    handleServerMessage(message) {
        try {
            switch (message.type) {
                case 'connection_status':
                    this.handleConnectionStatus(message);
                    break;

                case 'market_data':
                case 'time_and_sales':
                case 'bid_ask_tick':
                    if (window.marketDataDisplay) {
                        window.marketDataDisplay.updateData(message);
                    }
                    break;

                case 'order_status':
                    if (window.orderManager) {
                        window.orderManager.updateOrderStatus(message);
                    }
                    break;

                case 'contract_details':
                    this.handleContractDetails(message);
                    break;

                case 'contract_details_end':
                    logger.info(`Contract details request ${message.req_id} completed`);
                    break;

                case 'error':
                    this.handleServerError(message);
                    break;

                default:
                    logger.warning(`Unknown message type: ${message.type}`, message);
            }
        } catch (error) {
            logger.error('Error handling server message', { error, message });
        }
    }

    handleConnectionStatus(message) {
        if (message.status === 'connected') {
            logger.success(`IB connection established. Next order ID: ${message.next_order_id}`);
        } else {
            logger.info(`IB connection status: ${message.status}`);
        }
    }

    handleContractDetails(message) {
        const contract = message.contract;
        logger.info(`Contract details for ${contract.symbol}: ${message.market_name}`);

        // Could display contract details in a modal or dedicated section
        // For now, just log the information
        const details = [
            `Symbol: ${contract.symbol}`,
            `Exchange: ${contract.exchange}`,
            `Currency: ${contract.currency}`,
            `Market: ${message.market_name}`,
            `Min Tick: ${message.min_tick}`
        ];

        logger.info(`Contract Details:\n${details.join('\n')}`);
    }

    handleServerError(message) {
        const severity = message.severity || 'ERROR';
        const errorMsg = `${message.error_string} (Code: ${message.error_code})`;

        switch (severity) {
            case 'ERROR':
                logger.error(errorMsg);
                break;
            case 'WARNING':
                logger.warning(errorMsg);
                break;
            case 'INFO':
                logger.info(errorMsg);
                break;
            default:
                logger.error(errorMsg);
        }
    }

    setupAppHandlers() {
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                logger.info('Application hidden - reducing update frequency');
            } else {
                logger.info('Application visible - resuming normal updates');
            }
        });

        // Handle beforeunload to cleanup connections
        window.addEventListener('beforeunload', () => {
            if (window.wsClient && window.wsClient.isConnected) {
                window.wsClient.disconnect();
            }
        });

        // Setup keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K to clear logs
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                logger.clear();
                logger.info('Logs cleared');
            }

            // Ctrl/Cmd + R to reconnect (prevent default refresh)
            if ((e.ctrlKey || e.metaKey) && e.key === 'r' && e.shiftKey) {
                e.preventDefault();
                this.reconnectToServer();
            }
        });

        // Setup periodic cleanup
        setInterval(() => {
            if (window.orderManager) {
                window.orderManager.cleanup();
            }
        }, 60000); // Every minute
    }

    connectToServer() {
        logger.info('Connecting to MarketBridge server...');
        window.wsClient.connect();
    }

    reconnectToServer() {
        logger.info('Reconnecting to server...');
        window.wsClient.disconnect();
        setTimeout(() => {
            window.wsClient.connect();
        }, 1000);
    }

    // Utility methods for manual testing/debugging
    getConnectionStatus() {
        return {
            connected: window.wsClient.isConnected,
            connecting: window.wsClient.isConnecting,
            reconnectAttempts: window.wsClient.reconnectAttempts
        };
    }

    getApplicationState() {
        return {
            initialized: this.isInitialized,
            connection: this.getConnectionStatus(),
            subscriptions: window.subscriptionManager ? window.subscriptionManager.getAllSubscriptions() : new Map(),
            orders: window.orderManager ? window.orderManager.getAllOrders() : new Map(),
            marketData: window.marketDataDisplay ? window.marketDataDisplay.getAllData() : new Map()
        };
    }

    // Development helpers
    simulateMarketData(symbol = 'TEST', count = 10) {
        if (!window.wsClient.isConnected) {
            logger.error('Not connected to server');
            return;
        }

        for (let i = 0; i < count; i++) {
            setTimeout(() => {
                const message = {
                    type: 'market_data',
                    data_type: 'price',
                    req_id: 999,
                    tick_type: 'last',
                    tick_type_code: 4,
                    price: 100 + (Math.random() * 10 - 5),
                    timestamp: Date.now() / 1000
                };

                // Manually inject the message
                if (window.marketDataDisplay) {
                    window.marketDataDisplay.updateData({...message, symbol});
                }
            }, i * 100);
        }
    }

    clearAllData() {
        if (window.subscriptionManager) {
            window.subscriptionManager.clear();
        }
        if (window.orderManager) {
            window.orderManager.clear();
        }
        if (window.marketDataDisplay) {
            window.marketDataDisplay.clear();
        }
        logger.clear();
        logger.info('All application data cleared');
    }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new MarketBridgeApp();
});

// Make app available globally for debugging
window.MarketBridgeApp = MarketBridgeApp;
