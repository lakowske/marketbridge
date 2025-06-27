/**
 * Subscription Manager Component
 * Handles subscription UI and tracks active subscriptions
 */
class SubscriptionManager {
    constructor(containerId = 'subscriptions-list') {
        this.container = document.getElementById(containerId);
        this.subscriptions = new Map(); // key -> subscription data
        this.reqIdToSymbol = new Map(); // req_id -> symbol for message routing
        this.nextReqId = 1;

        this.init();
    }

    init() {
        if (!this.container) {
            logger.error('Subscription container not found');
            return;
        }

        this.showEmptyState();
        this.setupFormHandlers();
    }

    setupFormHandlers() {
        const form = document.getElementById('subscription-form');
        const subscribeBtn = document.getElementById('subscribe-btn');
        const unsubscribeBtn = document.getElementById('unsubscribe-btn');

        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleSubscribe();
            });
        }

        if (unsubscribeBtn) {
            unsubscribeBtn.addEventListener('click', () => {
                this.handleUnsubscribeSelected();
            });
        }
    }

    handleSubscribe() {
        const form = document.getElementById('subscription-form');
        const formData = new FormData(form);

        const symbol = formData.get('symbol')?.toUpperCase().trim();
        const instrumentType = formData.get('instrument_type');
        const dataType = formData.get('data_type');

        if (!symbol || !instrumentType || !dataType) {
            logger.error('Please fill in all required fields');
            return;
        }

        // Check if already subscribed
        const subscriptionKey = `${symbol}_${instrumentType}_${dataType}`;
        if (this.subscriptions.has(subscriptionKey)) {
            logger.warning(`Already subscribed to ${symbol} ${dataType}`);
            return;
        }

        // Subscribe based on data type
        let success = false;
        switch (dataType) {
            case 'market_data':
                success = window.wsClient.subscribeMarketData(symbol, instrumentType);
                break;
            case 'time_and_sales':
                success = window.wsClient.subscribeTimeAndSales(symbol, instrumentType);
                break;
            case 'bid_ask':
                success = window.wsClient.subscribeBidAsk(symbol, instrumentType);
                break;
        }

        if (success) {
            // Add to subscriptions
            const subscription = {
                symbol,
                instrumentType,
                dataType,
                timestamp: Date.now(),
                reqId: this.nextReqId++
            };

            this.subscriptions.set(subscriptionKey, subscription);
            this.reqIdToSymbol.set(subscription.reqId, symbol);

            this.renderSubscriptions();
            logger.success(`Subscribed to ${symbol} ${dataType}`);

            // Clear form
            form.reset();
        } else {
            logger.error('Failed to subscribe - WebSocket not connected');
        }
    }

    handleUnsubscribeSelected() {
        const selectedCheckboxes = this.container.querySelectorAll('input[type="checkbox"]:checked');

        if (selectedCheckboxes.length === 0) {
            logger.warning('No subscriptions selected for unsubscribe');
            return;
        }

        selectedCheckboxes.forEach(checkbox => {
            const subscriptionKey = checkbox.value;
            this.unsubscribe(subscriptionKey);
        });
    }

    unsubscribe(subscriptionKey) {
        const subscription = this.subscriptions.get(subscriptionKey);
        if (!subscription) return;

        // Send unsubscribe command
        const success = window.wsClient.unsubscribeMarketData(subscription.symbol);

        if (success) {
            this.subscriptions.delete(subscriptionKey);
            this.reqIdToSymbol.delete(subscription.reqId);

            // Remove from market data display
            if (window.marketDataDisplay) {
                window.marketDataDisplay.removeSymbol(subscription.symbol);
            }

            this.renderSubscriptions();
            logger.success(`Unsubscribed from ${subscription.symbol} ${subscription.dataType}`);
        } else {
            logger.error('Failed to unsubscribe - WebSocket not connected');
        }
    }

    renderSubscriptions() {
        if (this.subscriptions.size === 0) {
            this.showEmptyState();
            return;
        }

        this.container.innerHTML = '';

        for (const [key, subscription] of this.subscriptions) {
            const item = document.createElement('div');
            item.className = 'subscription-item';

            item.innerHTML = `
                <div class="subscription-info">
                    <div class="subscription-symbol">${subscription.symbol}</div>
                    <div class="subscription-details">
                        ${subscription.instrumentType} • ${subscription.dataType.replace('_', ' ')}
                    </div>
                </div>
                <div class="subscription-actions">
                    <input type="checkbox" value="${key}" id="sub-${key}">
                    <label for="sub-${key}" class="sr-only">Select ${subscription.symbol}</label>
                    <button class="btn-small btn-unsubscribe" onclick="subscriptionManager.unsubscribe('${key}')">
                        Unsubscribe
                    </button>
                </div>
            `;

            this.container.appendChild(item);
        }
    }

    showEmptyState() {
        this.container.innerHTML = `
            <div class="empty-state">
                No active subscriptions.<br>
                Use the form above to subscribe to market data.
            </div>
        `;
    }

    getSymbolByReqId(reqId) {
        return this.reqIdToSymbol.get(reqId);
    }

    getSubscription(symbol, dataType) {
        for (const [key, subscription] of this.subscriptions) {
            if (subscription.symbol === symbol && subscription.dataType === dataType) {
                return subscription;
            }
        }
        return null;
    }

    getAllSubscriptions() {
        return new Map(this.subscriptions);
    }

    isSubscribed(symbol, instrumentType, dataType) {
        const key = `${symbol}_${instrumentType}_${dataType}`;
        return this.subscriptions.has(key);
    }

    clear() {
        // Unsubscribe from all
        for (const [key] of this.subscriptions) {
            this.unsubscribe(key);
        }
    }

    // Handle reconnection - resubscribe to all active subscriptions
    resubscribeAll() {
        logger.info('Resubscribing to all active subscriptions...');

        const currentSubscriptions = new Map(this.subscriptions);
        this.subscriptions.clear();
        this.reqIdToSymbol.clear();

        for (const [key, subscription] of currentSubscriptions) {
            // Recreate subscription
            let success = false;
            switch (subscription.dataType) {
                case 'market_data':
                    success = window.wsClient.subscribeMarketData(subscription.symbol, subscription.instrumentType);
                    break;
                case 'time_and_sales':
                    success = window.wsClient.subscribeTimeAndSales(subscription.symbol, subscription.instrumentType);
                    break;
                case 'bid_ask':
                    success = window.wsClient.subscribeBidAsk(subscription.symbol, subscription.instrumentType);
                    break;
            }

            if (success) {
                subscription.reqId = this.nextReqId++;
                this.subscriptions.set(key, subscription);
                this.reqIdToSymbol.set(subscription.reqId, subscription.symbol);
                logger.info(`Resubscribed to ${subscription.symbol} ${subscription.dataType}`);
            } else {
                logger.error(`Failed to resubscribe to ${subscription.symbol} ${subscription.dataType}`);
            }
        }

        this.renderSubscriptions();
    }
}

// Create global subscription manager instance
window.subscriptionManager = new SubscriptionManager();
