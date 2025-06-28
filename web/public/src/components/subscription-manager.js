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
        const instrumentTypeSelect = document.getElementById('instrument-type');
        const symbolInput = document.getElementById('symbol');

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

        // Handle instrument type changes to show/hide futures fields
        if (instrumentTypeSelect) {
            instrumentTypeSelect.addEventListener('change', (e) => {
                this.handleInstrumentTypeChange(e.target.value);
            });
        }

        // Handle symbol changes for smart defaults
        if (symbolInput) {
            symbolInput.addEventListener('input', (e) => {
                this.handleSymbolChange(e.target.value);
            });
        }

        // Initialize contract month options
        this.populateContractMonths();

        // Initialize with current selection
        this.handleInstrumentTypeChange(instrumentTypeSelect?.value || 'stock');
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

        // Get futures-specific parameters if applicable
        let futuresParams = {};
        if (instrumentType === 'future') {
            futuresParams = {
                exchange: formData.get('exchange') || 'CME',
                contractMonth: formData.get('contract_month') || '',
                lastTradeDate: formData.get('last_trade_date') || ''
            };
        }

        // Subscribe based on data type
        let success = false;
        switch (dataType) {
            case 'market_data':
                success = window.wsClient.subscribeMarketData(symbol, instrumentType, futuresParams);
                break;
            case 'time_and_sales':
                success = window.wsClient.subscribeTimeAndSales(symbol, instrumentType, futuresParams);
                break;
            case 'bid_ask':
                success = window.wsClient.subscribeBidAsk(symbol, instrumentType, futuresParams);
                break;
        }

        if (success) {
            // Add to subscriptions
            const subscription = {
                symbol,
                instrumentType,
                dataType,
                timestamp: Date.now(),
                reqId: this.nextReqId++,
                futuresParams: instrumentType === 'future' ? futuresParams : null
            };

            this.subscriptions.set(subscriptionKey, subscription);
            this.reqIdToSymbol.set(subscription.reqId, symbol);

            this.renderSubscriptions();

            // Enhanced success message for futures
            let successMsg = `Subscribed to ${symbol} ${dataType}`;
            if (instrumentType === 'future' && futuresParams.exchange) {
                successMsg += ` (${futuresParams.exchange}`;
                if (futuresParams.contractMonth) {
                    successMsg += `, ${futuresParams.contractMonth}`;
                }
                successMsg += ')';
            }
            logger.success(successMsg);

            // Clear form but preserve instrument type selection
            const currentInstrumentType = instrumentType;
            form.reset();
            document.getElementById('instrument-type').value = currentInstrumentType;
            this.handleInstrumentTypeChange(currentInstrumentType);
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
            const futuresParams = subscription.futuresParams || {};

            switch (subscription.dataType) {
                case 'market_data':
                    success = window.wsClient.subscribeMarketData(subscription.symbol, subscription.instrumentType, futuresParams);
                    break;
                case 'time_and_sales':
                    success = window.wsClient.subscribeTimeAndSales(subscription.symbol, subscription.instrumentType, futuresParams);
                    break;
                case 'bid_ask':
                    success = window.wsClient.subscribeBidAsk(subscription.symbol, subscription.instrumentType, futuresParams);
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

    // Handle instrument type changes to show/hide futures fields
    handleInstrumentTypeChange(instrumentType) {
        const futuresDetails = document.getElementById('futures-details');
        const symbolInput = document.getElementById('symbol');

        if (!futuresDetails) return;

        if (instrumentType === 'future') {
            futuresDetails.style.display = 'block';
            // Update symbol placeholder for futures
            if (symbolInput) {
                symbolInput.placeholder = 'MNQ, ES, CL, GC';
            }
        } else {
            futuresDetails.style.display = 'none';
            // Restore original placeholder
            if (symbolInput) {
                symbolInput.placeholder = 'AAPL';
            }
        }
    }

    // Handle symbol changes for smart defaults
    handleSymbolChange(symbol) {
        const instrumentTypeSelect = document.getElementById('instrument-type');
        const exchangeSelect = document.getElementById('exchange');

        if (!symbol || !exchangeSelect) return;

        // Auto-detect exchange based on common futures symbols
        const futuresExchangeMap = {
            'MNQ': 'CME', 'NQ': 'CME', 'ES': 'CME', 'MES': 'CME',
            'YM': 'CBOT', 'MYM': 'CBOT', 'ZB': 'CBOT', 'ZN': 'CBOT', 'ZF': 'CBOT',
            'CL': 'NYMEX', 'NG': 'NYMEX', 'HO': 'NYMEX', 'RB': 'NYMEX',
            'GC': 'COMEX', 'SI': 'COMEX', 'HG': 'COMEX', 'PA': 'NYMEX', 'PL': 'NYMEX'
        };

        const upperSymbol = symbol.toUpperCase();

        // If futures instrument type and we recognize the symbol
        if (instrumentTypeSelect?.value === 'future' && futuresExchangeMap[upperSymbol]) {
            exchangeSelect.value = futuresExchangeMap[upperSymbol];
        }
    }

    // Populate contract month options
    populateContractMonths() {
        const contractMonthSelect = document.getElementById('contract-month');
        if (!contractMonthSelect) return;

        // Clear existing options except the first one (Auto-detect)
        while (contractMonthSelect.children.length > 1) {
            contractMonthSelect.removeChild(contractMonthSelect.lastChild);
        }

        const now = new Date();
        const monthCodes = ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z'];
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

        // Generate next 18 months of contract options
        for (let i = 0; i < 18; i++) {
            const date = new Date(now.getFullYear(), now.getMonth() + i, 1);
            const year = date.getFullYear().toString().slice(-2);
            const monthIndex = date.getMonth();
            const monthCode = monthCodes[monthIndex];
            const monthName = monthNames[monthIndex];

            const contractCode = `${monthCode}${year}`;
            const displayName = `${monthName} ${date.getFullYear()} (${contractCode})`;

            const option = document.createElement('option');
            option.value = contractCode;
            option.textContent = displayName;

            contractMonthSelect.appendChild(option);
        }
    }
}

// Create global subscription manager instance
window.subscriptionManager = new SubscriptionManager();
