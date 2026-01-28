# icotes AI Coding Agent Instructions

## Project Overview

icotes is an AI-powered web-based IDE with a **single-port architecture** serving both frontend and backend on port 8000. The system uses custom frameworks: **ICPY** (backend) and **ICUI** (frontend).

### Tech Stack
- **Frontend**: React 18 + TypeScript + Vite, ICUI custom panel system (Blender-inspired), CodeMirror 6
- **Backend**: FastAPI + Python 3.12, ICPY modular services
- **Package Managers**: `bun` (frontend), `uv` (backend - mandatory for speed/isolation)
- **Communication**: Single WebSocket connection (`/ws`) with event-driven message routing
- **Deployment**: Docker (single port), nginx/traefik compatible

## Critical Architecture Patterns

### ICPY Backend (Modular Event-Driven)

**Structure**: `backend/icpy/` contains independent service modules that communicate via message broker:
```
icpy/
├── api/          # REST + WebSocket endpoints
├── services/     # Core business logic (workspace, terminal, chat, filesystem, etc.)
├── agent/        # AI agents + custom tools (CrewAI, LangChain, LangGraph)
├── core/         # Connection manager, CORS, static file serving
└── gateway/      # Service coordination
```

**Service Pattern**: All services follow a singleton pattern with async initialization:
```python
# Example from backend/icpy/services/workspace_service.py
class WorkspaceService:
    _instance = None
    async def initialize(self): ...
    
# Access via: from icpy.services import get_workspace_service
```

**Message Protocol**: WebSocket messages use typed structure:
```typescript
{type: 'terminal'|'filesystem'|'chat'|'workspace', action: string, data: any, messageId?: string}
```

### ICUI Frontend (Custom Panel System)

**Structure**: `src/icui/` - Blender-inspired dynamic panel layout:
```
icui/
├── components/   # ICUILayout, panels, chat, editor, explorer
├── services/     # Singleton services (backend-service-impl, fileService, mediaService)
├── state/        # Chat session store (Zustand-like)
└── hooks/        # useWebSocketService, panel state hooks
```

**Service Pattern**: Frontend services are singletons accessed via exports:
```typescript
// From src/icui/services/backend-service-impl.tsx
export const icuiBackendService = new ICUIBackendService();
// All ICUI components import this shared instance
```

**Key Convention**: Services use EventEmitter for cross-component communication instead of React context for performance.

## Development Workflows

### Starting the Application

**Development** (SINGLE PORT - frontend served from backend):
```bash
./start-dev.sh  # Builds React, runs uvicorn with --reload on :8000
# OR: bun run dev (same command)
```

**Production**:
```bash
./start.sh      # Production build + serve
```

**Backend Only** (for testing):
```bash
cd backend && uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-config logging.conf
```

### Testing

**Backend** (uses `uv` exclusively):
```bash
cd backend
export PYTHONPATH=$(pwd)
uv sync --frozen --no-dev           # Sync dependencies
uv run pytest tests/ -v --tb=short  # Run all tests
uv run pytest tests/icpy/test_workspace_service.py -v  # Specific test
```

**Frontend**:
```bash
bun test              # Vitest unit tests (src/tests/)
bun run e2e           # Playwright e2e tests (e2e/)
bun run e2e:ui        # Playwright UI mode
```

**Important**: Backend tests use fixtures; no running server required. Frontend e2e tests expect app running on :8000.

### Building & Deployment

**Docker** (recommended):
```bash
docker run -d -p 8000:8000 penthoy/icotes:latest
# Auto-detects host/port - works on localhost, LAN, remote servers
```

**Manual Build**:
```bash
bun run build     # Builds to dist/, backend serves static files
./start.sh        # Production mode
```

## Code Conventions

### Backend (ICPY)

1. **Import Pattern**: Always use `from icpy.services import get_<service>_service()` for service access
2. **Async First**: All service methods are async; use `await` consistently
3. **Error Handling**: Services return structured responses: `{"success": bool, "data": any, "error": str}`
4. **Logging**: Use module-level logger: `logging.getLogger(__name__)`
5. **UV Only**: Never use `pip install` in development - always `uv sync` or `uv add <package>`

