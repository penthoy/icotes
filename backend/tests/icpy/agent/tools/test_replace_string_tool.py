"""
Tests for replace_string_tool
"""

import pytest
from unittest.mock import AsyncMock, patch
from icpy.agent.tools.replace_string_tool import ReplaceStringTool
from icpy.agent.tools.base_tool import ToolResult


class TestReplaceStringTool:
    """Test ReplaceStringTool implementation"""
    
    def test_tool_properties(self):
        """Test tool has correct properties"""
        tool = ReplaceStringTool()
        assert tool.name == "replace_string_in_file"
        assert "Replace a string in a file" in tool.description
        assert tool.parameters["type"] == "object"
        assert "filePath" in tool.parameters["properties"]
        assert "oldString" in tool.parameters["properties"]
        assert "newString" in tool.parameters["properties"]
        assert "validateContext" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["filePath", "oldString", "newString"]
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.replace_string_tool.get_workspace_service')
    @patch('icpy.agent.tools.replace_string_tool.get_filesystem_service')
    async def test_replace_single_occurrence(self, mock_fs_service, mock_ws_service):
        """Test replacing single occurrence"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.read_file.return_value = "Hello world\nHello universe"
        mock_fs.write_file.return_value = True
        mock_fs_service.return_value = mock_fs
        
        tool = ReplaceStringTool()
        result = await tool.execute(
            filePath="test.txt", 
            oldString="Hello world", 
            newString="Hello Python"
        )
        
        assert result.success is True
        assert result.data == {"replacedCount": 1}
        assert result.error is None
        
        # Verify file was read and written
        mock_fs.read_file.assert_called_once_with("/workspace/test.txt")
        mock_fs.write_file.assert_called_once_with("/workspace/test.txt", "Hello Python\nHello universe")
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.replace_string_tool.get_workspace_service')
    @patch('icpy.agent.tools.replace_string_tool.get_filesystem_service')
    async def test_replace_multiple_occurrences(self, mock_fs_service, mock_ws_service):
        """Test replacing multiple occurrences"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.read_file.return_value = "foo bar foo baz foo"
        mock_fs.write_file.return_value = True
        mock_fs_service.return_value = mock_fs
        
        tool = ReplaceStringTool()
        result = await tool.execute(
            filePath="test.txt", 
            oldString="foo", 
            newString="FOO"
        )
        
        assert result.success is True
        assert result.data == {"replacedCount": 3}
        
        mock_fs.write_file.assert_called_once_with("/workspace/test.txt", "FOO bar FOO baz FOO")
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.replace_string_tool.get_workspace_service')
    @patch('icpy.agent.tools.replace_string_tool.get_filesystem_service')
    async def test_replace_zero_occurrences(self, mock_fs_service, mock_ws_service):
        """Test replacing when string not found"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.read_file.return_value = "Hello world"
        mock_fs.write_file.return_value = True
        mock_fs_service.return_value = mock_fs
        
        tool = ReplaceStringTool()
        result = await tool.execute(
            filePath="test.txt", 
            oldString="nonexistent", 
            newString="replacement"
        )
        
        assert result.success is True
        assert result.data == {"replacedCount": 0}
        
        # File should not be written if no changes
        mock_fs.write_file.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.replace_string_tool.get_workspace_service')
    @patch('icpy.agent.tools.replace_string_tool.get_filesystem_service')
    async def test_validate_context_single_occurrence(self, mock_fs_service, mock_ws_service):
        """Test validateContext with single occurrence (success)"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.read_file.return_value = "Hello world\nGoodbye world"
        mock_fs.write_file.return_value = True
        mock_fs_service.return_value = mock_fs
        
        tool = ReplaceStringTool()
        result = await tool.execute(
            filePath="test.txt", 
            oldString="Hello world", 
            newString="Hello Python",
            validateContext=True
        )
        
        assert result.success is True
        assert result.data == {"replacedCount": 1}
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.replace_string_tool.get_workspace_service')
    @patch('icpy.agent.tools.replace_string_tool.get_filesystem_service')
    async def test_validate_context_multiple_occurrences(self, mock_fs_service, mock_ws_service):
        """Test validateContext with multiple occurrences (error)"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.read_file.return_value = "foo bar foo baz"
        mock_fs_service.return_value = mock_fs
        
        tool = ReplaceStringTool()
        result = await tool.execute(
            filePath="test.txt", 
            oldString="foo", 
            newString="FOO",
            validateContext=True
        )
        
        assert result.success is False
        assert result.data is None
        assert "exactly one" in result.error.lower()
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.replace_string_tool.get_workspace_service')
    @patch('icpy.agent.tools.replace_string_tool.get_filesystem_service')
    async def test_validate_context_zero_occurrences(self, mock_fs_service, mock_ws_service):
        """Test validateContext with zero occurrences (error)"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.read_file.return_value = "Hello world"
        mock_fs_service.return_value = mock_fs
        
        tool = ReplaceStringTool()
        result = await tool.execute(
            filePath="test.txt", 
            oldString="nonexistent", 
            newString="replacement",
            validateContext=True
        )
        
        assert result.success is False
        assert result.data is None
        assert "exactly one" in result.error.lower()
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.replace_string_tool.get_workspace_service')
    @patch('icpy.agent.tools.replace_string_tool.get_filesystem_service')
    async def test_file_not_found(self, mock_fs_service, mock_ws_service):
        """Test replacing in non-existent file"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.read_file.side_effect = FileNotFoundError("File not found")
        mock_fs_service.return_value = mock_fs
        
        tool = ReplaceStringTool()
        result = await tool.execute(
            filePath="nonexistent.txt", 
            oldString="old", 
            newString="new"
        )
        
        assert result.success is False
        assert result.data is None
        assert "File not found" in result.error
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.replace_string_tool.get_workspace_service')
    async def test_path_traversal_blocked(self, mock_ws_service):
        """Test that path traversal outside workspace is blocked"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        tool = ReplaceStringTool()
        result = await tool.execute(
            filePath="../../../etc/passwd", 
            oldString="old", 
            newString="new"
        )
        
        assert result.success is False
        assert result.data is None
        assert "outside workspace" in result.error.lower()
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.replace_string_tool.get_workspace_service')
    @patch('icpy.agent.tools.replace_string_tool.get_filesystem_service')
    async def test_empty_strings(self, mock_fs_service, mock_ws_service):
        """Test replacing with empty strings"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.read_file.return_value = "Hello world"
        mock_fs.write_file.return_value = True
        mock_fs_service.return_value = mock_fs
        
        tool = ReplaceStringTool()
        result = await tool.execute(
            filePath="test.txt", 
            oldString="world", 
            newString=""
        )
        
        assert result.success is True
        assert result.data == {"replacedCount": 1}
        
        mock_fs.write_file.assert_called_once_with("/workspace/test.txt", "Hello ")
    
    def test_to_openai_function(self):
        """Test OpenAI function schema"""
        tool = ReplaceStringTool()
        schema = tool.to_openai_function()
        
        assert schema["name"] == "replace_string_in_file"
        assert "parameters" in schema
        assert schema["parameters"]["properties"]["filePath"]["type"] == "string"
        assert schema["parameters"]["properties"]["oldString"]["type"] == "string"
        assert schema["parameters"]["properties"]["newString"]["type"] == "string"
        assert schema["parameters"]["properties"]["validateContext"]["type"] == "boolean" 