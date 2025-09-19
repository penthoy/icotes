# How to Test the Backend (uv)

Use the uv package manager for fast, isolated test runs.
## Prerequisites

- Python 3.12+
- uv installed
Install uv (if missing):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```
## Quick Start

From the `backend/` directory:
```bash
# Sync dependencies declared in pyproject.toml/uv.lock
uv sync --frozen --no-dev

# Ensure module discovery works
export PYTHONPATH=$(pwd)

# Run all tests
uv run pytest tests/ -v --tb=short
```
## Running Specific Tests

- All tests: `uv run pytest tests/ -v --tb=short`
- Specific suite: `uv run pytest tests/icpy/test_workspace_service.py -v`
- Pattern match: `uv run pytest tests/ -k "workspace" -v`
- Stop on first failure: `uv run pytest tests/ -x --tb=short`

## Troubleshooting
- Import errors: ensure `export PYTHONPATH=$(pwd)` while in `backend/`
- Missing uv: install as above
- Clean caches: `rm -rf .pytest_cache/ tests/__pycache__/ tests/icpy/__pycache__/`

## Notes
- Tests use fixtures; no running server required
- Some REST API tests may be skipped due to FastAPI version constraints
- For CI, use `uv sync --frozen --no-dev` then `uv run pytest`
# Testing Guide for icpy Backend

This guide covers how to run tests using modern `uv` package manager commands.

## Prerequisites

1. Install `uv` package manager:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   export PATH="$HOME/.local/bin:$PATH"
   ```

2. Set up the project environment:
   ```bash
   cd backend
   uv sync --frozen --no-dev  # Install from requirements.txt
   ```

## Running Tests

### All Tests
```bash
cd backend
uv run pytest
```

### Specific Test Files
```bash
# Framework validation tests
uv run pytest tests/icpy/test_agentic_frameworks.py -v

# Framework compatibility tests  
uv run pytest tests/icpy/test_framework_compatibility.py -v

# Specific service tests
uv run pytest tests/icpy/test_filesystem_service.py -v
uv run pytest tests/icpy/test_terminal_service.py -v
uv run pytest tests/icpy/test_workspace_service.py -v
```

### Specific Test Classes or Methods
```bash
# Run specific test class
uv run pytest tests/icpy/test_agentic_frameworks.py::TestAgenticFrameworks -v

# Run specific test method
uv run pytest tests/icpy/test_agentic_frameworks.py::TestAgenticFrameworks::test_framework_imports -v
```

### Test with Coverage
```bash
# Install coverage if not already installed
uv pip install coverage

# Run tests with coverage
uv run coverage run -m pytest
uv run coverage report
uv run coverage html  # Generate HTML report
```

### Test with Output
```bash
# Show print statements and detailed output
uv run pytest -v -s

# Show only test names
uv run pytest --tb=short
```

### Validation Scripts
```bash
# Run Step 6.1 validation
uv run python validate_step_6_1.py

# Run any validation script
uv run python <script_name>.py
```

## Test Organization

### Directory Structure
```
backend/tests/
├── icpy/                          # ICPY service tests
│   ├── test_agentic_frameworks.py # Framework installation tests
│   ├── test_framework_compatibility.py # Compatibility layer tests
│   ├── test_filesystem_service.py # File system service tests
│   ├── test_terminal_service.py   # Terminal service tests
│   ├── test_workspace_service.py  # Workspace service tests
│   └── ...
└── integration/                   # Integration tests
    └── ...
```

### Test Categories

1. **Framework Tests** (`test_agentic_frameworks.py`):
   - Framework import validation
   - Basic agent creation
   - Cross-framework compatibility
   - Error handling

2. **Compatibility Tests** (`test_framework_compatibility.py`):
   - Unified interface validation
   - Multi-agent management
   - Streaming execution
   - Lifecycle management

3. **Service Tests**:
   - Individual service functionality
   - Integration with message broker
   - Real-time event handling

## Continuous Integration

For CI/CD pipelines, use:
```bash
# Install uv in CI
curl -LsSf https://astral.sh/uv/install.sh | sh

# Set up and test
cd backend
uv sync --frozen --no-dev  # Install from requirements.txt
uv run pytest --junitxml=test-results.xml
```

## Debugging Tests

### Verbose Output
```bash
uv run pytest -v -s --tb=long
```

### Run Single Test for Debugging
```bash
uv run pytest tests/icpy/test_agentic_frameworks.py::TestAgenticFrameworks::test_framework_imports -v -s
```

### Debug with Print Statements
```bash
# Add print statements to tests and run with -s flag
uv run pytest -s tests/your_test.py
```

## Performance Testing

### Test Execution Time
```bash
uv run pytest --durations=10  # Show 10 slowest tests
```

### Parallel Testing
```bash
# Install pytest-xdist for parallel execution
uv pip install pytest-xdist

# Run tests in parallel
uv run pytest -n auto  # Use all available cores
uv run pytest -n 4     # Use 4 cores
```

## Legacy Approach (if needed)

If you need to use the legacy virtual environment approach:
```bash
cd backend
python -m pytest  # Run directly with system Python
```

However, the `uv` approach is recommended for better performance and dependency management.
