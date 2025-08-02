# ICPY Backend Agent SDK Documentation

**Version**: 1.0.0  
**Date**: July 16, 2025  
**Target**: AI Agents & Developers

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [REST API Reference](#rest-api-reference)
4. [CLI Usage Guide](#cli-usage-guide)
5. [WebSocket API](#websocket-api)
6. [Service Architecture](#service-architecture)
7. [Code Examples](#code-examples)
8. [Error Handling](#error-handling)
9. [Development Guide](#development-guide)

---

## Quick Start

### Prerequisites
- Python 3.12+
- Virtual environment recommended
- Port 8000 available (or specify custom port)

### Installation & Setup
```bash
# 1. Navigate to backend directory
cd backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python main.py

# 4. Test connectivity
curl http://localhost:8000/health
```

### First API Call
```bash
# Get backend status
curl http://localhost:8000/health

# List available workspaces
curl http://localhost:8000/api/workspaces

# Create a terminal session
curl -X POST http://localhost:8000/api/terminals \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## Architecture Overview

The icpy backend follows a **modular, event-driven architecture** with these key components:

### Core Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   REST API      │    │  WebSocket API  │    │   CLI Interface │
│   (HTTP/JSON)   │    │  (Real-time)    │    │   (Command)     │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
              ┌─────────────────────────────────────┐
              │         Message Broker             │
              │     (Event Distribution)           │
              └─────────────────┬───────────────────┘
                                │
    ┌───────────────────────────┼───────────────────────────┐
    │                           │                           │
┌───▼────────┐    ┌─────────────▼──┐    ┌─────────────────▼──┐
│ Workspace  │    │   FileSystem   │    │    Terminal       │
│  Service   │    │    Service     │    │    Service        │
└────────────┘    └────────────────┘    └────────────────────┘
```

### Key Features
- **Event-driven**: Services communicate via message broker
- **Real-time**: WebSocket for live updates
- **Modular**: Independent services with clear APIs
- **Scalable**: Connection pooling and session management
- **Extensible**: Plugin-friendly architecture

---

## REST API Reference

**Base URL**: `http://localhost:8000` (or configured IP/port)

### Authentication
Currently no authentication required. Future versions will support API keys.

### Response Format
All API responses follow this structure:
```json
{
  "success": true,
  "data": {...},
  "message": "Optional message",
  "timestamp": 1752692796.736252
}
```

### Core Endpoints

#### Health Check
```http
GET /health
```
**Response**:
```json
{
  "status": "healthy",
  "services": {
    "icpy": true,
    "terminal": true,
    "clipboard": true
  },
  "timestamp": 1752692796.736252
}
```

#### Workspace Management

**List Workspaces**
```http
GET /api/workspaces
```
**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "ws-123",
      "name": "Main Workspace",
      "path": "/path/to/workspace",
      "active": true,
      "created_at": "2025-07-16T10:00:00Z"
    }
  ]
}
```

**Get Workspace**
```http
GET /api/workspaces/{workspace_id}
```

**Create Workspace**
```http
POST /api/workspaces
Content-Type: application/json

{
  "name": "New Workspace",
  "path": "/path/to/workspace"
}
```

**Activate Workspace**
```http
POST /api/workspaces/{workspace_id}/activate
```

#### File Operations

**List Directory**
```http
GET /api/files?path=/path/to/workspace
```

**Get File Content**
```http
GET /api/files/content?path=/path/to/workspace/file.py
```
**Response**:
```json
{
  "success": true,
  "data": {
    "content": "file content here",
    "size": 1024,
    "modified": "2025-07-16T10:00:00Z",
    "mime_type": "text/plain"
  }
}
```

**Create/Update File**
```http
POST /api/files
Content-Type: application/json

{
  "path": "/path/to/workspace/newfile.py",
  "content": "print('Hello, World!')"
}
```

**Delete File**
```http
DELETE /api/files?path=/path/to/workspace/file.py
```

**Search Files**
```http
GET /api/files/search?query=function&path=/path/to/workspace
```

#### Terminal Management

**List Terminals**
```http
GET /api/terminals
```
**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "term-123",
      "name": "Terminal 1",
      "state": "running",
      "pid": 1234,
      "created_at": "2025-07-16T10:00:00Z",
      "last_activity": "2025-07-16T10:05:00Z"
    }
  ]
}
```

**Create Terminal**
```http
POST /api/terminals
Content-Type: application/json

{
  "name": "My Terminal",
  "shell": "/bin/bash",
  "cwd": "/path/to/workspace",
  "env": {"CUSTOM_VAR": "value"}
}
```

**Get Terminal Info**
```http
GET /api/terminals/{terminal_id}
```

**Send Input to Terminal**
```http
POST /api/terminals/{terminal_id}/input
Content-Type: application/json

{
  "data": "ls -la\n"
}
```

**Resize Terminal**
```http
POST /api/terminals/{terminal_id}/resize
Content-Type: application/json

{
  "rows": 24,
  "cols": 80
}
```

#### Legacy Endpoints

**Execute Code**
```http
POST /execute
Content-Type: application/json

{
  "code": "print('Hello, World!')",
  "language": "python"
}
```

**Clipboard Operations**
```http
# Set clipboard
POST /clipboard
Content-Type: application/json
{
  "text": "content to copy"
}

# Get clipboard
GET /clipboard

# Get clipboard history
GET /clipboard/history
```

---

## CLI Usage Guide

The icpy CLI provides command-line access to all backend functionality.

### Installation
```bash
cd backend
# CLI is available as: python icpy_cli.py
```

### Basic Usage
```bash
# Get help
python icpy_cli.py --help

# Check backend status
python icpy_cli.py --status

# Open a file
python icpy_cli.py /path/to/file.py

# Create a terminal
python icpy_cli.py --terminal

# List terminals
python icpy_cli.py --terminal-list

# List workspaces
python icpy_cli.py --workspace list
```

### Configuration
```bash
# Use custom backend URL
python icpy_cli.py --backend-url http://192.168.1.100:8000 --status

# Enable verbose output
python icpy_cli.py --verbose --status

# Set timeout
python icpy_cli.py --timeout 60 --status
```

### Advanced Usage
```bash
# Interactive mode
python icpy_cli.py --interactive

# List directory contents
python icpy_cli.py --list /path/to/workspace

# Work with specific workspace
python icpy_cli.py --workspace-id ws-123 --status
```

---

## WebSocket API

Real-time communication for live updates and terminal interactions.

### Connection Endpoints

**Enhanced WebSocket** (Recommended)
```
ws://localhost:8000/ws/enhanced
```

**Terminal WebSocket**
```
ws://localhost:8000/ws/terminal/{terminal_id}
```

**Legacy WebSocket**
```
ws://localhost:8000/ws
```

### Message Format
```json
{
  "type": "message_type",
  "data": {...},
  "timestamp": 1752692796.736252,
  "id": "unique-message-id"
}
```

### Enhanced WebSocket Messages

**Connection**
```json
{
  "type": "connect",
  "data": {
    "client_id": "optional-client-id",
    "capabilities": ["terminal", "workspace", "filesystem"]
  }
}
```

**Subscribe to Events**
```json
{
  "type": "subscribe",
  "data": {
    "events": ["file_changed", "terminal_output", "workspace_updated"]
  }
}
```

**File Change Event**
```json
{
  "type": "file_changed",
  "data": {
    "path": "/path/to/workspace/file.py",
    "event": "modified",
    "timestamp": "2025-07-16T10:00:00Z"
  }
}
```

### Terminal WebSocket
Direct terminal I/O:
```javascript
// Connect to terminal
const ws = new WebSocket('ws://localhost:8000/ws/terminal/term-123');

// Send input
ws.send('ls -la\n');

// Receive output
ws.onmessage = (event) => {
  console.log('Terminal output:', event.data);
};
```

---

## Service Architecture

### Message Broker
Central event distribution system.

**Key Events**:
- `file.changed` - File modifications
- `terminal.output` - Terminal output
- `workspace.activated` - Workspace changes
- `service.initialized` - Service startup
- `connection.established` - Client connections

### Workspace Service
Manages workspace state and organization.

**Key Methods**:
- `get_workspace_list()` - List all workspaces
- `create_workspace(name, path)` - Create new workspace
- `switch_workspace(id)` - Change active workspace
- `save_workspace_state()` - Persist workspace state

### FileSystem Service
Handles file operations and monitoring.

**Key Methods**:
- `read_file(path)` - Get file content
- `write_file(path, content)` - Save file
- `list_directory(path)` - List directory contents
- `search_files(query, path)` - Search in files
- `get_file_info(path)` - Get file metadata

**File Watching**: Automatically monitors file changes in workspace directories.

### Terminal Service
Manages terminal sessions and I/O.

**Key Methods**:
- `create_session(name, config)` - Create terminal session
- `list_sessions()` - Get active terminals
- `send_input(session_id, data)` - Send command to terminal
- `get_session(session_id)` - Get terminal info
- `destroy_session(session_id)` - Close terminal

**Terminal Config**:
```python
{
  "shell": "/bin/bash",
  "term": "xterm-256color",
  "cols": 80,
  "rows": 24,
  "env": {"TERM": "xterm-256color"},
  "cwd": "/path/to/workspace"
}
```

---

## Code Examples

### Python Client Example
```python
import requests
import json

class IcpyClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_status(self):
        response = self.session.get(f"{self.base_url}/health")
        return response.json()
    
    def list_workspaces(self):
        response = self.session.get(f"{self.base_url}/api/workspaces")
        return response.json()["data"]
    
    def create_terminal(self, name="Terminal"):
        data = {"name": name}
        response = self.session.post(
            f"{self.base_url}/api/terminals",
            json=data
        )
        return response.json()["data"]
    
    def read_file(self, path):
        response = self.session.get(
            f"{self.base_url}/api/files/content",
            params={"path": path}
        )
        return response.json()["data"]["content"]

# Usage
client = IcpyClient()
status = client.get_status()
workspaces = client.list_workspaces()
terminal = client.create_terminal("My Terminal")
content = client.read_file("/path/to/workspace/file.py")
```

### JavaScript Client Example
```javascript
class IcpyClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async getStatus() {
        const response = await fetch(`${this.baseUrl}/health`);
        return await response.json();
    }
    
    async listWorkspaces() {
        const response = await fetch(`${this.baseUrl}/api/workspaces`);
        const data = await response.json();
        return data.data;
    }
    
    async createTerminal(name = 'Terminal') {
        const response = await fetch(`${this.baseUrl}/api/terminals`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name})
        });
        const data = await response.json();
        return data.data;
    }
    
    async readFile(path) {
        const response = await fetch(
            `${this.baseUrl}/api/files/content?path=${encodeURIComponent(path)}`
        );
        const data = await response.json();
        return data.data.content;
    }
}

// Usage
const client = new IcpyClient();
const status = await client.getStatus();
const workspaces = await client.listWorkspaces();
const terminal = await client.createTerminal();
const content = await client.readFile('/path/to/workspace/file.py');
```

### WebSocket Client Example
```javascript
class IcpyWebSocketClient {
    constructor(url = 'ws://localhost:8000/ws/enhanced') {
        this.url = url;
        this.ws = null;
        this.handlers = {};
    }
    
    connect() {
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
            console.log('Connected to icpy backend');
            this.send('connect', {
                client_id: 'my-client',
                capabilities: ['terminal', 'workspace', 'filesystem']
            });
        };
        
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (this.handlers[message.type]) {
                this.handlers[message.type](message.data);
            }
        };
        
        this.ws.onclose = () => {
            console.log('Disconnected from icpy backend');
        };
    }
    
    send(type, data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({type, data}));
        }
    }
    
    on(eventType, handler) {
        this.handlers[eventType] = handler;
    }
    
    subscribe(events) {
        this.send('subscribe', {events});
    }
}

// Usage
const wsClient = new IcpyWebSocketClient();
wsClient.connect();

wsClient.on('file_changed', (data) => {
    console.log('File changed:', data.path);
});

wsClient.subscribe(['file_changed', 'terminal_output']);
```

### CLI Integration Example
```bash
#!/bin/bash
# Example script using icpy CLI

# Check if backend is running
if python icpy_cli.py --status > /dev/null 2>&1; then
    echo "Backend is running"
else
    echo "Backend is not running"
    exit 1
fi

# Create a terminal for this session
TERMINAL_ID=$(python icpy_cli.py --terminal | grep -o 'Terminal created: [^[:space:]]*' | cut -d' ' -f3)
echo "Created terminal: $TERMINAL_ID"

# Open a file
python icpy_cli.py /path/to/workspace/main.py

# List terminals
echo "Active terminals:"
python icpy_cli.py --terminal-list
```

---

## Error Handling

### Common HTTP Status Codes
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (resource doesn't exist)
- `405` - Method Not Allowed
- `500` - Internal Server Error

### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "FILE_NOT_FOUND",
    "message": "File not found: /path/to/file.py",
    "details": {
      "path": "/path/to/file.py",
      "suggestion": "Check if the file exists and path is correct"
    }
  },
  "timestamp": 1752692796.736252
}
```

### Common Errors and Solutions

**Backend Not Running**
```bash
# Error: Connection refused
# Solution: Start the backend
python main.py
```

**File Not Found**
```bash
# Error: File not found: /path/to/file.py
# Solution: Check file path and permissions
ls -la /path/to/file.py
```

**Permission Denied**
```bash
# Error: Permission denied
# Solution: Check file permissions or run with appropriate user
chmod +r /path/to/file.py
```

**Port Already in Use**
```bash
# Error: Port 8000 already in use
# Solution: Use different port or kill existing process
python main.py --port 8001
# Or kill existing process
lsof -ti:8000 | xargs kill
```

### Debugging Tips

**Enable Verbose Logging**
```bash
python main.py --debug
```

**Check Service Status**
```bash
curl http://localhost:8000/health
```

**Monitor WebSocket Connection**
```javascript
ws.addEventListener('error', (error) => {
    console.error('WebSocket error:', error);
});
```

---

## Development Guide

### Setting Up Development Environment

**1. Clone and Setup**
```bash
git clone <repository>
cd <repository>/backend

# Modern approach with UV (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv sync --frozen --no-dev

# Alternative: Direct pip installation
pip install -r requirements.txt
```

**2. Development Server**
```bash
# Start with auto-reload
python main.py --reload --debug

# Start with custom configuration
python main.py --host 0.0.0.0 --port 8001 --debug
```

### Project Structure
```
backend/
├── main.py              # Main server entry point
├── icpy_cli.py          # CLI entry point
├── requirements.txt     # Python dependencies
├── icpy/               # Core icpy module
│   ├── api/            # API layer
│   │   ├── rest_api.py
│   │   └── websocket_api.py
│   ├── cli/            # CLI interface
│   │   ├── http_client.py
│   │   ├── command_handlers.py
│   │   └── icpy_cli.py
│   ├── core/           # Core components
│   │   ├── message_broker.py
│   │   └── connection_manager.py
│   └── services/       # Business logic
│       ├── workspace_service.py
│       ├── filesystem_service.py
│       └── terminal_service.py
└── tests/              # Test files
    └── icpy/
        ├── test_cli_interface.py
        └── ...
```

### Adding New Endpoints

**1. Add to REST API**
```python
# In icpy/api/rest_api.py
@self.app.post("/api/my-endpoint")
async def my_endpoint(request: MyRequest):
    try:
        result = await self.my_service.do_something(request.data)
        return SuccessResponse(data=result)
    except Exception as e:
        logger.error(f"Error in my endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**2. Add CLI Support**
```python
# In icpy/cli/command_handlers.py
def handle_my_command(self, data: str) -> bool:
    try:
        if not self.client.check_connection():
            print("Error: Cannot connect to backend")
            return False
        
        result = self.client.my_api_call(data)
        print(f"Success: {result}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
```

**3. Add to HTTP Client**
```python
# In icpy/cli/http_client.py
def my_api_call(self, data: str) -> Dict[str, Any]:
    response = self.make_request('POST', '/api/my-endpoint', {'data': data})
    return response.get('data', {})
```

### Testing

**Run Tests**
```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/icpy/test_cli_interface.py

# Run with coverage
pytest --cov=icpy tests/
```

**Manual Testing**
```bash
# Test REST API
curl -X POST http://localhost:8000/api/terminals -H "Content-Type: application/json" -d '{}'

# Test CLI
python icpy_cli.py --status

# Test WebSocket
# Use a WebSocket client tool or browser console
```

### Configuration

**Environment Variables**
```bash
export FRONTEND_URL=http://localhost:3000
export NODE_ENV=production
export SSL_KEYFILE=/path/to/key.pem
export SSL_CERTFILE=/path/to/cert.pem
```

**Default Configuration**
- Host: `0.0.0.0`
- Port: `8000`
- Backend URL: `http://localhost:8000`
- Timeout: `30` seconds
- Max file size: `100MB`
- Max clipboard history: `10` items

### Deployment

**Production Deployment**
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export NODE_ENV=production
export FRONTEND_URL=https://yourdomain.com

# Start server
python main.py --host 0.0.0.0 --port 8000
```

**Docker Deployment**
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Conclusion

This documentation provides complete coverage of the icpy backend system. For additional help:

1. **Check the health endpoint**: `curl http://localhost:8000/health`
2. **Use CLI help**: `python icpy_cli.py --help`
3. **Enable debug logging**: `python main.py --debug`
4. **Review service logs**: Check terminal output for detailed error messages

The icpy backend is designed to be agent-friendly with clear APIs, comprehensive error handling, and extensive automation capabilities. All endpoints are stateless and can be called programmatically for automation workflows.

For questions or issues, refer to the error handling section or enable debug logging for detailed troubleshooting information.
