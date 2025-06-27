"""Unit tests for IBWrapper class."""

import logging
import queue
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from marketbridge.ib_websocket_bridge import IBWrapper
from tests.fixtures.mock_data import (
    EXPECTED_MESSAGE_FORMATS,
    SAMPLE_IB_DATA,
    MockContractDetails,
    MockTickAttrib,
    MockTickByTickAttrib,
    create_sample_contract,
)
from tests.fixtures.test_utils import MockQueue, assert_message_structure


class TestIBWrapper:
    """Test suite for IBWrapper class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_queue = MockQueue()
        self.wrapper = IBWrapper(self.mock_queue)

    def test_init(self):
        """Test IBWrapper initialization."""
        assert self.wrapper.message_queue == self.mock_queue
        assert self.wrapper.next_order_id is None

    def test_next_valid_id(self):
        """Test nextValidId callback."""
        order_id = 1001

        self.wrapper.nextValidId(order_id)

        assert self.wrapper.next_order_id == order_id
        assert self.mock_queue.qsize() == 1

        message = self.mock_queue.get_nowait()
        assert_message_structure(
            message, ["type", "status", "next_order_id", "timestamp"]
        )
        assert message["type"] == "connection_status"
        assert message["status"] == "connected"
        assert message["next_order_id"] == order_id

    def test_tick_price_with_important_tick_type(self):
        """Test tickPrice callback with important tick type."""
        req_id = 1001
        tick_type = 1  # BID
        price = 150.25
        attrib = MockTickAttrib()

        self.wrapper.tickPrice(req_id, tick_type, price, attrib)

        assert self.mock_queue.qsize() == 1
        message = self.mock_queue.get_nowait()

        expected_keys = [
            "type",
            "data_type",
            "req_id",
            "tick_type",
            "tick_type_code",
            "price",
            "timestamp",
        ]
        assert_message_structure(message, expected_keys)
        assert message["type"] == "market_data"
        assert message["data_type"] == "price"
        assert message["req_id"] == req_id
        assert message["tick_type"] == "bid"
        assert message["tick_type_code"] == tick_type
        assert message["price"] == price
        assert message["canAutoExecute"] == attrib.canAutoExecute
        assert message["pastLimit"] == attrib.pastLimit
        assert message["preOpen"] == attrib.preOpen

    def test_tick_price_with_none_attrib(self):
        """Test tickPrice callback with None attributes."""
        req_id = 1001
        tick_type = 4  # LAST
        price = 150.50

        self.wrapper.tickPrice(req_id, tick_type, price, None)

        message = self.mock_queue.get_nowait()
        assert message["canAutoExecute"] is None
        assert message["pastLimit"] is None
        assert message["preOpen"] is None

    def test_tick_price_ignored_tick_type(self):
        """Test tickPrice callback with unimportant tick type that should be ignored."""
        req_id = 1001
        tick_type = 100  # High tick type that should be ignored
        price = 150.25

        self.wrapper.tickPrice(req_id, tick_type, price, None)

        # Should still process since tickType <= 50 check includes many tick types
        assert (
            self.mock_queue.qsize() == 0
        )  # This specific tick type > 50 and not in important_ticks

    def test_tick_size_with_important_size_tick(self):
        """Test tickSize callback with important size tick type."""
        req_id = 1001
        tick_type = 0  # BID_SIZE
        size = 500

        self.wrapper.tickSize(req_id, tick_type, size)

        assert self.mock_queue.qsize() == 1
        message = self.mock_queue.get_nowait()

        expected_keys = [
            "type",
            "data_type",
            "req_id",
            "tick_type",
            "tick_type_code",
            "size",
            "timestamp",
        ]
        assert_message_structure(message, expected_keys)
        assert message["type"] == "market_data"
        assert message["data_type"] == "size"
        assert message["tick_type"] == "bid_size"
        assert message["size"] == size

    def test_tick_string(self):
        """Test tickString callback."""
        req_id = 1001
        tick_type = 45  # LAST_TIMESTAMP
        value = "1642678800"

        self.wrapper.tickString(req_id, tick_type, value)

        assert self.mock_queue.qsize() == 1
        message = self.mock_queue.get_nowait()

        expected_keys = [
            "type",
            "data_type",
            "req_id",
            "tick_type",
            "tick_type_code",
            "value",
            "timestamp",
        ]
        assert_message_structure(message, expected_keys)
        assert message["type"] == "market_data"
        assert message["data_type"] == "string"
        assert message["value"] == value

    def test_tick_by_tick_all_last(self):
        """Test tickByTickAllLast callback."""
        req_id = 1001
        tick_type = 1
        trade_time = 1642678800
        price = 150.25
        size = 100
        tick_attribs = MockTickByTickAttrib()
        exchange = "NASDAQ"
        special_conditions = ""

        self.wrapper.tickByTickAllLast(
            req_id,
            tick_type,
            trade_time,
            price,
            size,
            tick_attribs,
            exchange,
            special_conditions,
        )

        assert self.mock_queue.qsize() == 1
        message = self.mock_queue.get_nowait()

        expected_keys = [
            "type",
            "req_id",
            "tick_type",
            "trade_time",
            "price",
            "size",
            "exchange",
            "timestamp",
        ]
        assert_message_structure(message, expected_keys)
        assert message["type"] == "time_and_sales"
        assert message["tick_type"] == "last"
        assert message["trade_time"] == trade_time
        assert message["price"] == price
        assert message["size"] == size
        assert message["exchange"] == exchange

    def test_tick_by_tick_bid_ask(self):
        """Test tickByTickBidAsk callback."""
        req_id = 1001
        trade_time = 1642678800
        bid_price = 150.20
        ask_price = 150.30
        bid_size = 500
        ask_size = 300
        tick_attribs = MockTickByTickAttrib()

        self.wrapper.tickByTickBidAsk(
            req_id, trade_time, bid_price, ask_price, bid_size, ask_size, tick_attribs
        )

        assert self.mock_queue.qsize() == 1
        message = self.mock_queue.get_nowait()

        expected_keys = [
            "type",
            "req_id",
            "trade_time",
            "bid_price",
            "ask_price",
            "bid_size",
            "ask_size",
            "timestamp",
        ]
        assert_message_structure(message, expected_keys)
        assert message["type"] == "bid_ask_tick"
        assert message["bid_price"] == bid_price
        assert message["ask_price"] == ask_price
        assert message["bid_size"] == bid_size
        assert message["ask_size"] == ask_size

    def test_tick_by_tick_midpoint(self):
        """Test tickByTickMidPoint callback."""
        req_id = 1001
        trade_time = 1642678800
        midpoint = 150.25

        self.wrapper.tickByTickMidPoint(req_id, trade_time, midpoint)

        assert self.mock_queue.qsize() == 1
        message = self.mock_queue.get_nowait()

        expected_keys = ["type", "req_id", "trade_time", "midpoint", "timestamp"]
        assert_message_structure(message, expected_keys)
        assert message["type"] == "midpoint_tick"
        assert message["midpoint"] == midpoint

    def test_order_status(self):
        """Test orderStatus callback."""
        order_id = 2001
        status = "Filled"
        filled = 100
        remaining = 0
        avg_fill_price = 150.30
        perm_id = 1234567890
        parent_id = 0
        last_fill_price = 150.30
        client_id = 1
        why_held = ""
        mkt_cap_price = 0.0

        self.wrapper.orderStatus(
            order_id,
            status,
            filled,
            remaining,
            avg_fill_price,
            perm_id,
            parent_id,
            last_fill_price,
            client_id,
            why_held,
            mkt_cap_price,
        )

        assert self.mock_queue.qsize() == 1
        message = self.mock_queue.get_nowait()

        expected_keys = [
            "type",
            "order_id",
            "status",
            "filled",
            "remaining",
            "avg_fill_price",
            "last_fill_price",
            "timestamp",
        ]
        assert_message_structure(message, expected_keys)
        assert message["type"] == "order_status"
        assert message["order_id"] == order_id
        assert message["status"] == status
        assert message["filled"] == filled
        assert message["remaining"] == remaining

    def test_contract_details(self):
        """Test contractDetails callback."""
        req_id = 3001
        contract = create_sample_contract()
        contract_details = MockContractDetails(contract)

        self.wrapper.contractDetails(req_id, contract_details)

        assert self.mock_queue.qsize() == 1
        message = self.mock_queue.get_nowait()

        expected_keys = [
            "type",
            "req_id",
            "contract",
            "market_name",
            "min_tick",
            "price_magnifier",
            "timestamp",
        ]
        assert_message_structure(message, expected_keys)
        assert message["type"] == "contract_details"
        assert message["req_id"] == req_id
        assert isinstance(message["contract"], dict)
        assert message["contract"]["symbol"] == contract.symbol
        assert message["market_name"] == contract_details.marketName

    def test_contract_details_end(self):
        """Test contractDetailsEnd callback."""
        req_id = 3001

        self.wrapper.contractDetailsEnd(req_id)

        assert self.mock_queue.qsize() == 1
        message = self.mock_queue.get_nowait()

        expected_keys = ["type", "req_id", "timestamp"]
        assert_message_structure(message, expected_keys)
        assert message["type"] == "contract_details_end"
        assert message["req_id"] == req_id

    def test_error_with_different_severity_levels(self):
        """Test error callback with different severity levels."""
        req_id = 4001

        # Test ERROR severity (code < 2000)
        self.wrapper.error(req_id, 200, "Error message")
        message1 = self.mock_queue.get_nowait()
        assert message1["severity"] == "ERROR"

        # Test WARNING severity (2000 <= code < 10000)
        self.wrapper.error(req_id, 2104, "Warning message")
        message2 = self.mock_queue.get_nowait()
        assert message2["severity"] == "WARNING"

        # Test INFO severity (code >= 10000)
        self.wrapper.error(req_id, 10001, "Info message")
        message3 = self.mock_queue.get_nowait()
        assert message3["severity"] == "INFO"

    def test_send_message_with_full_queue(self):
        """Test send_message behavior when queue is full."""
        # Fill the queue to capacity
        full_queue = MockQueue(maxsize=2)
        full_queue.put_nowait("item1")
        full_queue.put_nowait("item2")

        wrapper = IBWrapper(full_queue)

        # This should not raise an exception but should log a warning
        with patch("marketbridge.ib_websocket_bridge.logger") as mock_logger:
            wrapper.send_message({"test": "message"})
            mock_logger.warning.assert_called_with(
                "Message queue full, dropping message"
            )

        # Queue should still be full with original items
        assert full_queue.qsize() == 2
        assert full_queue.full_count == 1

    @patch("marketbridge.ib_websocket_bridge.logger")
    def test_logging_calls(self, mock_logger):
        """Test that appropriate logging calls are made."""
        # Test initialization logging
        IBWrapper(self.mock_queue)
        mock_logger.info.assert_called_with("IBWrapper initialized")

        # Test nextValidId logging
        self.wrapper.nextValidId(1001)
        mock_logger.info.assert_called_with("Received next valid order ID: 1001")

        # Test orderStatus logging
        self.wrapper.orderStatus(
            2001, "Filled", 100, 0, 150.30, 1234, 0, 150.30, 1, "", 0.0
        )
        mock_logger.info.assert_called_with(
            "Order status - ID: 2001, Status: Filled, Filled: 100, Remaining: 0"
        )

    @patch("time.time")
    def test_timestamp_consistency(self, mock_time):
        """Test that timestamps are added consistently to messages."""
        mock_time.return_value = 1642678800.123

        self.wrapper.nextValidId(1001)
        message = self.mock_queue.get_nowait()

        assert message["timestamp"] == 1642678800.123

    def test_tick_type_enum_conversion(self):
        """Test that tick type enums are properly converted to strings."""
        with patch(
            "marketbridge.ib_websocket_bridge.TickTypeEnum.to_str"
        ) as mock_to_str:
            mock_to_str.return_value = "BID"

            self.wrapper.tickPrice(1001, 1, 150.25, None)

            mock_to_str.assert_called_with(1)
