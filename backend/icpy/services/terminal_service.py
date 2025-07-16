"""
Terminal Service for icpy Backend

This service provides terminal session management with PTY support and event-driven
communication through the message broker. It supports multiple terminal instances
with independent sessions and configuration.

Key Features:
- Multiple terminal instances with independent sessions
- PTY-based terminal sessions with full shell support
- Event-driven communication through message broker
- Terminal session management and configuration
- Real-time terminal I/O handling
- Terminal resizing and environment management
- Session persistence and recovery

Author: GitHub Copilot
Date: July 16, 2025
"""

import asyncio
import json
import logging
import os
import pty
import select
import signal
import struct
import subprocess
import termios
import fcntl
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any, Optional, List, Set, Callable
from fastapi import WebSocket

from ..core.message_broker import get_message_broker
from ..core.connection_manager import get_connection_manager

logger = logging.getLogger(__name__)

# Global service instance
_terminal_service = None


class TerminalState(Enum):
    """Terminal session states."""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class TerminalConfig:
    """Configuration for terminal sessions."""
    shell: str = "/bin/bash"
    term: str = "xterm-256color"
    cols: int = 80
    rows: int = 24
    env: Dict[str, str] = None
    cwd: str = None
    startup_script: str = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.env is None:
            self.env = {}
        if self.cwd is None:
            self.cwd = os.path.expanduser('~')


@dataclass
class TerminalSession:
    """Represents a terminal session."""
    id: str
    name: str
    config: TerminalConfig
    state: TerminalState
    master_fd: Optional[int] = None
    process: Optional[subprocess.Popen] = None
    read_task: Optional[asyncio.Task] = None
    write_task: Optional[asyncio.Task] = None
    created_at: float = None
    last_activity: float = None
    
    def __post_init__(self):
        """Initialize timestamps."""
        if self.created_at is None:
            self.created_at = time.time()
        if self.last_activity is None:
            self.last_activity = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'config': asdict(self.config),
            'state': self.state.value,
            'created_at': self.created_at,
            'last_activity': self.last_activity,
            'pid': self.process.pid if self.process else None,
            'has_process': self.process is not None
        }


