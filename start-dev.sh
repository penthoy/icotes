#!/bin/bash

# icotes Development Startup Script (Modern UV Edition)
# This script builds the frontend and runs the backend in development mode with auto-reload
# Uses SINGLE PORT setup - frontend served from backend (same as production)
# Modernized to use uv package manager for faster Python dependency management

echo "🚀 Starting icotes in development mode (with UV support)..."

# Load environment variables from .env if it exists
if [ -f ".env" ]; then
    echo "📄 Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
fi

# Ensure bun is available on PATH for non-interactive shells
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

if ! command -v bun &> /dev/null; then
    echo "❌ Error: bun not found. Please run ./setup.sh (or install bun from https://bun.sh)."
    exit 1
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

# Ensure logs directory exists
mkdir -p logs
echo "📁 Logs directory ready: ./logs/"

# Single-instance guard (development): prevent multiple uvicorn reloaders
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
PID_FILE="$REPO_ROOT/logs/backend.pid"
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$OLD_PID" ] && ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "❌ Backend already running (PID: $OLD_PID). Stop it first: kill $OLD_PID"
        exit 1
    else
        echo "⚠️  Removing stale PID file: $PID_FILE"
        rm -f "$PID_FILE"
    fi
fi
echo ""

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
    bun install
fi

# Build the frontend for development (with source maps and dev optimizations)
echo "🏗️  Building frontend for development..."
bun run build
if [ $? -ne 0 ]; then
    echo "❌ Frontend build failed. Please fix the errors and try again."
    exit 1
fi

# Setup Python environment with uv
echo "🐍 Setting up Python environment with uv..."
cd backend

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    
    if ! command -v uv &> /dev/null; then
        echo "❌ Error: Failed to install uv. Falling back to traditional pip."
        # Fallback to traditional approach
        if [ ! -d "venv" ]; then
            echo "🏗️  Creating Python virtual environment..."
            python3 -m venv venv
        fi
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
    else
        echo "✅ uv installed successfully"
        # Initialize uv project if needed
        if [ ! -f "pyproject.toml" ]; then
            uv init --no-readme --no-pin-python
        fi
        uv sync --frozen --no-dev || uv pip install -r requirements.txt
    fi
else
    echo "✅ uv already installed"
    # Initialize uv project if needed
    if [ ! -f "pyproject.toml" ]; then
        uv init --no-readme --no-pin-python
    fi
    # Install dependencies with uv
    echo "📦 Installing Python dependencies with uv..."
    uv sync --frozen --no-dev || uv pip install -r requirements.txt
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
echo "📋 Logs:"
echo "   Backend logs: ./logs/backend.log"
echo "   Access logs: Console output"
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
echo "🔧 Starting with uv (if available) or fallback to venv..."

# Check if we're using uv or traditional venv
if command -v uv &> /dev/null && [ -f "pyproject.toml" ]; then
    echo "✅ Using uv for execution"
    echo "🔧 Python: $(uv run python --version)"
    
    # Use uv run for execution
    uv run uvicorn main:app \
        --host "$BACKEND_HOST" \
        --port "$BACKEND_PORT" \
        --reload \
        --reload-dir . \
        --reload-exclude ".venv/*" \
        --reload-exclude "venv/*" \
        --reload-exclude "*.pyc" \
        --reload-exclude "__pycache__" \
        --log-config logging.conf \
        --access-log &
else
    echo "🔧 Falling back to virtual environment..."
    source venv/bin/activate || {
        echo "❌ Error: Virtual environment not found or not activated."
        echo "   Please ensure venv exists and contains a proper Python virtual environment."
        exit 1
    }
    
    echo "✅ Virtual environment activated: $(which python)"
    echo "🔧 Using Python: $(python --version)"
    
    # Use the venv's uvicorn instead of system uvicorn
    uvicorn main:app \
        --host "$BACKEND_HOST" \
        --port "$BACKEND_PORT" \
        --reload \
        --reload-dir . \
        --reload-exclude ".venv/*" \
        --reload-exclude "venv/*" \
        --reload-exclude "*.pyc" \
        --reload-exclude "__pycache__" \
        --log-config logging.conf \
        --access-log &
fi

BACKEND_PID=$!
echo $BACKEND_PID > "$PID_FILE"

trap 'echo; echo "🛑 Stopping dev backend (PID: $(cat "$PID_FILE" 2>/dev/null) )"; kill $(cat "$PID_FILE" 2>/dev/null) 2>/dev/null || true; rm -f "$PID_FILE"; exit 0' SIGINT SIGTERM

# Wait for the backend process
wait $BACKEND_PID
EXIT_CODE=$?
rm -f "$PID_FILE"
exit $EXIT_CODE
