import asyncio
import json
import logging
import queue
import threading
import time
from datetime import datetime

import websockets
from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.ticktype import TickTypeEnum
from ibapi.wrapper import EWrapper

# Configure logging with detailed format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class ContractFactory:
    """Factory for creating different types of contracts"""

    @staticmethod
    def create_stock(symbol, exchange="SMART", currency="USD"):
        """Create a stock contract"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = exchange
        contract.currency = currency
        logger.debug(f"Created stock contract: {symbol}")
        return contract

    @staticmethod
    def create_future(symbol, exchange, currency="USD", last_trade_date=""):
        """Create a futures contract"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "FUT"
        contract.exchange = exchange
        contract.currency = currency
        if last_trade_date:
            contract.lastTradeDateOrContractMonth = last_trade_date
        logger.debug(
            f"Created futures contract: {symbol} on {exchange} expiry: {last_trade_date}"
        )
        return contract

    @staticmethod
    def create_generic_future(symbol, exchange, currency="USD"):
        """Create a generic futures contract for contract details request"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "FUT"
        contract.exchange = exchange
        contract.currency = currency
        # No expiry specified - used for contract details requests
        logger.debug(f"Created generic futures contract: {symbol} on {exchange}")
        return contract

    @staticmethod
    def get_front_month_expiry(contract_details_list):
        """Determine front month from contract details list"""
        if not contract_details_list:
            return None

        # Filter for contracts that are likely active (not expired)
        import datetime

        today = datetime.date.today()

        valid_contracts = []
        for detail in contract_details_list:
            try:
                # Parse contract month (format: YYYYMM or YYYYMMDD)
                contract_month = detail.contract.lastTradeDateOrContractMonth
                if len(contract_month) >= 6:
                    year = int(contract_month[:4])
                    month = int(contract_month[4:6])
                    contract_date = datetime.date(year, month, 1)

                    # Only include contracts that haven't expired
                    if contract_date >= today.replace(day=1):
                        valid_contracts.append((contract_date, contract_month, detail))
            except (ValueError, IndexError) as e:
                logger.debug(f"Could not parse contract month {contract_month}: {e}")
                continue

        if not valid_contracts:
            logger.warning("No valid future contracts found")
            return None

        # Sort by date and return the nearest expiry (front month)
        valid_contracts.sort(key=lambda x: x[0])
        front_month = valid_contracts[0][1]

        logger.info(f"Selected front month contract: {front_month}")
        return front_month

    @staticmethod
    def create_option(symbol, strike, right, expiry, exchange="SMART", currency="USD"):
        """Create an options contract"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "OPT"
        contract.exchange = exchange
        contract.currency = currency
        contract.strike = strike
        contract.right = right  # 'C' for Call, 'P' for Put
        contract.lastTradeDateOrContractMonth = expiry
        logger.debug(f"Created option contract: {symbol} {strike} {right} {expiry}")
        return contract

    @staticmethod
    def create_forex(base_currency, quote_currency):
        """Create a forex contract"""
        contract = Contract()
        contract.symbol = base_currency
        contract.secType = "CASH"
        contract.currency = quote_currency
        contract.exchange = "IDEALPRO"
        logger.debug(f"Created forex contract: {base_currency}/{quote_currency}")
        return contract

    @staticmethod
    def create_index(symbol, exchange="CBOE", currency="USD"):
        """Create an index contract"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "IND"
        contract.exchange = exchange
        contract.currency = currency
        logger.debug(f"Created index contract: {symbol}")
        return contract

    @staticmethod
    def create_crypto(symbol, exchange="PAXOS", currency="USD"):
        """Create a cryptocurrency contract"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "CRYPTO"
        contract.exchange = exchange
        contract.currency = currency
        logger.debug(f"Created crypto contract: {symbol}")
        return contract


