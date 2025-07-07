# Port Configuration Guide

## Overview
The iLabors Code Editor supports flexible port configuration for different deployment environments.

## Port Configuration Priority

The application checks environment variables in this order:
1. `BACKEND_PORT` - Application-specific port setting
2. `PORT` - Standard containerized deployment port (used by Coolify, Railway, Render, etc.)
3. `8000` - Default fallback port

## Platform-Specific Configuration

### Coolify Deployment
```bash
# Environment Variables in Coolify UI:
NODE_ENV=production
# PORT is automatically set by Coolify - don't override it!
```

**How it works:**
- Coolify automatically assigns a port and sets the `PORT` environment variable
- The application will use this port automatically
- No manual port configuration needed

### Railway Deployment
```bash
# Environment Variables in Railway:
NODE_ENV=production
# PORT is automatically set by Railway
```

### Render Deployment
```bash
# Environment Variables in Render:
NODE_ENV=production
# PORT is automatically set by Render
```

### Manual Docker Deployment
```bash
# Option 1: Use PORT environment variable (recommended)
docker run -e NODE_ENV=production -e PORT=3000 -p 3000:3000 your-app

# Option 2: Use BACKEND_PORT
docker run -e NODE_ENV=production -e BACKEND_PORT=3000 -p 3000:3000 your-app
```

### VM/VPS Deployment
```bash
# Option 1: Use start.sh with PORT
PORT=3000 ./start.sh

# Option 2: Use start.sh with BACKEND_PORT
BACKEND_PORT=3000 ./start.sh

# Option 3: Set in .env.production
echo "BACKEND_PORT=3000" >> .env.production
./start.sh
```

### Docker Compose
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - PORT=3000
```

## Testing Port Configuration

### Test Different Ports
```bash
# Test with PORT environment variable
PORT=9000 ./start.sh

# Test with BACKEND_PORT environment variable
BACKEND_PORT=9001 ./start.sh

# Test with both (BACKEND_PORT takes precedence)
BACKEND_PORT=9002 PORT=9000 ./start.sh
```

### Verify Port Usage
```bash
# Check if port is in use
netstat -tlnp | grep :9000

# Test health endpoint
curl http://localhost:9000/health
```

## Environment Variable Reference

| Variable | Description | Default | Priority |
|----------|-------------|---------|----------|
| `BACKEND_PORT` | Application-specific port | `8000` | High |
| `PORT` | Standard containerized port | `8000` | Medium |
| `BACKEND_HOST` | Host to bind to | `0.0.0.0` | - |
| `HOST` | Alternative host variable | `0.0.0.0` | Low |

## Troubleshooting

### Port Already in Use
```bash
# Find process using port
sudo lsof -i :8000

# Kill process
sudo fuser -k 8000/tcp

# Or use a different port
PORT=8001 ./start.sh
```

### Port Not Accessible
```bash
# Check if service is running
curl http://localhost:8000/health

# Check firewall (if applicable)
sudo ufw status
sudo ufw allow 8000

# Check if binding to correct interface
ss -tlnp | grep :8000
```

### Container Port Issues
```bash
# Ensure port mapping is correct
docker run -p HOST_PORT:CONTAINER_PORT your-app

# Check container logs
docker logs container-name
```

## Best Practices

1. **Use PORT for containerized deployments** - Most platforms expect this
2. **Use BACKEND_PORT for manual deployments** - More descriptive
3. **Don't hardcode ports** - Always use environment variables
4. **Test port configuration** - Verify accessibility after deployment
5. **Document port usage** - Clearly communicate which ports are used

## Example Configurations

### Development
```bash
# .env (development)
NODE_ENV=development
BACKEND_PORT=8000
```

### Production (Manual)
```bash
# .env.production
NODE_ENV=production
BACKEND_PORT=8000
```

### Production (Coolify)
```bash
# Coolify environment variables
NODE_ENV=production
# PORT is set automatically by Coolify
```

This flexible configuration ensures your application works seamlessly across different deployment platforms while maintaining compatibility with manual deployments.
