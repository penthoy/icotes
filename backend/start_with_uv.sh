#!/bin/bash
# Modern uv-based startup script
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)"
uv run python main.py
