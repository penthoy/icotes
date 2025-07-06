#!/bin/bash
# Comprehensive connectivity test for iLabors Code Editor

echo "🔍 Testing iLabors Code Editor connectivity on 192.168.2.195..."
echo ""

# Test backend health
echo -n "Backend API Health: "
if curl -s http://192.168.2.195:8000 > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Test backend API docs
echo -n "Backend API Docs: "
if curl -s http://192.168.2.195:8000/docs > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Test frontend
echo -n "Frontend Interface: "
if curl -s http://192.168.2.195:5173 > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Test WebSocket endpoint (basic connectivity)
echo -n "WebSocket Endpoint: "
if curl -s --http1.1 -H "Connection: Upgrade" -H "Upgrade: websocket" http://192.168.2.195:8000/ws > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "⚠️  Cannot test WebSocket via curl (normal for WS)"
fi

echo ""
echo "🌐 Access URLs:"
echo "   📱 Frontend: http://192.168.2.195:5173"
echo "   🔧 Backend API: http://192.168.2.195:8000"
echo "   📚 API Docs: http://192.168.2.195:8000/docs"
echo "   🔌 WebSocket: ws://192.168.2.195:8000/ws"
echo ""

# Check if servers are listening on correct interfaces
echo "🔍 Server listening status:"
echo "Backend processes:"
netstat -tlnp 2>/dev/null | grep :8000 || echo "No backend process found on port 8000"
echo "Frontend processes:"
netstat -tlnp 2>/dev/null | grep :5173 || echo "No frontend process found on port 5173"

echo ""
echo "✅ Connectivity test completed!"
