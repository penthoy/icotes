#!/bin/bash
set -e

echo "Starting iLabors Code Editor..."

# Try different methods to install Python dependencies
echo "Installing Python dependencies..."
cd backend

# Method 1: Try with python3 -m pip
if python3 -m pip --version > /dev/null 2>&1; then
    echo "Using python3 -m pip..."
    python3 -m pip install --user -r requirements.txt
# Method 2: Try with pip3
elif command -v pip3 > /dev/null 2>&1; then
    echo "Using pip3..."
    pip3 install --user -r requirements.txt
# Method 3: Try with pip
elif command -v pip > /dev/null 2>&1; then
    echo "Using pip..."
    pip install --user -r requirements.txt
else
    echo "Warning: No pip found, trying to install packages manually..."
    # Try to install individual packages
    python3 -c "
import sys
import subprocess
packages = ['fastapi==0.104.1', 'uvicorn[standard]==0.24.0', 'websockets==12.0', 'pydantic==2.5.0', 'python-multipart==0.0.6']
for package in packages:
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', package])
        print(f'Successfully installed {package}')
    except Exception as e:
        print(f'Failed to install {package}: {e}')
"
fi

echo "Starting the application..."
python3 main.py
