#!/usr/bin/env python3
"""
Enhanced icotes Backend Server
Provides terminal and clipboard functionality for the icotes code editor
with advanced WebSocket API integration and message broker support.

This version integrates the new icpy backend architecture with:
- Enhanced WebSocket API with state synchronization
- Message broker for real-time communication
- Modular service architecture
- Connection recovery and message replay
- Multi-client support with session management

Author: GitHub Copilot
Date: July 16, 2025
"""

import sys
import argparse
import asyncio
import logging
import json
import os
import io
import contextlib
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import icpy modules
try:
    from icpy.api import get_websocket_api, shutdown_websocket_api, get_rest_api, shutdown_rest_api
    from icpy.core.connection_manager import get_connection_manager
    from icpy.services import get_workspace_service, get_filesystem_service, get_terminal_service
    ICPY_AVAILABLE = True
    logger.info("icpy modules loaded successfully")
except ImportError as e:
    logger.warning(f"icpy modules not available: {e}")
    ICPY_AVAILABLE = False

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

# For production, allow all origins if not specified (Coolify handles this)
if os.environ.get("NODE_ENV") == "production" and not allowed_origins:
    allowed_origins = ["*"]

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
    return {
        "status": "healthy",
        "services": {
            "icpy": ICPY_AVAILABLE,
            "terminal": TERMINAL_AVAILABLE,
            "clipboard": clipboard.system_clipboard_available
        },
        "timestamp": asyncio.get_event_loop().time()
    }

# Clipboard endpoints
@app.post("/clipboard", response_model=ClipboardResponse)
async def set_clipboard(request: ClipboardRequest):
    """Set clipboard content."""
    try:
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
    """Get clipboard content."""
    try:
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
    if not TERMINAL_AVAILABLE:
        await websocket.close(code=1011, reason="Terminal service not available")
        return
    
    try:
        await websocket.accept()
        
        # Create terminal connection
        conn = terminal_manager.create_terminal_connection(terminal_id)
        
        # Handle WebSocket communication
        async def read_from_terminal():
            while True:
                try:
                    data = await conn['terminal'].read()
                    if data:
                        await websocket.send_text(data)
                except Exception as e:
                    logger.error(f"Error reading from terminal: {e}")
                    break
        
        async def write_to_terminal():
            while True:
                try:
                    data = await websocket.receive_text()
                    await conn['terminal'].write(data)
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Error writing to terminal: {e}")
                    break
        
        # Store tasks in connection
        conn['read_task'] = asyncio.create_task(read_from_terminal())
        conn['write_task'] = asyncio.create_task(write_to_terminal())
        
        # Wait for tasks to complete
        await asyncio.gather(conn['read_task'], conn['write_task'], return_exceptions=True)
        
    except Exception as e:
        logger.error(f"Terminal WebSocket error: {e}")
    finally:
        if terminal_manager:
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

# Catch-all route for React app
@app.get("/{path:path}")
async def serve_react_app_catchall(path: str):
    """Catch-all route for React app."""
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
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
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
