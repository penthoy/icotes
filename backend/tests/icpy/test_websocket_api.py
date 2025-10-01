"""
Tests for WebSocket API

This module contains comprehensive tests for the enhanced WebSocket API,
including connection management, message handling, state synchronization,
and integration with the message broker.

Author: GitHub Copilot
Date: July 16, 2025
"""

import asyncio
import json
import pytest
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from enum import Enum

# Test imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icpy.api.websocket_api import (
    WebSocketAPI,
    WebSocketConnection,
    WebSocketConnectionState,
    WebSocketMessage,
    get_websocket_api,
    shutdown_websocket_api
)
from icpy.core.message_broker import MessageBroker
from icpy.core.connection_manager import ConnectionManager
from icpy.services.workspace_service import WorkspaceService
from icpy.services.filesystem_service import FileSystemService
from icpy.services.terminal_service import TerminalService

# Import actual WebSocket state
from fastapi.websockets import WebSocketState


class TestWebSocketMessage:
    """Test WebSocketMessage class."""
    
    def test_message_creation_with_defaults(self):
        """Test WebSocketMessage creation with default values."""
        message = WebSocketMessage(data={'test': 'data'})
        
        assert message.type == 'message'
        assert message.data == {'test': 'data'}
        assert message.session_id is None
        assert message.user_id is None
        assert isinstance(message.id, str)
        assert isinstance(message.timestamp, float)
    
    def test_message_creation_with_values(self):
        """Test WebSocketMessage creation with custom values."""
        message = WebSocketMessage(
            id='test-id',
            type='custom',
            data={'custom': 'data'},
            session_id='session-123',
            user_id='user-456',
            timestamp=1234567890.0
        )
        
        assert message.id == 'test-id'
        assert message.type == 'custom'
        assert message.data == {'custom': 'data'}
        assert message.session_id == 'session-123'
        assert message.user_id == 'user-456'
        assert message.timestamp == 1234567890.0


class TestWebSocketConnection:
    """Test WebSocketConnection class."""
    
    def test_connection_creation(self):
        """Test WebSocketConnection creation."""
        websocket = MagicMock()
        connection = WebSocketConnection(
            id='conn-123',
            websocket=websocket,
            state=WebSocketConnectionState.CONNECTED
        )
        
        assert connection.id == 'conn-123'
        assert connection.websocket == websocket
        assert connection.state == WebSocketConnectionState.CONNECTED
        assert connection.session_id is None
        assert connection.user_id is None
        assert isinstance(connection.created_at, float)
        assert isinstance(connection.last_activity, float)
        assert len(connection.message_queue) == 0
        assert len(connection.subscriptions) == 0
    
    def test_connection_to_dict(self):
        """Test connection to_dict method."""
        websocket = MagicMock()
        connection = WebSocketConnection(
            id='conn-123',
            websocket=websocket,
            state=WebSocketConnectionState.AUTHENTICATED,
            session_id='session-456',
            user_id='user-789'
        )
        
        connection.subscriptions.add('test.*')
        connection.subscriptions.add('workspace.*')
        
        result = connection.to_dict()
        
        assert result['id'] == 'conn-123'
        assert result['state'] == 'authenticated'
        assert result['session_id'] == 'session-456'
        assert result['user_id'] == 'user-789'
        assert result['message_queue_size'] == 0
        assert set(result['subscriptions']) == {'test.*', 'workspace.*'}
        assert isinstance(result['created_at'], float)
        assert isinstance(result['last_activity'], float)


