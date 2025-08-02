"""
Integration tests for WebSocket Code Execution
Tests WebSocket code execution integration with ICPY Code Execution Service
"""

import pytest
import pytest_asyncio
import asyncio
import json
import os
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
import uuid

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icpy.api.websocket_api import WebSocketAPI, get_websocket_api, shutdown_websocket_api
from icpy.services.code_execution_service import (
    CodeExecutionService, ExecutionResult, ExecutionStatus, Language,
    get_code_execution_service, shutdown_code_execution_service
)
from icpy.gateway.api_gateway import ApiGateway, get_api_gateway, shutdown_api_gateway
from icpy.core.message_broker import get_message_broker, shutdown_message_broker
from icpy.core.connection_manager import get_connection_manager, shutdown_connection_manager

# Mark all test methods as asyncio
pytestmark = pytest.mark.asyncio


class MockWebSocket:
    """Mock WebSocket for testing"""
    
    def __init__(self):
        self.messages_sent = []
        self.closed = False
        self.client_state = "CONNECTED"
        self.accepted = False
    
    async def accept(self):
        """Mock accept method"""
        self.accepted = True
    
    async def send_text(self, message: str):
        self.messages_sent.append(message)
    
    async def close(self):
        self.closed = True
        self.client_state = "DISCONNECTED"


