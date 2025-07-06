# iLabors Code Editor

A modern web-based code editor with real-time execution, terminal access, and collaborative features.

## Features

- 🎨 **Modern UI** - Built with React, TypeScript, and Tailwind CSS
- 🚀 **Real-time Code Execution** - Execute Python code instantly
- 💻 **Integrated Terminal** - Full terminal access via WebSocket
- 🔌 **WebSocket Support** - Real-time communication and updates
- 📱 **Responsive Design** - Works on desktop and mobile devices
- 🔧 **FastAPI Backend** - High-performance Python API server

## Quick Setup

### One-Command Installation

```bash
# Clone the repository
git clone https://github.com/penthoy/ilaborcode.git
cd ilaborcode

# Run automated setup (installs everything)
./setup.sh
```

### Manual Installation

**Prerequisites:** Ubuntu/Debian Linux

```bash
# Install dependencies
sudo apt update
sudo apt install -y nodejs npm python3 python3-pip python3-venv

# Install frontend dependencies
npm install

# Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

# Start development servers
./start-dev.sh
```

## Usage

```bash
# Start both servers
./start-dev.sh

# Check server status
./check-servers.sh

# Test connectivity
./test-connectivity.sh
```

## Access URLs

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000  
- **API Documentation**: http://localhost:8000/docs

## Configuration

Edit `.env` file to change host/port settings:

```bash
# Example for custom IP
BACKEND_HOST=192.168.1.100
FRONTEND_HOST=192.168.1.100
VITE_API_URL=http://192.168.1.100:8000
```

## Documentation

- [Environment Configuration](docs/environment-configuration.md)
- [Development Setup](SETUP.md)
- [Project Architecture](docs/architecture.md)

## Tech Stack

**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Radix UI  
**Backend:** FastAPI, Python 3.12, Uvicorn, WebSocket  
**Tools:** ESLint, Prettier, Storybook
