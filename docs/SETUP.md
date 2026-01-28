# icotes - Development Setup

This guide provides detailed setup instructions for the icotes development environment.

## Prerequisites

- **Node.js** (v18 or higher)
- **Python** 3.8 or higher
- **bun** (JavaScript runtime + package manager)
- **UV** package manager (recommended) or pip
- **Ubuntu/Debian Linux** (preferred, but adaptable to other systems)

## Automated Setup (Recommended)

The easiest way to set up icotes is using the automated setup script:

```bash
# From the project root directory
./setup.sh
```

**Features of the setup script:**
- ✅ **Idempotent**: Can be run multiple times safely for updates
- ✅ **Automatic dependency management**: Installs Node.js, Python, UV
- ✅ **Environment configuration**: Creates proper `.env` file
- ✅ **Single-port setup**: Configures everything to run on port 8000
- ✅ **Backup management**: Backs up existing configuration before updates

## Manual Setup Instructions

### 1. Install System Dependencies

```bash
# Update package lists
sudo apt update

# Install required system packages
sudo apt install -y curl git build-essential nodejs python3 python3-pip python3-venv unzip

# Install bun
curl -fsSL https://bun.sh/install | bash
source ~/.bashrc
```

### 2. Install UV Package Manager (Recommended)

```bash
# Install UV for faster Python dependency management
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload your shell or add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

### 3. Setup Frontend Dependencies

```bash
# Install JS dependencies
bun install

# Clean any previous builds
rm -rf dist
```

### 4. Setup Backend Dependencies

**With UV (Recommended):**
```bash
cd backend

# Initialize UV project (if needed)
uv init --no-readme --no-pin-python

# Install dependencies
uv sync --frozen --no-dev

cd ..
```

**Traditional method (fallback):**
```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

cd ..
```

### 5. Configure Environment

Create a `.env` file in the project root with your local IP:

```bash
# Get your local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')

# Create .env file
cat > .env << EOF
SITE_URL=${LOCAL_IP}
PORT=8000

# Single port configuration - everything runs on port 8000
BACKEND_HOST=${LOCAL_IP}
BACKEND_PORT=8000
BACKEND_URL=http://${LOCAL_IP}:8000

# Frontend should also be served from port 8000 in single port mode
FRONTEND_HOST=${LOCAL_IP}
FRONTEND_PORT=8000
FRONTEND_URL=http://${LOCAL_IP}:8000

# Vite-accessible environment variables (prefixed with VITE_)
VITE_BACKEND_URL=http://${LOCAL_IP}:8000
VITE_API_URL=http://${LOCAL_IP}:8000/api
VITE_SITE_URL=${LOCAL_IP}
VITE_WS_URL=ws://${LOCAL_IP}:8000/ws

# Workspace Configuration
WORKSPACE_ROOT=$(pwd)/workspace
VITE_WORKSPACE_ROOT=$(pwd)/workspace

# API Keys (update with your actual keys)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
# ... add other keys as needed
EOF
```

### 6. Make Scripts Executable

```bash
chmod +x setup.sh
chmod +x start-dev.sh
chmod +x backend/start.sh
chmod +x check-servers.sh
```

## Running the Development Environment

### Start Development Servers

```bash
# Start both frontend and backend (single port mode)
./start-dev.sh
```

### Alternative: Start Servers Separately

**Backend Server:**
```bash
cd backend

# With UV (recommended)
uv run python main.py

# Or with traditional venv
source venv/bin/activate
python main.py
```

**Frontend Build:**
```bash
# Build frontend (served by backend in single port mode)
bun run build
```

## SSH Hop Configuration

icotes uses OpenSSH config format for hop connections. This ensures full compatibility with VS Code Remote SSH and standard SSH clients.

- Config file: `workspace/.icotes/hop/config`
- SSH keys: `workspace/.icotes/ssh/keys/`
- Legacy JSON: `workspace/.icotes/ssh/credentials.json` (deprecated, read-only)

Example entry:

```
# icotes hop configuration
# This file is compatible with VS Code Remote SSH config

Host my-server
   HostName 192.168.1.10
   User ubuntu
   Port 22
   IdentityFile ~/.icotes/ssh/keys/my-server_key
   # icotes-meta: {"id": "hop-123", "auth": "privateKey"}
