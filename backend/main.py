#!/usr/bin/env python3
"""
Main entry point for the icotes backend server.

This module sets up and runs the FastAPI application with WebSocket support
for the icotes code editor interface.

Recommended: use uv for isolation and speed
Run with: uv run python main.py
"""

# Standard library imports
import asyncio
import contextlib
import io
import json
import logging
import os
import sys
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

# Third-party imports
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request, Body
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load environment variables
load_dotenv(dotenv_path="../.env")  # Load from parent directory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for application state
rest_api_instance = None

# Local imports
try:
    from icpy.api import get_websocket_api, shutdown_websocket_api, get_rest_api, shutdown_rest_api
    from icpy.api.media import router as media_router
    from icpy.api.rest_api import create_rest_api
    from icpy.core.connection_manager import get_connection_manager
    from icpy.services import get_workspace_service, get_filesystem_service, get_terminal_service, get_agent_service, get_chat_service, get_code_execution_service, get_preview_service
    from icpy.services.clipboard_service import clipboard_service
    from icpy.agent.custom_agent import get_available_custom_agents, call_custom_agent, call_custom_agent_stream
    from icpy.auth import auth_manager, get_current_user, get_optional_user
    ICPY_AVAILABLE = True
    logger.info("icpy modules loaded successfully")
except ImportError as e:
    logger.warning(f"icpy modules not available: {e}")
    ICPY_AVAILABLE = False
    clipboard_service = None
    get_available_custom_agents = lambda: ["TestAgent", "DefaultAgent"]  # Fallback
    call_custom_agent = lambda agent, msg, hist: f"Custom agent {agent} not available"
    call_custom_agent_stream = lambda agent, msg, hist: iter([f"Custom agent {agent} not available"])
    
    # Authentication fallbacks
    class MockAuthManager:
        def is_saas_mode(self): return False
        def is_standalone_mode(self): return True
    
    auth_manager = MockAuthManager()
    get_current_user = lambda request: None
    get_optional_user = lambda request: None

try:
    from terminal import terminal_manager
    TERMINAL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Terminal module not available: {e}")
    TERMINAL_AVAILABLE = False
    terminal_manager = None

# Import utilities and endpoints
from icpy.core.cors import configure_cors_origins
from icpy.core.static_files import mount_static_files
from icpy.core.auth_helpers import (
    issue_auth_cookie, serve_index_fallback, is_html_route, 
    is_browser_navigation, build_unauth_redirect
)
from icpy.cli.main_cli import parse_arguments, handle_clipboard_commands

# Import endpoint modules
from icpy.api.endpoints import health, auth, clipboard, preview, agents, websockets, hop


# Basic code execution functionality (legacy fallback)
def execute_python_code(code: str) -> tuple:
    """Execute Python code and return output, errors, and execution time"""
    
    # Capture stdout and stderr
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    
    start_time = time.time()
    
    try:
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            # Execute the code
            exec(code)
        
        execution_time = time.time() - start_time
        
        # Get output
        output = stdout_buffer.getvalue()
        errors = stderr_buffer.getvalue()
        
        return (
            output.split('\n') if output else [],
            errors.split('\n') if errors else [],
            execution_time
        )
    
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"{type(e).__name__}: {str(e)}"
        
        return (
            [],
            [error_msg],
            execution_time
        )


# Data models
class CodeExecutionRequest(BaseModel):
    """Request model for code execution."""
    code: str
    language: str = "python"


class CodeExecutionResponse(BaseModel):
    """Response model for code execution."""
    output: List[str]
    errors: List[str]
    execution_time: float


class FrontendLogEntry(BaseModel):
    """Frontend log entry model."""
    timestamp: str
    level: int
    component: str
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    sessionId: Optional[str] = None
    connectionId: Optional[str] = None


class FrontendLogsRequest(BaseModel):
    """Request model for frontend logs."""
    sessionId: str
    logs: List[FrontendLogEntry]


