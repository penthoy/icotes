# Environment Configuration Guide

This guide explains how to configure icotes for different deployment environments using environment variables.

## Environment Variables

The application uses the following environment variables:

### Backend Configuration
- `BACKEND_HOST`: Host address for the backend server (default: `localhost`)
- `BACKEND_PORT`: Port number for the backend server (default: `8000`)
- `BACKEND_URL`: Full URL for the backend API (default: `http://localhost:8000`)

### Frontend Configuration
- `FRONTEND_HOST`: Host address for the frontend server (default: `localhost`)
- `FRONTEND_PORT`: Port number for the frontend server (default: `5173`)
- `FRONTEND_URL`: Full URL for the frontend application (default: `http://localhost:5173`)

### API Configuration (Used by Frontend)
- `VITE_API_URL`: Backend API URL that the frontend connects to (default: `http://localhost:8000`)
- `VITE_WS_URL`: WebSocket URL for real-time communication (default: `ws://localhost:8000`)

### Environment
- `NODE_ENV`: Environment mode (`development` or `production`)

## Configuration Files

### `.env` (Current Configuration)
```bash
# Backend Configuration
BACKEND_HOST=localhost
BACKEND_PORT=8000
BACKEND_URL=http://localhost:8000

# Frontend Configuration
FRONTEND_HOST=localhost
FRONTEND_PORT=5173
FRONTEND_URL=http://localhost:5173

# API Configuration
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000

# Environment
NODE_ENV=development
```

### `.env.production` (Production Example)
```bash
# Backend Configuration
BACKEND_HOST=your-domain.com
BACKEND_PORT=8000
BACKEND_URL=https://your-domain.com:8000

# Frontend Configuration  
FRONTEND_HOST=your-domain.com
FRONTEND_PORT=3000
FRONTEND_URL=https://your-domain.com

# API Configuration
VITE_API_URL=https://your-domain.com:8000
VITE_WS_URL=wss://your-domain.com:8000

# Environment
NODE_ENV=production
```

## Deployment Scenarios

### 1. Local Development (Default)
No changes needed. The current `.env` file is configured for local development.

### 2. Development with Custom Domain
Update the `.env` file:
```bash
BACKEND_HOST=dev.yourcompany.com
FRONTEND_HOST=dev.yourcompany.com
VITE_API_URL=http://dev.yourcompany.com:8000
VITE_WS_URL=ws://dev.yourcompany.com:8000
```

### 3. Production Deployment
Copy `.env.production` to `.env` and update with your actual domain:
```bash
cp .env.production .env
# Edit .env with your actual domain name
```

### 4. Docker/Container Deployment
Set environment variables in your Docker Compose or Kubernetes configuration:
```yaml
# docker-compose.yml example
services:
  backend:
    environment:
      - BACKEND_HOST=0.0.0.0
      - BACKEND_PORT=8000
  frontend:
    environment:
      - VITE_API_URL=http://backend:8000
      - VITE_WS_URL=ws://backend:8000
```

### 5. Cloud Deployment (AWS, Azure, GCP)
Set environment variables in your cloud platform's configuration:
```bash
# Example for cloud deployment
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
VITE_API_URL=https://api.yourapp.com
VITE_WS_URL=wss://api.yourapp.com
```

## How It Works

### Backend
- The FastAPI server reads `BACKEND_HOST` and `BACKEND_PORT` to determine where to bind
- CORS is configured to allow connections from `FRONTEND_URL`
- The server logs show which host and port it's running on

### Frontend
- Vite development server uses `FRONTEND_HOST` and `FRONTEND_PORT`
- The frontend code uses `VITE_API_URL` and `VITE_WS_URL` to connect to the backend
- All API calls and WebSocket connections are routed through these URLs

### WebSocket Connections
The application uses WebSocket connections for:
- Real-time code execution
- Terminal functionality
- Live updates

Make sure your WebSocket URLs match your deployment setup:
- `ws://` for HTTP connections
- `wss://` for HTTPS connections

## Testing Configuration

After updating your `.env` file:

1. **Restart the servers**:
   ```bash
   ./start-dev.sh
   ```

2. **Check server status**:
   ```bash
   ./check-servers.sh
   ```

3. **Test the configuration**:
   - Frontend should be accessible at your configured `FRONTEND_URL`
   - Backend API should be accessible at your configured `BACKEND_URL`
   - WebSocket connections should work for code execution and terminal

## Troubleshooting

### Common Issues

1. **CORS Errors**:
   - Ensure `FRONTEND_URL` is correctly set in your `.env`
   - Check that the backend CORS configuration includes your frontend URL

2. **WebSocket Connection Failed**:
   - Verify `VITE_WS_URL` matches your backend WebSocket endpoint
   - Check if your deployment supports WebSocket connections

3. **API Calls Failing**:
   - Confirm `VITE_API_URL` points to your backend server
   - Ensure the backend is running and accessible

4. **Environment Variables Not Loaded**:
   - Make sure your `.env` file is in the project root
   - Restart the servers after changing environment variables
   - Check that there are no syntax errors in your `.env` file

### Debug Commands

```bash
# Check environment variables
echo $BACKEND_HOST
echo $VITE_API_URL

# Test backend connectivity
curl $BACKEND_URL

# Test frontend connectivity
curl $FRONTEND_URL
```

This configuration system allows you to easily switch between development, staging, and production environments without code changes.
