#!/usr/bin/env python3
"""
Test script to verify the streaming fix for chat service.
This script tests that only streaming messages are sent, not duplicate complete messages.
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock
from icpy.services.chat_service import ChatService, ChatMessage, MessageSender

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockWebSocket:
    def __init__(self):
        self.sent_messages = []
    
    async def send_json(self, data):
        self.sent_messages.append(data)
        print(f"WebSocket sent: {data.get('type', 'unknown')} - {data.get('content', data.get('chunk', 'no content'))[:50]}...")
    
    async def send_text(self, text):
        # Mock method for compatibility
        pass

class MockAgent:
    def __init__(self):
        self.responses = [
            {"message_type": "text", "content": "Hello "},
            {"message_type": "text", "content": "this "},
            {"message_type": "text", "content": "is "},
            {"message_type": "text", "content": "a "},
            {"message_type": "text", "content": "streaming "},
            {"message_type": "text", "content": "response!"}
        ]
    
    async def execute(self, task, context):
        """Mock agent execution that yields streaming responses"""
        for response in self.responses:
            from icpy.agent.base_agent import AgentMessage
            yield AgentMessage(
                agent_id="test-agent",
                content=response["content"],
                message_type=response["message_type"]
            )
            await asyncio.sleep(0.1)  # Simulate processing delay

class MockAgentSession:
    def __init__(self):
        self.session_id = "test-session"
        self.agent_id = "test-agent"
        self.agent_name = "Test Agent"
        self.status = MagicMock()
        self.status.value = "ready"
        self.last_activity = 0

class MockAgentService:
    def __init__(self):
        self.agent_sessions = {"test-session": MockAgentSession()}
        self.active_agents = {"test-session": MockAgent()}
    
    def get_agent_sessions(self):
        return [self.agent_sessions["test-session"]]

async def test_streaming_no_duplicates():
    """Test that streaming doesn't create duplicate messages"""
    print("\n=== Testing Streaming Response Fix ===")
    
    # Create chat service with mock database (in-memory)
    chat_service = ChatService(db_path=":memory:")
    
    # Initialize database properly
    import aiosqlite
    async with aiosqlite.connect(":memory:") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                sender TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                type TEXT DEFAULT 'message',
                metadata TEXT DEFAULT '{}',
                agent_id TEXT,
                session_id TEXT,
                created_at REAL DEFAULT (julianday('now'))
            )
        """)
        await db.commit()
    
    chat_service.db_path = ":memory:"
    
    # Mock the agent service
    chat_service.agent_service = MockAgentService()
    chat_service.config.agent_id = "test-agent"
    chat_service.config.agent_name = "Test Agent"
    
    # Mock WebSocket connection
    mock_websocket = MockWebSocket()
    connection_id = "test-connection"
    session_id = await chat_service.connect_websocket(connection_id)
    chat_service.websocket_connections[connection_id] = mock_websocket
    
    print(f"Chat session created: {session_id}")
    
    # Send a test message
    print("\nSending test message...")
    await chat_service.handle_user_message(connection_id, "Hello, please respond with streaming!")
    
    # Analyze sent messages
    print(f"\nTotal WebSocket messages sent: {len(mock_websocket.sent_messages)}")
    
    streaming_messages = []
    complete_messages = []
    
    for msg in mock_websocket.sent_messages:
        msg_type = msg.get('type', 'unknown')
        if msg_type == 'message_stream':
            streaming_messages.append(msg)
        elif msg_type == 'message':
            complete_messages.append(msg)
        else:
            print(f"Other message type: {msg_type}")
    
    print(f"Streaming messages: {len(streaming_messages)}")
    print(f"Complete messages: {len(complete_messages)}")
    
    # Check for duplicates
    if len(complete_messages) > 0:
        print("\n❌ DUPLICATE DETECTED!")
        print(f"Found {len(complete_messages)} complete message(s) in addition to streaming:")
        for msg in complete_messages:
            print(f"  - Complete message: {msg.get('content', 'no content')[:50]}...")
        return False
    else:
        print("\n✅ NO DUPLICATES FOUND!")
        print("Only streaming messages were sent (as expected)")
        
        # Show streaming progression
        print("\nStreaming message progression:")
        for i, msg in enumerate(streaming_messages):
            if msg.get('stream_start'):
                print(f"  {i+1}. Stream START")
            elif msg.get('stream_chunk'):
                chunk = msg.get('chunk', '')
                print(f"  {i+1}. Chunk: '{chunk}'")
            elif msg.get('stream_end'):
                print(f"  {i+1}. Stream END")
        
        return True

async def test_database_storage():
    """Test that only final complete messages are stored in database"""
    print("\n=== Testing Database Storage ===")
    
    chat_service = ChatService(db_path=":memory:")
    await chat_service._initialize_database()
    
    # Mock the agent service
    chat_service.agent_service = MockAgentService()
    chat_service.config.agent_id = "test-agent"
    
    connection_id = "test-connection"
    session_id = await chat_service.connect_websocket(connection_id)
    chat_service.websocket_connections[connection_id] = MockWebSocket()
    
    # Send test message
    await chat_service.handle_user_message(connection_id, "Test message for database")
    
    # Check database
    messages = await chat_service.get_message_history(session_id)
    
    ai_messages = [msg for msg in messages if msg.sender == MessageSender.AI]
    user_messages = [msg for msg in messages if msg.sender == MessageSender.USER]
    
    print(f"Messages in database: {len(messages)} total")
    print(f"  - User messages: {len(user_messages)}")
    print(f"  - AI messages: {len(ai_messages)}")
    
    if len(ai_messages) == 1:
        print("✅ Correct: Only one AI message stored in database")
        ai_msg = ai_messages[0]
        print(f"  Content: {ai_msg.content}")
        return True
    else:
        print(f"❌ Error: Expected 1 AI message, found {len(ai_messages)}")
        for msg in ai_messages:
            print(f"  AI message: {msg.content[:50]}...")
        return False

if __name__ == "__main__":
    async def main():
        print("Testing chat service streaming fix...")
        
        test1_result = await test_streaming_no_duplicates()
        test2_result = await test_database_storage()
        
        print(f"\n=== RESULTS ===")
        print(f"Streaming test: {'PASS' if test1_result else 'FAIL'}")
        print(f"Database test: {'PASS' if test2_result else 'FAIL'}")
        
        if test1_result and test2_result:
            print("\n🎉 ALL TESTS PASSED! Streaming fix is working correctly.")
        else:
            print("\n❌ Some tests failed. Review the fixes needed.")
    
    asyncio.run(main())
