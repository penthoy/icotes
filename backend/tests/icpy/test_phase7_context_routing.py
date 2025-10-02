"""
Tests for Phase 7: Chat tools with remote execution via ContextRouter

These tests verify that agent tools (read_file, create_file, replace_string)
properly route through ContextRouter to work with the active hop context.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from icpy.agent.tools.read_file_tool import ReadFileTool
from icpy.agent.tools.create_file_tool import CreateFileTool
from icpy.agent.tools.replace_string_tool import ReplaceStringTool


@pytest.mark.asyncio
async def test_read_file_uses_context_router(tmp_path, monkeypatch):
    """Verify ReadFileTool uses ContextRouter instead of direct filesystem service"""
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    # Mock ContextRouter to verify it's being called
    mock_fs = AsyncMock()
    mock_fs.read_file = AsyncMock(return_value="test content")
    
    # Patch where get_context_router is imported IN context_helpers
    with patch('icpy.services.context_router.get_context_router') as mock_router_getter:
        mock_router = AsyncMock()
        mock_router.get_filesystem = AsyncMock(return_value=mock_fs)
        mock_router_getter.return_value = mock_router
        
        tool = ReadFileTool()
        result = await tool.execute(filePath=str(test_file))
        
        # Verify context router was used
        mock_router_getter.assert_called_once()
        mock_router.get_filesystem.assert_called_once()
        mock_fs.read_file.assert_called_once()
        
        assert result.success is True
        assert result.data["content"] == "test content"


@pytest.mark.asyncio
async def test_create_file_uses_context_router(tmp_path, monkeypatch):
    """Verify CreateFileTool uses ContextRouter instead of direct filesystem service"""
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    
    # Mock ContextRouter to verify it's being called
    mock_fs = AsyncMock()
    mock_fs.write_file = AsyncMock(return_value=True)
    mock_fs.create_directory = AsyncMock(return_value=True)
    
    with patch('icpy.services.context_router.get_context_router') as mock_router_getter:
        mock_router = AsyncMock()
        mock_router.get_filesystem = AsyncMock(return_value=mock_fs)
        mock_router_getter.return_value = mock_router
        
        tool = CreateFileTool()
        result = await tool.execute(
            filePath=str(tmp_path / "newfile.txt"),
            content="new content",
            createDirectories=True
        )
        
        # Verify context router was used
        mock_router_getter.assert_called_once()
        mock_router.get_filesystem.assert_called_once()
        
        assert result.success is True


@pytest.mark.asyncio
async def test_replace_string_uses_context_router(tmp_path, monkeypatch):
    """Verify ReplaceStringTool uses ContextRouter instead of direct filesystem service"""
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    
    # Mock ContextRouter to verify it's being called
    mock_fs = AsyncMock()
    mock_fs.read_file = AsyncMock(return_value="old content")
    mock_fs.write_file = AsyncMock(return_value=True)
    
    with patch('icpy.services.context_router.get_context_router') as mock_router_getter:
        mock_router = AsyncMock()
        mock_router.get_filesystem = AsyncMock(return_value=mock_fs)
        mock_router_getter.return_value = mock_router
        
        tool = ReplaceStringTool()
        result = await tool.execute(
            filePath=str(tmp_path / "test.txt"),
            oldString="old",
            newString="new"
        )
        
        # Verify context router was used
        mock_router_getter.assert_called_once()
        mock_router.get_filesystem.assert_called()  # Called multiple times (read + write)
        
        assert result.success is True


@pytest.mark.asyncio
async def test_tools_fallback_to_local_fs_when_router_unavailable(tmp_path, monkeypatch):
    """Verify tools gracefully fallback to local FS if ContextRouter is unavailable"""
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("fallback content")
    
    # Mock ContextRouter to raise an exception
    # Patch where get_context_router is imported IN context_helpers
    with patch('icpy.services.context_router.get_context_router') as mock_router_getter:
        mock_router_getter.side_effect = Exception("Router unavailable")
        
        # Tool should fallback to local filesystem service
        tool = ReadFileTool()
        result = await tool.execute(filePath=str(test_file))
        
        # Verify it still works (fallback behavior)
        assert result.success is True
        assert result.data["content"] == "fallback content"


@pytest.mark.asyncio
async def test_context_helpers_get_current_context():
    """Verify get_current_context returns hop session info"""
    from icpy.agent.tools.context_helpers import get_current_context
    
    # Mock hop session
    mock_session = MagicMock()
    mock_session.contextId = "test-remote-123"
    mock_session.status = "connected"
    mock_session.host = "remote.example.com"
    mock_session.port = 22
    mock_session.username = "testuser"
    mock_session.cwd = "/home/testuser"
    
    with patch('icpy.services.context_router.get_context_router') as mock_router_getter:
        mock_router = AsyncMock()
        mock_router.get_context = AsyncMock(return_value=mock_session)
        mock_router_getter.return_value = mock_router
        
        context = await get_current_context()
        
        assert context["contextId"] == "test-remote-123"
        assert context["status"] == "connected"
        assert context["host"] == "remote.example.com"
        assert context["port"] == 22
        assert context["username"] == "testuser"
        assert context["cwd"] == "/home/testuser"


@pytest.mark.asyncio
async def test_context_helpers_fallback_to_local():
    """Verify get_current_context falls back to local context on error"""
    from icpy.agent.tools.context_helpers import get_current_context
    
    with patch('icpy.services.context_router.get_context_router') as mock_router_getter:
        mock_router_getter.side_effect = Exception("Router error")
        
        context = await get_current_context()
        
        # Should return local context on error
        assert context["contextId"] == "local"
        assert context["status"] == "disconnected"
