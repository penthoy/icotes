# icotes - System Architecture

## Overview

icotes is a web-based IDE with real-time collaboration features, built on a modular event-driven architecture. The system uses a single-port deployment model with WebSocket-based communication and a custom UI framework.

## Architecture (v1.0)

### Frontend (ICUI Framework)

**Technology Stack:**
- **Build**: Vite + React 18 + TypeScript
- **UI Framework**: ICUI (Interactive Component UI) - Custom panel system inspired by Blender
- **Editor**: CodeMirror 6 with syntax highlighting
- **Styling**: Tailwind CSS + ShadCN components
- **Communication**: WebSocket-first with REST fallback

**ICUI Architecture:**
```
src/icui/
├── components/         # Layout & panel components
├── services/          # Backend communication
├── hooks/             # State management hooks
└── types/             # TypeScript definitions
```

**Key Features:**
- Dynamic panel management with resizable layouts
- Real-time terminal with PTY support
- File explorer with live updates
- AI chat interface with tool call widgets

### Backend (ICPY Framework)

**Technology Stack:**
- **Framework**: FastAPI + Python 3.12
- **Package Manager**: UV for fast dependency management
- **Architecture**: Modular event-driven services
- **Communication**: WebSocket + REST API

**ICPY Modular Structure:**
```
backend/icpy/
├── api/               # REST & WebSocket endpoints
├── services/          # Core business logic
│   ├── workspace/     # File & project management
│   ├── terminal/      # PTY terminal sessions
│   ├── code_execution/# Python code execution
│   ├── chat/          # AI chat & agent management
│   └── filesystem/    # File operations & watching
├── core/              # Connection & message management
├── agent/             # AI agents & custom tools
└── gateway/           # Service coordination
```

### Communication Protocol

**Single WebSocket Connection:**
- All frontend-backend communication through `/ws`
- Event-driven message routing to appropriate services
- Real-time state synchronization across components

**Message Types:**
```typescript
interface ICPYMessage {
  type: 'terminal' | 'filesystem' | 'code_execution' | 'chat' | 'workspace';
  action: string;
  data: any;
  messageId?: string;
}
```

### Deployment Architecture

**Single-Port Model:**
- Frontend served as static files from backend
- All communication through single port (default: 8000)
- Dynamic URL construction for WebSocket connections

**Production Setup:**
```
┌─────────────────┐
│  Load Balancer  │
│ (nginx/traefik) │
└─────────┬───────┘
          │
┌─────────▼───────┐
│   icotes App    │
│ (FastAPI+React) │
│    Port 8000    │
└─────────┬───────┘
          │
┌─────────▼───────┐
│   File System   │
│ (SQLite + Disk) │
└─────────────────┘
```

## Key Features

### Real-Time Collaboration
- Live terminal sessions with PTY support
- Instant file synchronization across clients
- Real-time code execution with output streaming

### AI Integration
- Custom agent system with tool calls
- Streaming chat interface with widget support
- Context-aware code assistance

### Development Experience
- Hot module replacement in development
- Comprehensive logging and error handling
- Health monitoring and diagnostics

## Security & Performance

**Current Implementation:**
- CORS configuration for cross-origin requests
- Input sanitization for code execution
- WebSocket connection management
- Async request handling for scalability

**Limitations:**
- Code execution not sandboxed (development use)
- No authentication system (planned for v2.0)
- Single-instance deployment model

## Technology Decisions

**Why ICUI Framework?**
- Flexible panel system inspired by professional IDEs
- Dynamic layout management with user control
- Consistent theming and accessibility

**Why Event-Driven Backend?**
- Modular services for maintainability
- Real-time state synchronization
- Easy to extend with new features

**Why Single-Port Architecture?**
- Simplified deployment and networking
- No CORS issues in production
- Better compatibility with cloud platforms

## Future Roadmap

- **v2.0**: Rust backend migration for performance
- **Security**: Sandboxed code execution and authentication
- **Collaboration**: Multi-user editing and shared workspaces
- **Extensions**: Plugin system for custom functionality
