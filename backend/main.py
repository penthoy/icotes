#!/usr/bin/env python3
"""
Main entry point for the icotes backend server.

This module sets up and runs the FastAPI application with WebSocket support
for the icotes code editor interface.

IMPORTANT: Always run this in the virtual environment!
Run with: source venv/bin/activate && python main.py
"""

import asyncio
import logging
import json
import os
import io
import sys
import time
import argparse
import contextlib
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path="../.env")  # Load from parent directory
except ImportError:
    pass  # python-dotenv not available, skip .env loading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import icpy modules
try:
    from icpy.api import get_websocket_api, shutdown_websocket_api, get_rest_api, shutdown_rest_api
    from icpy.core.connection_manager import get_connection_manager
    from icpy.services import get_workspace_service, get_filesystem_service, get_terminal_service, get_agent_service, get_chat_service
    from icpy.services.clipboard_service import clipboard_service
    ICPY_AVAILABLE = True
    logger.info("icpy modules loaded successfully")
except ImportError as e:
    logger.warning(f"icpy modules not available: {e}")
    ICPY_AVAILABLE = False
    clipboard_service = None

# Import terminal module
try:
    from terminal import terminal_manager
    TERMINAL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Terminal module not available: {e}")
    TERMINAL_AVAILABLE = False
    terminal_manager = None

