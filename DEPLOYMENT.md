# Deployment Guide

This guide covers multiple deployment options for the icotes application.

## Quick Start

### Simple VM/Server Deployment
```bash
# Clone your repository
git clone <your-repo-url>
cd ilaborcode

# Make scripts executable
chmod +x start.sh deploy-production.sh

# Option 1: Simple startup (good for testing)
./start.sh

# Option 2: Production deployment with nginx + systemd
sudo ./deploy-production.sh --domain your-domain.com --ssl-email your-email@domain.com
```

### Coolify/Nixpacks Deployment
1. Connect your repository to Coolify
2. Set environment variables (see below)
3. Deploy (auto-detected by Nixpacks)

## Deployment Architecture

### Single-Port Setup (Default)
The application runs on **one port** with the backend serving both the API and the built frontend:
- **Default Port**: 8000
- **Frontend**: Served as static files from `/dist`
- **Backend API**: Available at `/api/*`
- **WebSocket**: Available at `/ws/*`
- **Health Check**: Available at `/health`

**Advantages:**
- Simplified deployment (one port to manage)
- No CORS issues (same origin)
- Better for production and containers
- Easier firewall configuration

**Usage:**
```bash
# Single-port production
./start.sh

# Single-port development
./start-dev.sh
```

### Dual-Port Setup (Development/Scaling)
The application runs on **two ports** with separate frontend and backend servers:
- **Backend Port**: 8000 (API and WebSocket)
- **Frontend Port**: 5173 (Vite development server)
- **Cross-Origin**: Frontend communicates with backend via CORS

**Advantages:**
- Hot reload during development
- Better for frontend development
- Can scale frontend and backend independently
- Development-friendly

**Usage:**
```bash
# Start backend (port 8000)
cd backend && python3 main.py

# Start frontend (port 5173) - in another terminal
npm run dev
```

### Architecture Flexibility
The backend is designed to support both setups seamlessly:
- **Single-port**: Backend serves static files when `dist/` exists
- **Dual-port**: Backend runs API-only when no `dist/` directory found
- **Dynamic URLs**: Frontend automatically detects the current host/port
- **CORS**: Automatically configured for both setups based on environment

## Deployment Options

### 1. Simple Production Start (`start.sh`)

The `start.sh` script is suitable for:
- Testing production builds
- Simple VM deployments
- Development environments

**Features:**
- Automatically installs dependencies
- Builds frontend if needed
- Sets up Python virtual environment
- Configurable workers and ports
- System requirements checking
- Daemon mode support

**Usage:**
```bash
# Basic usage
./start.sh

# With systemd service generation
./start.sh --systemd

# In daemon mode
./start.sh --daemon

# Skip security checks
./start.sh --skip-root-check
```

### 2. Full Production Deployment (`deploy-production.sh`)

The `deploy-production.sh` script provides industry-standard deployment:
- nginx reverse proxy
- systemd service
- SSL with Let's Encrypt
- Firewall configuration
- Log rotation
- Security hardening
- Dedicated application user

**Usage:**
```bash
# Full deployment with SSL
sudo ./deploy-production.sh --domain myapp.com --ssl-email admin@myapp.com

# Local deployment without SSL
sudo ./deploy-production.sh --skip-ssl

# Dry run (see what would be done)
sudo ./deploy-production.sh --dry-run --domain myapp.com
```

### 3. Coolify/Nixpacks Deployment

For containerized deployments (Coolify, Railway, etc.), the project uses:
- Auto-detection by Nixpacks
- `start.sh` as the startup script
- `Procfile` for process management
- Flexible port configuration

**Coolify Configuration:**
1. **Port Management**: Coolify automatically sets the `PORT` environment variable
2. **No manual port configuration needed**: The application will use Coolify's assigned port
3. **Environment Variables**: Set only these required variables in Coolify:
   ```bash
   NODE_ENV=production
   # PORT is automatically set by Coolify - don't override it
   ```

**Railway/Render Configuration:**
Similar to Coolify, these platforms set `PORT` automatically.

**Manual Container Deployment:**
```bash
# Use the PORT environment variable
docker run -e PORT=3000 -p 3000:3000 your-app

# Or use BACKEND_PORT if you prefer
docker run -e BACKEND_PORT=3000 -p 3000:3000 your-app
```

## Environment Variables

### Required Variables
```bash
# Primary Configuration
SITE_URL=192.168.2.195        # Your server IP or domain
NODE_ENV=production           # or development

# Single-Port Setup (Default)
PORT=8000                     # Backend port (serves both frontend and API)
BACKEND_HOST=192.168.2.195    # Backend host (defaults to SITE_URL)
BACKEND_PORT=8000             # Backend port (defaults to PORT)
```