# App lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle with proper startup and shutdown."""
    # Startup
    logger.info("Starting icotes backend server...")
    
    # Initialize icpy services if available
    if ICPY_AVAILABLE:
        try:
            logger.info("Initializing icpy services...")
            await get_websocket_api()
            # Initialize REST API services (if REST API was created)
            if rest_api_instance:
                await rest_api_instance.initialize()
            
            # Initialize preview service
            from icpy.services import initialize_preview_service
            await initialize_preview_service()
            
            logger.info("icpy services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize icpy services: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down icotes backend server...")
    
    # Shutdown icpy services if available
    if ICPY_AVAILABLE:
        try:
            logger.info("Shutting down icpy services...")
            
            # Shutdown preview service
            from icpy.services import shutdown_preview_service
            await shutdown_preview_service()
            
            await shutdown_websocket_api()
            await shutdown_rest_api()
            logger.info("icpy services shutdown complete")
        except Exception as e:
            logger.error(f"Error during icpy shutdown: {e}")


def initialize_rest_api(app: FastAPI) -> None:
    """Initialize icpy REST API before app starts to avoid middleware issues."""
    global rest_api_instance
    rest_api_instance = None
    if ICPY_AVAILABLE:
        try:
            logger.info("Initializing icpy REST API...")
            rest_api_instance = create_rest_api(app)
            logger.info("icpy REST API initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize icpy REST API: {e}")


# Create FastAPI app with lifecycle management
app = FastAPI(
    title="icotes Backend",
    version="1.0.0",
    description="Enhanced backend server for icotes code editor",
    lifespan=lifespan
)

# Initialize application components
initialize_rest_api(app)

# Configure CORS middleware
allowed_origins = configure_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    # Credentials cannot be used with wildcard origins
    allow_credentials=False if allowed_origins == ["*"] else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
mount_static_files(app)

# Register media router (Phase 1 minimal upload/download)
try:
    app.include_router(media_router, prefix="/api")
    logger.info("Media router registered at /api/media")
except Exception as e:
    logger.error(f"Failed to register media router: {e}")


# Register endpoint routes
app.get("/health")(health.health_check)
app.get("/healthz")(health.healthz)
app.get("/api/config")(health.get_frontend_config)

app.get("/auth/info")(auth.auth_info)
app.get("/auth/profile", dependencies=[Depends(get_current_user)])(auth.user_profile)
app.get("/auth/debug/test-token")(auth.debug_test_token)

app.post("/clipboard", response_model=clipboard.ClipboardResponse)(clipboard.set_clipboard)
app.get("/clipboard", response_model=clipboard.ClipboardResponse)(clipboard.get_clipboard)
app.get("/clipboard/history")(clipboard.get_clipboard_history)
app.get("/clipboard/status")(clipboard.get_clipboard_status)
app.post("/clipboard/clear")(clipboard.clear_clipboard)

app.post("/api/preview/create", response_model=preview.PreviewCreateResponse)(preview.create_preview)
app.post("/api/preview/{preview_id}/update")(preview.update_preview)
app.get("/api/preview/{preview_id}/status", response_model=preview.PreviewStatusResponse)(preview.get_preview_status)
app.delete("/api/preview/{preview_id}")(preview.delete_preview)
app.get("/preview/{preview_id}/{file_path:path}")(preview.serve_preview_file)

# Agent endpoints
app.get("/api/custom-agents")(agents.get_custom_agents)
app.get("/api/custom-agents/configured")(agents.get_configured_custom_agents)
app.post("/api/custom-agents/reload")(agents.reload_custom_agents_endpoint)
app.post("/api/environment/reload")(agents.reload_environment_endpoint)
app.post("/api/environment/update-keys")(agents.update_api_keys_endpoint)
app.get("/api/environment/keys")(agents.get_api_keys_status_endpoint)
app.get("/api/environment/key")(agents.get_api_key_value_endpoint)
app.get("/api/custom-agents/{agent_name}/info")(agents.get_custom_agent_info)

