"""
Document Processor Package

Provides handlers for reading and writing various document formats:
- Excel (.xlsx, .xls, .xlsb)
- Word (.docx)
- PDF
- PowerPoint (.pptx)
- CSV/TSV

Each handler follows a consistent interface for format detection,
text extraction, and document creation.
"""

from .base import (
    detect_format,
    get_handler_for_format,
    get_all_supported_formats,
    DocumentFormat,
    DocumentHandler,
    HandlerResult,
)
from .excel_handler import ExcelHandler
from .word_handler import WordHandler
from .pdf_handler import PDFHandler
from .pptx_handler import PPTXHandler
from .csv_handler import CSVHandler

__all__ = [
    # Base utilities
    "detect_format",
    "get_handler_for_format",
    "get_all_supported_formats",
    "DocumentFormat",
    "DocumentHandler",
    "HandlerResult",
    # Format handlers
    "ExcelHandler",
    "WordHandler",
    "PDFHandler",
    "PPTXHandler",
    "CSVHandler",
]