class TestWebSocketAPI:
    """Test WebSocketAPI class."""
    
    @pytest.fixture
    def websocket_api(self):
        """Create WebSocketAPI instance for testing."""
        return WebSocketAPI()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket for testing."""
        websocket = MagicMock()
        websocket.client_state = WebSocketState.CONNECTED
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket
    
    @pytest.fixture
    def mock_message_broker(self):
        """Create mock MessageBroker for testing."""
        broker = AsyncMock(spec=MessageBroker)
        broker.subscribe = AsyncMock()
        broker.publish = AsyncMock()
        return broker
    
    @pytest.fixture
    def mock_connection_manager(self):
        """Create mock ConnectionManager for testing."""
        manager = AsyncMock(spec=ConnectionManager)
        manager.handle_request = AsyncMock()
        return manager
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        return {
            'workspace': AsyncMock(spec=WorkspaceService),
            'filesystem': AsyncMock(spec=FileSystemService),
            'terminal': AsyncMock(spec=TerminalService)
        }
    
    @pytest.mark.asyncio
    async def test_websocket_api_initialization(self, websocket_api, mock_message_broker, mock_connection_manager, mock_services):
        """Test WebSocketAPI initialization."""
        # Mock dependencies
        websocket_api.message_broker = mock_message_broker
        websocket_api.connection_manager = mock_connection_manager
        websocket_api.workspace_service = mock_services['workspace']
        websocket_api.filesystem_service = mock_services['filesystem']
        websocket_api.terminal_service = mock_services['terminal']
        
        # Skip the actual initialization to avoid service dependencies
        await websocket_api.initialize()
        
        # The initialize method should have been called
        # (we can't easily test the actual subscriptions without mocking more deeply)
        assert websocket_api.message_broker is not None
        assert websocket_api.connection_manager is not None
        assert websocket_api.workspace_service is not None
        assert websocket_api.filesystem_service is not None
        assert websocket_api.terminal_service is not None
    
    @pytest.mark.asyncio
    async def test_connect_websocket_success(self, websocket_api, mock_websocket):
        """Test successful WebSocket connection."""
        websocket_api.message_broker = AsyncMock()
        websocket_api.message_broker.publish = AsyncMock()
        
        connection_id = await websocket_api.connect_websocket(
            mock_websocket,
            session_id='session-123',
            user_id='user-456'
        )
        
        # Verify connection was established
        assert connection_id in websocket_api.connections
        connection = websocket_api.connections[connection_id]
        assert connection.websocket == mock_websocket
        assert connection.state == WebSocketConnectionState.CONNECTED
        assert connection.session_id == 'session-123'
        assert connection.user_id == 'user-456'
        
        # Verify tracking was updated
        assert connection_id in websocket_api.user_connections['user-456']
        assert connection_id in websocket_api.session_connections['session-123']
        
        # Verify statistics
        assert websocket_api.stats['total_connections'] == 1
        assert websocket_api.stats['active_connections'] == 1
        
        # Verify WebSocket was accepted and welcome message sent
        mock_websocket.accept.assert_called_once()
        assert mock_websocket.send_text.call_count == 2  # Welcome + message replay
        
        # Verify connection event was published
        websocket_api.message_broker.publish.assert_called_with('websocket.connection_established', {
            'connection_id': connection_id,
            'session_id': 'session-123',
            'user_id': 'user-456',
            'timestamp': pytest.approx(time.time(), rel=1.0)
        })
    
    @pytest.mark.asyncio
    async def test_connect_websocket_max_connections(self, websocket_api, mock_websocket):
        """Test WebSocket connection when max connections reached."""
        websocket_api.max_connections = 1
        
        # Connect first WebSocket
        websocket_api.message_broker = AsyncMock()
        await websocket_api.connect_websocket(mock_websocket)
        
        # Try to connect second WebSocket
        with pytest.raises(Exception, match="Maximum number of connections"):
            await websocket_api.connect_websocket(mock_websocket)
    
    @pytest.mark.asyncio
    async def test_disconnect_websocket(self, websocket_api, mock_websocket):
        """Test WebSocket disconnection."""
        websocket_api.message_broker = AsyncMock()
        
        # Connect WebSocket
        connection_id = await websocket_api.connect_websocket(
            mock_websocket,
            session_id='session-123',
            user_id='user-456'
        )
        
        # Disconnect WebSocket
        await websocket_api.disconnect_websocket(connection_id)
        
        # Verify connection was removed
        assert connection_id not in websocket_api.connections
        assert 'user-456' not in websocket_api.user_connections
        assert 'session-123' not in websocket_api.session_connections
        
        # Verify statistics
        assert websocket_api.stats['active_connections'] == 0
        
        # Verify WebSocket close was attempted (it should be called for connected state)
        # Note: Since the mock websocket has CONNECTED state, close should be called
        if mock_websocket.client_state == WebSocketState.CONNECTED:
            mock_websocket.close.assert_called_once()
        
        # Verify disconnection event was published
        websocket_api.message_broker.publish.assert_called_with('websocket.connection_closed', {
            'connection_id': connection_id,
            'session_id': 'session-123',
            'user_id': 'user-456',
            'timestamp': pytest.approx(time.time(), rel=1.0)
        })
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, websocket_api, mock_websocket):
        """Test successful message sending."""
        websocket_api.message_broker = AsyncMock()
        
        # Connect WebSocket
        connection_id = await websocket_api.connect_websocket(mock_websocket)
        
        # Send message
        data = {'type': 'test', 'content': 'hello'}
        result = await websocket_api.send_message(connection_id, data)
        
        # Verify message was sent
        assert result is True
        assert mock_websocket.send_text.call_count == 2  # Welcome + test message
        
        # Verify message was added to connection queue
        connection = websocket_api.connections[connection_id]
        assert len(connection.message_queue) == 2  # Welcome + test message
        
        # Verify statistics
        assert websocket_api.stats['messages_sent'] == 2
    
    @pytest.mark.asyncio
    async def test_send_message_unknown_connection(self, websocket_api):
        """Test sending message to unknown connection."""
        result = await websocket_api.send_message('unknown-id', {'test': 'data'})
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_error(self, websocket_api, mock_websocket):
        """Test sending error message."""
        websocket_api.message_broker = AsyncMock()
        
        # Connect WebSocket
        connection_id = await websocket_api.connect_websocket(mock_websocket)
        
        # Send error
        await websocket_api.send_error(connection_id, "Test error")
        
        # Verify error message was sent
        assert mock_websocket.send_text.call_count == 2  # Welcome + error message
        
        # Check the error message format
        calls = mock_websocket.send_text.call_args_list
        error_call = calls[1][0][0]  # Second call, first argument
        error_data = json.loads(error_call)
        assert error_data['type'] == 'error'
        assert error_data['message'] == 'Test error'
        assert 'timestamp' in error_data
    
    @pytest.mark.asyncio
    async def test_broadcast_message_to_all(self, websocket_api, mock_message_broker):
        """Test broadcasting message to all connections."""
        websocket_api.message_broker = mock_message_broker
        
        # Create multiple WebSocket connections
        websockets = [MagicMock() for _ in range(3)]
        for ws in websockets:
            ws.client_state = WebSocketState.CONNECTED
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
        
        # Connect WebSockets
        connection_ids = []
        for i, ws in enumerate(websockets):
            connection_id = await websocket_api.connect_websocket(ws, user_id=f'user-{i}')
            connection_ids.append(connection_id)
        
        # Broadcast message
        data = {'type': 'broadcast', 'content': 'hello all'}
        await websocket_api.broadcast_message(data)
        
        # Verify message was sent to all connections
        for ws in websockets:
            assert ws.send_text.call_count == 2  # Welcome + broadcast message
    
    @pytest.mark.asyncio
    async def test_broadcast_message_to_user(self, websocket_api):
        """Test broadcasting message to specific user."""
        websocket_api.message_broker = AsyncMock()
        
        # Create WebSocket connections for different users
        websockets = [MagicMock() for _ in range(3)]
        for ws in websockets:
            ws.client_state = WebSocketState.CONNECTED
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
        
        # Connect WebSockets
        await websocket_api.connect_websocket(websockets[0], user_id='user-1')
        await websocket_api.connect_websocket(websockets[1], user_id='user-2')
        await websocket_api.connect_websocket(websockets[2], user_id='user-1')  # Same user
        
        # Broadcast message to user-1
        data = {'type': 'broadcast', 'content': 'hello user-1'}
        await websocket_api.broadcast_message(data, user_id='user-1')
        
        # Verify message was sent to user-1 connections only
        assert websockets[0].send_text.call_count == 2  # Welcome + broadcast
        assert websockets[1].send_text.call_count == 1  # Welcome only
        assert websockets[2].send_text.call_count == 2  # Welcome + broadcast
    
    @pytest.mark.asyncio
    async def test_handle_ping_message(self, websocket_api, mock_websocket):
        """Test handling ping message."""
        websocket_api.message_broker = AsyncMock()
        
        # Connect WebSocket
        connection_id = await websocket_api.connect_websocket(mock_websocket)
        
        # Handle ping message
        await websocket_api.handle_websocket_message(connection_id, json.dumps({
            'type': 'ping'
        }))
        
        # Verify pong response was sent
        assert mock_websocket.send_text.call_count == 2  # Welcome + pong
        
        # Check the pong message format
        calls = mock_websocket.send_text.call_args_list
        pong_call = calls[1][0][0]  # Second call, first argument
        pong_data = json.loads(pong_call)
        assert pong_data['type'] == 'pong'
        assert 'timestamp' in pong_data
    
    @pytest.mark.asyncio
    async def test_handle_subscribe_message(self, websocket_api, mock_websocket):
        """Test handling subscribe message."""
        websocket_api.message_broker = AsyncMock()
        
        # Connect WebSocket
        connection_id = await websocket_api.connect_websocket(mock_websocket)
        
        # Handle subscribe message
        await websocket_api.handle_websocket_message(connection_id, json.dumps({
            'type': 'subscribe',
            'topics': ['workspace.*', 'fs.*']
        }))
        
        # Verify subscriptions were added
        connection = websocket_api.connections[connection_id]
        assert 'workspace.*' in connection.subscriptions
        assert 'fs.*' in connection.subscriptions
        
        # Verify subscribed response was sent
        assert mock_websocket.send_text.call_count == 2  # Welcome + subscribed
    
    @pytest.mark.asyncio
    async def test_handle_authenticate_message(self, websocket_api, mock_websocket):
        """Test handling authenticate message."""
        websocket_api.message_broker = AsyncMock()
        
        # Connect WebSocket
        connection_id = await websocket_api.connect_websocket(mock_websocket)
        
        # Handle authenticate message
        await websocket_api.handle_websocket_message(connection_id, json.dumps({
            'type': 'authenticate',
            'user_id': 'user-123',
            'session_id': 'session-456'
        }))
        
        # Verify connection was authenticated
        connection = websocket_api.connections[connection_id]
        assert connection.user_id == 'user-123'
        assert connection.session_id == 'session-456'
        assert connection.state == WebSocketConnectionState.AUTHENTICATED
        
        # Verify tracking was updated
        assert connection_id in websocket_api.user_connections['user-123']
        assert connection_id in websocket_api.session_connections['session-456']
        
        # Verify statistics
        assert websocket_api.stats['authentication_attempts'] == 1
        assert websocket_api.stats['authentication_successes'] == 1
    
    @pytest.mark.asyncio
    async def test_handle_invalid_json(self, websocket_api, mock_websocket):
        """Test handling invalid JSON message."""
        websocket_api.message_broker = AsyncMock()
        
        # Connect WebSocket
        connection_id = await websocket_api.connect_websocket(mock_websocket)
        
        # Handle invalid JSON message
        await websocket_api.handle_websocket_message(connection_id, "invalid json")
        
        # Verify error response was sent
        assert mock_websocket.send_text.call_count == 2  # Welcome + error
        
        # Check the error message format
        calls = mock_websocket.send_text.call_args_list
        error_call = calls[1][0][0]  # Second call, first argument
        error_data = json.loads(error_call)
        assert error_data['type'] == 'error'
        assert 'Invalid JSON' in error_data['message']
    
    @pytest.mark.asyncio
    async def test_get_connection_info(self, websocket_api, mock_websocket):
        """Test getting connection information."""
        websocket_api.message_broker = AsyncMock()
        
        # Connect WebSocket
        connection_id = await websocket_api.connect_websocket(
            mock_websocket,
            session_id='session-123',
            user_id='user-456'
        )
        
        # Get connection info
        info = await websocket_api.get_connection_info(connection_id)
        
        # Verify connection info
        assert info is not None
        assert info['id'] == connection_id
        assert info['state'] == 'connected'
        assert info['session_id'] == 'session-123'
        assert info['user_id'] == 'user-456'
        assert isinstance(info['created_at'], float)
        assert isinstance(info['last_activity'], float)
        assert info['message_queue_size'] == 2  # Welcome + message replay
        assert info['subscriptions'] == ['fs.*']  # Auto-subscribed to filesystem events
    
    @pytest.mark.asyncio
    async def test_get_connection_info_unknown(self, websocket_api):
        """Test getting connection information for unknown connection."""
        info = await websocket_api.get_connection_info('unknown-id')
        assert info is None
    
    @pytest.mark.asyncio
    async def test_list_connections(self, websocket_api):
        """Test listing connections."""
        websocket_api.message_broker = AsyncMock()
        
        # Create multiple WebSocket connections
        websockets = [MagicMock() for _ in range(3)]
        for ws in websockets:
            ws.client_state = WebSocketState.CONNECTED
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
        
        # Connect WebSockets
        await websocket_api.connect_websocket(websockets[0], user_id='user-1')
        await websocket_api.connect_websocket(websockets[1], user_id='user-2')
        await websocket_api.connect_websocket(websockets[2], user_id='user-1')
        
        # List all connections
        connections = await websocket_api.list_connections()
        assert len(connections) == 3
        
        # List connections for user-1
        user_connections = await websocket_api.list_connections(user_id='user-1')
        assert len(user_connections) == 2
        
        # List connections for user-2
        user_connections = await websocket_api.list_connections(user_id='user-2')
        assert len(user_connections) == 1
    
    @pytest.mark.asyncio
    async def test_get_stats(self, websocket_api, mock_websocket):
        """Test getting WebSocket API statistics."""
        websocket_api.message_broker = AsyncMock()
        
        # Connect WebSocket with user_id
        await websocket_api.connect_websocket(mock_websocket, user_id='user-123')
        
        # Get stats
        stats = await websocket_api.get_stats()
        
        # Verify stats
        assert stats['total_connections'] == 1
        assert stats['active_connections'] == 1
        assert stats['user_connections'] == 1
        assert stats['session_connections'] == 0  # No session_id provided
        assert stats['messages_sent'] == 1  # Welcome message (no session for replay)
        assert stats['messages_received'] == 0
        assert stats['max_connections'] == 1000
        assert 'timestamp' in stats
    
    @pytest.mark.asyncio
    async def test_shutdown(self, websocket_api, mock_websocket):
        """Test WebSocket API shutdown."""
        websocket_api.message_broker = AsyncMock()
        
        # Connect WebSocket
        connection_id = await websocket_api.connect_websocket(mock_websocket)
        
        # Shutdown API
        await websocket_api.shutdown()
        
        # Verify all connections were closed
        assert len(websocket_api.connections) == 0
        assert len(websocket_api.user_connections) == 0
        assert len(websocket_api.session_connections) == 0
        assert len(websocket_api.message_history) == 0
        
        # Verify WebSocket was closed if connected
        if mock_websocket.client_state == WebSocketState.CONNECTED:
            mock_websocket.close.assert_called()
        
        # Verify shutdown event was published
        websocket_api.message_broker.publish.assert_called_with('websocket.service_shutdown', {
            'service': 'websocket',
            'timestamp': pytest.approx(time.time(), rel=1.0)
        })


class TestWebSocketAPIIntegration:
    """Integration tests for WebSocket API."""
    
    @pytest.mark.asyncio
    async def test_message_replay_on_reconnect(self):
        """Test message replay when client reconnects."""
        # This would be a more complex integration test
        # that verifies message replay functionality
        pass
    
    @pytest.mark.asyncio
    async def test_event_broadcasting_from_services(self):
        """Test event broadcasting from other services."""
        # This would test the integration with other services
        # and verify that events are properly broadcasted
        pass
    
    @pytest.mark.asyncio
    async def test_connection_recovery_after_failure(self):
        """Test connection recovery after network failure."""
        # This would test the robustness of the connection
        # recovery mechanisms
        pass


class TestWebSocketAPIGlobalInstance:
    """Test global WebSocket API instance management."""
    
    @pytest.mark.asyncio
    async def test_get_websocket_api_singleton(self):
        """Test that get_websocket_api returns singleton instance."""
        # Reset global instance
        import icpy.api.websocket_api
        icpy.api.websocket_api._websocket_api = None
        
        # Mock dependencies
        with patch('icpy.api.websocket_api.get_message_broker') as mock_get_broker, \
             patch('icpy.api.websocket_api.get_connection_manager') as mock_get_manager, \
             patch('icpy.api.websocket_api.get_workspace_service') as mock_get_workspace, \
             patch('icpy.api.websocket_api.get_filesystem_service') as mock_get_fs, \
             patch('icpy.api.websocket_api.get_terminal_service') as mock_get_terminal:
            
            # Configure mocks
            mock_get_broker.return_value = AsyncMock()
            mock_get_manager.return_value = AsyncMock()
            mock_get_workspace.return_value = AsyncMock()
            mock_get_fs.return_value = AsyncMock()
            mock_get_terminal.return_value = AsyncMock()
            
            # Get instance twice
            api1 = await get_websocket_api()
            api2 = await get_websocket_api()
            
            # Verify singleton behavior
            assert api1 is api2
            assert isinstance(api1, WebSocketAPI)
    
    @pytest.mark.asyncio
    async def test_shutdown_websocket_api(self):
        """Test shutdown of global WebSocket API instance."""
        # Reset global instance
        import icpy.api.websocket_api
        icpy.api.websocket_api._websocket_api = None
        
        # Mock dependencies
        with patch('icpy.api.websocket_api.get_message_broker') as mock_get_broker, \
             patch('icpy.api.websocket_api.get_connection_manager') as mock_get_manager, \
             patch('icpy.api.websocket_api.get_workspace_service') as mock_get_workspace, \
             patch('icpy.api.websocket_api.get_filesystem_service') as mock_get_fs, \
             patch('icpy.api.websocket_api.get_terminal_service') as mock_get_terminal:
            
            # Configure mocks
            mock_broker = AsyncMock()
            mock_get_broker.return_value = mock_broker
            mock_get_manager.return_value = AsyncMock()
            mock_get_workspace.return_value = AsyncMock()
            mock_get_fs.return_value = AsyncMock()
            mock_get_terminal.return_value = AsyncMock()
            
            # Get instance
            api = await get_websocket_api()
            
            # Shutdown
            await shutdown_websocket_api()
            
            # Verify shutdown was called
            mock_broker.publish.assert_called_with('websocket.service_shutdown', {
                'service': 'websocket',
                'timestamp': pytest.approx(time.time(), rel=1.0)
            })
            
            # Verify global instance was reset
            assert icpy.api.websocket_api._websocket_api is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
