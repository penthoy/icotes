# How to Test the ICPY Backend

Quick guide to run tests for the ICPY backend system.

**⚠️ CRITICAL: Always use the virtual environment!**

**Common mistake:** Running tests without `source venv/bin/activate` first will cause pydantic version conflicts and import errors.

## Quick Start

```bash
cd backend
source venv/bin/activate  # ALWAYS DO THIS FIRST!
export PYTHONPATH=$(pwd)
pytest tests/ -v
```

## Prerequisites

- Python 3.12+
- Virtual environment activated
- Dependencies installed (`pip install -r requirements.txt`)

## Test Commands

### All Tests (Recommended)
```bash
pytest tests/ -v --tb=short
```

### Current Status: **172/172 Core Tests Passing ✅**

| Test Suite | Status | Count | Command |
|------------|--------|--------|---------|
| Connection Manager | ✅ | 16/16 | `pytest tests/icpy/test_connection_manager.py -v` |
| Filesystem Service | ✅ | 26/26 | `pytest tests/icpy/test_filesystem_service.py -v` |
| Workspace Service | ✅ | 19/19 | `pytest tests/icpy/test_workspace_service.py -v` |
| Terminal Service | ✅ | 33/33 | `pytest tests/icpy/test_terminal_service.py -v` |
| WebSocket API | ✅ | 30/30 | `pytest tests/icpy/test_websocket_api.py -v` |
| Message Broker | ✅ | 25/25 | `pytest tests/icpy/test_message_broker.py -v` |
| Protocol | ✅ | 23/23 | `pytest tests/icpy/test_protocol.py -v` |
| REST API | ⏸️ | 0/34 | `pytest tests/icpy/test_rest_api.py -v` (FastAPI version issue) |

### Run Multiple Suites
```bash
# All working tests
pytest tests/icpy/test_connection_manager.py tests/icpy/test_filesystem_service.py tests/icpy/test_workspace_service.py tests/icpy/test_terminal_service.py tests/icpy/test_websocket_api.py tests/icpy/test_message_broker.py tests/icpy/test_protocol.py -v

# Just service tests
pytest tests/icpy/test_*_service.py -v

# Just API tests  
pytest tests/icpy/test_websocket_api.py tests/icpy/test_protocol.py -v
```

## Development Commands

### Quick Test During Development
```bash
pytest tests/ -x --tb=short  # Stop on first failure
pytest tests/ --lf           # Run only failed tests from last run
```

### Pattern-Based Testing  
```bash
pytest tests/ -k "workspace" -v    # Test workspace functionality
pytest tests/ -k "terminal" -v     # Test terminal functionality  
pytest tests/ -k "connection" -v   # Test connection management
```

### Individual Test Methods
```bash
pytest tests/icpy/test_workspace_service.py::TestWorkspaceService::test_create_workspace -v
pytest tests/icpy/test_terminal_service.py::TestTerminalService::test_session_creation -v
```

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
export PYTHONPATH=$(pwd)  # Run from backend/ directory
```

**Module Not Found:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Connection Manager/Message Broker Errors:**
```bash
# These are usually resolved by proper test fixtures (already fixed)
# If you see "Event loop is closed" errors, the test fixtures handle this
```

### Debug Mode
```bash
pytest tests/ -v -s --log-cli-level=DEBUG
```

### Clean Environment  
```bash
# Clear cache
rm -rf .pytest_cache/ tests/__pycache__/ tests/icpy/__pycache__/
```

## Test Architecture

```
tests/icpy/
├── test_connection_manager.py    # Connection/session management (16 tests) ✅
├── test_filesystem_service.py    # File operations (26 tests) ✅  
├── test_workspace_service.py     # Workspace management (19 tests) ✅
├── test_terminal_service.py      # Terminal sessions (33 tests) ✅
├── test_websocket_api.py         # WebSocket API (30 tests) ✅
├── test_message_broker.py        # Message routing (25 tests) ✅
├── test_protocol.py             # Protocol handling (23 tests) ✅
└── test_rest_api.py            # HTTP REST endpoints (34 tests) ⏸️
```

**Key Features:**
- **Mocked Dependencies**: All tests use mocked services - no backend server required
- **Event Loop Safety**: Test fixtures handle async cleanup automatically  
- **Isolated Tests**: Each test runs independently with fresh service instances
- **Comprehensive Coverage**: Tests cover success paths, error conditions, and edge cases

## Contributing

When adding tests:

1. **Follow naming**: `test_<functionality>.py`, `test_<specific_case>`
2. **Use fixtures**: Services are automatically mocked in test fixtures  
3. **Test both success and failure cases**
4. **Add docstrings** explaining what the test verifies

Example:
```python
async def test_create_workspace(self, workspace_service):
    """Test successful workspace creation"""
    workspace = await workspace_service.create_workspace("test", "/tmp")
    assert workspace.name == "test"
```

## Summary

The ICPY backend test suite provides **172 passing tests** covering all core functionality:
- ✅ Connection & session management
- ✅ File system operations  
- ✅ Workspace management
- ✅ Terminal services
- ✅ WebSocket communication
- ✅ Message broker
- ✅ Protocol handling

**Quick test run:**
```bash
cd backend && source venv/bin/activate && export PYTHONPATH=$(pwd) && pytest tests/ -v
```
