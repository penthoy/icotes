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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="iLabors Code Editor Backend", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    uvicorn.run(app, host="0.0.0.0", port=8000)