class IBWrapper(EWrapper):
    """Handles callbacks from IB TWS API"""

    def __init__(self, message_queue):
        EWrapper.__init__(self)
        self.message_queue = message_queue
        self.next_order_id = None
        self.bridge = None  # Will be set by IBWebSocketBridge
        logger.info("IBWrapper initialized")

    def nextValidId(self, orderId):
        """Receives next valid order ID"""
        self.next_order_id = orderId
        logger.info(f"Received next valid order ID: {orderId}")
        self.send_message(
            {
                "type": "connection_status",
                "status": "connected",
                "next_order_id": orderId,
                "timestamp": time.time(),
            }
        )

    def tickPrice(self, reqId, tickType, price, attrib):
        """Receives real-time price data"""
        tick_type_name = TickTypeEnum.to_str(tickType)

        # Map important tick types
        important_ticks = {
            1: "bid",  # BID
            2: "ask",  # ASK
            4: "last",  # LAST
            6: "high",  # HIGH
            7: "low",  # LOW
            9: "close",  # CLOSE
            14: "open",  # OPEN
            15: "low_13_week",  # LOW_13_WEEK
            16: "high_13_week",  # HIGH_13_WEEK
            17: "low_26_week",  # LOW_26_WEEK
            18: "high_26_week",  # HIGH_26_WEEK
            19: "low_52_week",  # LOW_52_WEEK
            20: "high_52_week",  # HIGH_52_WEEK
            21: "avg_volume",  # AVG_VOLUME
            35: "auction_volume",  # AUCTION_VOLUME
            37: "mark_price",  # MARK_PRICE
        }

        if tickType in important_ticks or tickType <= 50:  # Include common tick types
            logger.debug(
                f"Price tick - ReqId: {reqId}, Type: {tick_type_name}({tickType}), Price: {price}"
            )

            self.send_message(
                {
                    "type": "market_data",
                    "data_type": "price",
                    "req_id": reqId,
                    "tick_type": important_ticks.get(tickType, tick_type_name.lower()),
                    "tick_type_code": tickType,
                    "price": price,
                    "canAutoExecute": attrib.canAutoExecute if attrib else None,
                    "pastLimit": attrib.pastLimit if attrib else None,
                    "preOpen": attrib.preOpen if attrib else None,
                    "timestamp": time.time(),
                }
            )

    def tickSize(self, reqId, tickType, size):
        """Receives real-time size data"""
        tick_type_name = TickTypeEnum.to_str(tickType)

        # Map important size tick types
        size_ticks = {
            0: "bid_size",  # BID_SIZE
            3: "ask_size",  # ASK_SIZE
            5: "last_size",  # LAST_SIZE
            8: "volume",  # VOLUME
            21: "avg_volume",  # AVG_VOLUME
            27: "call_open_interest",  # CALL_OPEN_INTEREST
            28: "put_open_interest",  # PUT_OPEN_INTEREST
            29: "call_volume",  # CALL_VOLUME
            30: "put_volume",  # PUT_VOLUME
        }

        if tickType in size_ticks or tickType <= 50:
            logger.debug(
                f"Size tick - ReqId: {reqId}, Type: {tick_type_name}({tickType}), Size: {size}"
            )

            self.send_message(
                {
                    "type": "market_data",
                    "data_type": "size",
                    "req_id": reqId,
                    "tick_type": size_ticks.get(tickType, tick_type_name.lower()),
                    "tick_type_code": tickType,
                    "size": size,
                    "timestamp": time.time(),
                }
            )

    def tickString(self, reqId, tickType, value):
        """Receives string-based tick data"""
        tick_type_name = TickTypeEnum.to_str(tickType)
        logger.debug(
            f"String tick - ReqId: {reqId}, Type: {tick_type_name}({tickType}), Value: {value}"
        )

        self.send_message(
            {
                "type": "market_data",
                "data_type": "string",
                "req_id": reqId,
                "tick_type": tick_type_name.lower(),
                "tick_type_code": tickType,
                "value": value,
                "timestamp": time.time(),
            }
        )

    def tickByTickAllLast(
        self,
        reqId,
        tickType,
        time,
        price,
        size,
        tickAtrributes,
        exchange,
        specialConditions,
    ):
        """Receives time and sales data (all last trades)"""
        logger.debug(
            f"Time & Sales - ReqId: {reqId}, Time: {time}, Price: {price}, Size: {size}, Exchange: {exchange}"
        )

        self.send_message(
            {
                "type": "time_and_sales",
                "req_id": reqId,
                "tick_type": "last",
                "trade_time": time,
                "price": price,
                "size": size,
                "exchange": exchange,
                "special_conditions": specialConditions,
                "past_limit": tickAtrributes.pastLimit if tickAtrributes else None,
                "unreported": tickAtrributes.unreported if tickAtrributes else None,
                "timestamp": time,
            }
        )

    def tickByTickBidAsk(
        self, reqId, time, bidPrice, askPrice, bidSize, askSize, tickAttribs
    ):
        """Receives tick-by-tick bid/ask data"""
        logger.debug(
            f"Bid/Ask Tick - ReqId: {reqId}, Time: {time}, Bid: {bidPrice}x{bidSize}, Ask: {askPrice}x{askSize}"
        )

        self.send_message(
            {
                "type": "bid_ask_tick",
                "req_id": reqId,
                "trade_time": time,
                "bid_price": bidPrice,
                "ask_price": askPrice,
                "bid_size": bidSize,
                "ask_size": askSize,
                "bid_past_low": tickAttribs.bidPastLow if tickAttribs else None,
                "ask_past_high": tickAttribs.askPastHigh if tickAttribs else None,
                "timestamp": time,
            }
        )

    def tickByTickMidPoint(self, reqId, time, midPoint):
        """Receives tick-by-tick midpoint data"""
        logger.debug(
            f"Midpoint Tick - ReqId: {reqId}, Time: {time}, Midpoint: {midPoint}"
        )

        self.send_message(
            {
                "type": "midpoint_tick",
                "req_id": reqId,
                "trade_time": time,
                "midpoint": midPoint,
                "timestamp": time,
            }
        )

    def orderStatus(
        self,
        orderId,
        status,
        filled,
        remaining,
        avgFillPrice,
        permId,
        parentId,
        lastFillPrice,
        clientId,
        whyHeld,
        mktCapPrice,
    ):
        """Receives order status updates"""
        logger.info(
            f"Order status - ID: {orderId}, Status: {status}, Filled: {filled}, Remaining: {remaining}"
        )

        self.send_message(
            {
                "type": "order_status",
                "order_id": orderId,
                "status": status,
                "filled": filled,
                "remaining": remaining,
                "avg_fill_price": avgFillPrice,
                "last_fill_price": lastFillPrice,
                "why_held": whyHeld,
                "timestamp": time.time(),
            }
        )

    def contractDetails(self, reqId, contractDetails):
        """Receives contract details"""
        contract = contractDetails.contract
        logger.debug(
            f"Contract details - ReqId: {reqId}, Symbol: {contract.symbol}, SecType: {contract.secType}, Expiry: {contract.lastTradeDateOrContractMonth}"
        )

        # Check if this is a front month detection request
        if self.bridge and reqId in self.bridge.contract_details_requests:
            # Store contract details for front month processing
            self.bridge.contract_details_requests[reqId]["contract_details"].append(
                contractDetails
            )

        # Always send to WebSocket clients as well
        self.send_message(
            {
                "type": "contract_details",
                "req_id": reqId,
                "contract": {
                    "symbol": contract.symbol,
                    "sec_type": contract.secType,
                    "exchange": contract.exchange,
                    "currency": contract.currency,
                    "local_symbol": contract.localSymbol,
                    "trading_class": contract.tradingClass,
                    "con_id": contract.conId,
                    "multiplier": contract.multiplier,
                    "last_trade_date": contract.lastTradeDateOrContractMonth,
                },
                "market_name": contractDetails.marketName,
                "min_tick": contractDetails.minTick,
                "price_magnifier": contractDetails.priceMagnifier,
                "timestamp": time.time(),
            }
        )

    def contractDetailsEnd(self, reqId):
        """Called when contract details request is complete"""
        logger.debug(f"Contract details end - ReqId: {reqId}")

        # Check if this is a front month detection request
        if self.bridge and reqId in self.bridge.contract_details_requests:
            # Process front month detection
            self.bridge._process_contract_details_for_front_month(reqId)

        self.send_message(
            {"type": "contract_details_end", "req_id": reqId, "timestamp": time.time()}
        )

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        """Handles errors from IB"""
        severity = (
            "ERROR" if errorCode < 2000 else "WARNING" if errorCode < 10000 else "INFO"
        )
        logger.log(
            getattr(logging, severity, logging.ERROR),
            f"IB Error - ReqId: {reqId}, Code: {errorCode}, Message: {errorString}",
        )

        self.send_message(
            {
                "type": "error",
                "req_id": reqId,
                "error_code": errorCode,
                "error_string": errorString,
                "severity": severity,
                "advanced_order_reject": advancedOrderRejectJson,
                "timestamp": time.time(),
            }
        )

    def send_message(self, message):
        """Thread-safe message sending to WebSocket clients"""
        try:
            self.message_queue.put_nowait(message)
        except queue.Full:
            logger.warning("Message queue full, dropping message")


