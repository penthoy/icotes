"""
Create file tool for agents

Phase 7: Uses ContextRouter to work with active hop context (local or remote)

Phase 1 (Namespace Path Utils):
- When requested via returnFullData, include namespaced file path metadata in
    the result under `filePath` (namespaced), `absolutePath`, and `pathInfo`.
    This maintains backward compatibility with existing tests and agents.
"""

import os
import logging
import hashlib
from typing import Dict, Any, Optional
from .base_tool import BaseTool, ToolResult
from .context_helpers import get_contextual_filesystem
try:
    # Optional import for namespace-specific FS resolution
    from icpy.services.context_router import get_context_router
except Exception:  # pragma: no cover
    get_context_router = None  # type: ignore

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
        self.description = (
            "Create a new file with specified content. Accepts namespaced paths (e.g., local:/file, hop1:/file). "
            "When returnFullData=true, response includes namespaced file path and pathInfo."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "filePath": {
                    "type": "string",
                    "description": "Path where the file should be created. Optional namespace prefix supported (e.g., hop1:/dir/file.txt)."
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                },
                "createDirectories": {
                    "type": "boolean",
                    "description": "Whether to create parent directories if they don't exist"
                },
                "returnFullData": {
                    "type": "boolean",
                    "description": "If true, include namespaced filePath, absolutePath, and pathInfo in the result."
                },
                "returnChecksum": {
                    "type": "boolean",
                    "description": "If true, compute and return SHA256 checksum of the content for verification. Default false."
                },
                "returnPreview": {
                    "type": "integer",
                    "description": "If provided, return the first N lines of content as a preview for verification. Default: no preview."
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
                # Special case: if path starts with /workspace/, treat as relative to workspace_root
                # This handles local:/workspace/xxx from namespaced paths
                if file_path.startswith('/workspace/') or file_path.startswith('/workspace\\'):
                    relative_path = file_path[11:]  # Remove '/workspace/' (11 chars)
                    normalized_path = os.path.abspath(os.path.join(workspace_root, relative_path))
                elif file_path == '/workspace':
                    normalized_path = os.path.abspath(workspace_root)
                else:
                    # Already absolute path - check if it's within workspace
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
            
            # Check if the normalized path is within workspace using canonical paths
            # This prevents bypass with paths like /workspace_bad or /workspace2
            try:
                canonical_workspace = os.path.realpath(workspace_root)
                canonical_path = os.path.realpath(normalized_path)
                # Ensure the canonical path starts with the canonical workspace
                # os.path.commonpath will be the workspace if path is within it
                if os.path.commonpath([canonical_workspace, canonical_path]) != canonical_workspace:
                    return None
            except (ValueError, OSError):
                # commonpath can raise ValueError on Windows with different drives
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
            return_full = bool(kwargs.get("returnFullData", False))
            
            if not file_path:
                return ToolResult(success=False, error="filePath is required")
            
            if content is None:
                return ToolResult(success=False, error="content is required")
            
            # Parse potential namespaced path (Phase 4)
            ctx_id, parsed_abs = await self._parse_path_parameter(file_path)

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
                    workspace_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(backend_dir)))), 'workspace')

                # Preserve relative semantics for bare local inputs, but never pass a namespaced raw string
                # Detect if the raw input had a namespace like "ns:/path" (exclude Windows drive letters like C:/)
                raw = str(file_path)
                has_namespace = (":/" in raw) and not (len(raw) >= 3 and raw[1:3] == ":/" and raw[0].isalpha())
                if has_namespace:
                    candidate = parsed_abs
                elif raw and not os.path.isabs(raw) and not raw.startswith('workspace'):
                    candidate = raw
                else:
                    candidate = parsed_abs
                # Validate local normalized path against workspace boundaries
                normalized_path = self._validate_path(candidate, workspace_root)
                if normalized_path is None:
                    return ToolResult(
                        success=False,
                        error=f"Path is outside workspace root or invalid (namespace={ctx_id})"
                    )
            
            # Get filesystem service; prefer patched/local service for tests and local ctx,
            # but use router when an explicit remote namespace is requested.
            filesystem_service = None
            try:
                # First, prefer the generic contextual FS (tests patch this)
                filesystem_service = await get_filesystem_service()
            except Exception:
                filesystem_service = None

            # For explicit non-local namespaces, try router-specific FS
            if (ctx_id != "local") and get_context_router is not None:
                try:
                    router = await get_context_router()  # type: ignore[misc]
                    namespaced_fs = await router.get_filesystem_for_namespace(ctx_id)  # type: ignore[attr-defined]
                    if namespaced_fs is not None:
                        filesystem_service = namespaced_fs
                except Exception:
                    # Keep previously obtained filesystem_service
                    pass

            if filesystem_service is None:
                # Final fallback to contextual FS
                filesystem_service = await get_filesystem_service()
            
            # Create parent directories if requested
            if create_directories:
                parent_dir = os.path.dirname(normalized_path)
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
            
            # Compute checksum if requested
            checksum = None
            if kwargs.get("returnChecksum", False):
                try:
                    checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
                    logger.debug(f"Computed SHA256 checksum for {normalized_path}: {checksum}")
                except Exception as e:
                    logger.warning(f"Failed to compute checksum: {e}")
            
            # Generate preview if requested
            preview = None
            preview_lines_count = kwargs.get("returnPreview")
            if preview_lines_count and isinstance(preview_lines_count, int) and preview_lines_count > 0:
                try:
                    lines = content.split('\n')
                    preview_lines = lines[:preview_lines_count]
                    preview = '\n'.join(preview_lines)
                    if len(lines) > preview_lines_count:
                        preview += f"\n... ({len(lines) - preview_lines_count} more lines)"
                    logger.debug(f"Generated preview ({preview_lines_count} lines) for {normalized_path}")
                except Exception as e:
                    logger.warning(f"Failed to generate preview: {e}")
            
            if return_full:
                # Build namespaced path metadata for UI/agent consumption
                # Force the intended namespace so display is consistent even when hopped
                path_info = await self._format_path_info(f"{ctx_id}:{normalized_path}")
                # Keep backward compatibility while enriching payload
                result_data = {
                    "created": True,
                    "filePath": path_info.get("formatted_path"),
                    "absolutePath": path_info.get("absolute_path"),
                    "pathInfo": path_info,
                }
                
                # Add checksum if computed
                if checksum:
                    result_data["sha256"] = checksum
                
                # Add preview if generated
                if preview:
                    result_data["contentPreview"] = preview
                    result_data["previewLines"] = preview_lines_count
                
                return ToolResult(success=True, data=result_data)
            else:
                # Minimal data for backward compatibility with existing tests
                result_data = {"created": True}
                
                # Add checksum if computed (even in minimal mode, checksum is useful)
                if checksum:
                    result_data["sha256"] = checksum
                
                # Add preview if generated
                if preview:
                    result_data["contentPreview"] = preview
                    result_data["previewLines"] = preview_lines_count
                
                return ToolResult(success=True, data=result_data)
            
        except FileExistsError as e:
            return ToolResult(success=False, error=str(e))
        except FileNotFoundError as e:
            return ToolResult(success=False, error=str(e))
        except PermissionError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error creating file {kwargs.get('filePath')}: {e}")
            return ToolResult(success=False, error=f"Failed to create file: {str(e)}") 