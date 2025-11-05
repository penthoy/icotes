"""
Tests for semantic_search_tool Phase 7 hop support

Tests that semantic_search tool correctly handles both local and remote (hopped) contexts.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from icpy.agent.tools.semantic_search_tool import SemanticSearchTool
from icpy.agent.tools.base_tool import ToolResult


class TestSemanticSearchHopSupport:
    """Test Phase 7 hop support in SemanticSearchTool"""
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_contextual_filesystem')
    @patch('icpy.agent.tools.context_helpers.get_current_context')
    async def test_remote_search_when_hopped(self, mock_get_context, mock_get_fs):
        """Test that remote search is used when hopped to a remote server"""
        # Setup: Simulate hopped context
        mock_get_context.return_value = {
            "contextId": "hop1",
            "status": "connected",
            "host": "192.168.1.100",
            "username": "user"
        }
        
        # Mock remote filesystem service
        mock_fs = AsyncMock()
        mock_fs.search_files = AsyncMock(return_value=[
            {
                'file_info': {'path': '/home/user/project/file.py'},
                'matches': ['Found: test_function'],
                'score': 1.0,
                'context': {}
            }
        ])
        mock_get_fs.return_value = mock_fs
        
        tool = SemanticSearchTool()
        result = await tool.execute(query="test_function", maxResults=10)
        
        # Verify remote search was called
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]['file'] == '/home/user/project/file.py'
        mock_fs.search_files.assert_called_once()
        call_kwargs = mock_fs.search_files.call_args[1]
        assert call_kwargs['query'] == 'test_function'
        assert call_kwargs['max_results'] == 10
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    @patch('icpy.agent.tools.context_helpers.get_current_context')
    async def test_local_search_when_not_hopped(self, mock_get_context, mock_subprocess, mock_ws_service):
        """Test that local ripgrep search is used when not hopped"""
        # Setup: Simulate local context (no hop)
        mock_get_context.return_value = {
            "contextId": "local",
            "status": "disconnected"
        }
        
        mock_ws = MagicMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        # Mock ripgrep output
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "file.py:10:def test_function():"
        mock_subprocess.return_value = mock_result
        
        tool = SemanticSearchTool()
        result = await tool.execute(query="test_function")
        
        # Verify local ripgrep search was used
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]['file'] == 'file.py'
        assert result.data[0]['line'] == 10
        mock_subprocess.assert_called()
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.context_helpers.get_current_context')
    async def test_context_detection_error_fallback_to_local(self, mock_get_context):
        """Test that context detection errors fall back to local search"""
        # Setup: Simulate context detection error
        mock_get_context.side_effect = Exception("Context router unavailable")
        
        with patch('icpy.agent.tools.semantic_search_tool.get_workspace_service') as mock_ws_service:
            with patch('icpy.agent.tools.semantic_search_tool.subprocess.run') as mock_subprocess:
                mock_ws = MagicMock()
                mock_ws.get_workspace_root.return_value = "/workspace"
                mock_ws_service.return_value = mock_ws
                
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "file.py:5:test"
                mock_subprocess.return_value = mock_result
                
                tool = SemanticSearchTool()
                result = await tool.execute(query="test")
                
                # Should fall back to local search gracefully
                assert result.success is True
                assert len(result.data) >= 1
                mock_subprocess.assert_called()
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_contextual_filesystem')
    @patch('icpy.agent.tools.context_helpers.get_current_context')
    async def test_remote_search_empty_results(self, mock_get_context, mock_get_fs):
        """Test remote search with no results"""
        mock_get_context.return_value = {
            "contextId": "hop1",
            "status": "connected"
        }
        
        mock_fs = AsyncMock()
        mock_fs.search_files = AsyncMock(return_value=[])
        mock_get_fs.return_value = mock_fs
        
        tool = SemanticSearchTool()
        result = await tool.execute(query="nonexistent_pattern")
        
        assert result.success is True
        assert result.data == []
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_contextual_filesystem')
    @patch('icpy.agent.tools.context_helpers.get_current_context')
    async def test_remote_search_error_handling(self, mock_get_context, mock_get_fs):
        """Test remote search error handling"""
        mock_get_context.return_value = {
            "contextId": "hop1",
            "status": "connected"
        }
        
        mock_fs = AsyncMock()
        mock_fs.search_files = AsyncMock(side_effect=Exception("SFTP connection lost"))
        mock_get_fs.return_value = mock_fs
        
        tool = SemanticSearchTool()
        result = await tool.execute(query="test")
        
        assert result.success is False
        assert "Remote search failed" in result.error
        assert "SFTP connection lost" in result.error
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_contextual_filesystem')
    @patch('icpy.agent.tools.context_helpers.get_current_context')
    async def test_remote_search_result_formatting(self, mock_get_context, mock_get_fs):
        """Test that remote search results are properly formatted"""
        mock_get_context.return_value = {
            "contextId": "hop1",
            "status": "connected"
        }
        
        # Test with dict results
        mock_fs = AsyncMock()
        mock_fs.search_files = AsyncMock(return_value=[
            {
                'file_info': {'path': '/remote/file1.py', 'name': 'file1.py'},
                'matches': ['def helper():', 'class Helper:'],
                'score': 1.5
            },
            {
                'file_info': {'path': '/remote/file2.py', 'name': 'file2.py'},
                'matches': ['Helper.method()'],
                'score': 0.8
            }
        ])
        mock_get_fs.return_value = mock_fs
        
        tool = SemanticSearchTool()
        result = await tool.execute(query="Helper")
        
        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0]['file'] == '/remote/file1.py'
        assert result.data[0]['snippet'] == 'def helper():'
        assert result.data[1]['file'] == '/remote/file2.py'
        assert result.data[1]['snippet'] == 'Helper.method()'
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_contextual_filesystem')
    @patch('icpy.agent.tools.context_helpers.get_current_context')
    async def test_remote_search_respects_max_results(self, mock_get_context, mock_get_fs):
        """Test that remote search respects max_results parameter"""
        mock_get_context.return_value = {
            "contextId": "hop1",
            "status": "connected"
        }
        
        # Return more results than max_results
        mock_fs = AsyncMock()
        mock_fs.search_files = AsyncMock(return_value=[
            {'file_info': {'path': f'/file{i}.py'}, 'matches': [f'match{i}'], 'score': 1.0}
            for i in range(20)
        ])
        mock_get_fs.return_value = mock_fs
        
        tool = SemanticSearchTool()
        result = await tool.execute(query="test", maxResults=5)
        
        # Should be capped at 5 results
        assert result.success is True
        assert len(result.data) == 5
