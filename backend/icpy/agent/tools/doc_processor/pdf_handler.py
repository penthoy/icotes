"""
PDF document handler

Supports reading PDF files and extracting text content.
Uses pdfplumber for accurate text extraction.
"""

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


class PDFHandler(DocumentHandler):
    """Handler for PDF documents"""
    
    @property
    def supported_formats(self) -> List[DocumentFormat]:
        return [DocumentFormat.PDF]
    
    async def read_content(
        self,
        file_data: bytes,
        file_path: str,
        options: Optional[Dict[str, Any]] = None
    ) -> HandlerResult:
        """
        Extract content from PDF file.
        
        Options:
            max_pages: Maximum pages to read (default: 50)
            extract_tables: Try to extract tables (default: True)
            include_page_numbers: Add page markers (default: True)
        """
        options = options or {}
        max_pages = options.get("max_pages", 50)
        extract_tables = options.get("extract_tables", True)
        include_page_numbers = options.get("include_page_numbers", True)
        
        # Try pdfplumber first (better accuracy)
        try:
            return await self._read_with_pdfplumber(
                file_data, max_pages, extract_tables, include_page_numbers
            )
        except ImportError:
            logger.warning("pdfplumber not available, trying pypdf")
        
        # Fallback to pypdf
        try:
            return await self._read_with_pypdf(
                file_data, max_pages, include_page_numbers
            )
        except ImportError:
            return HandlerResult(
                success=False,
                error="No PDF library available. Install with: pip install pdfplumber"
            )
        except Exception as e:
            return HandlerResult(
                success=False,
                error=f"Failed to read PDF: {str(e)}"
            )
    
    async def _read_with_pdfplumber(
        self,
        file_data: bytes,
        max_pages: int,
        extract_tables: bool,
        include_page_numbers: bool
    ) -> HandlerResult:
        """Read PDF using pdfplumber for better accuracy"""
        import pdfplumber
        
        pdf_file = io.BytesIO(file_data)
        content_parts = []
        tables = []
        
        with pdfplumber.open(pdf_file) as pdf:
            total_pages = len(pdf.pages)
            pages_to_read = min(total_pages, max_pages)
            
            for page_num in range(pages_to_read):
                page = pdf.pages[page_num]
                
                if include_page_numbers:
                    content_parts.append(f"\n--- Page {page_num + 1} ---\n")
                
                # Extract text
                text = page.extract_text()
                if text:
                    content_parts.append(text)
                
                # Extract tables if requested
                if extract_tables:
                    page_tables = page.extract_tables()
                    for table_idx, table in enumerate(page_tables):
                        if table and len(table) > 0:
                            table_data = self._process_table(table, page_num, table_idx)
                            if table_data:
                                tables.append(table_data)
            
            # Add truncation notice
            if total_pages > max_pages:
                content_parts.append(
                    f"\n... (showing {max_pages} of {total_pages} pages)"
                )
            
            # Extract metadata
            metadata = self._extract_metadata_pdfplumber(pdf)
            metadata["total_pages"] = total_pages
            
            return HandlerResult(
                success=True,
                content="\n".join(content_parts),
                metadata=metadata,
                tables=tables,
                pages=total_pages
            )
    
    def _process_table(
        self, table: List[List], page_num: int, table_idx: int
    ) -> Optional[Dict[str, Any]]:
        """Process extracted table into structured format"""
        if not table or len(table) < 2:
            return None
        
        # Clean up None values
        cleaned = [
            [str(cell).strip() if cell else "" for cell in row]
            for row in table
        ]
        
        # First row as headers
        headers = cleaned[0]
        headers = [h if h else f"col_{i}" for i, h in enumerate(headers)]
        
        # Remaining rows as data
        data = [
            dict(zip(headers, row))
            for row in cleaned[1:]
        ]
        
        return {
            "page": page_num + 1,
            "table_index": table_idx,
            "columns": headers,
            "row_count": len(data),
            "data": data
        }
    
    def _extract_metadata_pdfplumber(self, pdf) -> Dict[str, Any]:
        """Extract PDF metadata using pdfplumber"""
        metadata = {}
        
        try:
            if pdf.metadata:
                metadata = {
                    "title": pdf.metadata.get("Title", ""),
                    "author": pdf.metadata.get("Author", ""),
                    "subject": pdf.metadata.get("Subject", ""),
                    "creator": pdf.metadata.get("Creator", ""),
                    "producer": pdf.metadata.get("Producer", ""),
                    "created": pdf.metadata.get("CreationDate", ""),
                    "modified": pdf.metadata.get("ModDate", ""),
                }
        except Exception as e:
            logger.debug(f"Metadata extraction error: {e}")
        
        return metadata
    
    async def _read_with_pypdf(
        self,
        file_data: bytes,
        max_pages: int,
        include_page_numbers: bool
    ) -> HandlerResult:
        """Fallback: read PDF using pypdf"""
        try:
            from pypdf import PdfReader
        except ImportError:
            # Try older PyPDF2
            from PyPDF2 import PdfReader
        
        pdf_file = io.BytesIO(file_data)
        reader = PdfReader(pdf_file)
        
        total_pages = len(reader.pages)
        pages_to_read = min(total_pages, max_pages)
        
        content_parts = []
        
        for page_num in range(pages_to_read):
            page = reader.pages[page_num]
            
            if include_page_numbers:
                content_parts.append(f"\n--- Page {page_num + 1} ---\n")
            
            text = page.extract_text()
            if text:
                content_parts.append(text)
        
        if total_pages > max_pages:
            content_parts.append(
                f"\n... (showing {max_pages} of {total_pages} pages)"
            )
        
        # Extract metadata
        metadata = {}
        if reader.metadata:
            metadata = {
                "title": reader.metadata.get("/Title", ""),
                "author": reader.metadata.get("/Author", ""),
                "subject": reader.metadata.get("/Subject", ""),
                "creator": reader.metadata.get("/Creator", ""),
            }
        metadata["total_pages"] = total_pages
        
        return HandlerResult(
            success=True,
            content="\n".join(content_parts),
            metadata=metadata,
            tables=[],  # pypdf doesn't extract tables
            pages=total_pages
        )
    
    async def write_content(
        self,
        content: Union[str, Dict[str, Any]],
        file_path: str,
        options: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Create PDF from content (requires reportlab).
        
        Options:
            title: Document title
            author: Document author
            font_size: Base font size (default: 12)
            margins: Page margins in points (default: 72)
        """
        options = options or {}
        
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.units import inch
        except ImportError:
            raise ImportError(
                "reportlab required for PDF creation. "
                "Install with: pip install reportlab"
            )
        
        output = io.BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=letter,
            topMargin=options.get("margins", 72),
            bottomMargin=options.get("margins", 72),
            leftMargin=options.get("margins", 72),
            rightMargin=options.get("margins", 72),
        )
        
        # Set up styles
        styles = getSampleStyleSheet()
        normal_style = styles['Normal']
        normal_style.fontSize = options.get("font_size", 12)
        normal_style.leading = normal_style.fontSize * 1.2
        
        heading_style = styles['Heading1']
        
        story = []
        
        # Add title if provided
        if options.get("title"):
            story.append(Paragraph(options["title"], heading_style))
            story.append(Spacer(1, 0.25 * inch))
        
        # Process content
        if isinstance(content, str):
            paragraphs = content.split("\n\n")
            for para in paragraphs:
                if para.strip():
                    # Handle markdown-style headings
                    if para.startswith("# "):
                        story.append(Paragraph(para[2:], styles['Heading1']))
                    elif para.startswith("## "):
                        story.append(Paragraph(para[3:], styles['Heading2']))
                    elif para.startswith("### "):
                        story.append(Paragraph(para[4:], styles['Heading3']))
                    else:
                        # Escape special characters for reportlab
                        safe_text = para.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        story.append(Paragraph(safe_text, normal_style))
                    story.append(Spacer(1, 0.1 * inch))
        
        elif isinstance(content, dict):
            for item in content.get("paragraphs", []):
                if isinstance(item, str):
                    safe_text = item.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    story.append(Paragraph(safe_text, normal_style))
                story.append(Spacer(1, 0.1 * inch))
        
        doc.build(story)
        output.seek(0)
        return output.read()


# Register handler when module is imported
_handler = PDFHandler()
register_handler(_handler)
