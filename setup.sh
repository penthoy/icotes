#!/bin/bash
# iLabors Code Editor - Automated Setup Script
# This script sets up the complete development environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Node.js
install_nodejs() {
    print_status "Installing Node.js and npm..."
    
    if command_exists node && command_exists npm; then
        NODE_VERSION=$(node --version)
        print_success "Node.js already installed: $NODE_VERSION"
        return 0
    fi
    
    # Install Node.js via NodeSource repository for better compatibility
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
    
    # Verify installation
    if command_exists node && command_exists npm; then
        NODE_VERSION=$(node --version)
        NPM_VERSION=$(npm --version)
        print_success "Node.js installed: $NODE_VERSION"
        print_success "npm installed: $NPM_VERSION"
    else
        print_error "Failed to install Node.js"
        exit 1
    fi
}

# Function to install Python and pip
install_python() {
    print_status "Installing Python and pip..."
    
    if command_exists python3 && command_exists pip3; then
        PYTHON_VERSION=$(python3 --version)
        print_success "Python already installed: $PYTHON_VERSION"
        return 0
    fi
    
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv python3-full
    
    # Verify installation
    if command_exists python3 && command_exists pip3; then
        PYTHON_VERSION=$(python3 --version)
        print_success "Python installed: $PYTHON_VERSION"
    else
        print_error "Failed to install Python"
        exit 1
    fi
}

# Function to setup backend
setup_backend() {
    print_status "Setting up backend..."
    
    cd backend
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    print_status "Installing Python dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
    
    print_success "Backend setup completed"
    cd ..
}

# Function to setup frontend
setup_frontend() {
    print_status "Setting up frontend..."
    
    # Install Node.js dependencies
    print_status "Installing Node.js dependencies..."
    npm install
    
    print_success "Frontend setup completed"
}

# Function to setup environment configuration
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        print_status "Creating .env file..."
        
        # Get local IP address
        LOCAL_IP=$(hostname -I | awk '{print $1}')
        
        cat > .env << EOF
# Environment Configuration for iLabors Code Editor

# Backend Configuration
BACKEND_HOST=${LOCAL_IP}
BACKEND_PORT=8000
BACKEND_URL=http://${LOCAL_IP}:8000

# Frontend Configuration
FRONTEND_HOST=${LOCAL_IP}
FRONTEND_PORT=5173
FRONTEND_URL=http://${LOCAL_IP}:5173

# API Configuration
VITE_API_URL=http://${LOCAL_IP}:8000
VITE_WS_URL=ws://${LOCAL_IP}:8000

# Development vs Production
NODE_ENV=development
EOF
        
        print_success ".env file created with IP: $LOCAL_IP"
    else
        print_warning ".env file already exists, skipping creation"
    fi
}

# Function to make scripts executable
setup_scripts() {
    print_status "Making scripts executable..."
    
    chmod +x start-dev.sh
    chmod +x backend/start.sh
    chmod +x check-servers.sh
    chmod +x test-connectivity.sh
    
    print_success "Scripts made executable"
}

# Function to test installation
test_installation() {
    print_status "Testing installation..."
    
    # Start servers in background
    print_status "Starting development servers..."
    ./start-dev.sh &
    SERVER_PID=$!
    
    # Wait for servers to start
    sleep 10
    
    # Test backend
    if curl -s http://localhost:8000 > /dev/null 2>&1; then
        print_success "Backend server is running"
    else
        print_error "Backend server failed to start"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
    
    # Test frontend
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        print_success "Frontend server is running"
    else
        print_error "Frontend server failed to start"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
    
    # Stop test servers
    kill $SERVER_PID 2>/dev/null
    sleep 2
    
    print_success "Installation test completed successfully"
}

# Main installation function
main() {
    echo "=========================================="
    echo "iLabors Code Editor - Setup Script"
    echo "=========================================="
    echo ""
    
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        print_error "Please don't run this script as root"
        exit 1
    fi
    
    # Check if we're in the correct directory
    if [ ! -f "package.json" ] || [ ! -f "backend/main.py" ]; then
        print_error "Please run this script from the project root directory"
        exit 1
    fi
    
    print_status "Starting installation process..."
    
    # Update system packages
    print_status "Updating system packages..."
    sudo apt-get update
    
    # Install system dependencies
    print_status "Installing system dependencies..."
    sudo apt-get install -y curl git build-essential
    
    # Install Node.js
    install_nodejs
    
    # Install Python
    install_python
    
    # Setup backend
    setup_backend
    
    # Setup frontend
    setup_frontend
    
    # Setup environment
    setup_environment
    
    # Setup scripts
    setup_scripts
    
    # Test installation
    test_installation
    
    echo ""
    echo "=========================================="
    print_success "Installation completed successfully!"
    echo "=========================================="
    echo ""
    echo "🚀 To start the development servers:"
    echo "   ./start-dev.sh"
    echo ""
    echo "🔍 To check server status:"
    echo "   ./check-servers.sh"
    echo ""
    echo "🌐 Access URLs:"
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    echo "   📱 Frontend: http://${LOCAL_IP}:5173"
    echo "   🔧 Backend:  http://${LOCAL_IP}:8000"
    echo "   📚 API Docs: http://${LOCAL_IP}:8000/docs"
    echo ""
    echo "📝 Configuration file: .env"
    echo "📖 Documentation: docs/"
    echo ""
}

# Run main function
main "$@"
