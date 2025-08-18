"""
Tests for read_file_tool
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from icpy.agent.tools.read_file_tool import ReadFileTool
from icpy.agent.tools.base_tool import ToolResult


class TestReadFileTool:
    """Test ReadFileTool implementation"""
    
    def test_tool_properties(self):
        """Test tool has correct properties"""
        tool = ReadFileTool()
        assert tool.name == "read_file"
        assert "Read the contents of a file" in tool.description
        assert tool.parameters["type"] == "object"
        assert "filePath" in tool.parameters["properties"]
        assert "startLine" in tool.parameters["properties"]
        assert "endLine" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["filePath"]
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.read_file_tool.get_workspace_service')
    @patch('icpy.agent.tools.read_file_tool.get_filesystem_service')
    async def test_read_full_file(self, mock_fs_service, mock_ws_service):
        """Test reading entire file"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.read_file.return_value = "file content"
        mock_fs_service.return_value = mock_fs
        
        tool = ReadFileTool()
        result = await tool.execute(filePath="test.txt")
        
        assert result.success is True
        assert result.data == {"content": "file content"}
        assert result.error is None
        
        # Verify workspace root resolution and file read
        mock_ws.get_workspace_root.assert_called_once()
        mock_fs.read_file.assert_called_once_with("/workspace/test.txt")
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.read_file_tool.get_workspace_service')
    @patch('icpy.agent.tools.read_file_tool.get_filesystem_service')
    async def test_read_file_range(self, mock_fs_service, mock_ws_service):
        """Test reading file with line range"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.read_file_range.return_value = "line 2\nline 3"
        mock_fs_service.return_value = mock_fs
        
        tool = ReadFileTool()
        result = await tool.execute(filePath="test.txt", startLine=2, endLine=3)
        
        assert result.success is True
        assert result.data == {"content": "line 2\nline 3"}
        assert result.error is None
        
        mock_fs.read_file_range.assert_called_once_with("/workspace/test.txt", 2, 3)
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.read_file_tool.get_workspace_service')
    @patch('icpy.agent.tools.read_file_tool.get_filesystem_service')
    async def test_read_file_start_line_only(self, mock_fs_service, mock_ws_service):
        """Test reading file from start line to end"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.read_file_range.return_value = "line 5\nline 6\nline 7"
        mock_fs_service.return_value = mock_fs
        
        tool = ReadFileTool()
        result = await tool.execute(filePath="test.txt", startLine=5)
        
        assert result.success is True
        assert result.data == {"content": "line 5\nline 6\nline 7"}
        
        mock_fs.read_file_range.assert_called_once_with("/workspace/test.txt", 5, None)
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.read_file_tool.get_workspace_service')
    @patch('icpy.agent.tools.read_file_tool.get_filesystem_service')
    async def test_read_nonexistent_file(self, mock_fs_service, mock_ws_service):
        """Test reading file that doesn't exist"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.read_file.side_effect = FileNotFoundError("File not found")
        mock_fs_service.return_value = mock_fs
        
        tool = ReadFileTool()
        result = await tool.execute(filePath="nonexistent.txt")
        
        assert result.success is False
        assert result.data is None
        assert "File not found" in result.error
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.read_file_tool.get_workspace_service')
    @patch('icpy.agent.tools.read_file_tool.get_filesystem_service')
    async def test_read_file_permission_error(self, mock_fs_service, mock_ws_service):
        """Test reading file with permission error"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.read_file.side_effect = PermissionError("Permission denied")
        mock_fs_service.return_value = mock_fs
        
        tool = ReadFileTool()
        result = await tool.execute(filePath="restricted.txt")
        
        assert result.success is False
        assert result.data is None
        assert "Permission denied" in result.error
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.read_file_tool.get_workspace_service')
    async def test_path_traversal_blocked(self, mock_ws_service):
        """Test that path traversal outside workspace is blocked"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        tool = ReadFileTool()
        result = await tool.execute(filePath="../../../etc/passwd")
        
        assert result.success is False
        assert result.data is None
        assert "outside workspace" in result.error.lower()
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.read_file_tool.get_workspace_service')
    @patch('icpy.agent.tools.read_file_tool.get_filesystem_service')
    async def test_invalid_line_range(self, mock_fs_service, mock_ws_service):
        """Test invalid line range (start > end)"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs_service.return_value = mock_fs
        
        tool = ReadFileTool()
        result = await tool.execute(filePath="test.txt", startLine=10, endLine=5)
        
        assert result.success is False
        assert result.data is None
        assert "cannot be greater than" in result.error.lower()
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.read_file_tool.get_workspace_service')
    @patch('icpy.agent.tools.read_file_tool.get_filesystem_service')
    async def test_negative_line_numbers(self, mock_fs_service, mock_ws_service):
        """Test negative line numbers"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs_service.return_value = mock_fs
        
        tool = ReadFileTool()
        result = await tool.execute(filePath="test.txt", startLine=-1)
        
        assert result.success is False
        assert result.data is None
        assert "positive" in result.error.lower()
    
    def test_to_openai_function(self):
        """Test OpenAI function schema"""
        tool = ReadFileTool()
        schema = tool.to_openai_function()
        
        assert schema["name"] == "read_file"
        assert "parameters" in schema
        assert schema["parameters"]["properties"]["filePath"]["type"] == "string"
        assert schema["parameters"]["properties"]["startLine"]["type"] == "integer"
        assert schema["parameters"]["properties"]["endLine"]["type"] == "integer" 