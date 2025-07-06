#!/bin/bash
# Verification script to check if both servers are running

echo "🔍 Checking iLabors Code Editor servers..."

# Check backend
echo -n "Backend (port 8000): "
if curl -s http://localhost:8000 > /dev/null 2>&1; then
    echo "✅ Running"
else
    echo "❌ Not running"
fi

# Check frontend
echo -n "Frontend (port 5173): "
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "✅ Running"
else
    echo "❌ Not running"
fi

echo ""
echo "🌐 If both servers are running, you can access:"
echo "   📱 Frontend: http://localhost:5173"
echo "   🔧 Backend API: http://localhost:8000"
echo "   📚 API Docs: http://localhost:8000/docs"
