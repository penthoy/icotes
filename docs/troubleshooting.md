# Troubleshooting Guide

## Common Setup Issues

### 1. Permission Denied Errors
```bash
# Make scripts executable
chmod +x setup.sh start-dev.sh check-servers.sh verify-setup.sh
```

### 2. Node.js Version Issues
```bash
# Install Node.js 18+ (recommended)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 3. Python Virtual Environment Issues
```bash
# Recreate virtual environment
rm -rf backend/venv
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Port Already in Use
```bash
# Kill processes using ports 8000 and 5173
sudo lsof -ti:8000 | xargs kill -9
sudo lsof -ti:5173 | xargs kill -9
```

### 5. Network Access Issues
```bash
# Check firewall settings
sudo ufw status
sudo ufw allow 8000
sudo ufw allow 5173
```

## Verification Commands

```bash
# Verify installation
./verify-setup.sh

# Check server status
./check-servers.sh

# Test connectivity
./test-connectivity.sh
```

## Fresh Installation

If you encounter persistent issues, try a fresh installation:

```bash
# Clean previous installation
rm -rf node_modules backend/venv .env

# Run setup again
./setup.sh
```

## Getting Help

1. Check the logs in the terminal when starting servers
2. Verify your `.env` file configuration
3. Ensure all required ports are available
4. Check system requirements (Ubuntu/Debian Linux)
