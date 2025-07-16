"""
CLI module for icpy Backend

This module provides command-line interface functionality for interacting with the icpy backend,
enabling external tools and AI agents to interact with the editor through CLI commands.

Key Components:
- CLI Interface: Command-line tool for file operations, terminal access, and workspace management
- HTTP Client: Communication with the backend REST API
- Command Handlers: Specific handlers for different CLI commands

Author: GitHub Copilot
Date: July 16, 2025
"""

from .icpy_cli import main as cli_main, IcpyCLI
from .http_client import HttpClient
from .command_handlers import CommandHandlers

__all__ = [
    'cli_main',
    'IcpyCLI',
    'HttpClient',
    'CommandHandlers'
]
