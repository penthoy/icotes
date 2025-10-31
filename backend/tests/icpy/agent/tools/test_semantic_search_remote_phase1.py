"""
Tests for semantic_search_tool Phase 1: Remote Search via Terminal

Tests the new remote search implementation that uses ripgrep/grep/find via terminal.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from icpy.agent.tools.semantic_search_tool import SemanticSearchTool
from icpy.agent.tools.base_tool import ToolResult


class TestCommandBuilding:
    """Test command building helpers"""
    
    def test_escape_shell_arg_simple(self):
        tool = SemanticSearchTool()
        result = tool._escape_shell_arg("test")
        assert result == "'test'"
    
    def test_escape_shell_arg_with_quotes(self):
        tool = SemanticSearchTool()
        result = tool._escape_shell_arg("test'with'quotes")
        assert result == "'test'\\''with'\\''quotes'"
    
    def test_escape_shell_arg_prevents_injection(self):
        tool = SemanticSearchTool()
        # Attempt command injection
        result = tool._escape_shell_arg("test'; rm -rf /")
        # The quote is properly escaped, preventing injection
        assert result == "'test'\\''; rm -rf /'"
        # Shell will treat this as a literal string, not execute rm
    
    def test_build_ripgrep_remote_cmd_content_search(self):
        tool = SemanticSearchTool()
        cmd = tool._build_ripgrep_remote_cmd(
            query="helper",
            workspace_root="/home/user/project",
            file_types=["py"],
            include_hidden=False,
            max_results=50,
            mode="content"
        )
        
        assert "rg -n -H --no-heading -i" in cmd
        assert "'helper'" in cmd
        assert "'/home/user/project'" in cmd
        assert "-t py" in cmd
        assert "head -n 50" in cmd
    
    def test_build_ripgrep_remote_cmd_filename_search(self):
        tool = SemanticSearchTool()
        cmd = tool._build_ripgrep_remote_cmd(
            query="test",
            workspace_root="/home/user/project",
            file_types=None,
            include_hidden=True,
            max_results=100,
            mode="filename"
        )
        
        assert "rg --files" in cmd
        assert "--hidden" in cmd
        assert "'test'" in cmd
        assert "head -n 100" in cmd
    
    def test_build_ripgrep_remote_cmd_multiple_file_types(self):
        tool = SemanticSearchTool()
        cmd = tool._build_ripgrep_remote_cmd(
            query="func",
            workspace_root="/home/user/project",
            file_types=["py", "js", "ts"],
            include_hidden=False,
            max_results=50,
            mode="content"
        )
        
        assert "-t py" in cmd
        assert "-t js" in cmd
        assert "-t ts" in cmd
    
    def test_build_grep_remote_cmd(self):
        tool = SemanticSearchTool()
        cmd = tool._build_grep_remote_cmd(
            query="helper",
            workspace_root="/home/user/project",
            file_types=["py"],
            max_results=50
        )
        
        assert "grep -rnH -i" in cmd
        assert "'helper'" in cmd
        assert "'/home/user/project'" in cmd
        assert "--include='*.py'" in cmd
        assert "head -n 50" in cmd
    
    def test_build_find_remote_cmd_with_file_types(self):
        tool = SemanticSearchTool()
        cmd = tool._build_find_remote_cmd(
            query="cat",
            workspace_root="/home/user/project",
            file_types=["png", "jpg"],
            max_results=50
        )
        
        assert "find" in cmd
        assert "'/home/user/project'" in cmd
        assert "-iname '*cat*.png'" in cmd
        assert "-iname '*cat*.jpg'" in cmd
        assert "head -n 50" in cmd
    
    def test_build_find_remote_cmd_without_file_types(self):
        tool = SemanticSearchTool()
        cmd = tool._build_find_remote_cmd(
            query="config",
            workspace_root="/home/user/project",
            file_types=None,
            max_results=50
        )
        
        assert "find" in cmd
        assert "-iname '*config*'" in cmd


class TestOutputParsing:
    """Test output parsing helpers"""
    
    def test_parse_search_output_ripgrep_format(self):
        tool = SemanticSearchTool()
        output = """file.py:10:def helper():
file.py:25:    return helper()
test.py:5:# Helper function"""
        
        results = tool._parse_search_output(output, "content")
        
        assert len(results) == 3
        assert results[0]["file"] == "file.py"
        assert results[0]["line"] == 10
        assert results[0]["snippet"] == "def helper():"
        
        assert results[1]["file"] == "file.py"
        assert results[1]["line"] == 25
        assert results[1]["snippet"] == "return helper()"
        
        assert results[2]["file"] == "test.py"
        assert results[2]["line"] == 5
        assert results[2]["snippet"] == "# Helper function"
    
    def test_parse_search_output_filename_format(self):
        tool = SemanticSearchTool()
        output = """/home/user/project/test.py
/home/user/project/helper.py
/home/user/project/utils/config.py"""
        
        results = tool._parse_search_output(output, "filename")
        
        assert len(results) == 3
        assert results[0]["file"] == "/home/user/project/test.py"
        assert results[0]["line"] is None
        assert results[0]["snippet"] is None
    
    def test_parse_search_output_empty(self):
        tool = SemanticSearchTool()
        results = tool._parse_search_output("", "content")
        assert results == []
    
    def test_parse_search_output_malformed_lines_skipped(self):
        tool = SemanticSearchTool()
        output = """file.py:10:valid line
malformed line without colons
file.py:abc:invalid line number
test.py:20:another valid line"""
        
        results = tool._parse_search_output(output, "content")
        
        # Should get 3 results: 2 valid lines with line numbers, 1 treated as filename-only
        assert len(results) == 3
        assert results[0]["file"] == "file.py"
        assert results[0]["line"] == 10
        assert results[1]["line"] is None  # Malformed line treated as filename
        assert results[2]["file"] == "test.py"
        assert results[2]["line"] == 20


