#!/bin/bash
# Start the FastAPI backend server (Modern UV Version)

# Load environment variables
if [ -f "../.env" ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
fi

# Set default values if not provided
export BACKEND_HOST=${BACKEND_HOST:-localhost}
export BACKEND_PORT=${BACKEND_PORT:-8000}

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
        echo "Starting FastAPI backend server..."
        python3 main.py
        exit 0
    fi
fi

echo "✅ Using uv for dependency management and execution"

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

echo "🚀 Starting FastAPI backend server with uv..."
uv run python3 main.py
