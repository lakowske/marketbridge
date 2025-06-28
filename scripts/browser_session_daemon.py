#!/usr/bin/env python3
"""
MarketBridge Browser Session Daemon

Daemon management script for the browser session server.
Inspired by browser-bunny's server_daemon.py but integrated with MarketBridge.
"""

import argparse
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# Add the src directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

logger = logging.getLogger(__name__)


class BrowserSessionDaemon:
    """
    Daemon manager for the MarketBridge browser session server.

    Provides start/stop/restart/status operations with PID file management
    and proper signal handling.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8766,
        pid_file: Optional[str] = None,
        log_file: Optional[str] = None,
    ):
        """
        Initialize the daemon manager.

        Args:
            host: Server host address
            port: Server port
            pid_file: Path to PID file
            log_file: Path to log file
        """
        self.host = host
        self.port = port

        # Setup file paths
        if pid_file is None:
            self.pid_file = project_root / "run" / "browser_session_server.pid"
        else:
            self.pid_file = Path(pid_file)

        if log_file is None:
            self.log_file = project_root / "logs" / "browser_session_server.log"
        else:
            self.log_file = Path(log_file)

        # Ensure directories exist
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Browser session daemon initialized - host: {self.host}, port: {self.port}, "
            f"pid_file: {self.pid_file}, log_file: {self.log_file}"
        )

    def is_running(self) -> bool:
        """
        Check if the daemon is currently running.

        Returns:
            True if daemon is running, False otherwise
        """
        if not self.pid_file.exists():
            return False

        try:
            with open(self.pid_file, "r") as f:
                pid = int(f.read().strip())

            # Check if process with this PID exists
            os.kill(pid, 0)
            return True

        except (ValueError, OSError, ProcessLookupError):
            # PID file exists but process is not running
            if self.pid_file.exists():
                self.pid_file.unlink()
            return False

    def get_pid(self) -> Optional[int]:
        """
        Get the PID of the running daemon.

        Returns:
            PID if daemon is running, None otherwise
        """
        if not self.pid_file.exists():
            return None

        try:
            with open(self.pid_file, "r") as f:
                pid = int(f.read().strip())

            # Verify process exists
            os.kill(pid, 0)
            return pid

        except (ValueError, OSError, ProcessLookupError):
            if self.pid_file.exists():
                self.pid_file.unlink()
            return None

    def start(self, background: bool = True) -> bool:
        """
        Start the browser session daemon.

        Args:
            background: Whether to run in background

        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running():
            print(f"Browser session server is already running (PID: {self.get_pid()})")
            return False

        print(f"Starting browser session server on {self.host}:{self.port}...")

        # Prepare command
        python_path = sys.executable
        server_module = "marketbridge.browser_session_server"

        cmd = [
            python_path,
            "-m",
            server_module,
            "--host",
            self.host,
            "--port",
            str(self.port),
        ]

        try:
            if background:
                # Run in background with output redirection
                with open(self.log_file, "a") as log_f:
                    process = subprocess.Popen(
                        cmd,
                        stdout=log_f,
                        stderr=subprocess.STDOUT,
                        cwd=str(project_root),
                        start_new_session=True,
                    )

                # Write PID file
                with open(self.pid_file, "w") as f:
                    f.write(str(process.pid))

                # Give the server a moment to start
                time.sleep(2)

                # Check if it's still running
                if process.poll() is None:
                    print(
                        f"Browser session server started successfully (PID: {process.pid})"
                    )
                    print(f"Logs: {self.log_file}")
                    return True
                else:
                    print("Failed to start browser session server")
                    if self.pid_file.exists():
                        self.pid_file.unlink()
                    return False
            else:
                # Run in foreground
                process = subprocess.run(cmd, cwd=str(project_root))
                return process.returncode == 0

        except Exception as e:
            print(f"Failed to start browser session server: {e}")
            if self.pid_file.exists():
                self.pid_file.unlink()
            return False

    def stop(self, force: bool = False) -> bool:
        """
        Stop the browser session daemon.

        Args:
            force: Whether to force kill the process

        Returns:
            True if stopped successfully, False otherwise
        """
        pid = self.get_pid()
        if pid is None:
            print("Browser session server is not running")
            return True

        print(f"Stopping browser session server (PID: {pid})...")

        try:
            if force:
                # Force kill
                os.kill(pid, signal.SIGKILL)
                print("Browser session server force killed")
            else:
                # Graceful shutdown
                os.kill(pid, signal.SIGTERM)

                # Wait for graceful shutdown
                for _ in range(10):  # Wait up to 10 seconds
                    time.sleep(1)
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        # Process has terminated
                        break
                else:
                    # Process still running, force kill
                    print("Graceful shutdown timeout, force killing...")
                    os.kill(pid, signal.SIGKILL)

                print("Browser session server stopped")

            # Clean up PID file
            if self.pid_file.exists():
                self.pid_file.unlink()

            return True

        except ProcessLookupError:
            # Process already terminated
            print("Browser session server was not running")
            if self.pid_file.exists():
                self.pid_file.unlink()
            return True
        except Exception as e:
            print(f"Failed to stop browser session server: {e}")
            return False

    def restart(self) -> bool:
        """
        Restart the browser session daemon.

        Returns:
            True if restarted successfully, False otherwise
        """
        print("Restarting browser session server...")

        # Stop first
        if not self.stop():
            print("Failed to stop browser session server")
            return False

        # Wait a moment
        time.sleep(1)

        # Start again
        return self.start()

    def status(self, verbose: bool = False) -> None:
        """
        Show the status of the browser session daemon.

        Args:
            verbose: Whether to show detailed status information
        """
        pid = self.get_pid()

        if pid is None:
            print("Browser session server: STOPPED")
            return

        print(f"Browser session server: RUNNING (PID: {pid})")
        print(f"Host: {self.host}")
        print(f"Port: {self.port}")
        print(f"PID file: {self.pid_file}")
        print(f"Log file: {self.log_file}")

        if verbose:
            # Get process information
            try:
                import psutil

                process = psutil.Process(pid)

                # Get memory usage
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024

                # Get CPU usage
                cpu_percent = process.cpu_percent(interval=1)

                # Get uptime
                create_time = process.create_time()
                uptime_seconds = time.time() - create_time
                uptime_hours = uptime_seconds / 3600

                print(f"Memory usage: {memory_mb:.1f} MB")
                print(f"CPU usage: {cpu_percent:.1f}%")
                print(f"Uptime: {uptime_hours:.1f} hours")

            except ImportError:
                print(
                    "Install psutil for detailed process information: pip install psutil"
                )
            except Exception as e:
                print(f"Failed to get detailed process information: {e}")

    def logs(self, lines: int = 50, follow: bool = False) -> None:
        """
        Show recent log entries.

        Args:
            lines: Number of lines to show
            follow: Whether to follow the log file (tail -f behavior)
        """
        if not self.log_file.exists():
            print(f"Log file does not exist: {self.log_file}")
            return

        try:
            if follow:
                # Follow log file
                import subprocess

                subprocess.run(["tail", "-f", str(self.log_file)])
            else:
                # Show last N lines
                import subprocess

                result = subprocess.run(
                    ["tail", "-n", str(lines), str(self.log_file)],
                    capture_output=True,
                    text=True,
                )
                print(result.stdout)

        except FileNotFoundError:
            # Fallback for systems without tail command
            with open(self.log_file, "r") as f:
                log_lines = f.readlines()

            if follow:
                # Simple follow implementation
                print("".join(log_lines[-lines:]))
                print("Following log file (Ctrl+C to exit)...")

                import time

                last_size = self.log_file.stat().st_size

                try:
                    while True:
                        time.sleep(1)
                        current_size = self.log_file.stat().st_size

                        if current_size > last_size:
                            with open(self.log_file, "r") as f:
                                f.seek(last_size)
                                new_content = f.read()
                                print(new_content, end="")
                            last_size = current_size

                except KeyboardInterrupt:
                    print("\nStopped following log file")
            else:
                print("".join(log_lines[-lines:]))

        except Exception as e:
            print(f"Failed to read log file: {e}")

    def cleanup(self) -> None:
        """Clean up daemon files (PID file, old logs, etc.)."""
        print("Cleaning up browser session daemon files...")

        # Remove PID file if exists
        if self.pid_file.exists():
            self.pid_file.unlink()
            print(f"Removed PID file: {self.pid_file}")

        # Rotate log file if it's too large (>10MB)
        if self.log_file.exists():
            log_size_mb = self.log_file.stat().st_size / 1024 / 1024
            if log_size_mb > 10:
                backup_log = self.log_file.with_suffix(".log.old")
                if backup_log.exists():
                    backup_log.unlink()
                self.log_file.rename(backup_log)
                print(f"Rotated large log file: {self.log_file} -> {backup_log}")

        print("Cleanup completed")


