#!/bin/bash
# Start the FastAPI backend server     echo "Starting FastAPI backend server (fallback uvicorn)..."
    # Start uvicorn directly for consistency
    cd "$SCRIPT_DIR"
    uvicorn main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --log-config logging.conf &
    echo $! > "$PID_FILE"
    wait $(cat "$PID_FILE")
    EXIT_CODE=$?
    rm -f "$PID_FILE"
    exit $EXIT_CODE Version) with single-instance guard

# Load environment variables
if [ -f "../.env" ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
fi

# Set default values if not provided
export BACKEND_HOST=${BACKEND_HOST:-0.0.0.0}
export BACKEND_PORT=${BACKEND_PORT:-8000}

# Determine repo root and logs dir for PID file
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOGS_DIR="$REPO_ROOT/logs"
mkdir -p "$LOGS_DIR"
PID_FILE="$LOGS_DIR/backend.pid"

# Single-instance guard using PID file
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$OLD_PID" ] && ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "❌ Backend already running (PID: $OLD_PID). Stop it first or remove $PID_FILE if stale."
        exit 1
    else
        echo "⚠️  Stale PID file found. Removing $PID_FILE"
        rm -f "$PID_FILE"
    fi
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 to run the backend."
    exit 1
fi

# Check if uv is available, install if not
if ! command -v uv &> /dev/null; then
    echo "🚀 Installing uv package manager for better performance..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    
    if ! command -v uv &> /dev/null; then
        echo "❌ Failed to install uv. Falling back to traditional approach..."
        echo "Activating virtual environment..."
        source venv/bin/activate
    echo "Starting FastAPI backend server (fallback uvicorn)..."
    # Start uvicorn directly for consistency
    cd "$SCRIPT_DIR"
    uvicorn main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --log-config logging.conf &
    echo $! > "$PID_FILE"
    wait $(cat "$PID_FILE")
    EXIT_CODE=$?
    rm -f "$PID_FILE"
    exit $EXIT_CODE
        exit 0
    fi
fi

echo "✅ Using uv for dependency management and execution"

cd "$SCRIPT_DIR"

# Initialize uv project if needed
if [ ! -f "pyproject.toml" ]; then
    echo "🏗️  Initializing uv project..."
    uv init --no-readme --no-pin-python
fi

# Install dependencies if needed
if [ -f "requirements.txt" ]; then
    echo "📦 Ensuring dependencies are installed..."
    uv sync --frozen --no-dev || uv pip install -r requirements.txt
fi

echo "🚀 Starting FastAPI backend server with uvicorn..."
uv run uvicorn main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --log-config logging.conf &
echo $! > "$PID_FILE"
trap 'echo; echo "🛑 Stopping backend (PID: $(cat "$PID_FILE" 2>/dev/null) )"; kill $(cat "$PID_FILE" 2>/dev/null) 2>/dev/null || true; rm -f "$PID_FILE"; exit 0' SIGINT SIGTERM
wait $(cat "$PID_FILE")
EXIT_CODE=$?
rm -f "$PID_FILE"
exit $EXIT_CODE
