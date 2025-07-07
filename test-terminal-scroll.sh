#!/bin/bash
# Simple bash script to test terminal scrollbar functionality

echo "🚀 Starting terminal scrollbar test (bash version)..."
echo "=========================================="

# Generate 50 lines of output
for i in {1..50}; do
    echo "Line $i: Testing terminal scrollbar functionality - abcdefghijklmnopqrstuvwxyz"
    sleep 0.1
done

echo ""
echo "=========================================="
echo "✅ Terminal scrollbar test complete!"
echo "📝 Check that the scrollbar is visible and working properly"
echo "🎯 The terminal should not overflow the bottom boundary"
echo "=========================================="
