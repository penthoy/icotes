"""
Integration tests for JSON-RPC Protocol
Tests message validation, serialization, error handling, and protocol versioning
"""

import asyncio
import pytest
import pytest_asyncio
import json
import time
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock

# Add the backend directory to the path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icpy.core.protocol import (
    ProtocolHandler, ProtocolValidator, ProtocolError, ErrorCode, ProtocolVersion,
    JsonRpcRequest, JsonRpcResponse, JsonRpcBatch,
    create_request, create_notification, create_success_response, create_error_response,
    get_protocol_handler, reset_protocol_handler
)


class TestJsonRpcRequest:
    """Test cases for JsonRpcRequest"""
    
    def test_valid_request_creation(self):
        """Test creating valid JSON-RPC requests"""
        request = JsonRpcRequest(
            method="test.method",
            params={"arg1": "value1"},
            id="test-id"
        )
        
        assert request.jsonrpc == "2.0"
        assert request.method == "test.method"
        assert request.params == {"arg1": "value1"}
        assert request.id == "test-id"
        assert not request.is_notification()
        assert not request.is_expired()
    
    def test_notification_creation(self):
        """Test creating JSON-RPC notifications"""
        notification = JsonRpcRequest(
            method="test.notify",
            params=["arg1", "arg2"],
            id=None
        )
        
        assert notification.is_notification()
        assert notification.id is None
    
    def test_request_validation_errors(self):
        """Test request validation errors"""
        # Empty method - expect pydantic ValidationError instead of ValueError
        with pytest.raises(Exception, match="Method cannot be empty"):
            JsonRpcRequest(method="", id="test")
        
        # Invalid JSON-RPC version
        with pytest.raises(ValueError, match="Only JSON-RPC 2.0 is supported"):
            JsonRpcRequest(method="test", jsonrpc="1.0", id="test")
    
    def test_request_expiration(self):
        """Test request timeout/expiration"""
        request = JsonRpcRequest(
            method="test.method",
            id="test",
            timeout=0.1
        )
        
        assert not request.is_expired()
        
        # Wait for expiration
        time.sleep(0.2)
        assert request.is_expired()
    
    def test_request_serialization(self):
        """Test request JSON serialization"""
        request = JsonRpcRequest(
            method="test.method",
            params={"key": "value"},
            id="test-id"
        )
        
        # Convert to dict
        data = request.model_dump()
        assert data['jsonrpc'] == "2.0"
        assert data['method'] == "test.method"
        assert data['params'] == {"key": "value"}
        assert data['id'] == "test-id"
        
        # Convert to JSON
        json_str = request.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed['jsonrpc'] == "2.0"
        assert parsed['method'] == "test.method"


class TestJsonRpcResponse:
    """Test cases for JsonRpcResponse"""
    
    def test_success_response(self):
        """Test successful response creation"""
        response = JsonRpcResponse(
            result={"status": "success"},
            id="test-id"
        )
        
        assert response.jsonrpc == "2.0"
        assert response.result == {"status": "success"}
        assert response.error is None
        assert response.id == "test-id"
        
        # Validation should pass
        response.validate_response()
    
    def test_error_response(self):
        """Test error response creation"""
        error = ProtocolError(
            code=ErrorCode.INVALID_PARAMS.value,
            message="Invalid parameters"
        )
        
        response = JsonRpcResponse(
            error=error.to_dict(),
            id="test-id"
        )
        
        assert response.result is None
        assert response.error is not None
        assert response.error['code'] == ErrorCode.INVALID_PARAMS.value
        assert response.error['message'] == "Invalid parameters"
        
        # Validation should pass
        response.validate_response()
    
    def test_response_validation_errors(self):
        """Test response validation errors"""
        # Both result and error
        response = JsonRpcResponse(
            result="success",
            error={"code": -1, "message": "error"},
            id="test"
        )
        
        with pytest.raises(ValueError, match="Response cannot have both result and error"):
            response.validate_response()
        
        # Neither result nor error
        response = JsonRpcResponse(id="test")
        with pytest.raises(ValueError, match="Response must have either result or error"):
            response.validate_response()


