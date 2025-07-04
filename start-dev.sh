#!/bin/bash

# Start development servers
echo "Starting development servers..."

# Start FastAPI backend
cd /app/backend
python3 main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start Vite frontend
cd /app
npm run dev &
FRONTEND_PID=$!

# Function to cleanup processes
cleanup() {
    echo "Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID
    exit 0
}

# Trap signals to cleanup processes
trap cleanup SIGINT SIGTERM

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
