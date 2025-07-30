#!/usr/bin/env python3
"""
Test Default Agent vs Custom Agent
"""

import asyncio
import json
import websockets
import time

async def test_default_vs_custom():
    """Compare default agent vs custom agent"""
    
    print("🧪 Testing Default vs Custom Agent")
    print("=" * 40)
    
    uri = "ws://192.168.2.195:8000/ws/chat"
    
    # Test 1: Default agent (no agentType)
    print("\n1️⃣ Testing DEFAULT agent (no agentType)")
    try:
        async with websockets.connect(uri) as websocket:
            test_message = {
                "type": "message",
                "content": "Hello, test default",
                "sender": "user", 
                "timestamp": int(time.time() * 1000)
                # No metadata/agentType - should use default
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 Sent message without agentType")
            
            # Wait for response
            timeout = 5
            start_time = time.time()
            while (time.time() - start_time) < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    response_data = json.loads(response)
                    
                    if response_data.get('type') == 'message' and response_data.get('sender') == 'ai':
                        print(f"🔧 Default Response: {response_data['content']}")
                        break
                        
                except asyncio.TimeoutError:
                    break
                    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Custom agent 
    print("\n2️⃣ Testing CUSTOM agent (PersonalAgent)")
    try:
        async with websockets.connect(uri) as websocket:
            test_message = {
                "type": "message",
                "content": "Hello, test custom",
                "sender": "user", 
                "timestamp": int(time.time() * 1000),
                "metadata": {
                    "agentType": "PersonalAgent"
                }
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 Sent message with agentType=PersonalAgent")
            
            # Wait for streaming response
            timeout = 5
            start_time = time.time()
            response_content = ""
            while (time.time() - start_time) < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    response_data = json.loads(response)
                    
                    if response_data.get('type') == 'message_stream' and response_data.get('chunk'):
                        response_content += response_data['chunk']
                    elif response_data.get('type') == 'message_stream' and response_data.get('stream_end'):
                        break
                        
                except asyncio.TimeoutError:
                    break
                    
            print(f"🤖 Custom Response: {response_content}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_default_vs_custom())
