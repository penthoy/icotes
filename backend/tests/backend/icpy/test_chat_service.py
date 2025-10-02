"""
Test Chat Service Implementation
Tests WebSocket communication, message persistence, agent integration, and error handling
"""

import asyncio
import json
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

# Import the chat service
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from icpy.services.chat_service import (
    ChatService, ChatMessage, MessageSender, ChatMessageType, AgentStatus, ChatConfig,
    get_chat_service, shutdown_chat_service
)


@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_workspaces():
    """Clean up any remaining temporary workspace directories after all tests"""
    yield
    # Cleanup after all tests in this module
    try:
        workspace_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', '..', 'workspace')
        if os.path.exists(workspace_root):
            import glob
            import shutil
            temp_dirs = glob.glob(os.path.join(workspace_root, '.icotes_tmp*'))
            for temp_dir in temp_dirs:
                try:
                    shutil.rmtree(temp_dir)
                    print(f"Cleaned up temporary workspace: {temp_dir}")
                except Exception as e:
                    print(f"Warning: Failed to clean up {temp_dir}: {e}")
    except Exception as e:
        print(f"Warning: Error during workspace cleanup: {e}")


@pytest.fixture
async def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def mock_message_broker():
    """Mock message broker"""
    broker = Mock()
    broker.subscribe = AsyncMock()
    broker.publish = AsyncMock()
    return broker


@pytest.fixture
def mock_connection_manager():
    """Mock connection manager"""
    manager = Mock()
    manager.send_to_connection = AsyncMock()
    return manager


@pytest.fixture
def mock_agent_service():
    """Mock agent service"""
    service = Mock()
    service.list_agent_sessions = Mock(return_value=[])
    service.execute_agent_task = AsyncMock(return_value={'success': True, 'result': 'Test response'})
    return service


@pytest.fixture
async def chat_service(mock_message_broker, mock_connection_manager):
    """Create a chat service for testing"""
    with patch('icpy.services.chat_service.get_message_broker', return_value=mock_message_broker), \
         patch('icpy.services.chat_service.get_connection_manager', return_value=mock_connection_manager):
        
        service = ChatService()
        yield service
        # Cleanup after test
        await service.cleanup()


class TestChatMessage:
    """Test ChatMessage functionality"""
    
    def test_chat_message_creation(self):
        """Test creating a chat message"""
        message = ChatMessage(
            id="test-id",
            content="Hello world",
            sender=MessageSender.USER,
            timestamp="2025-01-01T00:00:00Z"
        )
        
        assert message.id == "test-id"
        assert message.content == "Hello world"
        assert message.sender == MessageSender.USER
        assert message.timestamp == "2025-01-01T00:00:00Z"
        assert message.type == ChatMessageType.MESSAGE
    
    def test_chat_message_to_dict(self):
        """Test converting chat message to dictionary"""
        message = ChatMessage(
            id="test-id",
            content="Hello world",
            sender=MessageSender.AI,
            timestamp="2025-01-01T00:00:00Z",
            agent_id="agent-123"
        )
        
        data = message.to_dict()
        assert data['id'] == "test-id"
        assert data['content'] == "Hello world"
        assert data['sender'] == "ai"
        assert data['agent_id'] == "agent-123"
    
    def test_chat_message_from_dict(self):
        """Test creating chat message from dictionary"""
        data = {
            'id': "test-id",
            'content': "Hello world",
            'sender': "user",
            'timestamp': "2025-01-01T00:00:00Z",
            'type': "message",
            'metadata': {'key': 'value'},
            'agent_id': None,
            'session_id': "session-123"
        }
        
        message = ChatMessage.from_dict(data)
        assert message.id == "test-id"
        assert message.sender == MessageSender.USER
        assert message.metadata == {'key': 'value'}
        assert message.session_id == "session-123"


