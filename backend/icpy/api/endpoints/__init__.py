"""
API endpoint modules for main.py integration.

This module provides easy imports for all endpoint handlers.
"""

from .health import health_check, healthz, get_frontend_config
from .auth import auth_info, user_profile, debug_test_token
from .clipboard import set_clipboard, get_clipboard, get_clipboard_history, get_clipboard_status, clear_clipboard, ClipboardResponse
from .preview import create_preview, update_preview, get_preview_status, delete_preview, serve_preview_file, PreviewCreateResponse, PreviewStatusResponse
from .agents import (
    get_custom_agents, get_configured_custom_agents, reload_custom_agents_endpoint,
    reload_environment_endpoint, update_api_keys_endpoint, get_api_keys_status_endpoint,
    get_api_key_value_endpoint, get_custom_agent_info
)
from .websockets import agent_stream_websocket, workflow_monitor_websocket, chat_websocket

__all__ = [
    # Health endpoints
    'health_check', 'healthz', 'get_frontend_config',
    
    # Auth endpoints
    'auth_info', 'user_profile', 'debug_test_token',
    
    # Clipboard endpoints
    'set_clipboard', 'get_clipboard', 'get_clipboard_history', 
    'get_clipboard_status', 'clear_clipboard', 'ClipboardResponse',
    
    # Preview endpoints
    'create_preview', 'update_preview', 'get_preview_status', 
    'delete_preview', 'serve_preview_file', 'PreviewCreateResponse', 'PreviewStatusResponse',
    
    # Agent endpoints
    'get_custom_agents', 'get_configured_custom_agents', 'reload_custom_agents_endpoint',
    'reload_environment_endpoint', 'update_api_keys_endpoint', 'get_api_keys_status_endpoint',
    'get_api_key_value_endpoint', 'get_custom_agent_info',
    
    # WebSocket endpoints
    'agent_stream_websocket', 'workflow_monitor_websocket', 'chat_websocket'
]