class TestProtocolError:
    """Test cases for ProtocolError"""
    
    def test_error_creation(self):
        """Test error creation and serialization"""
        error = ProtocolError(
            code=ErrorCode.METHOD_NOT_FOUND.value,
            message="Method not found",
            data={"method": "test.method"}
        )
        
        assert error.code == ErrorCode.METHOD_NOT_FOUND.value
        assert error.message == "Method not found"
        assert error.data == {"method": "test.method"}
        
        # Test serialization
        error_dict = error.to_dict()
        assert error_dict['code'] == ErrorCode.METHOD_NOT_FOUND.value
        assert error_dict['message'] == "Method not found"
        assert error_dict['data'] == {"method": "test.method"}
        
        # Test deserialization
        recreated = ProtocolError.from_dict(error_dict)
        assert recreated.code == error.code
        assert recreated.message == error.message
        assert recreated.data == error.data
    
    def test_error_without_data(self):
        """Test error without data field"""
        error = ProtocolError(
            code=ErrorCode.INTERNAL_ERROR.value,
            message="Internal error"
        )
        
        error_dict = error.to_dict()
        assert 'data' not in error_dict
        assert error_dict['code'] == ErrorCode.INTERNAL_ERROR.value
        assert error_dict['message'] == "Internal error"


class TestProtocolValidator:
    """Test cases for ProtocolValidator"""
    
    def test_request_validation(self):
        """Test request validation"""
        validator = ProtocolValidator()
        
        # Valid request
        request = JsonRpcRequest(method="test.method", id="test")
        assert validator.validate_request(request) is True
        
        # Valid notification
        notification = JsonRpcRequest(method="test.notify", id=None)
        assert validator.validate_request(notification) is True
    
    def test_response_validation(self):
        """Test response validation"""
        validator = ProtocolValidator()
        
        # Valid success response
        response = JsonRpcResponse(result="success", id="test")
        assert validator.validate_response(response) is True
        
        # Valid error response
        error_response = JsonRpcResponse(
            error={"code": -1, "message": "error"},
            id="test"
        )
        assert validator.validate_response(error_response) is True
    
    def test_version_compatibility(self):
        """Test protocol version compatibility"""
        validator = ProtocolValidator(supported_versions=[ProtocolVersion.V2_0])
        
        # Supported version
        request = JsonRpcRequest(method="test", jsonrpc="2.0", id="test")
        assert validator.validate_request(request) is True


