# Deployment Guide for Coolify/Nixpacks

## Prerequisites
- The application requires a container with PTY support for terminal functionality
- Python 3.11+ and Node.js 18+ are required

## Deployment Configuration

### Auto-Detection Approach
This project uses Nixpacks auto-detection for the most reliable deployment:
- Nixpacks automatically detects Node.js and Python requirements
- No custom `nixpacks.toml` configuration needed
- Python dependencies are installed at runtime via `start.sh`

### Scripts
- `start.sh` - Production startup script with robust Python dependency installation
- `Procfile` - Process configuration for deployment platforms
- `package.json` - Contains build commands for the frontend

## Environment Variables
Set these in your Coolify deployment:

```
NODE_ENV=production
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
```

## Troubleshooting

### Terminal "Connecting..." Issue
If the terminal shows "Connecting..." and never connects:

1. **Check WebSocket Connection**:
   - Visit `/api/terminal/health` to check if PTY is available
   - Check browser console for WebSocket errors

2. **Check Container Permissions**:
   - Ensure the container has PTY support
   - The app needs permission to create pseudo-terminals

3. **Check Port Configuration**:
   - Ensure port 8000 is accessible
   - WebSocket connections need the same port as HTTP

4. **Check Logs**:
   - Look for "Terminal WebSocket connection attempt" in logs
   - Check for any PTY creation errors

### Common Issues

1. **PTY Not Available**:
   - Some container environments don't support PTY
   - Try adding `--cap-add=SYS_PTRACE` to Docker run command

2. **Bash Not Found**:
   - Ensure bash is installed in the container
   - Check `/bin/bash`, `/usr/bin/bash`, or `/usr/local/bin/bash`

3. **WebSocket CORS Issues**:
   - Check allowed origins in backend logs
   - Ensure proper domain configuration

4. **Nixpacks Configuration Errors**:
   - Error: "invalid type: map, expected a sequence for key 'providers'"
   - Solution: Remove custom nixpacks.toml and use auto-detection
   - Auto-detection is often more reliable for hybrid projects

5. **Python/Pip Issues in Nixpacks**:
   - Error: "No module named pip" 
   - Solution: start.sh script tries multiple pip installation methods
   - Falls back to manual package installation if pip unavailable

6. **Build Failures**:
   - Try removing nixpacks.toml to use auto-detection
   - Check that start.sh is executable
   - Verify requirements.txt is properly formatted

7. **Start Script Issues**:
   - Ensure start.sh is executable (`chmod +x start.sh`)
   - Script handles multiple pip installation methods
   - Check deployment logs for specific error messages

## Testing
After deployment, test these endpoints:
- `/` - Should return API info
- `/health` - Should return healthy status
- `/api/terminal/health` - Should show PTY and bash availability

## Development vs Production
- Development uses hardcoded local IPs
- Production uses dynamic URL construction
- WebSocket URLs are auto-detected in production
