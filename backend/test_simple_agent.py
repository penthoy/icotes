#!/usr/bin/env python3
"""
Test Custom Agent with Simple Message
"""

import asyncio
import json
import websockets
import time

async def test_custom_agent_simple():
    """Test PersonalAgent with simple message"""
    
    print("🧪 Testing PersonalAgent")
    print("=" * 30)
    
    uri = "ws://192.168.2.195:8000/ws/chat"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected")
            
            # Send message to PersonalAgent
            test_message = {
                "type": "message",
                "content": "Hello, who are you?",
                "sender": "user", 
                "timestamp": int(time.time() * 1000),
                "metadata": {
                    "agentType": "PersonalAgent"
                }
            }
            
            print(f"📤 Sending: {test_message['content']}")
            print(f"🎯 Agent: {test_message['metadata']['agentType']}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for responses
            ai_messages = []
            start_time = time.time()
            timeout = 10
            
            while (time.time() - start_time) < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    response_data = json.loads(response)
                    
                    # Only print AI messages and stream chunks
                    if response_data.get('type') == 'message' and response_data.get('sender') == 'ai':
                        ai_messages.append(response_data['content'])
                        print(f"🤖 AI Response: {response_data['content']}")
                    elif response_data.get('type') == 'message_stream' and response_data.get('chunk'):
                        print(f"📦 Stream: {response_data['chunk']}", end='', flush=True)
                    elif response_data.get('type') == 'message_stream' and response_data.get('stream_end'):
                        print("\n🏁 Stream complete")
                        break
                        
                except asyncio.TimeoutError:
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
                    break
            
            if ai_messages:
                print(f"\n✅ SUCCESS: Received {len(ai_messages)} AI response(s)")
                return True
            else:
                print(f"\n❌ FAILED: No AI responses received")
                return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_custom_agent_simple())
    print(f"\n🏁 Test Result: {'PASS' if result else 'FAIL'}")
