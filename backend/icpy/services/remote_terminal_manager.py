"""
Remote Terminal Manager

Phase 6: Bridge terminal WebSocket sessions to a remote PTY over an active SSH
hop using AsyncSSH. This provides a drop-in alternative to local PTY spawning
in environments where a hop is connected.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import struct
from typing import Dict, Any, Optional

from fastapi import WebSocket

from .hop_service import get_hop_service, ASYNCSSH_AVAILABLE
from ..utils.process_reaper import reap_zombies

logger = logging.getLogger(__name__)

# Module-level singleton (initialized to None)
_remote_terminal_manager_singleton: Optional[RemoteTerminalManager] = None


class RemoteTerminalManager:
    def __init__(self) -> None:
        self._hop = None
        # Track processes for cleanup
        self._sessions: Dict[str, Any] = {}
        # Track active tasks per terminal for cancellation
        self._tasks: Dict[str, list[asyncio.Task]] = {}
        logger.debug(f"[RemoteTerm] Manager initialized id={hex(id(self))}")

    async def initialize(self):
        self._hop = await get_hop_service()
        logger.debug(f"[RemoteTerm] Manager initialize complete id={hex(id(self))} hop_id={hex(id(self._hop))}")
        return self

    async def connect_terminal(self, websocket: WebSocket, terminal_id: str):
        """Attach WebSocket to a remote PTY using asyncssh connection.create_process.

        Returns a tuple (reader, writer, proc) representing remote streams.
        """
        if not ASYNCSSH_AVAILABLE:
            raise RuntimeError("AsyncSSH not available for remote terminal")
        # Use method call instead of getattr to ensure it works correctly in Docker
        conn = self._hop.get_active_connection() if self._hop else None
        session = self._hop.status() if self._hop else None
        logger.info(
            "[RemoteTerm] connect terminal_id=%s context=%s sessions_before=%d",
            terminal_id,
            getattr(session, 'contextId', None),
            len(self._sessions)
        )
        if not self._hop or conn is None:
            error_msg = f"No active SSH connection (hop={self._hop is not None}, conn={conn is not None})"
            logger.error(f"[RemoteTerm] {error_msg}")
            raise RuntimeError(error_msg)
        session = self._hop.status()
        cwd = session.cwd or "/"
        env = {
            'TERM': 'xterm-256color',
            'LANG': 'C.UTF-8',
            'LC_ALL': 'C.UTF-8',
            'HOME': cwd or '/',
            'PWD': cwd or '/',
        }
        # Prefer login interactive shell for paths/aliases; set cwd using a shell wrapper
        # Use bash -il if available; otherwise sh -i
        shell = os.environ.get('REMOTE_SHELL', '/bin/bash')
        args = [shell, '-il'] if shell.endswith('bash') else [shell, '-i']

        # Create remote process with PTY
        try:
            # AsyncSSH create_process expects a command string, supports PTY kwargs; cwd may not be supported across versions
            cmd = " ".join(args)
            logger.info(f"[RemoteTerm] Spawning remote shell: cmd='{cmd}' cwd='{cwd}' env_TERM={env.get('TERM')}")
            proc = await conn.create_process(cmd, term_type='xterm-256color', env=env, encoding='utf-8', errors='replace')
        except TypeError:
            # Extremely old signature - rethrow
            raise
        # Quick fallback: if the login shell exits immediately, retry without -l
        try:
            await asyncio.sleep(0.15)
            if proc.exit_status_ready():
                status = getattr(proc, 'exit_status', None)
                logger.info(f"[RemoteTerm] login shell exited immediately (status={status}), retrying with interactive-only shell")
                try:
                    proc = await conn.create_process(f"{shell} -i", term_type='xterm-256color', env=env, encoding='utf-8', errors='replace')
                except Exception:
                    # Last resort
                    proc = await conn.create_process("/bin/sh -i", term_type='xterm-256color', env=env, encoding='utf-8', errors='replace')
        except Exception:
            pass

        # Change directory after spawn to ensure correct working dir
        try:
            if cwd and cwd != "/":
                logger.debug(f"[RemoteTerm] cd to cwd: {cwd}")
                proc.stdin.write(f"cd {cwd}\n")
            # Set an initial terminal size to a reasonable default
            try:
                logger.debug("[RemoteTerm] set initial terminal size 120x30")
                proc.change_terminal_size(120, 30)
            except Exception:
                pass
            # Drain stdin to ensure cd command is sent
            try:
                await proc.stdin.drain()
            except Exception:
                pass
        except Exception:
            pass

        self._sessions[terminal_id] = proc
        logger.info(f"[RemoteTerm] shell started terminal_id={terminal_id} cwd={cwd} sessions_now={len(self._sessions)}")

        # Start I/O pumps
        read_task = asyncio.create_task(self._pump_stdout(proc, websocket, terminal_id))
        write_task = asyncio.create_task(self._pump_stdin(proc, websocket, terminal_id))
        watch_task = asyncio.create_task(self._watch_process(proc, terminal_id))
        
        self._tasks[terminal_id] = [read_task, write_task, watch_task]

        try:
            await asyncio.gather(read_task, write_task)
        finally:
            try:
                # Try to log exit details
                status = getattr(proc, 'exit_status', None)
                signal = getattr(proc, 'exit_signal', None)
                logger.info(f"[RemoteTerm] closing {terminal_id}: exit_status={status} exit_signal={signal}")
            except Exception:
                pass
            await self.disconnect_terminal(terminal_id)
            try:
                await asyncio.wait_for(watch_task, timeout=1.0)
            except Exception:
                pass
            self._tasks.pop(terminal_id, None)

    async def disconnect_terminal(self, terminal_id: str):
        """Gracefully disconnect a specific terminal session."""
        # Cancel tasks first
        tasks = self._tasks.pop(terminal_id, [])
        for t in tasks:
            if not t.done():
                t.cancel()
        
        proc = self._sessions.pop(terminal_id, None)
        if proc is not None:
            try:
                # Force kill immediately - no graceful shutdown
                proc.kill()
                logger.info(f"[RemoteTerm] Killed remote process for {terminal_id}")
            except Exception as e:
                logger.warning(f"[RemoteTerm] Failed to kill remote process: {e}")
        logger.info(f"[RemoteTerm] Terminal {terminal_id} disconnected")

    def session_count(self) -> int:
        """Return number of active remote terminal sessions currently tracked."""
        try:
            return len(self._sessions)
        except Exception:
            return 0

    async def shutdown_all(self, reason: str = "unknown") -> int:
        """Forcefully disconnect all tracked remote terminal sessions immediately.

        This is used during hop disconnect to ensure no lingering PTY processes keep
        the SSH connection alive or cause hangs.

        Returns the number of sessions that were terminated.
        """
        count = self.session_count()
        logger.info("[RemoteTerm] shutdown_all requested: count=%s reason=%s", count, reason)
        
        # Cancel ALL tasks first (prevents new I/O)
        for terminal_id in list(self._tasks.keys()):
            tasks = self._tasks.pop(terminal_id, [])
            for t in tasks:
                if not t.done():
                    t.cancel()
        
        # Then force-kill all processes
        for terminal_id in list(self._sessions.keys()):
            proc = self._sessions.pop(terminal_id, None)
            if proc:
                try:
                    proc.kill()
                    logger.info(f"[RemoteTerm] Force-killed terminal {terminal_id}")
                except Exception as e:
                    logger.warning(f"[RemoteTerm] Failed to kill {terminal_id}: {e}")
            
        logger.info("[RemoteTerm] shutdown_all complete: terminated=%s", count)
        return count

    async def _pump_stdout(self, proc, websocket: WebSocket, terminal_id: str):
        logger.info(f"[RemoteTerm] _pump_stdout started for {terminal_id}")
        try:
            first_chunk_logged = False
            while True:
                try:
                    # Use a timeout to avoid blocking forever
                    data = await asyncio.wait_for(proc.stdout.read(8192), timeout=0.1)
                    if not data:
                        # Check if process has exited
                        if proc.exit_status is not None or proc.exit_signal is not None:
                            break
                        continue
                    # asyncssh returns str for text streams; ensure str
                    if isinstance(data, bytes):
                        try:
                            text = data.decode('utf-8', errors='replace')
                        except Exception:
                            # Extremely defensive fallback
                            text = data.decode('latin-1', errors='replace')
                    else:
                        text = data
                    if not first_chunk_logged:
                        # Log a safe preview of the first chunk to validate data is flowing
                        preview = repr(text[:80]).replace('\n', '\\n').replace('\r', '\\r')
                        logger.info(f"[RemoteTerm] first stdout chunk for {terminal_id}: {preview}")
                        first_chunk_logged = True
                    logger.debug(f"[RemoteTerm] ->WS len={len(text)}")
                    await websocket.send_text(text)
                except asyncio.TimeoutError:
                    # Check if process has exited
                    if proc.exit_status is not None or proc.exit_signal is not None:
                        break
                    continue
                except asyncio.CancelledError:
                    logger.info(f"[RemoteTerm] _pump_stdout cancelled for {terminal_id}")
                    raise
        except Exception as e:
            if not isinstance(e, asyncio.CancelledError):
                logger.info(f"[RemoteTerm] stdout pump error {terminal_id}: {e}")
        finally:
            logger.info(f"[RemoteTerm] _pump_stdout exited for {terminal_id}")

    async def _pump_stdin(self, proc, websocket: WebSocket, terminal_id: str):
        logger.info(f"[RemoteTerm] _pump_stdin started for {terminal_id}")
        try:
            first_inbound_logged = False
            while True:
                try:
                    # Use a timeout to avoid blocking forever
                    msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                    # Handle resize messages
                    if msg.startswith('{"type":'):
                        try:
                            payload = json.loads(msg)
                            if payload.get('type') == 'resize':
                                cols = payload.get('cols', 80)
                                rows = payload.get('rows', 24)
                                try:
                                    # AsyncSSH API
                                    logger.debug(f"[RemoteTerm] resize to {cols}x{rows}")
                                    proc.change_terminal_size(cols, rows)
                                except Exception:
                                    pass
                                continue
                        except Exception:
                            pass
                    if not first_inbound_logged:
                        preview = repr(msg[:80]).replace('\n', '\\n').replace('\r', '\\r')
                        logger.info(f"[RemoteTerm] first WS text for {terminal_id}: {preview}")
                        first_inbound_logged = True
                    logger.debug(f"[RemoteTerm] WS-> len={len(msg)}")
                    proc.stdin.write(msg)
                except asyncio.TimeoutError:
                    # Check if process has exited
                    if proc.exit_status is not None or proc.exit_signal is not None:
                        break
                    continue
                except asyncio.CancelledError:
                    logger.info(f"[RemoteTerm] _pump_stdin cancelled for {terminal_id}")
                    raise
                except Exception:
                    # WebSocket closed or other error
                    break
        except Exception as e:
            if not isinstance(e, asyncio.CancelledError):
                logger.info(f"[RemoteTerm] stdin pump error {terminal_id}: {e}")
        finally:
            logger.info(f"[RemoteTerm] _pump_stdin exited for {terminal_id}")

    async def _watch_process(self, proc, terminal_id: str):
        try:
            await proc.wait_closed()
            status = getattr(proc, 'exit_status', None)
            signal = getattr(proc, 'exit_signal', None)
            logger.info(f"[RemoteTerm] process closed for {terminal_id}: exit_status={status} exit_signal={signal}")
        except Exception as e:
            logger.info(f"[RemoteTerm] process watcher error for {terminal_id}: {e}")


async def get_remote_terminal_manager() -> RemoteTerminalManager:
    """Return singleton RemoteTerminalManager.

    Previous implementation returned a NEW instance each call which meant
    connect_terminal() and disconnect/shutdown paths were operating on
    different manager objects (empty session tracking on disconnect).
    This caused zombie remote PTY processes to survive hop disconnect.
    """
    global _remote_terminal_manager_singleton
    if _remote_terminal_manager_singleton is None:
        logger.info("[RemoteTerm] Creating singleton manager instance")
        _remote_terminal_manager_singleton = await RemoteTerminalManager().initialize()
    else:
        logger.debug(
            "[RemoteTerm] Reusing singleton manager id=%s sessions=%d tasks=%d",
            hex(id(_remote_terminal_manager_singleton)),
            len(_remote_terminal_manager_singleton._sessions),
            len(_remote_terminal_manager_singleton._tasks),
        )
    return _remote_terminal_manager_singleton
