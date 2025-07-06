#!/bin/bash
# Quick installation verification script

echo "🔍 Verifying iLabors Code Editor installation..."
echo ""

# Check if required files exist
echo "📁 Checking required files..."
check_file() {
    if [ -f "$1" ]; then
        echo "✅ $1"
    else
        echo "❌ $1 (missing)"
        return 1
    fi
}

check_file "package.json"
check_file "backend/main.py"
check_file "backend/requirements.txt"
check_file ".env"
check_file "start-dev.sh"

echo ""

# Check if commands exist
echo "🔧 Checking system dependencies..."
check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        VERSION=$($1 --version 2>/dev/null | head -1 || echo "installed")
        echo "✅ $1 ($VERSION)"
    else
        echo "❌ $1 (not installed)"
        return 1
    fi
}

check_command "node"
check_command "npm"
check_command "python3"
check_command "pip3"

echo ""

# Check if backend venv exists
echo "🐍 Checking Python virtual environment..."
if [ -d "backend/venv" ]; then
    echo "✅ backend/venv directory exists"
    if [ -f "backend/venv/bin/activate" ]; then
        echo "✅ Virtual environment is properly configured"
    else
        echo "❌ Virtual environment incomplete"
    fi
else
    echo "❌ backend/venv directory missing"
fi

echo ""

# Check if node_modules exists
echo "📦 Checking Node.js dependencies..."
if [ -d "node_modules" ]; then
    echo "✅ node_modules directory exists"
    if [ -f "node_modules/.package-lock.json" ]; then
        echo "✅ Dependencies are installed"
    else
        echo "⚠️  Dependencies may not be fully installed"
    fi
else
    echo "❌ node_modules directory missing"
fi

echo ""

# Check if scripts are executable
echo "🔐 Checking script permissions..."
check_executable() {
    if [ -x "$1" ]; then
        echo "✅ $1 (executable)"
    else
        echo "❌ $1 (not executable)"
        return 1
    fi
}

check_executable "setup.sh"
check_executable "start-dev.sh"
check_executable "check-servers.sh"

echo ""
echo "✅ Installation verification completed!"
echo ""
echo "🚀 To start the servers: ./start-dev.sh"
echo "🔍 To check status: ./check-servers.sh"
