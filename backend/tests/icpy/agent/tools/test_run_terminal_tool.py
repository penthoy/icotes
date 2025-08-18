"""
Tests for run_terminal_tool
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from icpy.agent.tools.run_terminal_tool import RunTerminalTool
from icpy.agent.tools.base_tool import ToolResult


class TestRunTerminalTool:
    """Test RunTerminalTool implementation"""
    
    def test_tool_properties(self):
        """Test tool has correct properties"""
        tool = RunTerminalTool()
        assert tool.name == "run_in_terminal"
        assert "Execute a command in the terminal" in tool.description
        assert tool.parameters["type"] == "object"
        assert "command" in tool.parameters["properties"]
        assert "explanation" in tool.parameters["properties"]
        assert "isBackground" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["command", "explanation"]
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.run_terminal_tool.asyncio.create_subprocess_shell')
    async def test_run_simple_command(self, mock_subprocess):
        """Test running a simple command"""
        # Setup mocks
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"Hello World", b"")
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_subprocess.return_value = mock_process
        
        tool = RunTerminalTool()
        result = await tool.execute(
            command="echo 'Hello World'",
            explanation="Print hello world"
        )
        
        assert result.success is True
        assert result.data["status"] == 0
        assert result.data["output"] == "Hello World"
        assert result.data["pid"] == 12345
        assert result.error is None
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.run_terminal_tool.asyncio.create_subprocess_shell')
    async def test_run_background_command(self, mock_subprocess):
        """Test running a background command"""
        # Setup mocks
        mock_process = AsyncMock()
        mock_process.pid = 54321
        mock_subprocess.return_value = mock_process
        
        tool = RunTerminalTool()
        result = await tool.execute(
            command="sleep 10",
            explanation="Sleep for 10 seconds",
            isBackground=True
        )
        
        assert result.success is True
        assert result.data["status"] == 0
        assert result.data["pid"] == 54321
        # Background process doesn't wait for output
        mock_process.communicate.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.run_terminal_tool.asyncio.create_subprocess_shell')
    async def test_run_command_with_error(self, mock_subprocess):
        """Test running a command that fails"""
        # Setup mocks
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"command not found")
        mock_process.returncode = 1
        mock_process.pid = 67890
        mock_subprocess.return_value = mock_process
        
        tool = RunTerminalTool()
        result = await tool.execute(
            command="nonexistent_command",
            explanation="Run a command that doesn't exist"
        )
        
        assert result.success is True  # Tool succeeds even if command fails
        assert result.data["status"] == 1
        assert result.data["error"] == "command not found"
        assert result.error is None
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.run_terminal_tool.asyncio.create_subprocess_shell')
    async def test_run_command_with_output_and_error(self, mock_subprocess):
        """Test running a command with both output and error"""
        # Setup mocks
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"Some output", b"Some error")
        mock_process.returncode = 2
        mock_process.pid = 11111
        mock_subprocess.return_value = mock_process
        
        tool = RunTerminalTool()
        result = await tool.execute(
            command="ls /nonexistent",
            explanation="List non-existent directory"
        )
        
        assert result.success is True
        assert result.data["status"] == 2
        assert result.data["output"] == "Some output"
        assert result.data["error"] == "Some error"
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.run_terminal_tool.asyncio.create_subprocess_shell')
    async def test_subprocess_exception(self, mock_subprocess):
        """Test handling subprocess exceptions"""
        # Setup mocks
        mock_subprocess.side_effect = Exception("Subprocess error")
        
        tool = RunTerminalTool()
        result = await tool.execute(
            command="echo test",
            explanation="Test command"
        )
        
        assert result.success is False
        assert result.data is None
        assert "Subprocess error" in result.error
    
    @pytest.mark.asyncio
    async def test_missing_command(self):
        """Test executing without command"""
        tool = RunTerminalTool()
        result = await tool.execute(explanation="Missing command")
        
        assert result.success is False
        assert result.data is None
        assert "command is required" in result.error
    
    @pytest.mark.asyncio
    async def test_missing_explanation(self):
        """Test executing without explanation"""
        tool = RunTerminalTool()
        result = await tool.execute(command="echo test")
        
        assert result.success is False
        assert result.data is None
        assert "explanation is required" in result.error
    
    @pytest.mark.asyncio
    async def test_empty_command(self):
        """Test executing empty command"""
        tool = RunTerminalTool()
        result = await tool.execute(command="", explanation="Empty command")
        
        assert result.success is False
        assert result.data is None
        assert "command cannot be empty" in result.error.lower()
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.run_terminal_tool.asyncio.create_subprocess_shell')
    async def test_long_running_command(self, mock_subprocess):
        """Test long running command (simulated)"""
        # Setup mocks
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"Task completed after long time", b"")
        mock_process.returncode = 0
        mock_process.pid = 99999
        mock_subprocess.return_value = mock_process
        
        tool = RunTerminalTool()
        result = await tool.execute(
            command="python long_script.py",
            explanation="Run a long Python script"
        )
        
        assert result.success is True
        assert result.data["status"] == 0
        assert "Task completed" in result.data["output"]
    
    def test_to_openai_function(self):
        """Test OpenAI function schema"""
        tool = RunTerminalTool()
        schema = tool.to_openai_function()
        
        assert schema["name"] == "run_in_terminal"
        assert "parameters" in schema
        assert schema["parameters"]["properties"]["command"]["type"] == "string"
        assert schema["parameters"]["properties"]["explanation"]["type"] == "string"
        assert schema["parameters"]["properties"]["isBackground"]["type"] == "boolean" 