# Hop endpoints
try:
    app.include_router(hop.router)
    logger.info("Hop router registered at /api/hop")
except Exception as e:
    logger.error(f"Failed to register hop router: {e}")

# WebSocket endpoints (additional)
app.websocket("/ws/agents/{session_id}/stream")(websockets.agent_stream_websocket)
app.websocket("/ws/workflows/{session_id}/monitor")(websockets.workflow_monitor_websocket)
app.websocket("/ws/chat")(websockets.chat_websocket)


# Fallback single file download endpoint (mirrors rest_api implementation)
@app.get("/api/files/download")
async def fallback_download_file(path: str):  # type: ignore
    """Serve a file for download (fallback if REST API route not active)."""
    try:
        if not path:
            raise HTTPException(status_code=400, detail="path query parameter required")
        # Determine workspace root (parent of backend when launched inside backend)
        current_dir = os.getcwd()
        if os.path.basename(current_dir) == 'backend':
            workspace_root = os.path.realpath(os.path.join(current_dir, os.pardir))
        else:
            workspace_root = os.path.realpath(current_dir)
        candidates = []
        if os.path.isabs(path):
            candidates.append(os.path.realpath(path))
        else:
            # relative to filesystem workspace folder if exists
            fs_root = os.path.join(workspace_root, 'workspace')
            candidates.append(os.path.realpath(os.path.join(fs_root, path.lstrip('/'))))
            candidates.append(os.path.realpath(os.path.join(workspace_root, path.lstrip('/'))))
        resolved = None
        for cand in candidates:
            if os.path.exists(cand):
                resolved = cand
                break
        if not resolved:
            raise HTTPException(status_code=404, detail="File not found")
        if os.path.isdir(resolved):
            raise HTTPException(status_code=400, detail="Cannot download a directory (use zip)")
        # Use realpath and commonpath for secure path validation
        try:
            if os.path.commonpath([workspace_root, resolved]) != workspace_root:
                raise HTTPException(status_code=400, detail="Path outside workspace root")
        except ValueError:
            # Different drives on Windows
            raise HTTPException(status_code=400, detail="Invalid path")
        filename = os.path.basename(resolved)
        import mimetypes
        mime, _ = mimetypes.guess_type(filename)
        if not mime:
            mime = 'application/octet-stream'
        return FileResponse(resolved, filename=filename, media_type=mime)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[fallback_download] error for path={path}: {e}")
        raise HTTPException(status_code=500, detail="Download failed")


# Code execution endpoints
@app.post("/execute", response_model=CodeExecutionResponse)
async def execute_code(request: CodeExecutionRequest):
    """Execute code and return results."""
    try:
        if request.language.lower() == "python":
            output, errors, execution_time = execute_python_code(request.code)
            return CodeExecutionResponse(
                output=output,
                errors=errors,
                execution_time=execution_time
            )
        else:
            return CodeExecutionResponse(
                output=[],
                errors=[f"Language '{request.language}' not supported yet"],
                execution_time=0.0
            )
    except Exception as e:
        logger.error(f"Error executing code: {e}")
        return CodeExecutionResponse(
            output=[],
            errors=[f"Execution error: {str(e)}"],
            execution_time=0.0
        )