class TestProtocolHandler:
    """Test cases for ProtocolHandler"""
    
    @pytest_asyncio.fixture
    async def handler(self):
        """Create a protocol handler for testing"""
        reset_protocol_handler()
        handler = ProtocolHandler()
        yield handler
        reset_protocol_handler()
    
    @pytest.mark.asyncio
    async def test_method_registration(self, handler):
        """Test method handler registration"""
        def test_method(params, context):
            return {"result": "success"}
        
        handler.register_method("test.method", test_method)
        
        stats = handler.get_stats()
        assert "test.method" in stats['registered_methods']
    
    @pytest.mark.asyncio
    async def test_simple_request_processing(self, handler):
        """Test processing simple requests"""
        def test_method(params, context):
            return {"echo": params}
        
        handler.register_method("test.echo", test_method)
        
        request_json = json.dumps({
            "jsonrpc": "2.0",
            "method": "test.echo",
            "params": {"message": "hello"},
            "id": "test-1"
        })
        
        response_json = await handler.process_request(request_json)
        response = json.loads(response_json)
        
        assert response['jsonrpc'] == "2.0"
        assert response['result'] == {"echo": {"message": "hello"}}
        assert response['id'] == "test-1"
        assert 'execution_time' in response
    
    @pytest.mark.asyncio
    async def test_async_method_processing(self, handler):
        """Test processing async methods"""
        async def async_method(params, context):
            await asyncio.sleep(0.01)  # Simulate async work
            return {"async_result": params}
        
        handler.register_method("test.async", async_method)
        
        request_json = json.dumps({
            "jsonrpc": "2.0",
            "method": "test.async",
            "params": {"data": "test"},
            "id": "async-1"
        })
        
        response_json = await handler.process_request(request_json)
        response = json.loads(response_json)
        
        assert response['result'] == {"async_result": {"data": "test"}}
    
    @pytest.mark.asyncio
    async def test_notification_processing(self, handler):
        """Test processing notifications (no response)"""
        processed = []
        
        def notification_handler(params, context):
            processed.append(params)
        
        handler.register_method("test.notify", notification_handler)
        
        request_json = json.dumps({
            "jsonrpc": "2.0",
            "method": "test.notify",
            "params": {"message": "notification"}
        })
        
        response_json = await handler.process_request(request_json)
        
        # No response for notifications
        assert response_json == ""
        assert processed == [{"message": "notification"}]
    
    @pytest.mark.asyncio
    async def test_method_not_found(self, handler):
        """Test method not found error"""
        request_json = json.dumps({
            "jsonrpc": "2.0",
            "method": "nonexistent.method",
            "id": "test-1"
        })
        
        response_json = await handler.process_request(request_json)
        response = json.loads(response_json)
        
        assert response['jsonrpc'] == "2.0"
        assert response['error']['code'] == ErrorCode.METHOD_NOT_FOUND.value
        assert "nonexistent.method" in response['error']['message']
        assert response['id'] == "test-1"
    
    @pytest.mark.asyncio
    async def test_method_error_handling(self, handler):
        """Test method error handling"""
        def failing_method(params, context):
            raise ValueError("Test error")
        
        handler.register_method("test.fail", failing_method)
        
        request_json = json.dumps({
            "jsonrpc": "2.0",
            "method": "test.fail",
            "id": "test-1"
        })
        
        response_json = await handler.process_request(request_json)
        response = json.loads(response_json)
        
        assert response['error']['code'] == ErrorCode.INTERNAL_ERROR.value
        assert "Test error" in response['error']['message']
    
    @pytest.mark.asyncio
    async def test_batch_request_processing(self, handler):
        """Test batch request processing"""
        def echo_method(params, context):
            return {"echo": params}
        
        def math_add(params, context):
            return params['a'] + params['b']
        
        handler.register_method("test.echo", echo_method)
        handler.register_method("math.add", math_add)
        
        batch_request = json.dumps([
            {
                "jsonrpc": "2.0",
                "method": "test.echo",
                "params": {"msg": "hello"},
                "id": "1"
            },
            {
                "jsonrpc": "2.0",
                "method": "math.add",
                "params": {"a": 5, "b": 3},
                "id": "2"
            },
            {
                "jsonrpc": "2.0",
                "method": "test.notify",
                "params": {"notification": True}
            }
        ])
        
        response_json = await handler.process_request(batch_request)
        responses = json.loads(response_json)
        
        # Should have 2 responses (notification doesn't return response)
        assert len(responses) == 2
        
        # Check responses
        echo_response = next(r for r in responses if r['id'] == "1")
        assert echo_response['result'] == {"echo": {"msg": "hello"}}
        
        math_response = next(r for r in responses if r['id'] == "2")
        assert math_response['result'] == 8
    
    @pytest.mark.asyncio
    async def test_middleware_processing(self, handler):
        """Test middleware processing"""
        middleware_calls = []
        
        def auth_middleware(request, context):
            middleware_calls.append("auth")
            if context and context.get('user_id'):
                request.metadata = {"user_id": context['user_id']}
            return request
        
        async def async_middleware(request, context):
            middleware_calls.append("async")
            await asyncio.sleep(0.01)
            return request
        
        def test_method(params, context):
            return {"middleware_calls": middleware_calls}
        
        handler.register_middleware(auth_middleware)
        handler.register_middleware(async_middleware)
        handler.register_method("test.method", test_method)
        
        request_json = json.dumps({
            "jsonrpc": "2.0",
            "method": "test.method",
            "id": "test-1"
        })
        
        context = {"user_id": "user123"}
        response_json = await handler.process_request(request_json, context)
        response = json.loads(response_json)
        
        assert response['result']['middleware_calls'] == ["auth", "async"]
    
    @pytest.mark.asyncio
    async def test_parse_error_handling(self, handler):
        """Test parse error handling"""
        invalid_json = "{ invalid json }"
        
        response_json = await handler.process_request(invalid_json)
        response = json.loads(response_json)
        
        assert response['error']['code'] == ErrorCode.PARSE_ERROR.value
        assert "Parse error" in response['error']['message']
    
    @pytest.mark.asyncio
    async def test_request_timeout(self, handler):
        """Test request timeout handling"""
        def test_method(params, context):
            return "success"
        
        handler.register_method("test.method", test_method)
        
        # Create request with short timeout
        request_json = json.dumps({
            "jsonrpc": "2.0",
            "method": "test.method",
            "id": "test-1",
            "timeout": 0.01,
            "timestamp": time.time() - 1  # Already expired
        })
        
        response_json = await handler.process_request(request_json)
        response = json.loads(response_json)
        
        assert response['error']['code'] == ErrorCode.TIMEOUT_ERROR.value
        assert "expired" in response['error']['message']
    
    @pytest.mark.asyncio
    async def test_handler_statistics(self, handler):
        """Test handler statistics tracking"""
        def test_method(params, context):
            return "success"
        
        handler.register_method("test.method", test_method)
        
        # Process some requests
        for i in range(3):
            request_json = json.dumps({
                "jsonrpc": "2.0",
                "method": "test.method",
                "id": f"test-{i}"
            })
            await handler.process_request(request_json)
        
        stats = handler.get_stats()
        assert stats['requests_processed'] == 3
        assert stats['errors_count'] == 0
        assert stats['avg_response_time'] > 0
        assert "test.method" in stats['registered_methods']


