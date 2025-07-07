# Deployment Guide for Coolify/Nixpacks

## Prerequisites
- The application requires a container with PTY support for terminal functionality
- Python 3.11+ and Node.js 18+ are required

## Deployment Configuration

### Nixpacks Configuration
The project includes a `nixpacks.toml` file that configures the build process:
- Uses Node.js 18 and Python 3.11
- Installs Python dependencies during startup
- Builds the frontend during the build phase

### Scripts
- `start.sh` - Production startup script that installs Python deps and starts the app
- `package.json` - Contains build and start commands

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

4. **Python/Pip Issues in Nixpacks**:
   - Error: "No module named pip" 
   - Solution: Use providers instead of nixPkgs in nixpacks.toml
   - Install Python deps in start.sh script with `--user` flag
   - Alternative: Use auto-detection by removing nixpacks.toml

5. **Build Failures**:
   - Check nixpacks.toml configuration
   - Ensure all required system packages are listed
   - Verify requirements.txt is properly formatted
   - Try removing nixpacks.toml to use auto-detection

6. **Start Script Issues**:
   - Ensure start.sh is executable (`chmod +x start.sh`)
   - Check that Python dependencies install successfully
   - Verify file paths in the script

## Testing
After deployment, test these endpoints:
- `/` - Should return API info
- `/health` - Should return healthy status
- `/api/terminal/health` - Should show PTY and bash availability

## Development vs Production
- Development uses hardcoded local IPs
- Production uses dynamic URL construction
- WebSocket URLs are auto-detected in production
