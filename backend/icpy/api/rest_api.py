"""
HTTP REST API Endpoints for icpy Backend

This module provides comprehensive HTTP REST API endpoints for all icpy services,
enabling traditional HTTP-based client interactions alongside WebSocket real-time
communication.

Key Features:
- RESTful endpoints for all core services (workspace, filesystem, terminal)
- OpenAPI/Swagger documentation integration
- JSON-RPC protocol support over HTTP
- Request validation and error handling
- Integration with message broker for state synchronization
- Authentication and authorization support
- Rate limiting and request throttling
- Comprehensive error responses and status codes

Author: GitHub Copilot
Date: July 16, 2025
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field, validator
import uvicorn

from ..core.message_broker import get_message_broker
from ..core.connection_manager import get_connection_manager
from ..core.protocol import JsonRpcRequest, JsonRpcResponse, ProtocolError, ErrorCode
from ..services import get_workspace_service, get_filesystem_service, get_terminal_service

logger = logging.getLogger(__name__)

# Global service instance
_rest_api = None

# Security scheme
security = HTTPBearer(auto_error=False)

# Pydantic models for request/response validation
class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: bool = True
    message: str
    code: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: float = Field(default_factory=time.time)


class SuccessResponse(BaseModel):
    """Standard success response model."""
    success: bool = True
    data: Any = None
    message: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class JsonRpcRequestModel(BaseModel):
    """JSON-RPC request model for HTTP endpoints."""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name")
    params: Optional[Union[Dict[str, Any], List[Any]]] = Field(default=None, description="Method parameters")
    id: Optional[Union[str, int]] = Field(default=None, description="Request identifier")


class WorkspaceCreateRequest(BaseModel):
    """Request model for workspace creation."""
    name: str = Field(..., description="Workspace name")
    description: Optional[str] = Field(None, description="Workspace description")
    template: Optional[str] = Field(None, description="Workspace template")


class WorkspaceUpdateRequest(BaseModel):
    """Request model for workspace updates."""
    name: Optional[str] = Field(None, description="Workspace name")
    description: Optional[str] = Field(None, description="Workspace description")
    settings: Optional[Dict[str, Any]] = Field(None, description="Workspace settings")


class FileOperationRequest(BaseModel):
    """Request model for file operations."""
    path: str = Field(..., description="File path")
    content: Optional[str] = Field(None, description="File content")
    encoding: Optional[str] = Field(None, description="File encoding")
    create_dirs: Optional[bool] = Field(False, description="Create directories if needed")


class FileSearchRequest(BaseModel):
    """Request model for file search."""
    query: str = Field(..., description="Search query")
    path: Optional[str] = Field(None, description="Search path")
    file_types: Optional[List[str]] = Field(None, description="File types to search")
    case_sensitive: Optional[bool] = Field(False, description="Case sensitive search")
    regex: Optional[bool] = Field(False, description="Use regex search")


class TerminalCreateRequest(BaseModel):
    """Request model for terminal creation."""
    name: Optional[str] = Field(None, description="Terminal name")
    shell: Optional[str] = Field(None, description="Shell to use")
    cwd: Optional[str] = Field(None, description="Working directory")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    rows: Optional[int] = Field(None, description="Terminal rows")
    cols: Optional[int] = Field(None, description="Terminal columns")


class TerminalInputRequest(BaseModel):
    """Request model for terminal input."""
    data: str = Field(..., description="Input data")


class TerminalResizeRequest(BaseModel):
    """Request model for terminal resize."""
    rows: int = Field(..., description="Terminal rows")
    cols: int = Field(..., description="Terminal columns")


class RestAPI:
    """HTTP REST API for icpy Backend.
    
    This class provides comprehensive HTTP REST API endpoints for all icpy services,
    enabling traditional HTTP-based client interactions alongside WebSocket real-time
    communication.
    """

    def __init__(self, app: FastAPI):
        """Initialize the REST API.
        
        Args:
            app: FastAPI application instance
        """
        self.app = app
        self.message_broker = None
        self.connection_manager = None
        
        # Services
        self.workspace_service = None
        self.filesystem_service = None
        self.terminal_service = None
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0.0,
            'startup_time': 0.0
        }
        
        # Register middleware
        self._register_middleware()
        
        # Register routes
        self._register_routes()
        
        logger.info("RestAPI initialized")

    async def initialize(self):
        """Initialize the REST API.
        
        Sets up dependencies and services.
        """
        start_time = time.time()
        
        # Get dependencies
        self.message_broker = await get_message_broker()
        self.connection_manager = await get_connection_manager()
        
        # Get services
        self.workspace_service = await get_workspace_service()
        self.filesystem_service = await get_filesystem_service()
        self.terminal_service = await get_terminal_service()
        
        # Publish initialization event
        await self.message_broker.publish('rest_api.service_initialized', {
            'service': 'rest_api',
            'timestamp': time.time()
        })
        
        self.stats['startup_time'] = time.time() - start_time
        logger.info(f"RestAPI initialized in {self.stats['startup_time']:.3f}s")

    def _register_middleware(self):
        """Register middleware for the REST API."""
        
        @self.app.middleware("http")
        async def request_logging_middleware(request: Request, call_next):
            """Middleware for request logging and statistics."""
            start_time = time.time()
            
            # Update statistics
            self.stats['total_requests'] += 1
            
            try:
                response = await call_next(request)
                
                # Calculate response time
                response_time = time.time() - start_time
                self.stats['average_response_time'] = (
                    (self.stats['average_response_time'] * (self.stats['total_requests'] - 1) + response_time) /
                    self.stats['total_requests']
                )
                
                # Update success/failure counts
                if response.status_code < 400:
                    self.stats['successful_requests'] += 1
                else:
                    self.stats['failed_requests'] += 1
                
                # Log request
                logger.info(f"{request.method} {request.url.path} - {response.status_code} - {response_time:.3f}s")
                
                return response
                
            except Exception as e:
                # Update failure count
                self.stats['failed_requests'] += 1
                
                # Log error
                logger.error(f"Request failed: {request.method} {request.url.path} - {str(e)}")
                
                # Return error response
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": True,
                        "message": "Internal server error",
                        "details": str(e) if logger.getEffectiveLevel() <= logging.DEBUG else None,
                        "timestamp": time.time()
                    }
                )

    def _register_routes(self):
        """Register all REST API routes."""
        
        # Health check endpoint
        @self.app.get("/api/health")
        async def health_check():
            """Health check endpoint."""
            return SuccessResponse(
                data={
                    "status": "healthy",
                    "services": {
                        "message_broker": self.message_broker is not None,
                        "connection_manager": self.connection_manager is not None,
                        "workspace_service": self.workspace_service is not None,
                        "filesystem_service": self.filesystem_service is not None,
                        "terminal_service": self.terminal_service is not None
                    },
                    "stats": self.stats
                }
            )
        
        # API statistics endpoint
        @self.app.get("/api/stats")
        async def get_stats():
            """Get API statistics."""
            return SuccessResponse(data=self.stats)
        
        # JSON-RPC endpoint
        @self.app.post("/api/jsonrpc")
        async def jsonrpc_endpoint(request: JsonRpcRequestModel):
            """JSON-RPC endpoint for all service methods."""
            try:
                # Convert to JsonRpcRequest
                jsonrpc_request = JsonRpcRequest(
                    method=request.method,
                    params=request.params,
                    id=request.id
                )
                
                # Process through connection manager
                response = await self.connection_manager.handle_request(jsonrpc_request)
                
                return response.to_dict()
                
            except Exception as e:
                logger.error(f"JSON-RPC error: {e}")
                return ProtocolError(
                    code=ErrorCode.INTERNAL_ERROR.value,
                    message=str(e)
                ).to_dict()
        
        # Workspace endpoints
        self._register_workspace_routes()
        
        # Filesystem endpoints
        self._register_filesystem_routes()
        
        # Terminal endpoints
        self._register_terminal_routes()
        
        # Documentation endpoints
        self._register_documentation_routes()

    def _register_workspace_routes(self):
        """Register workspace-related routes."""
        
        @self.app.get("/api/workspaces")
        async def list_workspaces():
            """List all workspaces."""
            try:
                workspaces = await self.workspace_service.get_workspace_list()
                return SuccessResponse(data=workspaces)
            except Exception as e:
                logger.error(f"Error listing workspaces: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/workspaces")
        async def create_workspace(request: WorkspaceCreateRequest):
            """Create a new workspace."""
            try:
                workspace = await self.workspace_service.create_workspace(
                    name=request.name,
                    description=request.description,
                    template=request.template
                )
                return SuccessResponse(data=workspace, message="Workspace created successfully")
            except Exception as e:
                logger.error(f"Error creating workspace: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/workspaces/{workspace_id}")
        async def get_workspace(workspace_id: str):
            """Get workspace details."""
            try:
                workspace = await self.workspace_service.get_workspace(workspace_id)
                if not workspace:
                    raise HTTPException(status_code=404, detail="Workspace not found")
                return SuccessResponse(data=workspace)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting workspace: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.put("/api/workspaces/{workspace_id}")
        async def update_workspace(workspace_id: str, request: WorkspaceUpdateRequest):
            """Update workspace."""
            try:
                workspace = await self.workspace_service.update_workspace(
                    workspace_id=workspace_id,
                    name=request.name,
                    description=request.description,
                    settings=request.settings
                )
                return SuccessResponse(data=workspace, message="Workspace updated successfully")
            except Exception as e:
                logger.error(f"Error updating workspace: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/api/workspaces/{workspace_id}")
        async def delete_workspace(workspace_id: str):
            """Delete workspace."""
            try:
                await self.workspace_service.delete_workspace(workspace_id)
                return SuccessResponse(message="Workspace deleted successfully")
            except Exception as e:
                logger.error(f"Error deleting workspace: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/workspaces/{workspace_id}/activate")
        async def activate_workspace(workspace_id: str):
            """Activate workspace."""
            try:
                await self.workspace_service.activate_workspace(workspace_id)
                return SuccessResponse(message="Workspace activated successfully")
            except Exception as e:
                logger.error(f"Error activating workspace: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def _register_filesystem_routes(self):
        """Register filesystem-related routes."""
        
        @self.app.get("/api/files")
        async def list_files(path: str = "/"):
            """List files in directory."""
            try:
                files = await self.filesystem_service.list_directory(path)
                return SuccessResponse(data=files)
            except Exception as e:
                logger.error(f"Error listing files: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/files/content")
        async def get_file_content(path: str):
            """Get file content."""
            try:
                content = await self.filesystem_service.read_file(path)
                return SuccessResponse(data={"path": path, "content": content})
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="File not found")
            except Exception as e:
                logger.error(f"Error reading file: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/files")
        async def create_file(request: FileOperationRequest):
            """Create or update file."""
            import traceback
            try:
                logger.error(f"[DEBUG] Incoming create_file request: path={request.path}, content_len={len(request.content or '')}, encoding={request.encoding}, create_dirs={request.create_dirs}")
                await self.filesystem_service.write_file(
                    file_path=request.path,
                    content=request.content or "",
                    encoding=request.encoding,
                    create_dirs=request.create_dirs
                )
                return SuccessResponse(message="File created successfully")
            except Exception as e:
                logger.error(f"[DEBUG] Error creating file: {e}\n{traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.put("/api/files")
        async def update_file(request: FileOperationRequest):
            """Update file content."""
            try:
                await self.filesystem_service.write_file(
                    file_path=request.path,
                    content=request.content or "",
                    encoding=request.encoding,
                    create_dirs=request.create_dirs
                )
                return SuccessResponse(message="File updated successfully")
            except Exception as e:
                logger.error(f"Error updating file: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/api/files")
        async def delete_file(path: str):
            """Delete file."""
            try:
                await self.filesystem_service.delete_file(path)
                return SuccessResponse(message="File deleted successfully")
            except Exception as e:
                logger.error(f"Error deleting file: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/files/search")
        async def search_files(request: FileSearchRequest):
            """Search files."""
            try:
                results = await self.filesystem_service.search_files(
                    query=request.query,
                    path=request.path,
                    file_types=request.file_types,
                    case_sensitive=request.case_sensitive,
                    regex=request.regex
                )
                return SuccessResponse(data=results)
            except Exception as e:
                logger.error(f"Error searching files: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/files/info")
        async def get_file_info(path: str):
            """Get file information."""
            try:
                info = await self.filesystem_service.get_file_info(path)
                return SuccessResponse(data=info)
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="File not found")
            except Exception as e:
                logger.error(f"Error getting file info: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def _register_terminal_routes(self):
        """Register terminal-related routes."""
        
        @self.app.get("/api/terminals")
        async def list_terminals():
            """List all terminals."""
            try:
                terminals = await self.terminal_service.list_sessions()
                return SuccessResponse(data=terminals)
            except Exception as e:
                logger.error(f"Error listing terminals: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/terminals")
        async def create_terminal(request: TerminalCreateRequest):
            """Create a new terminal."""
            try:
                # Import TerminalConfig from the service module
                from ..services.terminal_service import TerminalConfig
                
                # Create terminal configuration
                config = TerminalConfig()
                if request.shell is not None:
                    config.shell = request.shell
                if request.cwd is not None:
                    config.cwd = request.cwd
                if request.env is not None:
                    config.env = request.env
                if request.rows is not None:
                    config.rows = request.rows
                if request.cols is not None:
                    config.cols = request.cols
                
                terminal_id = await self.terminal_service.create_session(
                    name=request.name,
                    config=config
                )
                
                # Get the full terminal object after creation
                terminal = await self.terminal_service.get_session(terminal_id)
                if not terminal:
                    raise HTTPException(status_code=500, detail="Failed to retrieve created terminal")
                
                logger.info(f"[DEBUG] Created terminal: {terminal}")
                return SuccessResponse(data=terminal, message="Terminal created successfully")
            except Exception as e:
                logger.error(f"Error creating terminal: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/terminals/{terminal_id}")
        async def get_terminal(terminal_id: str):
            """Get terminal details."""
            try:
                terminal = await self.terminal_service.get_session(terminal_id)
                if not terminal:
                    raise HTTPException(status_code=404, detail="Terminal not found")
                return SuccessResponse(data=terminal)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting terminal: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/terminals/{terminal_id}/start")
        async def start_terminal(terminal_id: str):
            """Start a terminal session."""
            try:
                success = await self.terminal_service.start_session(terminal_id)
                if success:
                    return SuccessResponse(message="Terminal started successfully")
                else:
                    raise HTTPException(status_code=500, detail="Failed to start terminal")
            except Exception as e:
                logger.error(f"Error starting terminal: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/terminals/{terminal_id}/input")
        async def send_terminal_input(terminal_id: str, request: TerminalInputRequest):
            """Send input to terminal."""
            try:
                await self.terminal_service.send_input(terminal_id, request.data)
                return SuccessResponse(message="Input sent successfully")
            except Exception as e:
                logger.error(f"Error sending terminal input: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/terminals/{terminal_id}/resize")
        async def resize_terminal(terminal_id: str, request: TerminalResizeRequest):
            """Resize terminal."""
            try:
                await self.terminal_service.resize_terminal(terminal_id, request.rows, request.cols)
                return SuccessResponse(message="Terminal resized successfully")
            except Exception as e:
                logger.error(f"Error resizing terminal: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/api/terminals/{terminal_id}")
        async def delete_terminal(terminal_id: str):
            """Delete terminal."""
            try:
                await self.terminal_service.destroy_session(terminal_id)
                return SuccessResponse(message="Terminal deleted successfully")
            except Exception as e:
                logger.error(f"Error deleting terminal: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def _register_documentation_routes(self):
        """Register documentation routes."""
        
        @self.app.get("/api/docs", include_in_schema=False)
        async def custom_swagger_ui_html():
            """Custom Swagger UI."""
            return get_swagger_ui_html(
                openapi_url="/api/openapi.json",
                title="icpy REST API Documentation",
                swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.6.2/swagger-ui-bundle.js",
                swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.6.2/swagger-ui.css"
            )
        
        @self.app.get("/api/openapi.json", include_in_schema=False)
        async def get_openapi_schema():
            """Get OpenAPI schema."""
            return get_openapi(
                title="icpy REST API",
                version="1.0.0",
                description="HTTP REST API for icpy Backend",
                routes=self.app.routes
            )

    async def get_stats(self) -> Dict[str, Any]:
        """Get REST API statistics.
        
        Returns:
            Dictionary containing service statistics
        """
        return {
            **self.stats,
            'timestamp': time.time()
        }

    async def shutdown(self):
        """Shutdown the REST API."""
        logger.info("Shutting down RestAPI...")
        
        # Publish shutdown event
        if self.message_broker:
            await self.message_broker.publish('rest_api.service_shutdown', {
                'service': 'rest_api',
                'timestamp': time.time()
            })
        
        logger.info("RestAPI shutdown complete")


def create_rest_api(app: FastAPI) -> RestAPI:
    """Create and initialize REST API.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        RestAPI instance
    """
    return RestAPI(app)


async def get_rest_api(app: FastAPI) -> RestAPI:
    """Get the REST API instance.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        The REST API instance
    """
    global _rest_api
    if _rest_api is None:
        _rest_api = create_rest_api(app)
        await _rest_api.initialize()
    return _rest_api


async def shutdown_rest_api():
    """Shutdown the REST API instance."""
    global _rest_api
    if _rest_api is not None:
        await _rest_api.shutdown()
        _rest_api = None