# Frontend logging endpoint
@app.post("/api/logs/frontend")
async def receive_frontend_logs(request: FrontendLogsRequest):
    """Receive and store frontend logs."""
    try:
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Create frontend log file path
        log_file = os.path.join(logs_dir, 'frontend.log')
        
        # Format and write logs
        with open(log_file, 'a', encoding='utf-8') as f:
            for log_entry in request.logs:
                level_names = {0: 'DEBUG', 1: 'INFO', 2: 'WARN', 3: 'ERROR'}
                level_name = level_names.get(log_entry.level, 'UNKNOWN')
                
                # Format log entry similar to backend format
                log_line = f"{log_entry.timestamp} - {level_name} - [{log_entry.component}] {log_entry.message}"
                
                if log_entry.data:
                    log_line += f" | Data: {json.dumps(log_entry.data)}"
                
                if log_entry.error:
                    log_line += f" | Error: {log_entry.error}"
                
                if log_entry.sessionId:
                    log_line += f" | Session: {log_entry.sessionId}"
                
                if log_entry.connectionId:
                    log_line += f" | Connection: {log_entry.connectionId}"
                
                f.write(log_line + '\n')
        
        return JSONResponse(content={"success": True, "message": f"Stored {len(request.logs)} log entries"})
        
    except Exception as e:
        logger.error(f"Error storing frontend logs: {e}")
        return JSONResponse(
            status_code=500, 
            content={"success": False, "message": f"Failed to store logs: {str(e)}"}
        )


# Terminal WebSocket endpoint (moved before generic /ws to fix routing)
@app.websocket("/ws/terminal/{terminal_id}")
async def terminal_websocket_endpoint(websocket: WebSocket, terminal_id: str):
    """Terminal WebSocket endpoint."""
    logger.info(f"[DEBUG] Terminal WebSocket connection attempt for terminal_id: {terminal_id}")
    
    if not TERMINAL_AVAILABLE or terminal_manager is None:
        logger.error(f"[DEBUG] Terminal service not available for terminal_id: {terminal_id}")
        await websocket.close(code=1011, reason="Terminal service not available")
        return
    
    try:
        # Accept once here to avoid double-accept across remote/local paths
        await websocket.accept()
        # Determine if SSH hop is active; align decision with ContextRouter FS
        use_remote = False
        remote_mgr = None
        context_fs_is_remote = False
        try:
            from icpy.services.context_router import get_context_router
            context_router = await get_context_router()
            fs_rt = await context_router.get_filesystem()
            context_fs_is_remote = bool(getattr(fs_rt, 'is_remote', False))
        except Exception as e:
            logger.debug(f"[TERM] ContextRouter check failed: {e}")
        try:
            from icpy.services.hop_service import get_hop_service
            hop = await get_hop_service()
            session = hop.status()
            has_conn = getattr(hop, '_conn', None) is not None
            has_sftp = getattr(hop, '_sftp', None) is not None
            use_remote = bool(session and session.status == 'connected' and has_conn)
            logger.info("[TERM] Decision use_remote=%s status=%s cwd=%s contextId=%s has_conn=%s has_sftp=%s fs_is_remote=%s", use_remote, getattr(session,'status',None), getattr(session,'cwd',None), getattr(session,'contextId',None), has_conn, has_sftp, context_fs_is_remote)
            # If FS says remote but decision false, retry briefly to avoid race on freshly-connected hop
            if context_fs_is_remote and not use_remote:
                logger.info("[TERM] FS indicates remote but conn not ready; retrying hop check shortly")
                await asyncio.sleep(0.3)
                session = hop.status()
                has_conn = getattr(hop, '_conn', None) is not None
                use_remote = bool(session and session.status == 'connected' and has_conn)
                logger.info("[TERM] Recheck use_remote=%s status=%s has_conn=%s", use_remote, getattr(session,'status',None), has_conn)
        except Exception as e:
            logger.debug(f"[TERM] Hop service check failed: {e}")

        if use_remote:
            try:
                logger.info(f"[TERM] Using remote terminal for {terminal_id}")
                from icpy.services.remote_terminal_manager import get_remote_terminal_manager
                remote_mgr = await get_remote_terminal_manager()
                await remote_mgr.connect_terminal(websocket, terminal_id)
                logger.info(f"[DEBUG] Remote terminal tasks completed for terminal_id: {terminal_id}")
                return
            except Exception as e:
                logger.warning(f"[TERM] Remote terminal failed, falling back to local for {terminal_id}: {e}")
                # Fall through to local

        # Local PTY path
        master_fd, proc = await terminal_manager.connect_terminal(websocket, terminal_id, already_accepted=True)
        logger.info(f"[DEBUG] Terminal connected for terminal_id: {terminal_id}")
        
        # Handle WebSocket communication
        async def read_from_terminal():
            logger.info(f"[DEBUG] Starting read_from_terminal task for terminal_id: {terminal_id}")
            if terminal_manager:
                await terminal_manager.read_from_terminal(websocket, master_fd)
        
        async def write_to_terminal():
            logger.info(f"[DEBUG] Starting write_to_terminal task for terminal_id: {terminal_id}")
            if terminal_manager:
                await terminal_manager.write_to_terminal(websocket, master_fd)
        
        # Wait for tasks to complete
        await asyncio.gather(read_from_terminal(), write_to_terminal(), return_exceptions=True)
        logger.info(f"[DEBUG] Terminal tasks completed for terminal_id: {terminal_id}")
    except asyncio.CancelledError:
        # Normal disconnect path; avoid noisy error logs
        logger.info(f"[DEBUG] Terminal WebSocket cancelled for terminal_id: {terminal_id}")
    except Exception as e:
        logger.error(f"[DEBUG] Terminal WebSocket error for terminal_id {terminal_id}: {e}")
    finally:
        if terminal_manager:
            logger.info(f"[DEBUG] Disconnecting terminal {terminal_id}")
            try:
                terminal_manager.disconnect_terminal(terminal_id)
            except Exception:
                pass
        try:
            if remote_mgr:
                await remote_mgr.disconnect_terminal(terminal_id)
        except Exception:
            pass


