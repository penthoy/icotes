# Single-Port Solution Architecture

## Problem Analysis
Applications with separate frontend and backend servers often face connectivity issues in various deployment environments. The traditional approach of running frontend on one port and backend on another can create complications in remote development environments, containerized deployments, and cloud platforms.

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
- In production, the application can run on standard web ports (80/443)
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

## Deployment for Production

### Single Command Deployment
```bash
# Build and deploy
./deploy-production.sh
```

### Manual Deployment
```bash
# 1. Build React app
npm run build

# 2. Start FastAPI server on desired port
cd backend
PORT=80 python3 main.py
```

## Testing Results
- ✅ **Port 80 deployment works**: Application serves from `http://localhost`
- ✅ **WebSocket connections work**: Terminal connects to `ws://localhost/ws/terminal/{id}`
- ✅ **Static files served**: React app loads from FastAPI backend
- ✅ **Terminal functionality**: PTY sessions work correctly
- ✅ **Code execution**: REST API endpoints work

## Deployment Environment Compatibility
- **Single Port**: Only needs one port for both frontend and backend
- **Dynamic URLs**: Automatically adapts to any domain/subdomain
- **HTTPS Support**: WebSocket automatically uses `wss://` for HTTPS sites
- **No Port Conflicts**: Everything runs through the same port

## Benefits of Single-Port Architecture
1. **Simplified deployment**: No need to manage multiple ports
2. **Better security**: Reduced attack surface with fewer open ports
3. **Easier configuration**: Single endpoint for all services
4. **Cloud-friendly**: Compatible with most cloud platforms and containers
5. **Remote development**: Works in various remote development environments

The solution is **technically sound** and **production-ready** for various deployment scenarios!