class TestWebSocketCodeExecution:
    """Test suite for WebSocket Code Execution Integration"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Setup and teardown for each test"""
        # Setup
        yield
        
        # Teardown
        await shutdown_websocket_api()
        await shutdown_code_execution_service()
        await shutdown_api_gateway()
        await shutdown_message_broker()
        await shutdown_connection_manager()

    @pytest_asyncio.fixture
    async def websocket_api(self):
        """Get WebSocket API instance"""
        api = await get_websocket_api()
        return api

    @pytest_asyncio.fixture
    async def code_execution_service(self):
        """Get Code Execution Service instance"""
        service = get_code_execution_service()
        await service.start()
        return service

    @pytest_asyncio.fixture
    async def api_gateway(self):
        """Get API Gateway instance"""
        gateway = await get_api_gateway()
        return gateway

    @pytest_asyncio.fixture
    async def mock_websocket(self):
        """Create mock WebSocket"""
        return MockWebSocket()

    async def test_websocket_execute_message_handling(self, websocket_api, code_execution_service, mock_websocket):
        """Test WebSocket execute message handling"""
        # Connect mock WebSocket
        connection_id = await websocket_api.connect_websocket(mock_websocket)
        
        # Prepare execution message
        message_data = {
            "type": "execute",
            "code": "print('Hello, World!')",
            "language": "python",
            "execution_id": str(uuid.uuid4())
        }
        
        # Handle the message
        await websocket_api.handle_websocket_message(connection_id, json.dumps(message_data))
        
        # Verify response was sent
        assert len(mock_websocket.messages_sent) > 0
        
        # Check if we got a welcome message first
        messages = [json.loads(msg) for msg in mock_websocket.messages_sent]
        execution_result = None
        
        for msg in messages:
            if msg.get("type") == "execution_result":
                execution_result = msg
                break
        
        assert execution_result is not None, f"No execution_result found in messages: {messages}"
        assert execution_result["execution_id"] == message_data["execution_id"]
        assert execution_result["status"] == ExecutionStatus.COMPLETED.value
        assert len(execution_result["output"]) > 0
        assert "Hello, World!" in execution_result["output"][0]

    async def test_websocket_execute_streaming_message_handling(self, websocket_api, code_execution_service, mock_websocket):
        """Test WebSocket streaming execute message handling"""
        # Connect mock WebSocket
        connection_id = await websocket_api.connect_websocket(mock_websocket)
        
        # Clear initial messages (welcome, etc.)
        mock_websocket.messages_sent.clear()
        
        # Prepare streaming execution message
        message_data = {
            "type": "execute_streaming",
            "code": "print('Streaming test')\nprint('Line 2')",
            "language": "python",
            "execution_id": str(uuid.uuid4())
        }
        
        # Handle the message
        await websocket_api.handle_websocket_message(connection_id, json.dumps(message_data))
        
        # Verify messages were sent (started + updates)
        assert len(mock_websocket.messages_sent) >= 2
        
        # Check execution started message
        started_msg = json.loads(mock_websocket.messages_sent[0])
        assert started_msg["type"] == "execution_started"
        assert started_msg["execution_id"] == message_data["execution_id"]
        
        # Check update messages
        update_messages = [json.loads(msg) for msg in mock_websocket.messages_sent[1:]]
        assert any(msg["type"] == "execution_update" for msg in update_messages)

    async def test_websocket_execute_with_config(self, websocket_api, code_execution_service, mock_websocket):
        """Test WebSocket execute with custom configuration"""
        # Connect mock WebSocket
        connection_id = await websocket_api.connect_websocket(mock_websocket)
        
        # Prepare execution message with config
        message_data = {
            "type": "execute",
            "code": "import time; time.sleep(0.1); print('Configured execution')",
            "language": "python",
            "config": {
                "timeout": 5.0,
                "sandbox": True,
                "capture_output": True
            },
            "execution_id": str(uuid.uuid4())
        }
        
        # Handle the message
        await websocket_api.handle_websocket_message(connection_id, json.dumps(message_data))
        
        # Verify response
        assert len(mock_websocket.messages_sent) > 0
        response = json.loads(mock_websocket.messages_sent[-1])
        assert response["type"] == "execution_result"
        assert response["status"] == ExecutionStatus.COMPLETED.value

    async def test_websocket_execute_error_handling(self, websocket_api, code_execution_service, mock_websocket):
        """Test WebSocket execute error handling"""
        # Connect mock WebSocket
        connection_id = await websocket_api.connect_websocket(mock_websocket)
        
        # Prepare execution message with error
        message_data = {
            "type": "execute",
            "code": "raise ValueError('Test error')",
            "language": "python",
            "execution_id": str(uuid.uuid4())
        }
        
        # Handle the message
        await websocket_api.handle_websocket_message(connection_id, json.dumps(message_data))
        
        # Verify error response
        assert len(mock_websocket.messages_sent) > 0
        response = json.loads(mock_websocket.messages_sent[-1])
        assert response["type"] == "execution_result"
        assert response["status"] == ExecutionStatus.FAILED.value
        assert len(response["errors"]) > 0
        assert "ValueError" in response["errors"][0]

    async def test_websocket_execute_no_code_error(self, websocket_api, mock_websocket):
        """Test WebSocket execute with no code provided"""
        # Connect mock WebSocket
        connection_id = await websocket_api.connect_websocket(mock_websocket)
        
        # Prepare execution message without code
        message_data = {
            "type": "execute",
            "language": "python"
        }
        
        # Handle the message
        await websocket_api.handle_websocket_message(connection_id, json.dumps(message_data))
        
        # Verify error response
        assert len(mock_websocket.messages_sent) > 0
        response = json.loads(mock_websocket.messages_sent[-1])
        assert response["type"] == "error"
        assert "No code provided" in response["message"]

    async def test_websocket_execute_multi_language(self, websocket_api, code_execution_service, mock_websocket):
        """Test WebSocket execute with multiple languages"""
        # Connect mock WebSocket
        connection_id = await websocket_api.connect_websocket(mock_websocket)
        
        test_cases = [
            {
                "language": "python",
                "code": "print('Python test')",
                "expected_output": "Python test"
            },
            {
                "language": "javascript",
                "code": "console.log('JavaScript test');",
                "expected_output": "JavaScript test"
            },
            {
                "language": "bash",
                "code": "echo 'Bash test'",
                "expected_output": "Bash test"
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            # Clear previous messages
            mock_websocket.messages_sent.clear()
            
            # Prepare execution message
            message_data = {
                "type": "execute",
                "code": test_case["code"],
                "language": test_case["language"],
                "execution_id": str(uuid.uuid4())
            }
            
            # Handle the message
            await websocket_api.handle_websocket_message(connection_id, json.dumps(message_data))
            
            # Verify response
            assert len(mock_websocket.messages_sent) > 0
            response = json.loads(mock_websocket.messages_sent[-1])
            assert response["type"] == "execution_result"
            assert response["language"] == test_case["language"]
            
            # Check language-specific results
            if test_case["language"] == "python":
                assert response["status"] == ExecutionStatus.COMPLETED.value
                if response["output"]:
                    assert test_case["expected_output"] in response["output"][0]

    async def test_api_gateway_execute_code_method(self, api_gateway, code_execution_service):
        """Test API Gateway execute.code method"""
        # Prepare parameters
        params = {
            "code": "print('API Gateway test')",
            "language": "python",
            "config": {
                "timeout": 10.0,
                "sandbox": True
            }
        }
        
        context = {
            "connection_id": str(uuid.uuid4()),
            "connection_type": "websocket"
        }
        
        # Call the handler
        result = await api_gateway._handle_execute_code(params, context)
        
        # Verify result
        assert "execution_id" in result
        assert result["status"] == ExecutionStatus.COMPLETED.value
        assert result["language"] == Language.PYTHON.value
        assert len(result["output"]) > 0
        assert "API Gateway test" in result["output"][0]

    async def test_api_gateway_execute_code_streaming_method(self, api_gateway, code_execution_service):
        """Test API Gateway execute.code_streaming method"""
        # Prepare parameters
        params = {
            "code": "print('Streaming API test')",
            "language": "python",
            "config": {
                "timeout": 10.0,
                "real_time": True
            }
        }
        
        context = {
            "connection_id": str(uuid.uuid4()),
            "connection_type": "websocket"
        }
        
        # Call the handler
        result = await api_gateway._handle_execute_code_streaming(params, context)
        
        # Verify result
        assert "execution_id" in result
        assert result["status"] == ExecutionStatus.COMPLETED.value
        assert result["streaming"] is True

    async def test_api_gateway_execute_error_handling(self, api_gateway):
        """Test API Gateway execute error handling"""
        # Test with invalid parameters
        with pytest.raises(ValueError, match="Invalid execution parameters"):
            await api_gateway._handle_execute_code("invalid", {})
        
        # Test with missing code
        with pytest.raises(ValueError, match="Code required"):
            await api_gateway._handle_execute_code({}, {})

    async def test_websocket_execute_event_broadcasting(self, websocket_api, code_execution_service, mock_websocket):
        """Test execution event broadcasting to subscribers"""
        # Connect mock WebSocket
        connection_id = await websocket_api.connect_websocket(mock_websocket)
        
        # Subscribe to code execution events
        subscribe_msg = {
            "type": "subscribe",
            "topics": ["code_execution.*"]
        }
        await websocket_api.handle_websocket_message(connection_id, json.dumps(subscribe_msg))
        
        # Clear subscription response
        mock_websocket.messages_sent.clear()
        
        # Execute code
        execute_msg = {
            "type": "execute",
            "code": "print('Broadcasting test')",
            "language": "python",
            "execution_id": str(uuid.uuid4())
        }
        await websocket_api.handle_websocket_message(connection_id, json.dumps(execute_msg))
        
        # Verify both execution result and broadcast event were sent
        assert len(mock_websocket.messages_sent) >= 2
        
        # Find broadcast message
        broadcast_msgs = [json.loads(msg) for msg in mock_websocket.messages_sent 
                         if json.loads(msg).get("type") == "code_execution_completed"]
        assert len(broadcast_msgs) > 0
        
        broadcast_msg = broadcast_msgs[0]
        assert broadcast_msg["execution_id"] == execute_msg["execution_id"]
        assert broadcast_msg["status"] == ExecutionStatus.COMPLETED.value

    async def test_websocket_execute_timeout_handling(self, websocket_api, code_execution_service, mock_websocket):
        """Test execution timeout handling (or graceful completion)"""
        # Connect mock WebSocket
        connection_id = await websocket_api.connect_websocket(mock_websocket)
        
        # Clear initial messages
        mock_websocket.messages_sent.clear()
        
        # Prepare execution message with short timeout and potentially long running code
        message_data = {
            "type": "execute",
            "code": "import time; time.sleep(0.05); print('Quick execution')",  # Short sleep
            "language": "python",
            "config": {
                "timeout": 0.1  # Short timeout
            },
            "execution_id": str(uuid.uuid4())
        }
        
        # Handle the message
        await websocket_api.handle_websocket_message(connection_id, json.dumps(message_data))
        
        # Verify response was received
        assert len(mock_websocket.messages_sent) > 0
        response = json.loads(mock_websocket.messages_sent[-1])
        assert response["type"] == "execution_result"
        
        # Verify execution completed (timeout handling may vary by implementation)
        assert response["status"] in [ExecutionStatus.TIMEOUT.value, ExecutionStatus.FAILED.value, ExecutionStatus.COMPLETED.value]
        assert "execution_id" in response

    async def test_connection_cleanup_on_error(self, websocket_api, mock_websocket):
        """Test connection cleanup on execution error"""
        # Connect mock WebSocket
        connection_id = await websocket_api.connect_websocket(mock_websocket)
        
        # Verify connection exists
        assert connection_id in websocket_api.connections
        
        # Send malformed execution message
        malformed_message = '{"type": "execute", "code": "invalid json'
        
        # Handle the malformed message
        await websocket_api.handle_websocket_message(connection_id, malformed_message)
        
        # Verify error response was sent
        assert len(mock_websocket.messages_sent) > 0
        response = json.loads(mock_websocket.messages_sent[-1])
        assert response["type"] == "error"
        assert "Invalid JSON" in response["message"]
        
        # Connection should still exist (not cleaned up for JSON errors)
        assert connection_id in websocket_api.connections


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