### Frontend (ICUI)

1. **Service Access**: Import singleton exports: `import { icuiBackendService } from '@/icui/services/backend-service-impl'`
2. **WebSocket**: Use `icuiBackendService.sendMessage({type, action, data})` - never create new WebSocket instances
3. **File Paths**: Use absolute imports with `@/` alias (configured in vite.config.ts)
4. **Panel Components**: Wrap in `ICUIBasePanel` for consistent layout integration
5. **State Management**: Chat uses `ChatSessionStore` (Zustand-like), other state via EventEmitter patterns

### Cross-Cutting Concerns

**Dynamic Configuration**: Frontend loads URLs from backend `/api/config` at runtime (no hardcoded URLs in build):
```typescript
// src/services/config-service.ts
configService.getConfig() // Returns { BACKEND_URL, WS_URL, API_URL }
```

**Environment Variables**: Single port setup uses `SITE_URL` and `PORT` in `.env`:
```bash
SITE_URL=192.168.1.100  # Auto-detected by setup.sh
PORT=8000
# All other URLs derived from these
```

**Hop (SSH) Sessions**: Backend supports remote context switching via `hop_session` - services use `activeNamespace` to route operations.

## Integration Points

### AI Agent System
- **Location**: `backend/icpy/agent/`
- **Frameworks**: Supports OpenAI SDK, CrewAI, LangChain, LangGraph
- **Custom Agents**: Add to `backend/icpy/agent/custom_agent.py`, expose via `/api/agents/custom/{agent_name}`
- **Tool Calling**: Uses function calling with widget rendering in frontend chat

### Terminal (PTY)
- **Backend**: `backend/icpy/services/terminal_service.py` - manages persistent PTY sessions
- **Frontend**: `src/icui/components/panels/TerminalPanel.tsx` - XTerm.js with fit addon
- **WebSocket**: Uses `type: 'terminal'` messages for bidirectional I/O

### File Operations
- **Backend**: `backend/icpy/services/filesystem_service.py` - watchdog integration for live updates
- **Frontend**: `src/icui/services/fileService.tsx` - batched operations, event-driven tree updates
- **Explorer**: `src/icui/components/explorer/` - virtual scrolling for large directories

## Common Pitfalls

1. **Port Conflicts**: App uses ONLY port 8000 - frontend doesn't run separately on :5173 in production
2. **UV Required**: Backend tests/dev fail without `uv` - install via `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. **PYTHONPATH**: Backend imports break without `export PYTHONPATH=$(pwd)` when in `backend/` dir
4. **WebSocket Reconnection**: ICUI handles auto-reconnect - don't manually create connections in components
5. **Service Initialization**: Call `await service.initialize()` before using backend services (usually in `main.py` lifespan)
6. **Docker Build Context**: Dockerfile expects to run from project root, not `backend/` dir

## Key Files Reference

- [backend/main.py](backend/main.py) - FastAPI app entry, service initialization, static file serving
- [backend/icpy/agent_sdk_doc.md](backend/icpy/agent_sdk_doc.md) - Comprehensive backend API reference
- [src/App.tsx](src/App.tsx) - Frontend routing, context providers
- [src/icui/services/backend-service-impl.tsx](src/icui/services/backend-service-impl.tsx) - Central WebSocket/backend communication
- [docs/architecture.md](docs/architecture.md) - System architecture deep dive
- [setup.sh](setup.sh) - Idempotent installation script (Node, Python, UV, deps)

## Testing Strategy

**Backend**: Pytest with fixtures, no server needed. Focus on service isolation and message handling.
**Frontend**: Vitest for components, Playwright for e2e flows (requires running app).
**Integration**: `tests/integration/` contains full-stack test scenarios.

When adding features:
1. Backend: Add service method + test in `tests/icpy/test_<service>_service.py`
2. Frontend: Add service method + component integration
3. Update message types in both `backend/icpy/core/` and `src/types/backend-types.ts`
