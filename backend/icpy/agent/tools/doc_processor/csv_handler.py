"""
CSV/TSV document handler

Supports reading and writing CSV and TSV files using built-in csv module.
"""

import csv
import io
import logging
from typing import Any, Dict, List, Optional, Union

from .base import (
    DocumentFormat,
    DocumentHandler,
    HandlerResult,
    register_handler,
)

logger = logging.getLogger(__name__)


class CSVHandler(DocumentHandler):
    """Handler for CSV/TSV files"""
    
    @property
    def supported_formats(self) -> List[DocumentFormat]:
        return [DocumentFormat.CSV, DocumentFormat.TSV]
    
    async def read_content(
        self,
        file_data: bytes,
        file_path: str,
        options: Optional[Dict[str, Any]] = None
    ) -> HandlerResult:
        """
        Extract content from CSV/TSV file.
        
        Options:
            max_rows: Maximum rows to read (default: 1000)
            encoding: File encoding (default: utf-8)
            delimiter: Custom delimiter (auto-detected if not provided)
            has_header: Whether first row is header (default: True)
        """
        options = options or {}
        max_rows = options.get("max_rows", 1000)
        encoding = options.get("encoding", "utf-8")
        has_header = options.get("has_header", True)
        
        try:
            # Decode bytes to string
            try:
                text_content = file_data.decode(encoding)
            except UnicodeDecodeError:
                # Try common encodings
                for enc in ["latin-1", "cp1252", "iso-8859-1"]:
                    try:
                        text_content = file_data.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    return HandlerResult(
                        success=False,
                        error="Could not decode file. Try specifying encoding."
                    )
            
            # Detect delimiter
            delimiter = options.get("delimiter")
            if not delimiter:
                # Check file extension first
                if file_path.lower().endswith(".tsv"):
                    delimiter = "\t"
                else:
                    delimiter = self._detect_delimiter(text_content)
            
            # Parse CSV
            reader = csv.reader(io.StringIO(text_content), delimiter=delimiter)
            rows = []
            
            for row_idx, row in enumerate(reader):
                if row_idx >= max_rows:
                    break
                rows.append(row)
            
            if not rows:
                return HandlerResult(
                    success=True,
                    content="(empty file)",
                    metadata={"delimiter": delimiter, "rows": 0},
                    tables=[]
                )
            
            # Extract headers and data
            if has_header and len(rows) > 0:
                headers = rows[0]
                headers = [h.strip() if h else f"col_{i}" for i, h in enumerate(headers)]
                data_rows = rows[1:]
            else:
                headers = [f"col_{i}" for i in range(len(rows[0]))]
                data_rows = rows
            
            # Build content string
            content_lines = [delimiter.join(headers)]
            content_lines.append("-" * 40)
            for row in data_rows:
                content_lines.append(delimiter.join(str(cell) for cell in row))
            
            # Build structured table data
            table_data = {
                "columns": headers,
                "row_count": len(data_rows),
                "data": [
                    dict(zip(headers, [str(cell).strip() for cell in row]))
                    for row in data_rows
                ]
            }
            
            # Count total rows in file
            total_rows = len(list(csv.reader(io.StringIO(text_content), delimiter=delimiter)))
            
            metadata = {
                "delimiter": delimiter,
                "encoding": encoding,
                "total_rows": total_rows,
                "columns": len(headers),
                "has_header": has_header
            }
            
            if total_rows > max_rows:
                content_lines.append(f"\n... (showing {max_rows} of {total_rows} rows)")
            
            return HandlerResult(
                success=True,
                content="\n".join(content_lines),
                metadata=metadata,
                tables=[table_data]
            )
            
        except Exception as e:
            logger.error(f"CSV read error: {e}")
            return HandlerResult(
                success=False,
                error=f"Failed to read CSV: {str(e)}"
            )
    
    def _detect_delimiter(self, text: str) -> str:
        """Detect delimiter from file content"""
        # Sample first few lines
        sample = text[:2000]
        
        # Count occurrences of common delimiters
        delimiters = {
            ",": sample.count(","),
            "\t": sample.count("\t"),
            ";": sample.count(";"),
            "|": sample.count("|"),
        }
        
        # Return most common delimiter (default to comma)
        best = max(delimiters, key=delimiters.get)
        return best if delimiters[best] > 0 else ","
    
    async def write_content(
        self,
        content: Union[str, Dict[str, Any], List[Dict[str, Any]]],
        file_path: str,
        options: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Create CSV/TSV from content.
        
        Content can be:
            - List of dicts: [{"col1": val1, "col2": val2}, ...]
            - Dict with "data" key: {"data": [...], "columns": [...]}
            - Plain text (written as-is)
        
        Options:
            delimiter: Field delimiter (default: "," for CSV, "\t" for TSV)
            include_header: Include header row (default: True)
            encoding: Output encoding (default: utf-8)
        """
        options = options or {}
        
        # Determine delimiter from file extension or options
        delimiter = options.get("delimiter")
        if not delimiter:
            delimiter = "\t" if file_path.lower().endswith(".tsv") else ","
        
        include_header = options.get("include_header", True)
        encoding = options.get("encoding", "utf-8")
        
        output = io.StringIO()
        
        if isinstance(content, str):
            # Write as-is
            output.write(content)
        
        elif isinstance(content, list):
            # List of dicts
            if content and isinstance(content[0], dict):
                headers = list(content[0].keys())
                writer = csv.DictWriter(output, fieldnames=headers, delimiter=delimiter)
                if include_header:
                    writer.writeheader()
                writer.writerows(content)
            elif content and isinstance(content[0], (list, tuple)):
                # List of lists
                writer = csv.writer(output, delimiter=delimiter)
                writer.writerows(content)
        
        elif isinstance(content, dict):
            data = content.get("data", [])
            headers = content.get("columns")
            
            if not headers and data:
                headers = list(data[0].keys()) if isinstance(data[0], dict) else None
            
            if headers and data:
                writer = csv.DictWriter(output, fieldnames=headers, delimiter=delimiter)
                if include_header:
                    writer.writeheader()
                for row in data:
                    if isinstance(row, dict):
                        writer.writerow(row)
                    else:
                        writer.writerow(dict(zip(headers, row)))
            elif data:
                writer = csv.writer(output, delimiter=delimiter)
                writer.writerows(data)
        
        return output.getvalue().encode(encoding)


# Register handler when module is imported
_handler = CSVHandler()
register_handler(_handler)
