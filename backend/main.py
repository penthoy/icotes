#!/usr/bin/env python3
"""
Main entry point for the icotes backend server.

This module sets up and runs the FastAPI application with WebSocket support
for the icotes code editor interface.

IMPORTANT: Always run this in the virtual environment!
Run with: source venv/bin/activate && python main.py
"""

# Standard library imports
import argparse
import asyncio
import contextlib
import io
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime

# Third-party imports
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request, Body
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

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
    from icpy.api.rest_api import create_rest_api
    from icpy.core.connection_manager import get_connection_manager
    from icpy.services import get_workspace_service, get_filesystem_service, get_terminal_service, get_agent_service, get_chat_service, get_code_execution_service, get_code_execution_service
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

# Code execution functionality
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

class ClipboardRequest(BaseModel):
    """Request model for clipboard operations."""
    text: str

class ClipboardResponse(BaseModel):
    """Response model for clipboard operations."""
    success: bool
    message: str
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

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

# Data models

# Helper: set host-only auth cookie
def _issue_auth_cookie(response: JSONResponse | RedirectResponse, token: str) -> None:
    cookie_name = os.getenv('COOKIE_NAME', 'auth_token')
    # Host-only cookie: do NOT set Domain attribute
    response.set_cookie(
        key=cookie_name,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        max_age=60 * 60 * 8  # 8 hours default validity; actual token exp governs access
    )

# New helpers for unauthenticated browser redirect behavior
EXCLUDED_PATHS = {"healthz", "readiness", "metrics", "favicon.ico"}

