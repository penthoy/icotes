# Single-Port Solution for Tempo Environment

## Problem Analysis
You were correct that the application was trying to connect to `ws://localhost:8000` which doesn't work in the Tempo environment. In Tempo, the application is served from URLs like `https://frosty-volhard3-k47y8.view-3.tempo-dev.app`, and there's no direct access to other ports.

## Solution Implemented

### 1. **Single-Port Architecture**
- **Everything runs on ONE port** (port 80 in production, configurable)
- FastAPI backend serves both:
  - Static React application (built files)
  - WebSocket endpoints for terminal connections
  - REST API endpoints for code execution

### 2. **Dynamic URL Construction**
- **Frontend automatically detects the current host/port**
- WebSocket URLs constructed as: `wss://current-host/ws/terminal/{id}`
- REST API URLs use the current page origin
- No hardcoded `localhost:8000` references

### 3. **Production Configuration**
- Backend reads `PORT` environment variable (defaults to 8000 for dev)
- In Tempo, the application will run on port 80
- All connections (HTTP, WebSocket) use the same port

## Key Changes Made

### Backend (`/app/backend/main.py`)
```python
# Port configuration from environment
port = int(os.environ.get("PORT", 8000))
```

### Frontend (`/app/src/lib/codeExecutor.ts`)
```typescript
// Dynamic WebSocket URL construction
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const host = window.location.host;
this.url = `${protocol}//${host}/ws`;
```

### Frontend (`/app/src/components/XTerminal.tsx`)
```typescript
// Dynamic terminal WebSocket URL
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const host = window.location.host;
const wsUrl = `${protocol}//${host}/ws/terminal/${terminalId.current}`;
```

## Deployment for Tempo

### Single Command Deployment
```bash
# Build and deploy
./deploy-production.sh
```

### Manual Deployment
```bash
# 1. Build React app
npm run build

# 2. Start FastAPI server on port 80
cd backend
PORT=80 python3 main.py
```

## Testing Results
- ✅ **Port 80 deployment works**: Application serves from `http://localhost`
- ✅ **WebSocket connections work**: Terminal connects to `ws://localhost/ws/terminal/{id}`
- ✅ **Static files served**: React app loads from FastAPI backend
- ✅ **Terminal functionality**: PTY sessions work correctly
- ✅ **Code execution**: REST API endpoints work

## Tempo Environment Compatibility
- **Single Port**: Only needs port 80 (or whatever port Tempo exposes)
- **Dynamic URLs**: Automatically adapts to `https://your-app.tempo-dev.app`
- **HTTPS Support**: WebSocket automatically uses `wss://` for HTTPS sites
- **No Port Conflicts**: Everything runs through the same port

## Why This Works in Tempo
1. **No separate port needed**: Terminal WebSocket uses same port as web app
2. **Dynamic host detection**: Works with any domain/subdomain
3. **HTTPS compatible**: Automatically uses secure WebSocket (wss://) when needed
4. **Production ready**: FastAPI serves both static files and WebSocket endpoints

The solution is **technically sound** and **production-ready** for the Tempo environment!
