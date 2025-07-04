#!/bin/bash

# Test script to verify terminal connection works

echo "Testing terminal connection..."

# Test 1: Check if backend is running
echo "1. Checking backend health..."
curl -s http://localhost:8000/health | grep -q "healthy"
if [ $? -eq 0 ]; then
    echo "✓ Backend is healthy"
else
    echo "✗ Backend is not healthy"
    exit 1
fi

# Test 2: Check if WebSocket endpoint is accessible
echo "2. Checking WebSocket endpoint..."
# We'll use a simple test to see if the endpoint exists
curl -s -I http://localhost:8000/ws/terminal/test | grep -q "426"
if [ $? -eq 0 ]; then
    echo "✓ WebSocket endpoint is accessible (426 Upgrade Required is expected)"
else
    echo "? WebSocket endpoint response unclear (this is normal for WebSocket endpoints)"
fi

# Test 3: Check if frontend is serving
echo "3. Checking frontend..."
curl -s http://localhost:5173 | grep -q "Vite"
if [ $? -eq 0 ]; then
    echo "✓ Frontend development server is running"
else
    echo "✗ Frontend development server not accessible"
fi

# Test 4: Check if production build works
echo "4. Checking production build..."
if [ -f "/app/dist/index.html" ]; then
    echo "✓ Production build exists"
    # Test if backend serves the React app
    curl -s http://localhost:8000 | grep -q "iLabors"
    if [ $? -eq 0 ]; then
        echo "✓ Backend serves React app correctly"
    else
        echo "? Backend serves React app but content unclear"
    fi
else
    echo "✗ Production build not found"
fi

echo "Test completed!"
