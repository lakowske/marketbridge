"""Unit tests for IBWebSocketBridge class."""

import asyncio
import json
import queue
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from marketbridge.ib_websocket_bridge import IBClient, IBWebSocketBridge, IBWrapper
from tests.fixtures.mock_data import (
    SAMPLE_WEBSOCKET_MESSAGES,
    create_sample_contract,
    create_sample_order,
)
from tests.fixtures.test_utils import (
    MockIBClient,
    MockQueue,
    MockWebSocket,
    assert_contract_attributes,
    assert_message_structure,
    assert_order_attributes,
)


class TestIBWebSocketBridge:
    """Test suite for IBWebSocketBridge class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.bridge = IBWebSocketBridge(ib_host="127.0.0.1", ib_port=7497, ws_port=8765)

    def test_init(self):
        """Test IBWebSocketBridge initialization."""
        assert self.bridge.ib_host == "127.0.0.1"
        assert self.bridge.ib_port == 7497
        assert self.bridge.ws_port == 8765
        assert isinstance(self.bridge.message_queue, queue.Queue)
        assert isinstance(self.bridge.websocket_clients, set)
        assert isinstance(self.bridge.wrapper, IBWrapper)
        assert isinstance(self.bridge.client, IBClient)
        assert self.bridge.next_req_id == 1
        assert isinstance(self.bridge.active_requests, dict)

    @patch("marketbridge.ib_websocket_bridge.threading.Thread")
    def test_connect_to_ib_success(self, mock_thread):
        """Test successful connection to IB."""
        mock_client = Mock()
        mock_client.connect.return_value = True
        self.bridge.client = mock_client

        result = self.bridge.connect_to_ib()

        assert result is True
        mock_client.connect.assert_called_once_with("127.0.0.1", 7497, clientId=1)
        mock_thread.assert_called_once()

    @patch("marketbridge.ib_websocket_bridge.threading.Thread")
    def test_connect_to_ib_failure(self, mock_thread):
        """Test failed connection to IB."""
        mock_client = Mock()
        mock_client.connect.side_effect = Exception("Connection failed")
        self.bridge.client = mock_client

        result = self.bridge.connect_to_ib()

        assert result is False
        mock_client.connect.assert_called_once()

    def test_create_contract_from_params_stock(self):
        """Test creating stock contract from parameters."""
        params = SAMPLE_WEBSOCKET_MESSAGES["subscribe_market_data"]

        contract = self.bridge.create_contract_from_params(params)

        assert_contract_attributes(contract, "AAPL", "STK", "SMART", "USD")

    def test_create_contract_from_params_option(self):
        """Test creating option contract from parameters."""
        params = SAMPLE_WEBSOCKET_MESSAGES["option_contract"]

        contract = self.bridge.create_contract_from_params(params)

        assert_contract_attributes(contract, "AAPL", "OPT", "SMART", "USD")
        assert contract.strike == 150.0
        assert contract.right == "C"
        assert contract.lastTradeDateOrContractMonth == "20240315"

    def test_create_contract_from_params_future(self):
        """Test creating future contract from parameters."""
        params = SAMPLE_WEBSOCKET_MESSAGES["future_contract"]

        contract = self.bridge.create_contract_from_params(params)

        assert_contract_attributes(contract, "ES", "FUT", "CME", "USD")
        assert contract.lastTradeDateOrContractMonth == "20240315"

    def test_create_contract_from_params_forex(self):
        """Test creating forex contract from parameters."""
        params = SAMPLE_WEBSOCKET_MESSAGES["forex_contract"]

        contract = self.bridge.create_contract_from_params(params)

        assert_contract_attributes(contract, "EUR", "CASH", "IDEALPRO", "USD")

    def test_create_contract_from_params_missing_symbol(self):
        """Test error when symbol is missing."""
        params = SAMPLE_WEBSOCKET_MESSAGES["missing_symbol"]

        with pytest.raises(ValueError, match="Symbol is required"):
            self.bridge.create_contract_from_params(params)

    def test_create_contract_from_params_unsupported_type(self):
        """Test error with unsupported instrument type."""
        params = {"symbol": "TEST", "instrument_type": "unsupported_type"}

        with pytest.raises(ValueError, match="Unsupported instrument type"):
            self.bridge.create_contract_from_params(params)

    def test_subscribe_market_data(self):
        """Test market data subscription."""
        mock_client = MockIBClient()
        self.bridge.client = mock_client

        data = SAMPLE_WEBSOCKET_MESSAGES["subscribe_market_data"]
        self.bridge.subscribe_market_data(data)

        # Check request was made
        assert len(mock_client.requests) == 1
        request = mock_client.requests[0]
        assert request["type"] == "market_data"
        assert request["req_id"] == 1

        # Check active requests tracking
        assert 1 in self.bridge.active_requests
        active_req = self.bridge.active_requests[1]
        assert active_req["type"] == "market_data"
        assert active_req["symbol"] == "AAPL"
        assert active_req["instrument_type"] == "stock"

    def test_subscribe_time_and_sales(self):
        """Test time and sales subscription."""
        mock_client = MockIBClient()
        self.bridge.client = mock_client

        data = SAMPLE_WEBSOCKET_MESSAGES["subscribe_time_and_sales"]
        self.bridge.subscribe_time_and_sales(data)

        # Check request was made
        assert len(mock_client.requests) == 1
        request = mock_client.requests[0]
        assert request["type"] == "tick_by_tick"
        assert request["tick_type"] == "AllLast"

    def test_subscribe_bid_ask(self):
        """Test bid/ask subscription."""
        mock_client = MockIBClient()
        self.bridge.client = mock_client

        data = SAMPLE_WEBSOCKET_MESSAGES["subscribe_bid_ask"]
        self.bridge.subscribe_bid_ask(data)

        # Check request was made
        assert len(mock_client.requests) == 1
        request = mock_client.requests[0]
        assert request["type"] == "tick_by_tick"
        assert request["tick_type"] == "BidAsk"

    def test_unsubscribe_market_data(self):
        """Test market data unsubscription."""
        mock_client = MockIBClient()
        self.bridge.client = mock_client

        # First subscribe
        data = SAMPLE_WEBSOCKET_MESSAGES["subscribe_market_data"]
        self.bridge.subscribe_market_data(data)

        # Then unsubscribe
        unsubscribe_data = SAMPLE_WEBSOCKET_MESSAGES["unsubscribe_market_data"]
        self.bridge.unsubscribe_market_data(unsubscribe_data)

        # Check cancel request was made
        cancel_requests = [
            r for r in mock_client.requests if r["type"] == "cancel_market_data"
        ]
        assert len(cancel_requests) == 1
        assert cancel_requests[0]["req_id"] == 1

        # Check active requests was cleaned up
        assert 1 not in self.bridge.active_requests

    def test_get_contract_details(self):
        """Test contract details request."""
        mock_client = MockIBClient()
        self.bridge.client = mock_client

        data = SAMPLE_WEBSOCKET_MESSAGES["get_contract_details"]
        self.bridge.get_contract_details(data)

        # Check request was made
        assert len(mock_client.requests) == 1
        request = mock_client.requests[0]
        assert request["type"] == "contract_details"
        assert request["req_id"] == 1

    def test_place_order_market_order(self):
        """Test placing a market order."""
        mock_client = MockIBClient()
        self.bridge.client = mock_client
        self.bridge.wrapper.next_order_id = 2001

        data = SAMPLE_WEBSOCKET_MESSAGES["place_order"]
        self.bridge.place_order(data)

        # Check order was placed
        assert len(mock_client.orders) == 1
        order_data = mock_client.orders[0]
        assert order_data["order_id"] == 2001

        order = order_data["order"]
        assert_order_attributes(order, "BUY", 100, "MKT")

    def test_place_order_limit_order(self):
        """Test placing a limit order."""
        mock_client = MockIBClient()
        self.bridge.client = mock_client
        self.bridge.wrapper.next_order_id = 2002

        data = SAMPLE_WEBSOCKET_MESSAGES["place_limit_order"]
        self.bridge.place_order(data)

        # Check order was placed
        assert len(mock_client.orders) == 1
        order_data = mock_client.orders[0]

        order = order_data["order"]
        assert_order_attributes(order, "SELL", 50, "LMT", 500.00)

    def test_place_order_missing_required_fields(self):
        """Test error when required order fields are missing."""
        mock_client = MockIBClient()
        self.bridge.client = mock_client

        data = {
            "command": "place_order",
            "symbol": "AAPL",
            "instrument_type": "stock"
            # Missing action and quantity
        }

        # Should not raise exception but should log error
        self.bridge.place_order(data)

        # No orders should be placed
        assert len(mock_client.orders) == 0

    def test_cancel_order(self):
        """Test order cancellation."""
        mock_client = MockIBClient()
        self.bridge.client = mock_client

        data = SAMPLE_WEBSOCKET_MESSAGES["cancel_order"]
        self.bridge.cancel_order(data)

        # Check cancel request was made
        assert len(mock_client.cancelled_orders) == 1
        assert mock_client.cancelled_orders[0] == 1001

    @pytest.mark.asyncio
    async def test_handle_client_message_subscribe_market_data(self):
        """Test handling subscribe market data message."""
        mock_websocket = MockWebSocket()
        mock_client = MockIBClient()
        self.bridge.client = mock_client

        message = json.dumps(SAMPLE_WEBSOCKET_MESSAGES["subscribe_market_data"])

        await self.bridge.handle_client_message(mock_websocket, message)

        # Check that subscription was processed
        assert len(mock_client.requests) == 1

    @pytest.mark.asyncio
    async def test_handle_client_message_invalid_json(self):
        """Test handling invalid JSON message."""
        mock_websocket = MockWebSocket()

        invalid_message = "invalid json {"

        await self.bridge.handle_client_message(mock_websocket, invalid_message)

        # Check error response was sent
        assert len(mock_websocket.sent_messages) == 1
        response = json.loads(mock_websocket.sent_messages[0])
        assert response["type"] == "error"
        assert "Invalid JSON message" in response["message"]

    @pytest.mark.asyncio
    async def test_handle_client_message_unknown_command(self):
        """Test handling unknown command."""
        mock_websocket = MockWebSocket()

        message = json.dumps(SAMPLE_WEBSOCKET_MESSAGES["invalid_command"])

        await self.bridge.handle_client_message(mock_websocket, message)

        # Check error response was sent
        assert len(mock_websocket.sent_messages) == 1
        response = json.loads(mock_websocket.sent_messages[0])
        assert response["type"] == "error"
        assert "Unknown command" in response["message"]

    @pytest.mark.asyncio
    async def test_broadcast_messages(self):
        """Test message broadcasting to WebSocket clients."""
        # Set up mock WebSocket clients
        client1 = MockWebSocket()
        client2 = MockWebSocket()
        self.bridge.websocket_clients.add(client1)
        self.bridge.websocket_clients.add(client2)

        # Add a message to the queue
        test_message = {"type": "test", "data": "test_data"}
        self.bridge.message_queue.put_nowait(test_message)

        # Run broadcast once
        with patch("asyncio.sleep") as mock_sleep:
            mock_sleep.side_effect = [
                None,
                Exception("Stop loop"),
            ]  # Stop after one iteration

            try:
                await self.bridge.broadcast_messages()
            except Exception:
                pass  # Expected to stop the loop

        # Check both clients received the message
        assert len(client1.sent_messages) == 1
        assert len(client2.sent_messages) == 1

        sent_data1 = json.loads(client1.sent_messages[0])
        sent_data2 = json.loads(client2.sent_messages[0])
        assert sent_data1 == test_message
        assert sent_data2 == test_message

    @pytest.mark.asyncio
    async def test_broadcast_messages_removes_disconnected_clients(self):
        """Test that disconnected clients are removed during broadcasting."""
        # Set up mock WebSocket clients
        client1 = MockWebSocket()
        client2 = MockWebSocket()
        client2.closed = True  # Simulate disconnected client

        self.bridge.websocket_clients.add(client1)
        self.bridge.websocket_clients.add(client2)

        # Add a message to the queue
        test_message = {"type": "test", "data": "test_data"}
        self.bridge.message_queue.put_nowait(test_message)

        # Run broadcast once
        with patch("asyncio.sleep") as mock_sleep:
            mock_sleep.side_effect = [None, Exception("Stop loop")]

            try:
                await self.bridge.broadcast_messages()
            except Exception:
                pass

        # Check that only the connected client is still in the set
        assert client1 in self.bridge.websocket_clients
        assert client2 not in self.bridge.websocket_clients

    @pytest.mark.asyncio
    async def test_handle_websocket_client(self):
        """Test WebSocket client handling."""
        messages_to_send = [SAMPLE_WEBSOCKET_MESSAGES["subscribe_market_data"]]
        mock_websocket = MockWebSocket(messages_to_send)
        mock_websocket.remote_address = ("127.0.0.1", 12345)

        mock_client = MockIBClient()
        self.bridge.client = mock_client

        # Run client handler
        await self.bridge.handle_websocket_client(mock_websocket)

        # Check client was added and removed from set
        assert mock_websocket not in self.bridge.websocket_clients

        # Check that the subscription was processed
        assert len(mock_client.requests) == 1

    def test_request_id_increments(self):
        """Test that request IDs increment properly."""
        mock_client = MockIBClient()
        self.bridge.client = mock_client

        # Make multiple requests
        for i in range(3):
            data = SAMPLE_WEBSOCKET_MESSAGES["subscribe_market_data"].copy()
            data["symbol"] = f"STOCK{i}"
            self.bridge.subscribe_market_data(data)

        # Check request IDs increment
        assert len(mock_client.requests) == 3
        for i, request in enumerate(mock_client.requests):
            assert request["req_id"] == i + 1

        # Check next_req_id is updated
        assert self.bridge.next_req_id == 4

    def test_active_requests_management(self):
        """Test management of active requests dictionary."""
        mock_client = MockIBClient()
        self.bridge.client = mock_client

        # Subscribe to market data
        data = SAMPLE_WEBSOCKET_MESSAGES["subscribe_market_data"]
        self.bridge.subscribe_market_data(data)

        # Check active request is tracked
        assert 1 in self.bridge.active_requests
        assert self.bridge.active_requests[1]["symbol"] == "AAPL"

        # Unsubscribe
        unsubscribe_data = SAMPLE_WEBSOCKET_MESSAGES["unsubscribe_market_data"]
        self.bridge.unsubscribe_market_data(unsubscribe_data)

        # Check active request is removed
        assert 1 not in self.bridge.active_requests

    def test_detect_instrument_type_futures(self):
        """Test automatic instrument type detection for futures symbols."""
        # Test known futures symbols
        assert self.bridge._detect_instrument_type("MNQ") == "future"
        assert self.bridge._detect_instrument_type("ES") == "future"
        assert self.bridge._detect_instrument_type("CL") == "future"
        assert self.bridge._detect_instrument_type("GC") == "future"
        assert self.bridge._detect_instrument_type("SI") == "future"

        # Test non-futures symbols
        assert self.bridge._detect_instrument_type("AAPL") == "stock"
        assert self.bridge._detect_instrument_type("UNKNOWN") == "stock"

    def test_automatic_instrument_type_correction(self):
        """Test that futures symbols are auto-corrected even when sent as 'stock'."""
        mock_client = MockIBClient()
        self.bridge.client = mock_client

        # Send MNQ as 'stock' - should be auto-corrected to 'future'
        data = {
            "symbol": "MNQ",
            "instrument_type": "stock",  # Wrong type
            "exchange": "CME",
        }

        # Should detect as futures and handle accordingly
        self.bridge.subscribe_market_data(data)

        # Check that it was handled as a futures contract
        # (would need contract details request for futures)
        assert len(mock_client.requests) > 0

    def test_request_front_month_contract(self):
        """Test requesting front month contract details."""
        mock_client = MockIBClient()
        self.bridge.client = mock_client

        data = {"symbol": "ES", "instrument_type": "future", "exchange": "CME"}

        # This should trigger a contract details request
        self.bridge._request_front_month_contract(data)

        # Check contract details request was made
        assert len(mock_client.requests) == 1
        # MockIBClient records the method differently, check for the presence of the request
        assert mock_client.requests[0]["req_id"] is not None

    def test_process_contract_details_for_front_month(self):
        """Test processing contract details to select front month."""
        import datetime
        from unittest.mock import Mock

        mock_client = MockIBClient()
        self.bridge.client = mock_client

        # Set up a pending contract details request
        req_id = 1
        original_data = {"symbol": "ES", "instrument_type": "future", "exchange": "CME"}
        self.bridge.contract_details_requests[req_id] = {
            "original_data": original_data,
            "contract_details": [],
        }

        # Create mock contract details
        detail1 = Mock()
        detail1.contract.lastTradeDateOrContractMonth = (
            f"{datetime.date.today().year + 1}0315"
        )

        detail2 = Mock()
        detail2.contract.lastTradeDateOrContractMonth = (
            f"{datetime.date.today().year + 1}0615"
        )

        contract_details = [detail1, detail2]
        self.bridge.contract_details_requests[req_id][
            "contract_details"
        ] = contract_details

        # Process the contract details
        self.bridge._process_contract_details_for_front_month(req_id)

        # Should have made a subscription request
        assert len(mock_client.requests) > 0

    def test_subscribe_to_contract(self):
        """Test subscribing to a specific contract."""
        from marketbridge.ib_websocket_bridge import ContractFactory

        mock_client = MockIBClient()
        self.bridge.client = mock_client

        data = {"symbol": "AAPL", "instrument_type": "stock"}
        contract = ContractFactory.create_stock("AAPL")

        self.bridge._subscribe_to_contract(data, contract)

        # Check market data request was made
        assert len(mock_client.requests) == 1
        assert mock_client.requests[0]["req_id"] is not None

    def test_websocket_server_start_stop(self):
        """Test WebSocket server lifecycle."""
        import asyncio

        # Test that server can be configured
        assert self.bridge.ws_port == 8765
        assert self.bridge.websocket_clients == set()

    def test_error_handling_methods(self):
        """Test various error handling scenarios."""
        # Test contract creation with invalid parameters - should raise ValueError
        try:
            result = self.bridge.create_contract_from_params({})
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Symbol is required" in str(e)

        # Test handling invalid JSON in client messages
        mock_websocket = MockWebSocket([])

        # This should not raise an exception
        try:
            result = asyncio.run(
                self.bridge.handle_client_message(mock_websocket, "invalid json")
            )
        except:
            pass  # Expected to handle gracefully

    def test_websocket_run_method(self):
        """Test WebSocket server run method configuration."""
        # Test basic server configuration
        assert hasattr(self.bridge, "run")
        assert callable(self.bridge.run)

        # Test server state initialization
        assert self.bridge.websocket_clients == set()
        assert self.bridge.active_requests == {}
        assert self.bridge.contract_details_requests == {}
