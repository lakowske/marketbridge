"""Integration tests for message flow between IB API and WebSocket clients."""

import asyncio
import json
import queue
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from marketbridge.ib_websocket_bridge import IBWebSocketBridge, IBWrapper
from tests.fixtures.mock_data import (
    EXPECTED_MESSAGE_FORMATS,
    MockContractDetails,
    MockTickAttrib,
    MockTickByTickAttrib,
    create_sample_contract,
)
from tests.fixtures.test_utils import MockIBClient, MockQueue, MockWebSocket


class TestMessageFlow:
    """Integration tests for message flow from IB callbacks to WebSocket clients."""

    def setup_method(self):
        """Set up test fixtures."""
        self.bridge = IBWebSocketBridge()
        self.bridge.client = MockIBClient()

        # Replace message queue with controllable mock
        self.mock_queue = MockQueue()
        self.bridge.message_queue = self.mock_queue
        self.bridge.wrapper.message_queue = self.mock_queue

    def test_tick_price_to_websocket_flow(self):
        """Test flow from IB tick price callback to WebSocket clients."""
        # Set up WebSocket client
        mock_client = MockWebSocket()
        self.bridge.websocket_clients.add(mock_client)

        # Simulate IB tick price callback
        req_id = 1001
        tick_type = 1  # BID
        price = 150.25
        attrib = MockTickAttrib()

        self.bridge.wrapper.tickPrice(req_id, tick_type, price, attrib)

        # Verify message was queued
        assert self.mock_queue.qsize() == 1
        message = self.mock_queue.get_nowait()

        # Verify message structure
        assert message["type"] == "market_data"
        assert message["data_type"] == "price"
        assert message["req_id"] == req_id
        assert message["tick_type"] == "bid"
        assert message["price"] == price

    def test_order_status_to_websocket_flow(self):
        """Test flow from IB order status callback to WebSocket clients."""
        # Set up WebSocket client
        mock_client = MockWebSocket()
        self.bridge.websocket_clients.add(mock_client)

        # Simulate IB order status callback
        order_id = 2001
        status = "Filled"
        filled = 100
        remaining = 0
        avg_fill_price = 150.30

        self.bridge.wrapper.orderStatus(
            order_id,
            status,
            filled,
            remaining,
            avg_fill_price,
            1234567890,
            0,
            150.30,
            1,
            "",
            0.0,
        )

        # Verify message was queued
        assert self.mock_queue.qsize() == 1
        message = self.mock_queue.get_nowait()

        # Verify message structure
        assert message["type"] == "order_status"
        assert message["order_id"] == order_id
        assert message["status"] == status
        assert message["filled"] == filled
        assert message["remaining"] == remaining

    def test_contract_details_to_websocket_flow(self):
        """Test flow from IB contract details callback to WebSocket clients."""
        # Set up WebSocket client
        mock_client = MockWebSocket()
        self.bridge.websocket_clients.add(mock_client)

        # Simulate IB contract details callback
        req_id = 3001
        contract = create_sample_contract()
        contract_details = MockContractDetails(contract)

        self.bridge.wrapper.contractDetails(req_id, contract_details)

        # Verify message was queued
        assert self.mock_queue.qsize() == 1
        message = self.mock_queue.get_nowait()

        # Verify message structure
        assert message["type"] == "contract_details"
        assert message["req_id"] == req_id
        assert message["contract"]["symbol"] == contract.symbol
        assert message["market_name"] == contract_details.marketName

    def test_error_to_websocket_flow(self):
        """Test flow from IB error callback to WebSocket clients."""
        # Set up WebSocket client
        mock_client = MockWebSocket()
        self.bridge.websocket_clients.add(mock_client)

        # Simulate IB error callback
        req_id = 4001
        error_code = 200
        error_string = "No security definition found"

        self.bridge.wrapper.error(req_id, error_code, error_string)

        # Verify message was queued
        assert self.mock_queue.qsize() == 1
        message = self.mock_queue.get_nowait()

        # Verify message structure
        assert message["type"] == "error"
        assert message["req_id"] == req_id
        assert message["error_code"] == error_code
        assert message["error_string"] == error_string
        assert message["severity"] == "ERROR"

    @pytest.mark.asyncio
    async def test_complete_market_data_flow(self):
        """Test complete market data flow from subscription to data delivery."""
        # Set up WebSocket client
        mock_client = MockWebSocket()
        self.bridge.websocket_clients.add(mock_client)

        # Step 1: Client subscribes to market data
        subscribe_message = {
            "command": "subscribe_market_data",
            "symbol": "AAPL",
            "instrument_type": "stock",
        }

        await self.bridge.handle_client_message(
            mock_client, json.dumps(subscribe_message)
        )

        # Verify subscription was processed
        assert len(self.bridge.client.requests) == 1
        assert 1 in self.bridge.active_requests

        # Step 2: IB sends tick data
        self.bridge.wrapper.tickPrice(1, 1, 150.25, MockTickAttrib())
        self.bridge.wrapper.tickSize(1, 0, 500)

        # Verify messages were queued
        assert self.mock_queue.qsize() == 2

        # Step 3: Messages should be broadcast to client
        price_message = self.mock_queue.get_nowait()
        size_message = self.mock_queue.get_nowait()

        assert price_message["type"] == "market_data"
        assert price_message["data_type"] == "price"
        assert size_message["type"] == "market_data"
        assert size_message["data_type"] == "size"

    @pytest.mark.asyncio
    async def test_order_placement_flow(self):
        """Test complete order placement flow."""
        # Set up WebSocket client
        mock_client = MockWebSocket()
        self.bridge.websocket_clients.add(mock_client)

        # Set up wrapper with valid order ID
        self.bridge.wrapper.next_order_id = 2001

        # Step 1: Client places order
        order_message = {
            "command": "place_order",
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 100,
            "order_type": "MKT",
            "instrument_type": "stock",
        }

        await self.bridge.handle_client_message(mock_client, json.dumps(order_message))

        # Verify order was placed
        assert len(self.bridge.client.orders) == 1
        placed_order = self.bridge.client.orders[0]
        assert placed_order["order_id"] == 2001

        # Step 2: IB sends order status updates
        self.bridge.wrapper.orderStatus(
            2001, "Submitted", 0, 100, 0.0, 1234567890, 0, 0.0, 1, "", 0.0
        )

        self.bridge.wrapper.orderStatus(
            2001, "Filled", 100, 0, 150.30, 1234567890, 0, 150.30, 1, "", 0.0
        )

        # Verify status messages were queued
        assert self.mock_queue.qsize() == 2

        submitted_message = self.mock_queue.get_nowait()
        filled_message = self.mock_queue.get_nowait()

        assert submitted_message["status"] == "Submitted"
        assert filled_message["status"] == "Filled"
        assert filled_message["filled"] == 100

    def test_time_and_sales_flow(self):
        """Test time and sales data flow."""
        # Set up WebSocket client
        mock_client = MockWebSocket()
        self.bridge.websocket_clients.add(mock_client)

        # Simulate time and sales data
        req_id = 1001
        trade_time = int(time.time())
        price = 150.25
        size = 100
        exchange = "NASDAQ"

        self.bridge.wrapper.tickByTickAllLast(
            req_id, 1, trade_time, price, size, MockTickByTickAttrib(), exchange, ""
        )

        # Verify message was queued
        assert self.mock_queue.qsize() == 1
        message = self.mock_queue.get_nowait()

        assert message["type"] == "time_and_sales"
        assert message["price"] == price
        assert message["size"] == size
        assert message["exchange"] == exchange
        assert message["trade_time"] == trade_time

    def test_bid_ask_tick_flow(self):
        """Test bid/ask tick data flow."""
        # Set up WebSocket client
        mock_client = MockWebSocket()
        self.bridge.websocket_clients.add(mock_client)

        # Simulate bid/ask tick data
        req_id = 1001
        trade_time = int(time.time())
        bid_price = 150.20
        ask_price = 150.30
        bid_size = 500
        ask_size = 300

        self.bridge.wrapper.tickByTickBidAsk(
            req_id,
            trade_time,
            bid_price,
            ask_price,
            bid_size,
            ask_size,
            MockTickByTickAttrib(),
        )

        # Verify message was queued
        assert self.mock_queue.qsize() == 1
        message = self.mock_queue.get_nowait()

        assert message["type"] == "bid_ask_tick"
        assert message["bid_price"] == bid_price
        assert message["ask_price"] == ask_price
        assert message["bid_size"] == bid_size
        assert message["ask_size"] == ask_size

    def test_connection_status_flow(self):
        """Test connection status message flow."""
        # Set up WebSocket client
        mock_client = MockWebSocket()
        self.bridge.websocket_clients.add(mock_client)

        # Simulate connection established
        order_id = 1001
        self.bridge.wrapper.nextValidId(order_id)

        # Verify connection status message was queued
        assert self.mock_queue.qsize() == 1
        message = self.mock_queue.get_nowait()

        assert message["type"] == "connection_status"
        assert message["status"] == "connected"
        assert message["next_order_id"] == order_id

    def test_message_queue_overflow_handling(self):
        """Test handling of message queue overflow."""
        # Create queue with very small capacity
        small_queue = MockQueue(maxsize=2)
        self.bridge.message_queue = small_queue
        self.bridge.wrapper.message_queue = small_queue

        # Fill queue to capacity
        small_queue.put_nowait("message1")
        small_queue.put_nowait("message2")

        # Try to add another message (should be dropped)
        with patch("marketbridge.ib_websocket_bridge.logger") as mock_logger:
            self.bridge.wrapper.tickPrice(1, 1, 150.25, None)
            mock_logger.warning.assert_called_with(
                "Message queue full, dropping message"
            )

        # Queue should still be full with original messages
        assert small_queue.qsize() == 2
        assert small_queue.full_count == 1

    @pytest.mark.asyncio
    async def test_multiple_clients_message_broadcast(self):
        """Test broadcasting messages to multiple WebSocket clients."""
        # Set up multiple WebSocket clients
        clients = []
        for i in range(3):
            client = Mock()
            client.send = AsyncMock()
            clients.append(client)
            self.bridge.websocket_clients.add(client)

        # Add test message to queue
        test_message = {"type": "test", "data": "broadcast_test"}
        self.mock_queue.put_nowait(test_message)

        # Simulate broadcast
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, Exception("Stop")]

            try:
                await self.bridge.broadcast_messages()
            except Exception:
                pass

        # Verify all clients received the message
        message_json = json.dumps(test_message)
        for client in clients:
            client.send.assert_called_once_with(message_json)

    def test_message_timestamp_consistency(self):
        """Test that messages have consistent timestamps."""
        with patch("time.time", return_value=1642678800.123):
            # Generate various types of messages
            self.bridge.wrapper.tickPrice(1, 1, 150.25, None)
            self.bridge.wrapper.orderStatus(
                1001, "Filled", 100, 0, 150.30, 1234, 0, 150.30, 1, "", 0.0
            )
            self.bridge.wrapper.error(1, 200, "Test error")

            # Check all messages have the expected timestamp
            while not self.mock_queue.empty():
                message = self.mock_queue.get_nowait()
                assert message["timestamp"] == 1642678800.123

    @pytest.mark.asyncio
    async def test_unsubscription_stops_message_flow(self):
        """Test that unsubscribing stops message flow for specific symbols."""
        # Subscribe to market data
        subscribe_data = {
            "command": "subscribe_market_data",
            "symbol": "AAPL",
            "instrument_type": "stock",
        }

        mock_client = MockWebSocket()
        await self.bridge.handle_client_message(mock_client, json.dumps(subscribe_data))

        # Verify subscription exists
        assert 1 in self.bridge.active_requests

        # Generate some tick data
        self.bridge.wrapper.tickPrice(1, 1, 150.25, None)
        assert self.mock_queue.qsize() == 1
        self.mock_queue.get_nowait()  # Clear the message

        # Unsubscribe
        unsubscribe_data = {"command": "unsubscribe_market_data", "symbol": "AAPL"}

        await self.bridge.handle_client_message(
            mock_client, json.dumps(unsubscribe_data)
        )

        # Verify subscription was removed
        assert 1 not in self.bridge.active_requests

        # Verify cancellation request was made
        cancel_requests = [
            r
            for r in self.bridge.client.requests
            if r.get("type") == "cancel_market_data"
        ]
        assert len(cancel_requests) == 1

    def test_message_serialization_compatibility(self):
        """Test that all message types can be serialized to JSON."""
        # Generate various message types
        self.bridge.wrapper.nextValidId(1001)
        self.bridge.wrapper.tickPrice(1, 1, 150.25, MockTickAttrib())
        self.bridge.wrapper.tickSize(1, 0, 500)
        self.bridge.wrapper.tickString(1, 45, "1642678800")
        self.bridge.wrapper.orderStatus(
            1001, "Filled", 100, 0, 150.30, 1234, 0, 150.30, 1, "", 0.0
        )
        self.bridge.wrapper.error(1, 200, "Test error")

        # Verify all messages can be serialized
        while not self.mock_queue.empty():
            message = self.mock_queue.get_nowait()
            try:
                json.dumps(message)  # Should not raise exception
            except (TypeError, ValueError) as e:
                pytest.fail(f"Message serialization failed: {e}")

    def test_request_id_tracking_in_messages(self):
        """Test that request IDs are properly tracked in messages."""
        # Subscribe to multiple instruments
        symbols = ["AAPL", "MSFT", "GOOGL"]

        for symbol in symbols:
            subscribe_data = {
                "command": "subscribe_market_data",
                "symbol": symbol,
                "instrument_type": "stock",
            }
            self.bridge.subscribe_market_data(subscribe_data)

        # Generate tick data for each request
        for req_id in range(1, 4):
            self.bridge.wrapper.tickPrice(req_id, 1, 150.00 + req_id, None)

        # Verify messages have correct request IDs
        for expected_req_id in range(1, 4):
            message = self.mock_queue.get_nowait()
            assert message["req_id"] == expected_req_id
            assert message["price"] == 150.00 + expected_req_id
