"""
Run terminal command tool for agents

Phase 7: Hop-aware command execution. When hopped to a remote server,
commands run on the remote host via SSH. Otherwise, commands run locally.
"""

import asyncio
import logging
import subprocess
from typing import Dict, Any, Optional
import traceback
from .base_tool import BaseTool, ToolResult
import os

logger = logging.getLogger(__name__)

# Throttle noisy fallback notice: log once at INFO, then DEBUG afterwards
_SCHEDULING_FALLBACK_LOGGED = False

# Optional imports for hop awareness
try:
    from icpy.services.hop_service import get_hop_service
    from icpy.services.context_router import get_context_router
    HOP_AVAILABLE = True
except ImportError:
    HOP_AVAILABLE = False


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
        """Execute the terminal command (hop-aware)"""
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
            
            # Determine execution context (local vs remote)
            is_remote = False
            ssh_conn = None
            if HOP_AVAILABLE:
                try:
                    router = await get_context_router()
                    context = await router.get_context()
                    if context.contextId and context.contextId != "local" and context.status == "connected":
                        hop = await get_hop_service()
                        ssh_conn = hop.get_active_connection()
                        if ssh_conn:
                            is_remote = True
                            logger.debug(f"[RunTerminal] Executing on remote: {context.contextId}")
                except Exception as e:
                    logger.debug(f"[RunTerminal] Hop detection failed, using local: {e}")
            
            if is_remote and ssh_conn:
                # Execute on remote host via SSH
                return await self._execute_remote(ssh_conn, command, is_background)
            else:
                # Execute locally via subprocess
                return await self._execute_local(command, is_background)
                
        except Exception as e:
            logger.error(f"Error executing command {kwargs.get('command')}: {e}")
            return ToolResult(success=False, error=f"Failed to execute command: {str(e)}")
    
    async def _execute_local(self, command: str, is_background: bool) -> ToolResult:
        """Execute command locally via subprocess"""
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
                    "pid": process.pid,
                    "context": "local"
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
                    "pid": process.pid,
                    "context": "local"
                }
            )
    
    async def _execute_remote(self, ssh_conn, command: str, is_background: bool) -> ToolResult:
        """Execute command on remote host via SSH connection.

        Prefers executing within the hop service's event loop using
        run_coroutine_threadsafe. If that times out (common cause of the
        previously observed hang), falls back to an ephemeral SSH connection
        created in the current loop to avoid cross-loop issues.
        """
        try:
            from concurrent.futures import Future
            import asyncio
            
            # Configurable, shorter scheduling timeout to avoid 30s stalls
            try:
                SCHEDULE_TIMEOUT_SEC = float(os.environ.get('HOP_RUN_SCHEDULE_TIMEOUT', '2.0'))
            except Exception:
                SCHEDULE_TIMEOUT_SEC = 2.0

            # Get the hop service's event loop where the connection was created
            if HOP_AVAILABLE:
                hop = await get_hop_service()
                conn_loop = hop.get_active_loop()
                
                if conn_loop and conn_loop != asyncio.get_running_loop():
                    # We're in a different loop, need to execute in the connection's loop
                    logger.debug("[RunTerminal] Executing command in hop service's event loop")
                    
                    async def _run_in_conn_loop():
                        """Helper to run command in the connection's loop"""
                        if is_background:
                            bg_cmd = f"nohup {command} > /dev/null 2>&1 & echo $!"
                            result = await ssh_conn.run(bg_cmd, check=False)
                            return {
                                "status": 0,
                                "output": "",
                                "error": "",
                                "pid": result.stdout.strip() if result.stdout else "unknown",
                                "context": "remote"
                            }
                        else:
                            result = await ssh_conn.run(command, check=False)
                            return {
                                "status": result.exit_status if result.exit_status is not None else -1,
                                "output": result.stdout if result.stdout else "",
                                "error": result.stderr if result.stderr else "",
                                "context": "remote"
                            }
                    
                    # Schedule the coroutine in the connection's loop
                    future = asyncio.run_coroutine_threadsafe(_run_in_conn_loop(), conn_loop)
                    try:
                        # Shorter timeout to avoid long hangs; we'll fall back if exceeded
                        data = future.result(timeout=SCHEDULE_TIMEOUT_SEC)
                        return ToolResult(success=True, data=data)
                    except Exception as e:
                        # Timeout or other scheduling failure -> fall back to ephemeral SSH
                        global _SCHEDULING_FALLBACK_LOGGED
                        if not _SCHEDULING_FALLBACK_LOGGED:
                            logger.info(f"[RunTerminal] Scheduling in hop loop failed after {SCHEDULE_TIMEOUT_SEC:.1f}s ({type(e).__name__}). Falling back to ephemeral SSH.")
                            _SCHEDULING_FALLBACK_LOGGED = True
                        else:
                            logger.debug(f"[RunTerminal] Scheduling in hop loop failed after {SCHEDULE_TIMEOUT_SEC:.1f}s ({type(e).__name__}). Using ephemeral SSH.")
                        try:
                            future.cancel()
                        except Exception:
                            pass
                        # Intentionally continue to ephemeral path below
                        pass

                # Fallback path: use ephemeral SSH in current loop
                try:
                    async with hop.ephemeral_ssh() as eph_conn:
                        if eph_conn is None:
                            raise RuntimeError("Ephemeral SSH not available")
                        if is_background:
                            bg_cmd = f"nohup {command} > /dev/null 2>&1 & echo $!"
                            result = await eph_conn.run(bg_cmd, check=False)
                            pid_str = result.stdout.strip() if result.stdout else "unknown"
                            return ToolResult(success=True, data={
                                "status": 0,
                                "output": "",
                                "error": "",
                                "pid": pid_str,
                                "context": "remote",
                                "mode": "ephemeral"
                            })
                        else:
                            result = await eph_conn.run(command, check=False)
                            return ToolResult(success=True, data={
                                "status": result.exit_status if result.exit_status is not None else -1,
                                "output": result.stdout if result.stdout else "",
                                "error": result.stderr if result.stderr else "",
                                "context": "remote",
                                "mode": "ephemeral"
                            })
                except Exception as e:
                    # Fall through to local execution attempt (below) or final error
                    logger.error(f"[RunTerminal] Ephemeral SSH execution failed: {e}")
            
            # Fallback: try direct execution (same loop)
            if is_background:
                bg_cmd = f"nohup {command} > /dev/null 2>&1 & echo $!"
                result = await ssh_conn.run(bg_cmd, check=False)
                pid_str = result.stdout.strip() if result.stdout else "unknown"
                
                return ToolResult(
                    success=True,
                    data={
                        "status": 0,
                        "output": "",
                        "error": "",
                        "pid": pid_str,
                        "context": "remote",
                        "mode": "direct"
                    }
                )
            else:
                result = await ssh_conn.run(command, check=False)
                
                return ToolResult(
                    success=True,
                    data={
                        "status": result.exit_status if result.exit_status is not None else -1,
                        "output": result.stdout if result.stdout else "",
                        "error": result.stderr if result.stderr else "",
                        "context": "remote",
                        "mode": "direct"
                    }
                )
                
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"[RunTerminal] Remote execution failed: {type(e).__name__}: {e}\n{tb}")
            return ToolResult(
                success=False,
                error=f"Remote command execution failed: {type(e).__name__}: {e}"
            )