class IBClient(EClient):
    """IB API client with custom methods"""

    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)
        self.wrapper = wrapper
        logger.info("IBClient initialized")


class IBWebSocketBridge:
    """Main bridge class coordinating IB API and WebSocket connections"""

    def __init__(self, ib_host="127.0.0.1", ib_port=7497, ws_port=8765):
        self.ib_host = ib_host
        self.ib_port = ib_port
        self.ws_port = ws_port

        # Message queue for thread-safe communication
        self.message_queue = queue.Queue(maxsize=10000)

        # WebSocket clients
        self.websocket_clients = set()

        # IB API setup
        self.wrapper = IBWrapper(self.message_queue)
        self.wrapper.bridge = self  # Give wrapper access to bridge methods
        self.client = IBClient(self.wrapper)

        # Request ID tracking
        self.next_req_id = 1
        self.active_requests = {}

        # Contract details tracking for front month detection
        self.contract_details_requests = {}
        self.pending_market_data_requests = {}

        # Shutdown control
        self.shutdown_event = asyncio.Event()
        self.is_running = False

        # Background tasks tracking
        self.tasks = []
        self.websocket_server = None
        self.api_thread = None

        logger.info(
            f"IBWebSocketBridge initialized - IB: {ib_host}:{ib_port}, WS: {ws_port}"
        )

    def connect_to_ib(self):
        """Connect to IB TWS/Gateway"""
        try:
            self.client.connect(self.ib_host, self.ib_port, clientId=1)

            # Start the IB API message loop in separate thread
            self.api_thread = threading.Thread(target=self.client.run, daemon=True)
            self.api_thread.start()

            logger.info(f"Connected to IB at {self.ib_host}:{self.ib_port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IB: {e}")
            return False

    async def handle_websocket_client(self, websocket):
        """Handle new WebSocket client connection"""
        client_addr = websocket.remote_address
        logger.info(f"New WebSocket client connected: {client_addr}")
        self.websocket_clients.add(websocket)

        try:
            async for message in websocket:
                await self.handle_client_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket client disconnected: {client_addr}")
        except Exception as e:
            logger.error(f"Error handling WebSocket client {client_addr}: {e}")
        finally:
            self.websocket_clients.discard(websocket)

    async def handle_client_message(self, websocket, message):
        """Process messages from WebSocket clients"""
        try:
            data = json.loads(message)
            command = data.get("command")
            logger.debug(f"Received command: {command}")

            if command == "subscribe_market_data":
                self.subscribe_market_data(data)
            elif command == "unsubscribe_market_data":
                self.unsubscribe_market_data(data)
            elif command == "subscribe_time_and_sales":
                self.subscribe_time_and_sales(data)
            elif command == "unsubscribe_time_and_sales":
                self.unsubscribe_time_and_sales(data)
            elif command == "subscribe_bid_ask":
                self.subscribe_bid_ask(data)
            elif command == "unsubscribe_bid_ask":
                self.unsubscribe_bid_ask(data)
            elif command == "place_order":
                self.place_order(data)
            elif command == "cancel_order":
                self.cancel_order(data)
            elif command == "get_contract_details":
                self.get_contract_details(data)
            else:
                logger.warning(f"Unknown command: {command}")
                await websocket.send(
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"Unknown command: {command}",
                            "timestamp": time.time(),
                        }
                    )
                )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON message: {e}")
            await websocket.send(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Invalid JSON message",
                        "timestamp": time.time(),
                    }
                )
            )
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await websocket.send(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Error processing message: {str(e)}",
                        "timestamp": time.time(),
                    }
                )
            )

    def create_contract_from_params(self, params):
        """Create a contract based on instrument parameters"""
        instrument_type = params.get("instrument_type", "stock").lower()
        symbol = params.get("symbol")

        if not symbol:
            raise ValueError("Symbol is required")

        if instrument_type == "stock":
            return ContractFactory.create_stock(
                symbol, params.get("exchange", "SMART"), params.get("currency", "USD")
            )
        elif instrument_type == "future":
            return ContractFactory.create_future(
                symbol,
                params.get("exchange", "CME"),  # Default to CME
                params.get("currency", "USD"),
                params.get("expiry", ""),
            )
        elif instrument_type == "option":
            return ContractFactory.create_option(
                symbol,
                params.get("strike"),
                params.get("right"),  # 'C' or 'P'
                params.get("expiry"),
                params.get("exchange", "SMART"),
                params.get("currency", "USD"),
            )
        elif instrument_type == "forex":
            return ContractFactory.create_forex(symbol, params.get("currency", "USD"))
        elif instrument_type == "index":
            return ContractFactory.create_index(
                symbol, params.get("exchange", "CBOE"), params.get("currency", "USD")
            )
        elif instrument_type == "crypto":
            return ContractFactory.create_crypto(
                symbol, params.get("exchange", "PAXOS"), params.get("currency", "USD")
            )
        else:
            raise ValueError(f"Unsupported instrument type: {instrument_type}")

    def subscribe_market_data(self, data):
        """Subscribe to market data for any instrument type"""
        try:
            symbol = data.get("symbol")
            instrument_type = data.get("instrument_type", "stock").lower()

            # Auto-detect instrument type for common futures if not specified correctly
            if instrument_type == "stock":
                detected_type = self._detect_instrument_type(symbol)
                if detected_type != "stock":
                    logger.info(
                        f"Auto-detected {symbol} as {detected_type} instead of stock"
                    )
                    instrument_type = detected_type
                    data = data.copy()  # Don't modify original
                    data["instrument_type"] = detected_type

            # For futures without explicit expiry, need to find front month first
            if instrument_type == "future" and not data.get("expiry"):
                logger.info(f"Finding front month contract for {symbol}")
                self._request_front_month_contract(data)
                return

            # For all other cases, create contract directly
            contract = self.create_contract_from_params(data)
            self._subscribe_to_contract(data, contract)

        except Exception as e:
            logger.error(f"Error subscribing to market data: {e}")

    def _detect_instrument_type(self, symbol):
        """Auto-detect instrument type based on symbol"""
        if not symbol:
            return "stock"

        # Common futures symbols
        futures_symbols = {
            # E-mini futures
            "ES",
            "NQ",
            "YM",
            "RTY",
            # Micro E-mini futures
            "MES",
            "MNQ",
            "MYM",
            "M2K",
            # Commodity futures
            "CL",
            "NG",
            "GC",
            "SI",
            "HG",
            "PL",
            "PA",
            # Agricultural futures
            "ZC",
            "ZS",
            "ZW",
            "ZL",
            "ZM",
            "KC",
            "SB",
            "CC",
            "CT",
            # Interest rate futures
            "ZB",
            "ZN",
            "ZF",
            "ZT",
            # Currency futures
            "6E",
            "6B",
            "6J",
            "6A",
            "6C",
            "6S",
            # Energy futures
            "RB",
            "HO",
            "BZ",
            # Metal futures
            "HG",
            "ZG",
            "ZI",
            "ZC",
            # Livestock futures
            "LE",
            "GF",
            "HE",
        }

        # Check if symbol is a known futures symbol
        if symbol.upper() in futures_symbols:
            return "future"

        # Check for forex pairs (like EURUSD, GBPUSD, etc.)
        if len(symbol) == 6 and symbol.upper().isalpha():
            return "forex"

        # Default to stock
        return "stock"

    def _request_front_month_contract(self, data):
        """Request contract details to find front month for futures"""
        try:
            # Create generic contract for contract details request
            generic_contract = ContractFactory.create_generic_future(
                data.get("symbol"),
                data.get("exchange", "CME"),
                data.get("currency", "USD"),
            )

            req_id = self.next_req_id
            self.next_req_id += 1

            # Store the original request data to use after we get contract details
            self.contract_details_requests[req_id] = {
                "original_data": data,
                "contract_details": [],
            }

            logger.debug(
                f"Requesting contract details for {data.get('symbol')} - req_id: {req_id}"
            )
            self.client.reqContractDetails(req_id, generic_contract)

        except Exception as e:
            logger.error(f"Error requesting contract details: {e}")

    def _subscribe_to_contract(self, data, contract):
        """Subscribe to market data for a specific contract"""
        req_id = self.next_req_id
        self.next_req_id += 1

        self.active_requests[req_id] = {
            "type": "market_data",
            "symbol": data.get("symbol"),
            "instrument_type": data.get("instrument_type", "stock"),
            "contract": contract,
            "expiry": getattr(contract, "lastTradeDateOrContractMonth", None),
        }

        # Request market data with generic tick list for comprehensive data
        generic_tick_list = "233,236,258"  # RTVolume, inventory, fundamentals
        self.client.reqMktData(req_id, contract, generic_tick_list, False, False, [])

        symbol = data.get("symbol")
        instrument_type = data.get("instrument_type", "stock")
        expiry = getattr(contract, "lastTradeDateOrContractMonth", None)
        expiry_str = f" expiry: {expiry}" if expiry else ""

        logger.info(
            f"Subscribed to market data for {symbol} ({instrument_type}){expiry_str} - req_id: {req_id}"
        )

    def _process_contract_details_for_front_month(self, req_id):
        """Process contract details to find front month and subscribe to market data"""
        try:
            if req_id not in self.contract_details_requests:
                logger.error(f"Contract details request {req_id} not found")
                return

            request_info = self.contract_details_requests[req_id]
            original_data = request_info["original_data"]
            contract_details_list = request_info["contract_details"]

            logger.debug(
                f"Processing {len(contract_details_list)} contract details for front month detection"
            )

            # Find front month expiry
            front_month = ContractFactory.get_front_month_expiry(contract_details_list)

            if front_month:
                # Create contract with front month expiry
                enhanced_data = original_data.copy()
                enhanced_data["expiry"] = front_month

                contract = self.create_contract_from_params(enhanced_data)
                self._subscribe_to_contract(enhanced_data, contract)

                logger.info(
                    f"Successfully subscribed to front month contract: {original_data.get('symbol')} {front_month}"
                )
            else:
                logger.error(
                    f"Could not determine front month for {original_data.get('symbol')}"
                )
                # Send error message to frontend
                self.message_queue.put(
                    {
                        "type": "error",
                        "message": f"Could not find front month contract for {original_data.get('symbol')}",
                        "symbol": original_data.get("symbol"),
                        "timestamp": time.time(),
                    }
                )

            # Clean up the request
            del self.contract_details_requests[req_id]

        except Exception as e:
            logger.error(
                f"Error processing contract details for front month: {e}", exc_info=True
            )

    def subscribe_time_and_sales(self, data):
        """Subscribe to time and sales data"""
        try:
            contract = self.create_contract_from_params(data)
            req_id = self.next_req_id
            self.next_req_id += 1

            self.active_requests[req_id] = {
                "type": "time_and_sales",
                "symbol": data.get("symbol"),
                "instrument_type": data.get("instrument_type", "stock"),
                "contract": contract,
            }

            # Request tick-by-tick data for time and sales
            self.client.reqTickByTickData(req_id, contract, "AllLast", 0, False)

            logger.info(
                f"Subscribed to time and sales for {data.get('symbol')} - req_id: {req_id}"
            )

        except Exception as e:
            logger.error(f"Error subscribing to time and sales: {e}")

    def subscribe_bid_ask(self, data):
        """Subscribe to bid/ask tick data"""
        try:
            contract = self.create_contract_from_params(data)
            req_id = self.next_req_id
            self.next_req_id += 1

            self.active_requests[req_id] = {
                "type": "bid_ask",
                "symbol": data.get("symbol"),
                "instrument_type": data.get("instrument_type", "stock"),
                "contract": contract,
            }

            # Request tick-by-tick bid/ask data
            self.client.reqTickByTickData(req_id, contract, "BidAsk", 0, False)

            logger.info(
                f"Subscribed to bid/ask for {data.get('symbol')} - req_id: {req_id}"
            )

        except Exception as e:
            logger.error(f"Error subscribing to bid/ask: {e}")

    def unsubscribe_market_data(self, data):
        """Unsubscribe from market data"""
        symbol = data.get("symbol")
        self._unsubscribe_by_symbol_and_type(
            symbol, "market_data", self.client.cancelMktData
        )

    def unsubscribe_time_and_sales(self, data):
        """Unsubscribe from time and sales data"""
        symbol = data.get("symbol")
        self._unsubscribe_by_symbol_and_type(
            symbol, "time_and_sales", self.client.cancelTickByTickData
        )

    def unsubscribe_bid_ask(self, data):
        """Unsubscribe from bid/ask data"""
        symbol = data.get("symbol")
        self._unsubscribe_by_symbol_and_type(
            symbol, "bid_ask", self.client.cancelTickByTickData
        )

    def _unsubscribe_by_symbol_and_type(self, symbol, data_type, cancel_func):
        """Helper method to unsubscribe by symbol and data type"""
        req_ids_to_remove = []

        for req_id, request in self.active_requests.items():
            if request["type"] == data_type and request["symbol"] == symbol:
                cancel_func(req_id)
                req_ids_to_remove.append(req_id)
                logger.info(
                    f"Unsubscribed from {data_type} for {symbol} - req_id: {req_id}"
                )

        for req_id in req_ids_to_remove:
            del self.active_requests[req_id]

    def get_contract_details(self, data):
        """Get contract details for an instrument"""
        try:
            contract = self.create_contract_from_params(data)
            req_id = self.next_req_id
            self.next_req_id += 1

            self.active_requests[req_id] = {
                "type": "contract_details",
                "symbol": data.get("symbol"),
                "instrument_type": data.get("instrument_type", "stock"),
                "contract": contract,
            }

            self.client.reqContractDetails(req_id, contract)
            logger.info(
                f"Requested contract details for {data.get('symbol')} - req_id: {req_id}"
            )

        except Exception as e:
            logger.error(f"Error requesting contract details: {e}")

    def place_order(self, data):
        """Place an order through IB"""
        try:
            contract = self.create_contract_from_params(data)

            action = data.get("action")  # BUY or SELL
            quantity = data.get("quantity")
            order_type = data.get("order_type", "MKT")
            price = data.get("price")

            if not all([action, quantity]):
                raise ValueError("Action and quantity are required")

            # Create order
            order = Order()
            order.action = action
            order.totalQuantity = quantity
            order.orderType = order_type

            if order_type == "LMT" and price:
                order.lmtPrice = price
            elif order_type == "STP" and price:
                order.auxPrice = price

            # Place order
            order_id = self.wrapper.next_order_id
            if order_id is None:
                logger.error(
                    "No valid order ID available. Connection to IB may not be established."
                )
                return
            self.wrapper.next_order_id += 1

            self.client.placeOrder(order_id, contract, order)
            logger.info(
                f"Placed {action} order for {quantity} {data.get('symbol')} - order_id: {order_id}"
            )

        except Exception as e:
            logger.error(f"Error placing order: {e}")

    def cancel_order(self, data):
        """Cancel an order"""
        order_id = data.get("order_id")
        if order_id:
            self.client.cancelOrder(order_id, "")
            logger.info(f"Cancelled order {order_id}")

    async def broadcast_messages(self):
        """Broadcast messages from IB to all WebSocket clients"""
        logger.debug("Message broadcaster started")
        while not self.shutdown_event.is_set():
            try:
                # Get message from queue (non-blocking)
                message = self.message_queue.get_nowait()

                # Broadcast to all connected clients
                if self.websocket_clients:
                    message_json = json.dumps(message)
                    disconnected_clients = set()

                    for client in self.websocket_clients:
                        try:
                            await client.send(message_json)
                        except websockets.exceptions.ConnectionClosed:
                            disconnected_clients.add(client)
                        except Exception as e:
                            logger.warning(f"Error sending to client: {e}")
                            disconnected_clients.add(client)

                    # Remove disconnected clients
                    if disconnected_clients:
                        self.websocket_clients -= disconnected_clients
                        logger.debug(
                            f"Removed {len(disconnected_clients)} disconnected clients"
                        )

            except queue.Empty:
                # No messages, sleep briefly
                await asyncio.sleep(0.001)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                await asyncio.sleep(0.1)

        logger.debug("Message broadcaster stopped")

    async def start_websocket_server(self):
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket server on port {self.ws_port}")

        # Start message broadcaster
        broadcaster_task = asyncio.create_task(self.broadcast_messages())
        self.tasks.append(broadcaster_task)

        # Start WebSocket server
        self.websocket_server = await websockets.serve(
            self.handle_websocket_client, "localhost", self.ws_port
        )

        logger.info(f"WebSocket server running on ws://localhost:{self.ws_port}")

    async def stop(self):
        """Stop the bridge gracefully"""
        logger.info("Stopping IBWebSocketBridge...")
        self.is_running = False
        self.shutdown_event.set()

        # Cancel all background tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.debug(f"Task cancelled successfully")
                except Exception as e:
                    logger.error(f"Error stopping task: {str(e)}")

        # Close WebSocket server
        if self.websocket_server:
            try:
                self.websocket_server.close()
                await self.websocket_server.wait_closed()
                logger.debug("WebSocket server stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping WebSocket server: {str(e)}")

        # Close all WebSocket client connections
        if self.websocket_clients:
            logger.debug(f"Closing {len(self.websocket_clients)} WebSocket connections")
            for client in self.websocket_clients.copy():
                try:
                    await client.close()
                except Exception as e:
                    logger.debug(f"Error closing WebSocket client: {str(e)}")
            self.websocket_clients.clear()

        # Disconnect from IB
        try:
            if self.client.isConnected():
                self.client.disconnect()
                logger.debug("Disconnected from IB successfully")
        except Exception as e:
            logger.error(f"Error disconnecting from IB: {str(e)}")

        logger.info("IBWebSocketBridge stopped")

    async def run(self):
        """Main run method"""
        try:
            # Connect to IB
            if not self.connect_to_ib():
                logger.error("Failed to connect to IB. Exiting.")
                return

            # Start WebSocket server
            await self.start_websocket_server()
            self.is_running = True

            # Keep running until shutdown
            logger.info("Bridge is running. Press Ctrl+C to stop.")
            await self.shutdown_event.wait()

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Bridge error: {str(e)}", exc_info=True)
        finally:
            await self.stop()


# Usage example
async def main():
    # Set logging level based on environment
    # logging.getLogger().setLevel(logging.DEBUG)  # Uncomment for verbose logging

    bridge = IBWebSocketBridge(
        ib_host="127.0.0.1",  # IB TWS/Gateway host
        ib_port=7497,  # Paper trading port (7496 for live)
        ws_port=8765,  # WebSocket server port
    )

    await bridge.run()


if __name__ == "__main__":
    # Install required packages:
    # pip install ibapi websockets

    asyncio.run(main())
