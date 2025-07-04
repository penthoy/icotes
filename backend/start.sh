#!/bin/bash
# Start the FastAPI backend server

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 to run the backend."
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "pip3 is not installed. Please install pip3 to run the backend."
    exit 1
fi

echo "Installing Python dependencies..."
pip3 install -r requirements.txt

echo "Starting FastAPI backend server..."
python3 main.py
