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
   uv venv
   uv pip install -r requirements.txt
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
uv venv
uv pip install -r requirements.txt
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
source venv/bin/activate
python -m pytest
```

However, the `uv` approach is recommended for better performance and dependency management.
