/**
 * WebSocket client for connecting to MarketBridge backend
 */
class WebSocketClient {
    constructor(url = 'ws://localhost:8765') {
        this.url = url;
        this.ws = null;
        this.isConnecting = false;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 1000; // Start with 1 second
        this.maxReconnectInterval = 30000; // Max 30 seconds
        this.reconnectTimer = null;

        // Event handlers
        this.onConnect = null;
        this.onDisconnect = null;
        this.onMessage = null;
        this.onError = null;

        this.messageQueue = [];
        this.pendingSubscriptions = new Map();
    }

    connect() {
        if (this.isConnecting || this.isConnected) {
            return;
        }

        this.isConnecting = true;
        this.updateConnectionStatus('connecting');

        try {
            logger.info(`Connecting to WebSocket server: ${this.url}`);
            this.ws = new WebSocket(this.url);

            this.ws.onopen = this.handleOpen.bind(this);
            this.ws.onmessage = this.handleMessage.bind(this);
            this.ws.onclose = this.handleClose.bind(this);
            this.ws.onerror = this.handleError.bind(this);

        } catch (error) {
            logger.error('Failed to create WebSocket connection', error);
            this.isConnecting = false;
            this.scheduleReconnect();
        }
    }

    disconnect() {
        logger.info('Disconnecting from WebSocket server');
        this.clearReconnectTimer();
        this.reconnectAttempts = 0;

        if (this.ws) {
            this.ws.close(1000, 'Client initiated disconnect');
        }
    }

    handleOpen(event) {
        logger.success('WebSocket connection established');
        this.isConnecting = false;
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.reconnectInterval = 1000; // Reset interval

        this.updateConnectionStatus('connected');

        // Process queued messages
        this.processMessageQueue();

        if (this.onConnect) {
            this.onConnect(event);
        }
    }

    handleMessage(event) {
        try {
            const message = JSON.parse(event.data);
            logger.info(`Received message: ${message.type}`, message);

            if (this.onMessage) {
                this.onMessage(message);
            }

        } catch (error) {
            logger.error('Failed to parse WebSocket message', { error, data: event.data });
        }
    }

    handleClose(event) {
        logger.warning(`WebSocket connection closed: ${event.code} - ${event.reason}`);
        this.isConnecting = false;
        this.isConnected = false;

        this.updateConnectionStatus('disconnected');

        if (this.onDisconnect) {
            this.onDisconnect(event);
        }

        // Attempt reconnection if it wasn't a clean close
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
        }
    }

    handleError(event) {
        logger.error('WebSocket error occurred', event);
        this.isConnecting = false;

        if (this.onError) {
            this.onError(event);
        }
    }

    scheduleReconnect() {
        this.clearReconnectTimer();

        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            logger.error('Max reconnection attempts reached. Giving up.');
            this.updateConnectionStatus('failed');
            return;
        }

        this.reconnectAttempts++;
        const delay = Math.min(
            this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1),
            this.maxReconnectInterval
        );

        logger.info(`Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);

        this.reconnectTimer = setTimeout(() => {
            this.connect();
        }, delay);
    }

    clearReconnectTimer() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
    }

    send(message) {
        if (!this.isConnected) {
            logger.warning('WebSocket not connected, queuing message', message);
            this.messageQueue.push(message);
            return false;
        }

        try {
            const messageStr = JSON.stringify(message);
            this.ws.send(messageStr);
            logger.info(`Sent message: ${message.command || message.type}`, message);
            return true;
        } catch (error) {
            logger.error('Failed to send WebSocket message', { error, message });
            return false;
        }
    }

    processMessageQueue() {
        while (this.messageQueue.length > 0 && this.isConnected) {
            const message = this.messageQueue.shift();
            this.send(message);
        }
    }

    updateConnectionStatus(status) {
        const statusIndicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');

        if (statusIndicator && statusText) {
            // Remove all status classes
            statusIndicator.className = 'status-indicator';

            switch (status) {
                case 'connected':
                    statusIndicator.classList.add('connected');
                    statusText.textContent = 'Connected';
                    break;
                case 'connecting':
                    statusIndicator.classList.add('connecting');
                    statusText.textContent = 'Connecting...';
                    break;
                case 'disconnected':
                    statusText.textContent = 'Disconnected';
                    break;
                case 'failed':
                    statusText.textContent = 'Connection Failed';
                    break;
            }
        }
    }

    // Market data subscription methods
    subscribeMarketData(symbol, instrumentType = 'stock', exchange = 'SMART', currency = 'USD') {
        const message = {
            command: 'subscribe_market_data',
            symbol: symbol.toUpperCase(),
            instrument_type: instrumentType,
            exchange,
            currency
        };

        const subscriptionKey = `${symbol}_${instrumentType}_market_data`;
        this.pendingSubscriptions.set(subscriptionKey, message);

        return this.send(message);
    }

    subscribeTimeAndSales(symbol, instrumentType = 'stock') {
        const message = {
            command: 'subscribe_time_and_sales',
            symbol: symbol.toUpperCase(),
            instrument_type: instrumentType
        };

        const subscriptionKey = `${symbol}_${instrumentType}_time_and_sales`;
        this.pendingSubscriptions.set(subscriptionKey, message);

        return this.send(message);
    }

    subscribeBidAsk(symbol, instrumentType = 'stock') {
        const message = {
            command: 'subscribe_bid_ask',
            symbol: symbol.toUpperCase(),
            instrument_type: instrumentType
        };

        const subscriptionKey = `${symbol}_${instrumentType}_bid_ask`;
        this.pendingSubscriptions.set(subscriptionKey, message);

        return this.send(message);
    }

    unsubscribeMarketData(symbol) {
        const message = {
            command: 'unsubscribe_market_data',
            symbol: symbol.toUpperCase()
        };

        // Remove from pending subscriptions
        const keysToRemove = [];
        for (const [key, value] of this.pendingSubscriptions) {
            if (value.symbol === symbol.toUpperCase()) {
                keysToRemove.push(key);
            }
        }
        keysToRemove.forEach(key => this.pendingSubscriptions.delete(key));

        return this.send(message);
    }

    // Order management methods
    placeOrder(symbol, action, quantity, orderType = 'MKT', price = null, instrumentType = 'stock') {
        const message = {
            command: 'place_order',
            symbol: symbol.toUpperCase(),
            action: action.toUpperCase(),
            quantity: parseInt(quantity),
            order_type: orderType.toUpperCase(),
            instrument_type: instrumentType
        };

        if (price && (orderType === 'LMT' || orderType === 'STP')) {
            message.price = parseFloat(price);
        }

        return this.send(message);
    }

    cancelOrder(orderId) {
        const message = {
            command: 'cancel_order',
            order_id: parseInt(orderId)
        };

        return this.send(message);
    }

    getContractDetails(symbol, instrumentType = 'stock') {
        const message = {
            command: 'get_contract_details',
            symbol: symbol.toUpperCase(),
            instrument_type: instrumentType
        };

        return this.send(message);
    }
}

// Create global WebSocket client instance
window.wsClient = new WebSocketClient();
