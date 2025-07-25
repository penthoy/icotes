#!/bin/bash

# DEPRECATED: This script is deprecated in favor of UV package manager
# Please use start_with_uv.sh or the main start.sh script instead

echo "⚠️  DEPRECATED: start_with_venv.sh is deprecated"
echo ""
echo "The project has migrated to UV package manager for better performance."
echo "Please use one of these alternatives:"
echo ""
echo "  📦 ./start_with_uv.sh      - Use UV package manager"
echo "  🚀 ./start.sh              - Updated script with UV support"
echo "  🔧 cd .. && ./start-dev.sh - Development mode with UV"
echo ""
echo "UV provides:"
echo "  ⚡ Faster dependency installation"
echo "  🔒 Better dependency locking"
echo "  💾 Improved caching"
echo ""
echo "To install UV: curl -LsSf https://astral.sh/uv/install.sh | sh"
echo ""
echo "Redirecting to UV script in 3 seconds..."
sleep 3

# Redirect to UV script
if [ -f "./start_with_uv.sh" ]; then
    echo "🔄 Using UV script..."
    exec ./start_with_uv.sh
else
    echo "❌ UV script not found. Please use the main start.sh script from project root."
    echo "   cd .. && ./start.sh"
    exit 1
fi
