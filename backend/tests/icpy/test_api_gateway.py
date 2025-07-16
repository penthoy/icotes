"""
Integration tests for API Gateway
Tests WebSocket, HTTP, and CLI endpoints, protocol handling, and service integration
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any
import uuid

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icpy.gateway.api_gateway import (
    ApiGateway, RequestContext, get_api_gateway, shutdown_api_gateway
)
from icpy.core.connection_manager import ConnectionType, get_connection_manager
from icpy.core.message_broker import get_message_broker
from icpy.core.protocol import (
    JsonRpcRequest, JsonRpcResponse, ProtocolError, ErrorCode,
    get_protocol_handler
)

# Test FastAPI availability
try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from fastapi.websockets import WebSocketDisconnect
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


class TestApiGateway:
    """Test suite for API Gateway"""
    
    @pytest.fixture
    async def api_gateway(self):
        """Create fresh API Gateway for each test"""
        # Reset global instances
        global _api_gateway, _connection_manager, _message_broker, _protocol_handler
        _api_gateway = None
        _connection_manager = None
        _message_broker = None
        _protocol_handler = None
        
        gateway = await get_api_gateway()
        yield gateway
        
        # Cleanup
        await shutdown_api_gateway()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket"""
        websocket = Mock()
        websocket.accept = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket
    
    @pytest.fixture
    def mock_request(self):
        """Create mock HTTP request"""
        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "Test Agent"}
        request.body = AsyncMock()
        return request
    
    @pytest.mark.asyncio
    async def test_gateway_initialization(self, api_gateway):
        """Test API Gateway initialization"""
        assert api_gateway is not None
        assert api_gateway.connection_manager is not None
        assert api_gateway.message_broker is not None
        assert api_gateway.protocol_handler is not None
        
        # Verify default handlers are registered
        handlers = api_gateway.protocol_handler.methods
        assert "connection.ping" in handlers
        assert "connection.info" in handlers
        assert "connection.stats" in handlers
        assert "auth.login" in handlers
        assert "auth.logout" in handlers
        assert "message.send" in handlers
        assert "message.broadcast" in handlers
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, api_gateway, mock_websocket):
        """Test WebSocket connection handling"""
        # Setup WebSocket mock to simulate connection
        mock_websocket.receive_text.side_effect = [
            '{"jsonrpc": "2.0", "method": "connection.ping", "id": 1}',
            WebSocketDisconnect()
        ]
        
        # Handle WebSocket connection
        task = asyncio.create_task(api_gateway.handle_websocket(mock_websocket))
        
        # Wait a bit for processing
        await asyncio.sleep(0.1)
        
        # Verify WebSocket was accepted
        mock_websocket.accept.assert_called_once()
        
        # Verify response was sent
        assert mock_websocket.send_text.call_count >= 1
        
        # Check if the response is valid JSON-RPC
        response_data = mock_websocket.send_text.call_args[0][0]
        response = json.loads(response_data)
        assert response.get("jsonrpc") == "2.0"
        assert response.get("id") == 1
        assert "result" in response
        
        # Wait for task to complete
        try:
            await task
        except:
            pass  # Expected due to WebSocketDisconnect
    
    @pytest.mark.asyncio
    async def test_http_rpc_request(self, api_gateway, mock_request):
        """Test HTTP RPC request handling"""
        # Setup request body
        request_data = {
            "jsonrpc": "2.0",
            "method": "connection.ping",
            "id": 1
        }
        mock_request.body.return_value = json.dumps(request_data).encode()
        
        # Handle HTTP request
        response = await api_gateway.handle_http_rpc(mock_request)
        
        # Verify response
        assert response is not None
        assert response.media_type == "application/json"
        
        # Parse response content
        response_data = json.loads(response.body)
        assert response_data.get("jsonrpc") == "2.0"
        assert response_data.get("id") == 1
        assert "result" in response_data
        
        # Verify statistics updated
        stats = await api_gateway.get_stats()
        assert stats["http_requests"] >= 1
        assert stats["requests_processed"] >= 1
    
    @pytest.mark.asyncio
    async def test_cli_request(self, api_gateway):
        """Test CLI request handling"""
        # Prepare CLI request
        request_data = json.dumps({
            "jsonrpc": "2.0",
            "method": "connection.ping",
            "id": 1
        })
        
        # Handle CLI request
        response = await api_gateway.handle_cli_request(
            request_data, 
            process_id="12345",
            command="test-command"
        )
        
        # Verify response
        assert response is not None
        response_data = json.loads(response)
        assert response_data.get("jsonrpc") == "2.0"
        assert response_data.get("id") == 1
        assert "result" in response_data
        
        # Verify statistics updated
        stats = await api_gateway.get_stats()
        assert stats["cli_requests"] >= 1
        assert stats["requests_processed"] >= 1
    
    @pytest.mark.asyncio
    async def test_ping_handler(self, api_gateway):
        """Test ping RPC handler"""
        # Create request context
        context = {
            "connection_id": "test-connection",
            "connection_type": "websocket"
        }
        
        # Call ping handler
        result = await api_gateway._handle_ping(None, context)
        
        # Verify response
        assert result is not None
        assert result["pong"] is True
        assert "timestamp" in result
        assert result["connection_id"] == "test-connection"
    
    @pytest.mark.asyncio
    async def test_connection_info_handler(self, api_gateway, mock_websocket):
        """Test connection info RPC handler"""
        # First create a connection
        connection_id = await api_gateway.connection_manager.connect_websocket(mock_websocket)
        
        # Create request context
        context = {
            "connection_id": connection_id,
            "connection_type": "websocket"
        }
        
        # Call connection info handler
        result = await api_gateway._handle_connection_info(None, context)
        
        # Verify response
        assert result is not None
        assert result["connection_id"] == connection_id
        assert result["connection_type"] == "websocket"
        assert result["state"] == "connected"
        assert "created_at" in result
        assert "last_activity" in result
        
        # Cleanup
        await api_gateway.connection_manager.disconnect(connection_id, "Test complete")
    
    @pytest.mark.asyncio
    async def test_connection_stats_handler(self, api_gateway):
        """Test connection stats RPC handler"""
        # Call connection stats handler
        result = await api_gateway._handle_connection_stats(None, {})
        
        # Verify response
        assert result is not None
        assert "total" in result
        assert "websocket" in result
        assert "http" in result
        assert "cli" in result
    
    @pytest.mark.asyncio
    async def test_auth_login_handler(self, api_gateway, mock_websocket):
        """Test authentication login handler"""
        # Create connection
        connection_id = await api_gateway.connection_manager.connect_websocket(mock_websocket)
        
        # Create request context
        context = {
            "connection_id": connection_id,
            "connection_type": "websocket"
        }
        
        # Call auth login handler
        params = {
            "token": "test-token",
            "method": "bearer"
        }
        result = await api_gateway._handle_auth_login(params, context)
        
        # Verify response
        assert result is not None
        assert result["authenticated"] is True
        assert result["connection_id"] == connection_id
        assert "timestamp" in result
        
        # Verify connection is authenticated
        connection = api_gateway.connection_manager.get_connection(connection_id)
        assert connection.authenticated is True
        assert connection.auth_token == "test-token"
        
        # Cleanup
        await api_gateway.connection_manager.disconnect(connection_id, "Test complete")
    
    @pytest.mark.asyncio
    async def test_auth_logout_handler(self, api_gateway, mock_websocket):
        """Test authentication logout handler"""
        # Create and authenticate connection
        connection_id = await api_gateway.connection_manager.connect_websocket(mock_websocket)
        await api_gateway.connection_manager.authenticate(connection_id, "test-token")
        
        # Create request context
        context = {
            "connection_id": connection_id,
            "connection_type": "websocket"
        }
        
        # Call auth logout handler
        result = await api_gateway._handle_auth_logout(None, context)
        
        # Verify response
        assert result is not None
        assert result["logged_out"] is True
        assert "timestamp" in result
        
        # Verify connection is removed
        connection = api_gateway.connection_manager.get_connection(connection_id)
        assert connection is None
    
    @pytest.mark.asyncio
    async def test_message_send_handler(self, api_gateway):
        """Test message send handler"""
        # Create two connections
        ws1 = Mock()
        ws1.send_text = AsyncMock()
        ws2 = Mock()
        ws2.send_text = AsyncMock()
        
        connection_id1 = await api_gateway.connection_manager.connect_websocket(ws1)
        connection_id2 = await api_gateway.connection_manager.connect_websocket(ws2)
        
        # Create request context
        context = {
            "connection_id": connection_id1,
            "connection_type": "websocket"
        }
        
        # Call message send handler
        params = {
            "target": connection_id2,
            "message": "test message"
        }
        result = await api_gateway._handle_message_send(params, context)
        
        # Verify response
        assert result is not None
        assert result["sent"] is True
        assert result["target"] == connection_id2
        assert "timestamp" in result
        
        # Verify message was sent
        ws2.send_text.assert_called_once_with("test message")
        
        # Cleanup
        await api_gateway.connection_manager.disconnect(connection_id1, "Test complete")
        await api_gateway.connection_manager.disconnect(connection_id2, "Test complete")
    
    @pytest.mark.asyncio
    async def test_message_broadcast_handler(self, api_gateway):
        """Test message broadcast handler"""
        # Create multiple connections
        ws1 = Mock()
        ws1.send_text = AsyncMock()
        ws2 = Mock()
        ws2.send_text = AsyncMock()
        
        connection_id1 = await api_gateway.connection_manager.connect_websocket(ws1)
        connection_id2 = await api_gateway.connection_manager.connect_websocket(ws2)
        
        # Create request context
        context = {
            "connection_id": connection_id1,
            "connection_type": "websocket"
        }
        
        # Call message broadcast handler
        params = {
            "message": "broadcast message",
            "connection_type": "websocket"
        }
        result = await api_gateway._handle_message_broadcast(params, context)
        
        # Verify response
        assert result is not None
        assert result["sent_count"] == 2
        assert "timestamp" in result
        
        # Verify messages were sent to both connections
        ws1.send_text.assert_called_once_with("broadcast message")
        ws2.send_text.assert_called_once_with("broadcast message")
        
        # Cleanup
        await api_gateway.connection_manager.disconnect(connection_id1, "Test complete")
        await api_gateway.connection_manager.disconnect(connection_id2, "Test complete")
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, api_gateway):
        """Test broadcast message functionality"""
        # Create multiple connections
        ws1 = Mock()
        ws1.send_text = AsyncMock()
        ws2 = Mock()
        ws2.send_text = AsyncMock()
        
        connection_id1 = await api_gateway.connection_manager.connect_websocket(ws1)
        connection_id2 = await api_gateway.connection_manager.connect_websocket(ws2)
        
        # Broadcast to all connections
        sent_count = await api_gateway.broadcast_message("test broadcast")
        assert sent_count == 2
        
        # Verify messages were sent
        ws1.send_text.assert_called_once_with("test broadcast")
        ws2.send_text.assert_called_once_with("test broadcast")
        
        # Broadcast to specific connection type
        ws1.send_text.reset_mock()
        ws2.send_text.reset_mock()
        
        sent_count = await api_gateway.broadcast_message(
            "websocket only", ConnectionType.WEBSOCKET
        )
        assert sent_count == 2
        
        # Cleanup
        await api_gateway.connection_manager.disconnect(connection_id1, "Test complete")
        await api_gateway.connection_manager.disconnect(connection_id2, "Test complete")
    
    @pytest.mark.asyncio
    async def test_send_notification(self, api_gateway):
        """Test send notification functionality"""
        # Create connection
        ws = Mock()
        ws.send_text = AsyncMock()
        
        connection_id = await api_gateway.connection_manager.connect_websocket(ws)
        
        # Send notification to specific connection
        sent_count = await api_gateway.send_notification(
            "test.notification", 
            {"data": "test"}, 
            connection_id=connection_id
        )
        assert sent_count == 1
        
        # Verify notification was sent
        ws.send_text.assert_called_once()
        notification_data = json.loads(ws.send_text.call_args[0][0])
        assert notification_data["jsonrpc"] == "2.0"
        assert notification_data["method"] == "test.notification"
        assert notification_data["params"] == {"data": "test"}
        assert "id" not in notification_data  # Notifications don't have IDs
        
        # Cleanup
        await api_gateway.connection_manager.disconnect(connection_id, "Test complete")
    
    @pytest.mark.asyncio
    async def test_health_status(self, api_gateway):
        """Test health status endpoint"""
        # Get health status
        health = await api_gateway.get_health_status()
        
        # Verify response
        assert health is not None
        assert health["status"] == "healthy"
        assert "timestamp" in health
        assert "connections" in health
        assert "message_broker" in health
        assert "protocol" in health
        assert "gateway" in health
    
    @pytest.mark.asyncio
    async def test_gateway_statistics(self, api_gateway):
        """Test gateway statistics"""
        # Get initial stats
        stats = await api_gateway.get_stats()
        
        # Verify response
        assert stats is not None
        assert "requests_processed" in stats
        assert "websocket_connections" in stats
        assert "http_requests" in stats
        assert "cli_requests" in stats
        assert "errors" in stats
        assert "avg_response_time" in stats
        assert "timestamp" in stats
    
    @pytest.mark.asyncio
    async def test_request_context_creation(self, api_gateway, mock_websocket):
        """Test request context creation"""
        # Create connection
        connection_id = await api_gateway.connection_manager.connect_websocket(mock_websocket)
        
        # Create request context
        context = await api_gateway._create_request_context(connection_id)
        
        # Verify context
        assert context is not None
        assert context.connection_id == connection_id
        assert context.connection_type == ConnectionType.WEBSOCKET
        assert context.session_id is None
        assert context.user_id is None
        assert isinstance(context.metadata, dict)
        assert context.created_at > 0
        
        # Test context serialization
        context_dict = context.to_dict()
        assert context_dict["connection_id"] == connection_id
        assert context_dict["connection_type"] == "websocket"
        
        # Cleanup
        await api_gateway.connection_manager.disconnect(connection_id, "Test complete")
    
    @pytest.mark.asyncio
    async def test_error_handling(self, api_gateway, mock_request):
        """Test error handling"""
        # Test invalid JSON in HTTP request
        mock_request.body.return_value = b"invalid json"
        
        response = await api_gateway.handle_http_rpc(mock_request)
        
        # Verify error response
        assert response is not None
        assert response.status_code == 500
        
        response_data = json.loads(response.body)
        assert response_data.get("jsonrpc") == "2.0"
        assert "error" in response_data
        
        # Verify error statistics
        stats = await api_gateway.get_stats()
        assert stats["errors"] >= 1
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, api_gateway):
        """Test concurrent request handling"""
        # Create multiple CLI requests concurrently
        async def make_request(i):
            request_data = json.dumps({
                "jsonrpc": "2.0",
                "method": "connection.ping",
                "id": i
            })
            return await api_gateway.handle_cli_request(request_data, process_id=str(i))
        
        # Make 50 concurrent requests
        tasks = [make_request(i) for i in range(50)]
        responses = await asyncio.gather(*tasks)
        
        # Verify all requests were processed
        assert len(responses) == 50
        
        for i, response in enumerate(responses):
            response_data = json.loads(response)
            assert response_data.get("jsonrpc") == "2.0"
            assert response_data.get("id") == i
            assert "result" in response_data
        
        # Verify statistics
        stats = await api_gateway.get_stats()
        assert stats["requests_processed"] >= 50
        assert stats["cli_requests"] >= 50
    
    @pytest.mark.asyncio
    async def test_protocol_validation(self, api_gateway, mock_request):
        """Test protocol validation"""
        # Test invalid JSON-RPC request
        invalid_request = {
            "method": "connection.ping",  # Missing jsonrpc and id
            "params": {}
        }
        mock_request.body.return_value = json.dumps(invalid_request).encode()
        
        response = await api_gateway.handle_http_rpc(mock_request)
        
        # Should handle gracefully (protocol handler deals with validation)
        assert response is not None
        
        # Test batch request
        batch_request = [
            {"jsonrpc": "2.0", "method": "connection.ping", "id": 1},
            {"jsonrpc": "2.0", "method": "connection.ping", "id": 2}
        ]
        mock_request.body.return_value = json.dumps(batch_request).encode()
        
        response = await api_gateway.handle_http_rpc(mock_request)
        
        # Should handle batch requests
        assert response is not None
        response_data = json.loads(response.body)
        assert isinstance(response_data, list)
        assert len(response_data) == 2


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestApiGatewayFastAPI:
    """Test suite for FastAPI integration"""
    
    @pytest.fixture
    def test_client(self):
        """Create FastAPI test client"""
        # Mock the gateway initialization
        with patch('icpy.gateway.api_gateway.get_api_gateway') as mock_get_gateway:
            mock_gateway = Mock()
            mock_gateway.app = FastAPI()
            mock_gateway.handle_websocket = AsyncMock()
            mock_gateway.handle_http_rpc = AsyncMock()
            mock_gateway.get_health_status = AsyncMock(return_value={"status": "healthy"})
            mock_gateway.get_stats = AsyncMock(return_value={"requests": 0})
            
            mock_get_gateway.return_value = mock_gateway
            
            from icpy.gateway.api_gateway import create_fastapi_app
            app = create_fastapi_app()
            
            yield TestClient(app)
    
    def test_health_endpoint(self, test_client):
        """Test health check endpoint"""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_stats_endpoint(self, test_client):
        """Test statistics endpoint"""
        response = test_client.get("/stats")
        assert response.status_code == 200
        assert "requests" in response.json()
    
    def test_rpc_endpoint(self, test_client):
        """Test RPC endpoint"""
        request_data = {
            "jsonrpc": "2.0",
            "method": "connection.ping",
            "id": 1
        }
        
        response = test_client.post("/rpc", json=request_data)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