### Dual-Port Setup (Development/Scaling)
```bash
# Backend Configuration
BACKEND_HOST=192.168.2.195    # Backend host
BACKEND_PORT=8000             # Backend API port

# Frontend Configuration  
FRONTEND_HOST=192.168.2.195   # Frontend host
FRONTEND_PORT=5173            # Frontend development server port
FRONTEND_URL=http://192.168.2.195:5173

# API Configuration (Used by Frontend)
VITE_API_URL=http://192.168.2.195:8000
VITE_WS_URL=ws://192.168.2.195:8000
```

### Configuration Priority
The backend uses the following priority for configuration:
- **Host**: `BACKEND_HOST` → `SITE_URL` → `HOST` → `0.0.0.0`
- **Port**: `BACKEND_PORT` → `PORT` → `8000`

### Optional Variables
```bash
WORKERS=2                # Number of uvicorn workers
DEBUG=false             # Enable debug logging
ALLOWED_ORIGINS=*       # CORS origins (comma-separated)
FRONTEND_URL=http://...  # Explicit frontend URL for CORS
SSL_KEYFILE=/path/to/key.pem    # SSL certificate key
SSL_CERTFILE=/path/to/cert.pem  # SSL certificate file
```

## Prerequisites

### System Requirements
- **OS:** Ubuntu 18.04+, Debian 10+, or compatible
- **Memory:** 512MB+ (1GB+ recommended)
- **Disk:** 1GB+ free space
- **Network:** Outbound internet access for package installation

### Software Requirements
- **Node.js:** 18.x or higher
- **Python:** 3.11 or higher
- **nginx:** (optional, for reverse proxy)
- **certbot:** (optional, for SSL)

## File Structure

```
ilaborcode/
├── start.sh                 # Simple production startup
├── deploy-production.sh     # Full production deployment
├── Procfile                 # Process configuration
├── package.json            # Node.js dependencies
├── backend/
│   ├── main.py            # FastAPI application
│   ├── requirements.txt   # Python dependencies
│   └── logging.conf       # Logging configuration
├── .env.production        # Production environment variables
└── dist/                  # Built frontend (after build)
```

## Service Management

### systemd Service (Full Deployment)
```bash
# Service control
sudo systemctl start ilaborcode
sudo systemctl stop ilaborcode
sudo systemctl restart ilaborcode
sudo systemctl status ilaborcode

# View logs
sudo journalctl -fu ilaborcode
sudo journalctl -u ilaborcode --since "1 hour ago"
```

### Manual Process Management
```bash
# Start in daemon mode
./start.sh --daemon

# Check if running
ps aux | grep uvicorn

# Stop daemon
kill $(cat logs/app.pid)
```

### nginx Management (if used)
```bash
# nginx control
sudo systemctl restart nginx
sudo systemctl status nginx

# Test configuration
sudo nginx -t

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## Monitoring and Maintenance

### Health Checks
```bash
# Application health
curl http://localhost:8000/health

# Terminal functionality
curl http://localhost:8000/api/terminal/health

# Through nginx (if configured)
curl http://localhost/health
```

### Log Management
```bash
# Application logs
tail -f logs/app.log              # Direct startup
sudo journalctl -fu ilaborcode    # systemd service

# nginx logs (if configured)
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Updates
```bash
# Update application
cd /opt/ilaborcode  # or your app directory
git pull origin main
sudo systemctl restart ilaborcode

# Update system packages
sudo apt update && sudo apt upgrade -y
```

## Security Considerations

### Application Security
- Runs as dedicated user (not root)
- Limited file system access
- Rate limiting on API endpoints
- Security headers via nginx

