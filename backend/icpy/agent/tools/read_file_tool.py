"""
Read file tool for agents
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


class ReadFileTool(BaseTool):
    """Tool for reading file contents"""
    
    def __init__(self):
        super().__init__()
        self.name = "read_file"
        self.description = "Read the contents of a file, optionally specifying line range"
        self.parameters = {
            "type": "object",
            "properties": {
                "filePath": {
                    "type": "string",
                    "description": "Path to the file to read"
                },
                "startLine": {
                    "type": "integer",
                    "description": "Starting line number (1-indexed, optional)"
                },
                "endLine": {
                    "type": "integer",
                    "description": "Ending line number (1-indexed, optional)"
                }
            },
            "required": ["filePath"]
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
    
    def _validate_line_range(self, start_line: Optional[int], end_line: Optional[int]) -> Optional[str]:
        """
        Validate line range parameters
        
        Returns:
            Error message if invalid, None if valid
        """
        if start_line is not None and start_line < 1:
            return "Start line must be positive (1-indexed)"
        
        if end_line is not None and end_line < 1:
            return "End line must be positive (1-indexed)"
        
        if start_line is not None and end_line is not None and start_line > end_line:
            return "Start line cannot be greater than end line"
        
        return None
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the read file operation"""
        try:
            file_path = kwargs.get("filePath")
            start_line = kwargs.get("startLine")
            end_line = kwargs.get("endLine")
            
            if not file_path:
                return ToolResult(success=False, error="filePath is required")
            
            # Validate line range
            range_error = self._validate_line_range(start_line, end_line)
            if range_error:
                return ToolResult(success=False, error=range_error)
            
            # Get workspace root from environment or default
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
            
            # Get filesystem service
            filesystem_service = await get_filesystem_service()
            
            # Read entire file content
            content = await filesystem_service.read_file(normalized_path)
            
            if content is None:
                return ToolResult(success=False, error="Failed to read file")
            # Extract line range if specified
            if start_line is not None or end_line is not None:
                lines = content.split('\n')
                
                # Convert to 0-based indexing
                start_idx = (start_line - 1) if start_line is not None else 0
                end_idx = end_line if end_line is not None else len(lines)
                
                # Ensure indices are within bounds
                start_idx = max(0, min(start_idx, len(lines)))
                end_idx = max(start_idx, min(end_idx, len(lines)))
                
                # Extract the requested lines
                selected_lines = lines[start_idx:end_idx]
                content = '\n'.join(selected_lines)
            
            return ToolResult(
                success=True, 
                data={
                    "content": content,
                    "filePath": file_path,
                    "startLine": start_line,
                    "endLine": end_line
                }
            )
            
        except FileNotFoundError as e:
            return ToolResult(success=False, error=str(e))
        except PermissionError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error reading file {kwargs.get('filePath')}: {e}")
            return ToolResult(success=False, error=f"Failed to read file: {str(e)}") 