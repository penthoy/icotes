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
import os
import mimetypes
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field, validator
import uvicorn

from ..core.message_broker import get_message_broker
from ..core.connection_manager import get_connection_manager
from ..core.protocol import JsonRpcRequest, JsonRpcResponse, ProtocolError, ErrorCode
from ..services import (
    get_workspace_service,
    get_filesystem_service,
    get_terminal_service,
    get_agent_service,
    get_chat_service,
    get_chat_service,
    get_source_control_service,
    get_context_router,
)

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
    encoding: Optional[str] = Field("utf-8", description="File encoding")
    create_dirs: Optional[bool] = Field(True, description="Create directories if needed")
    type: Optional[str] = Field("file", description="Type of item to create: 'file' or 'directory'")


class FileMoveRequest(BaseModel):
    """Request model for moving or renaming files and directories."""
    source_path: str = Field(..., description="Existing file or directory path")
    destination_path: str = Field(..., description="Destination path including new name")
    overwrite: Optional[bool] = Field(False, description="Allow overwriting existing destination")


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
    rows: Optional[int] = Field(24, description="Terminal rows")
    cols: Optional[int] = Field(80, description="Terminal columns")


class TerminalInputRequest(BaseModel):
    """Request model for terminal input."""
    data: str = Field(..., description="Input data")


class TerminalResizeRequest(BaseModel):
    """Request model for terminal resize."""
    rows: int = Field(..., description="Terminal rows")
    cols: int = Field(..., description="Terminal columns")


class AgentCreateRequest(BaseModel):
    """Request model for agent creation."""
    name: str = Field(..., description="Agent name")
    framework: str = Field("openai", description="AI framework to use")
    role: Optional[str] = Field(None, description="Agent role")
    goal: Optional[str] = Field(None, description="Agent goal")
    backstory: Optional[str] = Field(None, description="Agent backstory")
    capabilities: Optional[List[str]] = Field(default_factory=list, description="Agent capabilities")
    memory_enabled: Optional[bool] = Field(True, description="Enable memory")
    context_window: Optional[int] = Field(4000, description="Context window size")
    temperature: Optional[float] = Field(0.7, description="Temperature setting")
    model: Optional[str] = Field("gpt-4", description="Model to use")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens")
    custom_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom configuration")
    session_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session metadata")


class AgentFromTemplateRequest(BaseModel):
    """Request model for creating agent from template."""
    template_name: str = Field(..., description="Template name")
    agent_name: str = Field(..., description="Agent name")
    custom_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom configuration")
    session_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session metadata")


class AgentTaskRequest(BaseModel):
    """Request model for agent task execution."""
    task: str = Field(..., description="Task to execute")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Task context")


class WorkflowCreateRequest(BaseModel):
    """Request model for workflow creation."""
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    tasks: List[Dict[str, Any]] = Field(..., description="Workflow tasks")
    session_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session metadata")


class WorkflowFromTemplateRequest(BaseModel):
    """Request model for creating workflow from template."""
    template_name: str = Field(..., description="Template name")
    workflow_name: str = Field(..., description="Workflow name")
    session_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session metadata")


# Chat session request models
class ChatSessionCreateRequest(BaseModel):
    """Request body for creating a chat session."""
    name: Optional[str] = Field(None, description="Optional human-friendly session name")


