#!/bin/bash

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start development servers
echo "Starting development servers..."

# Start FastAPI backend
cd backend
source venv/bin/activate
python3 main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start Vite frontend
cd ..
npm run dev-frontend &
FRONTEND_PID=$!

# Function to cleanup processes
cleanup() {
    echo "Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID
    exit 0
}

# Trap signals to cleanup processes
trap cleanup SIGINT SIGTERM

echo "🚀 Development servers started:"
echo "   Frontend: ${FRONTEND_URL:-http://localhost:5173}"
echo "   Backend:  ${BACKEND_URL:-http://localhost:8000}"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
