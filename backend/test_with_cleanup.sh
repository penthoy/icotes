#!/bin/bash
# Test runner with automatic cleanup of test artifacts

set -e

echo "Running backend tests with cleanup..."

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up test artifacts..."
    python3 cleanup_test_artifacts.py
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Run tests
uv run pytest "$@"

echo "Tests completed."