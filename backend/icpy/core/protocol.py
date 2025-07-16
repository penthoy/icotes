"""
JSON-RPC Protocol Definition for icpy Backend
Provides standardized message format for all communication (WebSocket, HTTP, CLI)
Supports JSON-RPC 2.0 specification with extensions
"""

import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import asyncio
from pydantic import BaseModel, Field, field_validator, ValidationError

logger = logging.getLogger(__name__)


class ProtocolVersion(Enum):
    """Protocol versions for compatibility"""
    V1_0 = "1.0"
    V2_0 = "2.0"  # Current default


class ErrorCode(Enum):
    """Standard JSON-RPC error codes with icpy extensions"""
    # Standard JSON-RPC errors
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # icpy-specific errors (reserved range -32000 to -32099)
    AUTHENTICATION_ERROR = -32000
    AUTHORIZATION_ERROR = -32001
    RATE_LIMIT_ERROR = -32002
    SERVICE_UNAVAILABLE = -32003
    CONNECTION_ERROR = -32004
    VALIDATION_ERROR = -32005
    TIMEOUT_ERROR = -32006
    RESOURCE_NOT_FOUND = -32007
    RESOURCE_CONFLICT = -32008
    QUOTA_EXCEEDED = -32009


@dataclass
class ProtocolError(Exception):
    """JSON-RPC error structure"""
    code: int
    message: str
    data: Optional[Any] = None
    
    def __post_init__(self):
        """Initialize the Exception with the message"""
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'code': self.code,
            'message': self.message
        }
        if self.data is not None:
            result['data'] = self.data
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProtocolError':
        """Create from dictionary"""
        return cls(
            code=data['code'],
            message=data['message'],
            data=data.get('data')
        )


class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 request structure"""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name")
    params: Optional[Union[Dict[str, Any], List[Any]]] = Field(default=None, description="Method parameters")
    id: Optional[Union[str, int]] = Field(default=None, description="Request identifier")
    
    # icpy extensions
    timestamp: Optional[float] = Field(default_factory=time.time, description="Request timestamp")
    client_id: Optional[str] = Field(default=None, description="Client identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    timeout: Optional[float] = Field(default=30.0, description="Request timeout in seconds")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    @field_validator('jsonrpc')
    @classmethod
    def validate_jsonrpc(cls, v):
        if v != "2.0":
            raise ValueError("Only JSON-RPC 2.0 is supported")
        return v
    
    @field_validator('method')
    @classmethod
    def validate_method(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Method must be a non-empty string")
        return v
    
    def is_notification(self) -> bool:
        """Check if this is a notification (no id)"""
        return self.id is None
    
    def is_expired(self) -> bool:
        """Check if request has expired"""
        if self.timeout is None:
            return False
        return time.time() - self.timestamp > self.timeout


class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 response structure"""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    result: Optional[Any] = Field(default=None, description="Method result")
    error: Optional[Dict[str, Any]] = Field(default=None, description="Error information")
    id: Optional[Union[str, int]] = Field(..., description="Request identifier")
    
    # icpy extensions
    timestamp: Optional[float] = Field(default_factory=time.time, description="Response timestamp")
    execution_time: Optional[float] = Field(default=None, description="Execution time in seconds")
    server_id: Optional[str] = Field(default=None, description="Server identifier")
    
    @field_validator('jsonrpc')
    @classmethod
    def validate_jsonrpc(cls, v):
        if v != "2.0":
            raise ValueError("Only JSON-RPC 2.0 is supported")
        return v
    
    def validate_response(self):
        """Validate response structure"""
        if self.result is not None and self.error is not None:
            raise ValueError("Response cannot have both result and error")
        if self.result is None and self.error is None:
            raise ValueError("Response must have either result or error")


class JsonRpcBatch(BaseModel):
    """JSON-RPC batch request/response"""
    requests: List[JsonRpcRequest] = Field(..., description="Batch requests")
    
    @field_validator('requests')
    @classmethod
    def validate_requests(cls, v):
        if not v:
            raise ValueError("Batch cannot be empty")
        return v