# Enhanced WebSocket endpoint (now the primary /ws endpoint)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Primary WebSocket endpoint with icpy integration."""
    if not ICPY_AVAILABLE:
        await websocket.close(code=1011, reason="icpy services not available")
        return
    
    try:
        websocket_api = await get_websocket_api()
        connection_id = await websocket_api.connect_websocket(websocket)
        
        # Handle messages
        while True:
            try:
                message = await websocket.receive_text()
                await websocket_api.handle_websocket_message(connection_id, message)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in WebSocket: {e}")
                break
        
        # Cleanup
        await websocket_api.disconnect_websocket(connection_id)
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


# Legacy WebSocket endpoint (deprecated)
@app.websocket("/ws/legacy")
async def legacy_websocket_endpoint(websocket: WebSocket):
    """
    DEPRECATED: Legacy WebSocket endpoint for backward compatibility.
    This endpoint is deprecated and will be removed in a future version.
    Please use the main /ws endpoint which provides enhanced functionality.
    """
    await websocket.accept()
    
    # Send deprecation warning
    await websocket.send_text(json.dumps({
        "type": "warning",
        "message": "This endpoint (/ws/legacy) is deprecated. Please update your client to use /ws instead."
    }))
    
    try:
        while True:
            message = await websocket.receive_text()
            try:
                data = json.loads(message)
                
                if data.get("type") == "execute":
                    # Handle code execution using ICPY service
                    code = data.get("code", "")
                    language = data.get("language", "python")
                    
                    if ICPY_AVAILABLE:
                        try:
                            # Use ICPY code execution service
                            code_execution_service = get_code_execution_service()
                            
                            # Ensure service is running
                            if not code_execution_service.running:
                                await code_execution_service.start()
                            
                            result = await code_execution_service.execute_code(
                                code=code,
                                language=language
                            )
                            
                            # Send result back
                            await websocket.send_text(json.dumps({
                                "type": "result",
                                "execution_id": result.execution_id,
                                "status": result.status.value,
                                "output": result.output,
                                "errors": result.errors,
                                "execution_time": result.execution_time,
                                "language": result.language.value
                            }))
                        except Exception as e:
                            logger.error(f"ICPY code execution error: {e}")
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": f"Code execution failed: {str(e)}"
                            }))
                    else:
                        # Fallback to basic execution
                        try:
                            output, errors, execution_time = execute_python_code(code)
                            await websocket.send_text(json.dumps({
                                "type": "result",
                                "output": output,
                                "errors": errors,
                                "execution_time": execution_time
                            }))
                        except Exception as e:
                            logger.error(f"Basic code execution error: {e}")
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": f"Code execution failed: {str(e)}"
                            }))
                    
                elif data.get("type") == "ping":
                    # Handle ping
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    
                else:
                    # Echo unknown messages for debugging
                    await websocket.send_text(json.dumps({
                        "type": "echo",
                        "message": f"Unknown message type: {data.get('type')}"
                    }))
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except Exception as e:
                logger.error(f"WebSocket message error: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error", 
                    "message": f"Internal server error: {str(e)}"
                }))
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