class TestAgentStatus:
    """Test AgentStatus functionality"""
    
    def test_agent_status_creation(self):
        """Test creating agent status"""
        status = AgentStatus(
            available=True,
            name="Test Agent",
            type="openai",
            capabilities=["chat", "code"],
            agent_id="agent-123"
        )
        
        assert status.available is True
        assert status.name == "Test Agent"
        assert status.type == "openai"
        assert status.capabilities == ["chat", "code"]
        assert status.agent_id == "agent-123"
    
    def test_agent_status_to_dict(self):
        """Test converting agent status to dictionary"""
        status = AgentStatus(
            available=False,
            name="Unavailable Agent",
            type="crewai",
            capabilities=[]
        )
        
        data = status.to_dict()
        assert data['available'] is False
        assert data['name'] == "Unavailable Agent"
        assert data['type'] == "crewai"
        assert data['capabilities'] == []


class TestChatConfig:
    """Test ChatConfig functionality"""
    
    def test_chat_config_defaults(self):
        """Test default chat configuration"""
        config = ChatConfig()
        
        assert config.agent_id is None
        assert config.agent_name == "Assistant"
        assert config.system_prompt == "You are a helpful AI assistant."
        assert config.max_messages == 1000
        assert config.auto_scroll is True
        assert config.enable_typing_indicators is True
        assert config.message_retention_days == 30
    
    def test_chat_config_custom(self):
        """Test custom chat configuration"""
        config = ChatConfig(
            agent_id="custom-agent",
            agent_name="Custom Assistant",
            system_prompt="Custom prompt",
            max_messages=500,
            auto_scroll=False
        )
        
        assert config.agent_id == "custom-agent"
        assert config.agent_name == "Custom Assistant"
        assert config.system_prompt == "Custom prompt"
        assert config.max_messages == 500
        assert config.auto_scroll is False
    
    def test_chat_config_to_dict(self):
        """Test converting chat config to dictionary"""
        config = ChatConfig(agent_id="test-agent")
        data = config.to_dict()
        
        assert isinstance(data, dict)
        assert data['agent_id'] == "test-agent"
        assert data['agent_name'] == "Assistant"