```

Validation tool (recommended):

```bash
cd backend
uv run python -m icpy.scripts.validate_hop_config
```

Migration and deprecation:
- On startup, if a legacy `credentials.json` exists and no config file is present, icotes auto-migrates to SSH config format and creates a backup `credentials.json.bak`.
- Phase 5 stops writing to JSON. Only the SSH config file is updated.
- You may see a deprecation warning when loading from legacy JSON; this is expected during migration.

Docker note:
- Local dev credentials under `workspace/.icotes/hop/**` are excluded by `.dockerignore` to avoid leaking secrets into images.
## Project Structure

```
icotes/
├── src/                    # Frontend source code (React/TypeScript)
│   ├── components/         # React components
│   ├── contexts/          # React contexts
│   ├── hooks/             # Custom React hooks
│   ├── icui/              # UI component library
│   ├── lib/               # Utility libraries
│   ├── services/          # API and service layer
│   ├── types/             # TypeScript type definitions
│   └── stories/           # Storybook stories
├── backend/               # Backend source code (FastAPI/Python)
│   ├── icpy/              # Python package modules
│   │   ├── agent/         # AI agent implementations
│   │   ├── api/           # API route handlers
│   │   ├── core/          # Core functionality
│   │   ├── gateway/       # Gateway services
│   │   └── services/      # Business logic services
│   ├── tests/             # Backend tests
│   ├── main.py           # FastAPI application entry point
│   ├── requirements.txt  # Python dependencies
│   ├── pyproject.toml    # UV project configuration
│   └── start.sh          # Backend start script
├── workspace/            # Code execution workspace
├── docs/                 # Documentation
├── public/               # Static assets
├── .env                  # Environment configuration
├── setup.sh              # Automated setup script
└── start-dev.sh          # Development server startup
```

## Development URLs (Single Port Architecture)

- **Application**: http://your-ip:8000 (main application interface)
- **API Documentation**: http://your-ip:8000/docs (FastAPI auto-generated docs)
- **WebSocket**: ws://your-ip:8000/ws (real-time communication)

**Key Benefits of Single Port Setup:**
- Simplified development and deployment
- No CORS issues between frontend and backend
- Easier firewall and network configuration
- Production-like development environment

## Technologies Used

### Frontend
- **React 18** - Modern React with hooks
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Radix UI** - Accessible component library
- **CodeMirror** - Advanced code editor
- **Framer Motion** - Smooth animations

### Backend
- **FastAPI** - Modern Python web framework
- **Python 3.12** - Latest Python features
- **Uvicorn** - High-performance ASGI server
- **WebSocket** - Real-time bi-directional communication
- **UV Package Manager** - Fast Python dependency management
- **Pydantic** - Data validation and settings management

### AI Integration
- **OpenAI** - GPT models for code assistance
- **Anthropic** - Claude models
- **Groq** - Fast inference
- **Multiple providers** - Flexible AI backend support

## Available Scripts

### Project Scripts
- `./setup.sh` - Automated setup and updates
- `./start-dev.sh` - Start development environment
- `./check-servers.sh` - Check server status
- `./verify-setup.sh` - Verify installation

### Frontend Scripts
- `bun run dev` - Build frontend + start backend dev server (single-port)
- `bun run build` - Build for production
- `bun run lint` - Run ESLint
- `bun run preview` - Preview production build

### Backend Scripts
- `cd backend && uv run python main.py` - Start with UV
- `cd backend && ./start.sh` - Start with helper script
- `cd backend && python main.py` - Direct execution (in venv)

## Environment Configuration

The `.env` file contains all configuration. Key sections:

### Basic Configuration
```bash
SITE_URL=192.168.1.100    # Your local IP
PORT=8000                 # Single port for everything
```

### API Keys (Required for AI features)
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
# Update with your actual API keys
```

### Workspace Settings
```bash
WORKSPACE_ROOT=/path/to/icotes/workspace
VITE_WORKSPACE_ROOT=/path/to/icotes/workspace
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: 
   - The single port setup uses only port 8000
   - Kill any processes using port 8000: `sudo lsof -ti:8000 | xargs kill -9`

2. **UV package manager issues**:
   ```bash
   # Reinstall UV
   curl -LsSf https://astral.sh/uv/install.sh | sh
   export PATH="$HOME/.local/bin:$PATH"
   ```

3. **Python virtual environment (fallback)**:
   ```bash
   cd backend
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Node.js version issues**:
   ```bash
   # Check version (should be 18+)
   node --version
   
   # Update if needed
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
   sudo apt-get install -y nodejs
   ```

5. **Dependencies issues**:
   ```bash
   # Frontend
   rm -rf node_modules bun.lock
   bun install
   
   # Backend
   cd backend
   uv clean
   uv sync --frozen --no-dev
   ```

### Verification Steps

1. **Check setup**:
   ```bash
   ./verify-setup.sh
   ```

2. **Manual verification**:
   ```bash
   # Check if servers start
   ./start-dev.sh
   
   # In another terminal, check if API responds
   curl http://localhost:8000/docs
   ```

3. **Environment check**:
   ```bash
   # Verify environment variables are loaded
   source .env
   echo $BACKEND_URL
   ```

## Testing the Setup

1. **Run the setup script**: `./setup.sh`
2. **Start development servers**: `./start-dev.sh`
3. **Open browser**: Navigate to http://your-ip:8000
4. **Verify API**: Check http://your-ip:8000/docs
5. **Test features**: Try code execution, terminal, AI chat

## Next Steps

- **API Keys**: Update `.env` with your actual API keys for AI features
- **Development**: Both servers support hot reloading for development
- **Documentation**: Check `/docs` folder for additional project documentation
- **Contributing**: See contribution guidelines in the docs

## Production Deployment

For production deployment:

1. **Build frontend**: `bun run build`
2. **Configure environment**: Update `.env` for production
3. **Start backend**: The backend serves both API and frontend
4. **Use process manager**: Consider using PM2 or similar for production
