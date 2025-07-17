#!/bin/bash

# icotes Development Startup Script
# This script builds the frontend and runs the backend in development mode with auto-reload
# Uses SINGLE PORT setup - frontend served from backend (same as production)

echo "🚀 Starting icotes in development mode..."

# Load environment variables from .env if it exists
if [ -f ".env" ]; then
    echo "📄 Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
fi

# Set default values if not provided
export NODE_ENV=development
export BACKEND_HOST=${BACKEND_HOST:-${SITE_URL:-0.0.0.0}}
export BACKEND_PORT=${BACKEND_PORT:-${PORT:-8000}}

echo "🔧 Environment Configuration:"
echo "   NODE_ENV: $NODE_ENV"
echo "   SITE_URL: $SITE_URL"
echo "   BACKEND_HOST: $BACKEND_HOST"
echo "   BACKEND_PORT: $BACKEND_PORT"
echo "   ⚠️  SINGLE PORT SETUP: Frontend served from backend"
echo ""

# Check if we're in the correct directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Please run this script from the project root directory."
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down gracefully..."
    if [[ -n "$BACKEND_PID" ]]; then
        echo "   Stopping backend server (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null || true
    fi
    exit 0
}

# Setup signal handlers
trap cleanup SIGINT SIGTERM

# Install Node.js dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

# Build the frontend for development (with source maps and dev optimizations)
echo "🏗️  Building frontend for development..."
npm run build
if [ $? -ne 0 ]; then
    echo "❌ Frontend build failed. Please fix the errors and try again."
    exit 1
fi

# Setup Python environment
echo "🐍 Setting up Python environment..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🏗️  Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "⚡ Activating virtual environment..."
source venv/bin/activate

# Install/update Python dependencies
echo "📦 Installing Python dependencies..."
if command -v pip &> /dev/null; then
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "❌ Error: pip not available in virtual environment"
    exit 1
fi

# Start the backend server with development settings
echo ""
echo "🎯 Starting the development server..."
echo "   Backend will be available at: http://$BACKEND_HOST:$BACKEND_PORT"
echo "   Frontend will be served from the backend (single port setup)"
echo "   Health check: http://$BACKEND_HOST:$BACKEND_PORT/health"
echo "   Terminal health: http://$BACKEND_PORT/api/terminal/health"
echo ""
echo "   Press Ctrl+C to stop the server"
echo ""
echo "=============================================="
echo "🚀 icotes is now running!"
echo "=============================================="
echo ""
echo "📱 Frontend Access:"
echo "   URL: http://localhost:$BACKEND_PORT"
echo "   URL: http://$(hostname -I | awk '{print $1}' 2>/dev/null || echo 'your-ip'):$BACKEND_PORT"
echo ""
echo "🔧 Backend API:"
echo "   URL: http://localhost:$BACKEND_PORT/api"
echo "   Docs: http://localhost:$BACKEND_PORT/docs"
echo ""
echo "🔍 Health Check:"
echo "   General: http://localhost:$BACKEND_PORT/health"
echo "   Terminal: http://localhost:$BACKEND_PORT/api/terminal/health"
echo ""
echo "⚠️  Note: Frontend is served from the backend server (SINGLE PORT)"
echo "📝 Development Features:"
echo "   • Backend auto-reload on Python file changes"
echo "   • Frontend rebuilds when you restart this script"
echo "   • Development error logging enabled"
echo "   • Access logs enabled"
echo ""
echo "🔄 To see frontend changes:"
echo "   1. Press Ctrl+C to stop"
echo "   2. Re-run ./start-dev.sh"
echo "   3. Frontend will be rebuilt automatically"
echo ""
echo "🛑 To stop: Press Ctrl+C"
echo "=============================================="
echo ""

# Start the backend server in foreground with development features
python3 -m uvicorn main:app \
    --host "$BACKEND_HOST" \
    --port "$BACKEND_PORT" \
    --reload \
    --reload-dir . \
    --reload-exclude "*.pyc" \
    --reload-exclude "__pycache__" \
    --log-level debug \
    --access-log &

BACKEND_PID=$!

# Wait for the backend process
wait $BACKEND_PID
