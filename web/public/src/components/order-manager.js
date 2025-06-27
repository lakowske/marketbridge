/**
 * Order Manager Component
 * Handles order placement UI and tracks order status
 */
class OrderManager {
    constructor(containerId = 'orders-list') {
        this.container = document.getElementById(containerId);
        this.orders = new Map(); // order_id -> order data

        this.init();
    }

    init() {
        if (!this.container) {
            logger.error('Orders container not found');
            return;
        }

        this.showEmptyState();
        this.setupFormHandlers();
    }

    setupFormHandlers() {
        const form = document.getElementById('order-form');
        const orderTypeSelect = document.getElementById('order-type');
        const priceGroup = document.getElementById('price-group');

        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handlePlaceOrder();
            });
        }

        // Show/hide price field based on order type
        if (orderTypeSelect && priceGroup) {
            orderTypeSelect.addEventListener('change', (e) => {
                const orderType = e.target.value;
                if (orderType === 'LMT' || orderType === 'STP') {
                    priceGroup.style.display = 'block';
                    document.getElementById('order-price').required = true;
                } else {
                    priceGroup.style.display = 'none';
                    document.getElementById('order-price').required = false;
                }
            });
        }
    }

    handlePlaceOrder() {
        const form = document.getElementById('order-form');
        const formData = new FormData(form);

        const symbol = formData.get('symbol')?.toUpperCase().trim();
        const action = formData.get('action');
        const quantity = formData.get('quantity');
        const orderType = formData.get('order_type');
        const price = formData.get('price');

        if (!symbol || !action || !quantity || !orderType) {
            logger.error('Please fill in all required fields');
            return;
        }

        if ((orderType === 'LMT' || orderType === 'STP') && !price) {
            logger.error('Price is required for limit and stop orders');
            return;
        }

        // Validate quantity
        const qty = parseInt(quantity);
        if (isNaN(qty) || qty <= 0) {
            logger.error('Quantity must be a positive number');
            return;
        }

        // Validate price if provided
        let priceValue = null;
        if (price) {
            priceValue = parseFloat(price);
            if (isNaN(priceValue) || priceValue <= 0) {
                logger.error('Price must be a positive number');
                return;
            }
        }

        // Place order via WebSocket
        const success = window.wsClient.placeOrder(
            symbol,
            action,
            qty,
            orderType,
            priceValue,
            'stock' // Default to stock for now
        );

        if (success) {
            logger.success(`Placed ${action} order: ${qty} ${symbol} at ${orderType}${priceValue ? ' $' + priceValue : ''}`);

            // Create pending order entry
            this.addPendingOrder(symbol, action, qty, orderType, priceValue);

            // Clear form
            form.reset();
            document.getElementById('price-group').style.display = 'none';
            document.getElementById('order-price').required = false;
        } else {
            logger.error('Failed to place order - WebSocket not connected');
        }
    }

    addPendingOrder(symbol, action, quantity, orderType, price) {
        // Create a temporary order ID until we get the real one from the server
        const tempOrderId = `pending_${Date.now()}`;

        const order = {
            orderId: tempOrderId,
            symbol,
            action,
            quantity,
            orderType,
            price,
            status: 'Pending',
            filled: 0,
            remaining: quantity,
            avgFillPrice: null,
            lastFillPrice: null,
            timestamp: Date.now(),
            isPending: true
        };

        this.orders.set(tempOrderId, order);
        this.renderOrders();
    }

    updateOrderStatus(message) {
        if (message.type !== 'order_status') return;

        const orderId = message.order_id.toString();

        // Check if this is for a pending order and update the ID
        let order = this.orders.get(orderId);

        if (!order) {
            // This might be a new order from the server
            // Create a new order entry
            order = {
                orderId: orderId,
                symbol: 'Unknown', // We don't have symbol info in order status
                action: 'Unknown',
                quantity: message.filled + message.remaining,
                orderType: 'Unknown',
                price: null,
                status: message.status,
                filled: message.filled,
                remaining: message.remaining,
                avgFillPrice: message.avg_fill_price,
                lastFillPrice: message.last_fill_price,
                timestamp: message.timestamp * 1000, // Convert to milliseconds
                isPending: false
            };
        } else {
            // Update existing order
            order.status = message.status;
            order.filled = message.filled;
            order.remaining = message.remaining;
            order.avgFillPrice = message.avg_fill_price;
            order.lastFillPrice = message.last_fill_price;
            order.timestamp = message.timestamp * 1000;
            order.isPending = false;
        }

        this.orders.set(orderId, order);
        this.renderOrders();

        logger.info(`Order ${orderId} status: ${message.status} (${message.filled}/${message.filled + message.remaining} filled)`);
    }

    renderOrders() {
        if (this.orders.size === 0) {
            this.showEmptyState();
            return;
        }

        this.container.innerHTML = '';

        // Sort orders by timestamp (newest first)
        const sortedOrders = Array.from(this.orders.values())
            .sort((a, b) => b.timestamp - a.timestamp);

        sortedOrders.forEach(order => {
            const item = document.createElement('div');
            item.className = 'order-item';

            const statusClass = this.getStatusClass(order.status);
            const sideClass = order.action.toLowerCase();

            // Format timestamps
            const timeStr = new Date(order.timestamp).toLocaleTimeString();

            // Format fill info
            let fillInfo = '';
            if (order.filled > 0) {
                fillInfo = `Filled: ${order.filled}/${order.quantity}`;
                if (order.avgFillPrice) {
                    fillInfo += ` @ $${order.avgFillPrice.toFixed(2)}`;
                }
            } else {
                fillInfo = `Quantity: ${order.quantity}`;
            }

            // Format price info
            let priceInfo = '';
            if (order.orderType === 'LMT' && order.price) {
                priceInfo = ` @ $${order.price.toFixed(2)}`;
            } else if (order.orderType === 'STP' && order.price) {
                priceInfo = ` stop $${order.price.toFixed(2)}`;
            }

            item.innerHTML = `
                <div class="order-info">
                    <div class="order-header">
                        <span class="order-symbol">${order.symbol}</span>
                        <span class="order-side ${sideClass}">${order.action}</span>
                        <span class="order-type">${order.orderType}${priceInfo}</span>
                    </div>
                    <div class="order-details">
                        ${fillInfo} • ${timeStr}
                    </div>
                </div>
                <div class="order-status">
                    <span class="status-badge ${statusClass}">${order.status}</span>
                    ${order.remaining > 0 && order.status !== 'Filled' && order.status !== 'Cancelled' ?
                        `<button class="btn-small btn-cancel" onclick="orderManager.cancelOrder('${order.orderId}')">Cancel</button>` :
                        ''
                    }
                </div>
            `;

            this.container.appendChild(item);
        });
    }

    getStatusClass(status) {
        switch (status.toLowerCase()) {
            case 'filled':
                return 'status-filled';
            case 'cancelled':
            case 'canceled':
                return 'status-cancelled';
            case 'submitted':
            case 'presubmitted':
                return 'status-submitted';
            case 'pending':
            default:
                return 'status-pending';
        }
    }

    cancelOrder(orderId) {
        const order = this.orders.get(orderId);
        if (!order) {
            logger.error('Order not found');
            return;
        }

        if (order.isPending) {
            logger.warning('Cannot cancel pending order');
            return;
        }

        const success = window.wsClient.cancelOrder(orderId);

        if (success) {
            logger.info(`Cancel request sent for order ${orderId}`);
        } else {
            logger.error('Failed to cancel order - WebSocket not connected');
        }
    }

    showEmptyState() {
        this.container.innerHTML = `
            <div class="empty-state">
                No orders placed yet.<br>
                Use the form above to place orders.
            </div>
        `;
    }

    getOrder(orderId) {
        return this.orders.get(orderId);
    }

    getAllOrders() {
        return new Map(this.orders);
    }

    clear() {
        this.orders.clear();
        this.showEmptyState();
    }

    // Clean up old filled/cancelled orders
    cleanup(maxAge = 24 * 60 * 60 * 1000) { // 24 hours default
        const cutoff = Date.now() - maxAge;
        let removedCount = 0;

        for (const [orderId, order] of this.orders) {
            if (order.timestamp < cutoff &&
                (order.status === 'Filled' || order.status === 'Cancelled')) {
                this.orders.delete(orderId);
                removedCount++;
            }
        }

        if (removedCount > 0) {
            logger.info(`Cleaned up ${removedCount} old orders`);
            this.renderOrders();
        }
    }
}

// Create global order manager instance
window.orderManager = new OrderManager();
