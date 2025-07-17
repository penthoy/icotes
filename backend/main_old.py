#!/usr/bin/env python3
"""
icotes Backend Server
Provides terminal and clipboard functionality for the icotes code editor
"""

import sys
import argparse
import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import asyncio
import logging
from typing import List, Dict, Any
import sys
import io
import contextlib
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    def _write_to_system_clipboard(self, text: str) -> bool:
        """Write text to system clipboard"""
        if not self.system_clipboard_available:
            return False
            
        try:
            # File-based clipboard (headless environments)
            if hasattr(self, 'clipboard_type') and self.clipboard_type == "file":
                with open(self.clipboard_file, 'w', encoding='utf-8') as f:
                    f.write(text)
                logger.info(f"✓ Wrote to file-based clipboard: {len(text)} characters")
                return True
            
            # System clipboard tools (with X11 display)
            import subprocess
            
            # Try xclip first (most common on Linux)
            try:
                process = subprocess.Popen(['xclip', '-selection', 'clipboard'], 
                                         stdin=subprocess.PIPE, text=True)
                process.communicate(input=text)
                if process.returncode == 0:
                    logger.info("✓ Wrote to system clipboard via xclip")
                    return True
            except FileNotFoundError:
                pass
            
            # Try xsel as fallback
            try:
                process = subprocess.Popen(['xsel', '--clipboard', '--input'], 
                                         stdin=subprocess.PIPE, text=True)
                process.communicate(input=text)
                if process.returncode == 0:
                    logger.info("✓ Wrote to system clipboard via xsel")
                    return True
            except FileNotFoundError:
                pass
            
            # Try pbcopy (macOS)
            try:
                process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, text=True)
                process.communicate(input=text)
                if process.returncode == 0:
                    logger.info("✓ Wrote to system clipboard via pbcopy")
                    return True
            except FileNotFoundError:
                pass
                
            logger.warning("Failed to write to system clipboard - no tools worked")
            return False
            
        except Exception as e:
            logger.error(f"Error writing to system clipboard: {e}")
            return False
    
    def _read_from_system_clipboard(self) -> str:
        """Read text from system clipboard"""
        if not self.system_clipboard_available:
            return ""
            
        try:
            import os
            
            # File-based clipboard (headless environments)
            if hasattr(self, 'clipboard_type') and self.clipboard_type == "file":
                if os.path.exists(self.clipboard_file):
                    with open(self.clipboard_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    logger.info(f"✓ Read from file-based clipboard: {len(content)} characters")
                    return content
                return ""
            
            # System clipboard tools (with X11 display)
            import subprocess
            
            # Try xclip first
            try:
                result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    logger.info("✓ Read from system clipboard via xclip")
                    return result.stdout
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            
            # Try xsel as fallback
            try:
                result = subprocess.run(['xsel', '--clipboard', '--output'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    logger.info("✓ Read from system clipboard via xsel")
                    return result.stdout
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            
            # Try pbpaste (macOS)
            try:
                result = subprocess.run(['pbpaste'], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    logger.info("✓ Read from system clipboard via pbpaste")
                    return result.stdout
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
                
            logger.warning("Failed to read from system clipboard - no tools worked")
            return ""
            
        except Exception as e:
            logger.error(f"Error reading from system clipboard: {e}")
            return ""
    
    def write(self, text: str) -> bool:
        """Write text to both server buffer and system clipboard"""
        if not text:
            return False
        
        # Write to server buffer
        self.buffer = text
        # Add to history (avoid duplicates)
        if not self.history or self.history[-1] != text:
            self.history.append(text)
            if len(self.history) > self.max_history:
                self.history.pop(0)
        
        # Write to system clipboard
        system_success = self._write_to_system_clipboard(text)
        
        logger.info(f"Clipboard write: {len(text)} characters (system: {'✓' if system_success else '✗'})")
        return True
    
    def read(self) -> str:
        """Read text from system clipboard first, fallback to server buffer"""
        # Try to read from system clipboard first
        system_text = self._read_from_system_clipboard()
        if system_text:
            # Update server buffer with system clipboard content
            self.buffer = system_text
            return system_text
        
        # Fallback to server buffer
        return self.buffer
    
    def clear(self) -> bool:
        """Clear both server buffer and system clipboard"""
        self.buffer = ""
        
        # Try to clear system clipboard
        system_success = self._write_to_system_clipboard("")
        
        logger.info(f"Clipboard cleared (system: {'✓' if system_success else '✗'})")
        return True
    
    def get_history(self) -> List[str]:
        """Get clipboard history"""
        return self.history.copy()

# Global clipboard instance
server_clipboard = ServerClipboard()

# Import terminal module
try:
    from terminal import terminal_manager
    TERMINAL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Terminal module not available: {e}")
    TERMINAL_AVAILABLE = False
    terminal_manager = None

app = FastAPI(title="icotes Backend", version="1.0.0")

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
    import os
    if os.path.exists(os.path.join(dist_path, "static")):
        app.mount("/static", StaticFiles(directory=os.path.join(dist_path, "static")), name="static")
    logger.info(f"Serving static files from {dist_path}")
else:
    logger.info("No dist directory found - running in development mode")

# Data models
class CodeExecutionRequest(BaseModel):
    code: str
    language: str = "python"

class CodeExecutionResponse(BaseModel):
    output: List[str]
    errors: List[str]
    execution_time: float



class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connection established. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket connection closed. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Connection might be closed, remove it
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Code execution functionality
def execute_python_code(code: str) -> tuple[List[str], List[str], float]:
    """Execute Python code and capture output and errors"""
    import time
    start_time = time.time()
    
    output = []
    errors = []
    
    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()
    
    # Capture stderr
    old_stderr = sys.stderr
    sys.stderr = captured_error = io.StringIO()
    
    try:
        # Create a local namespace for execution
        local_namespace = {}
        
        # Execute the code
        exec(code, {}, local_namespace)
        
        # Get the output
        stdout_value = captured_output.getvalue()
        if stdout_value:
            output = stdout_value.strip().split('\n')
        
    except Exception as e:
        errors.append(str(e))
        stderr_value = captured_error.getvalue()
        if stderr_value:
            errors.extend(stderr_value.strip().split('\n'))
    
    finally:
        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    execution_time = time.time() - start_time
    return output, errors, execution_time

@app.get("/")
async def root():
    # Check if frontend build exists
    dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
    if os.path.exists(dist_path) and os.path.exists(os.path.join(dist_path, "index.html")):
        return FileResponse(os.path.join(dist_path, "index.html"))
    else:
        return {"message": "icotes Backend API", "version": "1.0.0", "frontend": "not built"}

@app.get("/health")
async def health_check():
    """Health check endpoint with enhanced terminal information"""
    try:
        if TERMINAL_AVAILABLE and terminal_manager:
            terminal_health = terminal_manager.get_terminal_health()
        else:
            terminal_health = {"active_terminals": 0, "status": "unavailable"}
        
        return {
            "status": "healthy",
            "message": "Backend is running",
            "terminal_health": terminal_health
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy", 
            "message": f"Backend error: {str(e)}",
            "terminal_health": {"active_terminals": 0, "error": str(e)}
        }

@app.post("/execute", response_model=CodeExecutionResponse)
async def execute_code(request: CodeExecutionRequest):
    """Execute code and return results"""
    logger.info(f"Executing {request.language} code")
    
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

@app.get("/api")
async def api_root():
    return {"message": "icotes Backend API", "version": "1.0.0"}

@app.get("/api/health")
async def api_health():
    return {"status": "healthy", "connections": len(manager.active_connections)}

@app.post("/api/execute", response_model=CodeExecutionResponse)
async def api_execute_code(request: CodeExecutionRequest):
    """Execute code and return results (API endpoint)"""
    logger.info(f"Executing {request.language} code")
    
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

@app.get("/api/terminal/health")
async def terminal_health():
    """Health check specifically for terminal functionality"""
    if TERMINAL_AVAILABLE and terminal_manager:
        return terminal_manager.get_terminal_health()
    else:
        return {"active_terminals": 0, "status": "unavailable"}

# Clipboard API endpoints
class ClipboardWriteRequest(BaseModel):
    text: str

class ClipboardResponse(BaseModel):
    success: bool
    message: str = ""

class ClipboardReadResponse(BaseModel):
    text: str
    success: bool

@app.post("/api/clipboard/write", response_model=ClipboardResponse)
async def write_clipboard(request: ClipboardWriteRequest):
    """Write text to server-side clipboard"""
    try:
        success = server_clipboard.write(request.text)
        return ClipboardResponse(
            success=success,
            message=f"Copied {len(request.text)} characters to clipboard"
        )
    except Exception as e:
        logger.error(f"Clipboard write error: {e}")
        return ClipboardResponse(
            success=False,
            message=f"Failed to write to clipboard: {str(e)}"
        )

@app.get("/api/clipboard/read", response_model=ClipboardReadResponse)
async def read_clipboard():
    """Read text from server-side clipboard"""
    try:
        text = server_clipboard.read()
        return ClipboardReadResponse(
            text=text,
            success=True
        )
    except Exception as e:
        logger.error(f"Clipboard read error: {e}")
        return ClipboardReadResponse(
            text="",
            success=False
        )

@app.delete("/api/clipboard/clear", response_model=ClipboardResponse)
async def clear_clipboard():
    """Clear server-side clipboard"""
    try:
        success = server_clipboard.clear()
        return ClipboardResponse(
            success=success,
            message="Clipboard cleared"
        )
    except Exception as e:
        logger.error(f"Clipboard clear error: {e}")
        return ClipboardResponse(
            success=False,
            message=f"Failed to clear clipboard: {str(e)}"
        )

@app.get("/api/clipboard/history")
async def get_clipboard_history():
    """Get clipboard history"""
    try:
        history = server_clipboard.get_history()
        return {
            "history": history,
            "success": True
        }
    except Exception as e:
        logger.error(f"Clipboard history error: {e}")
        return {
            "history": [],
            "success": False,
            "message": f"Failed to get clipboard history: {str(e)}"
        }

@app.get("/api/clipboard/info")
async def get_clipboard_info():
    """Get clipboard system information"""
    try:
        info = {
            "system_clipboard_available": server_clipboard.system_clipboard_available,
            "clipboard_type": getattr(server_clipboard, 'clipboard_type', 'system'),
            "success": True
        }
        
        # Add file path if using file-based clipboard
        if hasattr(server_clipboard, 'clipboard_file'):
            info["clipboard_file"] = server_clipboard.clipboard_file
            info["clipboard_dir"] = server_clipboard.clipboard_dir
            info["message"] = f"File-based clipboard: {server_clipboard.clipboard_file}"
        else:
            info["message"] = "System clipboard integration available"
            
        return info
    except Exception as e:
        logger.error(f"Clipboard info error: {e}")
        return {
            "success": False,
            "message": f"Failed to get clipboard info: {str(e)}"
        }

@app.websocket("/ws/terminal/{terminal_id}")
async def terminal_websocket(websocket: WebSocket, terminal_id: str):
    """WebSocket endpoint for terminal connections with PTY support and optimized performance"""
    logger.info(f"Terminal WebSocket connection attempt: {terminal_id}")
    
    if not TERMINAL_AVAILABLE or not terminal_manager:
        await websocket.accept()
        await websocket.send_text("Terminal functionality not available")
        await websocket.close()
        return
    
    try:
        master_fd, proc = await terminal_manager.connect_terminal(websocket, terminal_id)
        logger.info(f"Terminal session started for {terminal_id}")
        
        # Store tasks for cleanup
        conn = terminal_manager.terminal_connections[terminal_id]
        conn['read_task'] = asyncio.create_task(
            terminal_manager.read_from_terminal(websocket, master_fd)
        )
        conn['write_task'] = asyncio.create_task(
            terminal_manager.write_to_terminal(websocket, master_fd)
        )
        
        # Wait for either task to complete
        await asyncio.gather(conn['read_task'], conn['write_task'], return_exceptions=True)
        
    except Exception as e:
        logger.error(f"Terminal WebSocket error: {e}")
    finally:
        if terminal_manager:
            terminal_manager.disconnect_terminal(terminal_id)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
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
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


def main():
    """Main entry point with CLI argument handling"""
    args = parse_arguments()
    
    # Handle clipboard commands (these need async)
    if args.stdin_to_clipboard:
        asyncio.run(handle_stdin_to_clipboard())
        return
    elif args.clipboard_to_stdout:
        asyncio.run(handle_clipboard_to_stdout())
        return
    
    # Start server (this should NOT be async)
    import os
    
    # Use CLI args first, then environment variables
    host = args.host if args.host != '0.0.0.0' else os.environ.get("BACKEND_HOST", os.environ.get("HOST", "0.0.0.0"))
    port = args.port if args.port != 8000 else int(os.environ.get("BACKEND_PORT", os.environ.get("PORT", 8000)))
    
    # Log the configuration for debugging
    logger.info(f"Starting server on {host}:{port}")
    logger.info(f"Environment variables: PORT={os.environ.get('PORT')}, BACKEND_PORT={os.environ.get('BACKEND_PORT')}")
    
    import uvicorn
    uvicorn.run(app, host=host, port=port, reload=args.reload)

# Add catch-all route for React app (must be after all other routes)
@app.get("/{catch_all:path}")
async def serve_react_app(catch_all: str):
    """Serve React app for all non-API routes"""
    # Skip API routes and WebSocket routes
    if catch_all.startswith(('api/', 'ws/', 'docs', 'redoc', 'openapi.json')):
        raise HTTPException(status_code=404, detail="Not found")
    
    dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
    if os.path.exists(dist_path):
        # First, check if the requested file exists (for static assets)
        file_path = os.path.join(dist_path, catch_all)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # If not a static file, serve index.html for SPA routing
        index_path = os.path.join(dist_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
    
    # Fallback for development
    return {"message": "React app not built. Run 'npm run build' first."}

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='icotes Backend Server')
    
    # Server options
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
    
    # Clipboard options
    parser.add_argument('--stdin-to-clipboard', '-c', action='store_true', 
                       help='Read from stdin and send to system clipboard')
    parser.add_argument('--clipboard-to-stdout', action='store_true',
                       help='Read from system clipboard and send to stdout')
    
    return parser.parse_args()

async def handle_stdin_to_clipboard():
    """Handle --stdin-to-clipboard command"""
    try:
        # Read from stdin
        stdin_data = sys.stdin.read()
        
        # Initialize clipboard
        clipboard = ServerClipboard()
        
        # Write to clipboard (this will handle both server buffer and system clipboard)
        success = clipboard.write(stdin_data)
        
        if success:
            logger.info(f"✓ Successfully copied {len(stdin_data)} characters to clipboard")
            print(f"✓ Copied {len(stdin_data)} characters to clipboard", file=sys.stderr)
            sys.exit(0)
        else:
            logger.error("✗ Failed to copy to clipboard")
            print("✗ Failed to copy to clipboard", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error in stdin-to-clipboard: {e}")
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)

async def handle_clipboard_to_stdout():
    """Handle --clipboard-to-stdout command"""
    try:
        # Initialize clipboard
        clipboard = ServerClipboard()
        
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

if __name__ == "__main__":
    main()
