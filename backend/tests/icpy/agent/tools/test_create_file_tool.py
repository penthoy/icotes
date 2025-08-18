"""
Tests for create_file_tool
"""

import pytest
from unittest.mock import AsyncMock, patch
from icpy.agent.tools.create_file_tool import CreateFileTool
from icpy.agent.tools.base_tool import ToolResult


class TestCreateFileTool:
    """Test CreateFileTool implementation"""
    
    def test_tool_properties(self):
        """Test tool has correct properties"""
        tool = CreateFileTool()
        assert tool.name == "create_file"
        assert "Create a new file" in tool.description
        assert tool.parameters["type"] == "object"
        assert "filePath" in tool.parameters["properties"]
        assert "content" in tool.parameters["properties"]
        assert "createDirectories" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["filePath", "content"]
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.create_file_tool.get_workspace_service')
    @patch('icpy.agent.tools.create_file_tool.get_filesystem_service')
    async def test_create_file_success(self, mock_fs_service, mock_ws_service):
        """Test successful file creation"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.write_file.return_value = True
        mock_fs_service.return_value = mock_fs
        
        tool = CreateFileTool()
        result = await tool.execute(filePath="test.txt", content="Hello World")
        
        assert result.success is True
        assert result.data == {"created": True}
        assert result.error is None
        
        mock_fs.write_file.assert_called_once_with("/workspace/test.txt", "Hello World")
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.create_file_tool.get_workspace_service')
    @patch('icpy.agent.tools.create_file_tool.get_filesystem_service')
    async def test_create_file_with_directories(self, mock_fs_service, mock_ws_service):
        """Test creating file with parent directories"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.create_directory.return_value = True
        mock_fs.write_file.return_value = True
        mock_fs_service.return_value = mock_fs
        
        tool = CreateFileTool()
        result = await tool.execute(
            filePath="subdir/test.txt", 
            content="Hello World", 
            createDirectories=True
        )
        
        assert result.success is True
        assert result.data == {"created": True}
        
        mock_fs.create_directory.assert_called_once_with("/workspace/subdir")
        mock_fs.write_file.assert_called_once_with("/workspace/subdir/test.txt", "Hello World")
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.create_file_tool.get_workspace_service')
    @patch('icpy.agent.tools.create_file_tool.get_filesystem_service')
    async def test_create_file_no_directories(self, mock_fs_service, mock_ws_service):
        """Test creating file without creating parent directories"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.write_file.side_effect = FileNotFoundError("Directory not found")
        mock_fs_service.return_value = mock_fs
        
        tool = CreateFileTool()
        result = await tool.execute(
            filePath="nonexistent/test.txt", 
            content="Hello World", 
            createDirectories=False
        )
        
        assert result.success is False
        assert result.data is None
        assert "Directory not found" in result.error
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.create_file_tool.get_workspace_service')
    @patch('icpy.agent.tools.create_file_tool.get_filesystem_service')
    async def test_create_file_already_exists(self, mock_fs_service, mock_ws_service):
        """Test creating file that already exists"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.write_file.side_effect = FileExistsError("File already exists")
        mock_fs_service.return_value = mock_fs
        
        tool = CreateFileTool()
        result = await tool.execute(filePath="existing.txt", content="New content")
        
        assert result.success is False
        assert result.data is None
        assert "already exists" in result.error
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.create_file_tool.get_workspace_service')
    @patch('icpy.agent.tools.create_file_tool.get_filesystem_service')
    async def test_create_file_permission_error(self, mock_fs_service, mock_ws_service):
        """Test creating file with permission error"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.write_file.side_effect = PermissionError("Permission denied")
        mock_fs_service.return_value = mock_fs
        
        tool = CreateFileTool()
        result = await tool.execute(filePath="restricted.txt", content="Content")
        
        assert result.success is False
        assert result.data is None
        assert "Permission denied" in result.error
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.create_file_tool.get_workspace_service')
    async def test_path_traversal_blocked(self, mock_ws_service):
        """Test that path traversal outside workspace is blocked"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        tool = CreateFileTool()
        result = await tool.execute(filePath="../../../tmp/malicious.txt", content="bad")
        
        assert result.success is False
        assert result.data is None
        assert "outside workspace" in result.error.lower()
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.create_file_tool.get_workspace_service')
    @patch('icpy.agent.tools.create_file_tool.get_filesystem_service')
    async def test_create_file_empty_content(self, mock_fs_service, mock_ws_service):
        """Test creating file with empty content"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.write_file.return_value = True
        mock_fs_service.return_value = mock_fs
        
        tool = CreateFileTool()
        result = await tool.execute(filePath="empty.txt", content="")
        
        assert result.success is True
        assert result.data == {"created": True}
        
        mock_fs.write_file.assert_called_once_with("/workspace/empty.txt", "")
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.create_file_tool.get_workspace_service')
    @patch('icpy.agent.tools.create_file_tool.get_filesystem_service')
    async def test_create_file_large_content(self, mock_fs_service, mock_ws_service):
        """Test creating file with large content"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_fs = AsyncMock()
        mock_fs.write_file.return_value = True
        mock_fs_service.return_value = mock_fs
        
        large_content = "x" * 10000  # 10KB content
        
        tool = CreateFileTool()
        result = await tool.execute(filePath="large.txt", content=large_content)
        
        assert result.success is True
        assert result.data == {"created": True}
        
        mock_fs.write_file.assert_called_once_with("/workspace/large.txt", large_content)
    
    def test_to_openai_function(self):
        """Test OpenAI function schema"""
        tool = CreateFileTool()
        schema = tool.to_openai_function()
        
        assert schema["name"] == "create_file"
        assert "parameters" in schema
        assert schema["parameters"]["properties"]["filePath"]["type"] == "string"
        assert schema["parameters"]["properties"]["content"]["type"] == "string"
        assert schema["parameters"]["properties"]["createDirectories"]["type"] == "boolean" 