### Network Security
- Firewall configured (UFW)
- SSL/TLS encryption (Let's Encrypt)
- nginx as reverse proxy
- WebSocket security headers

### File Permissions
```bash
# Check permissions
ls -la /opt/ilaborcode
ls -la /var/log/ilaborcode

# Fix permissions if needed
sudo chown -R ilaborcode:ilaborcode /opt/ilaborcode
sudo chmod 755 /opt/ilaborcode
```

## Performance Tuning

### Application Performance
```bash
# Adjust workers in .env.production
WORKERS=4  # Typically 2 * CPU cores

# Monitor resource usage
htop
iotop
```

### nginx Performance
```bash
# Edit nginx config
sudo nano /etc/nginx/sites-available/ilaborcode

# Key settings:
# - worker_processes auto
# - worker_connections 1024
# - keepalive_timeout 65
# - client_max_body_size 10M
```

## Backup and Recovery

### Application Backup
```bash
# Create backup
sudo tar -czf ilaborcode-backup-$(date +%Y%m%d).tar.gz /opt/ilaborcode

# Restore from backup
sudo tar -xzf ilaborcode-backup-YYYYMMDD.tar.gz -C /
```

### Database Backup
If you add a database later:
```bash
# Example for PostgreSQL
pg_dump dbname > backup.sql

# Example for MySQL
mysqldump -u user -p dbname > backup.sql
```
## Troubleshooting

### Terminal Issues

#### "Connecting..." Problem
If the terminal shows "Connecting..." and never connects:

1. **Check WebSocket Connection**:
   ```bash
   # Test health endpoints
   curl http://localhost:8000/health
   curl http://localhost:8000/api/terminal/health
   
   # Check browser console for WebSocket errors
   # Look for CORS or connection refused errors
   ```

2. **Check Container/PTY Permissions**:
   ```bash
   # Ensure PTY support is available
   ls -la /dev/pts/
   
   # Check if bash is available
   which bash
   
   # Test PTY creation manually
   python3 -c "import pty; pty.spawn('/bin/bash')"
   ```

3. **Check Port Configuration**:
   ```bash
   # Verify port is open
   netstat -tlnp | grep :8000
   
   # Test WebSocket connection
   curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" http://localhost:8000/ws/terminal/test
   ```

### Common Issues

#### Port Already in Use
```bash
# Find process using port
sudo lsof -i :8000
sudo fuser -k 8000/tcp

# Change port in .env.production
BACKEND_PORT=8001
```

#### Permission Denied
```bash
# Check file permissions
ls -la start.sh
chmod +x start.sh

# Check user permissions
sudo -u ilaborcode whoami
```

#### Build Failures
```bash
# Clear node_modules and rebuild
rm -rf node_modules dist
npm install
npm run build

# Check for Python issues
cd backend
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

#### SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate
sudo certbot renew --dry-run
sudo certbot renew
```

#### nginx Configuration Errors
```bash
# Test nginx configuration
sudo nginx -t

# Check nginx error log
sudo tail -f /var/log/nginx/error.log

# Reload nginx
sudo systemctl reload nginx
```

#### Memory Issues
```bash
# Check memory usage
free -h
df -h

# Add swap if needed
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Debug Mode

Enable debug logging:
```bash
# Add to .env.production
DEBUG=true

# Restart service
sudo systemctl restart ilaborcode

# View debug logs
sudo journalctl -fu ilaborcode
```

### Container-Specific Issues

#### Coolify/Nixpacks Problems
1. **PTY Not Available**:
   - Some container environments don't support PTY
   - Check container capabilities

2. **Build Failures**:
   - Ensure `start.sh` is executable
   - Check Nixpacks auto-detection logs
   - Verify requirements.txt format

3. **WebSocket CORS Issues**:
   - Check allowed origins in backend logs
   - Ensure proper domain configuration

### Getting Help

1. **Check Logs**: Always start with logs
   ```bash
   # Application logs
   sudo journalctl -fu ilaborcode
   
   # nginx logs
   sudo tail -f /var/log/nginx/error.log
   ```

2. **Test Endpoints**: Verify basic functionality
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/api/terminal/health
   ```

3. **Check Resources**: Monitor system resources
   ```bash
   htop
   df -h
   free -h
   ```

## Development vs Production

### Key Differences
- **Development**: Uses hardcoded localhost URLs
- **Production**: Uses dynamic URL construction
- **WebSocket URLs**: Auto-detected based on environment
- **CORS**: More restrictive in production
- **Logging**: Structured logging in production
- **Security**: Additional headers and restrictions

### Environment Variables
```bash
# Development
NODE_ENV=development
BACKEND_HOST=localhost
BACKEND_PORT=8000

# Production
NODE_ENV=production
BACKEND_HOST=0.0.0.0  # or 127.0.0.1 with nginx
BACKEND_PORT=8000
WORKERS=2
```

## Best Practices

1. **Always use a reverse proxy** (nginx) in production
2. **Run as a dedicated user**, not root
3. **Enable SSL/TLS** for any internet-facing deployment
4. **Monitor logs and resources** regularly
5. **Keep backups** of your configuration and data
6. **Use environment variables** for configuration
7. **Test deployments** in a staging environment first
8. **Keep the system updated** with security patches

## Support

For additional support:
1. Check the application logs first
2. Review this troubleshooting guide
3. Test the health endpoints
4. Verify system requirements are met
5. Check firewall and network configuration
