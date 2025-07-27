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

# Third-party imports
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
    from icpy.api.rest_api import create_rest_api
    from icpy.core.connection_manager import get_connection_manager
    from icpy.services import get_workspace_service, get_filesystem_service, get_terminal_service, get_agent_service, get_chat_service
    from icpy.services.clipboard_service import clipboard_service
    from icpy.agent.custom_agent import auto_initialize_chat_agent, get_available_custom_agents
    ICPY_AVAILABLE = True
    logger.info("icpy modules loaded successfully")
except ImportError as e:
    logger.warning(f"icpy modules not available: {e}")
    ICPY_AVAILABLE = False
    clipboard_service = None
    get_available_custom_agents = lambda: ["TestAgent", "DefaultAgent"]  # Fallback

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

# Data models

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
            await auto_initialize_chat_agent()
            
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
mount_static_files(app)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    clipboard_status = await clipboard_service.get_status() if ICPY_AVAILABLE else {"capabilities": {"read": False, "write": False}}
    return {
        "status": "healthy",
        "services": {
            "icpy": ICPY_AVAILABLE,
            "terminal": TERMINAL_AVAILABLE,
            "clipboard": clipboard_status["capabilities"]
        },
        "timestamp": asyncio.get_event_loop().time()
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

# Enhanced WebSocket endpoints
@app.websocket("/ws/enhanced")
async def enhanced_websocket_endpoint(websocket: WebSocket):
    """Enhanced WebSocket endpoint with icpy integration."""
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
                logger.error(f"Error in enhanced WebSocket: {e}")
                break
        
        # Cleanup
        await websocket_api.disconnect_websocket(connection_id)
        
    except Exception as e:
        logger.error(f"Enhanced WebSocket error: {e}")

# Terminal WebSocket endpoint
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
        
    except Exception as e:
        logger.error(f"[DEBUG] Terminal WebSocket error for terminal_id {terminal_id}: {e}")
    finally:
        if terminal_manager:
            logger.info(f"[DEBUG] Disconnecting terminal {terminal_id}")
            terminal_manager.disconnect_terminal(terminal_id)

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
        fallback_agents = ["OpenAIDemoAgent", "TestAgent", "DefaultAgent"]
        return {"success": True, "agents": fallback_agents}
    except Exception as e:
        logger.error(f"Error getting custom agents: {e}")
        return {"success": False, "error": str(e), "agents": []}

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
async def serve_react_app():
    """Serve React app for production."""
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
async def serve_react_app_catchall(path: str):
    """Catch-all route for React app, excluding API routes."""
    # Skip API routes - let them be handled by their specific handlers
    if path.startswith("api/") or path.startswith("ws/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
    file_path = os.path.join(dist_path, path)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    else:
        # Return index.html for client-side routing
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
