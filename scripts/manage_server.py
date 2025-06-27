#!/usr/bin/env python3
"""
MarketBridge Server Management Tool

A professional CLI tool for managing the MarketBridge server process.
Provides start, stop, restart, status, and log management functionality.
"""

import argparse
import os
import signal
import subprocess  # nosec B404 # Used for controlled server management
import sys
import time
from datetime import datetime
from pathlib import Path


# ANSI color codes for terminal output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


class ServerManager:
    def __init__(self, project_root=None):
        if project_root:
            self.project_root = Path(project_root)
        else:
            # Auto-detect project root (parent of scripts directory)
            self.project_root = Path(__file__).parent.parent

        # Create necessary directories
        self.run_dir = self.project_root / "run"
        self.logs_dir = self.project_root / "logs"
        self.run_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

        # File paths
        self.pid_file = self.run_dir / "marketbridge.pid"
        self.log_file = self.logs_dir / "marketbridge.log"
        self.error_log_file = self.logs_dir / "marketbridge_error.log"
        self.server_script = self.project_root / "run_server.py"

        # Virtual environment python
        venv_python = self.project_root / ".venv" / "bin" / "python"
        if venv_python.exists():
            self.python_exe = str(venv_python)
        else:
            self.python_exe = "python3"  # Fallback to system python

    def _print_status(self, message, status="info"):
        """Print colored status message"""
        color = {
            "success": Colors.GREEN,
            "error": Colors.RED,
            "warning": Colors.YELLOW,
            "info": Colors.BLUE,
        }.get(status, "")

        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{color}[{timestamp}] {message}{Colors.END}")

    def _get_pid(self):
        """Get PID from pid file if it exists and process is running"""
        if not self.pid_file.exists():
            return None

        try:
            with open(self.pid_file, "r") as f:
                pid = int(f.read().strip())

            # Check if process is actually running
            try:
                os.kill(pid, 0)  # Send signal 0 to check if process exists
                return pid
            except OSError:
                # Process doesn't exist, remove stale pid file
                self.pid_file.unlink()
                return None
        except (ValueError, FileNotFoundError):
            return None

    def _save_pid(self, pid):
        """Save PID to pid file"""
        with open(self.pid_file, "w") as f:
            f.write(str(pid))

    def _remove_pid_file(self):
        """Remove pid file"""
        if self.pid_file.exists():
            self.pid_file.unlink()

    def start(self, verbose=False):
        """Start the MarketBridge server"""
        # Check if already running
        existing_pid = self._get_pid()
        if existing_pid:
            self._print_status(
                f"Server is already running (PID: {existing_pid})", "warning"
            )
            return False

        # Check if server script exists
        if not self.server_script.exists():
            self._print_status(
                f"Server script not found: {self.server_script}", "error"
            )
            return False

        self._print_status("Starting MarketBridge server...", "info")

        try:
            # Start the server process
            with open(self.log_file, "a") as log_out, open(
                self.error_log_file, "a"
            ) as log_err:
                # Add startup marker to logs
                timestamp = datetime.now().isoformat()
                log_out.write(f"\n--- MarketBridge started at {timestamp} ---\n")
                log_out.flush()

                process = subprocess.Popen(  # nosec B603 # Controlled server startup with validated paths
                    [str(self.python_exe), str(self.server_script)],
                    cwd=str(self.project_root),
                    stdout=log_out,
                    stderr=log_err,
                    preexec_fn=os.setsid,  # Create new session to detach from terminal
                )

            # Save PID
            self._save_pid(process.pid)

            # Give it a moment to start
            time.sleep(1)

            # Verify it's still running
            if self._get_pid():
                self._print_status(
                    f"Server started successfully (PID: {process.pid})", "success"
                )
                self._print_status(f"Logs: {self.log_file}", "info")
                self._print_status(f"Error logs: {self.error_log_file}", "info")
                if verbose:
                    self._print_status(
                        f"Working directory: {self.project_root}", "info"
                    )
                    self._print_status(f"Python executable: {self.python_exe}", "info")
                return True
            else:
                self._print_status("Server failed to start", "error")
                return False

        except Exception as e:
            self._print_status(f"Failed to start server: {e}", "error")
            return False

    def stop(self, verbose=False):
        """Stop the MarketBridge server"""
        pid = self._get_pid()
        if not pid:
            self._print_status("Server is not running", "warning")
            return True

        self._print_status(f"Stopping MarketBridge server (PID: {pid})...", "info")

        try:
            # Try graceful shutdown first (SIGTERM)
            os.kill(pid, signal.SIGTERM)

            # Wait for graceful shutdown with shorter intervals
            for i in range(30):  # Wait up to 3 seconds with 0.1s intervals
                time.sleep(0.1)
                if not self._get_pid():
                    self._print_status("Server stopped gracefully", "success")
                    self._remove_pid_file()
                    return True

            # If still running, force kill
            if self._get_pid():
                self._print_status(
                    "Graceful shutdown timeout, forcing kill...", "warning"
                )
                os.kill(pid, signal.SIGKILL)
                time.sleep(1)

                if not self._get_pid():
                    self._print_status("Server force-killed", "success")
                    self._remove_pid_file()
                    return True
                else:
                    self._print_status("Failed to stop server", "error")
                    return False

        except OSError as e:
            if e.errno == 3:  # No such process
                self._print_status(
                    "Server process not found (was already stopped)", "warning"
                )
                self._remove_pid_file()
                return True
            else:
                self._print_status(f"Error stopping server: {e}", "error")
                return False

    def restart(self, verbose=False):
        """Restart the MarketBridge server"""
        self._print_status("Restarting MarketBridge server...", "info")

        # Stop first
        if not self.stop(verbose):
            return False

        # Wait a moment
        time.sleep(2)

        # Start again
        return self.start(verbose)

    def status(self, verbose=False):
        """Show server status"""
        pid = self._get_pid()

        if pid:
            self._print_status(
                f"Server is {Colors.BOLD}RUNNING{Colors.END} (PID: {pid})", "success"
            )

            if verbose:
                try:
                    # Get process info
                    with open(f"/proc/{pid}/stat", "r") as f:
                        stat_data = f.read().split()

                    # Parse start time and memory info
                    start_time = stat_data[21]
                    rss_pages = int(stat_data[23])
                    rss_mb = (rss_pages * 4096) // (1024 * 1024)  # Convert to MB

                    self._print_status(f"Memory usage: ~{rss_mb} MB", "info")

                    # Check log file sizes
                    if self.log_file.exists():
                        log_size = self.log_file.stat().st_size // 1024  # KB
                        self._print_status(f"Log file size: {log_size} KB", "info")

                except (FileNotFoundError, ValueError, IndexError):
                    pass  # Ignore if we can't get detailed info

            return True
        else:
            self._print_status(f"Server is {Colors.BOLD}STOPPED{Colors.END}", "error")
            return False

    def logs(self, follow=False, lines=50, error_logs=False):
        """Show server logs"""
        log_file = self.error_log_file if error_logs else self.log_file

        if not log_file.exists():
            self._print_status(f"Log file not found: {log_file}", "warning")
            return False

        log_type = "error logs" if error_logs else "logs"

        if follow:
            self._print_status(f"Following {log_type} (Ctrl+C to stop)...", "info")
            try:
                # Use tail -f equivalent
                subprocess.run(
                    ["tail", "-f", str(log_file)]
                )  # nosec B607, B603 # Safe use of tail command with validated file path
            except KeyboardInterrupt:
                self._print_status("Stopped following logs", "info")
        else:
            self._print_status(f"Showing last {lines} lines of {log_type}:", "info")
            try:
                result = subprocess.run(  # nosec B607, B603 # Safe use of tail command with validated file path
                    ["tail", "-n", str(lines), str(log_file)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    print(result.stdout)
                else:
                    self._print_status("Error reading log file", "error")
            except FileNotFoundError:
                # Fallback to Python implementation if tail is not available
                try:
                    with open(log_file, "r") as f:
                        all_lines = f.readlines()
                        for line in all_lines[-lines:]:
                            print(line.rstrip())
                except Exception as e:
                    self._print_status(f"Error reading log file: {e}", "error")

        return True


def main():
    parser = argparse.ArgumentParser(
        description="MarketBridge Server Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start                 Start the server in background
  %(prog)s stop                  Stop the server gracefully
  %(prog)s restart               Restart the server
  %(prog)s status                Show server status
  %(prog)s status -v             Show detailed status
  %(prog)s logs                  Show recent logs
  %(prog)s logs --follow         Follow logs in real-time
  %(prog)s logs --error          Show error logs
        """,
    )

    # Global options
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    parser.add_argument(
        "--project-root",
        type=str,
        help="Path to MarketBridge project root (auto-detected if not specified)",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start the MarketBridge server")

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop the MarketBridge server")

    # Restart command
    restart_parser = subparsers.add_parser(
        "restart", help="Restart the MarketBridge server"
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Show server status")

    # Logs command
    logs_parser = subparsers.add_parser("logs", help="Show server logs")
    logs_parser.add_argument(
        "-f", "--follow", action="store_true", help="Follow log output in real-time"
    )
    logs_parser.add_argument(
        "-n",
        "--lines",
        type=int,
        default=50,
        help="Number of lines to show (default: 50)",
    )
    logs_parser.add_argument(
        "-e",
        "--error",
        action="store_true",
        help="Show error logs instead of standard logs",
    )

    # Parse arguments
    args = parser.parse_args()

    # Show help if no command provided
    if not args.command:
        parser.print_help()
        return 1

    # Create server manager
    try:
        manager = ServerManager(args.project_root)
    except Exception as e:
        print(f"{Colors.RED}Error initializing server manager: {e}{Colors.END}")
        return 1

    # Execute command
    success = False

    if args.command == "start":
        success = manager.start(args.verbose)
    elif args.command == "stop":
        success = manager.stop(args.verbose)
    elif args.command == "restart":
        success = manager.restart(args.verbose)
    elif args.command == "status":
        success = manager.status(args.verbose)
    elif args.command == "logs":
        success = manager.logs(args.follow, args.lines, args.error)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
