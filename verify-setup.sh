#!/bin/bash
# Quick installation verification script

echo "🔍 Verifying icotes installation..."
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

# Check if UV is available and backend dependencies are installed
echo "🐍 Checking Python dependency management..."
if command -v uv >/dev/null 2>&1; then
    echo "✅ UV package manager available"
    cd backend
    if [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
        if uv run python -c "import fastapi" 2>/dev/null; then
            echo "✅ Python dependencies properly installed"
        else
            echo "❌ Python dependencies not installed - run 'uv sync' in backend/"
        fi
    else
        echo "❌ No pyproject.toml or requirements.txt found"
    fi
    cd ..
else
    echo "❌ UV package manager not available - install UV or use traditional pip"
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
