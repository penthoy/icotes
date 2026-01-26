"""
Write Document Tool for agents

Creates document files from structured content:
- Excel (.xlsx)
- Word (.docx)
- PDF (requires reportlab)
- PowerPoint (.pptx)
- CSV/TSV

Follows existing tool patterns with namespaced path support.
"""

import os
import logging
from typing import Any, Dict, Optional, Union

from .base_tool import BaseTool, ToolResult
from .context_helpers import get_contextual_filesystem

logger = logging.getLogger(__name__)


# Lazy import handlers
def _get_handlers():
    """Lazy load document handlers"""
    from .doc_processor import (
        detect_format,
        get_handler_for_format,
        DocumentFormat,
        get_all_supported_formats,
    )
    return detect_format, get_handler_for_format, DocumentFormat, get_all_supported_formats


async def get_filesystem_service():
    """Get filesystem service for the active context"""
    return await get_contextual_filesystem()


async def get_workspace_service():
    """Get workspace service for path resolution"""
    try:
        from icpy.services import get_workspace_service as _get_workspace_service
        return await _get_workspace_service()
    except ImportError:
        return None


class WriteDocTool(BaseTool):
    """
    Tool for creating document files from structured content.
    
    Supports Excel, Word, PDF, PowerPoint, and CSV formats.
    Auto-detects format from file extension.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "write_doc"
        self.description = (
            "Create document files from content. "
            "Supports Excel (.xlsx), Word (.docx), PDF, PowerPoint (.pptx), and CSV/TSV. "
            "Content can be plain text or structured data (JSON). "
            "Accepts namespaced paths like 'local:/path' or 'hop1:/path'."
        )
        logger.debug(f"[WriteDocTool] Initializing tool with schema validation")
        self.parameters = {
            "type": "object",
            "properties": {
                "filePath": {
                    "type": "string",
                    "description": (
                        "Path for the output document. Format is detected from extension. "
                        "Accepts optional namespace prefix (e.g., local:/output.xlsx)."
                    )
                },
                "content": {
                    "description": (
                        "Content to write. Can be:\n"
                        "- Plain text string (for Word/PDF)\n"
                        "- Array of objects (for Excel/CSV): [{\"name\": \"Alice\", \"score\": 95}, ...]\n"
                        "- Structured object with format-specific keys\n\n"
                        "Word example: \"# Title\\n\\nParagraph text\"\n"
                        "PowerPoint: {\"slides\": [{\"title\": \"...\", \"content\": [...]}]}"
                    ),
                    "anyOf": [
                        {"type": "string"},
                        {"type": "object"},
                        {
                            "type": "array",
                            "items": {
                                "type": "object"
                            }
                        }
                    ]
                },
                "options": {
                    "type": "object",
                    "description": (
                        "Format-specific options:\n"
                        "- sheet_name: Excel sheet name\n"
                        "- title/author: Document metadata\n"
                        "- delimiter: CSV field separator\n"
                    ),
                    "properties": {
                        "sheet_name": {"type": "string", "description": "Excel sheet name"},
                        "title": {"type": "string", "description": "Document title"},
                        "author": {"type": "string", "description": "Document author"},
                        "delimiter": {"type": "string", "description": "CSV delimiter"},
                    }
                },
                "createDirectories": {
                    "type": "boolean",
                    "description": "Create parent directories if they don't exist (default: true)"
                },
                "returnFullData": {
                    "type": "boolean",
                    "description": (
                        "If true, includes namespaced filePath, absolutePath, and pathInfo "
                        "in the response. Default false."
                    )
                }
            },
            "required": ["filePath", "content"]
        }
        logger.debug(f"[WriteDocTool] Schema registered: {self.parameters}")
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute document write operation.
        
        Args:
            filePath: Path for output document
            content: Content to write (text, list, or dict)
            options: Format-specific options
            createDirectories: Create parent dirs if needed
            returnFullData: Include path metadata in response
            
        Returns:
            ToolResult with success status and file info
        """
        file_path = kwargs.get("filePath", "")
        content = kwargs.get("content")
        options = kwargs.get("options", {})
        create_directories = kwargs.get("createDirectories", True)
        return_full_data = kwargs.get("returnFullData", False)
        
        if not file_path:
            return ToolResult(
                success=False,
                error="filePath is required"
            )
        
        if content is None:
            return ToolResult(
                success=False,
                error="content is required"
            )
        
        try:
            # Parse namespaced path
            ctx_id, abs_path = await self._parse_path_parameter(file_path)
            logger.info(f"[WriteDocTool] Writing document: {abs_path} (context: {ctx_id})")
            
            # Resolve path against workspace if relative
            if not os.path.isabs(abs_path):
                workspace_service = await get_workspace_service()
                if workspace_service:
                    workspace_root = await workspace_service.get_workspace_root()
                    abs_path = os.path.join(workspace_root, abs_path)
            
            # Detect format
            detect_format, get_handler_for_format, DocumentFormat, get_all_supported_formats = _get_handlers()
            doc_format = detect_format(abs_path)
            
            if doc_format == DocumentFormat.UNKNOWN:
                supported = ", ".join(get_all_supported_formats())
                return ToolResult(
                    success=False,
                    error=f"Unsupported file format. Supported formats: {supported}"
                )
            
            # Get handler
            handler = get_handler_for_format(doc_format)
            if not handler:
                return ToolResult(
                    success=False,
                    error=f"No handler available for {doc_format.value} format"
                )
            
            # Create directories if needed
            if create_directories:
                await self._ensure_directories(abs_path, ctx_id)
            
            # Generate document content
            try:
                file_bytes = await handler.write_content(content, abs_path, options)
            except NotImplementedError as e:
                return ToolResult(
                    success=False,
                    error=f"Write not supported for {doc_format.value}: {str(e)}"
                )
            
            if not file_bytes:
                return ToolResult(
                    success=False,
                    error="Failed to generate document content"
                )
            
            # Write file
            success = await self._write_file_bytes(abs_path, file_bytes, ctx_id)
            
            if not success:
                return ToolResult(
                    success=False,
                    error=f"Failed to write file: {abs_path}"
                )
            
            # Build response
            response_data = {
                "format": doc_format.value,
                "size": len(file_bytes),
                "message": f"Successfully created {doc_format.value.upper()} document"
            }
            
            # Add path info if requested
            if return_full_data:
                path_info = await self._format_path_info(abs_path)
                response_data["filePath"] = path_info.get("formatted_path", abs_path)
                response_data["absolutePath"] = abs_path
                response_data["pathInfo"] = path_info
            
            return ToolResult(
                success=True,
                data=response_data
            )
            
        except ImportError as e:
            return ToolResult(
                success=False,
                error=f"Missing dependency: {str(e)}. Install required packages."
            )
        except Exception as e:
            logger.error(f"[WriteDocTool] Error writing document: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Failed to write document: {str(e)}"
            )
    
    async def _ensure_directories(self, file_path: str, ctx_id: str) -> bool:
        """Ensure parent directories exist"""
        try:
            dir_path = os.path.dirname(file_path)
            if not dir_path:
                return True
            
            filesystem_service = None
            try:
                from icpy.services.context_router import get_context_router as _get_cr
                router = await _get_cr()
                filesystem_service = await router.get_filesystem_for_namespace(ctx_id)
            except Exception:
                pass
            
            if filesystem_service is None:
                filesystem_service = await get_filesystem_service()
            
            if hasattr(filesystem_service, 'create_directory'):
                await filesystem_service.create_directory(dir_path)
            elif hasattr(filesystem_service, 'ensure_directory'):
                await filesystem_service.ensure_directory(dir_path)
            else:
                # Fallback to os.makedirs for local
                os.makedirs(dir_path, exist_ok=True)
            
            return True
            
        except Exception as e:
            logger.warning(f"[WriteDocTool] Could not create directories: {e}")
            return False
    
    async def _write_file_bytes(self, file_path: str, data: bytes, ctx_id: str) -> bool:
        """
        Write bytes to file.
        
        Handles both local and hop contexts.
        """
        try:
            filesystem_service = None
            
            try:
                from icpy.services.context_router import get_context_router as _get_cr
                router = await _get_cr()
                filesystem_service = await router.get_filesystem_for_namespace(ctx_id)
            except Exception:
                pass
            
            if filesystem_service is None:
                filesystem_service = await get_filesystem_service()
            
            # Try binary write first
            if hasattr(filesystem_service, 'write_file_binary'):
                await filesystem_service.write_file_binary(file_path, data)
                return True
            
            # Try regular write_file with content
            if hasattr(filesystem_service, 'write_file'):
                await filesystem_service.write_file(file_path, data)
                return True
            
            # Fallback to direct file write for local
            with open(file_path, 'wb') as f:
                f.write(data)
            return True
            
        except Exception as e:
            logger.error(f"[WriteDocTool] Failed to write file: {e}")
            return False
