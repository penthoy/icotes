#!/bin/bash
# Tempo environment startup script
# This script builds the React app and starts the FastAPI backend

set -e  # Exit on any error

echo "🚀 Starting iLabors Code Editor for Tempo environment..."

# Step 1: Install backend dependencies
echo "📦 Installing backend dependencies..."
cd /app/backend
pip3 install -r requirements.txt

# Step 2: Build the React app
echo "🏗️  Building React application..."
cd /app
npm run build

# Step 3: Start the FastAPI backend
echo "🔧 Starting FastAPI backend..."
cd /app/backend

# Use PORT environment variable if set, otherwise default to 8000
export PORT=${PORT:-8000}
echo "📡 Server will run on port: $PORT"

# Start the server
exec python3 main.py