def main():
    """Main entry point for the daemon management script."""
    parser = argparse.ArgumentParser(
        description="MarketBridge Browser Session Daemon Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start                    # Start daemon in background
  %(prog)s stop                     # Stop daemon gracefully
  %(prog)s restart                  # Restart daemon
  %(prog)s status                   # Show daemon status
  %(prog)s status -v                # Show detailed status
  %(prog)s logs                     # Show recent logs
  %(prog)s logs -n 100              # Show last 100 log lines
  %(prog)s logs --follow            # Follow logs in real-time
        """,
    )

    parser.add_argument(
        "action",
        choices=["start", "stop", "restart", "status", "logs", "cleanup"],
        help="Action to perform",
    )
    parser.add_argument(
        "--host", default="localhost", help="Server host (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=8766, help="Server port (default: 8766)"
    )
    parser.add_argument("--pid-file", help="PID file path")
    parser.add_argument("--log-file", help="Log file path")
    parser.add_argument("--foreground", action="store_true", help="Run in foreground")
    parser.add_argument("--force", action="store_true", help="Force action (for stop)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "-n", "--lines", type=int, default=50, help="Number of log lines to show"
    )
    parser.add_argument("--follow", action="store_true", help="Follow log file")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create daemon instance
    daemon = BrowserSessionDaemon(
        host=args.host,
        port=args.port,
        pid_file=args.pid_file,
        log_file=args.log_file,
    )

    # Execute action
    try:
        if args.action == "start":
            success = daemon.start(background=not args.foreground)
            sys.exit(0 if success else 1)

        elif args.action == "stop":
            success = daemon.stop(force=args.force)
            sys.exit(0 if success else 1)

        elif args.action == "restart":
            success = daemon.restart()
            sys.exit(0 if success else 1)

        elif args.action == "status":
            daemon.status(verbose=args.verbose)

        elif args.action == "logs":
            daemon.logs(lines=args.lines, follow=args.follow)

        elif args.action == "cleanup":
            daemon.cleanup()

    except KeyboardInterrupt:
        print("\nOperation cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
