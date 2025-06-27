"""Test fixtures and mock data for IBWebSocketBridge tests."""

import time
from unittest.mock import Mock

from ibapi.contract import Contract
from ibapi.order import Order


class MockTickAttrib:
    """Mock tick attributes for testing."""

    def __init__(self, canAutoExecute=True, pastLimit=False, preOpen=False):
        self.canAutoExecute = canAutoExecute
        self.pastLimit = pastLimit
        self.preOpen = preOpen


class MockTickByTickAttrib:
    """Mock tick-by-tick attributes for testing."""

    def __init__(
        self, pastLimit=False, unreported=False, bidPastLow=False, askPastHigh=False
    ):
        self.pastLimit = pastLimit
        self.unreported = unreported
        self.bidPastLow = bidPastLow
        self.askPastHigh = askPastHigh


class MockContractDetails:
    """Mock contract details for testing."""

    def __init__(
        self, contract, market_name="TEST_MARKET", min_tick=0.01, price_magnifier=1
    ):
        self.contract = contract
        self.marketName = market_name
        self.minTick = min_tick
        self.priceMagnifier = price_magnifier


def create_sample_contract(
    symbol="AAPL", sec_type="STK", exchange="SMART", currency="USD"
):
    """Create a sample contract for testing."""
    contract = Contract()
    contract.symbol = symbol
    contract.secType = sec_type
    contract.exchange = exchange
    contract.currency = currency
    contract.localSymbol = symbol
    contract.tradingClass = symbol
    contract.conId = 12345
    contract.multiplier = "1"
    contract.lastTradeDateOrContractMonth = ""
    return contract


def create_sample_order(action="BUY", quantity=100, order_type="MKT", price=None):
    """Create a sample order for testing."""
    order = Order()
    order.action = action
    order.totalQuantity = quantity
    order.orderType = order_type
    if price and order_type == "LMT":
        order.lmtPrice = price
    elif price and order_type == "STP":
        order.auxPrice = price
    return order


# Sample WebSocket messages for testing
SAMPLE_WEBSOCKET_MESSAGES = {
    "subscribe_market_data": {
        "command": "subscribe_market_data",
        "symbol": "AAPL",
        "instrument_type": "stock",
        "exchange": "SMART",
        "currency": "USD",
    },
    "subscribe_time_and_sales": {
        "command": "subscribe_time_and_sales",
        "symbol": "MSFT",
        "instrument_type": "stock",
    },
    "subscribe_bid_ask": {
        "command": "subscribe_bid_ask",
        "symbol": "GOOGL",
        "instrument_type": "stock",
    },
    "place_order": {
        "command": "place_order",
        "symbol": "TSLA",
        "action": "BUY",
        "quantity": 100,
        "order_type": "MKT",
        "instrument_type": "stock",
    },
    "place_limit_order": {
        "command": "place_order",
        "symbol": "NVDA",
        "action": "SELL",
        "quantity": 50,
        "order_type": "LMT",
        "price": 500.00,
        "instrument_type": "stock",
    },
    "get_contract_details": {
        "command": "get_contract_details",
        "symbol": "SPY",
        "instrument_type": "stock",
    },
    "unsubscribe_market_data": {"command": "unsubscribe_market_data", "symbol": "AAPL"},
    "cancel_order": {"command": "cancel_order", "order_id": 1001},
    "invalid_command": {"command": "invalid_test_command", "symbol": "TEST"},
    "missing_symbol": {"command": "subscribe_market_data", "instrument_type": "stock"},
    "option_contract": {
        "command": "subscribe_market_data",
        "symbol": "AAPL",
        "instrument_type": "option",
        "strike": 150.0,
        "right": "C",
        "expiry": "20240315",
    },
    "future_contract": {
        "command": "subscribe_market_data",
        "symbol": "ES",
        "instrument_type": "future",
        "exchange": "CME",
        "expiry": "20240315",
    },
    "forex_contract": {
        "command": "subscribe_market_data",
        "symbol": "EUR",
        "instrument_type": "forex",
        "currency": "USD",
    },
}

# Sample IB callback data
SAMPLE_IB_DATA = {
    "tick_price": {
        "req_id": 1001,
        "tick_type": 1,  # BID
        "price": 150.25,
        "attrib": MockTickAttrib(),
    },
    "tick_size": {"req_id": 1001, "tick_type": 0, "size": 500},  # BID_SIZE
    "tick_string": {
        "req_id": 1001,
        "tick_type": 45,  # LAST_TIMESTAMP
        "value": "1642678800",
    },
    "order_status": {
        "order_id": 2001,
        "status": "Filled",
        "filled": 100,
        "remaining": 0,
        "avg_fill_price": 150.30,
        "perm_id": 1234567890,
        "parent_id": 0,
        "last_fill_price": 150.30,
        "client_id": 1,
        "why_held": "",
        "mkt_cap_price": 0.0,
    },
    "contract_details": {
        "req_id": 3001,
        "contract_details": MockContractDetails(create_sample_contract()),
    },
    "error": {
        "req_id": 4001,
        "error_code": 200,
        "error_string": "No security definition has been found for the request",
        "advanced_order_reject": "",
    },
}

# Expected message formats for testing
EXPECTED_MESSAGE_FORMATS = {
    "connection_status": {
        "type": "connection_status",
        "status": "connected",
        "next_order_id": 1,
        "timestamp": time.time(),
    },
    "market_data_price": {
        "type": "market_data",
        "data_type": "price",
        "req_id": 1001,
        "tick_type": "bid",
        "tick_type_code": 1,
        "price": 150.25,
        "canAutoExecute": True,
        "pastLimit": False,
        "preOpen": False,
        "timestamp": time.time(),
    },
    "market_data_size": {
        "type": "market_data",
        "data_type": "size",
        "req_id": 1001,
        "tick_type": "bid_size",
        "tick_type_code": 0,
        "size": 500,
        "timestamp": time.time(),
    },
    "time_and_sales": {
        "type": "time_and_sales",
        "req_id": 1001,
        "tick_type": "last",
        "trade_time": 1642678800,
        "price": 150.25,
        "size": 100,
        "exchange": "NASDAQ",
        "special_conditions": "",
        "past_limit": False,
        "unreported": False,
        "timestamp": 1642678800,
    },
    "bid_ask_tick": {
        "type": "bid_ask_tick",
        "req_id": 1001,
        "trade_time": 1642678800,
        "bid_price": 150.20,
        "ask_price": 150.30,
        "bid_size": 500,
        "ask_size": 300,
        "bid_past_low": False,
        "ask_past_high": False,
        "timestamp": 1642678800,
    },
    "order_status": {
        "type": "order_status",
        "order_id": 2001,
        "status": "Filled",
        "filled": 100,
        "remaining": 0,
        "avg_fill_price": 150.30,
        "last_fill_price": 150.30,
        "why_held": "",
        "timestamp": time.time(),
    },
    "error": {
        "type": "error",
        "req_id": 4001,
        "error_code": 200,
        "error_string": "No security definition has been found for the request",
        "severity": "ERROR",
        "advanced_order_reject": "",
        "timestamp": time.time(),
    },
}
