#!/bin/bash
# icotes - Automated Setup Script
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
    print_status "Checking Node.js installation..."
    
    if command_exists node && command_exists npm; then
        NODE_VERSION=$(node --version)
        NPM_VERSION=$(npm --version)
        print_success "Node.js already installed: $NODE_VERSION"
        print_success "npm already installed: $NPM_VERSION"
        
        # Check if version is adequate (v18+)
        NODE_MAJOR=$(echo $NODE_VERSION | sed 's/v//' | cut -d. -f1)
        if [ "$NODE_MAJOR" -ge 18 ]; then
            print_success "Node.js version is adequate (v18+)"
            return 0
        else
            print_warning "Node.js version is old ($NODE_VERSION), upgrading..."
        fi
    fi
    
    print_status "Installing/upgrading Node.js and npm..."
    
    # Install Node.js via NodeSource repository for better compatibility
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
    
    # Verify installation
    if command_exists node && command_exists npm; then
        NODE_VERSION=$(node --version)
        NPM_VERSION=$(npm --version)
        print_success "Node.js installed/updated: $NODE_VERSION"
        print_success "npm installed/updated: $NPM_VERSION"
    else
        print_error "Failed to install Node.js"
        exit 1
    fi
}

# Function to install Python and pip
install_python() {
    print_status "Checking Python installation..."
    
    if command_exists python3 && command_exists pip3; then
        PYTHON_VERSION=$(python3 --version)
        print_success "Python already installed: $PYTHON_VERSION"
        return 0
    fi
    
    print_status "Installing/updating Python and pip..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-full python3-venv
    
    # Verify installation
    if command_exists python3 && command_exists pip3; then
        PYTHON_VERSION=$(python3 --version)
        print_success "Python installed/updated: $PYTHON_VERSION"
    else
        print_error "Failed to install Python"
        exit 1
    fi
}

# Function to setup backend
setup_backend() {
    print_status "Setting up backend with UV package manager..."
    
    cd backend
    
    # Install UV if not available
    if ! command_exists uv; then
        print_status "Installing UV package manager..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
        
        if ! command_exists uv; then
            print_warning "UV installation failed, falling back to traditional pip..."
            
            # Setup virtual environment if needed
            if [ ! -d "venv" ]; then
                print_status "Creating Python virtual environment..."
                python3 -m venv venv
            fi
            
            print_status "Activating virtual environment and installing dependencies..."
            source venv/bin/activate
            python3 -m pip install --upgrade pip
            python3 -m pip install -r requirements.txt
        else
            print_success "UV installed successfully"
            # Initialize UV project if needed
            if [ ! -f "pyproject.toml" ]; then
                print_status "Initializing UV project..."
                uv init --no-readme --no-pin-python
            fi
            # Install/update dependencies with UV
            print_status "Installing/updating Python dependencies with UV..."
            uv sync --frozen --no-dev || uv pip install -r requirements.txt
        fi
    else
        print_status "UV already installed, updating dependencies..."
        # Initialize UV project if needed
        if [ ! -f "pyproject.toml" ]; then
            print_status "Initializing UV project..."
            uv init --no-readme --no-pin-python
        fi
        # Install/update dependencies with UV
        print_status "Installing/updating Python dependencies with UV..."
        uv sync --frozen --no-dev || uv pip install -r requirements.txt
    fi
    
    # Ensure workspace directory exists
    if [ ! -d "../workspace" ]; then
        print_status "Creating workspace directory..."
        mkdir -p ../workspace
        print_success "Workspace directory created"
    fi
    
    print_success "Backend setup completed with modern dependency management"
    cd ..
}

# Function to setup frontend
setup_frontend() {
    print_status "Setting up frontend..."
    
    # Install/update Node.js dependencies
    print_status "Installing/updating Node.js dependencies..."
    npm install
    
    # Ensure dist directory is clean for fresh builds
    if [ -d "dist" ]; then
        print_status "Cleaning previous build artifacts..."
        rm -rf dist
    fi
    
    print_success "Frontend setup completed"
}

