"""Test utilities and helper functions."""

import asyncio
import json
import queue
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import websockets
from websockets.exceptions import ConnectionClosed


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self, messages_to_receive=None):
        self.messages_to_receive = messages_to_receive or []
        self.sent_messages = []
        self.remote_address = ("127.0.0.1", 12345)
        self.closed = False
        self._message_index = 0

    async def send(self, message):
        """Mock send method."""
        if self.closed:
            raise ConnectionClosed(None, None)
        self.sent_messages.append(message)

    async def recv(self):
        """Mock receive method."""
        if self.closed:
            raise ConnectionClosed(None, None)

        if self._message_index < len(self.messages_to_receive):
            message = self.messages_to_receive[self._message_index]
            self._message_index += 1
            return json.dumps(message) if isinstance(message, dict) else message
        else:
            # Simulate connection staying open
            await asyncio.sleep(0.1)
            raise ConnectionClosed(None, None)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await self.recv()
        except ConnectionClosed:
            raise StopAsyncIteration

    def close(self):
        """Close the mock websocket."""
        self.closed = True


class MockQueue:
    """Mock queue for testing message flow."""

    def __init__(self, maxsize=10000):
        self.maxsize = maxsize
        self.items = []
        self.full_count = 0

    def put_nowait(self, item):
        """Mock put_nowait method."""
        if len(self.items) >= self.maxsize:
            self.full_count += 1
            raise queue.Full()
        self.items.append(item)

    def get_nowait(self):
        """Mock get_nowait method."""
        if not self.items:
            raise queue.Empty()
        return self.items.pop(0)

    def empty(self):
        """Check if queue is empty."""
        return len(self.items) == 0

    def qsize(self):
        """Get queue size."""
        return len(self.items)


class MockIBClient:
    """Mock IB client for testing."""

    def __init__(self):
        self.connected = False
        self.requests = []
        self.orders = []
        self.cancelled_orders = []
        self.wrapper = None

    def connect(self, host, port, client_id):
        """Mock connect method."""
        self.connected = True
        return True

    def isConnected(self):
        """Mock isConnected method."""
        return self.connected

    def run(self):
        """Mock run method - does nothing in tests."""
        pass

    def reqMktData(
        self,
        req_id,
        contract,
        generic_tick_list,
        snapshot,
        regulatory_snapshot,
        mkt_data_options,
    ):
        """Mock market data request."""
        self.requests.append(
            {
                "type": "market_data",
                "req_id": req_id,
                "contract": contract,
                "generic_tick_list": generic_tick_list,
            }
        )

    def reqTickByTickData(
        self, req_id, contract, tick_type, number_of_ticks, ignore_size
    ):
        """Mock tick-by-tick data request."""
        self.requests.append(
            {
                "type": "tick_by_tick",
                "req_id": req_id,
                "contract": contract,
                "tick_type": tick_type,
            }
        )

    def reqContractDetails(self, req_id, contract):
        """Mock contract details request."""
        self.requests.append(
            {"type": "contract_details", "req_id": req_id, "contract": contract}
        )

    def placeOrder(self, order_id, contract, order):
        """Mock place order."""
        self.orders.append({"order_id": order_id, "contract": contract, "order": order})

    def cancelOrder(self, order_id, manual_order_cancel_time):
        """Mock cancel order."""
        self.cancelled_orders.append(order_id)

    def cancelMktData(self, req_id):
        """Mock cancel market data."""
        self.requests.append({"type": "cancel_market_data", "req_id": req_id})

    def cancelTickByTickData(self, req_id):
        """Mock cancel tick-by-tick data."""
        self.requests.append({"type": "cancel_tick_by_tick", "req_id": req_id})


@asynccontextmanager
async def mock_websocket_server(host, port, handler):
    """Mock WebSocket server context manager."""
    # This is a placeholder for WebSocket server mocking
    # In real tests, we would mock websockets.serve
    yield


def create_message_queue_with_items(items):
    """Create a mock queue pre-populated with items."""
    mock_queue = MockQueue()
    for item in items:
        mock_queue.put_nowait(item)
    return mock_queue


def assert_message_structure(message, expected_keys):
    """Assert that a message has the expected structure."""
    assert isinstance(message, dict), "Message should be a dictionary"

    for key in expected_keys:
        assert key in message, f"Message missing required key: {key}"

    # Check for timestamp if expected
    if "timestamp" in expected_keys:
        assert isinstance(
            message["timestamp"], (int, float)
        ), "Timestamp should be numeric"
        assert message["timestamp"] > 0, "Timestamp should be positive"


def assert_contract_attributes(
    contract,
    expected_symbol,
    expected_sec_type,
    expected_exchange=None,
    expected_currency=None,
):
    """Assert contract has expected attributes."""
    assert contract.symbol == expected_symbol
    assert contract.secType == expected_sec_type

    if expected_exchange:
        assert contract.exchange == expected_exchange

    if expected_currency:
        assert contract.currency == expected_currency


def assert_order_attributes(
    order, expected_action, expected_quantity, expected_order_type, expected_price=None
):
    """Assert order has expected attributes."""
    assert order.action == expected_action
    assert order.totalQuantity == expected_quantity
    assert order.orderType == expected_order_type

    if expected_price and expected_order_type == "LMT":
        assert order.lmtPrice == expected_price
    elif expected_price and expected_order_type == "STP":
        assert order.auxPrice == expected_price


async def wait_for_condition(condition_func, timeout=1.0, check_interval=0.01):
    """Wait for a condition to become true with timeout."""
    elapsed = 0
    while elapsed < timeout:
        if condition_func():
            return True
        await asyncio.sleep(check_interval)
        elapsed += check_interval
    return False


class AsyncIteratorMock:
    """Mock async iterator for testing."""

    def __init__(self, items):
        self.items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.items)
        except StopIteration:
            raise StopAsyncIteration
