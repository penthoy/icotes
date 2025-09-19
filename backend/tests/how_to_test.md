# How to Test the ICPY Backend (uv)

This guide shows how to run backend tests using the uv package manager.

Why uv? It’s fast, creates isolated environments automatically, and avoids the usual venv/pip pitfalls.

## Quick Start

```bash
cd backend
# One-time (or when dependencies change):
uv sync --frozen --no-dev

# Ensure module resolution works from backend/
export PYTHONPATH=$(pwd)

# Run all tests
uv run pytest tests/ -v --tb=short
```

## Prerequisites

- Python 3.12+
- uv installed

Install uv (if missing):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

## Test Commands

### All Tests (Recommended)
```bash
uv run pytest tests/ -v --tb=short
```

### Suites and Files
```bash
# Connection Manager
uv run pytest tests/icpy/test_connection_manager.py -v

# Filesystem Service
uv run pytest tests/icpy/test_filesystem_service.py -v

# Workspace Service
uv run pytest tests/icpy/test_workspace_service.py -v

# Terminal Service
uv run pytest tests/icpy/test_terminal_service.py -v

# WebSocket API
uv run pytest tests/icpy/test_websocket_api.py -v

# Message Broker
uv run pytest tests/icpy/test_message_broker.py -v

# Protocol
uv run pytest tests/icpy/test_protocol.py -v

# REST API (currently paused due to FastAPI version issue)
uv run pytest tests/icpy/test_rest_api.py -v
```

### Multiple Suites
```bash
uv run pytest \
    tests/icpy/test_connection_manager.py \
    tests/icpy/test_filesystem_service.py \
    tests/icpy/test_workspace_service.py \
    tests/icpy/test_terminal_service.py \
    tests/icpy/test_websocket_api.py \
    tests/icpy/test_message_broker.py \
    tests/icpy/test_protocol.py -v
```

### Development Shortcuts
```bash
# Stop on first failure
uv run pytest tests/ -x --tb=short

# Re-run last failed
uv run pytest tests/ --lf

# Pattern filter
uv run pytest tests/ -k "workspace" -v
uv run pytest tests/ -k "terminal" -v
uv run pytest tests/ -k "connection" -v
```

### Individual Test Methods
```bash
uv run pytest tests/icpy/test_workspace_service.py::TestWorkspaceService::test_create_workspace -v
uv run pytest tests/icpy/test_terminal_service.py::TestTerminalService::test_session_creation -v
```

## Troubleshooting

### Import Errors
```bash
export PYTHONPATH=$(pwd)  # Must run from backend/ directory
```

### Missing uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

### Debug Mode
```bash
uv run pytest tests/ -v -s --log-cli-level=DEBUG
```

### Clean Environment
```bash
rm -rf .pytest_cache/ tests/__pycache__/ tests/icpy/__pycache__/
```

## Notes

- Tests are isolated and use fixtures; no running server required.
- Event loop cleanup is handled in fixtures.
- For CI, prefer `uv sync --frozen --no-dev` then `uv run pytest`.

Legacy venv alternative (not recommended):
```bash
source venv/bin/activate && export PYTHONPATH=$(pwd) && pytest tests/ -v
```