# Serve index.html or a simple fallback without assuming authentication
# (kept for non-redirect cases)
def _serve_index_fallback():
    dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
    index_path = os.path.join(dist_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return JSONResponse(content={"message": "icotes backend", "status": "unauthenticated"}, status_code=200)

# Compute the home/base URL to send unauthenticated users to (e.g., icotes.com)
def _get_home_redirect_base() -> str:
    # Prefer explicit absolute URL envs
    for key in ["MAIN_SITE_URL", "PUBLIC_HOME_URL", "SITE_HOME_URL", "LOGIN_BASE_URL", "UNAUTH_REDIRECT_URL"]:
        val = os.getenv(key)
        if val and val.startswith("http"):
            return val.rstrip('/')
    # If only a root path was provided, ignore it and build from APP_DOMAIN
    app_domain = os.getenv('APP_DOMAIN', 'icotes.com')
    # Default to https main site
    return f"https://{app_domain}".rstrip('/')

def _is_html_route(path: str) -> bool:
    # Exclude api/ws and common static paths
    if path.startswith("api/") or path.startswith("ws/"):
        return False
    if path.startswith("assets/") or path.startswith("static/"):
        return False
    if path in EXCLUDED_PATHS:
        return False
    return True

def _is_browser_navigation(request: Request) -> bool:
    if request.method.upper() != "GET":
        return False
    accept = (request.headers.get("accept") or "").lower()
    sec_mode = (request.headers.get("sec-fetch-mode") or "").lower()
    # Treat as browser navigation if HTML is acceptable and mode is navigate (or header missing)
    is_html = "text/html" in accept or "*/*" in accept
    is_nav = (sec_mode == "navigate") or (sec_mode == "")
    return is_html and is_nav

def _sanitize_return_to(url_str: str) -> Optional[str]:
    try:
        # Updated to support new landing/orchestrator authentication flow
        token_param = os.getenv('TOKEN_QUERY_PARAM', 'token')  # Changed default from 't' to 'token'
        app_domain = os.getenv('APP_DOMAIN', 'icotes.com')
        u = urlparse(url_str)
        # Allow only http/https and enforce host allowlist (app_domain or its subdomains)
        if u.scheme not in ("https", "http"):
            return None
        if app_domain:
            host = (u.hostname or "").lower()
            if not (host == app_domain.lower() or host.endswith("." + app_domain.lower())):
                return None
        # Force https scheme to avoid http→https extra hops
        scheme = "https"
        # Strip sensitive or looping params
        strip_keys = {token_param.lower(), "return_to", "token", "state", "code"}
        q = [(k, v) for (k, v) in parse_qsl(u.query, keep_blank_values=True) if k.lower() not in strip_keys]
        clean = u._replace(scheme=scheme, query=urlencode(q, doseq=True))
        sanitized = urlunparse(clean)
        if len(sanitized) > 2048:
            return None
        return sanitized
    except Exception:
        return None

def _build_unauth_redirect(request: Request) -> RedirectResponse:
    # Always send unauthenticated users straight to the main site, not this session subdomain
    base = _get_home_redirect_base()
    redirect = RedirectResponse(url=base, status_code=303)
    redirect.headers['Cache-Control'] = 'no-store'
    redirect.headers['X-Robots-Tag'] = 'noindex'
    return redirect

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
            logger.info("icpy services initialized successfully")
            
            # Auto-initialize chat agent after services are ready
            # await auto_initialize_chat_agent()  # Function not yet implemented
            
        except Exception as e:
            logger.error(f"Failed to initialize icpy services: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down icotes backend server...")
    
    # Shutdown icpy services if available
    if ICPY_AVAILABLE:
        try:
            logger.info("Shutting down icpy services...")
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

def configure_cors_origins() -> List[str]:
    """Configure and return CORS allowed origins based on environment variables."""
    allowed_origins = []
    
    # Add production domains if available
    frontend_url = os.environ.get("FRONTEND_URL")
    if frontend_url:
        allowed_origins.append(frontend_url)
    
    # Add SITE_URL-based origins for both single-port and dual-port setups
    site_url = os.environ.get("SITE_URL")
    if site_url:
        # Single-port setup (backend serves frontend)
        backend_port = os.environ.get("BACKEND_PORT") or os.environ.get("PORT") or "8000"
        allowed_origins.append(f"http://{site_url}:{backend_port}")
        allowed_origins.append(f"https://{site_url}:{backend_port}")
        
        # Dual-port setup (separate frontend)
        frontend_port = os.environ.get("FRONTEND_PORT") or "5173"
        allowed_origins.append(f"http://{site_url}:{frontend_port}")
        allowed_origins.append(f"https://{site_url}:{frontend_port}")
    
    # For development, allow localhost and common development ports
    if os.environ.get("NODE_ENV") == "development":
        allowed_origins.extend([
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ])
        
        # Add SITE_URL with common development ports
        if site_url:
            for port in ["8000", "3000", "5173"]:
                allowed_origins.append(f"http://{site_url}:{port}")
                allowed_origins.append(f"https://{site_url}:{port}")
    
    # For production, allow all origins if not specified (Coolify handles this)
    if os.environ.get("NODE_ENV") == "production" and not allowed_origins:
        allowed_origins = ["*"]
    
    # Remove duplicates and log
    allowed_origins = list(set(allowed_origins))
    logger.info(f"CORS allowed origins: {allowed_origins}")
    
    return allowed_origins

def mount_static_files(app: FastAPI) -> None:
    """Mount static files for production React app build."""
    # Check if dist directory exists (production)
    dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
    if os.path.exists(dist_path):
        # Mount static files for production
        app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")
        # Mount additional static files that might be needed
        if os.path.exists(os.path.join(dist_path, "static")):
            app.mount("/static", StaticFiles(directory=os.path.join(dist_path, "static")), name="static")
        logger.info(f"Serving static files from {dist_path}")
    else:
        logger.info("No dist directory found - running in development mode")

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

# Health check endpoint
@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint."""
    clipboard_status = await clipboard_service.get_status() if ICPY_AVAILABLE else {"capabilities": {"read": False, "write": False}}
    
    # Get user info without failing if not authenticated
    user = None
    try:
        user = get_optional_user(request) if ICPY_AVAILABLE else None
    except Exception:
        user = None
    
    health_data = {
        "status": "healthy",
        "services": {
            "icpy": ICPY_AVAILABLE,
            "terminal": TERMINAL_AVAILABLE,
            "clipboard": clipboard_status["capabilities"]
        },
        "timestamp": asyncio.get_event_loop().time(),
        "auth": {
            "mode": "saas" if (ICPY_AVAILABLE and auth_manager.is_saas_mode()) else "standalone",
            "authenticated": user is not None if (ICPY_AVAILABLE and auth_manager.is_saas_mode()) else None,
            "user_id": user.get("user_id") if user else None
        }
    }
    
    return health_data

# SaaS-compatible health check endpoint (orchestrator requirement)
@app.get("/healthz")
async def healthz():
    """Simple health check endpoint for orchestrator probes."""
    return {"status": "ok"}

# Dynamic configuration endpoint for frontend
@app.get("/api/config")
async def get_frontend_config(request: Request):
    """
    Provide dynamic configuration for the frontend based on the request host.
    Prioritizes dynamic host detection for Cloudflare tunnel compatibility.
    Falls back to environment variables only when hosts match.
    """
    import os
    
    # Get the host from the request
    host = request.headers.get("host", "localhost:8000")
    
    # Check for development environment variables
    env_backend_url = os.getenv('VITE_BACKEND_URL')
    env_api_url = os.getenv('VITE_API_URL') 
    env_ws_url = os.getenv('VITE_WS_URL')
    
    # Check if the request host matches the environment configuration
    use_env_config = False
    if env_backend_url and env_api_url and env_ws_url:
        try:
            env_host = env_backend_url.replace('http://', '').replace('https://', '').split('/')[0]
            if host == env_host:
                use_env_config = True
                logger.info(f"Request host {host} matches environment host {env_host}, using environment config")
            else:
                logger.info(f"Request host {host} differs from environment host {env_host}, using dynamic detection for Cloudflare tunnel compatibility")
        except Exception as e:
            logger.warning(f"Error parsing environment URL {env_backend_url}: {e}")
    
    if use_env_config:
        # Development mode with matching host: use environment variables
        config = {
            "base_url": env_backend_url,
            "api_url": env_api_url,
            "ws_url": env_ws_url,
            "version": "1.0.0",
            "auth_mode": auth_manager.auth_mode if ICPY_AVAILABLE else "standalone",
            "features": {
                "terminal": TERMINAL_AVAILABLE,
                "icpy": ICPY_AVAILABLE,
                "clipboard": True
            }
        }
        logger.info(f"Using environment-based config: {config}")
        return config
    
    # Dynamic host detection mode (used for Cloudflare tunnels, Docker, and mismatched hosts)
    
    # Determine protocol (HTTP vs HTTPS)
    # Check for forwarded proto first (reverse proxy), then connection
    protocol = "http"
    if (request.headers.get("x-forwarded-proto") == "https" or 
        request.headers.get("x-forwarded-ssl") == "on" or
        str(request.url.scheme) == "https"):
        protocol = "https"
    
    # Build URLs
    base_url = f"{protocol}://{host}"
    ws_protocol = "wss" if protocol == "https" else "ws"
    ws_url = f"{ws_protocol}://{host}/ws"
    
    config = {
        "base_url": base_url,
        "api_url": f"{base_url}/api",
        "ws_url": ws_url,
        "version": "1.0.0",
        "auth_mode": auth_manager.auth_mode if ICPY_AVAILABLE else "standalone",
        "features": {
            "terminal": TERMINAL_AVAILABLE,
            "icpy": ICPY_AVAILABLE,
            "clipboard": True
        }
    }
    
    logger.info(f"Using dynamic host-based config: {config}")
    return config

# Authentication info endpoint
@app.get("/auth/info")
async def auth_info(request: Request):
    """Get authentication information."""
    user = None
    try:
        user = get_optional_user(request) if ICPY_AVAILABLE else None
    except Exception:
        user = None
        
    return {
        "auth_mode": "saas" if (ICPY_AVAILABLE and auth_manager.is_saas_mode()) else "standalone",
        "authenticated": user is not None if (ICPY_AVAILABLE and auth_manager.is_saas_mode()) else None,
        "user": {
            "id": user.get("user_id") if user else None,
            "email": user.get("email") if user else None,
            "role": user.get("role") if user else None
        } if user else None,
        "requires_auth": ICPY_AVAILABLE and auth_manager.is_saas_mode()
    }

# SaaS mode user profile endpoint (protected)
@app.get("/auth/profile")
async def user_profile(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user profile. Only available in SaaS mode."""
    if auth_manager.is_standalone_mode():
        raise HTTPException(status_code=404, detail="User profiles not available in standalone mode")
    
    return {
        "user": {
            "id": user.get("user_id"),
            "email": user.get("email"),
            "role": user.get("role"),
            "token_issued_at": user.get("iat"),
            "token_expires_at": user.get("exp")
        }
    }

# Debug endpoint for testing authentication tokens (SaaS mode only)
@app.get("/auth/debug/test-token")
async def debug_test_token(request: Request):
    """Debug endpoint to test authentication token validation. For development/testing only."""
    if not ICPY_AVAILABLE or auth_manager.is_standalone_mode():
        raise HTTPException(status_code=404, detail="Debug endpoints not available in standalone mode")
    
    token = request.query_params.get('token')
    source = request.query_params.get('src', 'test')
    
    if not token:
        return {
            "error": "missing_token", 
            "message": "Please provide token as query parameter",
            "example": "/auth/debug/test-token?token=your_jwt_here&src=test"
        }
    
    try:
        # Test token validation
        payload = auth_manager.validate_jwt_token(token)
        return {
            "success": True,
            "source": source,
            "token_valid": True,
            "user": {
                "id": payload.get('sub'),
                "email": payload.get('email'),
                "role": payload.get('role', 'user'),
                "issued_at": payload.get('iat'),
                "expires_at": payload.get('exp')
            },
            "payload": payload if os.getenv('CONTAINER_DEBUG_AUTH') else None
        }
    except HTTPException as e:
        return {
            "success": False,
            "source": source,
            "token_valid": False,
            "error": e.detail,
            "status_code": e.status_code
        }

# ========================================
# ICPY API Integration Complete
# ========================================
# The ICPY REST API provides all file operations through:
# - backend/icpy/api/rest_api.py - REST API implementation  
# - backend/icpy/services/filesystem_service.py - File operations
# - Integration with message broker for real-time events
# - Proper error handling and security

# Enhanced Clipboard endpoints with multi-layer support
@app.post("/clipboard", response_model=ClipboardResponse)
async def set_clipboard(request: ClipboardRequest):
    """Set clipboard content using enhanced multi-layer strategy."""
    try:
        if ICPY_AVAILABLE and clipboard_service:
            result = await clipboard_service.write_clipboard(request.text)
            return ClipboardResponse(
                success=result["success"],
                message=f"Clipboard updated via {result['method']}" if result["success"] else result.get("error", "Failed to update clipboard"),
                metadata=result
            )
        else:
            return ClipboardResponse(
                success=False,
                message="Clipboard service not available"
            )
    except Exception as e:
        logger.error(f"Error setting clipboard: {e}")
        return ClipboardResponse(
            success=False,
            message=f"Error: {str(e)}"
        )

@app.get("/clipboard", response_model=ClipboardResponse)
async def get_clipboard():
    """Get clipboard content using enhanced multi-layer strategy."""
    try:
        if ICPY_AVAILABLE and clipboard_service:
            result = await clipboard_service.read_clipboard()
            return ClipboardResponse(
                success=result["success"],
                message=f"Clipboard retrieved via {result['method']}" if result["success"] else result.get("error", "Failed to retrieve clipboard"),
                text=result.get("content", ""),
                metadata=result
            )
        else:
            return ClipboardResponse(
                success=False,
                message="Clipboard service not available"
            )
    except Exception as e:
        logger.error(f"Error getting clipboard: {e}")
        return ClipboardResponse(
            success=False,
            message=f"Error: {str(e)}"
        )

@app.get("/clipboard/history")
async def get_clipboard_history():
    """Get clipboard history."""
    try:
        if ICPY_AVAILABLE and clipboard_service:
            history = await clipboard_service.get_history()
            return {
                "success": True,
                "history": history,
                "count": len(history)
            }
        else:
            return {
                "success": False,
                "message": "Clipboard service not available"
            }
    except Exception as e:
        logger.error(f"Error getting clipboard history: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@app.get("/clipboard/status")
async def get_clipboard_status():
    """Get clipboard service status and capabilities."""
    try:
        if ICPY_AVAILABLE and clipboard_service:
            status = await clipboard_service.get_status()
            return {
                "success": True,
                "status": status
            }
        else:
            return {
                "success": False,
                "message": "Clipboard service not available"
            }
    except Exception as e:
        logger.error(f"Error getting clipboard status: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@app.post("/clipboard/clear")
async def clear_clipboard():
    """Clear clipboard content."""
    try:
        if ICPY_AVAILABLE and clipboard_service:
            result = await clipboard_service.clear_clipboard()
            return {
                "success": result["success"],
                "message": f"Clipboard cleared via {result['method']}" if result["success"] else result.get("error", "Failed to clear clipboard")
            }
        else:
            return {
                "success": False,
                "message": "Clipboard service not available"
            }
    except Exception as e:
        logger.error(f"Error clearing clipboard: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

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
        # Connect terminal using TerminalManager
        master_fd, proc = await terminal_manager.connect_terminal(websocket, terminal_id)
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
            terminal_manager.disconnect_terminal(terminal_id)

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

# Custom Agents API endpoints
@app.get("/api/custom-agents")
async def get_custom_agents():
    """Get list of available custom agents for frontend dropdown menu."""
    try:
        logger.info("Custom agents endpoint called")
        agents = get_available_custom_agents()
        logger.info(f"Retrieved custom agents: {agents}")
        return {"success": True, "agents": agents}
    except ImportError as e:
        logger.warning(f"icpy custom agent module not available: {e}")
        # Fallback: return some default agents for testing
        fallback_agents = ["AgentCreator", "OpenAIDemoAgent", "TestAgent", "DefaultAgent"]
        return {"success": True, "agents": fallback_agents}
    except Exception as e:
        logger.error(f"Error getting custom agents: {e}")
        return {"success": False, "error": str(e), "agents": []}

@app.get("/api/custom-agents/configured")
async def get_configured_custom_agents():
    """Get list of custom agents with their display configuration from workspace."""
    try:
        logger.info("Configured custom agents endpoint called")
        from icpy.agent.custom_agent import get_configured_custom_agents
        from icpy.services.agent_config_service import get_agent_config_service
        
        configured_agents = get_configured_custom_agents()
        logger.info(f"Retrieved {len(configured_agents)} configured agents")
        
        # Also get settings and categories including default agent
        config_service = get_agent_config_service()
        config = config_service.load_config()
        settings = config.get("settings", {})
        categories = config.get("categories", {})
        
        return {
            "success": True, 
            "agents": configured_agents,
            "settings": settings,
            "categories": categories,
            "message": f"Retrieved {len(configured_agents)} configured agents"
        }
    except ImportError as e:
        logger.warning(f"Agent config service not available: {e}")
        # Fallback to basic agent list
        agents = get_available_custom_agents()
        fallback_agents = [{"name": agent, "displayName": agent, "description": "", "category": "General", "order": 999, "icon": "🤖"} for agent in agents]
        return {"success": True, "agents": fallback_agents}
    except Exception as e:
        logger.error(f"Error getting configured custom agents: {e}")
        return {"success": False, "error": str(e), "agents": []}

@app.post("/api/custom-agents/reload")
async def reload_custom_agents_endpoint(request: Request):
    """Reload all custom agents and return updated list."""
    try:
        # Check authentication in SaaS mode
        if auth_manager.is_saas_mode():
            user = get_optional_user(request)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            # TODO: Add admin role check if needed
            logger.info(f"Agent reload requested by user: {user.get('sub', 'unknown')}")
        else:
            logger.info("Agent reload requested in standalone mode")
        
        # Import reload function
        from icpy.agent.custom_agent import reload_custom_agents
        
        # Perform reload
        reloaded_agents = await reload_custom_agents()
        
        logger.info(f"Agent reload complete. Available agents: {reloaded_agents}")
        
        # Send WebSocket notification to connected clients
        try:
            if ICPY_AVAILABLE:
                # Lazy import to avoid startup errors when messaging is unavailable
                from icpy.core.message_broker import get_message_broker
                message_broker = await get_message_broker()
                await message_broker.publish(
                    topic="agents.reloaded",
                    payload={
                        "type": "agents_reloaded",
                        "agents": reloaded_agents,
                        "timestamp": time.time(),
                        "message": f"Reloaded {len(reloaded_agents)} agents"
                    }
                )
                logger.info("WebSocket notification sent for agent reload")
        except Exception as e:
            logger.warning(f"Failed to send WebSocket notification: {e}")
        
        return {"success": True, "agents": reloaded_agents, "message": f"Reloaded {len(reloaded_agents)} agents"}
        
    except ImportError as e:
        logger.error(f"Hot reload system not available: {e}")
        return {"success": False, "error": "Hot reload system not available", "agents": []}
    except HTTPException:
        raise  # Re-raise HTTP exceptions (like 401)
    except Exception as e:
        logger.error(f"Error reloading custom agents: {e}")
        return {"success": False, "error": str(e), "agents": []}

@app.post("/api/environment/reload")
async def reload_environment_endpoint(request: Request):
    """Reload environment variables for all agents."""
    try:
        # Check authentication in SaaS mode
        if auth_manager.is_saas_mode():
            user = get_optional_user(request)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            logger.info(f"Environment reload requested by user: {user.get('sub', 'unknown')}")
        else:
            logger.info("Environment reload requested in standalone mode")
        
        # Import reload function
        from icpy.agent.custom_agent import reload_agent_environment
        
        # Perform environment reload
        success = await reload_agent_environment()
        
        if success:
            logger.info("Environment reload successful")
            return {"success": True, "message": "Environment variables reloaded successfully"}
        else:
            logger.warning("Environment reload failed")
            return {"success": False, "error": "Environment reload failed"}
            
    except ImportError as e:
        logger.error(f"Hot reload system not available: {e}")
        return {"success": False, "error": "Hot reload system not available"}
    except HTTPException:
        raise  # Re-raise HTTP exceptions (like 401)
    except Exception as e:
        logger.error(f"Error reloading environment: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/environment/update-keys")
async def update_api_keys_endpoint(request: Request):
    """Update API keys in environment variables with hot reload."""
    try:
        # Check authentication in SaaS mode
        if auth_manager.is_saas_mode():
            user = get_optional_user(request)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            logger.info(f"API key update requested by user: {user.get('sub', 'unknown')}")
        else:
            logger.info("API key update requested in standalone mode")
        
        # Get request body
        body = await request.json()
        api_keys = body.get('api_keys', {})
        
        if not api_keys:
            return {"success": False, "error": "No API keys provided"}
        
        # Update environment variables directly
        updated_keys = {}
        for key, value in api_keys.items():
            if value and value.strip():  # Only update non-empty values
                os.environ[key] = value.strip()
                updated_keys[key] = True
                logger.info(f"Updated environment variable: {key}")
        
        # Reload environment for agents
        try:
            from icpy.agent.custom_agent import reload_agent_environment
            await reload_agent_environment()
        except Exception as reload_error:
            logger.warning(f"Failed to reload agent environment: {reload_error}")
        
        logger.info(f"API keys updated: {list(updated_keys.keys())}")
        
        return {
            "success": True, 
            "updated_keys": list(updated_keys.keys()), 
            "message": f"Updated {len(updated_keys)} API keys and reloaded environment"
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions (like 401)
    except Exception as e:
        logger.error(f"Error updating API keys: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/environment/keys")
async def get_api_keys_status_endpoint(request: Request):
    """Get the status of API keys (whether they are set or not, without revealing values)."""
    try:
        # Check authentication in SaaS mode
        if auth_manager.is_saas_mode():
            user = get_optional_user(request)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
        
        # Define the API keys we support
        api_keys = [
            'OPENAI_API_KEY',
            'ANTHROPIC_API_KEY',
            'OPENROUTER_API_KEY', 
            'GOOGLE_API_KEY',
            'DEEPSEEK_API_KEY',
            'GROQ_API_KEY',
            'CEREBRAS_API_KEY',
            'DASHSCOPE_API_KEY',
            'MAILERSEND_API_KEY',
            'PUSHOVER_USER',
            'PUSHOVER_TOKEN'
        ]
        
        # Check which keys are set (without revealing values)
        key_status = {}
        for key in api_keys:
            value = os.getenv(key)
            if value:
                # Show first 4 chars and mask the rest
                masked = value[:4] + '*' * (len(value) - 4) if len(value) > 4 else '*' * len(value)
                key_status[key] = {
                    "is_set": True,
                    "masked_value": masked,
                    "length": len(value)
                }
            else:
                key_status[key] = {
                    "is_set": False,
                    "masked_value": "",
                    "length": 0
                }
        
        return {"success": True, "keys": key_status}
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions (like 401)
    except Exception as e:
        logger.error(f"Error getting API key status: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/custom-agents/{agent_name}/info")
async def get_custom_agent_info(agent_name: str):
    """Get information about a specific custom agent."""
    try:
        logger.info(f"Agent info requested for: {agent_name}")
        
        # Import info function
        from icpy.agent.custom_agent import get_agent_info
        
        info = get_agent_info(agent_name)
        
        return {"success": True, "agent_info": info}
        
    except ImportError as e:
        logger.warning(f"Agent info system not available: {e}")
        return {"success": False, "error": "Agent info system not available"}
    except Exception as e:
        logger.error(f"Error getting agent info for {agent_name}: {e}")
        return {"success": False, "error": str(e)}

# Agent WebSocket endpoints
@app.websocket("/ws/agents/{session_id}/stream")
async def agent_stream_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time agent output streaming."""
    if not ICPY_AVAILABLE:
        await websocket.close(code=1011, reason="icpy services not available")
        return
    
    try:
        await websocket.accept()
        
        # Get agent service
        agent_service = await get_agent_service()
        
        # Verify agent session exists
        session = agent_service.get_agent_session(session_id)
        if not session:
            await websocket.close(code=1008, reason="Agent session not found")
            return
        
        # Connect to message broker for agent stream events
        websocket_api = await get_websocket_api()
        connection_id = await websocket_api.connect_websocket(websocket)
        
        # Subscribe to agent stream topic
        # Lazy import to avoid startup errors when messaging is unavailable
        from icpy.core.message_broker import get_message_broker
        message_broker = await get_message_broker()
        await message_broker.subscribe(f"agent.{session_id}.stream", 
                                     lambda msg: websocket_api.send_to_connection(connection_id, msg.payload))
        
        # Send initial session info
        await websocket.send_json({
            "type": "agent_session_info",
            "session": session.to_dict()
        })
        
        # Keep connection alive
        while True:
            try:
                # Wait for ping/pong or other control messages
                message = await websocket.receive_text()
                data = json.loads(message)
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data.get("type") == "get_status":
                    # Send current session status
                    updated_session = agent_service.get_agent_session(session_id)
                    if updated_session:
                        await websocket.send_json({
                            "type": "agent_status",
                            "session": updated_session.to_dict()
                        })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Agent stream WebSocket error: {e}")
                break
        
        # Cleanup
        await websocket_api.disconnect_websocket(connection_id)
        
    except Exception as e:
        logger.error(f"Agent stream WebSocket initialization error: {e}")
        await websocket.close(code=1011, reason="Internal server error")


@app.websocket("/ws/workflows/{session_id}/monitor")
async def workflow_monitor_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time workflow monitoring."""
    if not ICPY_AVAILABLE:
        await websocket.close(code=1011, reason="icpy services not available")
        return
    
    try:
        await websocket.accept()
        
        # Get agent service
        agent_service = await get_agent_service()
        
        # Verify workflow session exists
        session = agent_service.get_workflow_session(session_id)
        if not session:
            await websocket.close(code=1008, reason="Workflow session not found")
            return
        
        # Connect to message broker for workflow events
        websocket_api = await get_websocket_api()
        connection_id = await websocket_api.connect_websocket(websocket)
        
        # Subscribe to workflow events
        # Lazy import to avoid startup errors when messaging is unavailable
        from icpy.core.message_broker import get_message_broker
        message_broker = await get_message_broker()
        await message_broker.subscribe(f"workflow.{session_id}.*", 
                                     lambda msg: websocket_api.send_to_connection(connection_id, msg.payload))
        
        # Send initial session info
        await websocket.send_json({
            "type": "workflow_session_info",
            "session": session.to_dict()
        })
        
        # Keep connection alive and handle control messages
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data.get("type") == "get_status":
                    # Send current workflow status
                    updated_session = agent_service.get_workflow_session(session_id)
                    if updated_session:
                        await websocket.send_json({
                            "type": "workflow_status",
                            "session": updated_session.to_dict()
                        })
                elif data.get("type") == "control":
                    # Handle workflow control commands
                    action = data.get("action")
                    if action == "pause":
                        await agent_service.pause_workflow(session_id)
                    elif action == "resume":
                        await agent_service.resume_workflow(session_id)
                    elif action == "cancel":
                        await agent_service.cancel_workflow(session_id)
                    
                    # Send updated status
                    updated_session = agent_service.get_workflow_session(session_id)
                    if updated_session:
                        await websocket.send_json({
                            "type": "workflow_status",
                            "session": updated_session.to_dict()
                        })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Workflow monitor WebSocket error: {e}")
                break
        
        # Cleanup
        await websocket_api.disconnect_websocket(connection_id)
        
    except Exception as e:
        logger.error(f"Workflow monitor WebSocket initialization error: {e}")
        await websocket.close(code=1011, reason="Internal server error")


# Chat WebSocket endpoint
@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time chat with AI agents."""
    if not ICPY_AVAILABLE:
        await websocket.close(code=1011, reason="icpy services not available")
        return
    
    connection_id = None
    
    try:
        await websocket.accept()
        
        # Get chat service
        chat_service = get_chat_service()
        
        # Generate connection ID for this chat session
        connection_id = str(uuid.uuid4())
        
        # Store the WebSocket in chat service for this connection
        chat_service.websocket_connections[connection_id] = websocket
        
        # Connect to chat service
        session_id = await chat_service.connect_websocket(connection_id)
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "timestamp": time.time()
        })
        
        # Handle incoming messages
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                message_type = data.get("type")
                
                if message_type == "message":
                    # Handle user message
                    content = data.get("content", "")
                    metadata = data.get("metadata", {})
                    
                    if content.strip():
                        await chat_service.handle_user_message(
                            connection_id, 
                            content, 
                            metadata
                        )
                
                elif message_type == "ping":
                    # Respond to ping
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": time.time()
                    })
                
                elif message_type == "get_status":
                    # Send current agent status
                    status = await chat_service.get_agent_status()
                    await websocket.send_json({
                        "type": "status",
                        "agent": status.to_dict(),
                        "timestamp": time.time()
                    })
                
                elif message_type == "get_config":
                    # Send current chat configuration
                    await websocket.send_json({
                        "type": "config",
                        "config": chat_service.config.to_dict(),
                        "timestamp": time.time()
                    })
                
                elif message_type == "update_config":
                    # Update chat configuration
                    config_updates = data.get("config", {})
                    await chat_service.update_config(config_updates)
                    
                    await websocket.send_json({
                        "type": "config_updated",
                        "config": chat_service.config.to_dict(),
                        "timestamp": time.time()
                    })
                
                elif message_type == "stop":
                    # Stop/interrupt current streaming response
                    # Derive session_id from the connection mapping; don't trust client override
                    mapped_session_id = chat_service.chat_sessions.get(connection_id)
                    requested_session_id = data.get("session_id")
                    if mapped_session_id and requested_session_id and requested_session_id != mapped_session_id:
                        logger.warning(
                            f"Stop requested with mismatched session_id "
                            f"(requested={requested_session_id}, mapped={mapped_session_id}); ignoring client override."
                        )
                    session_id_to_stop = mapped_session_id or requested_session_id
                    if not session_id_to_stop:
                        await websocket.send_json({
                            "type": "stop_response",
                            "success": False,
                            "error": "no_session_for_connection",
                            "timestamp": time.time()
                        })
                        continue

                    success = await chat_service.stop_streaming(session_id_to_stop)
                    
                    await websocket.send_json({
                        "type": "stop_response",
                        "success": success,
                        "session_id": session_id_to_stop,
                        "timestamp": time.time()
                    })
                
                else:
                    logger.warning(f"Unknown chat message type: {message_type}")
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.error("Invalid JSON received in chat WebSocket")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": time.time()
                })
            except Exception as e:
                logger.error(f"Chat WebSocket message error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Internal server error",
                    "timestamp": time.time()
                })
        
        # Cleanup
        if connection_id:
            # Remove WebSocket from chat service
            chat_service.websocket_connections.pop(connection_id, None)
            await chat_service.disconnect_websocket(connection_id)
        
    except Exception as e:
        logger.error(f"Chat WebSocket initialization error: {e}")
        if connection_id:
            chat_service.websocket_connections.pop(connection_id, None)
        await websocket.close(code=1011, reason="Internal server error")



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
                    _issue_auth_cookie(redirect, token_from_query)
                    
                    user_id = payload.get('sub', 'unknown')
                    logger.info(f"[container] Auto-authenticated user {user_id} from {source} -> issuing host-only cookie and redirecting to clean root")
                    return redirect
                except HTTPException as e:
                    # Invalid authentication token → 401 JSON to avoid loops
                    logger.warning(f"[container] Invalid authentication token from {source}: {e.detail}")
                    return JSONResponse(status_code=401, content={"error": "invalid_token", "detail": e.detail})
            else:
                # 3) No cookie and no authentication token
                if _is_browser_navigation(request) and _is_html_route(""):
                    logger.info("[container] Unauthenticated browser navigation to root - redirecting to home page")
                    return _build_unauth_redirect(request)
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
                    _issue_auth_cookie(redirect, token_from_query)
                    
                    user_id = payload.get('sub', 'unknown')
                    logger.info(f"[container] Auto-authenticated user {user_id} from {source} on path {path} - redirecting to clean root")
                    return redirect
                except HTTPException as e:
                    logger.warning(f"[container] Invalid authentication token from {source} on path {path}: {e.detail}")
                    return JSONResponse(status_code=401, content={"error": "invalid_token", "detail": e.detail})
            else:
                if _is_browser_navigation(request) and _is_html_route(path):
                    logger.info(f"[container] Unauthenticated browser navigation to '{path}' - redirecting to home page")
                    return _build_unauth_redirect(request)
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

# CLI argument parsing
def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="icotes Backend Server")
    
    # Host configuration priority: BACKEND_HOST -> SITE_URL -> HOST -> default
    default_host = os.getenv('BACKEND_HOST') or os.getenv('SITE_URL') or os.getenv('HOST') or '0.0.0.0'
    parser.add_argument("--host", default=default_host, help="Host to bind to")
    
    # Port configuration priority: BACKEND_PORT -> PORT -> default
    default_port = int(os.getenv('BACKEND_PORT') or os.getenv('PORT') or '8000')
    parser.add_argument("--port", type=int, default=default_port, help="Port to bind to")
    
    parser.add_argument("--stdin-to-clipboard", action="store_true", 
                       help="Read stdin and copy to clipboard")
    parser.add_argument("--clipboard-to-stdout", action="store_true",
                       help="Read clipboard and output to stdout")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    return parser.parse_args()

# CLI clipboard handlers
async def handle_stdin_to_clipboard():
    """Handle --stdin-to-clipboard command."""
    try:
        # Read from stdin
        stdin_data = sys.stdin.read()
        
        if stdin_data:
            # Write to clipboard using icpy clipboard service
            if ICPY_AVAILABLE and clipboard_service:
                result = await clipboard_service.write_clipboard(stdin_data)
                success = result["success"]
            else:
                logger.error("Clipboard service not available")
                print("✗ Clipboard service not available", file=sys.stderr)
                sys.exit(1)
            
            if success:
                logger.info(f"✓ Copied {len(stdin_data)} characters to clipboard")
                print(f"✓ Copied {len(stdin_data)} characters to clipboard", file=sys.stderr)
                sys.exit(0)
            else:
                logger.error("✗ Failed to copy to clipboard")
                print("✗ Failed to copy to clipboard", file=sys.stderr)
                sys.exit(1)
        else:
            logger.info("No input data received")
            print("No input data received", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error in stdin-to-clipboard: {e}")
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)

async def handle_clipboard_to_stdout():
    """Handle --clipboard-to-stdout command."""
    try:
        # Read from clipboard using icpy clipboard service
        if ICPY_AVAILABLE and clipboard_service:
            result = await clipboard_service.read_clipboard()
            clipboard_data = result.get("content", "") if result["success"] else ""
        else:
            logger.error("Clipboard service not available")
            print("✗ Clipboard service not available", file=sys.stderr)
            sys.exit(1)
        
        if clipboard_data:
            # Write to stdout
            sys.stdout.write(clipboard_data)
            sys.stdout.flush()
            logger.info(f"✓ Successfully read {len(clipboard_data)} characters from clipboard")
            sys.exit(0)
        else:
            logger.info("Clipboard is empty")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Error in clipboard-to-stdout: {e}")
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """Main entry point with CLI argument handling."""
    args = parse_arguments()
    
    # Configure debug logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Handle clipboard commands (these need async)
    if args.stdin_to_clipboard:
        asyncio.run(handle_stdin_to_clipboard())
        return
    elif args.clipboard_to_stdout:
        asyncio.run(handle_clipboard_to_stdout())
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
