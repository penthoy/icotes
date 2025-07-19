# How to Test the ICPY Backend

This guide explains how to set up the testing environment and run all tests for the ICPY backend system.

## Prerequisites

- Python 3.12+
- Git
- Virtual environment support

## Environment Setup

### 1. Navigate to Backend Directory

```bash
cd backend
```

### 2. Set up Virtual Environment

If you don't have a virtual environment yet:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

If you already have a virtual environment:

```bash
# Activate existing virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
# Install all dependencies including test dependencies
pip install -r requirements.txt
```

### 4. Set Python Path

For proper module importing during tests:

```bash
export PYTHONPATH=$(pwd)
```

## Running Tests

### Run All Tests

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run all tests with detailed output and coverage
pytest tests/ -v --tb=short

# Run tests with coverage report
pytest tests/ --cov=icpy --cov-report=term-missing
```

### Run Specific Test Categories

**REST API Tests:**
```bash
pytest tests/icpy/test_rest_api.py -v
```

**CLI Interface Tests:**
```bash
pytest tests/icpy/test_cli_interface.py -v
```

**WebSocket API Tests:**
```bash
pytest tests/icpy/test_websocket_api.py -v
```

**Service Tests:**
```bash
# Workspace service tests
pytest tests/icpy/test_workspace_service.py -v

# Filesystem service tests
pytest tests/icpy/test_filesystem_service.py -v

# Terminal service tests
pytest tests/icpy/test_terminal_service.py -v
```

**Core Component Tests:**
```bash
# Message broker tests
pytest tests/icpy/test_message_broker.py -v

# Connection manager tests
pytest tests/icpy/test_connection_manager.py -v
```

### Run Tests by Pattern

```bash
# Run tests matching a pattern
pytest tests/ -k "test_file" -v

# Run tests for specific functionality
pytest tests/ -k "workspace" -v
pytest tests/ -k "terminal" -v
pytest tests/ -k "api" -v
```

### Run Individual Test Files

```bash
# Run a specific test file
pytest tests/icpy/test_rest_api.py::TestRestAPI::test_health_check -v

# Run a specific test class
pytest tests/icpy/test_rest_api.py::TestRestAPI -v

# Run a specific test method
pytest tests/icpy/test_cli_interface.py::TestHttpClient::test_make_request -v
```

## Test Environment Configuration

### Environment Variables

Set these environment variables for testing if needed:

```bash
export ICPY_TEST_MODE=true
export ICPY_TEST_BACKEND_URL=http://localhost:8000
export ICPY_LOG_LEVEL=DEBUG
```

### Mock Backend Testing

For tests that don't require a running backend:

```bash
# Most unit tests use mocked services and don't require a running backend
pytest tests/icpy/test_rest_api.py -v
pytest tests/icpy/test_workspace_service.py -v
```

### Integration Testing with Running Backend

For full integration tests:

1. **Start the backend server in a separate terminal:**
   ```bash
   # Terminal 1: Start backend
   source venv/bin/activate
   export PYTHONPATH=$(pwd)
   python main.py
   ```

2. **Run integration tests in another terminal:**
   ```bash
   # Terminal 2: Run integration tests
   source venv/bin/activate
   export PYTHONPATH=$(pwd)
   pytest tests/icpy/test_cli_interface.py::TestIntegration -v
   ```

## Test Structure

The test suite is organized as follows:

```
tests/
├── __init__.py
├── how_to_test.md           # This guide
└── icpy/
    ├── __init__.py
    ├── test_rest_api.py          # REST API endpoint tests
    ├── test_websocket_api.py     # WebSocket API tests
    ├── test_cli_interface.py     # CLI interface tests
    ├── test_workspace_service.py # Workspace management tests
    ├── test_filesystem_service.py # File operations tests
    ├── test_terminal_service.py   # Terminal management tests
    ├── test_message_broker.py    # Message broker tests
    ├── test_connection_manager.py # Connection handling tests
    ├── test_api_gateway.py       # API gateway tests
    └── test_protocol.py          # Protocol tests