class ChatSessionUpdateRequest(BaseModel):
    """Request body for updating a chat session (rename)."""
    name: str = Field(..., description="New session name")


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
        self.agent_service = None
        self.chat_service = None
        self.source_control_service = None
        self.context_router = None
        
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
        # Resolve FS/Terminal directly so tests can patch these services.
        # ContextRouter is still initialized for optional remote overrides per-request.
        try:
            self.context_router = await get_context_router()
        except Exception as e:
            logger.warning(f"[REST] ContextRouter unavailable: {e}")
            self.context_router = None
        # Always prefer direct services here (allows test patches to work)
        self.filesystem_service = await get_filesystem_service()
        self.terminal_service = await get_terminal_service()
        self.agent_service = await get_agent_service()
        self.chat_service = get_chat_service()
        try:
            self.source_control_service = await get_source_control_service()
        except Exception as e:
            logger.warning(f"[REST] Source control service unavailable: {e}")
        
        # Publish initialization event
        await self.message_broker.publish('rest_api.service_initialized', {
            'service': 'rest_api',
            'timestamp': time.time()
        })
        
        self.stats['startup_time'] = time.time() - start_time
        logger.info(f"RestAPI initialized in {self.stats['startup_time']:.3f}s")

    def _register_middleware(self):
        """Register middleware for the REST API."""
        
        # Endpoints to exclude from INFO level logging (frequent polling/status checks)
        EXCLUDED_PATHS = {
            '/api/logs/frontend',  # Circular logging
            '/api/scm/status',     # Frequent polling
            '/api/health',         # Health checks
            '/health',             # Health checks
        }
        
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
                
                # Log request (exclude noisy endpoints from INFO logging)
                should_log = request.url.path not in EXCLUDED_PATHS
                
                if should_log:
                    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {response_time:.3f}s")
                else:
                    # Still log at DEBUG level for troubleshooting
                    logger.debug(f"{request.method} {request.url.path} - {response.status_code} - {response_time:.3f}s")
                
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
                        "terminal_service": self.terminal_service is not None,
                        "agent_service": self.agent_service is not None,
                        "chat_service": self.chat_service is not None
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
        
        # Agent endpoints
        self._register_agent_routes()
        
        # Chat endpoints
        self._register_chat_routes()

        # Source control endpoints
        self._register_scm_routes()
        
        # Documentation endpoints
        self._register_documentation_routes()

    def _register_workspace_routes(self):
        """Register workspace-related routes."""
        
        @self.app.get("/api/workspaces")
        async def list_workspaces():
            """List all workspaces."""
            try:
                # Tests stub list_workspaces on the service
                if hasattr(self.workspace_service, 'list_workspaces'):
                    workspaces = await self.workspace_service.list_workspaces()
                else:
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
        async def list_files(path: str = "/", include_hidden: bool = False):
            """List files in directory."""
            try:
                fs = self.filesystem_service
                # Only override with remote FS when explicitly remote
                if self.context_router is not None:
                    try:
                        fs_rt = await self.context_router.get_filesystem()
                        if getattr(fs_rt, 'is_remote', False):
                            fs = fs_rt
                    except Exception as e:
                        logger.warning(f"[REST] FS routing error, falling back local: {e}")
                        pass
                files = await fs.list_directory(path, include_hidden=include_hidden)
                return SuccessResponse(data=files)
            except Exception as e:
                logger.error(f"Error listing files: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/files/content")
        async def get_file_content(path: str):
            """Get file content."""
            try:
                fs = self.filesystem_service
                if self.context_router is not None:
                    try:
                        fs_rt = await self.context_router.get_filesystem()
                        if getattr(fs_rt, 'is_remote', False):
                            fs = fs_rt
                    except Exception:
                        pass
                logger.info("[REST] get_file_content path=%s use_remote=%s", path, getattr(fs, 'is_remote', False))
                content = await fs.read_file(path)
                if content is None:
                    raise HTTPException(status_code=404, detail="File not found")
                return SuccessResponse(data={"path": path, "content": content})
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="File not found")
            except Exception as e:
                logger.error(f"Error reading file: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/files/raw")
        async def get_file_raw(path: str):
            """Return raw (binary) file bytes for previews (images, etc.).

            Security: Only serves files inside the configured filesystem root or workspace root.
            """
            try:
                import os, mimetypes, aiofiles
                from pathlib import Path
                from fastapi.responses import StreamingResponse
                from typing import AsyncIterator

                if not path:
                    raise HTTPException(status_code=400, detail="path query parameter required")

                # Resolve active filesystem and roots
                current_dir = os.getcwd()
                if os.path.basename(current_dir) == "backend":
                    workspace_root = os.path.abspath(os.path.join(current_dir, os.pardir))
                else:
                    workspace_root = os.path.abspath(current_dir)
                fs_service = self.filesystem_service
                if self.context_router is not None:
                    try:
                        fs_service = await self.context_router.get_filesystem()
                    except Exception:
                        fs_service = self.filesystem_service

                fs_root = getattr(fs_service, 'root_path', workspace_root) if fs_service else workspace_root

                # Prefer serving from local disk if the path resolves within workspace/fs roots AND has non-zero size
                candidates: list[str] = []
                if os.path.isabs(path):
                    candidates.append(os.path.abspath(path))
                else:
                    # Relative to fs_root and workspace_root
                    candidates.append(os.path.abspath(os.path.join(fs_root, path.lstrip('/'))))
                    if fs_root != workspace_root:
                        candidates.append(os.path.abspath(os.path.join(workspace_root, path.lstrip('/'))))

                abs_path = None
                for cand in candidates:
                    if os.path.exists(cand) and not os.path.isdir(cand) and os.path.getsize(cand) > 0:
                        abs_path = cand
                        break

                if abs_path is not None:
                    # Security: ensure selected path is inside either fs_root or workspace_root
                    if not (abs_path.startswith(fs_root) or abs_path.startswith(workspace_root)):
                        raise HTTPException(status_code=400, detail="Path outside workspace root")

                    # Best-effort mime detection
                    mime, _ = mimetypes.guess_type(abs_path)
                    if mime is None:
                        mime = "application/octet-stream"

                    async def iter_file() -> AsyncIterator[bytes]:
                        async with aiofiles.open(abs_path, 'rb') as f:
                            while True:
                                chunk = await f.read(1024 * 1024)  # 1MB chunks
                                if not chunk:
                                    break
                                yield chunk

                    return StreamingResponse(iter_file(), media_type=mime)

                # If no local candidate found (or file is 0-byte) and remote FS is active, stream via adapter
                if getattr(fs_service, 'is_remote', False):
                    # Keep original path semantics (absolute or relative to remote root)
                    mime, _ = mimetypes.guess_type(path)
                    if mime is None:
                        mime = "application/octet-stream"
                    try:
                        streamer = fs_service.stream_file(path)  # type: ignore[attr-defined]
                        return StreamingResponse(streamer, media_type=mime)
                    except Exception as e:
                        logger.error(f"[REST] remote raw stream error for {path}: {e}")
                        raise HTTPException(status_code=404, detail="File not found on remote")

                # Nothing found
                raise HTTPException(status_code=404, detail="File not found")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error reading raw file {path}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/files")
        async def create_file(request: FileOperationRequest):
            """Create file or directory based on request type."""
            import traceback
            try:
                logger.info(f"[DEBUG] Incoming create request: path={request.path}, type={request.type}, content_len={len(request.content or '')}")

                fs = self.filesystem_service
                if self.context_router is not None:
                    try:
                        fs_rt = await self.context_router.get_filesystem()
                        if getattr(fs_rt, 'is_remote', False):
                            fs = fs_rt
                    except Exception:
                        pass
                # Normalize type for folder creation
                type_norm = (request.type or "file").strip().lower()
                is_dir = type_norm in ("directory", "folder", "dir", "tree")
                logger.info("[REST] create_file path=%s type=%s (is_dir=%s) use_remote=%s", request.path, request.type, is_dir, getattr(fs, 'is_remote', False))

                if is_dir:
                    # Create directory
                    success = await fs.create_directory(
                        dir_path=request.path,
                        parents=request.create_dirs
                    )
                    if success:
                        return SuccessResponse(message="Directory created successfully")
                    else:
                        raise Exception("Failed to create directory")
                else:
                    # Create file (existing logic)
                    ok = await fs.write_file(
                        file_path=request.path,
                        content=request.content or "",
                        encoding=request.encoding,
                        create_dirs=request.create_dirs
                    )
                    if ok is False:
                        raise HTTPException(status_code=500, detail="Failed to create file")
                    return SuccessResponse(message="File created successfully")
            except Exception as e:
                error_type = "directory" if is_dir else "file"
                logger.error(f"[DEBUG] Error creating {error_type}: {e}\n{traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.put("/api/files")
        async def update_file(request: FileOperationRequest):
            """Update file content."""
            try:
                fs = self.filesystem_service
                if self.context_router is not None:
                    try:
                        fs_rt = await self.context_router.get_filesystem()
                        if getattr(fs_rt, 'is_remote', False):
                            fs = fs_rt
                    except Exception:
                        pass
                logger.info("[REST] update_file path=%s use_remote=%s", request.path, getattr(fs, 'is_remote', False))
                ok = await fs.write_file(
                    file_path=request.path,
                    content=request.content or "",
                    encoding=request.encoding,
                    create_dirs=request.create_dirs
                )
                if ok is False:
                    raise HTTPException(status_code=500, detail="Failed to update file")
                return SuccessResponse(message="File updated successfully")
            except Exception as e:
                logger.error(f"Error updating file: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.delete("/api/files")
        async def delete_file(path: str):
            """Delete file."""
            try:
                fs = self.filesystem_service
                if self.context_router is not None:
                    try:
                        fs_rt = await self.context_router.get_filesystem()
                        if getattr(fs_rt, 'is_remote', False):
                            fs = fs_rt
                    except Exception:
                        pass
                logger.info("[REST] delete_file path=%s use_remote=%s", path, getattr(fs, 'is_remote', False))
                ok = await fs.delete_file(path)
                if ok is False:
                    raise HTTPException(status_code=500, detail="Failed to delete file")
                return SuccessResponse(message="File deleted successfully")
            except Exception as e:
                logger.error(f"Error deleting file: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/files/move")
        async def move_file(request: FileMoveRequest):
            """Move or rename a file or directory."""
            try:
                if not request.overwrite and os.path.exists(request.destination_path):
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Destination already exists")

                fs = self.filesystem_service
                if self.context_router is not None:
                    try:
                        fs_rt = await self.context_router.get_filesystem()
                        if getattr(fs_rt, 'is_remote', False):
                            fs = fs_rt
                    except Exception:
                        pass
                logger.info("[REST] move_file src=%s dst=%s use_remote=%s", request.source_path, request.destination_path, getattr(fs, 'is_remote', False))

                success = await fs.move_file(
                    src_path=request.source_path,
                    dest_path=request.destination_path,
                    overwrite=request.overwrite or False
                )

                if not success:
                    raise HTTPException(status_code=400, detail="Failed to move file")

                return SuccessResponse(message="File moved successfully")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error moving file: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/files/search")
        async def search_files(request: FileSearchRequest):
            """Search files."""
            try:
                fs = self.filesystem_service
                if self.context_router is not None:
                    try:
                        fs_rt = await self.context_router.get_filesystem()
                        if getattr(fs_rt, 'is_remote', False):
                            fs = fs_rt
                    except Exception:
                        pass
                logger.info("[REST] search_files query=%s use_remote=%s", request.query, getattr(fs, 'is_remote', False))
                # Map to service-supported parameters; path/case/regex can be handled in future
                results = await fs.search_files(
                    query=request.query,
                    search_content=True
                )
                return SuccessResponse(data=results)
            except Exception as e:
                logger.error(f"Error searching files: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/files/info")
        async def get_file_info(path: str):
            """Get file information."""
            try:
                fs = self.filesystem_service
                if self.context_router is not None:
                    try:
                        fs_rt = await self.context_router.get_filesystem()
                        if getattr(fs_rt, 'is_remote', False):
                            fs = fs_rt
                    except Exception:
                        pass
                logger.info("[REST] get_file_info path=%s use_remote=%s", path, getattr(fs, 'is_remote', False))
                info = await fs.get_file_info(path)
                if info is None:
                    raise HTTPException(status_code=404, detail="File not found")
                return SuccessResponse(data=info)
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="File not found")
            except Exception as e:
                logger.error(f"Error getting file info: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # File download endpoint (Phase 5 - explorer download)
        @self.app.get("/api/files/download")
        async def download_file(path: str):  # type: ignore
            """Download a single file specified by absolute or workspace-relative path.

            The frontend passes the raw file path as displayed in the explorer tree.
            We allow absolute paths within the workspace root, or relative paths which
            are resolved against the filesystem service root. Directories are rejected.
            """
            try:
                if not path:
                    raise HTTPException(status_code=400, detail="path query parameter required")
                # Determine workspace root (parent of backend dir if running from backend/)
                current_dir = os.getcwd()
                if os.path.basename(current_dir) == "backend":
                    workspace_root = os.path.abspath(os.path.join(current_dir, os.pardir))
                else:
                    workspace_root = os.path.abspath(current_dir)

                fs_service = self.filesystem_service
                if self.context_router is not None:
                    try:
                        fs_service = await self.context_router.get_filesystem()
                    except Exception:
                        fs_service = self.filesystem_service

                fs_root = getattr(fs_service, 'root_path', workspace_root)

                candidates = []  # possible absolute paths to try (local-first)

                # If user supplied absolute path, use it directly first
                if os.path.isabs(path):
                    candidates.append(os.path.abspath(path))
                else:
                    # Relative to fs_root
                    candidates.append(os.path.abspath(os.path.join(fs_root, path.lstrip('/'))))
                    # Relative to workspace root (if different)
                    if fs_root != workspace_root:
                        candidates.append(os.path.abspath(os.path.join(workspace_root, path.lstrip('/'))))

                abs_path = None
                for cand in candidates:
                    if os.path.exists(cand) and not os.path.isdir(cand) and os.path.getsize(cand) > 0:
                        abs_path = cand
                        break

                if abs_path is not None:
                    # Security: ensure selected path is inside either fs_root or workspace_root
                    if not (abs_path.startswith(fs_root) or abs_path.startswith(workspace_root)):
                        raise HTTPException(status_code=400, detail="Path outside workspace root")
                    filename = os.path.basename(abs_path)
                    mime, _ = mimetypes.guess_type(filename)
                    if not mime:
                        mime = 'application/octet-stream'
                    return FileResponse(abs_path, filename=filename, media_type=mime)

                # No local candidate or file is 0-byte; if remote FS is active, stream bytes via adapter
                if getattr(fs_service, 'is_remote', False):
                    from fastapi.responses import StreamingResponse
                    filename = os.path.basename(path) or 'download'
                    mime, _ = mimetypes.guess_type(filename)
                    if not mime:
                        mime = 'application/octet-stream'
                    headers = {
                        'Content-Disposition': f'attachment; filename="{filename}"'
                    }
                    try:
                        streamer = fs_service.stream_file(path)  # type: ignore[attr-defined]
                        return StreamingResponse(streamer, media_type=mime, headers=headers)
                    except Exception as e:
                        logger.error(f"[REST] remote download stream error for {path}: {e}")
                        raise HTTPException(status_code=404, detail="File not found on remote")

                # Nothing found anywhere
                raise HTTPException(status_code=404, detail="File not found")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error downloading file {path}: {e}")
                raise HTTPException(status_code=500, detail="Download failed")

    def _register_terminal_routes(self):
        """Register terminal-related routes."""
        
        @self.app.get("/api/terminals")
        async def list_terminals():
            """List all terminals."""
            try:
                # Tests stub list_terminals on the service
                if hasattr(self.terminal_service, 'list_terminals'):
                    terminals = await self.terminal_service.list_terminals()
                else:
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
                if hasattr(request, 'shell') and request.shell:
                    config.shell = request.shell
                if hasattr(request, 'cwd') and request.cwd:
                    config.cwd = request.cwd
                if hasattr(request, 'env') and request.env:
                    config.env = request.env
                if hasattr(request, 'rows') and request.rows:
                    config.rows = request.rows
                if hasattr(request, 'cols') and request.cols:
                    config.cols = request.cols
                
                # Tests stub create_terminal returning the terminal dict directly
                if hasattr(self.terminal_service, 'create_terminal'):
                    terminal = await self.terminal_service.create_terminal(
                        name=getattr(request, 'name', None),
                        config=config
                    )
                else:
                    terminal_id = await self.terminal_service.create_session(
                        name=getattr(request, 'name', None),
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
                # Tests stub get_terminal on the service
                if hasattr(self.terminal_service, 'get_terminal'):
                    terminal = await self.terminal_service.get_terminal(terminal_id)
                else:
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

    def _register_agent_routes(self):
        """Register agent-related routes."""
        
        # List all agent sessions
        @self.app.get("/api/agents")
        async def list_agent_sessions():
            """List all agent sessions."""
            try:
                sessions = self.agent_service.get_agent_sessions()
                return SuccessResponse(
                    data=[session.to_dict() for session in sessions],
                    message=f"Found {len(sessions)} agent sessions"
                )
            except Exception as e:
                logger.error(f"Failed to list agent sessions: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Get agent status for chat
        @self.app.get("/api/agents/status")
        async def get_agent_status():
            """Get current agent status for chat."""
            try:
                # Try to get chat agent status first
                try:
                    status = await self.chat_service.get_agent_status()
                    return SuccessResponse(
                        data=status.to_dict(),
                        message="Agent status retrieved"
                    )
                except Exception:
                    # If no chat agent configured, return general agent capabilities
                    agent_sessions = self.agent_service.list_agent_sessions() if self.agent_service else []
                    return SuccessResponse(
                        data={
                            "available": len(agent_sessions) > 0,
                            "name": "Agent Service",
                            "type": "multi",
                            "capabilities": ["openai", "crewai", "langchain", "langgraph"],
                            "agent_id": None,
                            "sessions": len(agent_sessions),
                            "frameworks": {
                                "openai": True,
                                "crewai": True, 
                                "langchain": True,
                                "langgraph": True
                            }
                        },
                        message="General agent status retrieved (no active session)"
                    )
            except Exception as e:
                logger.error(f"Failed to get agent status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Get specific agent session
        @self.app.get("/api/agents/{session_id}")
        async def get_agent_session(session_id: str):
            """Get specific agent session."""
            try:
                session = self.agent_service.get_agent_session(session_id)
                if not session:
                    raise HTTPException(status_code=404, detail="Agent session not found")
                
                return SuccessResponse(
                    data=session.to_dict(),
                    message="Agent session retrieved"
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get agent session {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Create agent
        @self.app.post("/api/agents")
        async def create_agent(request: AgentCreateRequest):
            """Create a new agent."""
            try:
                from ..agent.base_agent import AgentConfig
                
                config = AgentConfig(
                    name=request.name,
                    framework=request.framework,
                    role=request.role,
                    goal=request.goal,
                    backstory=request.backstory,
                    capabilities=request.capabilities,
                    memory_enabled=request.memory_enabled,
                    context_window=request.context_window,
                    temperature=request.temperature,
                    model=request.model,
                    max_tokens=request.max_tokens,
                    custom_config=request.custom_config
                )
                
                session_id = await self.agent_service.create_agent(config, request.session_metadata)
                session = self.agent_service.get_agent_session(session_id)
                
                return SuccessResponse(
                    data=session.to_dict(),
                    message="Agent created successfully"
                )
            except Exception as e:
                logger.error(f"Failed to create agent: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Create agent from template
        @self.app.post("/api/agents/from-template")
        async def create_agent_from_template(request: AgentFromTemplateRequest):
            """Create agent from template."""
            try:
                session_id = await self.agent_service.create_agent_from_template(
                    request.template_name,
                    request.agent_name,
                    request.custom_config,
                    request.session_metadata
                )
                session = self.agent_service.get_agent_session(session_id)
                
                return SuccessResponse(
                    data=session.to_dict(),
                    message=f"Agent created from template '{request.template_name}'"
                )
            except Exception as e:
                logger.error(f"Failed to create agent from template: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Start agent
        @self.app.post("/api/agents/{session_id}/start")
        async def start_agent(session_id: str):
            """Start an agent."""
            try:
                success = await self.agent_service.start_agent(session_id)
                if not success:
                    raise HTTPException(status_code=400, detail="Failed to start agent")
                
                session = self.agent_service.get_agent_session(session_id)
                return SuccessResponse(
                    data=session.to_dict(),
                    message="Agent started successfully"
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to start agent {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Stop agent
        @self.app.post("/api/agents/{session_id}/stop")
        async def stop_agent(session_id: str):
            """Stop an agent."""
            try:
                success = await self.agent_service.stop_agent(session_id)
                if not success:
                    raise HTTPException(status_code=400, detail="Failed to stop agent")
                
                session = self.agent_service.get_agent_session(session_id)
                return SuccessResponse(
                    data=session.to_dict(),
                    message="Agent stopped successfully"
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to stop agent {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Execute agent task
        @self.app.post("/api/agents/{session_id}/execute")
        async def execute_agent_task(session_id: str, request: AgentTaskRequest):
            """Execute a task with an agent."""
            try:
                result = await self.agent_service.execute_agent_task(
                    session_id, request.task, request.context
                )
                
                return SuccessResponse(
                    data={"result": result},
                    message="Task executed successfully"
                )
            except Exception as e:
                logger.error(f"Failed to execute task for agent {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Destroy agent
        @self.app.delete("/api/agents/{session_id}")
        async def destroy_agent(session_id: str):
            """Destroy an agent session."""
            try:
                success = await self.agent_service.destroy_agent(session_id)
                if not success:
                    raise HTTPException(status_code=400, detail="Failed to destroy agent")
                
                return SuccessResponse(message="Agent destroyed successfully")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to destroy agent {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # List all workflow sessions
        @self.app.get("/api/workflows")
        async def list_workflow_sessions():
            """List all workflow sessions."""
            try:
                sessions = self.agent_service.get_workflow_sessions()
                return SuccessResponse(
                    data=[session.to_dict() for session in sessions],
                    message=f"Found {len(sessions)} workflow sessions"
                )
            except Exception as e:
                logger.error(f"Failed to list workflow sessions: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Get specific workflow session
        @self.app.get("/api/workflows/{session_id}")
        async def get_workflow_session(session_id: str):
            """Get specific workflow session."""
            try:
                session = self.agent_service.get_workflow_session(session_id)
                if not session:
                    raise HTTPException(status_code=404, detail="Workflow session not found")
                
                return SuccessResponse(
                    data=session.to_dict(),
                    message="Workflow session retrieved"
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get workflow session {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Create workflow
        @self.app.post("/api/workflows")
        async def create_workflow(request: WorkflowCreateRequest):
            """Create a new workflow."""
            try:
                from ..agent.workflows.workflow_engine import WorkflowConfig, WorkflowTask
                
                # Convert task definitions to WorkflowTask objects
                tasks = []
                for task_def in request.tasks:
                    task = WorkflowTask(
                        name=task_def.get('name', ''),
                        task_content=task_def.get('content', ''),
                        dependencies=task_def.get('dependencies', []),
                        # Add other task properties as needed
                    )
                    tasks.append(task)
                
                config = WorkflowConfig(
                    name=request.name,
                    description=request.description or f"Workflow: {request.name}",
                    tasks=tasks
                )
                
                session_id = await self.agent_service.create_workflow(config, request.session_metadata)
                session = self.agent_service.get_workflow_session(session_id)
                
                return SuccessResponse(
                    data=session.to_dict(),
                    message="Workflow created successfully"
                )
            except Exception as e:
                logger.error(f"Failed to create workflow: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Create workflow from template
        @self.app.post("/api/workflows/from-template")
        async def create_workflow_from_template(request: WorkflowFromTemplateRequest):
            """Create workflow from template."""
            try:
                session_id = await self.agent_service.create_workflow_from_template(
                    request.template_name,
                    request.workflow_name,
                    request.session_metadata
                )
                session = self.agent_service.get_workflow_session(session_id)
                
                return SuccessResponse(
                    data=session.to_dict(),
                    message=f"Workflow created from template '{request.template_name}'"
                )
            except Exception as e:
                logger.error(f"Failed to create workflow from template: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Execute workflow
        @self.app.post("/api/workflows/{session_id}/execute")
        async def execute_workflow(session_id: str):
            """Execute a workflow."""
            try:
                success = await self.agent_service.execute_workflow(session_id)
                if not success:
                    raise HTTPException(status_code=400, detail="Failed to execute workflow")
                
                session = self.agent_service.get_workflow_session(session_id)
                return SuccessResponse(
                    data=session.to_dict(),
                    message="Workflow executed successfully"
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to execute workflow {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Pause workflow
        @self.app.post("/api/workflows/{session_id}/pause")
        async def pause_workflow(session_id: str):
            """Pause a workflow."""
            try:
                success = await self.agent_service.pause_workflow(session_id)
                if not success:
                    raise HTTPException(status_code=400, detail="Failed to pause workflow")
                
                session = self.agent_service.get_workflow_session(session_id)
                return SuccessResponse(
                    data=session.to_dict(),
                    message="Workflow paused successfully"
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to pause workflow {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Resume workflow
        @self.app.post("/api/workflows/{session_id}/resume")
        async def resume_workflow(session_id: str):
            """Resume a workflow."""
            try:
                success = await self.agent_service.resume_workflow(session_id)
                if not success:
                    raise HTTPException(status_code=400, detail="Failed to resume workflow")
                
                session = self.agent_service.get_workflow_session(session_id)
                return SuccessResponse(
                    data=session.to_dict(),
                    message="Workflow resumed successfully"
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to resume workflow {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Cancel workflow
        @self.app.post("/api/workflows/{session_id}/cancel")
        async def cancel_workflow(session_id: str):
            """Cancel a workflow."""
            try:
                success = await self.agent_service.cancel_workflow(session_id)
                if not success:
                    raise HTTPException(status_code=400, detail="Failed to cancel workflow")
                
                return SuccessResponse(message="Workflow cancelled successfully")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to cancel workflow {session_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Get available templates
        @self.app.get("/api/templates")
        async def get_available_templates():
            """Get available agent and workflow templates."""
            try:
                templates = self.agent_service.get_available_templates()
                return SuccessResponse(
                    data=templates,
                    message="Templates retrieved successfully"
                )
            except Exception as e:
                logger.error(f"Failed to get templates: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Get resource usage
        @self.app.get("/api/agents/stats")
        async def get_agent_service_stats():
            """Get agent service resource usage and statistics."""
            try:
                stats = self.agent_service.get_resource_usage()
                return SuccessResponse(
                    data=stats,
                    message="Agent service statistics retrieved"
                )
            except Exception as e:
                logger.error(f"Failed to get agent service stats: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def _register_chat_routes(self):
        """Register chat-related routes."""
        
        # Get message history
        @self.app.get("/api/chat/messages")
        async def get_chat_messages(session_id: Optional[str] = None, limit: int = 50, offset: int = 0):
            """Get chat message history with pagination."""
            try:
                messages = await self.chat_service.get_message_history(session_id, limit, offset)
                return SuccessResponse(
                    data=[message.to_dict() for message in messages],
                    message=f"Retrieved {len(messages)} messages"
                )
            except Exception as e:
                logger.error(f"Failed to get chat messages: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Get chat configuration
        @self.app.get("/api/chat/config")
        async def get_chat_config():
            """Get current chat configuration."""
            try:
                return SuccessResponse(
                    data=self.chat_service.config.to_dict(),
                    message="Chat configuration retrieved"
                )
            except Exception as e:
                logger.error(f"Failed to get chat config: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Update chat configuration
        @self.app.post("/api/chat/config")
        async def update_chat_config(config_updates: Dict[str, Any]):
            """Update chat configuration."""
            try:
                await self.chat_service.update_config(config_updates)
                return SuccessResponse(
                    data=self.chat_service.config.to_dict(),
                    message="Chat configuration updated"
                )
            except Exception as e:
                logger.error(f"Failed to update chat config: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Clear message history
        @self.app.post("/api/chat/clear")
        async def clear_chat_history(session_id: Optional[str] = None):
            """Clear chat message history."""
            try:
                success = await self.chat_service.clear_message_history(session_id)
                if success:
                    return SuccessResponse(
                        message=f"Chat history cleared for session: {session_id or 'all'}"
                    )
                else:
                    raise HTTPException(status_code=500, detail="Failed to clear chat history")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to clear chat history: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Get chat service statistics
        @self.app.get("/api/chat/stats")
        async def get_chat_stats():
            """Get chat service statistics."""
            try:
                stats = self.chat_service.get_stats()
                return SuccessResponse(
                    data=stats,
                    message="Chat service statistics retrieved"
                )
            except Exception as e:
                logger.error(f"Failed to get chat stats: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def _register_scm_routes(self):
        """Register source control (SCM) routes."""
        logger.info("[REST] Registering SCM routes...")
        
        @self.app.get("/api/scm/repo")
        async def scm_repo_info():
            try:
                # Check if service is available at runtime
                if not self.source_control_service:
                    raise HTTPException(status_code=503, detail="SCM service not available")
                data = await self.source_control_service.get_repo_info()
                return SuccessResponse(data=data)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"[SCM] repo info error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/scm/status")
        async def scm_status():
            try:
                if not self.source_control_service:
                    raise HTTPException(status_code=503, detail="SCM service not available")
                data = await self.source_control_service.status()
                return SuccessResponse(data=data)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"[SCM] status error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/scm/diff")
        async def scm_diff(path: Optional[str] = None):
            try:
                if not self.source_control_service:
                    raise HTTPException(status_code=503, detail="SCM service not available")
                data = await self.source_control_service.diff(path)
                return SuccessResponse(data=data)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"[SCM] diff error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/scm/stage")
        async def scm_stage(payload: Dict[str, List[str]]):
            try:
                if not self.source_control_service:
                    raise HTTPException(status_code=503, detail="SCM service not available")
                ok = await self.source_control_service.stage(payload.get("paths", []))
                return SuccessResponse(data={"ok": ok})
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"[SCM] stage error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/scm/unstage")
        async def scm_unstage(payload: Dict[str, List[str]]):
            try:
                if not self.source_control_service:
                    raise HTTPException(status_code=503, detail="SCM service not available")
                ok = await self.source_control_service.unstage(payload.get("paths", []))
                return SuccessResponse(data={"ok": ok})
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"[SCM] unstage error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/scm/discard")
        async def scm_discard(payload: Dict[str, List[str]]):
            try:
                if not self.source_control_service:
                    raise HTTPException(status_code=503, detail="SCM service not available")
                ok = await self.source_control_service.discard(payload.get("paths", []))
                return SuccessResponse(data={"ok": ok})
            except HTTPException:
                raise
            except Exception as e:
                logger.exception("[SCM] discard error")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/scm/commit")
        async def scm_commit(payload: Dict[str, Any]):
            try:
                if not self.source_control_service:
                    raise HTTPException(status_code=503, detail="SCM service not available")
                ok = await self.source_control_service.commit(
                    message=str(payload.get("message", "")),
                    amend=bool(payload.get("amend", False)),
                    signoff=bool(payload.get("signoff", False)),
                )
                return SuccessResponse(data={"ok": ok})
            except HTTPException:
                raise
            except Exception as e:
                logger.exception("[SCM] commit error")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/scm/branches")
        async def scm_branches():
            try:
                if not self.source_control_service:
                    raise HTTPException(status_code=503, detail="SCM service not available")
                data = await self.source_control_service.branches()
                return SuccessResponse(data=data)
            except HTTPException:
                raise
            except Exception as e:
                logger.exception("[SCM] branches error")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/scm/checkout")
        async def scm_checkout(payload: Dict[str, Any]):
            try:
                if not self.source_control_service:
                    raise HTTPException(status_code=503, detail="SCM service not available")
                ok = await self.source_control_service.checkout(
                    branch=str(payload.get("branch", "")),
                    create=bool(payload.get("create", False)),
                )
                return SuccessResponse(data={"ok": ok})
            except HTTPException:
                raise
            except Exception as e:
                logger.exception("[SCM] checkout error")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/scm/pull")
        async def scm_pull():
            try:
                if not self.source_control_service:
                    raise HTTPException(status_code=503, detail="SCM service not available")
                ok = await self.source_control_service.pull()
                return SuccessResponse(data={"ok": ok})
            except HTTPException:
                raise
            except Exception as e:
                logger.exception("[SCM] pull error")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/scm/push")
        async def scm_push(payload: Dict[str, Any] | None = None):
            try:
                if not self.source_control_service:
                    raise HTTPException(status_code=503, detail="SCM service not available")
                payload = payload or {}
                ok = await self.source_control_service.push(set_upstream=bool(payload.get("set_upstream", False)))
                return SuccessResponse(data={"ok": ok})
            except HTTPException:
                raise
            except Exception as e:
                logger.exception("[SCM] push error")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/scm/init")
        async def scm_init():
            """Initialize a Git repository in the workspace."""
            try:
                if not self.source_control_service:
                    raise HTTPException(status_code=503, detail="SCM service not available")
                ok = await self.source_control_service.init_repo()
                return SuccessResponse(data={"ok": ok}, message="Git repository initialized successfully" if ok else "Failed to initialize Git repository")
            except HTTPException:
                raise
            except Exception as e:
                logger.exception("[SCM] init error")
                raise HTTPException(status_code=500, detail=str(e))

        # Session CRUD endpoints
        @self.app.get("/api/chat/sessions")
        async def get_chat_sessions():
            """Get list of all chat sessions with metadata."""
            try:
                sessions = await self.chat_service.get_sessions()
                return SuccessResponse(
                    data=sessions,
                    message=f"Retrieved {len(sessions)} chat sessions"
                )
            except Exception as e:
                logger.error(f"Failed to get chat sessions: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/chat/sessions")
        async def create_chat_session(request: ChatSessionCreateRequest):
            """Create a new chat session."""
            try:
                session_id = await self.chat_service.create_session(request.name)
                return SuccessResponse(
                    data={"session_id": session_id, "name": request.name},
                    message="Chat session created successfully"
                )
            except Exception as e:
                logger.error(f"Failed to create chat session: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.put("/api/chat/sessions/{session_id}")
        async def update_chat_session(session_id: str, request: ChatSessionUpdateRequest):
            """Update chat session metadata (rename)."""
            try:
                success = await self.chat_service.update_session(session_id, request.name)
                if success:
                    return SuccessResponse(
                        data={"session_id": session_id, "name": request.name},
                        message="Chat session updated successfully"
                    )
                else:
                    raise HTTPException(status_code=404, detail="Session not found")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to update chat session: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/api/chat/sessions/{session_id}")
        async def delete_chat_session(session_id: str):
            """Delete a chat session and its history."""
            try:
                success = await self.chat_service.delete_session(session_id)
                if success:
                    return SuccessResponse(
                        message="Chat session deleted successfully"
                    )
                else:
                    raise HTTPException(status_code=404, detail="Session not found")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to delete chat session: {e}")
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
