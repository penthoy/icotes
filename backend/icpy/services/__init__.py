"""
Services module for icpy backend
Contains modular services for workspace, filesystem, terminal, and other functionality
"""

from .workspace_service import WorkspaceService, get_workspace_service, shutdown_workspace_service
from .filesystem_service import FileSystemService, get_filesystem_service, shutdown_filesystem_service

__all__ = [
    'WorkspaceService',
    'get_workspace_service', 
    'shutdown_workspace_service',
    'FileSystemService',
    'get_filesystem_service',
    'shutdown_filesystem_service'
]
