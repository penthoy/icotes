"""
Base utilities for document processing

Provides format detection, handler interface, and shared utilities
for all document format handlers.
"""

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class DocumentFormat(Enum):
    """Supported document formats"""
    EXCEL_XLSX = "xlsx"
    EXCEL_XLS = "xls"
    EXCEL_XLSB = "xlsb"
    WORD_DOCX = "docx"
    PDF = "pdf"
    POWERPOINT = "pptx"
    CSV = "csv"
    TSV = "tsv"
    UNKNOWN = "unknown"


# File extension to format mapping
EXTENSION_MAP: Dict[str, DocumentFormat] = {
    ".xlsx": DocumentFormat.EXCEL_XLSX,
    ".xls": DocumentFormat.EXCEL_XLS,
    ".xlsb": DocumentFormat.EXCEL_XLSB,
    ".docx": DocumentFormat.WORD_DOCX,
    ".doc": DocumentFormat.WORD_DOCX,  # Try docx handler, may fail for old .doc
    ".pdf": DocumentFormat.PDF,
    ".pptx": DocumentFormat.POWERPOINT,
    ".ppt": DocumentFormat.POWERPOINT,  # Try pptx handler, may fail for old .ppt
    ".csv": DocumentFormat.CSV,
    ".tsv": DocumentFormat.TSV,
}


@dataclass
class HandlerResult:
    """Result from a document handler operation"""
    success: bool
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    
    # Format-specific fields
    sheets: Optional[List[str]] = None  # Excel sheet names
    pages: Optional[int] = None  # PDF/Word page count
    slides: Optional[int] = None  # PowerPoint slide count


def detect_format(file_path: str) -> DocumentFormat:
    """
    Detect document format from file extension.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        DocumentFormat enum value
    """
    ext = os.path.splitext(file_path.lower())[1]
    return EXTENSION_MAP.get(ext, DocumentFormat.UNKNOWN)


class DocumentHandler(ABC):
    """
    Abstract base class for document format handlers.
    
    Each handler must implement read_content() and optionally write_content().
    """
    
    @property
    @abstractmethod
    def supported_formats(self) -> List[DocumentFormat]:
        """List of formats this handler supports"""
        pass
    
    @abstractmethod
    async def read_content(
        self,
        file_data: bytes,
        file_path: str,
        options: Optional[Dict[str, Any]] = None
    ) -> HandlerResult:
        """
        Extract content from document.
        
        Args:
            file_data: Raw file bytes
            file_path: Original file path (for extension detection)
            options: Format-specific options
            
        Returns:
            HandlerResult with extracted content and metadata
        """
        pass
    
    async def write_content(
        self,
        content: Union[str, Dict[str, Any]],
        file_path: str,
        options: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Create document from content.
        
        Args:
            content: Text or structured data to write
            file_path: Target file path (for format detection)
            options: Format-specific options
            
        Returns:
            Raw bytes of the created document
            
        Raises:
            NotImplementedError: If handler doesn't support writing
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support document creation"
        )


# Handler registry - populated by individual handler modules
_handler_registry: Dict[DocumentFormat, DocumentHandler] = {}


def register_handler(handler: DocumentHandler) -> None:
    """Register a handler for its supported formats"""
    for fmt in handler.supported_formats:
        _handler_registry[fmt] = handler
        logger.debug(f"Registered {handler.__class__.__name__} for {fmt.value}")


def get_handler_for_format(fmt: DocumentFormat) -> Optional[DocumentHandler]:
    """
    Get the handler for a specific format.
    
    Args:
        fmt: DocumentFormat to get handler for
        
    Returns:
        Handler instance or None if not available
    """
    return _handler_registry.get(fmt)


def get_all_supported_formats() -> List[str]:
    """Get list of all supported file extensions"""
    return list(EXTENSION_MAP.keys())
