"""
Run terminal command tool for agents
"""

import asyncio
import logging
import subprocess
from typing import Dict, Any, Optional
from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)


async def get_terminal_service():
    """Import and return terminal service (for compatibility, but we'll use subprocess)"""
    from icpy.services.terminal_service import get_terminal_service as _get_terminal_service
    return await _get_terminal_service()


class RunTerminalTool(BaseTool):
    """Tool for executing terminal commands"""
    
    def __init__(self):
        super().__init__()
        self.name = "run_in_terminal"
        self.description = "Execute a command in the terminal"
        self.parameters = {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Command to execute"
                },
                "explanation": {
                    "type": "string",
                    "description": "Explanation of what the command does"
                },
                "isBackground": {
                    "type": "boolean",
                    "description": "Whether to run the command in background"
                }
            },
            "required": ["command", "explanation"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the terminal command"""
        try:
            command = kwargs.get("command")
            explanation = kwargs.get("explanation")
            is_background = kwargs.get("isBackground", False)
            
            if command is None:
                return ToolResult(success=False, error="command is required")
            
            if explanation is None:
                return ToolResult(success=False, error="explanation is required")
            
            if not command.strip():
                return ToolResult(success=False, error="command cannot be empty")
            
            logger.info(f"Executing command: {command} ({explanation})")
            
            if is_background:
                # For background processes, start and return immediately
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
                
                return ToolResult(
                    success=True, 
                    data={
                        "status": 0,  # Process started successfully
                        "output": "",
                        "error": "",
                        "pid": process.pid
                    }
                )
            else:
                # For foreground processes, wait for completion
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
                
                stdout, stderr = await process.communicate()
                
                return ToolResult(
                    success=True,
                    data={
                        "status": process.returncode,
                        "output": stdout.decode('utf-8', errors='replace') if stdout else "",
                        "error": stderr.decode('utf-8', errors='replace') if stderr else "",
                        "pid": process.pid
                    }
                )
                
        except Exception as e:
            logger.error(f"Error executing command {kwargs.get('command')}: {e}")
            return ToolResult(success=False, error=f"Failed to execute command: {str(e)}") 