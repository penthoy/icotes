# icotes Backend

A FastAPI backend for icotes that provides code execution capabilities and WebSocket communication.

## Features

- **Code Execution**: Execute Python code safely with output capture
- **WebSocket Support**: Real-time communication with the frontend
- **CORS Enabled**: Supports cross-origin requests from the frontend
- **Health Monitoring**: Health check endpoint for monitoring
- **Error Handling**: Comprehensive error handling and logging

## API Endpoints

### REST API

- `GET /` - API information
- `GET /health` - Health check and connection status
- `POST /execute` - Execute code synchronously

### WebSocket

- `WS /ws` - WebSocket connection for real-time communication

## Setup

**CRITICAL: Always use the virtual environment for any Python operations!**

1. Install Python 3.8+ and pip
2. Set up virtual environment and install dependencies:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # ALWAYS DO THIS FIRST!
   pip install -r requirements.txt
   ```

**Common mistake:** Running `python3` or `python` directly without `source venv/bin/activate` first will cause pydantic version conflicts and import errors.

## Development

```bash
# ALWAYS start with this:
cd backend
source venv/bin/activate

# Then run any Python commands:
python main.py
python -m pytest
python -c "from icpy.api import get_rest_api"
```
3. Start the server:
   ```bash
   python main.py
   ```

Or use the convenience script:
```bash
./start.sh
```

## API Usage

### Execute Code (REST)

```bash
curl -X POST "http://localhost:8000/execute" \
     -H "Content-Type: application/json" \
     -d '{
       "code": "print(\"Hello, World!\")",
       "language": "python"
     }'
```

### WebSocket Communication

Connect to `ws://localhost:8000/ws` and send messages:

```javascript
{
  "type": "execute_code",
  "code": "print('Hello from WebSocket!')",
  "language": "python"
}
```

## Development

The backend runs on port 8000 by default. For development:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Security Notes

- The current implementation executes Python code directly
- In production, consider using sandboxed execution environments
- Implement proper authentication and authorization
- Limit execution time and resources