class ProtocolMessage:
    """Base class for protocol messages with serialization support"""
    
    def __init__(self, version: ProtocolVersion = ProtocolVersion.V2_0):
        self.version = version
        self.timestamp = time.time()
        self.message_id = str(uuid.uuid4())
    
    def to_json(self) -> str:
        """Serialize to JSON string"""
        try:
            return json.dumps(self.to_dict(), default=str)
        except Exception as e:
            logger.error(f"Failed to serialize message: {e}")
            raise ProtocolError(
                code=ErrorCode.INTERNAL_ERROR.value,
                message=f"Serialization error: {str(e)}"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary - to be implemented by subclasses"""
        raise NotImplementedError
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ProtocolMessage':
        """Deserialize from JSON string"""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise ProtocolError(
                code=ErrorCode.PARSE_ERROR.value,
                message=f"Parse error: {str(e)}"
            )
        except Exception as e:
            raise ProtocolError(
                code=ErrorCode.INTERNAL_ERROR.value,
                message=f"Deserialization error: {str(e)}"
            )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProtocolMessage':
        """Create from dictionary - to be implemented by subclasses"""
        raise NotImplementedError


class ProtocolHandler:
    """Protocol message handler with validation and routing"""
    
    def __init__(self, version: ProtocolVersion = ProtocolVersion.V2_0):
        self.version = version
        self.method_handlers: Dict[str, Callable] = {}
        self.middleware: List[Callable] = []
        self.stats = {
            'requests_processed': 0,
            'errors_count': 0,
            'avg_response_time': 0.0
        }
    
    def register_method(self, method_name: str, handler: Callable):
        """Register a method handler"""
        self.method_handlers[method_name] = handler
        logger.debug(f"Registered method handler: {method_name}")
    
    def register_middleware(self, middleware: Callable):
        """Register middleware for request processing"""
        self.middleware.append(middleware)
        logger.debug(f"Registered middleware: {middleware.__name__}")
    
    async def process_request(self, request_data: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process a JSON-RPC request and return response"""
        start_time = time.time()
        
        try:
            # Parse request
            request = self._parse_request(request_data)
            
            # Apply middleware
            for middleware in self.middleware:
                request = await self._apply_middleware(middleware, request, context)
            
            # Process request
            if isinstance(request, list):
                # Batch request
                responses = []
                for req in request:
                    response = await self._process_single_request(req, context)
                    if response:  # Don't include responses for notifications
                        responses.append(response)
                result = responses
            else:
                # Single request
                result = await self._process_single_request(request, context)
            
            # Update stats
            execution_time = time.time() - start_time
            self.stats['requests_processed'] += 1
            self.stats['avg_response_time'] = (
                (self.stats['avg_response_time'] * (self.stats['requests_processed'] - 1) + execution_time) /
                self.stats['requests_processed']
            )
            
            return json.dumps(result, default=str) if result else ""
            
        except ProtocolError as e:
            self.stats['errors_count'] += 1
            error_response = JsonRpcResponse(
                error=e.to_dict(),
                id=None
            )
            return error_response.model_dump_json()
        except Exception as e:
            self.stats['errors_count'] += 1
            logger.error(f"Unexpected error processing request: {e}")
            error_response = JsonRpcResponse(
                error=ProtocolError(
                    code=ErrorCode.INTERNAL_ERROR.value,
                    message=f"Internal error: {str(e)}"
                ).to_dict(),
                id=None
            )
            return error_response.model_dump_json()
    
    def _parse_request(self, request_data: str) -> Union[JsonRpcRequest, List[JsonRpcRequest]]:
        """Parse JSON-RPC request"""
        try:
            data = json.loads(request_data)
            
            if isinstance(data, list):
                # Batch request
                if not data:
                    raise ProtocolError(
                        code=ErrorCode.INVALID_REQUEST.value,
                        message="Batch request cannot be empty"
                    )
                return [JsonRpcRequest(**item) for item in data]
            else:
                # Single request
                return JsonRpcRequest(**data)
                
        except json.JSONDecodeError as e:
            raise ProtocolError(
                code=ErrorCode.PARSE_ERROR.value,
                message=f"Parse error: {str(e)}"
            )
        except ValidationError as e:
            raise ProtocolError(
                code=ErrorCode.INVALID_REQUEST.value,
                message=f"Invalid request: {str(e)}"
            )
    
    async def _apply_middleware(self, middleware: Callable, request: JsonRpcRequest, 
                              context: Optional[Dict[str, Any]]) -> JsonRpcRequest:
        """Apply middleware to request"""
        try:
            if asyncio.iscoroutinefunction(middleware):
                return await middleware(request, context)
            else:
                return middleware(request, context)
        except Exception as e:
            logger.error(f"Middleware error: {e}")
            raise ProtocolError(
                code=ErrorCode.INTERNAL_ERROR.value,
                message=f"Middleware error: {str(e)}"
            )
    
    async def _process_single_request(self, request: JsonRpcRequest, 
                                    context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Process a single JSON-RPC request"""
        start_time = time.time()
        
        try:
            # Check if request has expired
            if request.is_expired():
                if not request.is_notification():
                    return JsonRpcResponse(
                        error=ProtocolError(
                            code=ErrorCode.TIMEOUT_ERROR.value,
                            message="Request has expired"
                        ).to_dict(),
                        id=request.id
                    ).model_dump()
                return None
            
            # Find method handler
            if request.method not in self.method_handlers:
                if not request.is_notification():
                    return JsonRpcResponse(
                        error=ProtocolError(
                            code=ErrorCode.METHOD_NOT_FOUND.value,
                            message=f"Method '{request.method}' not found"
                        ).to_dict(),
                        id=request.id
                    ).model_dump()
                return None
            
            # Call method handler
            handler = self.method_handlers[request.method]
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(request.params, context)
                else:
                    result = handler(request.params, context)
                
                # Return response for non-notifications
                if not request.is_notification():
                    execution_time = time.time() - start_time
                    return JsonRpcResponse(
                        result=result,
                        id=request.id,
                        execution_time=execution_time
                    ).model_dump()
                
                return None
                
            except Exception as e:
                logger.error(f"Method handler error: {e}")
                if not request.is_notification():
                    return JsonRpcResponse(
                        error=ProtocolError(
                            code=ErrorCode.INTERNAL_ERROR.value,
                            message=f"Method error: {str(e)}"
                        ).to_dict(),
                        id=request.id
                    ).model_dump()
                return None
                
        except Exception as e:
            logger.error(f"Request processing error: {e}")
            if not request.is_notification():
                return JsonRpcResponse(
                    error=ProtocolError(
                        code=ErrorCode.INTERNAL_ERROR.value,
                        message=f"Processing error: {str(e)}"
                    ).to_dict(),
                    id=request.id
                ).model_dump()
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get protocol handler statistics"""
        return {
            **self.stats,
            'registered_methods': list(self.method_handlers.keys()),
            'middleware_count': len(self.middleware)
        }


class ProtocolValidator:
    """Protocol message validator with version compatibility"""
    
    def __init__(self, supported_versions: List[ProtocolVersion] = None):
        self.supported_versions = supported_versions or [ProtocolVersion.V2_0]
    
    def validate_request(self, request: JsonRpcRequest) -> bool:
        """Validate JSON-RPC request"""
        try:
            # Basic validation is handled by Pydantic
            
            # Check version compatibility
            if request.jsonrpc not in [v.value for v in self.supported_versions]:
                raise ProtocolError(
                    code=ErrorCode.INVALID_REQUEST.value,
                    message=f"Unsupported protocol version: {request.jsonrpc}"
                )
            
            # Validate method name format
            if not request.method or not isinstance(request.method, str):
                raise ProtocolError(
                    code=ErrorCode.INVALID_REQUEST.value,
                    message="Method must be a non-empty string"
                )
            
            # Validate parameters
            if request.params is not None:
                if not isinstance(request.params, (dict, list)):
                    raise ProtocolError(
                        code=ErrorCode.INVALID_PARAMS.value,
                        message="Parameters must be an object or array"
                    )
            
            return True
            
        except ProtocolError:
            raise
        except Exception as e:
            raise ProtocolError(
                code=ErrorCode.VALIDATION_ERROR.value,
                message=f"Validation error: {str(e)}"
            )
    
    def validate_response(self, response: JsonRpcResponse) -> bool:
        """Validate JSON-RPC response"""
        try:
            # Basic validation is handled by Pydantic
            response.validate_response()
            return True
            
        except Exception as e:
            raise ProtocolError(
                code=ErrorCode.VALIDATION_ERROR.value,
                message=f"Response validation error: {str(e)}"
            )


# Global protocol handler instance
_protocol_handler: Optional[ProtocolHandler] = None


def get_protocol_handler() -> ProtocolHandler:
    """Get the global protocol handler instance"""
    global _protocol_handler
    if _protocol_handler is None:
        _protocol_handler = ProtocolHandler()
    return _protocol_handler


def reset_protocol_handler():
    """Reset the global protocol handler"""
    global _protocol_handler
    _protocol_handler = None


# Utility functions for common protocol operations
def create_request(method: str, params: Optional[Union[Dict, List]] = None, 
                  request_id: Optional[str] = None, **kwargs) -> JsonRpcRequest:
    """Create a JSON-RPC request"""
    return JsonRpcRequest(
        method=method,
        params=params,
        id=request_id or str(uuid.uuid4()),
        **kwargs
    )


def create_notification(method: str, params: Optional[Union[Dict, List]] = None, 
                       **kwargs) -> JsonRpcRequest:
    """Create a JSON-RPC notification (no id)"""
    return JsonRpcRequest(
        method=method,
        params=params,
        id=None,
        **kwargs
    )


def create_success_response(result: Any, request_id: Union[str, int], 
                          **kwargs) -> JsonRpcResponse:
    """Create a successful JSON-RPC response"""
    return JsonRpcResponse(
        result=result,
        id=request_id,
        **kwargs
    )


def create_error_response(error: ProtocolError, request_id: Optional[Union[str, int]] = None, 
                         **kwargs) -> JsonRpcResponse:
    """Create an error JSON-RPC response"""
    return JsonRpcResponse(
        error=error.to_dict(),
        id=request_id,
        **kwargs
    )
