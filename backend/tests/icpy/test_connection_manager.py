"""
Integration tests for Connection Manager
Tests connection lifecycle, authentication, health monitoring, and event hooks
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any, List
import uuid

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icpy.core.connection_manager import (
    ConnectionManager, Connection, ConnectionType, ConnectionState,
    get_connection_manager, shutdown_connection_manager
)
from icpy.core.message_broker import MessageBroker, get_message_broker


class TestConnectionManager:
    """Test suite for ConnectionManager"""
    
    @pytest.fixture
    async def connection_manager(self):
        """Create a fresh connection manager for each test"""
        # Reset global instance
        global _connection_manager
        _connection_manager = None
        
        manager = await get_connection_manager()
        yield manager
        
        # Cleanup
        await shutdown_connection_manager()
    
    @pytest.fixture
    async def mock_websocket(self):
        """Create mock WebSocket"""
        websocket = Mock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket
    
    @pytest.fixture
    async def mock_message_broker(self):
        """Create mock message broker"""
        broker = Mock()
        broker.publish = AsyncMock()
        broker.subscribe = AsyncMock()
        broker.get_stats = AsyncMock(return_value={})
        return broker
    
    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle(self, connection_manager, mock_websocket):
        """Test WebSocket connection lifecycle"""
        # Connect
        connection_id = await connection_manager.connect_websocket(mock_websocket)
        assert connection_id is not None
        
        # Verify connection exists
        connection = connection_manager.get_connection(connection_id)
        assert connection is not None
        assert connection.connection_type == ConnectionType.WEBSOCKET
        assert connection.state == ConnectionState.CONNECTED
        assert connection.websocket == mock_websocket
        
        # Update activity
        initial_activity = connection.last_activity
        await asyncio.sleep(0.01)  # Small delay
        await connection_manager.update_activity(connection_id)
        assert connection.last_activity > initial_activity
        
        # Disconnect
        await connection_manager.disconnect(connection_id, "Test disconnect")
        assert connection_manager.get_connection(connection_id) is None
    
    @pytest.mark.asyncio
    async def test_http_connection_lifecycle(self, connection_manager):
        """Test HTTP connection lifecycle"""
        # Connect
        connection_id = await connection_manager.connect_http(
            remote_addr="127.0.0.1",
            user_agent="Test Agent"
        )
        assert connection_id is not None
        
        # Verify connection
        connection = connection_manager.get_connection(connection_id)
        assert connection is not None
        assert connection.connection_type == ConnectionType.HTTP
        assert connection.state == ConnectionState.CONNECTED
        assert connection.metadata.get('remote_addr') == "127.0.0.1"
        assert connection.metadata.get('user_agent') == "Test Agent"
        
        # Disconnect
        await connection_manager.disconnect(connection_id, "Test disconnect")
        assert connection_manager.get_connection(connection_id) is None
    
    @pytest.mark.asyncio
    async def test_cli_connection_lifecycle(self, connection_manager):
        """Test CLI connection lifecycle"""
        # Connect
        connection_id = await connection_manager.connect_cli(
            process_id="12345",
            command="test-command"
        )
        assert connection_id is not None
        
        # Verify connection
        connection = connection_manager.get_connection(connection_id)
        assert connection is not None
        assert connection.connection_type == ConnectionType.CLI
        assert connection.state == ConnectionState.CONNECTED
        assert connection.metadata.get('process_id') == "12345"
        assert connection.metadata.get('command') == "test-command"
        
        # Disconnect
        await connection_manager.disconnect(connection_id, "Test disconnect")
        assert connection_manager.get_connection(connection_id) is None
    
    @pytest.mark.asyncio
    async def test_session_management(self, connection_manager, mock_websocket):
        """Test session management"""
        # Create session
        session_id = await connection_manager.create_session(
            user_id="user123",
            session_data={"theme": "dark"}
        )
        assert session_id is not None
        
        # Verify session
        session = connection_manager.get_session(session_id)
        assert session is not None
        assert session.user_id == "user123"
        assert session.session_data == {"theme": "dark"}
        
        # Connect with session
        connection_id = await connection_manager.connect_websocket(
            mock_websocket, session_id=session_id
        )
        
        connection = connection_manager.get_connection(connection_id)
        assert connection.session_id == session_id
        
        # Update session
        await connection_manager.update_session(
            session_id, {"theme": "light", "language": "en"}
        )
        
        updated_session = connection_manager.get_session(session_id)
        assert updated_session.session_data == {"theme": "light", "language": "en"}
        
        # Cleanup
        await connection_manager.disconnect(connection_id, "Test complete")
        await connection_manager.end_session(session_id)
        assert connection_manager.get_session(session_id) is None
    
    @pytest.mark.asyncio
    async def test_user_management(self, connection_manager, mock_websocket):
        """Test user management"""
        # Register user
        user_id = await connection_manager.register_user(
            "testuser", {"email": "test@example.com"}
        )
        assert user_id is not None
        
        # Verify user
        user = connection_manager.get_user(user_id)
        assert user is not None
        assert user.username == "testuser"
        assert user.user_data == {"email": "test@example.com"}
        
        # Connect with user
        connection_id = await connection_manager.connect_websocket(
            mock_websocket, user_id=user_id
        )
        
        connection = connection_manager.get_connection(connection_id)
        assert connection.user_id == user_id
        
        # Update user
        await connection_manager.update_user(
            user_id, {"email": "updated@example.com", "verified": True}
        )
        
        updated_user = connection_manager.get_user(user_id)
        assert updated_user.user_data == {"email": "updated@example.com", "verified": True}
        
        # Cleanup
        await connection_manager.disconnect(connection_id, "Test complete")
        await connection_manager.unregister_user(user_id)
        assert connection_manager.get_user(user_id) is None
    
    @pytest.mark.asyncio
    async def test_authentication(self, connection_manager, mock_websocket):
        """Test authentication"""
        # Connect
        connection_id = await connection_manager.connect_websocket(mock_websocket)
        connection = connection_manager.get_connection(connection_id)
        assert not connection.authenticated
        
        # Authenticate
        success = await connection_manager.authenticate(
            connection_id, "test-token", "bearer"
        )
        assert success
        
        # Verify authentication
        connection = connection_manager.get_connection(connection_id)
        assert connection.authenticated
        assert connection.auth_token == "test-token"
        assert connection.auth_method == "bearer"
        
        # Cleanup
        await connection_manager.disconnect(connection_id, "Test complete")
    
    @pytest.mark.asyncio
    async def test_health_monitoring(self, connection_manager, mock_websocket):
        """Test health monitoring"""
        # Connect
        connection_id = await connection_manager.connect_websocket(mock_websocket)
        
        # Get health status
        health = await connection_manager.get_health_status()
        assert health is not None
        assert health['status'] == 'healthy'
        assert health['connections']['total'] == 1
        assert health['connections']['websocket'] == 1
        
        # Simulate unhealthy connection
        connection = connection_manager.get_connection(connection_id)
        connection.last_activity = time.time() - 3600  # 1 hour ago
        
        # Should still be healthy (no timeout configured)
        health = await connection_manager.get_health_status()
        assert health['status'] == 'healthy'
        
        # Cleanup
        await connection_manager.disconnect(connection_id, "Test complete")
    
    @pytest.mark.asyncio
    async def test_event_hooks(self, connection_manager, mock_websocket):
        """Test event hooks"""
        # Create event handlers
        connect_handler = AsyncMock()
        disconnect_handler = AsyncMock()
        auth_handler = AsyncMock()
        
        # Register hooks
        connection_manager.register_hook('connection_created', connect_handler)
        connection_manager.register_hook('connection_removed', disconnect_handler)
        connection_manager.register_hook('connection_authenticated', auth_handler)
        
        # Connect
        connection_id = await connection_manager.connect_websocket(mock_websocket)
        
        # Verify connect hook called
        connect_handler.assert_called_once()
        args = connect_handler.call_args[0]
        assert args[0] == connection_id
        
        # Authenticate
        await connection_manager.authenticate(connection_id, "test-token")
        
        # Verify auth hook called
        auth_handler.assert_called_once()
        args = auth_handler.call_args[0]
        assert args[0] == connection_id
        
        # Disconnect
        await connection_manager.disconnect(connection_id, "Test complete")
        
        # Verify disconnect hook called
        disconnect_handler.assert_called_once()
        args = disconnect_handler.call_args[0]
        assert args[0] == connection_id
    
    @pytest.mark.asyncio
    async def test_message_sending(self, connection_manager, mock_websocket):
        """Test message sending"""
        # Connect
        connection_id = await connection_manager.connect_websocket(mock_websocket)
        
        # Send message
        success = await connection_manager.send_message(connection_id, "test message")
        assert success
        
        # Verify WebSocket send was called
        mock_websocket.send_text.assert_called_once_with("test message")
        
        # Try sending to non-existent connection
        success = await connection_manager.send_message("invalid", "test")
        assert not success
        
        # Cleanup
        await connection_manager.disconnect(connection_id, "Test complete")
    
    @pytest.mark.asyncio
    async def test_message_broadcasting(self, connection_manager):
        """Test message broadcasting"""
        # Create multiple connections
        ws1 = Mock()
        ws1.send_text = AsyncMock()
        ws2 = Mock()
        ws2.send_text = AsyncMock()
        
        connection_id1 = await connection_manager.connect_websocket(ws1)
        connection_id2 = await connection_manager.connect_websocket(ws2)
        
        # Broadcast to all
        sent_count = await connection_manager.broadcast_message("broadcast test")
        assert sent_count == 2
        
        # Verify both received message
        ws1.send_text.assert_called_once_with("broadcast test")
        ws2.send_text.assert_called_once_with("broadcast test")
        
        # Broadcast to specific connection type
        sent_count = await connection_manager.broadcast_message(
            "websocket only", ConnectionType.WEBSOCKET
        )
        assert sent_count == 2
        
        # Cleanup
        await connection_manager.disconnect(connection_id1, "Test complete")
        await connection_manager.disconnect(connection_id2, "Test complete")
    
    @pytest.mark.asyncio
    async def test_connection_filtering(self, connection_manager):
        """Test connection filtering"""
        # Create user and session
        user_id = await connection_manager.register_user("testuser", {})
        session_id = await connection_manager.create_session(user_id, {})
        
        # Create connections
        ws1 = Mock()
        ws1.send_text = AsyncMock()
        ws2 = Mock()
        ws2.send_text = AsyncMock()
        
        connection_id1 = await connection_manager.connect_websocket(
            ws1, session_id=session_id, user_id=user_id
        )
        connection_id2 = await connection_manager.connect_websocket(ws2)
        
        # Broadcast to session
        sent_count = await connection_manager.broadcast_message(
            "session message", session_id=session_id
        )
        assert sent_count == 1
        ws1.send_text.assert_called_once_with("session message")
        
        # Broadcast to user
        sent_count = await connection_manager.broadcast_message(
            "user message", user_id=user_id
        )
        assert sent_count == 1
        ws1.send_text.assert_called_with("user message")
        
        # Cleanup
        await connection_manager.disconnect(connection_id1, "Test complete")
        await connection_manager.disconnect(connection_id2, "Test complete")
        await connection_manager.end_session(session_id)
        await connection_manager.unregister_user(user_id)
    
    @pytest.mark.asyncio
    async def test_statistics(self, connection_manager, mock_websocket):
        """Test statistics collection"""
        # Get initial stats
        stats = await connection_manager.get_stats()
        assert stats['total'] == 0
        assert stats['websocket'] == 0
        assert stats['http'] == 0
        assert stats['cli'] == 0
        
        # Create connections
        ws_id = await connection_manager.connect_websocket(mock_websocket)
        http_id = await connection_manager.connect_http()
        cli_id = await connection_manager.connect_cli()
        
        # Get updated stats
        stats = await connection_manager.get_stats()
        assert stats['total'] == 3
        assert stats['websocket'] == 1
        assert stats['http'] == 1
        assert stats['cli'] == 1
        
        # Cleanup
        await connection_manager.disconnect(ws_id, "Test complete")
        await connection_manager.disconnect(http_id, "Test complete")
        await connection_manager.disconnect(cli_id, "Test complete")
        
        # Verify cleanup
        stats = await connection_manager.get_stats()
        assert stats['total'] == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self, connection_manager):
        """Test concurrent connection handling"""
        # Create many connections concurrently
        async def create_connection(i):
            ws = Mock()
            ws.send_text = AsyncMock()
            connection_id = await connection_manager.connect_websocket(ws)
            return connection_id, ws
        
        # Create 100 connections concurrently
        tasks = [create_connection(i) for i in range(100)]
        connections = await asyncio.gather(*tasks)
        
        # Verify all connections created
        assert len(connections) == 100
        stats = await connection_manager.get_stats()
        assert stats['total'] == 100
        
        # Broadcast message to all
        sent_count = await connection_manager.broadcast_message("concurrent test")
        assert sent_count == 100
        
        # Cleanup all connections
        cleanup_tasks = [
            connection_manager.disconnect(conn_id, "Test complete")
            for conn_id, _ in connections
        ]
        await asyncio.gather(*cleanup_tasks)
        
        # Verify cleanup
        stats = await connection_manager.get_stats()
        assert stats['total'] == 0
    
    @pytest.mark.asyncio
    async def test_connection_timeout(self, connection_manager, mock_websocket):
        """Test connection timeout handling"""
        # Connect
        connection_id = await connection_manager.connect_websocket(mock_websocket)
        
        # Simulate old connection
        connection = connection_manager.get_connection(connection_id)
        connection.last_activity = time.time() - 3600  # 1 hour ago
        
        # Manual cleanup of timed out connections
        await connection_manager.cleanup_inactive_connections(timeout=1800)  # 30 minutes
        
        # Connection should be removed
        assert connection_manager.get_connection(connection_id) is None
        
        # Verify WebSocket was closed
        mock_websocket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, connection_manager):
        """Test error handling"""
        # Try to get non-existent connection
        connection = connection_manager.get_connection("invalid")
        assert connection is None
        
        # Try to disconnect non-existent connection
        # Should not raise exception
        await connection_manager.disconnect("invalid", "Test")
        
        # Try to update activity for non-existent connection
        # Should not raise exception
        await connection_manager.update_activity("invalid")
        
        # Try to authenticate non-existent connection
        success = await connection_manager.authenticate("invalid", "token")
        assert not success
        
        # Try to send message to non-existent connection
        success = await connection_manager.send_message("invalid", "message")
        assert not success
    
    @pytest.mark.asyncio
    async def test_message_broker_integration(self, connection_manager, mock_websocket):
        """Test integration with message broker"""
        # Connect
        connection_id = await connection_manager.connect_websocket(mock_websocket)
        
        # The connection manager should publish events to message broker
        # This is tested indirectly through the event hooks
        
        # Authenticate
        await connection_manager.authenticate(connection_id, "test-token")
        
        # Disconnect
        await connection_manager.disconnect(connection_id, "Test complete")
        
        # Events should have been published (tested through hooks)
        # This test ensures the integration works without errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
