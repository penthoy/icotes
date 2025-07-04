# Tempo Environment Deployment Instructions

## Problem Summary
The terminal connection was failing in the Tempo environment because:
1. The application was running in development mode (Vite dev server)
2. WebSocket connections were trying to connect to the same host/port as the web page
3. But the web page was served by Vite (port 5173) while the WebSocket backend was on port 8000
4. In Tempo, only one port is exposed externally

## Solution
Run the application in **production mode** where:
- FastAPI backend serves both the React app AND the WebSocket endpoints
- Everything runs on the same port (configurable via PORT environment variable)
- WebSocket connections use the same host/port as the main application

## Deployment Instructions for Tempo

### Method 1: Use the startup script (Recommended)
```bash
# Run this command in the Tempo terminal
./start-tempo.sh
```

### Method 2: Manual deployment
```bash
# Step 1: Install backend dependencies
cd /app/backend
pip3 install -r requirements.txt

# Step 2: Build the React app
cd /app
npm run build

# Step 3: Start the FastAPI backend
cd /app/backend
python3 main.py
```

### Method 3: Use npm scripts
```bash
# This runs the production build and starts the backend
npm run dev
```

## How It Works in Tempo

1. **Single Port**: Everything runs on the PORT environment variable (default 8000)
2. **Production Build**: React app is built and served as static files by FastAPI
3. **WebSocket URLs**: Frontend automatically constructs WebSocket URLs using the current page's host/port
4. **No Development Server**: Vite dev server is not used in production

## Expected Behavior

When deployed correctly:
- Application accessible at: `https://your-app.tempo-dev.app/`
- WebSocket terminals connect to: `wss://your-app.tempo-dev.app/ws/terminal/{id}`
- All connections use the same host/port as the main application
- No more "connection refused" errors

## Verification

1. Open the application in Tempo
2. Navigate to the Terminal tab
3. Terminal should show "Connected" status
4. You should be able to type commands and see responses

## Notes

- The `dev` script in package.json has been updated to run the production build
- The backend automatically detects the PORT environment variable
- All WebSocket URLs are constructed dynamically based on the current page location
- No hardcoded localhost:8000 URLs remain in the codebase

This setup ensures the application works correctly in the Tempo environment where only one port is exposed externally.
