#!/usr/bin/env python3
"""
Test WebSocket connection to terminal
"""
import asyncio
import websockets
import json

async def test_websocket():
    # Get available terminals
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8000/api/terminals') as resp:
            data = await resp.json()
            terminals = data.get('data', [])
            
            if not terminals:
                print("No terminals available")
                return
            
            terminal_id = terminals[0]['id']
            print(f"Testing terminal {terminal_id}")
            
            # Connect to WebSocket
            uri = f"ws://localhost:8000/ws/terminal/{terminal_id}"
            print(f"Connecting to {uri}")
            
            try:
                async with websockets.connect(uri) as websocket:
                    print("Connected to WebSocket!")
                    
                    # Send a simple command
                    await websocket.send("echo 'Hello from WebSocket test'\n")
                    
                    # Read response
                    for i in range(5):
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            print(f"Received: {repr(response)}")
                        except asyncio.TimeoutError:
                            print("No response received")
                            break
                            
            except Exception as e:
                print(f"WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
