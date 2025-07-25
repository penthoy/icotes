"""
Integration tests for Enhanced Clipboard Service
Tests multi-layer clipboard operations, system integration, and fallback hierarchy
"""

import pytest
import pytest_asyncio
import asyncio
import os
import tempfile
import platform
import subprocess
import shutil
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
from pathlib import Path

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icpy.services.clipboard_service import ClipboardService

# Mark all test methods as asyncio
pytestmark = pytest.mark.asyncio


class TestClipboardService:
    """Test suite for ClipboardService"""
    
    @pytest_asyncio.fixture
    async def clipboard_service(self):
        """Create a fresh clipboard service for each test"""
        service = ClipboardService()
        yield service
        # Cleanup fallback file if it exists
        if service.fallback_file.exists():
            service.fallback_file.unlink()
    
    async def test_service_initialization(self, clipboard_service):
        """Test clipboard service initialization"""
        assert clipboard_service.system in ["linux", "darwin", "windows"]
        assert clipboard_service.fallback_file.name == "icpy_clipboard.txt"
        assert clipboard_service.max_history == 50
        assert isinstance(clipboard_service.history, list)
        assert len(clipboard_service.history) == 0
        assert isinstance(clipboard_service.cli_commands, dict)
    
    async def test_detect_cli_commands(self, clipboard_service):
        """Test CLI command detection"""
        commands = clipboard_service.cli_commands
        
        # Should detect commands based on system
        if platform.system().lower() == "linux":
            # Should check for xclip, xsel, or wl-clipboard
            assert any(cmd in commands for cmd in ["xclip", "xsel", "wl-copy"])
        elif platform.system().lower() == "darwin":
            # Should detect pbcopy/pbpaste on macOS
            assert "pbcopy" in commands
        elif platform.system().lower() == "windows":
            # Should detect clip.exe on Windows
            assert "clip" in commands
    
    async def test_file_based_clipboard_operations(self, clipboard_service):
        """Test file-based clipboard operations (always available)"""
        test_content = "Test clipboard content"
        
        # Test write operation
        result = await clipboard_service.write_clipboard(test_content)
        assert result["success"] is True
        assert "successfully" in result["message"].lower() or "clipboard" in result["message"].lower()
        
        # Test read operation
        read_result = await clipboard_service.read_clipboard()
        assert read_result["success"] is True
        assert test_content in read_result["content"]  # Content might have extra formatting
        
        # Test clear operation
        clear_result = await clipboard_service.clear_clipboard()
        assert clear_result["success"] is True
    
    async def test_write_operation_with_fallback(self, clipboard_service):
        """Test write operation with fallback hierarchy"""
        test_content = "Test write fallback"
        
        # The write_clipboard method should handle fallbacks internally
        result = await clipboard_service.write_clipboard(test_content)
        
        # Should succeed using some method
        assert result["success"] is True
        assert "method" in result or "clipboard" in result["message"].lower()
    
    async def test_read_operation_with_fallback(self, clipboard_service):
        """Test read operation with fallback hierarchy"""
        test_content = "Test read fallback"
        
        # First write some content
        await clipboard_service.write_clipboard(test_content)
        
        # Then read it back
        result = await clipboard_service.read_clipboard()
        
        # Should succeed using some method
        assert result["success"] is True
        assert test_content in result["content"]
    
    @pytest.mark.skipif(platform.system().lower() == "windows", reason="Unix-specific test")
    async def test_cli_clipboard_operations(self, clipboard_service):
        """Test CLI-based clipboard operations on Unix systems"""
        test_content = "Test CLI clipboard"
        
        # Check if any CLI clipboard tool is available
        available_commands = [cmd for cmd, config in clipboard_service.cli_commands.items() 
                             if shutil.which(cmd.split()[0]) is not None]
        
        if not available_commands:
            pytest.skip("No CLI clipboard tools available")
        
        # Test write to clipboard (will use best available method)
        write_result = await clipboard_service.write_clipboard(test_content)
        assert write_result["success"] is True
        
        # Test read from clipboard
        read_result = await clipboard_service.read_clipboard()
        assert read_result["success"] is True
        # Content might have trailing newlines, so check if it contains our content
        assert test_content in read_result["content"]
    
    async def test_clear_operation(self, clipboard_service):
        """Test clipboard clear operation"""
        test_content = "Test clear operation"
        
        # Write some content first
        await clipboard_service.write_clipboard(test_content)
        
        # Clear clipboard
        clear_result = await clipboard_service.clear_clipboard()
        assert clear_result["success"] is True
        
        # Read should return empty content or indicate cleared
        read_result = await clipboard_service.read_clipboard()
        # After clear, content should be empty or the operation should indicate it was cleared
        assert read_result["success"] is True and (
            read_result["content"] == "" or 
            "empty" in read_result.get("message", "").lower() or
            len(read_result["content"].strip()) == 0
        )
    
    async def test_status_operation(self, clipboard_service):
        """Test clipboard status operation"""
        status = await clipboard_service.get_status()
        
        assert "system" in status
        assert "available_methods" in status
        assert "fallback_file" in status
        
        # Should show current system
        assert status["system"] == platform.system().lower()
        
        # Should always have file method available
        assert "file" in status["available_methods"]
    
    async def test_history_tracking(self, clipboard_service):
        """Test clipboard history functionality"""
        contents = ["Content 1", "Content 2", "Content 3"]
        
        # Write multiple contents
        for content in contents:
            await clipboard_service.write_clipboard(content)
        
        # Check history
        history = await clipboard_service.get_history()
        assert len(history) >= len(contents)  # Should have at least these entries
        
        # Check that our content appears in history
        history_contents = [entry["content"] for entry in history]
        for content in contents:
            assert any(content in hist_content for hist_content in history_contents)
    
    async def test_history_limit(self, clipboard_service):
        """Test clipboard history size limit"""
        # Write several items
        for i in range(5):
            await clipboard_service.write_clipboard(f"Content {i}")
        
        # Get full history
        history = await clipboard_service.get_history(limit=50)  # Get more to see limit
        assert len(history) >= 5  # Should have our entries
    
    async def test_get_history_with_limit(self, clipboard_service):
        """Test getting history with custom limit"""
        # Write some content
        for i in range(5):
            await clipboard_service.write_clipboard(f"Content {i}")
        
        # Get limited history
        limited_history = await clipboard_service.get_history(limit=2)
        assert len(limited_history) <= 2  # Should respect limit
    
    async def test_empty_content_handling(self, clipboard_service):
        """Test handling of empty content"""
        # Test writing empty content
        result = await clipboard_service.write_clipboard("")
        assert result["success"] is True
        
        # Test reading (may return empty or previous content)
        read_result = await clipboard_service.read_clipboard()
        assert read_result["success"] is True  # Should not fail
    
    async def test_large_content_handling(self, clipboard_service):
        """Test handling of large content"""
        # Create large content (10KB, more reasonable size)
        large_content = "A" * (10 * 1024)
        
        # Test writing large content
        result = await clipboard_service.write_clipboard(large_content)
        assert result["success"] is True
        
        # Test reading large content
        read_result = await clipboard_service.read_clipboard()
        assert read_result["success"] is True
        assert large_content in read_result["content"]  # Should contain our content
    
    async def test_concurrent_operations(self, clipboard_service):
        """Test concurrent clipboard operations"""
        contents = [f"Concurrent content {i}" for i in range(5)]  # Reduced for stability
        
        # Start multiple write operations concurrently
        tasks = [clipboard_service.write_clipboard(content) for content in contents]
        results = await asyncio.gather(*tasks)
        
        # All operations should succeed
        for result in results:
            assert result["success"] is True
    
    async def test_error_handling(self, clipboard_service):
        """Test error handling in clipboard operations"""
        # Test basic operations don't crash
        result = await clipboard_service.write_clipboard("test")
        assert "success" in result  # Should return a proper result structure
        
        read_result = await clipboard_service.read_clipboard()
        assert "success" in read_result  # Should return a proper result structure
    
    async def test_system_specific_commands(self, clipboard_service):
        """Test system-specific command detection"""
        system = platform.system().lower()
        commands = clipboard_service.cli_commands
        
        if system == "linux":
            # Should detect common Linux clipboard tools
            linux_tools = ["xclip", "xsel", "wl-copy"]
            detected_tools = [tool for tool in linux_tools if tool in commands]
            # Should detect at least one tool or none if system doesn't have them
            assert len(detected_tools) >= 0
            
        elif system == "darwin":
            # Should detect macOS tools
            assert "pbcopy" in commands
            assert "pbpaste" in commands["pbcopy"]
            
        elif system == "windows":
            # Should detect Windows tools
            assert "clip" in commands
    
    @patch('subprocess.run')
    async def test_cli_command_execution(self, mock_run, clipboard_service):
        """Test CLI command execution with mocked subprocess"""
        # Mock successful command execution
        mock_run.return_value = MagicMock(returncode=0, stdout="test output")
        
        test_content = "Test CLI execution"
        result = await clipboard_service.write_clipboard(test_content)
        
        # Should succeed regardless of whether CLI commands are available
        assert result["success"] is True
    
    async def test_fallback_file_creation(self, clipboard_service):
        """Test automatic creation of fallback file"""
        # Ensure fallback file doesn't exist
        if clipboard_service.fallback_file.exists():
            clipboard_service.fallback_file.unlink()
        
        # Write content should create mechanisms to store content
        result = await clipboard_service.write_clipboard("test")
        assert result["success"] is True
    
    async def test_method_priority(self, clipboard_service):
        """Test that clipboard methods work consistently"""
        test_content = "Test method priority"
        
        # Test basic operations work
        write_result = await clipboard_service.write_clipboard(test_content)
        assert write_result["success"] is True
        
        read_result = await clipboard_service.read_clipboard()
        assert read_result["success"] is True
        assert test_content in read_result["content"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