```

## Test Categories

### Unit Tests
- Test individual functions and methods in isolation
- Use mocked dependencies
- Fast execution
- Located in: `test_*_service.py`, `test_message_broker.py`, `test_connection_manager.py`

### Integration Tests  
- Test interaction between components
- May require running backend
- Located in: `test_rest_api.py`, `test_websocket_api.py`, `test_cli_interface.py`

### API Tests
- Test HTTP REST endpoints
- Test WebSocket connections
- Verify request/response formats
- Located in: `test_rest_api.py`, `test_websocket_api.py`

## Common Test Commands

### Development Workflow

```bash
# Quick test run during development
pytest tests/ -x --tb=short

# Test with file watching (requires pytest-watch)
pytest-watch tests/

# Run tests in parallel (requires pytest-xdist)
pytest tests/ -n auto

# Run only failed tests from last run
pytest tests/ --lf
```

### Debugging Tests

```bash
# Run with Python debugger
pytest tests/icpy/test_rest_api.py::test_health_check -v -s --pdb

# Run with detailed output
pytest tests/ -v -s --tb=long

# Run with warnings shown
pytest tests/ -v -W ignore::DeprecationWarning
```

### Performance Testing

```bash
# Run with timing information
pytest tests/ --durations=10

# Profile test execution
pytest tests/ --profile
```

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Fix: Set Python path
export PYTHONPATH=$(pwd)

# Or run from backend directory
cd backend
pytest tests/ -v
```

**Module Not Found:**
```bash
# Fix: Ensure virtual environment is activated
source venv/bin/activate

# Fix: Install dependencies
pip install -r requirements.txt
```

**Connection Refused (Integration Tests):**
```bash
# Fix: Start backend server first
python main.py

# Or run unit tests only (no backend required)
pytest tests/icpy/test_workspace_service.py -v
```

**Permission Denied:**
```bash
# Fix: Check file permissions
chmod +x venv/bin/activate

# Fix: Check directory permissions
ls -la tests/
```

### Debug Mode

Enable debug logging for tests:

```bash
# Set environment variables
export ICPY_LOG_LEVEL=DEBUG
export PYTHONPATH=$(pwd)

# Run tests with logging
pytest tests/ -v -s --log-cli-level=DEBUG
```

### Clean Test Environment

```bash
# Remove cache files
rm -rf tests/__pycache__/
rm -rf tests/icpy/__pycache__/
rm -rf .pytest_cache/

# Remove Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
```

## Test Data and Fixtures

Tests use pytest fixtures for:
- Mock services (workspace, filesystem, terminal)
- Mock message broker and connection manager
- Test clients for API testing
- Temporary directories for file operations

Key fixtures are defined in test files and provide:
- `client_with_rest_api` - FastAPI test client with mocked services
- `mock_*_service` - Mocked service instances
- `app` - FastAPI application instance

## Contributing to Tests

When adding new tests:

1. **Follow naming conventions:**
   - Test files: `test_<component>.py`
   - Test classes: `Test<Component>`
   - Test methods: `test_<functionality>`

2. **Use appropriate fixtures:**
   - Mock external dependencies
   - Use temporary directories for file operations
   - Clean up resources in teardown

3. **Include docstrings:**
   - Describe what the test verifies
   - Include any setup requirements

4. **Test both success and error cases:**
   - Happy path testing
   - Error condition testing
   - Edge case testing

## Continuous Integration

For automated testing in CI/CD:

```bash
# CI script example
#!/bin/bash
set -e

# Setup environment
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=$(pwd)

# Run tests with coverage
pytest tests/ --cov=icpy --cov-report=xml --cov-report=term-missing

# Check test coverage
coverage report --fail-under=80
```

## Summary

The ICPY backend has a comprehensive test suite covering:
- ✅ REST API endpoints (health, workspaces, files, terminals)
- ✅ WebSocket API functionality
- ✅ CLI interface commands
- ✅ Service layer (workspace, filesystem, terminal)
- ✅ Core components (message broker, connection manager)
- ✅ Error handling and edge cases

To get started quickly:

```bash
cd backend
source venv/bin/activate
export PYTHONPATH=$(pwd)
pytest tests/ -v
```

For questions or issues, check the troubleshooting section or run tests with debug output enabled.
