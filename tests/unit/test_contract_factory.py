"""Unit tests for ContractFactory class."""

from unittest.mock import patch

import pytest
from ibapi.contract import Contract

from marketbridge.ib_websocket_bridge import ContractFactory
from tests.fixtures.test_utils import assert_contract_attributes


class TestContractFactory:
    """Test suite for ContractFactory class."""

    def test_create_stock_with_defaults(self):
        """Test creating a stock contract with default parameters."""
        contract = ContractFactory.create_stock("AAPL")

        assert_contract_attributes(contract, "AAPL", "STK", "SMART", "USD")

    def test_create_stock_with_custom_params(self):
        """Test creating a stock contract with custom parameters."""
        contract = ContractFactory.create_stock(
            symbol="GOOGL", exchange="NASDAQ", currency="USD"
        )

        assert_contract_attributes(contract, "GOOGL", "STK", "NASDAQ", "USD")

    def test_create_future_with_defaults(self):
        """Test creating a futures contract with default parameters."""
        contract = ContractFactory.create_future(symbol="ES", exchange="CME")

        assert_contract_attributes(contract, "ES", "FUT", "CME", "USD")
        assert contract.lastTradeDateOrContractMonth == ""

    def test_create_future_with_expiry(self):
        """Test creating a futures contract with expiry date."""
        contract = ContractFactory.create_future(
            symbol="CL", exchange="NYMEX", currency="USD", last_trade_date="20240315"
        )

        assert_contract_attributes(contract, "CL", "FUT", "NYMEX", "USD")
        assert contract.lastTradeDateOrContractMonth == "20240315"

    def test_create_option_call(self):
        """Test creating a call option contract."""
        contract = ContractFactory.create_option(
            symbol="AAPL", strike=150.0, right="C", expiry="20240315"
        )

        assert_contract_attributes(contract, "AAPL", "OPT", "SMART", "USD")
        assert contract.strike == 150.0
        assert contract.right == "C"
        assert contract.lastTradeDateOrContractMonth == "20240315"

    def test_create_option_put(self):
        """Test creating a put option contract."""
        contract = ContractFactory.create_option(
            symbol="MSFT",
            strike=200.0,
            right="P",
            expiry="20240420",
            exchange="CBOE",
            currency="USD",
        )

        assert_contract_attributes(contract, "MSFT", "OPT", "CBOE", "USD")
        assert contract.strike == 200.0
        assert contract.right == "P"
        assert contract.lastTradeDateOrContractMonth == "20240420"

    def test_create_forex(self):
        """Test creating a forex contract."""
        contract = ContractFactory.create_forex("EUR", "USD")

        assert_contract_attributes(contract, "EUR", "CASH", "IDEALPRO", "USD")

    def test_create_forex_different_pair(self):
        """Test creating a different forex contract."""
        contract = ContractFactory.create_forex("GBP", "JPY")

        assert_contract_attributes(contract, "GBP", "CASH", "IDEALPRO", "JPY")

    def test_create_index_with_defaults(self):
        """Test creating an index contract with default parameters."""
        contract = ContractFactory.create_index("SPX")

        assert_contract_attributes(contract, "SPX", "IND", "CBOE", "USD")

    def test_create_index_with_custom_params(self):
        """Test creating an index contract with custom parameters."""
        contract = ContractFactory.create_index(
            symbol="VIX", exchange="CBOE", currency="USD"
        )

        assert_contract_attributes(contract, "VIX", "IND", "CBOE", "USD")

    def test_create_crypto_with_defaults(self):
        """Test creating a crypto contract with default parameters."""
        contract = ContractFactory.create_crypto("BTC")

        assert_contract_attributes(contract, "BTC", "CRYPTO", "PAXOS", "USD")

    def test_create_crypto_with_custom_params(self):
        """Test creating a crypto contract with custom parameters."""
        contract = ContractFactory.create_crypto(
            symbol="ETH", exchange="PAXOS", currency="USD"
        )

        assert_contract_attributes(contract, "ETH", "CRYPTO", "PAXOS", "USD")

    @patch("marketbridge.ib_websocket_bridge.logger")
    def test_logging_for_contract_creation(self, mock_logger):
        """Test that contract creation includes appropriate logging."""
        ContractFactory.create_stock("AAPL")
        mock_logger.debug.assert_called_with("Created stock contract: AAPL")

        ContractFactory.create_future("ES", "CME")
        mock_logger.debug.assert_called_with(
            "Created futures contract: ES on CME expiry:  multiplier: 50 tradingClass: ES"
        )

        ContractFactory.create_option("AAPL", 150.0, "C", "20240315")
        mock_logger.debug.assert_called_with(
            "Created option contract: AAPL 150.0 C 20240315"
        )

        ContractFactory.create_forex("EUR", "USD")
        mock_logger.debug.assert_called_with("Created forex contract: EUR/USD")

        ContractFactory.create_index("SPX")
        mock_logger.debug.assert_called_with("Created index contract: SPX")

        ContractFactory.create_crypto("BTC")
        mock_logger.debug.assert_called_with("Created crypto contract: BTC")

    def test_contract_is_instance_of_contract_class(self):
        """Test that all factory methods return Contract instances."""
        contracts = [
            ContractFactory.create_stock("AAPL"),
            ContractFactory.create_future("ES", "CME"),
            ContractFactory.create_option("AAPL", 150.0, "C", "20240315"),
            ContractFactory.create_forex("EUR", "USD"),
            ContractFactory.create_index("SPX"),
            ContractFactory.create_crypto("BTC"),
        ]

        for contract in contracts:
            assert isinstance(contract, Contract)

    def test_contract_attributes_are_strings_or_numbers(self):
        """Test that contract attributes have correct types."""
        contract = ContractFactory.create_option("AAPL", 150.5, "C", "20240315")

        assert isinstance(contract.symbol, str)
        assert isinstance(contract.secType, str)
        assert isinstance(contract.exchange, str)
        assert isinstance(contract.currency, str)
        assert isinstance(contract.strike, (int, float))
        assert isinstance(contract.right, str)
        assert isinstance(contract.lastTradeDateOrContractMonth, str)

    def test_empty_string_handling(self):
        """Test handling of empty strings in contract creation."""
        # Test future without expiry date
        contract = ContractFactory.create_future("ES", "CME", last_trade_date="")
        assert contract.lastTradeDateOrContractMonth == ""

        # Test future with None expiry date (should convert to empty string)
        contract = ContractFactory.create_future("ES", "CME")
        assert contract.lastTradeDateOrContractMonth == ""

    def test_create_generic_future(self):
        """Test creating a generic futures contract for contract details requests."""
        contract = ContractFactory.create_generic_future("MNQ", "CME")

        assert_contract_attributes(contract, "MNQ", "FUT", "CME", "USD")
        # Generic future should not have expiry set
        assert (
            not hasattr(contract, "lastTradeDateOrContractMonth")
            or contract.lastTradeDateOrContractMonth == ""
        )

    def test_get_front_month_expiry_with_valid_contracts(self):
        """Test front month detection with valid contract details."""
        import datetime
        from unittest.mock import Mock

        # Use current year and create dates that will definitely be in the future
        current_year = (
            datetime.date.today().year + 1
        )  # Next year to ensure future dates

        # Create mock contract details
        detail1 = Mock()
        detail1.contract.lastTradeDateOrContractMonth = f"{current_year}0315"  # March

        detail2 = Mock()
        detail2.contract.lastTradeDateOrContractMonth = (
            f"{current_year}0615"  # June (later)
        )

        detail3 = Mock()
        detail3.contract.lastTradeDateOrContractMonth = (
            f"{current_year}0115"  # January (earliest)
        )

        contract_details = [detail1, detail2, detail3]

        front_month = ContractFactory.get_front_month_expiry(contract_details)
        assert (
            front_month == f"{current_year}0115"
        )  # Should pick January as it's the earliest (front month)

    def test_get_front_month_expiry_with_empty_list(self):
        """Test front month detection with empty contract list."""
        front_month = ContractFactory.get_front_month_expiry([])
        assert front_month is None

    def test_get_front_month_expiry_with_invalid_dates(self):
        """Test front month detection with invalid date formats."""
        from unittest.mock import Mock

        detail1 = Mock()
        detail1.contract.lastTradeDateOrContractMonth = "invalid"

        detail2 = Mock()
        detail2.contract.lastTradeDateOrContractMonth = "123"  # Too short

        contract_details = [detail1, detail2]

        front_month = ContractFactory.get_front_month_expiry(contract_details)
        assert front_month is None
