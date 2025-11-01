"""
Replace string in file tool for agents

Phase 7: Uses ContextRouter to work with active hop context (local or remote)

Phase 4/7 upgrades:
- Accept namespaced paths like 'local:/path' or 'hop1:/path' in filePath
- For returnFullData=true, include namespaced `filePath`, `absolutePath`, and `pathInfo`
- Robust handling when remote reads return None (no attribute errors)
- Optionally target a specific namespace's filesystem, not just the active one
"""

import os
import logging
from typing import Dict, Any, Optional
from .base_tool import BaseTool, ToolResult
from .context_helpers import get_contextual_filesystem
from icpy.services.path_utils import get_display_path_info

# Optional import for cross-namespace FS selection
try:
    from icpy.services.context_router import get_context_router
except Exception:  # pragma: no cover
    get_context_router = None  # type: ignore

logger = logging.getLogger(__name__)


async def get_filesystem_service():
    """Import and return filesystem service for the active context (Phase 7)"""
    return await get_contextual_filesystem()


async def get_workspace_service():
    """Import and return workspace service"""
    from icpy.services import get_workspace_service as _get_workspace_service
    return await _get_workspace_service()


class ReplaceStringTool(BaseTool):
    """Tool for replacing strings in files"""
    
    def __init__(self):
        super().__init__()
        self.name = "replace_string_in_file"
        self.description = (
            "Replace a string in a file with another string. "
            "Supports namespaced paths (e.g., local:/file, hop1:/file). "
            "When returnFullData=true, response includes namespaced filePath and pathInfo."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "filePath": {
                    "type": "string",
                    "description": "Path to the file to modify. Accepts optional namespace prefix (e.g., hop1:/dir/file.txt)."
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
                },
                "returnFullData": {
                    "type": "boolean", 
                    "description": "If true, include namespaced filePath, absolutePath, pathInfo, and strings. Default false for backward compatibility."
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
                # Special case: if path starts with /workspace/, treat as relative to workspace_root
                # This handles local:/workspace/xxx from namespaced paths
                if file_path.startswith('/workspace/') or file_path.startswith('/workspace\\'):
                    relative_path = file_path[11:]  # Remove '/workspace/' (11 chars)
                    normalized_path = os.path.realpath(os.path.abspath(os.path.join(workspace_root, relative_path)))
                elif file_path == '/workspace':
                    normalized_path = workspace_root
                else:
                    # Already absolute path - check if it's within workspace
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
    
    def _generate_diff_preview(self, content: str, old_string: str, new_string: str) -> Dict[str, Any]:
        """
        Generate a diff preview showing before/after context for the first replacement
        
        Returns:
            Dict with 'before', 'after', 'lineNumber', and 'contextLines'
        """
        try:
            # Find first occurrence
            pos = content.find(old_string)
            if pos == -1:
                return {"error": "No occurrences found"}
            
            # Calculate line number
            lines_before = content[:pos].count('\n')
            line_num = lines_before + 1
            
            # Extract context: 3 lines before and after
            lines = content.split('\n')
            context_size = 3
            start_line = max(0, lines_before - context_size)
            end_line = min(len(lines), lines_before + context_size + 1)
            
            # Build before snippet
            before_lines = lines[start_line:end_line]
            before_snippet = '\n'.join(before_lines)
            
            # Build after snippet (with replacement applied)
            after_content = content.replace(old_string, new_string, 1)  # Only first occurrence
            after_lines_full = after_content.split('\n')
            after_lines = after_lines_full[start_line:end_line]
            after_snippet = '\n'.join(after_lines)
            
            return {
                "lineNumber": line_num,
                "contextLines": f"{start_line + 1}-{end_line}",
                "before": before_snippet,
                "after": after_snippet,
                "oldString": old_string,
                "newString": new_string
            }
        except Exception as e:
            logger.warning(f"Failed to generate diff preview: {e}")
            return {"error": str(e)}
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the replace string operation"""
        try:
            file_path = kwargs.get("filePath")
            old_string = kwargs.get("oldString")
            new_string = kwargs.get("newString")
            validate_context = kwargs.get("validateContext", False)
            return_full = bool(kwargs.get("returnFullData", False))
            
            if not file_path:
                return ToolResult(success=False, error="filePath is required")
            
            if old_string is None:
                return ToolResult(success=False, error="oldString is required")
            
            if new_string is None:
                return ToolResult(success=False, error="newString is required")
            
            # Parse potential namespaced path (Phase 4)
            ctx_id, parsed_abs = await self._parse_path_parameter(file_path)

            # Determine local-vs-remote normalization and workspace validation
            normalized_path = parsed_abs
            if ctx_id == "local":
                # Determine workspace root using WorkspaceService when available
                workspace_root = None
                try:
                    ws = await get_workspace_service()
                    if ws:
                        root = None
                        if hasattr(ws, 'get_workspace_root'):
                            try:
                                root = await ws.get_workspace_root()  # type: ignore[attr-defined]
                            except Exception:
                                root = None
                        if not root and getattr(ws, 'current_workspace', None) is not None:
                            try:
                                root = ws.current_workspace.root_path  # type: ignore[attr-defined]
                            except Exception:
                                root = None
                        if not root and hasattr(ws, 'get_workspace_state'):
                            try:
                                state = await ws.get_workspace_state()  # type: ignore[attr-defined]
                                if isinstance(state, dict):
                                    root = state.get('root_path')
                            except Exception:
                                root = None
                        workspace_root = root
                except Exception:
                    workspace_root = None

                if not workspace_root:
                    workspace_root = os.environ.get('WORKSPACE_ROOT')

                if not workspace_root:
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

                # Preserve relative semantics for bare local inputs, but never pass raw namespaced strings
                raw = str(file_path)
                has_namespace = (":/" in raw) and not (len(raw) >= 3 and raw[1:3] == ":/" and raw[0].isalpha())
                if has_namespace:
                    candidate = parsed_abs
                elif raw and not os.path.isabs(raw) and not raw.startswith('workspace'):
                    candidate = raw
                else:
                    candidate = parsed_abs
                normalized_path = self._validate_path(candidate, workspace_root)
                if normalized_path is None:
                    return ToolResult(
                        success=False,
                        error=f"Path is outside workspace root or invalid (namespace={ctx_id})"
                    )

            # Get filesystem service; if a specific namespace is requested, attempt to use it
            filesystem_service = None
            if get_context_router is not None:
                try:
                    router = await get_context_router()  # type: ignore[misc]
                    filesystem_service = await router.get_filesystem_for_namespace(ctx_id)  # type: ignore[attr-defined]
                except Exception:
                    filesystem_service = None
            if filesystem_service is None:
                filesystem_service = await get_filesystem_service()
            
            # Read file content
            content = await filesystem_service.read_file(normalized_path)
            if content is None:
                return ToolResult(success=False, error="Failed to read file (content is empty or unreadable)")
            
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
                    # Remote adapters return bool; local may return None
                    write_ok = await filesystem_service.write_file(normalized_path, new_content)
                    if write_ok is False:
                        return ToolResult(success=False, error=f"Failed to write modified content to {normalized_path}")

            # Return minimal data for test compatibility unless requested otherwise
            if return_full:
                # Build namespaced path metadata for UI/agent consumption
                path_info = await self._format_path_info(f"{ctx_id}:{normalized_path}")
                data = {
                    "replacedCount": occurrence_count,
                    "filePath": path_info.get("formatted_path"),
                    "absolutePath": path_info.get("absolute_path"),
                    "pathInfo": path_info,
                    "oldString": old_string,
                    "newString": new_string,
                }
                # Optional content echo with diff preview (capped)
                if kwargs.get("returnContent", False):
                    MAX_PREVIEW = 10000
                    data["originalContent"] = content[:MAX_PREVIEW]
                    data["modifiedContent"] = new_content[:MAX_PREVIEW]
                    if len(content) > MAX_PREVIEW or len(new_content) > MAX_PREVIEW:
                        data["contentTruncated"] = True
                    
                    # Add diff preview showing before/after context for first replacement
                    if occurrence_count > 0:
                        data["diff"] = self._generate_diff_preview(content, old_string, new_string)
            else:
                # Minimal data for test compatibility
                data = {"replacedCount": occurrence_count}
            
            return ToolResult(success=True, data=data)
            
        except FileNotFoundError as e:
            return ToolResult(success=False, error=str(e))
        except PermissionError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error replacing string in file {kwargs.get('filePath')}: {e}")
            return ToolResult(success=False, error=f"Failed to replace string: {str(e)}") 