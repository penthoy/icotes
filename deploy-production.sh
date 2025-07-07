#!/bin/bash

# Production deployment script
# This script builds the React app and starts the FastAPI server on port 80

echo "🚀 Starting production deployment..."

# Step 1: Build the React app
echo "📦 Building React application..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Build successful!"

# Step 2: Start the FastAPI server on port 80
echo "🔧 Starting FastAPI server on port 80..."
cd backend

# Set environment variables for production
export PORT=80
export ENVIRONMENT=production

# Start the server
python3 main.py

echo "🎉 Production server started!"
echo "📡 Application accessible at: http://localhost"
echo "🔌 WebSocket terminals available at: ws://localhost/ws/terminal/{id}"
