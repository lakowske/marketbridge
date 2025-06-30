/**
 * Market Data Display Component
 * Handles displaying real-time market data in a table format
 */
class MarketDataDisplay {
    constructor(containerId = 'market-data-grid') {
        this.container = document.getElementById(containerId);
        this.data = new Map(); // symbol -> data object
        this.table = null;
        this.lastPrices = new Map(); // For price change detection

        this.init();
    }

    init() {
        if (!this.container) {
            logger.error('Market data container not found');
            return;
        }

        this.createTable();
        this.showEmptyState();
    }

    createTable() {
        this.table = document.createElement('table');
        this.table.className = 'market-data-table';

        // Create header
        const header = document.createElement('thead');
        header.innerHTML = `
            <tr>
                <th>Symbol</th>
                <th>Last</th>
                <th>Bid</th>
                <th>Ask</th>
                <th>Bid Size</th>
                <th>Ask Size</th>
                <th>Change</th>
                <th>Volume</th>
                <th>Time</th>
            </tr>
        `;

        this.table.appendChild(header);

        // Create body
        this.tbody = document.createElement('tbody');
        this.table.appendChild(this.tbody);

        this.container.appendChild(this.table);
    }

    showEmptyState() {
        if (this.data.size === 0) {
            this.tbody.innerHTML = `
                <tr>
                    <td colspan="9" class="empty-state">
                        No market data subscriptions active.<br>
                        Subscribe to instruments to see live data here.
                    </td>
                </tr>
            `;
        }
    }

    updateData(message) {
        const symbol = this.getSymbolFromMessage(message);
        if (!symbol) return;

        // Initialize data for symbol if not exists
        if (!this.data.has(symbol)) {
            this.data.set(symbol, {
                symbol,
                last: null,
                bid: null,
                ask: null,
                bidSize: null,
                askSize: null,
                volume: null,
                change: null,
                timestamp: null
            });
        }

        const symbolData = this.data.get(symbol);

        // Update based on message type
        switch (message.type) {
            case 'market_data':
                this.handleMarketData(symbolData, message);
                break;
            case 'time_and_sales':
                this.handleTimeAndSales(symbolData, message);
                break;
            case 'bid_ask_tick':
                this.handleBidAskTick(symbolData, message);
                break;
        }

        this.renderRow(symbol);
    }

    getSymbolFromMessage(message) {
        // Try to extract symbol from the message or active requests
        if (message.symbol) {
            return message.symbol;
        }

        // For messages with req_id, look up the symbol
        if (message.req_id && window.subscriptionManager) {
            return window.subscriptionManager.getSymbolByReqId(message.req_id);
        }

        logger.warning('Could not determine symbol from message', message);
        return null;
    }

    handleMarketData(symbolData, message) {
        switch (message.data_type) {
            case 'price':
                switch (message.tick_type) {
                    case 'last':
                        symbolData.last = message.price;
                        break;
                    case 'bid':
                        symbolData.bid = message.price;
                        break;
                    case 'ask':
                        symbolData.ask = message.price;
                        break;
                }
                break;
            case 'size':
                switch (message.tick_type) {
                    case 'bid_size':
                        symbolData.bidSize = message.size;
                        break;
                    case 'ask_size':
                        symbolData.askSize = message.size;
                        break;
                    case 'volume':
                        symbolData.volume = message.size;
                        break;
                }
                break;
        }

        symbolData.timestamp = message.timestamp;
    }

    handleTimeAndSales(symbolData, message) {
        symbolData.last = message.price;
        symbolData.volume = (symbolData.volume || 0) + message.size;
        symbolData.timestamp = message.timestamp;
    }

    handleBidAskTick(symbolData, message) {
        symbolData.bid = message.bid_price;
        symbolData.ask = message.ask_price;
        symbolData.bidSize = message.bid_size;
        symbolData.askSize = message.ask_size;
        symbolData.timestamp = message.timestamp;
    }

    renderRow(symbol) {
        const symbolData = this.data.get(symbol);
        if (!symbolData) return;

        // Remove empty state if present
        if (this.data.size === 1) {
            this.tbody.innerHTML = '';
        }

        let row = this.tbody.querySelector(`tr[data-symbol="${symbol}"]`);

        if (!row) {
            row = document.createElement('tr');
            row.setAttribute('data-symbol', symbol);
            this.tbody.appendChild(row);
        }

        // Calculate price change
        const lastPrice = this.lastPrices.get(symbol);
        let changeClass = '';
        let changeText = '-';

        if (symbolData.last !== null) {
            if (lastPrice !== undefined && lastPrice !== null) {
                const change = symbolData.last - lastPrice;
                if (change > 0) {
                    changeClass = 'price-up';
                    changeText = `+${change.toFixed(2)}`;
                } else if (change < 0) {
                    changeClass = 'price-down';
                    changeText = change.toFixed(2);
                } else {
                    changeText = '0.00';
                }
            }
            this.lastPrices.set(symbol, symbolData.last);
        }

        // Format timestamp
        const timeStr = symbolData.timestamp ?
            new Date(symbolData.timestamp * 1000).toLocaleTimeString() : '-';

        row.innerHTML = `
            <td class="symbol-cell">${symbolData.symbol}</td>
            <td class="price-cell ${symbolData.last !== null ? (changeClass || '') : ''}">${this.formatPrice(symbolData.last)}</td>
            <td class="price-cell">${this.formatPrice(symbolData.bid)}</td>
            <td class="price-cell">${this.formatPrice(symbolData.ask)}</td>
            <td>${this.formatSize(symbolData.bidSize)}</td>
            <td>${this.formatSize(symbolData.askSize)}</td>
            <td class="${changeClass}">${changeText}</td>
            <td>${this.formatSize(symbolData.volume)}</td>
            <td class="time-cell">${timeStr}</td>
        `;

        // Flash effect for price changes
        if (changeClass) {
            setTimeout(() => {
                const priceCell = row.querySelector('.price-cell');
                if (priceCell) {
                    priceCell.classList.remove('price-up', 'price-down');
                }
            }, 500);
        }
    }

    formatPrice(price) {
        if (price === null || price === undefined) return '-';
        return typeof price === 'number' ? price.toFixed(2) : price.toString();
    }

    formatSize(size) {
        if (size === null || size === undefined) return '-';
        return typeof size === 'number' ? size.toLocaleString() : size.toString();
    }

    removeSymbol(symbol) {
        this.data.delete(symbol);
        this.lastPrices.delete(symbol);

        const row = this.tbody.querySelector(`tr[data-symbol="${symbol}"]`);
        if (row) {
            row.remove();
        }

        if (this.data.size === 0) {
            this.showEmptyState();
        }
    }

    clear() {
        this.data.clear();
        this.lastPrices.clear();
        this.showEmptyState();
    }

    getSymbolData(symbol) {
        return this.data.get(symbol);
    }

    getAllData() {
        return new Map(this.data);
    }
}

// Create global market data display instance
window.marketDataDisplay = new MarketDataDisplay();
