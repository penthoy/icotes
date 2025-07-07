#!/bin/bash
set -e

echo "Installing Python dependencies..."
cd backend
python3 -m pip install --user -r requirements.txt

echo "Starting application..."
python3 main.py
