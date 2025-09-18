"""
Services module for icpy backend
Contains modular services for workspace, filesystem, terminal, state synchronization, agent management, and preview
"""

from .workspace_service import WorkspaceService, get_workspace_service, shutdown_workspace_service
from .filesystem_service import FileSystemService, get_filesystem_service, shutdown_filesystem_service
from .terminal_service import TerminalService, get_terminal_service, shutdown_terminal_service
from .state_sync_service import StateSyncService, get_state_sync_service, shutdown_state_sync_service
from .agent_service import AgentService, get_agent_service, shutdown_agent_service
from .chat_service import ChatService, get_chat_service, shutdown_chat_service
from .code_execution_service import CodeExecutionService, get_code_execution_service, shutdown_code_execution_service
from .source_control_service import SourceControlService, get_source_control_service, shutdown_source_control_service
from .preview_service import PreviewService, get_preview_service, initialize_preview_service, shutdown_preview_service

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
    'shutdown_state_sync_service',
    'AgentService',
    'get_agent_service',
    'shutdown_agent_service',
    'ChatService',
    'get_chat_service',
    'shutdown_chat_service',
    'CodeExecutionService',
    'get_code_execution_service',
    'shutdown_code_execution_service',
    'SourceControlService',
    'get_source_control_service',
    'shutdown_source_control_service',
    'PreviewService',
    'get_preview_service',
    'initialize_preview_service',
    'shutdown_preview_service'
]
