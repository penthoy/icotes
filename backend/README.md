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

**Modern approach using uv package manager (recommended):**

1. Install uv package manager:
   ```bash
   # Install uv (fast Python package manager)
   curl -LsSf https://astral.sh/uv/install.sh | sh
   export PATH="$HOME/.local/bin:$PATH"
   ```

2. Set up project environment:
   ```bash
   cd backend
   uv sync --frozen --no-dev  # Install from requirements.txt
   ```

**Alternative manual approach (if uv is not available):**

1. Install Python 3.11+ and pip:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

## Development

**Using uv (recommended):**

```bash
cd backend

# Run the server
uv run python main.py

# Run tests
uv run pytest

# Run specific test
uv run pytest tests/icpy/test_agentic_frameworks.py -v

# Execute any Python script
uv run python validate_step_6_1.py
```

**Alternative approach (without uv):**

```bash
cd backend

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