# Include remaining important endpoints from the icpy modules
# These will be added in a separate module in the next iteration


# Serve React app for production
@app.get("/")
async def serve_react_app(request: Request):
    """Serve React app for production with SaaS authentication check and handoff token support."""
    # SaaS mode: Check authentication before serving app
    if ICPY_AVAILABLE and auth_manager.is_saas_mode():
        cookie_name = os.getenv('COOKIE_NAME', 'auth_token')
        # Updated to support new landing/orchestrator authentication flow
        token_param = os.getenv('TOKEN_QUERY_PARAM', 'token')  # Changed default from 't' to 'token'
        auth_token = request.cookies.get(cookie_name)
        
        # 1) If we already have a valid cookie, continue
        if auth_token:
            try:
                _ = auth_manager.validate_jwt_token(auth_token)
            except HTTPException:
                auth_token = None  # Treat as missing/invalid
        
        # 2) If missing/invalid cookie, check for authentication token in query
        if not auth_token:
            token_from_query = request.query_params.get(token_param)
            source = request.query_params.get('src', 'direct')  # Get authentication source
            
            # Debug logging
            if os.getenv('CONTAINER_DEBUG_AUTH'):
                logger.info(f"[auth] Token received: {bool(token_from_query)}")
                logger.info(f"[auth] Source: {source}")
                logger.info(f"[auth] User Agent: {request.headers.get('User-Agent')}")
            
            if token_from_query:
                try:
                    # Validate JWT token from landing/orchestrator (using standard JWT validation)
                    payload = auth_manager.validate_jwt_token(token_from_query)
                    # Mint session cookie using the same token
                    # Clean URL: redirect to root path to remove token from URL
                    redirect = RedirectResponse(url="/", status_code=303)
                    issue_auth_cookie(redirect, token_from_query)
                    
                    user_id = payload.get('sub', 'unknown')
                    logger.info(f"[container] Auto-authenticated user {user_id} from {source} -> issuing host-only cookie and redirecting to clean root")
                    return redirect
                except HTTPException as e:
                    # Invalid authentication token → 401 JSON to avoid loops
                    logger.warning(f"[container] Invalid authentication token from {source}: {e.detail}")
                    return JSONResponse(status_code=401, content={"error": "invalid_token", "detail": e.detail})
            else:
                # 3) No cookie and no authentication token
                if is_browser_navigation(request) and is_html_route(""):
                    logger.info("[container] Unauthenticated browser navigation to root - redirecting to home page")
                    return build_unauth_redirect(request)
                return JSONResponse(status_code=401, content={"error": "unauthenticated", "detail": "Missing auth cookie and authentication token"})
    
    # Serve the React app (authenticated user or standalone mode, or unauth fallback)
    dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
    index_path = os.path.join(dist_path, "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return JSONResponse(
            content={"message": "icotes backend is running", "status": "healthy"},
            status_code=200
        )


