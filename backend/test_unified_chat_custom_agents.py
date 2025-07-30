#!/usr/bin/env python3
"""
Test script to validate unified chat service custom agent integration (Step 6.5).
Tests that the chat service correctly routes messages based on agentType.
"""

import asyncio
import aiohttp
import json
import pytest
from unittest.mock import AsyncMock, patch

from icpy.services.chat_service import ChatService, ChatMessage, MessageSender
from icpy.agent import custom_agent


@pytest.mark.asyncio
async def test_custom_agent_routing():
    """Test that chat service routes to custom agents based on agentType"""
    
    # Mock the custom agent registry
    mock_registry = AsyncMock()
    mock_registry.get_agent.return_value = AsyncMock()
    mock_registry.get_agent.return_value.stream_chat.return_value = [
        "Hello! I'm a personal agent.",
        " I can help you with personal tasks.",
        " How can I assist you today?"
    ]
    
    # Mock dependencies
    with patch('icpy.services.chat_service.get_db_manager') as mock_db, \
         patch('icpy.services.chat_service.get_message_broker') as mock_broker, \
         patch('icpy.services.chat_service.get_connection_manager') as mock_conn, \
         patch('icpy.agent.custom_agent.registry', mock_registry):
        
        # Setup mocks
        mock_db.return_value = AsyncMock()
        mock_broker.return_value = AsyncMock()
        mock_conn.return_value = AsyncMock()
        
        # Create chat service
        chat_service = ChatService()
        await chat_service.initialize()
        
        # Create test message with custom agent type
        test_message = ChatMessage(
            id="test-msg-1",
            content="Help me with my personal tasks",
            sender=MessageSender.USER,
            timestamp="2024-01-01T12:00:00Z",
            session_id="test-session-1",
            metadata={'agentType': 'personal'}
        )
        
        # Mock WebSocket for streaming
        mock_websocket = AsyncMock()
        chat_service.chat_sessions["ws-1"] = "test-session-1"
        chat_service.connection_manager.connections["ws-1"] = mock_websocket
        
        # Process message
        await chat_service.handle_user_message(test_message)
        
        # Verify custom agent was called
        mock_registry.get_agent.assert_called_once_with('personal')
        mock_registry.get_agent.return_value.stream_chat.assert_called_once()
        
        # Verify streaming messages were sent
        assert mock_websocket.send_text.call_count >= 3  # START, chunks, END
        
        # Verify message content in calls
        calls = [call.args[0] for call in mock_websocket.send_text.call_args_list]
        
        # Check stream start message
        start_msg = json.loads(calls[0])
        assert start_msg['type'] == 'message_stream'
        assert start_msg['agentType'] == 'personal'
        assert start_msg['agentId'] == 'personal'
        assert start_msg['agentName'] == 'Personal'
        assert start_msg['stream_start'] is True
        
        # Check stream chunks contain content
        chunk_msgs = [json.loads(call) for call in calls[1:-1]]  # Exclude start and end
        assert all(msg['stream_chunk'] is True for msg in chunk_msgs)
        assert any('personal agent' in msg.get('content', '').lower() for msg in chunk_msgs)
        
        # Check stream end message
        end_msg = json.loads(calls[-1])
        assert end_msg['stream_end'] is True


@pytest.mark.asyncio
async def test_openai_agent_fallback():
    """Test that chat service falls back to OpenAI for non-custom agent types"""
    
    with patch('icpy.services.chat_service.get_db_manager') as mock_db, \
         patch('icpy.services.chat_service.get_message_broker') as mock_broker, \
         patch('icpy.services.chat_service.get_connection_manager') as mock_conn, \
         patch('icpy.services.chat_service.AsyncOpenAI') as mock_openai:
        
        # Setup mocks
        mock_db.return_value = AsyncMock()
        mock_broker.return_value = AsyncMock()
        mock_conn.return_value = AsyncMock()
        
        # Mock OpenAI streaming
        mock_openai_client = AsyncMock()
        mock_openai.return_value = mock_openai_client
        
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = [
            AsyncMock(choices=[AsyncMock(delta=AsyncMock(content="Hello! I'm GPT."))]),
            AsyncMock(choices=[AsyncMock(delta=AsyncMock(content=" How can I help?"))]),
        ]
        mock_openai_client.chat.completions.create.return_value = mock_stream
        
        # Create chat service
        chat_service = ChatService()
        await chat_service.initialize()
        
        # Create test message with OpenAI agent type
        test_message = ChatMessage(
            id="test-msg-2",
            content="Help me with general questions",
            sender=MessageSender.USER,
            timestamp="2024-01-01T12:00:00Z",
            session_id="test-session-2",
            metadata={'agentType': 'openai'}
        )
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        chat_service.chat_sessions["ws-2"] = "test-session-2"
        chat_service.connection_manager.connections["ws-2"] = mock_websocket
        
        # Process message
        await chat_service.handle_user_message(test_message)
        
        # Verify OpenAI was called
        mock_openai_client.chat.completions.create.assert_called_once()
        
        # Verify streaming messages were sent
        assert mock_websocket.send_text.call_count >= 2  # At least START and chunks
        
        calls = [call.args[0] for call in mock_websocket.send_text.call_args_list]
        start_msg = json.loads(calls[0])
        assert start_msg['agentType'] == 'openai'


