#!/bin/bash

# icotes Development Startup Script (Modern UV Version)
# This script builds the frontend and runs the backend in development mode with auto-reload
# Uses SINGLE PORT setup - frontend served from backend (same as production)
# Modernized to use uv package manager for faster Python dependency management

echo "🚀 Starting icotes in development mode (UV edition)..."

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
echo "   🆕 Using UV package manager for Python dependencies"
echo ""

# Check if we're in the correct directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Please run this script from the project root directory."
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv package manager not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
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

# Build frontend
echo "🏗️  Building frontend..."
npm run build

# Check backend Python environment
echo "🐍 Setting up Python backend environment..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
    echo "   Creating virtual environment with uv..."
    uv venv
fi

# Install Python dependencies
echo "   Installing Python dependencies with uv..."
uv pip install -r requirements.txt

echo ""
echo "✅ Setup complete! Starting development server..."
echo "🌍 Server will be available at: http://$BACKEND_HOST:$BACKEND_PORT"
echo "📱 Frontend files served from: backend static directory"
echo ""
echo "Press Ctrl+C to stop the development server"
echo "----------------------------------------"

# Start backend server in background
echo "🔄 Starting backend server..."
uv run python main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

echo ""
echo "🎉 Development server is running!"
echo "   📍 Backend: http://$BACKEND_HOST:$BACKEND_PORT"
echo "   📁 Static files: Served from backend"
echo "   🔧 Mode: Development (auto-reload enabled)"
echo ""
echo "📜 Logs:"
echo "----------------------------------------"

# Wait for the backend process
wait $BACKEND_PID
