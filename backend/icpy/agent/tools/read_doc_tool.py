"""
Read Document Tool for agents

Extracts text and structured data from common document formats:
- Excel (.xlsx, .xls, .xlsb)
- Word (.docx)
- PDF
- PowerPoint (.pptx)
- CSV/TSV

Follows existing tool patterns with namespaced path support.
"""

import os
import logging
from typing import Any, Dict, Optional

from .base_tool import BaseTool, ToolResult
from .context_helpers import get_contextual_filesystem

logger = logging.getLogger(__name__)


# Lazy import handlers to avoid loading heavy dependencies at startup
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


class ReadDocTool(BaseTool):
    """
    Tool for reading document contents and extracting text/data.
    
    Supports Excel, Word, PDF, PowerPoint, and CSV formats.
    Auto-detects format from file extension.
    Includes smart truncation to prevent LLM context overflow.
    """
    
    # Default limits to prevent LLM context overflow
    # ~2K tokens ≈ 8K chars (1 token ≈ 4 chars)
    # Being conservative to leave room for agent reasoning
    DEFAULT_MAX_CHARS = 8000
    DEFAULT_MAX_LINES = 500
    DEFAULT_MAX_TABLE_ROWS = 50  # Limit table rows to prevent overflow
    
    def __init__(self):
        super().__init__()
        self.name = "read_doc"
        self.description = (
            "Read and extract text/data from document files. "
            "Supports Excel (.xlsx, .xls), Word (.docx), PDF, PowerPoint (.pptx), and CSV/TSV. "
            "Returns extracted text content, metadata, and structured table data when available. "
            "Accepts namespaced paths like 'local:/path' or 'hop1:/path'. "
            "Large documents are auto-truncated; use start_line/end_line or start_page/end_page for pagination."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "filePath": {
                    "type": "string",
                    "description": (
                        "Path to the document file. Accepts optional namespace prefix "
                        "(e.g., local:/file.xlsx, hop1:/docs/report.pdf)."
                    )
                },
                "options": {
                    "type": "object",
                    "description": (
                        "Format-specific and pagination options:\n"
                        "- max_chars: Max characters to return (default: 20000, ~5K tokens)\n"
                        "- max_lines: Max lines to return (default: 1000)\n"
                        "- start_line/end_line: Extract specific line range\n"
                        "- start_page/end_page: Extract specific page range (PDF/Word/PPT)\n"
                        "- summary_only: Return metadata + first/last sections only\n"
                        "- max_rows/max_pages: Limit content extraction\n"
                        "- sheet_name: Specific Excel sheet to read\n"
                        "- extract_tables: Include structured table data (default: true)\n"
                        "- include_notes: Include speaker notes for PowerPoint\n"
                    ),
                    "properties": {
                        "max_chars": {"type": "integer", "description": "Max characters to return"},
                        "max_lines": {"type": "integer", "description": "Max lines to return"},
                        "start_line": {"type": "integer", "description": "Start line for range (1-indexed)"},
                        "end_line": {"type": "integer", "description": "End line for range (1-indexed)"},
                        "start_page": {"type": "integer", "description": "Start page for range (1-indexed)"},
                        "end_page": {"type": "integer", "description": "End page for range (1-indexed)"},
                        "summary_only": {"type": "boolean", "description": "Return summary instead of full content"},
                        "max_rows": {"type": "integer", "description": "Max rows for Excel/CSV"},
                        "max_pages": {"type": "integer", "description": "Max pages for PDF/Word"},
                        "sheet_name": {"type": "string", "description": "Specific Excel sheet"},
                        "extract_tables": {"type": "boolean", "description": "Extract tables"},
                        "include_notes": {"type": "boolean", "description": "Include PowerPoint notes"},
                    }
                },
                "returnFullData": {
                    "type": "boolean",
                    "description": (
                        "If true, includes namespaced filePath, absolutePath, and pathInfo "
                        "in the response. Default false."
                    )
                }
            },
            "required": ["filePath"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute document read operation.
        
        Args:
            filePath: Path to document file
            options: Format-specific options
            returnFullData: Include path metadata in response
            
        Returns:
            ToolResult with extracted content, metadata, and tables
        """
        file_path = kwargs.get("filePath", "")
        options = kwargs.get("options", {})
        return_full_data = kwargs.get("returnFullData", False)
        
        if not file_path:
            return ToolResult(
                success=False,
                error="filePath is required"
            )
        
        try:
            # Parse namespaced path
            ctx_id, abs_path = await self._parse_path_parameter(file_path)
            logger.info(f"[ReadDocTool] Reading document: {abs_path} (context: {ctx_id})")
            
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
            
            # Read file content
            file_data = await self._read_file_bytes(abs_path, ctx_id)
            if file_data is None:
                return ToolResult(
                    success=False,
                    error=f"Failed to read file: {abs_path}"
                )
            
            # Extract content
            result = await handler.read_content(file_data, abs_path, options)
            
            if not result.success:
                return ToolResult(
                    success=False,
                    error=result.error or "Failed to extract document content"
                )
            
            # Apply content truncation to prevent LLM context overflow
            content = result.content
            truncation_info = None
            
            # Get truncation options
            max_chars = options.get("max_chars", self.DEFAULT_MAX_CHARS)
            max_lines = options.get("max_lines", self.DEFAULT_MAX_LINES)
            start_line = options.get("start_line")
            end_line = options.get("end_line")
            summary_only = options.get("summary_only", False)
            
            # Apply truncation
            content, truncation_info = self._apply_truncation(
                content=content,
                max_chars=max_chars,
                max_lines=max_lines,
                start_line=start_line,
                end_line=end_line,
                summary_only=summary_only
            )
            
            # Build response data
            response_data = {
                "format": doc_format.value,
                "content": content,
                "metadata": result.metadata,
            }
            
            # Add truncation info if content was truncated
            if truncation_info:
                response_data["truncated"] = truncation_info.get("truncated", False)
                response_data["truncation_info"] = truncation_info
            
            # Add format-specific fields (with truncation for tables)
            if result.tables:
                max_table_rows = options.get("max_table_rows", self.DEFAULT_MAX_TABLE_ROWS)
                response_data["tables"] = self._truncate_tables(result.tables, max_table_rows)
            if result.sheets:
                response_data["sheets"] = result.sheets
            if result.pages:
                response_data["pages"] = result.pages
            if result.slides:
                response_data["slides"] = result.slides
            
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
            logger.error(f"[ReadDocTool] Error reading document: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Failed to read document: {str(e)}"
            )
    
    async def _read_file_bytes(self, file_path: str, ctx_id: str) -> Optional[bytes]:
        """
        Read file as bytes from filesystem.
        
        Handles both local and hop contexts.
        """
        try:
            # Get filesystem for the context
            filesystem_service = None
            
            try:
                from icpy.services.context_router import get_context_router as _get_cr
                router = await _get_cr()
                filesystem_service = await router.get_filesystem_for_namespace(ctx_id)
            except Exception:
                pass
            
            if filesystem_service is None:
                filesystem_service = await get_filesystem_service()
            
            # Try binary read first
            if hasattr(filesystem_service, 'read_file_binary'):
                return await filesystem_service.read_file_binary(file_path)
            
            # Fallback to regular read
            content = await filesystem_service.read_file(file_path)
            if isinstance(content, bytes):
                return content
            
            # If string, try to encode (shouldn't happen for binary files)
            return content.encode('utf-8') if content else None
            
        except Exception as e:
            logger.error(f"[ReadDocTool] Failed to read file bytes: {e}")
            return None

    def _apply_truncation(
        self,
        content: str,
        max_chars: int,
        max_lines: int,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        summary_only: bool = False
    ) -> tuple:
        """
        Apply content truncation to prevent LLM context overflow.
        
        Args:
            content: Full document content
            max_chars: Maximum characters to return
            max_lines: Maximum lines to return
            start_line: Start line for range extraction (1-indexed)
            end_line: End line for range extraction (1-indexed)
            summary_only: Return only metadata + first/last preview
            
        Returns:
            Tuple of (truncated_content, truncation_info)
        """
        if not content:
            return content, None
        
        original_chars = len(content)
        lines = content.split('\n')
        original_lines = len(lines)
        
        # Check if truncation is needed
        needs_truncation = original_chars > max_chars or original_lines > max_lines
        
        truncation_info = {
            "truncated": False,
            "total_chars": original_chars,
            "total_lines": original_lines,
            "returned_chars": original_chars,
            "returned_lines": original_lines,
        }
        
        # Summary mode: return first/last sections only
        if summary_only:
            preview_chars = 500
            first_preview = content[:preview_chars]
            last_preview = content[-preview_chars:] if original_chars > preview_chars * 2 else ""
            
            summary_content = f"=== DOCUMENT SUMMARY ===\n"
            summary_content += f"Total characters: {original_chars:,}\n"
            summary_content += f"Total lines: {original_lines:,}\n"
            summary_content += f"Estimated tokens: ~{original_chars // 4:,}\n\n"
            summary_content += f"=== FIRST {preview_chars} CHARS ===\n{first_preview}\n"
            if last_preview:
                summary_content += f"\n...\n\n=== LAST {preview_chars} CHARS ===\n{last_preview}"
            
            truncation_info.update({
                "truncated": True,
                "returned_chars": len(summary_content),
                "returned_lines": summary_content.count('\n') + 1,
                "mode": "summary",
            })
            return summary_content, truncation_info
        
        # Line range extraction (like head/tail)
        if start_line is not None or end_line is not None:
            # Convert to 0-indexed
            start_idx = (start_line - 1) if start_line else 0
            end_idx = end_line if end_line else len(lines)
            
            # Clamp to valid range
            start_idx = max(0, min(start_idx, len(lines)))
            end_idx = max(start_idx, min(end_idx, len(lines)))
            
            selected_lines = lines[start_idx:end_idx]
            result_content = '\n'.join(selected_lines)
            
            truncation_info.update({
                "truncated": start_idx > 0 or end_idx < len(lines),
                "returned_chars": len(result_content),
                "returned_lines": len(selected_lines),
                "start_line": start_idx + 1,
                "end_line": end_idx,
                "has_more": end_idx < len(lines),
            })
            
            if end_idx < len(lines):
                truncation_info["suggested_next"] = {
                    "start_line": end_idx + 1,
                    "end_line": min(end_idx + max_lines, len(lines))
                }
            
            return result_content, truncation_info
        
        # Auto-truncation based on limits
        if not needs_truncation:
            return content, None
        
        # Apply line limit first (more predictable)
        if original_lines > max_lines:
            lines = lines[:max_lines]
            content = '\n'.join(lines)
        
        # Then apply character limit
        if len(content) > max_chars:
            content = content[:max_chars]
            # Try to break at last newline for cleaner output
            last_newline = content.rfind('\n')
            if last_newline > max_chars * 0.8:  # Only if we don't lose too much
                content = content[:last_newline]
        
        returned_lines = content.count('\n') + 1
        returned_chars = len(content)
        
        # Add truncation notice
        content += f"\n\n... [TRUNCATED: Showing {returned_chars:,} of {original_chars:,} chars, " \
                   f"{returned_lines:,} of {original_lines:,} lines] ..."
        content += f"\n\nTo read more, use options: {{\"start_line\": {returned_lines + 1}, \"end_line\": {min(returned_lines + max_lines, original_lines)}}}"
        
        truncation_info.update({
            "truncated": True,
            "returned_chars": len(content),
            "returned_lines": returned_lines,
            "start_line": 1,
            "end_line": returned_lines,
            "has_more": True,
            "suggested_next": {
                "start_line": returned_lines + 1,
                "end_line": min(returned_lines + max_lines, original_lines)
            }
        })
        
        return content, truncation_info

    def _truncate_tables(
        self,
        tables: list,
        max_rows: int
    ) -> list:
        """
        Truncate table data to prevent LLM context overflow.
        
        Args:
            tables: List of table dictionaries with 'data' key
            max_rows: Maximum rows per table
            
        Returns:
            Truncated tables list
        """
        if not tables:
            return tables
        
        truncated_tables = []
        for table in tables:
            if not isinstance(table, dict):
                continue
                
            truncated_table = table.copy()
            
            # Truncate data rows
            if "data" in table and isinstance(table["data"], list):
                original_rows = len(table["data"])
                if original_rows > max_rows:
                    truncated_table["data"] = table["data"][:max_rows]
                    truncated_table["truncated"] = True
                    truncated_table["total_rows"] = original_rows
                    truncated_table["shown_rows"] = max_rows
            
            truncated_tables.append(truncated_table)
        
        # Limit number of tables returned
        max_tables = 5
        if len(truncated_tables) > max_tables:
            truncated_tables = truncated_tables[:max_tables]
            truncated_tables.append({
                "note": f"... and {len(tables) - max_tables} more tables (use specific sheet/page options)"
            })
        
        return truncated_tables