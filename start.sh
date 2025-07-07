#!/bin/bash
set -e

# iLabors Code Editor Production Startup Script
# This script can be used for VM deployment or local production setup

echo "🚀 Starting iLabors Code Editor in production mode..."

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        echo "⚠️  Warning: Running as root is not recommended for production."
        echo "   Consider creating a dedicated user for the application."
        read -p "Continue as root? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Exiting. Please run as a non-root user."
            exit 1
        fi
    fi
}

# Function to setup systemd service
setup_systemd() {
    if command -v systemctl &> /dev/null; then
        echo "🔧 Setting up systemd service..."
        
        # Create systemd service file
        cat > /tmp/ilaborcode.service << EOF
[Unit]
Description=iLabors Code Editor
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
ExecStart=$PWD/start.sh
Restart=always
RestartSec=10
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF

        echo "📄 Systemd service file created at /tmp/ilaborcode.service"
        echo "   To install: sudo cp /tmp/ilaborcode.service /etc/systemd/system/"
        echo "   To enable: sudo systemctl enable ilaborcode"
        echo "   To start: sudo systemctl start ilaborcode"
        echo "   To view logs: sudo journalctl -fu ilaborcode"
        echo ""
    fi
}

# Parse command line arguments
SETUP_SYSTEMD=false
DAEMON_MODE=false
SKIP_ROOT_CHECK=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --systemd)
            SETUP_SYSTEMD=true
            shift
            ;;
        --daemon)
            DAEMON_MODE=true
            shift
            ;;
        --skip-root-check)
            SKIP_ROOT_CHECK=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --systemd         Generate systemd service file"
            echo "  --daemon          Run in daemon mode (background)"
            echo "  --skip-root-check Skip root user check"
            echo "  -h, --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Security checks
if [[ "$SKIP_ROOT_CHECK" != "true" ]]; then
    check_root
fi

# Check if we're in the correct directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Please run this script from the project root directory."
    exit 1
fi

# Setup systemd if requested
if [[ "$SETUP_SYSTEMD" == "true" ]]; then
    setup_systemd
    exit 0
fi

# Set production environment
export NODE_ENV=production

# Load environment variables from .env.production if it exists
if [ -f ".env.production" ]; then
    echo "📄 Loading environment variables from .env.production..."
    export $(cat .env.production | grep -v '^#' | grep -v '^$' | xargs)
fi

# Set default values if not provided
# Support both BACKEND_PORT and PORT environment variables (for platform flexibility)
export BACKEND_HOST=${BACKEND_HOST:-0.0.0.0}
export BACKEND_PORT=${BACKEND_PORT:-${PORT:-8000}}
export WORKERS=${WORKERS:-1}

echo "🔧 Environment Configuration:"
echo "   NODE_ENV: $NODE_ENV"
echo "   BACKEND_HOST: $BACKEND_HOST"
echo "   BACKEND_PORT: $BACKEND_PORT"
echo "   WORKERS: $WORKERS"
echo "   USER: $USER"
echo "   PWD: $PWD"

# Create logs directory
mkdir -p logs

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down gracefully..."
    if [[ -n "$UVICORN_PID" ]]; then
        kill $UVICORN_PID 2>/dev/null || true
    fi
    exit 0
}

# Setup signal handlers
trap cleanup SIGINT SIGTERM

# Function to check system requirements
check_system_requirements() {
    echo "🔍 Checking system requirements..."
    
    # Check available memory
    if command -v free &> /dev/null; then
        AVAILABLE_MEM=$(free -m | awk 'NR==2{printf "%d", $7}')
        if [[ $AVAILABLE_MEM -lt 512 ]]; then
            echo "⚠️  Warning: Low available memory (${AVAILABLE_MEM}MB). Consider adding swap or upgrading."
        fi
    fi
    
    # Check disk space
    if command -v df &> /dev/null; then
        AVAILABLE_DISK=$(df -h . | awk 'NR==2{print $4}')
        echo "💾 Available disk space: $AVAILABLE_DISK"
    fi
    
    # Check if ports are available
    if command -v netstat &> /dev/null; then
        if netstat -tuln | grep -q ":$BACKEND_PORT "; then
            echo "⚠️  Warning: Port $BACKEND_PORT is already in use"
            echo "   You may need to stop the existing service or change the port"
        fi
    fi
}

# Check system requirements
check_system_requirements

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node --version | cut -d'v' -f2)
NODE_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1)
if [[ $NODE_MAJOR -lt 18 ]]; then
    echo "⚠️  Warning: Node.js version $NODE_VERSION detected. Node.js 18+ is recommended."
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 11 ]]; then
    echo "⚠️  Warning: Python version $PYTHON_VERSION detected. Python 3.11+ is recommended."
fi

# Install Node.js dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm ci --omit=dev
fi

# Build the frontend if dist directory doesn't exist
if [ ! -d "dist" ]; then
    echo "🏗️  Building frontend..."
    npm run build
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

# Check if all dependencies are installed
echo "✅ Verifying Python dependencies..."
python3 -c "
import sys
required_packages = ['fastapi', 'uvicorn', 'websockets', 'pydantic']
missing_packages = []
for package in required_packages:
    try:
        __import__(package)
        print(f'✓ {package}')
    except ImportError:
        missing_packages.append(package)
        print(f'✗ {package}')
        
if missing_packages:
    print(f'❌ Missing packages: {missing_packages}')
    sys.exit(1)
else:
    print('✅ All required packages are installed')
"

# Start the application
echo ""
echo "🎯 Starting the application..."
echo "   Backend will be available at: http://$BACKEND_HOST:$BACKEND_PORT"
echo "   Frontend (if built) will be served from the backend"
echo "   Health check: http://$BACKEND_HOST:$BACKEND_PORT/health"
echo "   Terminal health: http://$BACKEND_HOST:$BACKEND_PORT/api/terminal/health"
echo ""

if [[ "$DAEMON_MODE" == "true" ]]; then
    echo "🔄 Starting in daemon mode..."
    echo "   Logs will be written to: $PWD/logs/app.log"
    echo "   To stop: kill \$(cat $PWD/logs/app.pid)"
    echo ""
    
    # Start in background and save PID
    nohup python3 -m uvicorn main:app \
        --host "$BACKEND_HOST" \
        --port "$BACKEND_PORT" \
        --workers "$WORKERS" \
        --log-level info \
        --access-log \
        --log-config logging.conf 2>&1 > logs/app.log &
    
    echo $! > logs/app.pid
    echo "✅ Application started in daemon mode (PID: $(cat logs/app.pid))"
    
    # Display final access information
    echo ""
    echo "=============================================="
    echo "🚀 iLabors Code Editor is now running!"
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
    echo "⚠️  Note: Frontend is served from the backend server"
    echo "   Don't try to access ports 5173/5174 - they're not running in production"
    echo ""
    echo "🛑 To stop: kill \$(cat logs/app.pid)"
    echo "=============================================="
else
    echo "   Press Ctrl+C to stop the server"
    echo ""
    echo "=============================================="
    echo "🚀 iLabors Code Editor is now running!"
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
    echo "⚠️  Note: Frontend is served from the backend server"
    echo "   Don't try to access ports 5173/5174 - they're not running in production"
    echo ""
    echo "🛑 To stop: Press Ctrl+C"
    echo "=============================================="
    echo ""
    
    # Start in foreground
    python3 -m uvicorn main:app \
        --host "$BACKEND_HOST" \
        --port "$BACKEND_PORT" \
        --workers "$WORKERS" \
        --log-level info \
        --access-log &
    
    UVICORN_PID=$!
    wait $UVICORN_PID
fi
