"""
Services module for icpy backend
Contains modular services for workspace, filesystem, terminal, state synchronization, and other functionality
"""

from .workspace_service import WorkspaceService, get_workspace_service, shutdown_workspace_service
from .filesystem_service import FileSystemService, get_filesystem_service, shutdown_filesystem_service
from .terminal_service import TerminalService, get_terminal_service, shutdown_terminal_service
from .state_sync_service import StateSyncService, get_state_sync_service, shutdown_state_sync_service

__all__ = [
    'WorkspaceService',
    'get_workspace_service', 
    'shutdown_workspace_service',
    'FileSystemService',
    'get_filesystem_service',
    'shutdown_filesystem_service',
    'TerminalService',
    'get_terminal_service',
    'shutdown_terminal_service',
    'StateSyncService',
    'get_state_sync_service',
    'shutdown_state_sync_service'
]
