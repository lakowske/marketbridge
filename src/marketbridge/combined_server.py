"""
MarketBridge Combined Server
Runs both the WebSocket bridge and web server together.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from .ib_websocket_bridge import IBWebSocketBridge
from .web_server import WebServer


class CombinedServer:
    """Combined server running both WebSocket bridge and web server."""

    def __init__(
        self,
        # IB WebSocket Bridge config
        ib_host: str = "127.0.0.1",
        ib_port: int = 7497,
        ws_port: int = 8765,
        # Web server config
        web_host: str = "localhost",
        web_port: int = 8080,
        web_root: str = None,
        log_dir: str = None,
        enable_cors: bool = True,
    ):
        self.ib_host = ib_host
        self.ib_port = ib_port
        self.ws_port = ws_port
        self.web_host = web_host
        self.web_port = web_port
        self.web_root = web_root
        self.log_dir = log_dir
        self.enable_cors = enable_cors

        # Components
        self.bridge = None
        self.web_server = None
        self.tasks = []

        # Shutdown control
        self.shutdown_event = asyncio.Event()

        # Setup logging
        self.setup_logging()

    def setup_logging(self):
        """Setup combined logging for both components."""
        # Set log directory if not provided
        if self.log_dir is None:
            project_root = Path(__file__).parent.parent.parent
            self.log_dir = project_root / "logs"
        else:
            self.log_dir = Path(self.log_dir)

        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup main logger
        self.logger = logging.getLogger("marketbridge.combined")
        self.logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        self.logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler
        log_file = self.log_dir / "combined_server.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        self.logger.info(
            f"Combined server logging initialized - Log directory: {self.log_dir}"
        )
        self.logger.info(f"Log level set to: {logging.getLevelName(self.logger.level)}")

    async def start_bridge(self):
        """Start the WebSocket bridge."""
        try:
            self.logger.info("Starting IBWebSocketBridge...")
            self.bridge = IBWebSocketBridge(
                ib_host=self.ib_host, ib_port=self.ib_port, ws_port=self.ws_port
            )

            # Run the bridge
            await self.bridge.run()

        except Exception as e:
            self.logger.error(f"IBWebSocketBridge error: {str(e)}", exc_info=True)
            raise

    async def start_web_server(self):
        """Start the web server."""
        try:
            self.logger.info("Starting Web Server...")
            self.web_server = WebServer(
                host=self.web_host,
                port=self.web_port,
                web_root=self.web_root,
                log_dir=str(self.log_dir),
                enable_cors=self.enable_cors,
            )

            # Run the web server
            await self.web_server.run_forever()

        except Exception as e:
            self.logger.error(f"Web server error: {str(e)}", exc_info=True)
            raise

    async def start(self):
        """Start both servers."""
        self.logger.info("Starting MarketBridge Combined Server...")
        self.logger.info(f"IB Connection: {self.ib_host}:{self.ib_port}")
        self.logger.info(f"WebSocket Server: ws://localhost:{self.ws_port}")
        self.logger.info(f"Web UI available at: http://{self.web_host}:{self.web_port}")
        self.logger.info(f"Health check: http://{self.web_host}:{self.web_port}/health")
        self.logger.info(f"Statistics: http://{self.web_host}:{self.web_port}/stats")

        try:
            # Start both servers concurrently
            self.tasks = [
                asyncio.create_task(self.start_bridge(), name="bridge"),
                asyncio.create_task(self.start_web_server(), name="web_server"),
                asyncio.create_task(self.shutdown_event.wait(), name="shutdown_waiter"),
            ]

            # Wait for either task to complete (or shutdown signal)
            done, pending = await asyncio.wait(
                self.tasks, return_when=asyncio.FIRST_COMPLETED
            )

            # Check if shutdown was requested
            for task in done:
                if task.get_name() == "shutdown_waiter":
                    self.logger.info("Graceful shutdown requested")
                    break
                try:
                    await task
                except Exception as e:
                    self.logger.error(f"Task {task.get_name()} failed: {str(e)}")

            # Cancel pending tasks
            for task in pending:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

        except Exception as e:
            self.logger.error(f"Combined server error: {str(e)}", exc_info=True)
            raise

    async def stop(self):
        """Stop both servers."""
        self.logger.info("Stopping MarketBridge Combined Server...")

        # Signal shutdown
        self.shutdown_event.set()

        # Signal bridge to shutdown gracefully before cancelling tasks
        if self.bridge:
            try:
                await self.bridge.stop()
                self.logger.debug("IBWebSocketBridge stopped successfully")
            except Exception as e:
                self.logger.error(f"Error stopping bridge: {str(e)}")

        # Stop web server
        if self.web_server:
            try:
                await self.web_server.stop()
                self.logger.debug("Web server stopped successfully")
            except Exception as e:
                self.logger.error(f"Error stopping web server: {str(e)}")

        # Cancel all remaining tasks
        for task in self.tasks:
            if not task.done() and task.get_name() != "shutdown_waiter":
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    self.logger.debug(f"Task {task.get_name()} cancelled successfully")
                except Exception as e:
                    self.logger.error(
                        f"Error stopping task {task.get_name()}: {str(e)}"
                    )

        self.logger.info("Combined server stopped")

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(sig_num, _):
            self.logger.info(f"Received signal {sig_num}, initiating shutdown...")
            # Set shutdown event to trigger graceful shutdown
            self.shutdown_event.set()

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def run(self):
        """Run the combined server."""
        try:
            self.setup_signal_handlers()
            await self.start()
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Server error: {str(e)}", exc_info=True)
        finally:
            await self.stop()
            self.logger.info("Server run completed, exiting...")


async def main():
    """Main function to run the combined server."""
    import argparse

    parser = argparse.ArgumentParser(description="MarketBridge Combined Server")

    # IB WebSocket Bridge arguments
    parser.add_argument(
        "--ib-host", default="127.0.0.1", help="IB host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--ib-port", type=int, default=7497, help="IB port (default: 7497)"
    )
    parser.add_argument(
        "--ws-port", type=int, default=8765, help="WebSocket port (default: 8765)"
    )

    # Web server arguments
    parser.add_argument(
        "--web-host", default="localhost", help="Web host (default: localhost)"
    )
    parser.add_argument(
        "--web-port", type=int, default=8080, help="Web port (default: 8080)"
    )
    parser.add_argument("--web-root", help="Web root directory (default: web/public)")
    parser.add_argument("--log-dir", help="Log directory (default: logs)")
    parser.add_argument("--no-cors", action="store_true", help="Disable CORS headers")

    args = parser.parse_args()

    # Create and run combined server
    server = CombinedServer(
        ib_host=args.ib_host,
        ib_port=args.ib_port,
        ws_port=args.ws_port,
        web_host=args.web_host,
        web_port=args.web_port,
        web_root=args.web_root,
        log_dir=args.log_dir,
        enable_cors=not args.no_cors,
    )

    await server.run()


if __name__ == "__main__":
    import logging.handlers

    asyncio.run(main())