# Function to setup environment configuration
setup_environment() {
    print_status "Setting up environment configuration..."
    
    # Get local IP address
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    
    # Check if .env already exists - if so, skip creation to preserve existing configuration
    if [ -f ".env" ]; then
        print_success ".env file already exists - preserving existing configuration"
        print_warning "⚠️  If you need to update configuration, please manually edit .env or remove it and run setup again"
        return 0
    fi
    
    print_status "Creating .env file with single-port configuration..."
    
    # Create new .env file matching current configuration structure
    cat > .env << EOF
SITE_URL=${LOCAL_IP}
PORT=8000

# Single port configuration - everything runs on port 8000
BACKEND_HOST=${LOCAL_IP}
BACKEND_PORT=8000
BACKEND_URL=http://${LOCAL_IP}:8000

# Frontend should also be served from port 8000 in single port mode
FRONTEND_HOST=${LOCAL_IP}
FRONTEND_PORT=8000
FRONTEND_URL=http://${LOCAL_IP}:8000

# Vite-accessible environment variables (prefixed with VITE_)
VITE_BACKEND_URL=http://${LOCAL_IP}:8000
VITE_API_URL=http://${LOCAL_IP}:8000/api
VITE_SITE_URL=${LOCAL_IP}
VITE_WS_URL=ws://${LOCAL_IP}:8000/ws

# Workspace Configuration
WORKSPACE_ROOT=$(pwd)/workspace
VITE_WORKSPACE_ROOT=$(pwd)/workspace

# API For Agents (placeholder keys - replace with your actual keys):
OPENAI_API_KEY=your_openai_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CEREBRAS_API_KEY=your_cerebras_api_key_here
PUSHOVER_USER=your_pushover_user_here
PUSHOVER_TOKEN=your_pushover_token_here
MAILERSEND_API_KEY=your_mailersend_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
DASHSCOPE_API_KEY=your_dashscope_api_key_here
MOONSHOT_API_KEY=your_moonshot_api_key_here
EOF
    
    print_success ".env file created with single-port configuration (IP: $LOCAL_IP)"
    print_warning "⚠️  Please update the API keys in .env with your actual keys before using agent features"
}

# Function to make scripts executable
setup_scripts() {
    print_status "Making scripts executable..."
    
    # Make all necessary scripts executable
    chmod +x start-dev.sh 2>/dev/null || print_warning "start-dev.sh not found"
    chmod +x backend/start.sh 2>/dev/null || print_warning "backend/start.sh not found"
    chmod +x backend/start_with_uv.sh 2>/dev/null || print_warning "backend/start_with_uv.sh not found"
    chmod +x check-servers.sh 2>/dev/null || print_warning "check-servers.sh not found"
    chmod +x setup.sh 2>/dev/null || print_warning "setup.sh not found"
    chmod +x verify-setup.sh 2>/dev/null || print_warning "verify-setup.sh not found"
    chmod +x deploy-production.sh 2>/dev/null || print_warning "deploy-production.sh not found"
    
    print_success "Scripts made executable"
}

# Function to test installation
test_installation() {
    print_status "Testing installation..."
    
    # Build frontend first
    print_status "Building frontend for testing..."
    npm run build || {
        print_error "Frontend build failed"
        return 1
    }
    
    # Test backend startup
    print_status "Testing backend startup..."
    cd backend
    
    # Test with UV if available, fallback to traditional method
    if command_exists uv; then
        timeout 10s uv run python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from main import app
    print('✅ Backend imports successfully')
except Exception as e:
    print(f'❌ Backend import failed: {e}')
    sys.exit(1)
" || {
        print_error "Backend startup test failed"
        cd ..
        return 1
    }
    else
        # Fallback to traditional venv test
        if [ -d "venv" ]; then
            source venv/bin/activate
            timeout 10s python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from main import app
    print('✅ Backend imports successfully')
except Exception as e:
    print(f'❌ Backend import failed: {e}')
    sys.exit(1)
" || {
            print_error "Backend startup test failed"
            cd ..
            return 1
        }
        fi
    fi
    
    cd ..
    print_success "Installation test completed successfully"
}

# Main installation function
main() {
    echo "=========================================="
    echo "icotes - Setup Script"
    echo "Modern Development Environment Setup"
    echo "=========================================="
    echo ""
    
    # Check if this is a re-run
    if [ -f ".env" ] && [ -d "node_modules" ] && [ -d "backend" ]; then
        print_status "Existing installation detected - updating configuration..."
        echo ""
    fi
    
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        print_error "Please don't run this script as root"
        print_error "Run as your regular user account"
        exit 1
    fi
    
    # Check if we're in the correct directory
    if [ ! -f "package.json" ] || [ ! -f "backend/main.py" ]; then
        print_error "Please run this script from the project root directory"
        print_error "Expected files: package.json, backend/main.py"
        exit 1
    fi
    
    print_status "Starting setup process..."
    
    # Update system packages
    print_status "Updating system packages..."
    sudo apt-get update -qq
    
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
    print_success "Setup completed successfully!"
    echo "=========================================="
    echo ""
    echo "🚀 To start the development servers:"
    echo "   ./start-dev.sh"
    echo ""
    echo "🔍 To check server status:"
    echo "   ./check-servers.sh"
    echo ""
    echo "🌐 Access URLs (Single Port Setup):"
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    echo "   🌍 Application: http://${LOCAL_IP}:8000"
    echo "   � API Docs:    http://${LOCAL_IP}:8000/docs"
    echo "   � WebSocket:   ws://${LOCAL_IP}:8000/ws"
    echo ""
    echo "📝 Configuration:"
    echo "   .env file - Main configuration (API keys need to be updated)"
    echo "   backend/ - Python backend with UV package manager"
    echo "   src/ - React frontend components"
    echo "   workspace/ - Code execution workspace"
    echo ""
    echo "📖 Documentation:"
    echo "   README.md - Quick start guide"
    echo "   SETUP.md - Detailed setup instructions"
    echo "   docs/ - Full documentation"
    echo ""
    echo "⚠️  IMPORTANT: Update API keys in .env before using agent features!"
    echo ""
}

# Run main function
main "$@"
