"""
Services module for icpy backend
Contains modular services for workspace, filesystem, terminal, and other functionality
"""

from .workspace_service import WorkspaceService, get_workspace_service, shutdown_workspace_service

__all__ = [
    'WorkspaceService',
    'get_workspace_service', 
    'shutdown_workspace_service'
]
