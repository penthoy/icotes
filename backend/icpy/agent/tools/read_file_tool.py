"""
Read file tool for agents

Phase 7: Uses ContextRouter to work with active hop context (local or remote)

Phase 1 (Namespace Path Utils):
- When returnFullData=true, enrich the response with namespaced path metadata
    under `filePath` (namespaced), `absolutePath`, and `pathInfo`.

Phase 8 (Image Handling):
- Detects image files and returns ImageReference instead of raw content
- Prevents token overflow from reading large binary files as text
"""

import os
import logging
import base64
from typing import Dict, Any, Optional
from .base_tool import BaseTool, ToolResult
from .context_helpers import get_contextual_filesystem
from icpy.services.path_utils import get_display_path_info

logger = logging.getLogger(__name__)

# Common image file extensions
IMAGE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg', 
    '.ico', '.tiff', '.tif', '.heic', '.heif'
}


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


async def get_image_reference_service():
    """Import and return image reference service"""
    try:
        from icpy.services.image_reference_service import get_image_reference_service as _get_img_svc
        return _get_img_svc()
    except ImportError:
        return None


class ReadFileTool(BaseTool):
    """Tool for reading file contents"""
    
    def __init__(self):
        super().__init__()
        self.name = "read_file"
        self.description = (
            "Read the contents of a file, optionally specifying line range. "
            "For image files, returns an ImageReference with thumbnail instead of raw content to avoid token overflow. "
            "Supports namespaced paths like 'local:/path' or 'hop1:/path' and returns pathInfo when requested."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "filePath": {
                    "type": "string",
                    "description": "Path to the file to read. Accepts optional namespace prefix (e.g., local:/file, hop1:/file). For images, returns ImageReference."
                },
                "startLine": {
                    "type": "integer",
                    "description": "Starting line number (1-indexed, optional, ignored for image files)"
                },
                "endLine": {
                    "type": "integer",
                    "description": "Ending line number (1-indexed, optional, ignored for image files)"
                },
                "returnFullData": {
                    "type": "boolean",
                    "description": "If true, includes namespaced filePath, absolutePath, pathInfo, and line numbers. Default false for backward compatibility."
                }
            },
            "required": ["filePath"]
        }
    
    def _is_image_file(self, file_path: str) -> bool:
        """Check if file is an image based on extension"""
        ext = os.path.splitext(file_path.lower())[1]
        return ext in IMAGE_EXTENSIONS
    
    async def _create_image_reference(self, file_path: str, ctx_id: str, ctx_host: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create an ImageReference for an image file.
        
        Args:
            file_path: Absolute path to image file
            ctx_id: Context ID (local or hop)
            ctx_host: Host address if remote
            
        Returns:
            ImageReference dict or None if failed
        """
        try:
            # Get image reference service
            img_service = await get_image_reference_service()
            if not img_service:
                logger.warning("ImageReferenceService not available for image file")
                return None

            # Preferred: leverage ImagenTool's robust, hop-aware loader if available
            image_bytes = None
            mime_type_from_loader: Optional[str] = None
            try:
                from .imagen_tool import ImagenTool  # Lightweight import; safe even without Google SDK
                loader = ImagenTool()
                part = await loader._decode_image_input(f"file://{file_path}", None)
                if part and isinstance(part.get("data"), (bytes, bytearray)):
                    image_bytes = bytes(part["data"])  # normalize to bytes
                    mime_type_from_loader = part.get("mime_type")
                    logger.info("[ReadFileTool] Loaded image via ImagenTool loader (%d bytes)", len(image_bytes))
            except Exception as e:
                logger.debug(f"[ReadFileTool] ImagenTool loader unavailable or failed: {e}")

            # Fallback: use filesystem service to read the image data
            if image_bytes is None:
                filesystem_service = None
                try:
                    from icpy.services.context_router import get_context_router as _get_cr
                    router = await _get_cr()
                    filesystem_service = await router.get_filesystem_for_namespace(ctx_id)
                except Exception:
                    filesystem_service = None
                if filesystem_service is None:
                    filesystem_service = await get_filesystem_service()

                try:
                    if hasattr(filesystem_service, 'read_file_binary'):
                        image_bytes = await filesystem_service.read_file_binary(file_path)
                    else:
                        content = await filesystem_service.read_file(file_path)
                        if isinstance(content, bytes):
                            image_bytes = content
                        else:
                            try:
                                image_bytes = base64.b64decode(content)
                            except Exception:
                                logger.error(f"Failed to read image file as binary: {file_path}")
                                return None
                except Exception as e:
                    logger.error(f"Failed to read image file: {file_path}: {e}")
                    return None

            if not image_bytes:
                return None

            # Convert to base64
            image_data = base64.b64encode(image_bytes).decode('utf-8')

            # Determine MIME type (prefer loader-provided type)
            ext = os.path.splitext(file_path.lower())[1]
            mime_map = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp',
                '.webp': 'image/webp',
                '.svg': 'image/svg+xml',
                '.ico': 'image/x-icon',
                '.tiff': 'image/tiff',
                '.tif': 'image/tiff',
            }
            mime_type = mime_type_from_loader or mime_map.get(ext, 'image/png')

            # Get filename
            filename = os.path.basename(file_path)

            # Create reference
            reference = await img_service.create_reference(
                image_data=image_data,
                filename=filename,
                prompt=f"Read from file: {filename}",
                model="file_read",
                mime_type=mime_type,
                only_thumbnail_if_missing=False,  # We have the data
                context_id=ctx_id if ctx_id != "local" else None,
                context_host=ctx_host
            )

            return reference.to_dict()

        except Exception as e:
            logger.error(f"Failed to create image reference for {file_path}: {e}", exc_info=True)
            return None
    
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
            
            # Parse potential namespaced path first (Phase 4)
            ctx_id, parsed_abs = await self._parse_path_parameter(file_path)

            # Determine workspace root using WorkspaceService when available (only for local)
            normalized_path = parsed_abs
            if ctx_id == "local":
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

                # Choose candidate: keep relative semantics for bare inputs, but never pass raw namespaced strings
                raw = str(file_path)
                has_namespace = (":/" in raw) and not (len(raw) >= 3 and raw[1:3] == ":/" and raw[0].isalpha())
                if has_namespace:
                    candidate = parsed_abs
                elif raw and not os.path.isabs(raw) and not raw.startswith('workspace'):
                    candidate = raw
                else:
                    candidate = parsed_abs
                # Validate and normalize local path within workspace
                normalized_path = self._validate_path(candidate, workspace_root)
                if normalized_path is None:
                    return ToolResult(
                        success=False,
                        error=f"Path is outside workspace root or invalid (namespace={ctx_id})"
                    )
            
            # Get filesystem service; prefer explicit namespace when available
            filesystem_service = None
            try:
                from icpy.services.context_router import get_context_router as _get_cr
                router = await _get_cr()
                filesystem_service = await router.get_filesystem_for_namespace(ctx_id)
            except Exception:
                filesystem_service = None
            if filesystem_service is None:
                filesystem_service = await get_filesystem_service()
            
            # Check if this is an image file
            is_image = self._is_image_file(normalized_path)
            
            if is_image:
                # For image files, create an ImageReference instead of reading as text
                logger.info(f"Detected image file: {normalized_path}, creating ImageReference")
                
                # Get context host if remote
                ctx_host = None
                if ctx_id != "local":
                    try:
                        from icpy.services.context_router import get_context_router as _get_cr
                        router = await _get_cr()
                        context = await router.get_context()
                        ctx_host = context.host if hasattr(context, 'host') else None
                    except Exception:
                        pass
                
                # Create image reference
                image_ref = await self._create_image_reference(normalized_path, ctx_id, ctx_host)
                
                if image_ref is None:
                    return ToolResult(
                        success=False,
                        error=f"Failed to create image reference for {normalized_path}. The file may be corrupted or unreadable."
                    )
                
                # Return image reference with metadata
                if kwargs.get("returnFullData", False):
                    # Format namespaced path explicitly using the ctx_id we already determined
                    from icpy.services.path_utils import format_namespaced_path
                    formatted_path = await format_namespaced_path(ctx_id, normalized_path)
                    
                    return ToolResult(
                        success=True,
                        data={
                            "isImage": True,
                            "imageReference": image_ref,
                            "filePath": formatted_path,
                            "absolutePath": normalized_path,
                            "contextId": ctx_id,
                            "message": f"Image file detected. Returning ImageReference to prevent token overflow. Use the imageReference to display or edit the image."
                        }
                    )
                else:
                    return ToolResult(
                        success=True,
                        data={
                            "isImage": True,
                            "imageReference": image_ref,
                            "message": f"Image file detected. Returning ImageReference to prevent token overflow."
                        }
                    )
            
            # Try to use read_file_range if available and line range is specified
            if (start_line is not None or end_line is not None) and hasattr(filesystem_service, 'read_file_range'):
                content = await filesystem_service.read_file_range(normalized_path, start_line, end_line)
            else:
                # Read entire file content
                # Optional pre-check for clearer error messaging when available
                try:
                    info = None
                    if hasattr(filesystem_service, 'get_file_info'):
                        info = await filesystem_service.get_file_info(normalized_path)
                except Exception:
                    info = None

                content = await filesystem_service.read_file(normalized_path)
                if content is None:
                    hint = ""
                    if ctx_id == "local":
                        hint = " The path may be outside WORKSPACE_ROOT or not exist. Try 'local:/<path-within-workspace>' or a relative path."
                    else:
                        hint = " The file may not exist on the remote host or the path is incorrect. Try prefixing with the correct namespace like 'hop1:/...'."
                    detail = " not found or unreadable" if info is None else " unreadable"
                    return ToolResult(success=False, error=f"Failed to read file: {normalized_path} ({detail})." + hint)
                
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
            
            # Return minimal data for test compatibility unless requested otherwise
            if kwargs.get("returnFullData", False):
                # Format namespaced path explicitly using the ctx_id we already determined
                from icpy.services.path_utils import format_namespaced_path
                formatted_path = await format_namespaced_path(ctx_id, normalized_path)
                
                return ToolResult(
                    success=True, 
                    data={
                        "content": content,
                        "filePath": formatted_path,
                        "absolutePath": normalized_path,
                        "contextId": ctx_id,
                        "startLine": start_line,
                        "endLine": end_line
                    }
                )
            else:
                # Minimal data for test compatibility
                return ToolResult(success=True, data={"content": content})
            
        except FileNotFoundError as e:
            return ToolResult(success=False, error=str(e))
        except PermissionError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error reading file {kwargs.get('filePath')}: {e}")
            return ToolResult(success=False, error=f"Failed to read file: {str(e)}") 