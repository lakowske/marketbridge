#!/bin/bash
"""
Frontend Setup Script
Copies JavaScript files to the correct public location for serving.
"""

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up MarketBridge frontend..."

# Copy JavaScript files to public directory
if [ -d "src" ] && [ -d "public" ]; then
    echo "Copying JavaScript files to public directory..."
    cp -r src public/
    echo "✅ JavaScript files copied successfully"
else
    echo "❌ Source directories not found"
    exit 1
fi

# Check if all required files exist
echo "Verifying frontend files..."

required_files=(
    "public/index.html"
    "public/assets/css/main.css"
    "public/assets/css/components.css"
    "public/src/js/app.js"
    "public/src/utils/logger.js"
    "public/src/services/websocket-client.js"
    "public/src/components/market-data-display.js"
    "public/src/components/subscription-manager.js"
    "public/src/components/order-manager.js"
)

missing_files=()
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    else
        echo "✅ $file"
    fi
done

if [ ${#missing_files[@]} -eq 0 ]; then
    echo ""
    echo "🎉 Frontend setup complete!"
    echo "All required files are in place."
    echo ""
    echo "Frontend structure:"
    echo "web/public/"
    echo "├── index.html"
    echo "├── assets/css/"
    echo "│   ├── main.css"
    echo "│   └── components.css"
    echo "└── src/"
    echo "    ├── js/app.js"
    echo "    ├── utils/logger.js"
    echo "    ├── services/websocket-client.js"
    echo "    └── components/"
    echo "        ├── market-data-display.js"
    echo "        ├── subscription-manager.js"
    echo "        └── order-manager.js"
else
    echo ""
    echo "❌ Missing files:"
    for file in "${missing_files[@]}"; do
        echo "   $file"
    done
    exit 1
fi
