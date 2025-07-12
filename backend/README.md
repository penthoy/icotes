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

1. Install Python 3.8+ and pip
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
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