class TestChatService:
    """Test ChatService functionality"""
    
    @pytest.mark.asyncio
    async def test_chat_service_initialization(self, chat_service):
        """Test chat service initialization"""
        assert chat_service.chat_sessions == {}
        assert chat_service.active_connections == set()
        assert isinstance(chat_service.config, ChatConfig)
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, chat_service):
        """Test WebSocket connection management"""
        websocket_id = "ws-123"
        
        # Connect
        session_id = await chat_service.connect_websocket(websocket_id)
        assert websocket_id in chat_service.chat_sessions
        assert chat_service.chat_sessions[websocket_id] == session_id
        assert websocket_id in chat_service.active_connections
        
        # Disconnect
        await chat_service.disconnect_websocket(websocket_id)
        assert websocket_id not in chat_service.chat_sessions
        assert websocket_id not in chat_service.active_connections
    
    @pytest.mark.asyncio
    async def test_handle_user_message(self, chat_service):
        """Test handling user messages"""
        websocket_id = "ws-123"
        session_id = await chat_service.connect_websocket(websocket_id)
        
        with patch.object(chat_service, '_store_message', new=AsyncMock()) as mock_store, \
             patch.object(chat_service, '_process_with_agent', new=AsyncMock()) as mock_process:
            
            message = await chat_service.handle_user_message(websocket_id, "Hello!")
            
            assert message.content == "Hello!"
            assert message.sender == MessageSender.USER
            assert message.session_id == session_id
            
            mock_store.assert_called_once()
            # User messages should NOT be broadcast back - clients already have them
            mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_message_persistence(self, chat_service):
        """Test message storage and retrieval"""
        # Create and store a message
        message = ChatMessage(
            id="test-msg-1",
            content="Test message",
            sender=MessageSender.USER,
            timestamp="2025-01-01T00:00:00Z",
            session_id="session-123"
        )
        
        await chat_service._store_message(message)
        
        # Retrieve messages
        messages = await chat_service.get_message_history("session-123", limit=10)
        assert len(messages) == 1
        assert messages[0].content == "Test message"
        assert messages[0].sender == MessageSender.USER
    
    @pytest.mark.asyncio
    async def test_message_history_pagination(self, chat_service):
        """Test message history with pagination"""
        session_id = "session-123"
        
        # Store multiple messages
        for i in range(5):
            message = ChatMessage(
                id=f"msg-{i}",
                content=f"Message {i}",
                sender=MessageSender.USER,
                timestamp=f"2025-01-01T00:0{i}:00Z",
                session_id=session_id
            )
            await chat_service._store_message(message)
        
        # Test pagination
        messages = await chat_service.get_message_history(session_id, limit=3, offset=0)
        assert len(messages) == 3
        assert messages[0].content == "Message 0"  # Chronological order
        
        messages = await chat_service.get_message_history(session_id, limit=3, offset=3)
        assert len(messages) == 2
        assert messages[0].content == "Message 3"
    
    @pytest.mark.asyncio
    async def test_clear_message_history(self, chat_service):
        """Test clearing message history"""
        session_id = "session-123"
        
        # Store a message
        message = ChatMessage(
            id="test-msg",
            content="Test message",
            sender=MessageSender.USER,
            timestamp="2025-01-01T00:00:00Z",
            session_id=session_id
        )
        await chat_service._store_message(message)
        
        # Verify message exists
        messages = await chat_service.get_message_history(session_id)
        assert len(messages) == 1
        
        # Clear messages
        success = await chat_service.clear_message_history(session_id)
        assert success is True
        
        # Verify messages cleared
        messages = await chat_service.get_message_history(session_id)
        assert len(messages) == 0
    
    @pytest.mark.asyncio
    async def test_agent_status_no_agent(self, chat_service):
        """Test getting agent status when no agent is configured"""
        status = await chat_service.get_agent_status()
        
        assert status.available is False
        assert status.name == "No Agent Configured"
        assert status.type == "none"
        assert status.capabilities == []
    
    @pytest.mark.asyncio
    async def test_agent_status_with_agent(self, chat_service, mock_agent_service):
        """Test getting agent status with configured agent"""
        # Configure agent
        chat_service.config.agent_id = "test-agent"
        
        # Mock agent session
        mock_session = Mock()
        mock_session.agent_id = "test-agent"
        mock_session.agent_name = "Test Agent"
        mock_session.framework = "openai"
        mock_session.capabilities = ["chat"]
        mock_session.status.value = "ready"
        
        with patch.object(chat_service, 'agent_service', mock_agent_service):
            mock_agent_service.list_agent_sessions.return_value = [mock_session]
            
            status = await chat_service.get_agent_status()
            
            assert status.available is True
            assert status.name == "Test Agent"
            assert status.type == "openai"
            assert status.capabilities == ["chat"]
            assert status.agent_id == "test-agent"
    
    @pytest.mark.asyncio
    async def test_config_update(self, chat_service):
        """Test updating chat configuration"""
        original_agent_name = chat_service.config.agent_name
        
        with patch.object(chat_service, '_broadcast_config_update', new=AsyncMock()) as mock_broadcast:
            await chat_service.update_config({
                'agent_name': 'Updated Assistant',
                'max_messages': 2000
            })
            
            assert chat_service.config.agent_name == 'Updated Assistant'
            assert chat_service.config.max_messages == 2000
            mock_broadcast.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_chat_service_stats(self, chat_service):
        """Test getting chat service statistics"""
        # Connect some websockets
        await chat_service.connect_websocket("ws-1")
        await chat_service.connect_websocket("ws-2")
        
        stats = chat_service.get_stats()
        
        assert stats['active_connections'] == 2
        assert stats['chat_sessions'] == 2
        assert stats['agent_configured'] is False  # No agent configured in test
        assert 'config' in stats
    
    @pytest.mark.asyncio
    async def test_typing_indicator(self, chat_service):
        """Test sending typing indicators"""
        websocket_id = "ws-123"
        session_id = await chat_service.connect_websocket(websocket_id)
        
        with patch.object(chat_service.connection_manager, 'send_to_connection', new=AsyncMock()) as mock_send:
            await chat_service._send_typing_indicator(session_id, True)
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] == websocket_id  # websocket_id
            
            # Parse the message
            message_data = json.loads(call_args[0][1])
            assert message_data['type'] == 'typing'
            assert message_data['is_typing'] is True


