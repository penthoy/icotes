#!/usr/bin/env python3
"""
Test script to verify WebSocket endpoint migration from /ws/enhanced to /ws.
This script tests the new /ws endpoint (which should now have enhanced functionality)
and the deprecated /ws/legacy endpoint.
"""

import asyncio
import json
import websockets
import sys
import time

async def test_websocket_endpoint(url, test_name):
    """Test a WebSocket endpoint with a simple ping/pong and code execution."""
    print(f"\n=== Testing {test_name} ===")
    print(f"Connecting to: {url}")
    
    try:
        async with websockets.connect(url) as websocket:
            print("✓ Connected successfully")
            
            # First, check if we get a welcome message (enhanced endpoint)
            try:
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                welcome_data = json.loads(welcome_msg)
                if welcome_data.get("type") == "welcome":
                    print(f"✓ Received welcome message: {welcome_data.get('connection_id', 'N/A')}")
                    is_enhanced = True
                elif welcome_data.get("type") == "warning":
                    print(f"⚠ Received deprecation warning: {welcome_data.get('message')}")
                    is_enhanced = False
                else:
                    print(f"? Unexpected initial message: {welcome_data}")
                    is_enhanced = False
            except asyncio.TimeoutError:
                print("? No initial message received")
                is_enhanced = False
            
            # Test 1: Basic ping/pong
            print("Test 1: Ping/Pong")
            ping_message = json.dumps({"type": "ping"})
            await websocket.send(ping_message)
            response = await websocket.recv()
            response_data = json.loads(response)
            
            if response_data.get("type") == "pong":
                print("✓ Ping/Pong test passed")
            else:
                print(f"✗ Ping/Pong test failed: {response_data}")
            
            # Test 2: Code execution
            print("Test 2: Code Execution")
            if is_enhanced:
                # Use enhanced API format (direct execute message)
                code_message = json.dumps({
                    "type": "execute",
                    "code": "print('Hello from Enhanced WebSocket!')",
                    "language": "python"
                })
            else:
                # Use legacy format
                code_message = json.dumps({
                    "type": "execute",
                    "code": "print('Hello from Legacy WebSocket!')",
                    "language": "python"
                })
            
            await websocket.send(code_message)
            
            # For enhanced endpoint, we might get multiple messages
            max_attempts = 5
            for attempt in range(max_attempts):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "result":
                        print("✓ Code execution test passed")
                        print(f"  Output: {response_data.get('output', [])}")
                        break
                    elif response_data.get("type") == "execution_result":
                        print("✓ Code execution test passed (enhanced format)")
                        print(f"  Output: {response_data.get('output', [])}")
                        print(f"  Status: {response_data.get('status', 'unknown')}")
                        print(f"  Execution Time: {response_data.get('execution_time', 0):.4f}s")
                        break
                    elif response_data.get("type") in ["execution_started", "execution_update"]:
                        print(f"  Execution update: {response_data.get('status', 'unknown')}")
                        continue
                    elif response_data.get("type") == "error":
                        print(f"✗ Code execution failed with error: {response_data.get('message')}")
                        break
                    else:
                        print(f"  Received: {response_data.get('type', 'unknown')} - {response_data}")
                        if attempt == max_attempts - 1:
                            print("✗ Code execution test failed - no result received")
                except asyncio.TimeoutError:
                    print(f"✗ Code execution test failed - timeout on attempt {attempt + 1}")
                    break
            
    except Exception as e:
        print(f"✗ Error connecting to {url}: {e}")

async def main():
    """Run tests for both WebSocket endpoints."""
    base_url = "ws://localhost:8001"
    
    # Test the main /ws endpoint (should now have enhanced functionality)
    await test_websocket_endpoint(f"{base_url}/ws", "Main /ws Endpoint (Enhanced)")
    
    # Test the legacy /ws/legacy endpoint (should show deprecation warning)
    await test_websocket_endpoint(f"{base_url}/ws/legacy", "Legacy /ws/legacy Endpoint (Deprecated)")
    
    print("\n=== Migration Test Complete ===")
    print("Expected behavior:")
    print("- /ws should work with enhanced functionality (no warnings)")
    print("- /ws/legacy should work but show deprecation warnings")
    print("- Both endpoints should execute code successfully")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(0)