class TestUtilityFunctions:
    """Test cases for utility functions"""
    
    def test_create_request(self):
        """Test create_request utility"""
        request = create_request("test.method", {"param": "value"}, "test-id")
        
        assert request.method == "test.method"
        assert request.params == {"param": "value"}
        assert request.id == "test-id"
        assert not request.is_notification()
    
    def test_create_notification(self):
        """Test create_notification utility"""
        notification = create_notification("test.notify", ["arg1", "arg2"])
        
        assert notification.method == "test.notify"
        assert notification.params == ["arg1", "arg2"]
        assert notification.id is None
        assert notification.is_notification()
    
    def test_create_success_response(self):
        """Test create_success_response utility"""
        response = create_success_response({"status": "ok"}, "test-id")
        
        assert response.result == {"status": "ok"}
        assert response.error is None
        assert response.id == "test-id"
        response.validate_response()
    
    def test_create_error_response(self):
        """Test create_error_response utility"""
        error = ProtocolError(
            code=ErrorCode.INVALID_PARAMS.value,
            message="Invalid parameters"
        )
        response = create_error_response(error, "test-id")
        
        assert response.result is None
        assert response.error is not None
        assert response.error['code'] == ErrorCode.INVALID_PARAMS.value
        assert response.id == "test-id"
        response.validate_response()


class TestProtocolVersioning:
    """Test cases for protocol versioning"""
    
    def test_version_enumeration(self):
        """Test protocol version enumeration"""
        assert ProtocolVersion.V1_0.value == "1.0"
        assert ProtocolVersion.V2_0.value == "2.0"
    
    def test_version_validation(self):
        """Test version validation in requests"""
        # Valid version
        request = JsonRpcRequest(method="test", jsonrpc="2.0", id="test")
        assert request.jsonrpc == "2.0"
        
        # Invalid version should raise error
        with pytest.raises(ValueError):
            JsonRpcRequest(method="test", jsonrpc="1.0", id="test")


class TestErrorCodes:
    """Test cases for error codes"""
    
    def test_standard_error_codes(self):
        """Test standard JSON-RPC error codes"""
        assert ErrorCode.PARSE_ERROR.value == -32700
        assert ErrorCode.INVALID_REQUEST.value == -32600
        assert ErrorCode.METHOD_NOT_FOUND.value == -32601
        assert ErrorCode.INVALID_PARAMS.value == -32602
        assert ErrorCode.INTERNAL_ERROR.value == -32603
    
    def test_icpy_error_codes(self):
        """Test icpy-specific error codes"""
        assert ErrorCode.AUTHENTICATION_ERROR.value == -32000
        assert ErrorCode.AUTHORIZATION_ERROR.value == -32001
        assert ErrorCode.RATE_LIMIT_ERROR.value == -32002
        assert ErrorCode.SERVICE_UNAVAILABLE.value == -32003
        assert ErrorCode.CONNECTION_ERROR.value == -32004
        assert ErrorCode.VALIDATION_ERROR.value == -32005
        assert ErrorCode.TIMEOUT_ERROR.value == -32006
        assert ErrorCode.RESOURCE_NOT_FOUND.value == -32007
        assert ErrorCode.RESOURCE_CONFLICT.value == -32008
        assert ErrorCode.QUOTA_EXCEEDED.value == -32009


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
