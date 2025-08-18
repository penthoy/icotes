"""
Tests for semantic_search_tool
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from icpy.agent.tools.semantic_search_tool import SemanticSearchTool
from icpy.agent.tools.base_tool import ToolResult


class TestSemanticSearchTool:
    """Test SemanticSearchTool implementation"""
    
    def test_tool_properties(self):
        """Test tool has correct properties"""
        tool = SemanticSearchTool()
        assert tool.name == "semantic_search"
        assert "Search for code or files" in tool.description
        assert tool.parameters["type"] == "object"
        assert "query" in tool.parameters["properties"]
        assert "scope" in tool.parameters["properties"]
        assert "fileTypes" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["query"]
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    async def test_basic_search(self, mock_subprocess, mock_ws_service):
        """Test basic search functionality"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        # Mock ripgrep output
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "file1.py:10:def function_name():\nfile2.py:25:    function_name()"
        mock_subprocess.return_value = mock_result
        
        tool = SemanticSearchTool()
        result = await tool.execute(query="function_name")
        
        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0]["file"] == "file1.py"
        assert result.data[0]["line"] == 10
        assert result.data[0]["snippet"] == "def function_name():"
        assert result.data[1]["file"] == "file2.py"
        assert result.data[1]["line"] == 25
        assert result.data[1]["snippet"] == "    function_name()"
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    async def test_search_with_scope(self, mock_subprocess, mock_ws_service):
        """Test search with directory scope"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "src/main.py:5:import os"
        mock_subprocess.return_value = mock_result
        
        tool = SemanticSearchTool()
        result = await tool.execute(query="import", scope="src")
        
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["file"] == "src/main.py"
        
        # Verify ripgrep was called with correct scope
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "/workspace/src" in call_args
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    async def test_search_with_file_types(self, mock_subprocess, mock_ws_service):
        """Test search with file type filter"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "test.py:1:print('hello')"
        mock_subprocess.return_value = mock_result
        
        tool = SemanticSearchTool()
        result = await tool.execute(query="print", fileTypes=["py", "js"])
        
        assert result.success is True
        assert len(result.data) == 1
        
        # Verify ripgrep was called with file type filters
        call_args = mock_subprocess.call_args[0][0]
        assert "--type" in call_args or "-t" in call_args
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    async def test_search_no_results(self, mock_subprocess, mock_ws_service):
        """Test search with no results"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_result = MagicMock()
        mock_result.returncode = 1  # ripgrep returns 1 when no matches
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result
        
        tool = SemanticSearchTool()
        result = await tool.execute(query="nonexistent_pattern")
        
        assert result.success is True
        assert result.data == []
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    async def test_search_capped_results(self, mock_subprocess, mock_ws_service):
        """Test that results are capped at 50"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        # Generate 60 lines of output
        lines = [f"file{i}.py:{i}:match line {i}" for i in range(1, 61)]
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "\n".join(lines)
        mock_subprocess.return_value = mock_result
        
        tool = SemanticSearchTool()
        result = await tool.execute(query="match")
        
        assert result.success is True
        assert len(result.data) == 50  # Should be capped at 50
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    async def test_search_ripgrep_error(self, mock_subprocess, mock_ws_service):
        """Test handling ripgrep errors"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_result = MagicMock()
        mock_result.returncode = 2  # ripgrep error
        mock_result.stderr = "ripgrep error"
        mock_subprocess.return_value = mock_result
        
        tool = SemanticSearchTool()
        result = await tool.execute(query="test")
        
        assert result.success is False
        assert result.data is None
        assert "ripgrep error" in result.error
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    async def test_search_subprocess_exception(self, mock_subprocess, mock_ws_service):
        """Test handling subprocess exceptions"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_subprocess.side_effect = Exception("Subprocess error")
        
        tool = SemanticSearchTool()
        result = await tool.execute(query="test")
        
        assert result.success is False
        assert result.data is None
        assert "Subprocess error" in result.error
    
    @pytest.mark.asyncio
    async def test_missing_query(self):
        """Test executing without query"""
        tool = SemanticSearchTool()
        result = await tool.execute()
        
        assert result.success is False
        assert result.data is None
        assert "query is required" in result.error
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    async def test_empty_query(self, mock_subprocess, mock_ws_service):
        """Test executing with empty query"""
        tool = SemanticSearchTool()
        result = await tool.execute(query="")
        
        assert result.success is False
        assert result.data is None
        assert "query cannot be empty" in result.error.lower()
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    async def test_malformed_ripgrep_output(self, mock_subprocess, mock_ws_service):
        """Test handling malformed ripgrep output"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "malformed:line\nfile.py:not_a_number:content\nvalid.py:10:good line"
        mock_subprocess.return_value = mock_result
        
        tool = SemanticSearchTool()
        result = await tool.execute(query="test")
        
        assert result.success is True
        # Should only include the valid line
        assert len(result.data) == 1
        assert result.data[0]["file"] == "valid.py"
        assert result.data[0]["line"] == 10
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    async def test_fixed_string_mode(self, mock_subprocess, mock_ws_service):
        """Test that fixed string mode (-F) is used by default"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result
        
        tool = SemanticSearchTool()
        await tool.execute(query="test.*pattern")
        
        # Verify -F flag is used for fixed string search
        call_args = mock_subprocess.call_args[0][0]
        assert "-F" in call_args
    
    def test_to_openai_function(self):
        """Test OpenAI function schema"""
        tool = SemanticSearchTool()
        schema = tool.to_openai_function()
        
        assert schema["name"] == "semantic_search"
        assert "parameters" in schema
        assert schema["parameters"]["properties"]["query"]["type"] == "string"
        assert schema["parameters"]["properties"]["scope"]["type"] == "string"
        assert schema["parameters"]["properties"]["fileTypes"]["type"] == "array" 