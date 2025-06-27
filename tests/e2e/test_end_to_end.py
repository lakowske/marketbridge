"""End-to-end tests for IBWebSocketBridge system."""

import asyncio
import json
import threading
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from marketbridge.ib_websocket_bridge import IBWebSocketBridge
from tests.fixtures.mock_data import SAMPLE_WEBSOCKET_MESSAGES
from tests.fixtures.test_utils import MockIBClient, MockWebSocket, wait_for_condition


class TestEndToEnd:
    """End-to-end tests for the complete IBWebSocketBridge system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.bridge = IBWebSocketBridge(ib_host="127.0.0.1", ib_port=7497, ws_port=8765)
        # Use mock IB client to avoid actual connections
        self.bridge.client = MockIBClient()

    @pytest.mark.asyncio
    async def test_complete_market_data_subscription_workflow(self):
        """Test complete workflow from WebSocket subscription to market data delivery."""
        # Step 1: Start the bridge (mock the IB connection)
        with patch.object(self.bridge, "connect_to_ib", return_value=True):
            # Step 2: Simulate WebSocket client connection
            mock_client = MockWebSocket(
                [SAMPLE_WEBSOCKET_MESSAGES["subscribe_market_data"]]
            )

            # Step 3: Handle client connection and subscription
            await self.bridge.handle_websocket_client(mock_client, "/")

            # Verify subscription was processed
            assert len(self.bridge.client.requests) == 1
            request = self.bridge.client.requests[0]
            assert request["type"] == "market_data"
            assert request["req_id"] == 1

            # Verify active request tracking
            assert 1 in self.bridge.active_requests
            assert self.bridge.active_requests[1]["symbol"] == "AAPL"

            # Step 4: Simulate IB sending market data
            self.bridge.wrapper.tickPrice(1, 1, 150.25, None)  # BID
            self.bridge.wrapper.tickPrice(1, 2, 150.30, None)  # ASK
            self.bridge.wrapper.tickSize(1, 0, 500)  # BID_SIZE
            self.bridge.wrapper.tickSize(1, 3, 300)  # ASK_SIZE

            # Step 5: Verify messages were queued
            assert self.bridge.message_queue.qsize() == 4

            # Step 6: Verify message content
            messages = []
            while not self.bridge.message_queue.empty():
                messages.append(self.bridge.message_queue.get_nowait())

            # Verify market data structure
            price_messages = [m for m in messages if m["data_type"] == "price"]
            size_messages = [m for m in messages if m["data_type"] == "size"]

            assert len(price_messages) == 2  # BID and ASK
            assert len(size_messages) == 2  # BID_SIZE and ASK_SIZE

            # Verify specific data
            bid_message = next(m for m in price_messages if m["tick_type"] == "bid")
            ask_message = next(m for m in price_messages if m["tick_type"] == "ask")

            assert bid_message["price"] == 150.25
            assert ask_message["price"] == 150.30

    @pytest.mark.asyncio
    async def test_complete_order_placement_workflow(self):
        """Test complete order placement and status tracking workflow."""
        # Setup
        self.bridge.wrapper.next_order_id = 2001

        with patch.object(self.bridge, "connect_to_ib", return_value=True):
            # Step 1: Client places market order
            mock_client = MockWebSocket([SAMPLE_WEBSOCKET_MESSAGES["place_order"]])

            await self.bridge.handle_websocket_client(mock_client, "/")

            # Verify order was placed
            assert len(self.bridge.client.orders) == 1
            order_data = self.bridge.client.orders[0]
            assert order_data["order_id"] == 2001
            assert order_data["order"].action == "BUY"
            assert order_data["order"].totalQuantity == 100
            assert order_data["order"].orderType == "MKT"

            # Step 2: Simulate order status progression
            status_updates = [
                ("Submitted", 0, 100, 0.0),
                ("PreSubmitted", 0, 100, 0.0),
                ("Filled", 100, 0, 150.30),
            ]

            for status, filled, remaining, avg_price in status_updates:
                self.bridge.wrapper.orderStatus(
                    2001,
                    status,
                    filled,
                    remaining,
                    avg_price,
                    1234567890,
                    0,
                    avg_price if filled > 0 else 0.0,
                    1,
                    "",
                    0.0,
                )

            # Step 3: Verify status messages were generated
            assert self.bridge.message_queue.qsize() == 3

            # Verify order progression
            status_messages = []
            while not self.bridge.message_queue.empty():
                status_messages.append(self.bridge.message_queue.get_nowait())

            assert status_messages[0]["status"] == "Submitted"
            assert status_messages[1]["status"] == "PreSubmitted"
            assert status_messages[2]["status"] == "Filled"
            assert status_messages[2]["filled"] == 100
            assert status_messages[2]["avg_fill_price"] == 150.30

    @pytest.mark.asyncio
    async def test_multiple_instrument_subscriptions(self):
        """Test handling multiple instrument type subscriptions."""
        with patch.object(self.bridge, "connect_to_ib", return_value=True):
            # Subscribe to different instrument types
            subscription_messages = [
                SAMPLE_WEBSOCKET_MESSAGES["subscribe_market_data"],  # Stock
                SAMPLE_WEBSOCKET_MESSAGES["option_contract"],  # Option
                SAMPLE_WEBSOCKET_MESSAGES["future_contract"],  # Future
                SAMPLE_WEBSOCKET_MESSAGES["forex_contract"],  # Forex
            ]

            mock_client = MockWebSocket(subscription_messages)
            await self.bridge.handle_websocket_client(mock_client, "/")

            # Verify all subscriptions were processed
            assert len(self.bridge.client.requests) == 4
            assert len(self.bridge.active_requests) == 4

            # Verify different instrument types
            request_types = []
            for req_id in range(1, 5):
                assert req_id in self.bridge.active_requests
                request = self.bridge.active_requests[req_id]
                request_types.append(request["instrument_type"])

            expected_types = ["stock", "option", "future", "forex"]
            assert all(inst_type in request_types for inst_type in expected_types)

            # Simulate market data for each instrument
            for req_id in range(1, 5):
                self.bridge.wrapper.tickPrice(req_id, 1, 100.0 + req_id, None)

            # Verify messages for all instruments
            assert self.bridge.message_queue.qsize() == 4

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self):
        """Test error handling throughout the system."""
        with patch.object(self.bridge, "connect_to_ib", return_value=True):
            # Step 1: Invalid subscription (missing symbol)
            invalid_message = SAMPLE_WEBSOCKET_MESSAGES["missing_symbol"]
            mock_client = MockWebSocket([invalid_message])

            await self.bridge.handle_websocket_client(mock_client, "/")

            # Should handle gracefully without creating subscription
            assert len(self.bridge.client.requests) == 0

            # Step 2: Valid subscription followed by IB error
            valid_message = SAMPLE_WEBSOCKET_MESSAGES["subscribe_market_data"]
            mock_client2 = MockWebSocket([valid_message])

            await self.bridge.handle_websocket_client(mock_client2, "/")

            # Should create subscription
            assert len(self.bridge.client.requests) == 1

            # Step 3: Simulate IB error response
            self.bridge.wrapper.error(1, 200, "No security definition found")

            # Verify error message was queued
            assert self.bridge.message_queue.qsize() == 1
            error_message = self.bridge.message_queue.get_nowait()

            assert error_message["type"] == "error"
            assert error_message["error_code"] == 200
            assert error_message["severity"] == "ERROR"

    @pytest.mark.asyncio
    async def test_subscription_and_unsubscription_cycle(self):
        """Test complete subscription/unsubscription cycle."""
        with patch.object(self.bridge, "connect_to_ib", return_value=True):
            # Step 1: Subscribe
            subscribe_msg = SAMPLE_WEBSOCKET_MESSAGES["subscribe_market_data"]
            mock_client = MockWebSocket([subscribe_msg])

            await self.bridge.handle_websocket_client(mock_client, "/")

            assert len(self.bridge.client.requests) == 1
            assert 1 in self.bridge.active_requests

            # Step 2: Generate some market data
            self.bridge.wrapper.tickPrice(1, 1, 150.25, None)
            assert self.bridge.message_queue.qsize() == 1
            self.bridge.message_queue.get_nowait()  # Clear message

            # Step 3: Unsubscribe
            unsubscribe_msg = SAMPLE_WEBSOCKET_MESSAGES["unsubscribe_market_data"]
            mock_client2 = MockWebSocket([unsubscribe_msg])

            await self.bridge.handle_websocket_client(mock_client2, "/")

            # Verify unsubscription
            assert 1 not in self.bridge.active_requests

            # Verify cancellation request
            cancel_requests = [
                r
                for r in self.bridge.client.requests
                if r.get("type") == "cancel_market_data"
            ]
            assert len(cancel_requests) == 1

    @pytest.mark.asyncio
    async def test_contract_details_workflow(self):
        """Test contract details request workflow."""
        with patch.object(self.bridge, "connect_to_ib", return_value=True):
            # Step 1: Request contract details
            details_msg = SAMPLE_WEBSOCKET_MESSAGES["get_contract_details"]
            mock_client = MockWebSocket([details_msg])

            await self.bridge.handle_websocket_client(mock_client, "/")

            # Verify request was made
            assert len(self.bridge.client.requests) == 1
            request = self.bridge.client.requests[0]
            assert request["type"] == "contract_details"

            # Step 2: Simulate IB contract details response
            from tests.fixtures.mock_data import (
                MockContractDetails,
                create_sample_contract,
            )

            contract = create_sample_contract("SPY")
            contract_details = MockContractDetails(contract)

            self.bridge.wrapper.contractDetails(1, contract_details)
            self.bridge.wrapper.contractDetailsEnd(1)

            # Verify messages were generated
            assert self.bridge.message_queue.qsize() == 2

            details_message = self.bridge.message_queue.get_nowait()
            end_message = self.bridge.message_queue.get_nowait()

            assert details_message["type"] == "contract_details"
            assert details_message["contract"]["symbol"] == "SPY"
            assert end_message["type"] == "contract_details_end"

    @pytest.mark.asyncio
    async def test_time_and_sales_workflow(self):
        """Test time and sales subscription workflow."""
        with patch.object(self.bridge, "connect_to_ib", return_value=True):
            # Step 1: Subscribe to time and sales
            time_sales_msg = SAMPLE_WEBSOCKET_MESSAGES["subscribe_time_and_sales"]
            mock_client = MockWebSocket([time_sales_msg])

            await self.bridge.handle_websocket_client(mock_client, "/")

            # Verify subscription
            assert len(self.bridge.client.requests) == 1
            request = self.bridge.client.requests[0]
            assert request["type"] == "tick_by_tick"
            assert request["tick_type"] == "AllLast"

            # Step 2: Simulate time and sales data
            trade_time = int(time.time())
            self.bridge.wrapper.tickByTickAllLast(
                1, 1, trade_time, 150.25, 100, None, "NASDAQ", ""
            )

            # Verify time and sales message
            assert self.bridge.message_queue.qsize() == 1
            message = self.bridge.message_queue.get_nowait()

            assert message["type"] == "time_and_sales"
            assert message["price"] == 150.25
            assert message["size"] == 100
            assert message["exchange"] == "NASDAQ"

    @pytest.mark.asyncio
    async def test_bid_ask_subscription_workflow(self):
        """Test bid/ask subscription workflow."""
        with patch.object(self.bridge, "connect_to_ib", return_value=True):
            # Step 1: Subscribe to bid/ask
            bid_ask_msg = SAMPLE_WEBSOCKET_MESSAGES["subscribe_bid_ask"]
            mock_client = MockWebSocket([bid_ask_msg])

            await self.bridge.handle_websocket_client(mock_client, "/")

            # Verify subscription
            assert len(self.bridge.client.requests) == 1
            request = self.bridge.client.requests[0]
            assert request["type"] == "tick_by_tick"
            assert request["tick_type"] == "BidAsk"

            # Step 2: Simulate bid/ask data
            trade_time = int(time.time())
            self.bridge.wrapper.tickByTickBidAsk(
                1, trade_time, 150.20, 150.30, 500, 300, None
            )

            # Verify bid/ask message
            assert self.bridge.message_queue.qsize() == 1
            message = self.bridge.message_queue.get_nowait()

            assert message["type"] == "bid_ask_tick"
            assert message["bid_price"] == 150.20
            assert message["ask_price"] == 150.30
            assert message["bid_size"] == 500
            assert message["ask_size"] == 300

    @pytest.mark.asyncio
    async def test_system_resilience_under_load(self):
        """Test system behavior under high message load."""
        with patch.object(self.bridge, "connect_to_ib", return_value=True):
            # Step 1: Set up multiple subscriptions
            num_subscriptions = 10

            for i in range(num_subscriptions):
                subscribe_msg = SAMPLE_WEBSOCKET_MESSAGES[
                    "subscribe_market_data"
                ].copy()
                subscribe_msg["symbol"] = f"STOCK{i}"

                mock_client = MockWebSocket([subscribe_msg])
                await self.bridge.handle_websocket_client(mock_client, "/")

            # Verify all subscriptions
            assert len(self.bridge.client.requests) == num_subscriptions
            assert len(self.bridge.active_requests) == num_subscriptions

            # Step 2: Generate high volume of market data
            messages_per_subscription = 20
            total_expected_messages = num_subscriptions * messages_per_subscription

            for req_id in range(1, num_subscriptions + 1):
                for tick_num in range(messages_per_subscription):
                    price = 100.0 + req_id + (tick_num * 0.01)
                    self.bridge.wrapper.tickPrice(req_id, 1, price, None)

            # Step 3: Verify all messages were queued
            assert self.bridge.message_queue.qsize() == total_expected_messages

            # Step 4: Verify message integrity
            req_id_counts = {}
            while not self.bridge.message_queue.empty():
                message = self.bridge.message_queue.get_nowait()
                req_id = message["req_id"]
                req_id_counts[req_id] = req_id_counts.get(req_id, 0) + 1

            # Each request ID should have exactly messages_per_subscription messages
            for req_id in range(1, num_subscriptions + 1):
                assert req_id_counts[req_id] == messages_per_subscription

    @pytest.mark.asyncio
    async def test_graceful_shutdown_workflow(self):
        """Test graceful system shutdown."""
        # This test would normally test the full run() method
        # but we'll test the key components of shutdown

        with patch.object(self.bridge, "connect_to_ib", return_value=True):
            # Set up some active subscriptions
            subscribe_msg = SAMPLE_WEBSOCKET_MESSAGES["subscribe_market_data"]
            mock_client = MockWebSocket([subscribe_msg])

            await self.bridge.handle_websocket_client(mock_client, "/")

            # Verify active state
            assert len(self.bridge.active_requests) == 1
            assert (
                len(self.bridge.websocket_clients) == 0
            )  # Client disconnected after processing

            # Simulate some market data
            self.bridge.wrapper.tickPrice(1, 1, 150.25, None)
            assert self.bridge.message_queue.qsize() == 1

            # The actual shutdown would be handled by KeyboardInterrupt
            # in the run() method, but we can verify the state is manageable