@pytest.mark.asyncio
async def test_agent_type_missing_fallback():
    """Test fallback when agentType is missing from metadata"""
    
    with patch('icpy.services.chat_service.get_db_manager') as mock_db, \
         patch('icpy.services.chat_service.get_message_broker') as mock_broker, \
         patch('icpy.services.chat_service.get_connection_manager') as mock_conn, \
         patch('icpy.services.chat_service.AsyncOpenAI') as mock_openai:
        
        # Setup mocks
        mock_db.return_value = AsyncMock()
        mock_broker.return_value = AsyncMock()
        mock_conn.return_value = AsyncMock()
        
        mock_openai_client = AsyncMock()
        mock_openai.return_value = mock_openai_client
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = [
            AsyncMock(choices=[AsyncMock(delta=AsyncMock(content="Default response"))]),
        ]
        mock_openai_client.chat.completions.create.return_value = mock_stream
        
        # Create chat service
        chat_service = ChatService()
        await chat_service.initialize()
        
        # Create test message without agentType
        test_message = ChatMessage(
            id="test-msg-3",
            content="General question",
            sender=MessageSender.USER,
            timestamp="2024-01-01T12:00:00Z",
            session_id="test-session-3",
            metadata={}  # No agentType
        )
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        chat_service.chat_sessions["ws-3"] = "test-session-3"
        chat_service.connection_manager.connections["ws-3"] = mock_websocket
        
        # Process message
        await chat_service.handle_user_message(test_message)
        
        # Should fall back to OpenAI
        mock_openai_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio  
async def test_custom_agent_error_handling():
    """Test error handling when custom agent fails"""
    
    # Mock registry with failing agent
    mock_registry = AsyncMock()
    mock_registry.get_agent.return_value = AsyncMock()
    mock_registry.get_agent.return_value.stream_chat.side_effect = Exception("Agent error")
    
    with patch('icpy.services.chat_service.get_db_manager') as mock_db, \
         patch('icpy.services.chat_service.get_message_broker') as mock_broker, \
         patch('icpy.services.chat_service.get_connection_manager') as mock_conn, \
         patch('icpy.agent.custom_agent.registry', mock_registry):
        
        # Setup mocks
        mock_db.return_value = AsyncMock()
        mock_broker.return_value = AsyncMock()
        mock_conn.return_value = AsyncMock()
        
        # Create chat service
        chat_service = ChatService()
        await chat_service.initialize()
        
        # Create test message
        test_message = ChatMessage(
            id="test-msg-4",
            content="This will fail",
            sender=MessageSender.USER,
            timestamp="2024-01-01T12:00:00Z",
            session_id="test-session-4",
            metadata={'agentType': 'failing'}
        )
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        chat_service.chat_sessions["ws-4"] = "test-session-4"
        chat_service.connection_manager.connections["ws-4"] = mock_websocket
        
        # Process message (should handle error gracefully)
        await chat_service.handle_user_message(test_message)
        
        # Should still send streaming response with error message
        assert mock_websocket.send_text.call_count >= 3  # START, error chunk, END
        
        calls = [call.args[0] for call in mock_websocket.send_text.call_args_list]
        chunk_contents = []
        for call in calls:
            msg = json.loads(call)
            if msg.get('stream_chunk'):
                chunk_contents.append(msg.get('content', ''))
        
        # Error message should be present
        error_content = ''.join(chunk_contents)
        assert 'error' in error_content.lower()


if __name__ == "__main__":
    print("🧪 Testing Unified Chat Service Custom Agent Integration (Step 6.5)")
    
    # Run tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
    
    print("✅ Custom agent integration tests completed!")
