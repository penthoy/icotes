#!/bin/bash

# Test script for Custom Agent Dropdown functionality
# Run this after starting the development server

echo "🔍 Testing Custom Agent Dropdown Implementation..."
echo ""

# Test 1: Check if the API endpoint responds
echo "📡 Testing /api/agents/custom endpoint..."
curl -s -w "HTTP Status: %{http_code}\n" http://localhost:8000/api/agents/custom || echo "❌ Server not running on port 8000"
echo ""

# Test 2: Check if files exist
echo "📁 Checking component files..."
if [ -f "/home/penthoy/ilaborcode/src/components/CustomAgentDropdown.tsx" ]; then
    echo "✅ CustomAgentDropdown.tsx exists"
else
    echo "❌ CustomAgentDropdown.tsx missing"
fi

if [ -f "/home/penthoy/ilaborcode/src/hooks/useCustomAgents.ts" ]; then
    echo "✅ useCustomAgents.ts hook exists"
else
    echo "❌ useCustomAgents.ts hook missing"
fi

# Test 3: Check SimpleChat integration
echo ""
echo "📋 Checking SimpleChat integration..."
if grep -q "CustomAgentDropdown" "/home/penthoy/ilaborcode/tests/integration/simplechat.tsx"; then
    echo "✅ CustomAgentDropdown imported in SimpleChat"
else
    echo "❌ CustomAgentDropdown not imported in SimpleChat"
fi

if grep -q "selectedAgent" "/home/penthoy/ilaborcode/tests/integration/simplechat.tsx"; then
    echo "✅ Agent selection state implemented"
else
    echo "❌ Agent selection state missing"
fi

# Test 4: Check build
echo ""
echo "🔧 Testing build..."
cd /home/penthoy/ilaborcode
npm run build > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Build successful"
else
    echo "❌ Build failed"
fi

echo ""
echo "🎉 Custom Agent Dropdown testing complete!"
echo "📝 To test the full functionality:"
echo "   1. Start the development server: ./start-dev.sh"
echo "   2. Navigate to http://localhost:8000/simple-chat"
echo "   3. Verify the agent dropdown appears in the header"
echo "   4. Test agent selection and message sending"
