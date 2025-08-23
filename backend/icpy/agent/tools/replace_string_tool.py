"""
Replace string in file tool for agents
"""

import os
import logging
from typing import Dict, Any, Optional
from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


async def get_filesystem_service():
    """Import and return filesystem service"""
    from icpy.services.filesystem_service import get_filesystem_service as _get_filesystem_service
    return await _get_filesystem_service()


async def get_workspace_service():
    """Import and return workspace service"""
    from icpy.services import get_workspace_service as _get_workspace_service
    return await _get_workspace_service()


class ReplaceStringTool(BaseTool):
    """Tool for replacing strings in files"""
    
    def __init__(self):
        super().__init__()
        self.name = "replace_string_in_file"
        self.description = "Replace a string in a file with another string"
        self.parameters = {
            "type": "object",
            "properties": {
                "filePath": {
                    "type": "string",
                    "description": "Path to the file to modify"
                },
                "oldString": {
                    "type": "string",
                    "description": "String to be replaced"
                },
                "newString": {
                    "type": "string",
                    "description": "String to replace with"
                },
                "validateContext": {
                    "type": "boolean",
                    "description": "Whether to validate that exactly one occurrence exists before replacement"
                },
                "returnContent": {
                    "type": "boolean",
                    "description": "Include original/modified content in the result (truncated). Default: false"
                }
            },
            "required": ["filePath", "oldString", "newString"]
        }
    
    def _validate_path(self, file_path: str, workspace_root: str) -> Optional[str]:
        """
        Validate and normalize file path to prevent traversal outside workspace
        
        Returns:
            Normalized absolute path if valid, None if invalid
        """
        try:
            # Normalize and resolve symlinks
            workspace_root = os.path.realpath(os.path.abspath(workspace_root))
            
            # Handle absolute vs relative paths
            if os.path.isabs(file_path):
                normalized_path = os.path.realpath(os.path.abspath(file_path))
            else:
                # For relative paths, check if they already include workspace
                if file_path.startswith('workspace/') or file_path.startswith('workspace\\'):
                    # Remove 'workspace/' prefix and join with workspace_root
                    relative_path = file_path[10:]  # Remove 'workspace/' (10 chars)
                    normalized_path = os.path.realpath(os.path.abspath(os.path.join(workspace_root, relative_path)))
                elif file_path == 'workspace':
                    normalized_path = workspace_root
                else:
                    # Normal relative path from workspace root
                    normalized_path = os.path.realpath(os.path.abspath(os.path.join(workspace_root, file_path)))
            
            # Ensure normalized_path is within workspace_root
            if os.path.commonpath([workspace_root, normalized_path]) != workspace_root:
                return None
            
            return normalized_path
            
        except Exception:
            return None
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the replace string operation"""
        try:
            file_path = kwargs.get("filePath")
            old_string = kwargs.get("oldString")
            new_string = kwargs.get("newString")
            validate_context = kwargs.get("validateContext", False)
            
            if not file_path:
                return ToolResult(success=False, error="filePath is required")
            
            if old_string is None:
                return ToolResult(success=False, error="oldString is required")
            
            if new_string is None:
                return ToolResult(success=False, error="newString is required")
            
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
                workspace_root = os.path.join(
                    os.path.dirname(
                        os.path.dirname(
                            os.path.dirname(
                                os.path.dirname(backend_dir)
                            )
                        )
                    ),
                    'workspace'
                )
            
            # Validate and normalize path
            normalized_path = self._validate_path(file_path, workspace_root)
            if normalized_path is None:
                return ToolResult(
                    success=False, 
                    error="Path is outside workspace root or invalid"
                )
            
            # Get filesystem service
            filesystem_service = await get_filesystem_service()
            
            # Read file content
            content = await filesystem_service.read_file(normalized_path)
            
            # Count occurrences
            occurrence_count = content.count(old_string)
            
            # Validate context if requested
            if validate_context:
                if occurrence_count != 1:
                    return ToolResult(
                        success=False,
                        error=f"validateContext requires exactly one occurrence, found {occurrence_count}"
                    )
            
            # Perform replacement
            new_content = content
            if occurrence_count > 0:
                new_content = content.replace(old_string, new_string)
                if new_content != content:
                    await filesystem_service.write_file(normalized_path, new_content)

            data = {
                "replacedCount": occurrence_count,
                "filePath": normalized_path,
                "oldString": old_string,
                "newString": new_string
            }
            # Optional content echo (capped)
            if kwargs.get("returnContent", False):
                MAX_PREVIEW = 10000
                data["originalContent"] = content[:MAX_PREVIEW]
                data["modifiedContent"] = new_content[:MAX_PREVIEW]
                if len(content) > MAX_PREVIEW or len(new_content) > MAX_PREVIEW:
                    data["contentTruncated"] = True
            
            return ToolResult(success=True, data=data)
            
        except FileNotFoundError as e:
            return ToolResult(success=False, error=str(e))
        except PermissionError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error replacing string in file {kwargs.get('filePath')}: {e}")
            return ToolResult(success=False, error=f"Failed to replace string: {str(e)}") 