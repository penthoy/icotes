"""
Log rotation utility for frontend logs.
Provides rotating file handler functionality for custom log files.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional


class FrontendLogRotator:
    """
    Manages log rotation for frontend logs with the same policy as backend logs.
    Uses Python's RotatingFileHandler for consistency.
    """
    
    def __init__(self, log_file_path: str, max_bytes: int = 10485760, backup_count: int = 5):
        """
        Initialize the log rotator.
        
        Args:
            log_file_path: Path to the log file
            max_bytes: Maximum size in bytes before rotation (default: 10MB)
            backup_count: Number of backup files to keep (default: 5)
        """
        self.log_file_path = log_file_path
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._handler: Optional[RotatingFileHandler] = None
        self._setup_handler()
    
    def _setup_handler(self):
        """Setup the rotating file handler."""
        # Ensure directory exists
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
        
        # Create rotating file handler
        self._handler = RotatingFileHandler(
            self.log_file_path,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
    
    def write_log(self, log_line: str):
        """
        Write a log line with automatic rotation.
        
        Args:
            log_line: The log line to write (should include newline)
        """
        if not self._handler:
            self._setup_handler()
        
        # Check if rotation is needed
        if self._handler.shouldRollover(self._make_record(log_line)):
            self._handler.doRollover()
        
        # Write to file
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(log_line)
    
    def _make_record(self, message: str) -> logging.LogRecord:
        """
        Create a dummy LogRecord for rotation checking.
        
        Args:
            message: The log message
            
        Returns:
            A LogRecord instance
        """
        return logging.LogRecord(
            name='frontend',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg=message,
            args=(),
            exc_info=None
        )
    
    def close(self):
        """Close the handler."""
        if self._handler:
            self._handler.close()
            self._handler = None