class TerminalService:
    """Service for managing terminal sessions with event-driven communication.
    
    This service provides comprehensive terminal session management including:
    - Multiple terminal instances with independent sessions
    - PTY-based terminal sessions with full shell support
    - Event-driven communication through message broker
    - Terminal session management and configuration
    - Real-time terminal I/O handling
    - Terminal resizing and environment management
    - Session persistence and recovery
    """

    def __init__(self):
        """Initialize the Terminal Service."""
        self.message_broker = None
        self.connection_manager = None
        
        # Terminal sessions
        self.sessions: Dict[str, TerminalSession] = {}
        self.websocket_sessions: Dict[str, str] = {}  # websocket_id -> session_id
        
        # Statistics
        self.stats = {
            'sessions_created': 0,
            'sessions_destroyed': 0,
            'total_input_bytes': 0,
            'total_output_bytes': 0,
            'resize_operations': 0,
            'startup_time': 0.0
        }
        
        # Configuration
        self.max_sessions = 100
        self.session_timeout = 3600  # 1 hour
        self.cleanup_interval = 300  # 5 minutes
        
        # Default shell paths
        self.shell_paths = ['/bin/bash', '/usr/bin/bash', '/usr/local/bin/bash']
        
        logger.info("TerminalService initialized")

    async def initialize(self):
        """Initialize the terminal service.
        
        Sets up message broker connections and starts background tasks.
        """
        start_time = time.time()
        
        # Get dependencies
        self.message_broker = await get_message_broker()
        self.connection_manager = await get_connection_manager()
        
        # Subscribe to message broker events
        await self.message_broker.subscribe('terminal.*', self._handle_terminal_event)
        await self.message_broker.subscribe('connection.disconnected', self._handle_connection_disconnected)
        
        # Start background tasks
        asyncio.create_task(self._cleanup_sessions_task())
        
        # Publish initialization event
        await self.message_broker.publish('terminal.service_initialized', {
            'service': 'terminal',
            'timestamp': time.time(),
            'max_sessions': self.max_sessions
        })
        
        self.stats['startup_time'] = time.time() - start_time
        logger.info(f"TerminalService initialized in {self.stats['startup_time']:.3f}s")

    async def shutdown(self):
        """Shutdown the terminal service.
        
        Stops all terminal sessions and cleans up resources.
        """
        logger.info("Shutting down TerminalService...")
        
        # Stop all terminal sessions
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self.stop_session(session_id)
        
        # Clear data structures
        self.sessions.clear()
        self.websocket_sessions.clear()
        
        # Publish shutdown event
        if self.message_broker:
            await self.message_broker.publish('terminal.service_shutdown', {
                'service': 'terminal',
                'timestamp': time.time()
            })
        
        logger.info("TerminalService shutdown complete")

    async def create_session(self, name: str = None, config: TerminalConfig = None) -> str:
        """Create a new terminal session.
        
        Args:
            name: Optional name for the session
            config: Terminal configuration
            
        Returns:
            The session ID
            
        Raises:
            Exception: If session creation fails
        """
        if len(self.sessions) >= self.max_sessions:
            raise Exception(f"Maximum number of sessions ({self.max_sessions}) reached")
        
        # Generate session ID and name
        session_id = str(uuid.uuid4())
        if name is None:
            name = f"Terminal {len(self.sessions) + 1}"
        
        # Use default config if not provided
        if config is None:
            config = TerminalConfig()
        
        # Create session object
        session = TerminalSession(
            id=session_id,
            name=name,
            config=config,
            state=TerminalState.CREATED
        )
        
        # Store session
        self.sessions[session_id] = session
        self.stats['sessions_created'] += 1
        
        # Publish event
        await self.message_broker.publish('terminal.session_created', {
            'session_id': session_id,
            'name': name,
            'config': asdict(config),
            'timestamp': time.time()
        })
        
        logger.info(f"Terminal session created: {session_id} (name: {name})")
        return session_id

    async def start_session(self, session_id: str) -> bool:
        """Start a terminal session with PTY.
        
        Args:
            session_id: The session ID
            
        Returns:
            True if successful, False otherwise
        """
        if session_id not in self.sessions:
            logger.error(f"Session not found: {session_id}")
            return False
        
        session = self.sessions[session_id]
        
        if session.state != TerminalState.CREATED:
            logger.error(f"Session {session_id} is not in CREATED state: {session.state}")
            return False
        
        try:
            session.state = TerminalState.STARTING
            
            # Create PTY
            logger.info(f"Creating PTY for session {session_id}")
            master_fd, slave_fd = pty.openpty()
            
            # Set terminal size
            try:
                fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, 
                          struct.pack('HHHH', session.config.rows, session.config.cols, 0, 0))
            except Exception as e:
                logger.warning(f"Could not set terminal size: {e}")
            
            # Configure terminal attributes
            try:
                attrs = termios.tcgetattr(slave_fd)
                attrs[3] &= ~termios.ICANON  # Disable canonical mode
                attrs[3] |= termios.ISIG     # Enable signal processing
                attrs[0] |= termios.ICRNL    # Map CR to NL on input
                attrs[1] |= termios.ONLCR    # Map NL to CR-NL on output
                attrs[6][termios.VMIN] = 1   # Minimum characters
                attrs[6][termios.VTIME] = 0  # Timeout
                termios.tcsetattr(slave_fd, termios.TCSANOW, attrs)
            except Exception as e:
                logger.warning(f"Could not set terminal attributes: {e}")
            
            # Prepare environment
            env = os.environ.copy()
            env.update({
                'TERM': session.config.term,
                'SHELL': session.config.shell,
                'HOME': os.path.expanduser('~'),
                'PATH': env.get('PATH', '/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin'),
                'LANG': 'C.UTF-8',
                'LC_ALL': 'C.UTF-8',
                'PS1': '\\[\\033[01;32m\\]\\u@\\h\\[\\033[00m\\]:\\[\\033[01;34m\\]\\w\\[\\033[00m\\]\\$ ',
                'USER': env.get('USER', 'app'),
                'LOGNAME': env.get('LOGNAME', 'app'),
            })
            env.update(session.config.env)
            
            # Find shell executable
            shell_path = self._find_shell(session.config.shell)
            if not shell_path:
                raise Exception(f"Shell not found: {session.config.shell}")
            
            # Prepare shell arguments
            shell_args = [shell_path]
            if session.config.startup_script and os.path.isfile(session.config.startup_script):
                shell_args.extend(["--rcfile", session.config.startup_script, "-i"])
            else:
                shell_args.extend(["-il"])
            
            # Start shell process
            def preexec():
                os.setsid()
                try:
                    fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
                except:
                    pass
            
            process = subprocess.Popen(
                shell_args,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                preexec_fn=preexec,
                env=env,
                cwd=session.config.cwd
            )
            
            # Close slave fd in parent process
            os.close(slave_fd)
            
            # Set master fd to non-blocking
            try:
                flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
                fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            except Exception as e:
                logger.warning(f"Could not set master fd to non-blocking: {e}")
            
            # Update session
            session.master_fd = master_fd
            session.process = process
            session.state = TerminalState.RUNNING
            session.last_activity = time.time()
            
            # Publish event
            await self.message_broker.publish('terminal.session_started', {
                'session_id': session_id,
                'pid': process.pid,
                'shell': shell_path,
                'cwd': session.config.cwd,
                'timestamp': time.time()
            })
            
            logger.info(f"Terminal session started: {session_id} (PID: {process.pid})")
            return True
            
        except Exception as e:
            session.state = TerminalState.ERROR
            logger.error(f"Error starting terminal session {session_id}: {e}")
            
            # Publish error event
            await self.message_broker.publish('terminal.session_error', {
                'session_id': session_id,
                'error': str(e),
                'timestamp': time.time()
            })
            
            return False

    async def stop_session(self, session_id: str) -> bool:
        """Stop a terminal session.
        
        Args:
            session_id: The session ID
            
        Returns:
            True if successful, False otherwise
        """
        if session_id not in self.sessions:
            logger.error(f"Session not found: {session_id}")
            return False
        
        session = self.sessions[session_id]
        
        try:
            # Cancel tasks
            if session.read_task:
                session.read_task.cancel()
                session.read_task = None
            if session.write_task:
                session.write_task.cancel()
                session.write_task = None
            
            # Close file descriptor
            if session.master_fd:
                try:
                    os.close(session.master_fd)
                except Exception as e:
                    logger.warning(f"Error closing master fd: {e}")
                session.master_fd = None
            
            # Terminate process
            if session.process and session.process.poll() is None:
                try:
                    # Send SIGTERM first
                    os.killpg(os.getpgid(session.process.pid), signal.SIGTERM)
                    
                    # Wait a bit, then force kill if needed
                    try:
                        session.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        os.killpg(os.getpgid(session.process.pid), signal.SIGKILL)
                        session.process.wait()
                except Exception as e:
                    logger.warning(f"Error terminating process: {e}")
                
                session.process = None
            
            # Update session state
            session.state = TerminalState.STOPPED
            
            # Publish event
            await self.message_broker.publish('terminal.session_stopped', {
                'session_id': session_id,
                'timestamp': time.time()
            })
            
            logger.info(f"Terminal session stopped: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping terminal session {session_id}: {e}")
            return False

    async def destroy_session(self, session_id: str) -> bool:
        """Destroy a terminal session and remove it.
        
        Args:
            session_id: The session ID
            
        Returns:
            True if successful, False otherwise
        """
        if session_id not in self.sessions:
            logger.error(f"Session not found: {session_id}")
            return False
        
        # Stop session first
        await self.stop_session(session_id)
        
        # Remove from sessions
        del self.sessions[session_id]
        self.stats['sessions_destroyed'] += 1
        
        # Remove websocket mapping
        websocket_ids_to_remove = [ws_id for ws_id, s_id in self.websocket_sessions.items() if s_id == session_id]
        for ws_id in websocket_ids_to_remove:
            del self.websocket_sessions[ws_id]
        
        # Publish event
        await self.message_broker.publish('terminal.session_destroyed', {
            'session_id': session_id,
            'timestamp': time.time()
        })
        
        logger.info(f"Terminal session destroyed: {session_id}")
        return True

    async def connect_websocket(self, websocket: WebSocket, session_id: str) -> bool:
        """Connect a WebSocket to a terminal session.
        
        Args:
            websocket: The WebSocket connection
            session_id: The session ID
            
        Returns:
            True if successful, False otherwise
        """
        if session_id not in self.sessions:
            logger.error(f"Session not found: {session_id}")
            return False
        
        session = self.sessions[session_id]
        
        if session.state != TerminalState.RUNNING:
            logger.error(f"Session {session_id} is not running: {session.state}")
            return False
        
        try:
            await websocket.accept()
            
            # Generate websocket ID
            websocket_id = str(uuid.uuid4())
            self.websocket_sessions[websocket_id] = session_id
            
            # Start I/O tasks
            session.read_task = asyncio.create_task(
                self._read_from_terminal(websocket, session)
            )
            session.write_task = asyncio.create_task(
                self._write_to_terminal(websocket, session)
            )
            
            # Publish event
            await self.message_broker.publish('terminal.websocket_connected', {
                'session_id': session_id,
                'websocket_id': websocket_id,
                'timestamp': time.time()
            })
            
            logger.info(f"WebSocket connected to terminal session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket to session {session_id}: {e}")
            return False

    async def disconnect_websocket(self, websocket_id: str):
        """Disconnect a WebSocket from a terminal session.
        
        Args:
            websocket_id: The WebSocket ID
        """
        if websocket_id not in self.websocket_sessions:
            return
        
        session_id = self.websocket_sessions[websocket_id]
        session = self.sessions.get(session_id)
        
        if session:
            # Cancel I/O tasks
            if session.read_task:
                session.read_task.cancel()
                session.read_task = None
            if session.write_task:
                session.write_task.cancel()
                session.write_task = None
        
        # Remove websocket mapping
        del self.websocket_sessions[websocket_id]
        
        # Publish event
        await self.message_broker.publish('terminal.websocket_disconnected', {
            'session_id': session_id,
            'websocket_id': websocket_id,
            'timestamp': time.time()
        })
        
        logger.info(f"WebSocket disconnected from terminal session: {session_id}")

    async def resize_terminal(self, session_id: str, cols: int, rows: int) -> bool:
        """Resize a terminal session.
        
        Args:
            session_id: The session ID
            cols: Number of columns
            rows: Number of rows
            
        Returns:
            True if successful, False otherwise
        """
        if session_id not in self.sessions:
            logger.error(f"Session not found: {session_id}")
            return False
        
        session = self.sessions[session_id]
        
        if session.state != TerminalState.RUNNING or not session.master_fd:
            logger.error(f"Session {session_id} is not running with valid fd")
            return False
        
        try:
            # Set terminal size
            fcntl.ioctl(session.master_fd, termios.TIOCSWINSZ, 
                       struct.pack('HHHH', rows, cols, 0, 0))
            
            # Update config
            session.config.cols = cols
            session.config.rows = rows
            session.last_activity = time.time()
            
            self.stats['resize_operations'] += 1
            
            # Publish event
            await self.message_broker.publish('terminal.session_resized', {
                'session_id': session_id,
                'cols': cols,
                'rows': rows,
                'timestamp': time.time()
            })
            
            logger.info(f"Terminal session resized: {session_id} ({cols}x{rows})")
            return True
            
        except Exception as e:
            logger.error(f"Error resizing terminal session {session_id}: {e}")
            return False

    async def send_input(self, session_id: str, data: str) -> bool:
        """Send input to a terminal session.
        
        Args:
            session_id: The session ID
            data: Input data
            
        Returns:
            True if successful, False otherwise
        """
        if session_id not in self.sessions:
            logger.error(f"Session not found: {session_id}")
            return False
        
        session = self.sessions[session_id]
        
        if session.state != TerminalState.RUNNING or not session.master_fd:
            logger.error(f"Session {session_id} is not running with valid fd")
            return False
        
        try:
            # Write data to terminal
            os.write(session.master_fd, data.encode('utf-8'))
            
            # Update statistics
            self.stats['total_input_bytes'] += len(data.encode('utf-8'))
            session.last_activity = time.time()
            
            # Publish event
            await self.message_broker.publish('terminal.input_sent', {
                'session_id': session_id,
                'data_length': len(data),
                'timestamp': time.time()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending input to session {session_id}: {e}")
            return False

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a terminal session.
        
        Args:
            session_id: The session ID
            
        Returns:
            Session information or None if not found
        """
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        return session.to_dict()

    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all terminal sessions.
        
        Returns:
            List of session information
        """
        return [session.to_dict() for session in self.sessions.values()]

    async def get_stats(self) -> Dict[str, Any]:
        """Get terminal service statistics.
        
        Returns:
            Dictionary containing service statistics
        """
        return {
            **self.stats,
            'active_sessions': len(self.sessions),
            'websocket_connections': len(self.websocket_sessions),
            'max_sessions': self.max_sessions,
            'session_timeout': self.session_timeout,
            'timestamp': time.time()
        }

    def _find_shell(self, shell_path: str) -> Optional[str]:
        """Find the shell executable.
        
        Args:
            shell_path: Path to shell executable
            
        Returns:
            Full path to shell or None if not found
        """
        # If full path is provided, only check that specific path
        if shell_path.startswith('/'):
            if os.path.exists(shell_path):
                return shell_path
            else:
                return None
        
        # Otherwise check default paths
        for path in self.shell_paths:
            if os.path.exists(path):
                return path
        
        return None

    async def _read_from_terminal(self, websocket: WebSocket, session: TerminalSession):
        """Read from terminal and send to WebSocket.
        
        Args:
            websocket: The WebSocket connection
            session: The terminal session
        """
        try:
            while session.state == TerminalState.RUNNING and session.master_fd:
                try:
                    # Use select with low timeout for responsiveness
                    ready, _, _ = select.select([session.master_fd], [], [], 0.001)
                    if ready:
                        # Read available data
                        data = os.read(session.master_fd, 8192)
                        if data:
                            # Decode terminal data
                            try:
                                decoded_data = data.decode('utf-8')
                            except UnicodeDecodeError:
                                decoded_data = data.decode('latin-1')
                            
                            # Send to WebSocket
                            await websocket.send_text(decoded_data)
                            
                            # Update statistics
                            self.stats['total_output_bytes'] += len(data)
                            session.last_activity = time.time()
                            
                            # Publish event
                            await self.message_broker.publish('terminal.output_sent', {
                                'session_id': session.id,
                                'data_length': len(data),
                                'timestamp': time.time()
                            })
                        else:
                            # EOF reached
                            break
                    else:
                        # No data available, yield control
                        await asyncio.sleep(0.001)
                        
                except Exception as e:
                    logger.error(f"Error reading from terminal {session.id}: {e}")
                    break
                    
        except asyncio.CancelledError:
            logger.info(f"Read task cancelled for session {session.id}")
        except Exception as e:
            logger.error(f"Unexpected error in read task for session {session.id}: {e}")

    async def _write_to_terminal(self, websocket: WebSocket, session: TerminalSession):
        """Read from WebSocket and write to terminal.
        
        Args:
            websocket: The WebSocket connection
            session: The terminal session
        """
        try:
            while session.state == TerminalState.RUNNING and session.master_fd:
                try:
                    data = await websocket.receive_text()
                    
                    # Handle special messages
                    if data.startswith('{"type":'):
                        message = json.loads(data)
                        if message.get('type') == 'resize':
                            cols = message.get('cols', 80)
                            rows = message.get('rows', 24)
                            await self.resize_terminal(session.id, cols, rows)
                        continue
                    
                    # Regular terminal input
                    await self.send_input(session.id, data)
                    
                except Exception as e:
                    logger.error(f"Error writing to terminal {session.id}: {e}")
                    break
                    
        except asyncio.CancelledError:
            logger.info(f"Write task cancelled for session {session.id}")
        except Exception as e:
            logger.error(f"Unexpected error in write task for session {session.id}: {e}")

    async def _handle_terminal_event(self, message):
        """Handle terminal-related events.
        
        Args:
            message: Message object containing topic and payload
        """
        try:
            topic = message.topic
            data = message.payload
            
            if topic == 'terminal.create_session':
                session_id = await self.create_session(
                    name=data.get('name'),
                    config=TerminalConfig(**data.get('config', {}))
                )
                await self.message_broker.publish('terminal.session_created_response', {
                    'session_id': session_id,
                    'request_id': data.get('request_id'),
                    'timestamp': time.time()
                })
            
            elif topic == 'terminal.start_session':
                session_id = data.get('session_id')
                success = await self.start_session(session_id)
                await self.message_broker.publish('terminal.session_started_response', {
                    'session_id': session_id,
                    'success': success,
                    'request_id': data.get('request_id'),
                    'timestamp': time.time()
                })
            
            elif topic == 'terminal.stop_session':
                session_id = data.get('session_id')
                success = await self.stop_session(session_id)
                await self.message_broker.publish('terminal.session_stopped_response', {
                    'session_id': session_id,
                    'success': success,
                    'request_id': data.get('request_id'),
                    'timestamp': time.time()
                })
            
            elif topic == 'terminal.destroy_session':
                session_id = data.get('session_id')
                success = await self.destroy_session(session_id)
                await self.message_broker.publish('terminal.session_destroyed_response', {
                    'session_id': session_id,
                    'success': success,
                    'request_id': data.get('request_id'),
                    'timestamp': time.time()
                })
            
            elif topic == 'terminal.list_sessions':
                sessions = await self.list_sessions()
                await self.message_broker.publish('terminal.sessions_listed', {
                    'sessions': sessions,
                    'request_id': data.get('request_id'),
                    'timestamp': time.time()
                })
            
            elif topic == 'terminal.get_stats':
                stats = await self.get_stats()
                await self.message_broker.publish('terminal.stats_retrieved', {
                    'stats': stats,
                    'request_id': data.get('request_id'),
                    'timestamp': time.time()
                })
                
        except Exception as e:
            logger.error(f"Error handling terminal event {topic}: {e}")

    async def _handle_connection_disconnected(self, message):
        """Handle connection disconnected events.
        
        Args:
            message: Message object containing topic and payload
        """
        try:
            data = message.payload
            connection_id = data.get('connection_id')
            if connection_id in self.websocket_sessions:
                await self.disconnect_websocket(connection_id)
                
        except Exception as e:
            logger.error(f"Error handling connection disconnected event: {e}")

    async def _cleanup_sessions_task(self):
        """Background task to cleanup inactive sessions."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                current_time = time.time()
                sessions_to_cleanup = []
                
                for session_id, session in self.sessions.items():
                    # Check for timeout
                    if current_time - session.last_activity > self.session_timeout:
                        sessions_to_cleanup.append(session_id)
                    
                    # Check if process is still alive
                    if session.process and session.process.poll() is not None:
                        sessions_to_cleanup.append(session_id)
                
                # Cleanup sessions
                for session_id in sessions_to_cleanup:
                    logger.info(f"Cleaning up inactive session: {session_id}")
                    await self.destroy_session(session_id)
                    
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")


async def get_terminal_service() -> TerminalService:
    """Get the global terminal service instance.
    
    Returns:
        The terminal service instance
    """
    global _terminal_service
    if _terminal_service is None:
        _terminal_service = TerminalService()
        await _terminal_service.initialize()
    return _terminal_service


async def shutdown_terminal_service():
    """Shutdown the global terminal service instance."""
    global _terminal_service
    if _terminal_service is not None:
        await _terminal_service.shutdown()
        _terminal_service = None
