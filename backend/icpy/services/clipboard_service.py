"""
Enhanced Clipboard Service with Multi-Layer Strategy

This service implements a robust clipboard system that bypasses browser security limitations
by providing multiple fallback layers, similar to code-server's approach.

Fallback Hierarchy:
1. Browser native Clipboard API (when available in secure context)
2. Server-side clipboard bridge with system integration  
3. CLI-based clipboard commands (xclip, pbcopy, etc.)
4. File-based clipboard fallback

Author: ICPY Development Team
"""

import asyncio
import os
import platform
import subprocess
import tempfile
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class ClipboardService:
    """
    Enhanced clipboard service with multi-layer fallback strategy.
    
    Provides robust clipboard operations that work across different environments
    and security contexts, with automatic fallback to ensure functionality.
    """
    
    def __init__(self):
        """Initialize the clipboard service with system detection."""
        self.system = platform.system().lower()
        self.fallback_file = Path(tempfile.gettempdir()) / "icpy_clipboard.txt"
        self.history: List[Dict[str, Any]] = []
        self.max_history = 50
        
        # Detect available clipboard commands
        self.cli_commands = self._detect_cli_commands()
        
        logger.info(f"ClipboardService initialized for {self.system}")
        logger.info(f"Available CLI commands: {self.cli_commands}")
    
    def _detect_cli_commands(self) -> Dict[str, Dict[str, str]]:
        """
        Detect available clipboard CLI commands for the current system.
        
        Returns:
            Dict mapping operation types to command configurations
        """
        commands = {}
        
        if self.system == "linux":
            # Check for xclip
            if self._command_exists("xclip"):
                commands["xclip"] = {
                    "read": ["xclip", "-selection", "clipboard", "-o"],
                    "write": ["xclip", "-selection", "clipboard"]
                }
            # Check for xsel
            elif self._command_exists("xsel"):
                commands["xsel"] = {
                    "read": ["xsel", "--clipboard", "--output"],
                    "write": ["xsel", "--clipboard", "--input"]
                }
            # Check for wl-clipboard (Wayland)
            elif self._command_exists("wl-copy") and self._command_exists("wl-paste"):
                commands["wl-clipboard"] = {
                    "read": ["wl-paste"],
                    "write": ["wl-copy"]
                }
        
        elif self.system == "darwin":  # macOS
            if self._command_exists("pbcopy") and self._command_exists("pbpaste"):
                commands["pbclipboard"] = {
                    "read": ["pbpaste"],
                    "write": ["pbcopy"]
                }
        
        elif self.system == "windows":
            # Windows has built-in clip command for writing
            commands["clip"] = {
                "write": ["clip"]
            }
            # PowerShell for reading
            if self._command_exists("powershell"):
                commands["powershell"] = {
                    "read": ["powershell", "-command", "Get-Clipboard"]
                }
        
        return commands
    
    def _command_exists(self, command: str) -> bool:
        """
        Check if a command exists in the system PATH.
        
        Args:
            command: Command name to check
            
        Returns:
            True if command exists, False otherwise
        """
        try:
            subprocess.run(
                ["which", command] if self.system != "windows" else ["where", command],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    async def read_clipboard(self) -> Dict[str, Any]:
        """
        Read clipboard content using the best available method.
        
        Returns:
            Dict containing clipboard content and metadata
        """
        result = {
            "content": "",
            "method": None,
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "error": None
        }
        
        # Try CLI methods first (most reliable)
        for method_name, commands in self.cli_commands.items():
            if "read" in commands:
                try:
                    process = await asyncio.create_subprocess_exec(
                        *commands["read"],
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode == 0:
                        content = stdout.decode('utf-8', errors='ignore')
                        result.update({
                            "content": content,
                            "method": f"cli_{method_name}",
                            "success": True
                        })
                        logger.debug(f"Clipboard read via {method_name}: {len(content)} chars")
                        return result
                    else:
                        logger.warning(f"CLI read failed for {method_name}: {stderr.decode()}")
                        
                except Exception as e:
                    logger.warning(f"Exception reading clipboard via {method_name}: {e}")
        
        # Fallback to file-based clipboard
        try:
            if self.fallback_file.exists():
                content = self.fallback_file.read_text(encoding='utf-8')
                result.update({
                    "content": content,
                    "method": "file_fallback",
                    "success": True
                })
                logger.debug(f"Clipboard read via file fallback: {len(content)} chars")
                return result
        except Exception as e:
            logger.warning(f"File fallback read failed: {e}")
            result["error"] = str(e)
        
        # If all methods fail
        result["error"] = "No clipboard access methods available"
        logger.error("All clipboard read methods failed")
        return result
    
    async def write_clipboard(self, content: str) -> Dict[str, Any]:
        """
        Write content to clipboard using the best available method.
        
        Args:
            content: Text content to write to clipboard
            
        Returns:
            Dict containing operation result and metadata
        """
        result = {
            "method": None,
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "content_length": len(content),
            "error": None
        }
        
        # Add to history
        self._add_to_history(content)
        
        # Try CLI methods first
        for method_name, commands in self.cli_commands.items():
            if "write" in commands:
                try:
                    process = await asyncio.create_subprocess_exec(
                        *commands["write"],
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate(input=content.encode('utf-8'))
                    
                    if process.returncode == 0:
                        result.update({
                            "method": f"cli_{method_name}",
                            "success": True
                        })
                        logger.debug(f"Clipboard written via {method_name}: {len(content)} chars")
                        
                        # Also write to file fallback as backup
                        await self._write_file_fallback(content)
                        return result
                    else:
                        logger.warning(f"CLI write failed for {method_name}: {stderr.decode()}")
                        
                except Exception as e:
                    logger.warning(f"Exception writing clipboard via {method_name}: {e}")
        
        # Fallback to file-based clipboard
        try:
            await self._write_file_fallback(content)
            result.update({
                "method": "file_fallback",
                "success": True
            })
            logger.debug(f"Clipboard written via file fallback: {len(content)} chars")
            return result
        except Exception as e:
            logger.error(f"File fallback write failed: {e}")
            result["error"] = str(e)
        
        # If all methods fail
        result["error"] = "No clipboard write methods available"
        logger.error("All clipboard write methods failed")
        return result
    
    async def _write_file_fallback(self, content: str) -> None:
        """
        Write content to the file-based clipboard fallback.
        
        Args:
            content: Content to write
        """
        self.fallback_file.parent.mkdir(exist_ok=True)
        self.fallback_file.write_text(content, encoding='utf-8')
    
    def _add_to_history(self, content: str) -> None:
        """
        Add content to clipboard history.
        
        Args:
            content: Content to add to history
        """
        entry = {
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "length": len(content)
        }
        
        # Remove duplicates
        self.history = [h for h in self.history if h["content"] != content]
        
        # Add to front
        self.history.insert(0, entry)
        
        # Limit history size
        if len(self.history) > self.max_history:
            self.history = self.history[:self.max_history]
    
    async def clear_clipboard(self) -> Dict[str, Any]:
        """
        Clear clipboard content.
        
        Returns:
            Dict containing operation result
        """
        result = await self.write_clipboard("")
        
        # Also clear file fallback
        try:
            if self.fallback_file.exists():
                self.fallback_file.unlink()
        except Exception as e:
            logger.warning(f"Failed to clear file fallback: {e}")
        
        return result
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get clipboard service status and capabilities.
        
        Returns:
            Dict containing status information
        """
        return {
            "system": self.system,
            "available_methods": list(self.cli_commands.keys()) + ["file_fallback"],
            "fallback_file": str(self.fallback_file),
            "file_exists": self.fallback_file.exists(),
            "history_count": len(self.history),
            "capabilities": {
                "read": len(self.cli_commands) > 0 or self.fallback_file.exists(),
                "write": len(self.cli_commands) > 0 or True,  # File fallback always available
                "history": True,
                "multi_format": False  # Future enhancement
            }
        }
    
    async def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get clipboard history.
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            List of history entries
        """
        return self.history[:limit]


# Global service instance
clipboard_service = ClipboardService()
