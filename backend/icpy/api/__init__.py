"""
API module for icpy Backend

This module provides the API layer for the icpy backend system,
including WebSocket and HTTP REST APIs.

Key Components:
- WebSocket API: Real-time communication with message broker integration
- HTTP REST API: Traditional HTTP endpoints for stateless operations

Author: GitHub Copilot
Date: July 16, 2025
"""

from .websocket_api import WebSocketAPI, get_websocket_api, shutdown_websocket_api
from .rest_api import RestAPI, get_rest_api, shutdown_rest_api

__all__ = [
    'WebSocketAPI',
    'get_websocket_api',
    'shutdown_websocket_api',
    'RestAPI',
    'get_rest_api',
    'shutdown_rest_api'
]
