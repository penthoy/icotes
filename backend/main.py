from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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
import pty
import os
import select
import termios
import struct
import fcntl
import signal
import subprocess
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="iLabors Code Editor Backend", version="1.0.0")

# Get allowed origins from environment
allowed_origins = []

# Add production domains if available
frontend_url = os.environ.get("FRONTEND_URL")
if frontend_url:
    allowed_origins.append(frontend_url)

# Add development origins for local development
if os.environ.get("NODE_ENV") != "production":
    allowed_origins.extend([
        "http://localhost:3000", 
        "http://localhost:5173", 
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
        "http://192.168.2.195:5173",
        "http://192.168.2.195:5174",
        "http://192.168.2.195:5175",
        "http://192.168.2.195:5176"
    ])

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
        self.terminal_connections: Dict[str, Dict] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connection established. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket connection closed. Total connections: {len(self.active_connections)}")

    async def connect_terminal(self, websocket: WebSocket, terminal_id: str):
        try:
            await websocket.accept()
            
            # Debug logging for production troubleshooting
            logger.info(f"WebSocket client: {websocket.client}")
            logger.info(f"WebSocket headers: {websocket.headers}")
            
            # Create a new terminal session
            logger.info(f"Creating PTY for terminal {terminal_id}")
            master_fd, slave_fd = pty.openpty()
            logger.info(f"PTY created: master_fd={master_fd}, slave_fd={slave_fd}")
            
            # Set terminal size (default to 80x24 if not specified)
            try:
                fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
            except Exception as e:
                logger.warning(f"Could not set terminal size: {e}")
            
            # Set terminal attributes for better compatibility and performance
            try:
                attrs = termios.tcgetattr(slave_fd)
                # Disable canonical mode for better real-time interaction
                attrs[3] &= ~termios.ICANON  # Disable canonical mode
                attrs[3] |= termios.ECHO | termios.ISIG  # Enable echo and signal processing
                # Set input/output processing for better performance
                attrs[0] |= termios.ICRNL  # Map CR to NL on input
                attrs[1] |= termios.ONLCR  # Map NL to CR-NL on output
                # Set minimum characters and timeout for immediate response
                attrs[6][termios.VMIN] = 0  # Minimum characters (0 for non-blocking)
                attrs[6][termios.VTIME] = 0  # Timeout (0 for immediate return)
                termios.tcsetattr(slave_fd, termios.TCSANOW, attrs)
            except Exception as e:
                logger.warning(f"Could not set terminal attributes: {e}")
            
            # Set environment variables for better terminal compatibility
            env = os.environ.copy()
            env.update({
                'TERM': 'xterm-256color',
                'SHELL': '/bin/bash',
                'HOME': os.path.expanduser('~'),
                'PATH': env.get('PATH', '/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin'),
                'LANG': 'C.UTF-8',
                'LC_ALL': 'C.UTF-8',
                'PS1': '\\[\\033[01;32m\\]\\u@\\h\\[\\033[00m\\]:\\[\\033[01;34m\\]\\w\\[\\033[00m\\]\\$ ',
                'USER': env.get('USER', 'app'),
                'LOGNAME': env.get('LOGNAME', 'app'),
            })
            
            # Find bash executable
            bash_path = None
            for path in ['/bin/bash', '/usr/bin/bash', '/usr/local/bin/bash']:
                if os.path.exists(path):
                    bash_path = path
                    break
            
            if not bash_path:
                raise Exception("Bash executable not found")
                
            logger.info(f"Using bash at: {bash_path}")
            
            # Start bash in the new terminal
            proc = subprocess.Popen(
                [bash_path, "-i"],  # Interactive bash
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                preexec_fn=os.setsid,
                env=env,
                cwd=os.path.expanduser('~')
            )
            logger.info(f"Bash process started with PID: {proc.pid}")
            
            # Close slave fd in parent process
            os.close(slave_fd)
            
            # Set master fd to non-blocking for better performance
            try:
                flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
                fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            except Exception as e:
                logger.warning(f"Could not set master fd to non-blocking: {e}")
            
            # Store terminal connection info
            self.terminal_connections[terminal_id] = {
                'websocket': websocket,
                'master_fd': master_fd,
                'process': proc,
                'read_task': None,
                'write_task': None
            }
            
            logger.info(f"Terminal connection established: {terminal_id}")
            return master_fd, proc
            
        except Exception as e:
            logger.error(f"Error creating terminal session: {e}")
            raise e

    def disconnect_terminal(self, terminal_id: str):
        if terminal_id in self.terminal_connections:
            conn = self.terminal_connections[terminal_id]
            
            # Cancel tasks
            if conn['read_task']:
                conn['read_task'].cancel()
            if conn['write_task']:
                conn['write_task'].cancel()
            
            # Close file descriptor
            try:
                os.close(conn['master_fd'])
            except:
                pass
            
            # Terminate process
            try:
                conn['process'].terminate()
                conn['process'].wait(timeout=1)
            except:
                try:
                    conn['process'].kill()
                except:
                    pass
            
            del self.terminal_connections[terminal_id]
            logger.info(f"Terminal connection closed: {terminal_id}")

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
    return {"message": "iLabors Code Editor Backend API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "connections": len(manager.active_connections)}

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
    return {"message": "iLabors Code Editor Backend API", "version": "1.0.0"}

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
    try:
        # Test if we can create a PTY
        import pty
        master_fd, slave_fd = pty.openpty()
        os.close(master_fd)
        os.close(slave_fd)
        
        # Test if bash is available
        bash_available = any(os.path.exists(path) for path in ['/bin/bash', '/usr/bin/bash', '/usr/local/bin/bash'])
        
        return {
            "status": "healthy",
            "pty_available": True,
            "bash_available": bash_available,
            "terminal_connections": len(manager.terminal_connections)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "pty_available": False,
            "bash_available": False,
            "terminal_connections": len(manager.terminal_connections)
        }

@app.websocket("/ws/terminal/{terminal_id}")
async def terminal_websocket(websocket: WebSocket, terminal_id: str):
    """WebSocket endpoint for terminal connections with PTY support and optimized performance"""
    logger.info(f"Terminal WebSocket connection attempt: {terminal_id}")
    try:
        master_fd, proc = await manager.connect_terminal(websocket, terminal_id)
        logger.info(f"Terminal session started for {terminal_id}")
        
        async def read_from_terminal():
            """Read from terminal and send to WebSocket with optimized performance"""
            while True:
                try:
                    # Use select with very short timeout for immediate response
                    ready, _, _ = select.select([master_fd], [], [], 0.001)
                    if ready:
                        # Read available data
                        data = os.read(master_fd, 4096)  # Increased buffer size
                        if data:
                            # Properly decode terminal data with better error handling
                            try:
                                decoded_data = data.decode('utf-8')
                            except UnicodeDecodeError:
                                # Fallback to latin-1 for binary data
                                decoded_data = data.decode('latin-1')
                            
                            # Send data to WebSocket immediately
                            try:
                                await websocket.send_text(decoded_data)
                            except Exception as send_error:
                                logger.error(f"Error sending data to WebSocket: {send_error}")
                                break
                        else:
                            # EOF reached
                            break
                    else:
                        # No data available, yield control briefly
                        await asyncio.sleep(0.001)
                except Exception as e:
                    logger.error(f"Error reading from terminal: {e}")
                    break
        
        async def write_to_terminal():
            """Read from WebSocket and write to terminal with optimized performance"""
            while True:
                try:
                    data = await websocket.receive_text()
                    
                    # Handle special messages
                    if data.startswith('{"type":'):
                        message = json.loads(data)
                        if message.get('type') == 'resize':
                            # Handle terminal resize
                            cols = message.get('cols', 80)
                            rows = message.get('rows', 24)
                            try:
                                # Set terminal size
                                fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
                                logger.info(f"Terminal resized to {cols}x{rows}")
                            except Exception as e:
                                logger.error(f"Error resizing terminal: {e}")
                        continue
                    
                    # Regular terminal input - write directly for maximum performance
                    try:
                        os.write(master_fd, data.encode('utf-8'))
                    except BlockingIOError:
                        # Handle non-blocking write
                        await asyncio.sleep(0.001)
                        try:
                            os.write(master_fd, data.encode('utf-8'))
                        except:
                            pass
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Error writing to terminal: {e}")
                    break
        
        # Store tasks for cleanup
        conn = manager.terminal_connections[terminal_id]
        conn['read_task'] = asyncio.create_task(read_from_terminal())
        conn['write_task'] = asyncio.create_task(write_to_terminal())
        
        # Wait for either task to complete
        await asyncio.gather(conn['read_task'], conn['write_task'], return_exceptions=True)
        
    except Exception as e:
        logger.error(f"Terminal WebSocket error: {e}")
    finally:
        manager.disconnect_terminal(terminal_id)

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

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get host and port from environment variables
    host = os.environ.get("BACKEND_HOST", "0.0.0.0")
    port = int(os.environ.get("BACKEND_PORT", 8000))
    
    print(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

# Add catch-all route for React app (must be after all other routes)
@app.get("/{catch_all:path}")
async def serve_react_app(catch_all: str):
    """Serve React app for all non-API routes"""
    dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
    if os.path.exists(dist_path):
        index_path = os.path.join(dist_path, "index.html")
        if os.path.exists(index_path):
            from fastapi.responses import FileResponse
            return FileResponse(index_path)
    
    # Fallback for development
    return {"message": "React app not built. Run 'npm run build' first."}
