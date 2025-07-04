#!/usr/bin/env python3

"""
Test script to verify WebSocket terminal connection works
"""

import asyncio
import websockets
import json
import sys

async def test_terminal_connection():
    uri = "ws://localhost/ws/terminal/test123"
    
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✓ WebSocket connection established")
            
            # Send a simple command
            await websocket.send("echo 'Hello from terminal test!'\n")
            print("✓ Command sent")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"✓ Received response: {repr(response)}")
                return True
            except asyncio.TimeoutError:
                print("✗ No response received within timeout")
                return False
                
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_terminal_connection())
    sys.exit(0 if success else 1)
