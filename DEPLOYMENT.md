# Deployment Guide for Coolify/Nixpacks

## Prerequisites
- The application requires a container with PTY support for terminal functionality
- Python 3.11+ and Node.js 18+ are required

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

## Testing
After deployment, test these endpoints:
- `/` - Should return API info
- `/health` - Should return healthy status
- `/api/terminal/health` - Should show PTY and bash availability

## Development vs Production
- Development uses hardcoded local IPs
- Production uses dynamic URL construction
- WebSocket URLs are auto-detected in production
