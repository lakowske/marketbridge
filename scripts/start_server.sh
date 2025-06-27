#!/bin/bash
"""
MarketBridge Server Startup Script
Starts the combined server with production settings.
"""

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project directory
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Check if dependencies are installed
echo "Checking dependencies..."
python -c "import aiohttp, aiofiles, websockets, ibapi" 2>/dev/null || {
    echo "Missing dependencies. Installing..."
    pip install -e .
}

# Create logs directory
mkdir -p logs

# Start the server
echo "Starting MarketBridge Combined Server..."
echo "WebSocket API: ws://localhost:8765"
echo "Web Interface: http://localhost:8080"
echo "Health Check: http://localhost:8080/health"
echo "Statistics: http://localhost:8080/stats"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================"

python run_server.py "$@"