class TestRemoteSearchExecution:
    """Test remote search execution with mocked terminal"""
    
    @pytest.mark.asyncio
    async def test_remote_search_ripgrep_success(self):
        tool = SemanticSearchTool()
        
        # Mock context
        mock_context = {
            "contextId": "hop1",
            "status": "connected",
            "workspaceRoot": "/home/user/project",
            "cwd": "/home/user/project"
        }
        
        # Mock terminal
        mock_terminal = AsyncMock()
        mock_terminal.execute_command = AsyncMock(return_value={
            "output": "test.py:10:def test_function():\nhelper.py:5:import test"
        })
        
        with patch('icpy.agent.tools.context_helpers.get_current_context', new_callable=AsyncMock) as mock_get_context:
            with patch('icpy.agent.tools.context_helpers.get_contextual_terminal', new_callable=AsyncMock) as mock_get_terminal:
                with patch('icpy.services.path_utils.format_namespaced_path', new_callable=AsyncMock) as mock_format_path:
                    mock_get_context.return_value = mock_context
                    mock_get_terminal.return_value = mock_terminal
                    mock_format_path.side_effect = lambda ctx, path: f"{ctx}:{path}"
                    
                    result = await tool._execute_remote_search(
                        query="test",
                        scope=None,
                        file_types=["py"],
                        include_hidden=False,
                        max_results=50
                    )
                    
                    assert result.success is True
                    assert len(result.data) == 2
                    assert result.data[0]["file"] == "test.py"
                    assert result.data[0]["line"] == 10
                    assert "hop1:" in result.data[0]["filePath"]
    
    @pytest.mark.asyncio
    async def test_remote_search_fallback_to_grep(self):
        tool = SemanticSearchTool()
        
        mock_context = {
            "contextId": "hop1",
            "workspaceRoot": "/home/user/project"
        }
        
        # Mock terminal - ripgrep not found, grep succeeds
        mock_terminal = AsyncMock()
        call_count = [0]
        
        async def execute_side_effect(cmd):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call (ripgrep) - not found
                return {"output": "rg: command not found"}
            else:
                # Second call (grep) - success
                return {"output": "file.py:5:test content"}
        
        mock_terminal.execute_command = AsyncMock(side_effect=execute_side_effect)
        
        with patch('icpy.agent.tools.context_helpers.get_current_context', new_callable=AsyncMock) as mock_get_context:
            with patch('icpy.agent.tools.context_helpers.get_contextual_terminal', new_callable=AsyncMock) as mock_get_terminal:
                with patch('icpy.services.path_utils.format_namespaced_path', new_callable=AsyncMock) as mock_format_path:
                    mock_get_context.return_value = mock_context
                    mock_get_terminal.return_value = mock_terminal
                    mock_format_path.side_effect = lambda ctx, path: f"{ctx}:{path}"
                    
                    result = await tool._execute_remote_search(
                        query="test",
                        scope=None,
                        file_types=None,
                        include_hidden=False,
                        max_results=50
                    )
                    
                    assert result.success is True
                    assert len(result.data) == 1
                    assert result.data[0]["file"] == "file.py"
    
    @pytest.mark.asyncio
    async def test_remote_search_fallback_to_find(self):
        tool = SemanticSearchTool()
        
        mock_context = {
            "contextId": "hop1",
            "workspaceRoot": "/home/user/project"
        }
        
        # Mock terminal - ripgrep and grep fail, find succeeds
        mock_terminal = AsyncMock()
        call_count = [0]
        
        async def execute_side_effect(cmd):
            call_count[0] += 1
            if call_count[0] <= 2:
                # First two calls fail
                return {"output": "command not found"}
            else:
                # Third call (find) succeeds
                return {"output": "/home/user/project/test.txt\n/home/user/project/config.txt"}
        
        mock_terminal.execute_command = AsyncMock(side_effect=execute_side_effect)
        
        with patch('icpy.agent.tools.context_helpers.get_current_context', new_callable=AsyncMock) as mock_get_context:
            with patch('icpy.agent.tools.context_helpers.get_contextual_terminal', new_callable=AsyncMock) as mock_get_terminal:
                with patch('icpy.services.path_utils.format_namespaced_path', new_callable=AsyncMock) as mock_format_path:
                    mock_get_context.return_value = mock_context
                    mock_get_terminal.return_value = mock_terminal
                    mock_format_path.side_effect = lambda ctx, path: f"{ctx}:{path}"
                    
                    result = await tool._execute_remote_search(
                        query="test",
                        scope=None,
                        file_types=["txt"],
                        include_hidden=False,
                        max_results=50
                    )
                    
                    assert result.success is True
                    assert len(result.data) == 2
    
    @pytest.mark.asyncio
    async def test_remote_search_no_results(self):
        tool = SemanticSearchTool()
        
        mock_context = {
            "contextId": "hop1",
            "workspaceRoot": "/home/user/project"
        }
        
        # Mock terminal - all commands return empty
        mock_terminal = AsyncMock()
        mock_terminal.execute_command = AsyncMock(return_value={"output": ""})
        
        with patch('icpy.agent.tools.context_helpers.get_current_context', new_callable=AsyncMock) as mock_get_context:
            with patch('icpy.agent.tools.context_helpers.get_contextual_terminal', new_callable=AsyncMock) as mock_get_terminal:
                mock_get_context.return_value = mock_context
                mock_get_terminal.return_value = mock_terminal
                
                result = await tool._execute_remote_search(
                    query="nonexistent",
                    scope=None,
                    file_types=None,
                    include_hidden=False,
                    max_results=50
                )
                
                assert result.success is True
                assert len(result.data) == 0
                assert "ripgrep" in result.error.lower() or "grep" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_remote_search_with_scope(self):
        tool = SemanticSearchTool()
        
        mock_context = {
            "contextId": "hop1",
            "workspaceRoot": "/home/user/project"
        }
        
        mock_terminal = AsyncMock()
        mock_terminal.execute_command = AsyncMock(return_value={
            "output": "src/utils/helper.py:10:test"
        })
        
        with patch('icpy.agent.tools.context_helpers.get_current_context', new_callable=AsyncMock) as mock_get_context:
            with patch('icpy.agent.tools.context_helpers.get_contextual_terminal', new_callable=AsyncMock) as mock_get_terminal:
                with patch('icpy.services.path_utils.format_namespaced_path', new_callable=AsyncMock) as mock_format_path:
                    mock_get_context.return_value = mock_context
                    mock_get_terminal.return_value = mock_terminal
                    mock_format_path.side_effect = lambda ctx, path: f"{ctx}:{path}"
                    
                    result = await tool._execute_remote_search(
                        query="test",
                        scope="src",
                        file_types=["py"],
                        include_hidden=False,
                        max_results=50
                    )
                    
                    # Verify scope was applied in command
                    call_args = mock_terminal.execute_command.call_args[0][0]
                    assert "'/home/user/project/src'" in call_args
    
    @pytest.mark.asyncio
    async def test_remote_search_error_handling(self):
        tool = SemanticSearchTool()
        
        mock_context = {
            "contextId": "hop1",
            "workspaceRoot": "/home/user/project"
        }
        
        # Mock terminal raises exception for all tools
        mock_terminal = AsyncMock()
        mock_terminal.execute_command = AsyncMock(side_effect=Exception("Connection lost"))
        
        with patch('icpy.agent.tools.context_helpers.get_current_context', new_callable=AsyncMock) as mock_get_context:
            with patch('icpy.agent.tools.context_helpers.get_contextual_terminal', new_callable=AsyncMock) as mock_get_terminal:
                mock_get_context.return_value = mock_context
                mock_get_terminal.return_value = mock_terminal
                
                result = await tool._execute_remote_search(
                    query="test",
                    scope=None,
                    file_types=None,
                    include_hidden=False,
                    max_results=50
                )
                
                # All strategies fail gracefully, returning success=True with empty data
                assert result.success is True
                assert result.data == []
                assert "No results found" in result.error


class TestIntegration:
    """Integration tests for full execute() flow"""
    
    @pytest.mark.asyncio
    async def test_execute_detects_remote_and_routes(self):
        tool = SemanticSearchTool()
        
        mock_context = {
            "contextId": "hop1",
            "status": "connected",
            "workspaceRoot": "/home/user/project"
        }
        
        mock_terminal = AsyncMock()
        mock_terminal.execute_command = AsyncMock(return_value={
            "output": "test.py:1:content"
        })
        
        with patch('icpy.agent.tools.context_helpers.get_current_context', new_callable=AsyncMock) as mock_get_context:
            with patch('icpy.agent.tools.context_helpers.get_contextual_terminal', new_callable=AsyncMock) as mock_get_terminal:
                with patch('icpy.services.path_utils.format_namespaced_path', new_callable=AsyncMock) as mock_format_path:
                    mock_get_context.return_value = mock_context
                    mock_get_terminal.return_value = mock_terminal
                    mock_format_path.side_effect = lambda ctx, path: f"{ctx}:{path}"
                    
                    result = await tool.execute(query="test")
                    
                    assert result.success is True
                    # Verify remote search was called (terminal was used)
                    assert mock_terminal.execute_command.called
