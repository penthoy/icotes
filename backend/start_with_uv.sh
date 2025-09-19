#!/bin/bash
# Modern uv-based startup script
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)"

# Ensure uv is on PATH (common install location)
export PATH="$HOME/.local/bin:$PATH"

# Sync dependencies quickly (no dev) if lock or pyproject present
if [ -f "uv.lock" ] || [ -f "pyproject.toml" ]; then
	uv sync --frozen --no-dev || true
fi

uv run python main.py