# Server-side clipboard implementation with system clipboard integration
class ServerClipboard:
    """Server-side clipboard to handle copy/paste operations with system clipboard sync"""
    
    def __init__(self):
        self.buffer = ""
        self.history = []
        self.max_history = 10
        self.system_clipboard_available = self._check_system_clipboard()
    
    def _check_system_clipboard(self) -> bool:
        """Check if system clipboard tools are available"""
        try:
            import subprocess
            import os
            
            # Check if we have X11 display (required for xclip/xsel)
            if not os.environ.get('DISPLAY'):
                logger.info("No X11 display available - using file-based clipboard")
                return self._setup_file_clipboard()
            
            # Check for xclip (Linux)
            result = subprocess.run(['which', 'xclip'], capture_output=True, text=True)
            if result.returncode == 0:
                # Test if xclip actually works
                try:
                    test_process = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], 
                                                capture_output=True, text=True, timeout=1)
                    logger.info("System clipboard available: xclip")
                    return True
                except:
                    logger.warning("xclip found but not working (no X11 display)")
                    return self._setup_file_clipboard()
            
            # Check for xsel (Linux alternative)
            result = subprocess.run(['which', 'xsel'], capture_output=True, text=True)
            if result.returncode == 0:
                try:
                    test_process = subprocess.run(['xsel', '--clipboard', '--output'], 
                                                capture_output=True, text=True, timeout=1)
                    logger.info("System clipboard available: xsel")
                    return True
                except:
                    logger.warning("xsel found but not working (no X11 display)")
                    return self._setup_file_clipboard()
                
            # Check for pbcopy/pbpaste (macOS)
            result = subprocess.run(['which', 'pbcopy'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("System clipboard available: pbcopy/pbpaste")
                return True
                
            logger.warning("No system clipboard tools found - using file-based clipboard")
            return self._setup_file_clipboard()
        except Exception as e:
            logger.warning(f"Error checking system clipboard: {e} - using file-based clipboard")
            return self._setup_file_clipboard()
    
    def _setup_file_clipboard(self) -> bool:
        """Setup file-based clipboard for headless environments"""
        try:
            import os
            import tempfile
            
            # Create clipboard directory in temp
            self.clipboard_dir = os.path.join(tempfile.gettempdir(), "icotes_clipboard")
            os.makedirs(self.clipboard_dir, exist_ok=True)
            
            self.clipboard_file = os.path.join(self.clipboard_dir, "clipboard.txt")
            self.clipboard_type = "file"
            
            # Create empty clipboard file if it doesn't exist
            if not os.path.exists(self.clipboard_file):
                with open(self.clipboard_file, 'w') as f:
                    f.write("")
            
            logger.info(f"File-based clipboard setup: {self.clipboard_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to setup file-based clipboard: {e}")
            return False
    
    def write(self, text: str) -> bool:
        """Write text to clipboard"""
        try:
            if self.system_clipboard_available:
                if hasattr(self, 'clipboard_type') and self.clipboard_type == "file":
                    return self._write_file_clipboard(text)
                else:
                    return self._write_system_clipboard(text)
            else:
                self.buffer = text
                self.history.append(text)
                if len(self.history) > self.max_history:
                    self.history.pop(0)
                return True
        except Exception as e:
            logger.error(f"Error writing to clipboard: {e}")
            return False
    
    def _write_system_clipboard(self, text: str) -> bool:
        """Write to system clipboard"""
        try:
            import subprocess
            
            # Try xclip first
            try:
                process = subprocess.run(['xclip', '-selection', 'clipboard'], 
                                       input=text, text=True, timeout=2)
                return process.returncode == 0
            except:
                pass
            
            # Try xsel
            try:
                process = subprocess.run(['xsel', '--clipboard', '--input'], 
                                       input=text, text=True, timeout=2)
                return process.returncode == 0
            except:
                pass
            
            # Try pbcopy (macOS)
            try:
                process = subprocess.run(['pbcopy'], input=text, text=True, timeout=2)
                return process.returncode == 0
            except:
                pass
            
            return False
        except Exception as e:
            logger.error(f"Error writing to system clipboard: {e}")
            return False
    
    def _write_file_clipboard(self, text: str) -> bool:
        """Write to file-based clipboard"""
        try:
            with open(self.clipboard_file, 'w') as f:
                f.write(text)
            return True
        except Exception as e:
            logger.error(f"Error writing to file clipboard: {e}")
            return False
    
    def read(self) -> str:
        """Read text from clipboard"""
        try:
            if self.system_clipboard_available:
                if hasattr(self, 'clipboard_type') and self.clipboard_type == "file":
                    return self._read_file_clipboard()
                else:
                    return self._read_system_clipboard()
            else:
                return self.buffer
        except Exception as e:
            logger.error(f"Error reading from clipboard: {e}")
            return ""
    
    def _read_system_clipboard(self) -> str:
        """Read from system clipboard"""
        try:
            import subprocess
            
            # Try xclip first
            try:
                result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    return result.stdout
            except:
                pass
            
            # Try xsel
            try:
                result = subprocess.run(['xsel', '--clipboard', '--output'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    return result.stdout
            except:
                pass
            
            # Try pbpaste (macOS)
            try:
                result = subprocess.run(['pbpaste'], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    return result.stdout
            except:
                pass
            
            return ""
        except Exception as e:
            logger.error(f"Error reading from system clipboard: {e}")
            return ""
    
    def _read_file_clipboard(self) -> str:
        """Read from file-based clipboard"""
        try:
            with open(self.clipboard_file, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading from file clipboard: {e}")
            return ""
    
    def get_history(self) -> List[str]:
        """Get clipboard history"""
        return self.history.copy()
    
    def clear(self) -> bool:
        """Clear clipboard"""
        try:
            if self.system_clipboard_available:
                if hasattr(self, 'clipboard_type') and self.clipboard_type == "file":
                    return self._write_file_clipboard("")
                else:
                    return self._write_system_clipboard("")
            else:
                self.buffer = ""
                return True
        except Exception as e:
            logger.error(f"Error clearing clipboard: {e}")
            return False

# Global clipboard instance
clipboard = ServerClipboard()

# Code execution functionality
def execute_python_code(code: str) -> tuple:
    """Execute Python code and return output, errors, and execution time"""
    import time
    import sys
    import io
    import contextlib
    
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

# Legacy ConnectionManager for backwards compatibility
class ConnectionManager:
    """Legacy connection manager for backwards compatibility."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Connect a WebSocket."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket."""
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        """Broadcast message to all connected WebSockets."""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                self.disconnect(connection)

# Legacy manager instance
manager = ConnectionManager()

# Auto-initialization function for agents and chat
async def auto_initialize_chat_agent():
    """Automatically create a default agent and configure chat service on startup."""
    try:
        logger.info("🚀 Auto-initializing chat agent...")
        
        # Get agent and chat services
        agent_service = await get_agent_service()
        chat_service = get_chat_service()
        
        # Check if an agent is already configured
        if chat_service.config.agent_id:
            logger.info(f"✅ Chat agent already configured: {chat_service.config.agent_id}")
            return
        
        # Check if there are existing agent sessions
        existing_sessions = agent_service.get_agent_sessions()
        if existing_sessions:
            # Use the first available agent
            first_agent = existing_sessions[0]
            logger.info(f"🔄 Using existing agent: {first_agent.agent_name} ({first_agent.agent_id})")
            await chat_service.update_config({"agent_id": first_agent.agent_id})
            return
        
        # Create a new default agent using AgentConfig
        logger.info("🤖 Creating default OpenAI agent...")
        
        # Import AgentConfig
        from icpy.agent.base_agent import AgentConfig
        
        agent_config = AgentConfig(
            name="default_chat_agent",
            framework="openai",
            role="assistant",
            goal="Help users with questions, code assistance, and general tasks",
            backstory="I am a helpful AI assistant powered by OpenAI's GPT-4o-mini model",
            capabilities=["chat", "reasoning", "code_generation"],
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=2000,
            custom_config={
                "stream": True
            }
        )
        
        # Create the agent
        agent_session_id = await agent_service.create_agent(agent_config)
        
        # Get the agent ID from the session
        sessions = agent_service.get_agent_sessions()
        agent_id = None
        for session in sessions:
            if session.session_id == agent_session_id:
                agent_id = session.agent_id
                break
        
        if agent_id:
            logger.info(f"✅ Created default agent: {agent_id}")
            
            # Configure chat service to use this agent
            await chat_service.update_config({"agent_id": agent_id})
            logger.info(f"✅ Chat service configured with agent: {agent_id}")
        else:
            logger.error("❌ Failed to get agent ID after creation")
            
    except Exception as e:
        logger.error(f"💥 Error during auto-initialization: {e}")
        logger.exception("Full traceback:")

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

# Create FastAPI app with lifecycle management
app = FastAPI(
    title="icotes Backend",
    version="1.0.0",
    description="Enhanced backend server for icotes code editor",
    lifespan=lifespan
)

# Initialize icpy REST API before app starts (to avoid middleware issues)
rest_api_instance = None
if ICPY_AVAILABLE:
    try:
        from icpy.api.rest_api import create_rest_api
        logger.info("Initializing icpy REST API...")
        rest_api_instance = create_rest_api(app)
        logger.info("icpy REST API initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize icpy REST API: {e}")

# Get allowed origins from environment
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (React app build)
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
            # Fallback to old system
            success = clipboard.write(request.text)
            return ClipboardResponse(
                success=success,
                message="Clipboard updated successfully" if success else "Failed to update clipboard"
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
            # Fallback to old system
            text = clipboard.read()
            return ClipboardResponse(
                success=True,
                message="Clipboard retrieved successfully",
                text=text
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
            # Fallback to old system
            history = clipboard.get_history()
            return {
                "success": True,
                "history": history,
                "count": len(history)
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
            # Fallback status
            return {
                "success": True,
                "status": {
                    "system": "legacy",
                    "available_methods": ["file_fallback"],
                    "capabilities": {
                        "read": True,
                        "write": True,
                        "history": True,
                        "multi_format": False
                    }
                }
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
            # Fallback clear
            clipboard.write("")
            return {
                "success": True,
                "message": "Clipboard cleared"
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

# Terminal API endpoints
@app.post("/api/terminals")
async def create_terminal(request: Dict[str, Any]):
    """Create a new terminal session."""
    try:
        if not TERMINAL_AVAILABLE:
            raise HTTPException(status_code=503, detail="Terminal service not available")
        
        terminal_id = f"{os.urandom(8).hex()}-{os.urandom(4).hex()}-{os.urandom(4).hex()}-{os.urandom(4).hex()}-{os.urandom(8).hex()}"
        name = request.get("name", f"Terminal {len(terminal_manager.terminal_connections) + 1}")
        
        # Create terminal entry
        terminal_data = {
            "id": terminal_id,
            "name": name,
            "config": {
                "shell": "/bin/bash",
                "term": "xterm-256color",
                "cols": 80,
                "rows": 24,
                "env": {},
                "cwd": os.path.expanduser("~"),
                "startup_script": None
            },
            "state": "created",
            "created_at": asyncio.get_event_loop().time(),
            "last_activity": asyncio.get_event_loop().time(),
            "pid": None,
            "has_process": False
        }
        
        # Store terminal info
        terminal_manager.terminal_connections[terminal_id] = {
            "data": terminal_data,
            "websocket": None,
            "master_fd": None,
            "process": None,
            "read_task": None,
            "write_task": None
        }
        
        return {
            "success": True,
            "data": terminal_data,
            "message": "Terminal created successfully",
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger.error(f"Error creating terminal: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create terminal: {str(e)}")

@app.get("/api/terminals")
async def get_terminals():
    """Get all terminal sessions."""
    try:
        if not TERMINAL_AVAILABLE:
            raise HTTPException(status_code=503, detail="Terminal service not available")
        
        terminals = []
        for terminal_id, connection in terminal_manager.terminal_connections.items():
            terminals.append(connection["data"])
        
        return {
            "success": True,
            "data": terminals,
            "message": None,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger.error(f"Error getting terminals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get terminals: {str(e)}")

@app.get("/api/terminals/{terminal_id}")
async def get_terminal(terminal_id: str):
    """Get a specific terminal session."""
    try:
        if not TERMINAL_AVAILABLE:
            raise HTTPException(status_code=503, detail="Terminal service not available")
        
        if terminal_id not in terminal_manager.terminal_connections:
            raise HTTPException(status_code=404, detail="Terminal not found")
        
        connection = terminal_manager.terminal_connections[terminal_id]
        return {
            "success": True,
            "data": connection["data"],
            "message": None,
            "timestamp": asyncio.get_event_loop().time()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting terminal {terminal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get terminal: {str(e)}")

@app.post("/api/terminals/{terminal_id}/start")
async def start_terminal(terminal_id: str):
    """Start a terminal session."""
    try:
        if not TERMINAL_AVAILABLE:
            raise HTTPException(status_code=503, detail="Terminal service not available")
        
        if terminal_id not in terminal_manager.terminal_connections:
            raise HTTPException(status_code=404, detail="Terminal not found")
        
        connection = terminal_manager.terminal_connections[terminal_id]
        
        # Update terminal state
        connection["data"]["state"] = "running"
        connection["data"]["last_activity"] = asyncio.get_event_loop().time()
        
        return {
            "success": True,
            "data": None,
            "message": "Terminal started successfully",
            "timestamp": asyncio.get_event_loop().time()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting terminal {terminal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start terminal: {str(e)}")

@app.delete("/api/terminals/{terminal_id}")
async def delete_terminal(terminal_id: str):
    """Delete a terminal session."""
    try:
        if not TERMINAL_AVAILABLE:
            raise HTTPException(status_code=503, detail="Terminal service not available")
        
        if terminal_id not in terminal_manager.terminal_connections:
            raise HTTPException(status_code=404, detail="Terminal not found")
        
        # Clean up terminal connection
        terminal_manager.disconnect_terminal(terminal_id)
        
        return {
            "success": True,
            "data": None,
            "message": "Terminal deleted successfully",
            "timestamp": asyncio.get_event_loop().time()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting terminal {terminal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete terminal: {str(e)}")

@app.post("/api/terminals/{terminal_id}/input")
async def send_terminal_input(terminal_id: str, request: Dict[str, Any]):
    """Send input to a terminal session."""
    try:
        if not TERMINAL_AVAILABLE:
            raise HTTPException(status_code=503, detail="Terminal service not available")
        
        if terminal_id not in terminal_manager.terminal_connections:
            raise HTTPException(status_code=404, detail="Terminal not found")
        
        input_data = request.get("input", "")
        connection = terminal_manager.terminal_connections[terminal_id]
        
        # Send input to terminal if WebSocket is connected
        if connection.get("websocket") and connection["websocket"].client_state.name == "CONNECTED":
            await connection["websocket"].send_text(input_data)
        
        return {
            "success": True,
            "data": None,
            "message": "Input sent successfully",
            "timestamp": asyncio.get_event_loop().time()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending input to terminal {terminal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send input: {str(e)}")

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

# Legacy WebSocket endpoint for backwards compatibility
@app.websocket("/ws")
async def legacy_websocket_endpoint(websocket: WebSocket):
    """Legacy WebSocket endpoint for backwards compatibility."""
    await manager.connect(websocket)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "execute_code":
                # Handle code execution via WebSocket
                code = message.get("code", "")
                language = message.get("language", "python")
                
                logger.info(f"WebSocket: Executing {language} code")
                
                if language.lower() == "python":
                    output, errors, execution_time = execute_python_code(code)
                    response = {
                        "type": "execution_result",
                        "output": output,
                        "errors": errors,
                        "execution_time": execution_time
                    }
                else:
                    response = {
                        "type": "execution_result",
                        "output": [],
                        "errors": [f"Language '{language}' not supported yet"],
                        "execution_time": 0.0
                    }
                
                await manager.send_personal_message(json.dumps(response), websocket)
            
            elif message.get("type") == "ping":
                # Handle ping/pong for connection keepalive
                await manager.send_personal_message(json.dumps({"type": "pong"}), websocket)
            
            else:
                # Echo unknown messages
                await manager.send_personal_message(json.dumps({
                    "type": "echo",
                    "message": f"Unknown message type: {message.get('type')}"
                }), websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Legacy WebSocket error: {e}")
        manager.disconnect(websocket)

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
        import uuid
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
            # Write to clipboard
            success = clipboard.write(stdin_data)
            
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
        # Read from clipboard
        clipboard_data = clipboard.read()
        
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
