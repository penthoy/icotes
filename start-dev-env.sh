#!/bin/bash

# Start development environment with proper environment variables

echo "Starting icotes Development Environment..."

# Load environment variables from .env file
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "Loaded environment variables from .env"
else
    echo "Warning: .env file not found"
fi

# Kill any existing processes
echo "Stopping any existing servers..."
pkill -f "uvicorn"
pkill -f "vite"
sleep 2

# Start backend
echo "Starting backend server..."
cd backend
chmod +x start.sh
./start.sh &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 3

# Test backend connection
if curl -s http://${BACKEND_HOST}:${BACKEND_PORT}/health > /dev/null; then
    echo "✅ Backend is running at http://${BACKEND_HOST}:${BACKEND_PORT}"
else
    echo "❌ Backend failed to start"
    exit 1
fi

# Start frontend
echo "Starting frontend server..."
FRONTEND_HOST=${FRONTEND_HOST} FRONTEND_PORT=${FRONTEND_PORT} VITE_API_URL=${VITE_API_URL} VITE_WS_URL=${VITE_WS_URL} npm run dev-frontend &
FRONTEND_PID=$!

# Wait for frontend to start
echo "Waiting for frontend to start..."
sleep 3

# Test frontend connection
if curl -s http://${FRONTEND_HOST}:${FRONTEND_PORT} > /dev/null; then
    echo "✅ Frontend is running at http://${FRONTEND_HOST}:${FRONTEND_PORT}"
else
    echo "❌ Frontend failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo ""
echo "🚀 Development environment is ready!"
echo "📱 Frontend: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
echo "🔧 Backend: http://${BACKEND_HOST}:${BACKEND_PORT}"
echo "❤️  Health: http://${BACKEND_HOST}:${BACKEND_PORT}/health"
echo ""
echo "Press Ctrl+C to stop all servers"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    pkill -f "uvicorn" 2>/dev/null
    pkill -f "vite" 2>/dev/null
    echo "Servers stopped."
    exit 0
}

# Trap Ctrl+C
trap cleanup INT

# Wait for processes
wait
