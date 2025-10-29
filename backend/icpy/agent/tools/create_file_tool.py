"""
Create file tool for agents

Phase 7: Uses ContextRouter to work with active hop context (local or remote)
"""

import os
import logging
from typing import Dict, Any, Optional
from .base_tool import BaseTool, ToolResult
from .context_helpers import get_contextual_filesystem

logger = logging.getLogger(__name__)


async def get_filesystem_service():
    """Import and return filesystem service for the active context (Phase 7)"""
    return await get_contextual_filesystem()


async def get_workspace_service():
    """Import and return workspace service (shim for test patching)"""
    try:
        from icpy.services import get_workspace_service as _get_workspace_service
        return await _get_workspace_service()
    except ImportError:
        return None


class CreateFileTool(BaseTool):
    """Tool for creating new files"""
    
    def __init__(self):
        super().__init__()
        self.name = "create_file"
        self.description = "Create a new file with specified content"
        self.parameters = {
            "type": "object",
            "properties": {
                "filePath": {
                    "type": "string",
                    "description": "Path where the file should be created"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                },
                "createDirectories": {
                    "type": "boolean",
                    "description": "Whether to create parent directories if they don't exist"
                }
            },
            "required": ["filePath", "content"]
        }
    
    def _validate_path(self, file_path: str, workspace_root: str) -> Optional[str]:
        """
        Validate and normalize file path to prevent traversal outside workspace
        
        Returns:
            Normalized absolute path if valid, None if invalid
        """
        try:
            # Normalize the workspace root
            workspace_root = os.path.abspath(workspace_root)
            
            # Handle absolute vs relative paths
            if os.path.isabs(file_path):
                normalized_path = os.path.abspath(file_path)
            else:
                # For relative paths, check if they already include workspace
                if file_path.startswith('workspace/') or file_path.startswith('workspace\\'):
                    # Remove 'workspace/' prefix and join with workspace_root
                    relative_path = file_path[10:]  # Remove 'workspace/' (10 chars)
                    normalized_path = os.path.abspath(os.path.join(workspace_root, relative_path))
                elif file_path == 'workspace':
                    normalized_path = os.path.abspath(workspace_root)
                else:
                    # Normal relative path from workspace root
                    normalized_path = os.path.abspath(os.path.join(workspace_root, file_path))
            
            # Check if the normalized path is within workspace
            if not normalized_path.startswith(workspace_root):
                return None
            
            return normalized_path
            
        except Exception:
            return None
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the create file operation"""
        try:
            file_path = kwargs.get("filePath")
            content = kwargs.get("content")
            create_directories = kwargs.get("createDirectories", False)
            
            if not file_path:
                return ToolResult(success=False, error="filePath is required")
            
            if content is None:
                return ToolResult(success=False, error="content is required")
            
            # Determine workspace root using WorkspaceService when available
            workspace_root = None
            try:
                ws = await get_workspace_service()
                if ws:
                    # Prefer active workspace root from service
                    root = None
                    # Some implementations may expose a coroutine get_workspace_root()
                    if hasattr(ws, 'get_workspace_root'):
                        try:
                            root = await ws.get_workspace_root()  # type: ignore[attr-defined]
                        except Exception:
                            root = None
                    # Fall back to current_workspace.root_path if available
                    if not root and getattr(ws, 'current_workspace', None) is not None:
                        try:
                            root = ws.current_workspace.root_path  # type: ignore[attr-defined]
                        except Exception:
                            root = None
                    # Fall back to get_workspace_state()['root_path']
                    if not root and hasattr(ws, 'get_workspace_state'):
                        try:
                            state = await ws.get_workspace_state()  # type: ignore[attr-defined]
                            if isinstance(state, dict):
                                root = state.get('root_path')
                        except Exception:
                            root = None
                    workspace_root = root
            except Exception:
                # Fallback to env or static detection
                workspace_root = None

            if not workspace_root:
                workspace_root = os.environ.get('WORKSPACE_ROOT')
            
            if not workspace_root:
                # Default to workspace directory relative to backend
                # From: /path/to/icotes/backend/icpy/agent/tools -> /path/to/icotes/workspace
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                workspace_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(backend_dir)))), 'workspace')
            
            # Validate and normalize path
            normalized_path = self._validate_path(file_path, workspace_root)
            if normalized_path is None:
                return ToolResult(
                    success=False, 
                    error="Path is outside workspace root or invalid"
                )
            
            # Get filesystem service (use wrapper so tests can patch this)
            filesystem_service = await get_filesystem_service()
            
            # Create parent directories if requested
            if create_directories:
                parent_dir = os.path.dirname(normalized_path)
                if parent_dir != workspace_root:
                    await filesystem_service.create_directory(parent_dir)
            
            # Write file and verify success
            # Phase 8: Check return value from remote_fs_adapter (returns bool for success/failure)
            result = await filesystem_service.write_file(normalized_path, content)
            
            # For remote filesystem adapter, result is a boolean indicating success
            # Local filesystem service returns None on success, but for consistency we check
            if result is False:
                return ToolResult(
                    success=False,
                    error=f"Failed to write file {normalized_path}. This may indicate an event loop synchronization issue when hopped to a remote server."
                )
            
            return ToolResult(success=True, data={"created": True})
            
        except FileExistsError as e:
            return ToolResult(success=False, error=str(e))
        except FileNotFoundError as e:
            return ToolResult(success=False, error=str(e))
        except PermissionError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error creating file {kwargs.get('filePath')}: {e}")
            return ToolResult(success=False, error=f"Failed to create file: {str(e)}") 