# Catch-all route for React app (excluding API routes)
@app.get("/{path:path}")
async def serve_react_app_catchall(path: str, request: Request):
    """Catch-all route for React app, excluding API routes, with SaaS auth and handoff processing."""
    # Skip API and websocket routes - let them be handled by their specific handlers
    if path.startswith("api/") or path.startswith("ws/") or path == "healthz":
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Additional exclusions for static/metrics
    from icpy.core.auth_helpers import EXCLUDED_PATHS
    if path in EXCLUDED_PATHS or path.startswith("assets/") or path.startswith("static/"):
        raise HTTPException(status_code=404, detail="Not found")
    
    if ICPY_AVAILABLE and auth_manager.is_saas_mode():
        cookie_name = os.getenv('COOKIE_NAME', 'auth_token')
        # Updated to support new landing/orchestrator authentication flow
        token_param = os.getenv('TOKEN_QUERY_PARAM', 'token')  # Changed default from 't' to 'token'
        auth_token = request.cookies.get(cookie_name)
        
        # Validate existing cookie if present
        if auth_token:
            try:
                _ = auth_manager.validate_jwt_token(auth_token)
            except HTTPException:
                auth_token = None
        
        if not auth_token:
            token_from_query = request.query_params.get(token_param)
            source = request.query_params.get('src', 'direct')  # Get authentication source
            
            # Debug logging
            if os.getenv('CONTAINER_DEBUG_AUTH'):
                logger.info(f"[auth] Token received on path '{path}': {bool(token_from_query)}")
                logger.info(f"[auth] Source: {source}")
                logger.info(f"[auth] User Agent: {request.headers.get('User-Agent')}")
            
            if token_from_query:
                try:
                    # Validate JWT token from landing/orchestrator (using standard JWT validation)
                    payload = auth_manager.validate_jwt_token(token_from_query)
                    # For catch-all routes, redirect to root to ensure clean URL
                    redirect = RedirectResponse(url="/", status_code=303)
                    issue_auth_cookie(redirect, token_from_query)
                    
                    user_id = payload.get('sub', 'unknown')
                    logger.info(f"[container] Auto-authenticated user {user_id} from {source} on path {path} - redirecting to clean root")
                    return redirect
                except HTTPException as e:
                    logger.warning(f"[container] Invalid authentication token from {source} on path {path}: {e.detail}")
                    return JSONResponse(status_code=401, content={"error": "invalid_token", "detail": e.detail})
            else:
                if is_browser_navigation(request) and is_html_route(path):
                    logger.info(f"[container] Unauthenticated browser navigation to '{path}' - redirecting to home page")
                    return build_unauth_redirect(request)
                return JSONResponse(status_code=401, content={"error": "unauthenticated", "detail": "Missing auth cookie and authentication token"})
    
    dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
    file_path = os.path.join(dist_path, path)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    else:
        index_path = os.path.join(dist_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            return JSONResponse(
                content={"message": "File not found", "path": path},
                status_code=404
            )


def main():
    """Main entry point with CLI argument handling."""
    args = parse_arguments()
    
    # Configure debug logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Handle clipboard commands (these need async)
    if handle_clipboard_commands(args):
        return
    
    # Normal server mode
    logger.info(f"Starting icotes backend server on {args.host}:{args.port}")
    
    # Configure uvicorn
    uvicorn_config = {
        "app": "main:app",
        "host": args.host,
        "port": args.port,
        "log_level": "debug" if args.debug else "info",
        "reload": args.reload,
        "access_log": True,
        "use_colors": True
    }
    
    # Add SSL config if certificates exist
    ssl_keyfile = os.environ.get("SSL_KEYFILE")
    ssl_certfile = os.environ.get("SSL_CERTFILE")
    
    if ssl_keyfile and ssl_certfile and os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile):
        uvicorn_config.update({
            "ssl_keyfile": ssl_keyfile,
            "ssl_certfile": ssl_certfile
        })
        logger.info("SSL enabled")
    
    # Run server
    uvicorn.run(**uvicorn_config)


if __name__ == "__main__":
    main()