"""Integration tests for WebSocket functionality."""

import asyncio
import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest
import websockets
from websockets.exceptions import ConnectionClosed

from marketbridge.ib_websocket_bridge import IBWebSocketBridge
from tests.fixtures.mock_data import SAMPLE_WEBSOCKET_MESSAGES
from tests.fixtures.test_utils import MockIBClient, MockQueue


class TestWebSocketIntegration:
    """Integration tests for WebSocket server and client handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.bridge = IBWebSocketBridge(ib_host="127.0.0.1", ib_port=7497, ws_port=8765)
        # Replace with mock client for testing
        self.bridge.client = MockIBClient()

    @pytest.mark.asyncio
    async def test_websocket_client_connection_lifecycle(self):
        """Test complete WebSocket client connection lifecycle."""
        connected_clients = []
        disconnected_clients = []

        # Mock the handle_websocket_client method to track connections
        original_handler = self.bridge.handle_websocket_client

        async def tracking_handler(websocket, path):
            connected_clients.append(websocket)
            try:
                await original_handler(websocket, path)
            finally:
                disconnected_clients.append(websocket)

        self.bridge.handle_websocket_client = tracking_handler

        # Mock websockets.serve to use our handler
        with patch("websockets.serve") as mock_serve:
            # Create a mock coroutine that returns an awaitable
            async def mock_serve_coro(*args, **kwargs):
                return Mock()

            mock_serve.return_value = mock_serve_coro()

            # Start WebSocket server (without actually binding to port)
            await self.bridge.start_websocket_server()

            # Verify serve was called with correct parameters
            mock_serve.assert_called_once_with(tracking_handler, "localhost", 8765)

    @pytest.mark.asyncio
    async def test_multiple_websocket_clients(self):
        """Test handling multiple WebSocket clients simultaneously."""
        # Create multiple mock WebSocket connections
        num_clients = 3
        mock_clients = []

        for i in range(num_clients):
            mock_client = Mock()
            mock_client.remote_address = (f"127.0.0.{i+1}", 12345 + i)
            mock_client.send = AsyncMock()
            mock_clients.append(mock_client)

        # Add clients to the bridge
        for client in mock_clients:
            self.bridge.websocket_clients.add(client)

        # Add a test message to the queue
        test_message = {"type": "test", "data": "broadcast_test"}
        self.bridge.message_queue.put_nowait(test_message)

        # Run broadcast once
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [
                None,
                Exception("Stop"),
            ]  # Stop after one iteration

            try:
                await self.bridge.broadcast_messages()
            except Exception:
                pass  # Expected to stop the loop

        # Verify all clients received the message
        message_json = json.dumps(test_message)
        for client in mock_clients:
            client.send.assert_called_once_with(message_json)

    @pytest.mark.asyncio
    async def test_websocket_client_message_processing(self):
        """Test processing of messages from WebSocket clients."""
        # Mock WebSocket client
        mock_websocket = Mock()
        mock_websocket.send = AsyncMock()
        mock_websocket.remote_address = ("127.0.0.1", 12345)

        # Test market data subscription message
        message = json.dumps(SAMPLE_WEBSOCKET_MESSAGES["subscribe_market_data"])

        await self.bridge.handle_client_message(mock_websocket, message)

        # Verify the subscription was processed
        assert len(self.bridge.client.requests) == 1
        request = self.bridge.client.requests[0]
        assert request["type"] == "market_data"
        assert request["req_id"] == 1

        # Verify active request tracking
        assert 1 in self.bridge.active_requests
        assert self.bridge.active_requests[1]["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_websocket_error_handling(self):
        """Test WebSocket error handling and client cleanup."""
        # Create mock clients, one that will fail
        good_client = Mock()
        good_client.send = AsyncMock()
        bad_client = Mock()
        bad_client.send = AsyncMock(side_effect=ConnectionClosed(None, None))

        self.bridge.websocket_clients.add(good_client)
        self.bridge.websocket_clients.add(bad_client)

        # Add test message
        test_message = {"type": "test", "data": "error_test"}
        self.bridge.message_queue.put_nowait(test_message)

        # Run broadcast
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, Exception("Stop")]

            try:
                await self.bridge.broadcast_messages()
            except Exception:
                pass

        # Verify good client received message, bad client was removed
        good_client.send.assert_called_once()
        bad_client.send.assert_called_once()

        # Bad client should be removed from the set
        assert good_client in self.bridge.websocket_clients
        assert bad_client not in self.bridge.websocket_clients

    @pytest.mark.asyncio
    async def test_websocket_json_error_response(self):
        """Test WebSocket JSON error response handling."""
        mock_websocket = Mock()
        mock_websocket.send = AsyncMock()

        # Send invalid JSON
        invalid_json = "invalid json {{"

        await self.bridge.handle_client_message(mock_websocket, invalid_json)

        # Verify error response was sent
        mock_websocket.send.assert_called_once()
        sent_message = mock_websocket.send.call_args[0][0]
        error_response = json.loads(sent_message)

        assert error_response["type"] == "error"
        assert "Invalid JSON message" in error_response["message"]
        assert "timestamp" in error_response

    @pytest.mark.asyncio
    async def test_websocket_command_routing(self):
        """Test that WebSocket commands are routed correctly."""
        mock_websocket = Mock()
        mock_websocket.send = AsyncMock()

        # Set up valid order ID for order placement
        self.bridge.wrapper.next_order_id = 2001

        # Test various command types
        commands_to_test = [
            "subscribe_market_data",
            "subscribe_time_and_sales",
            "subscribe_bid_ask",
            "get_contract_details",
            "place_order",
            "unsubscribe_market_data",
        ]

        for command in commands_to_test:
            if command in SAMPLE_WEBSOCKET_MESSAGES:
                message = json.dumps(SAMPLE_WEBSOCKET_MESSAGES[command])
                await self.bridge.handle_client_message(mock_websocket, message)

        # Verify requests were processed (exact number depends on command types)
        assert len(self.bridge.client.requests) > 0

        # Check that some orders were placed if place_order was included
        if "place_order" in commands_to_test:
            assert len(self.bridge.client.orders) > 0

    @pytest.mark.asyncio
    async def test_websocket_message_queue_integration(self):
        """Test integration between message queue and WebSocket broadcasting."""
        # Set up mock client
        mock_client = Mock()
        mock_client.send = AsyncMock()
        self.bridge.websocket_clients.add(mock_client)

        # Add multiple messages to queue
        messages = [
            {"type": "market_data", "symbol": "AAPL", "price": 150.25},
            {"type": "order_status", "order_id": 1001, "status": "Filled"},
            {"type": "error", "code": 200, "message": "Test error"},
        ]

        for msg in messages:
            self.bridge.message_queue.put_nowait(msg)

        # Process messages with broadcast
        processed_count = 0
        max_iterations = len(messages) + 2  # Safety buffer

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

            async def count_and_stop(*args):
                nonlocal processed_count
                processed_count += 1
                if processed_count >= max_iterations:
                    raise Exception("Stop")
                return None

            mock_sleep.side_effect = count_and_stop

            try:
                await self.bridge.broadcast_messages()
            except Exception:
                pass

        # Verify all messages were sent
        assert mock_client.send.call_count == len(messages)

        # Verify message content
        sent_calls = mock_client.send.call_args_list
        for i, call in enumerate(sent_calls):
            sent_message = json.loads(call[0][0])
            assert sent_message == messages[i]

    @pytest.mark.asyncio
    async def test_websocket_concurrent_client_handling(self):
        """Test handling of concurrent WebSocket client operations."""
        # Create multiple mock clients
        clients = []
        for i in range(5):
            client = Mock()
            client.send = AsyncMock()
            client.remote_address = (f"127.0.0.{i+1}", 12345 + i)
            clients.append(client)
            self.bridge.websocket_clients.add(client)

        # Create messages for concurrent sending
        messages = [
            {"type": f"test_message_{i}", "data": f"data_{i}"} for i in range(10)
        ]

        # Add all messages to queue
        for msg in messages:
            self.bridge.message_queue.put_nowait(msg)

        # Process with broadcast
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            call_count = 0

            async def limit_calls(*args):
                nonlocal call_count
                call_count += 1
                if call_count >= 15:  # Enough iterations to process all messages
                    raise Exception("Stop")
                return None

            mock_sleep.side_effect = limit_calls

            try:
                await self.bridge.broadcast_messages()
            except Exception:
                pass

        # Verify all clients received all messages
        for client in clients:
            assert client.send.call_count == len(messages)

    @pytest.mark.asyncio
    async def test_websocket_client_disconnect_during_processing(self):
        """Test handling client disconnection during message processing."""
        # Mock client that fails after first message
        failing_client = Mock()
        call_count = 0

        async def failing_send(*args):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise ConnectionClosed(None, None)
            return None

        failing_client.send = failing_send

        # Add good client too
        good_client = Mock()
        good_client.send = AsyncMock()

        self.bridge.websocket_clients.add(failing_client)
        self.bridge.websocket_clients.add(good_client)

        # Add multiple messages
        for i in range(3):
            self.bridge.message_queue.put_nowait({"type": "test", "count": i})

        # Run broadcast
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            iteration = 0

            async def count_iterations(*args):
                nonlocal iteration
                iteration += 1
                if iteration >= 5:  # Process enough iterations
                    raise Exception("Stop")
                return None

            mock_sleep.side_effect = count_iterations

            try:
                await self.bridge.broadcast_messages()
            except Exception:
                pass

        # Verify failing client was removed
        assert failing_client not in self.bridge.websocket_clients
        assert good_client in self.bridge.websocket_clients

        # Good client should have received all messages
        assert good_client.send.call_count == 3