class TestChatServiceIntegration:
    """Test chat service integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_full_chat_flow(self, chat_service, mock_agent_service):
        """Test complete chat flow from user message to AI response"""
        websocket_id = "ws-123"
        session_id = await chat_service.connect_websocket(websocket_id)
        
        # Configure agent
        chat_service.config.agent_id = "test-agent"
        
        # Mock agent session
        mock_session = Mock()
        mock_session.agent_id = "test-agent"
        mock_session.status.value = "ready"
        
        with patch.object(chat_service, 'agent_service', mock_agent_service), \
             patch.object(chat_service, '_store_message', new=AsyncMock()), \
             patch.object(chat_service, '_broadcast_message', new=AsyncMock()), \
             patch.object(chat_service, '_send_typing_indicator', new=AsyncMock()) as mock_typing, \
             patch.object(chat_service, '_send_ai_response', new=AsyncMock()) as mock_ai_response:
            
            mock_agent_service.list_agent_sessions.return_value = [mock_session]
            
            # Send user message
            await chat_service.handle_user_message(websocket_id, "Hello, AI!")
            
            # Verify typing indicators were sent
            assert mock_typing.call_count == 2  # Start and stop typing
            
            # Verify AI response was sent
            mock_ai_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_no_websocket(self, chat_service):
        """Test error handling when WebSocket is not connected"""
        with pytest.raises(ValueError, match="WebSocket not connected"):
            await chat_service.handle_user_message("invalid-ws", "Hello!")
    
    @pytest.mark.asyncio
    async def test_agent_error_handling(self, chat_service, mock_agent_service):
        """Test error handling when agent fails"""
        websocket_id = "ws-123"
        session_id = await chat_service.connect_websocket(websocket_id)
        
        # Configure agent
        chat_service.config.agent_id = "test-agent"
        
        with patch.object(chat_service, 'agent_service', mock_agent_service), \
             patch.object(chat_service, '_store_message', new=AsyncMock()), \
             patch.object(chat_service, '_broadcast_message', new=AsyncMock()), \
             patch.object(chat_service, '_send_typing_indicator', new=AsyncMock()), \
             patch.object(chat_service, '_send_ai_response', new=AsyncMock()) as mock_ai_response:
            
            # Mock agent service to raise exception
            mock_agent_service.list_agent_sessions.side_effect = Exception("Agent error")
            
            # Send user message (should not raise exception)
            await chat_service.handle_user_message(websocket_id, "Hello!")
            
            # Verify error response was sent
            mock_ai_response.assert_called_once()
            args = mock_ai_response.call_args[0]
            assert "error" in args[1].lower()


class TestChatServiceGlobal:
    """Test global chat service functions"""
    
    def test_get_chat_service_singleton(self):
        """Test that get_chat_service returns singleton"""
        with patch('icpy.services.chat_service.get_message_broker', return_value=Mock()), \
             patch('icpy.services.chat_service.get_connection_manager', return_value=Mock()):
            
            service1 = get_chat_service()
            service2 = get_chat_service()
            
            assert service1 is service2
    
    @pytest.mark.asyncio
    async def test_shutdown_chat_service(self):
        """Test chat service shutdown"""
        with patch('icpy.services.chat_service.get_message_broker', return_value=Mock()), \
             patch('icpy.services.chat_service.get_connection_manager', return_value=Mock()):
            
            # Get service to initialize global instance
            service = get_chat_service()
            assert service is not None
            
            # Shutdown service
            await shutdown_chat_service()
            
            # Get new service (should be new instance)
            new_service = get_chat_service()
            assert new_service is not service


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
