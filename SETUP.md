# iLabors Code Editor - Development Setup

This guide will help you set up the development environment for the iLabors Code Editor.

## Prerequisites

- Node.js (v18 or higher)
- Python 3.8 or higher
- npm (comes with Node.js)
- pip (Python package manager)

## Setup Instructions

### 1. Install Dependencies

The repository contains both frontend (React/Vite/TypeScript) and backend (FastAPI/Python) components.

**Frontend Dependencies:**
```bash
npm install
```

**Backend Dependencies:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Running the Development Servers

#### Option 1: Start Both Servers with One Command
```bash
./start-dev.sh
```

#### Option 2: Start Servers Separately

**Backend Server:**
```bash
cd backend
./start.sh
```
The backend will run on: `http://localhost:8000`

**Frontend Server:**
```bash
npm run dev
```
The frontend will run on: `http://localhost:5173`

## Project Structure

```
├── src/                    # Frontend source code
│   ├── components/         # React components
│   ├── lib/               # Utility libraries
│   ├── types/             # TypeScript type definitions
│   └── stories/           # Storybook stories
├── backend/               # Backend source code
│   ├── main.py           # FastAPI application
│   ├── requirements.txt  # Python dependencies
│   └── start.sh          # Backend start script
├── public/               # Static assets
└── docs/                 # Documentation
```

## Development URLs

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (FastAPI auto-generated docs)

## Technologies Used

### Frontend
- React 18
- TypeScript
- Vite (build tool)
- Tailwind CSS
- Radix UI components
- CodeMirror (code editor)
- Framer Motion (animations)

### Backend
- FastAPI
- Python 3.12
- Uvicorn (ASGI server)
- WebSocket support
- CORS middleware

## Available Scripts

### Frontend
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run lint` - Run ESLint
- `npm run preview` - Preview production build

### Backend
- `./start.sh` - Start backend server
- `python3 main.py` - Run server directly

## Troubleshooting

1. **Port conflicts**: If ports 3000 or 8000 are in use, the servers will automatically use the next available port.

2. **Python virtual environment**: Make sure to activate the virtual environment before running backend commands:
   ```bash
   cd backend
   source venv/bin/activate
   ```

3. **Node.js version**: Ensure you're using Node.js v18 or higher:
   ```bash
   node --version
   ```

4. **Dependencies**: If you encounter dependency issues, try:
   ```bash
   # Frontend
   rm -rf node_modules package-lock.json
   npm install
   
   # Backend
   cd backend
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Testing the Setup

1. Open your browser to `http://localhost:5173`
2. You should see the iLabors Code Editor interface
3. The backend API should be accessible at `http://localhost:8000`
4. API documentation is available at `http://localhost:8000/docs`

## Next Steps

- The development environment is now ready for coding and testing
- Both servers support hot reloading for development
- Check the `/docs` folder for additional project documentation
