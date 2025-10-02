"""
Terminal Module for icotes Backend
Handles PTY-based terminal sessions with WebSocket communication
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
import getpass
import pwd
from typing import Dict, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class TerminalManager:
    """Manages terminal sessions and PTY connections"""
    
    def __init__(self):
        self.terminal_connections: Dict[str, Dict] = {}
    
    async def connect_terminal(self, websocket: WebSocket, terminal_id: str, already_accepted: bool = False):
        """Create a new terminal session with PTY support"""
        try:
            if not already_accepted:
                await websocket.accept()
            logger.info(f"[TERM] Connection start terminal_id={terminal_id} client={websocket.client}")
            logger.info(f"[TERM] Headers: {dict(websocket.headers)}")

            # Create PTY
            master_fd, slave_fd = pty.openpty()
            logger.info(f"[TERM] PTY created master={master_fd} slave={slave_fd}")

            # Detect docker (keep extremely simple now)
            is_docker = os.path.exists('/.dockerenv') or os.environ.get('container') == 'docker'
            logger.info(f"[TERM] Docker detected={is_docker}")

            # Determine workspace root from environment variable or default
            workspace_root = os.environ.get('WORKSPACE_ROOT')
            if not workspace_root:
                if is_docker:
                    # In Docker, default to /app/workspace
                    workspace_root = '/app/workspace'
                else:
                    # In development, default to ~/workspace or project workspace
                    project_root = os.path.dirname(os.path.abspath(__file__ + '/../..'))
                    workspace_root = os.path.join(project_root, 'workspace')
                    # Fallback to home directory if workspace doesn't exist
                    if not os.path.exists(workspace_root):
                        workspace_root = os.path.expanduser('~')
            
            # Ensure workspace directory exists and is accessible
            if not os.path.exists(workspace_root):
                logger.warning(f"[TERM] Workspace root {workspace_root} doesn't exist, creating it")
                try:
                    os.makedirs(workspace_root, exist_ok=True)
                except Exception as e:
                    logger.error(f"[TERM] Failed to create workspace root {workspace_root}: {e}")
                    # Fallback to home directory
                    workspace_root = os.path.expanduser('~') if not is_docker else '/app/backend'
            
            logger.info(f"[TERM] Using workspace root: {workspace_root}")

            # If docker: use minimal safe path that we verified manually works
            if is_docker:
                try:
                    logger.info("[TERM][DOCKER] Using improved spawn path with controlling TTY & login shell")
                    # Determine proper HOME so bash can load rc files (aliases like ll)
                    try:
                        home_dir = pwd.getpwuid(os.getuid()).pw_dir
                    except Exception:
                        home_dir = os.environ.get('HOME', '/root')
                    env = os.environ.copy()
                    env.setdefault('TERM', 'xterm-256color')
                    env['HOME'] = home_dir
                    # Preexec to create new session & set controlling tty to enable job control
                    def preexec():
                        try:
                            os.setsid()
                        except Exception:
                            pass
                        try:
                            fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
                        except Exception:
                            # If this fails we will just run without job control
                            pass
                    # Use login + interactive shell so /etc/profile & bashrc load (provides aliases like ll)
                    proc = subprocess.Popen(
                        ['/bin/bash', '-il'],
                        stdin=slave_fd,
                        stdout=slave_fd,
                        stderr=slave_fd,
                        preexec_fn=preexec,
                        env=env,
                        cwd=workspace_root  # Use workspace root instead of hardcoded /app/backend
                    )
                    logger.info(f"[TERM][DOCKER] Bash started pid={proc.pid} home={home_dir} cwd={workspace_root}")
                except Exception:
                    logger.exception("[TERM][DOCKER] Improved spawn failed, falling back to minimal path")
                    try:
                        proc = subprocess.Popen(
                            ['/bin/bash', '-i'],
                            stdin=slave_fd,
                            stdout=slave_fd,
                            stderr=slave_fd,
                            preexec_fn=None,
                            env={'TERM': 'xterm-256color', 'HOME': '/home/icotes', 'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')},
                            cwd=workspace_root,  # Use workspace root instead of hardcoded /app/backend
                            start_new_session=False
                        )
                    except Exception:
                        logger.exception("[TERM][DOCKER] Minimal fallback spawn failed")
                        raise
            else:
                # Non-docker (retain richer configuration)
                try:
                    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
                except Exception:
                    logger.exception("[TERM] Failed to set window size (non-docker)")
                try:
                    attrs = termios.tcgetattr(slave_fd)
                    attrs[3] &= ~termios.ICANON
                    attrs[3] |= termios.ISIG | termios.ECHO
                    attrs[6][termios.VMIN] = 1
                    attrs[6][termios.VTIME] = 0
                    termios.tcsetattr(slave_fd, termios.TCSANOW, attrs)
                except Exception:
                    logger.exception("[TERM] Failed to set term attrs (non-docker)")
                def preexec():
                    os.setsid()
                    try:
                        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
                    except Exception:
                        pass
                proc = subprocess.Popen(
                    ['/bin/bash', '-il'],
                    stdin=slave_fd,
                    stdout=slave_fd,
                    stderr=slave_fd,
                    preexec_fn=preexec,
                    env=os.environ.copy() | {'TERM': 'xterm-256color'},
                    cwd=workspace_root  # Use workspace root instead of expanduser('~')
                )
                logger.info(f"[TERM] Bash started pid={proc.pid} cwd={workspace_root}")

            # Close slave in parent
            os.close(slave_fd)

            # Non-blocking master
            try:
                flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
                fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            except Exception:
                logger.exception("[TERM] Failed to set non-blocking master fd")

            self.terminal_connections[terminal_id] = {
                'websocket': websocket,
                'master_fd': master_fd,
                'process': proc,
                'read_task': None,
                'write_task': None
            }
            logger.info(f"[TERM] Terminal ready terminal_id={terminal_id}")
            return master_fd, proc
        except Exception as e:
            logger.exception(f"[TERM] Error creating terminal session id={terminal_id}")
            raise e

    def disconnect_terminal(self, terminal_id: str):
        """Clean up terminal connection and resources"""
        if terminal_id in self.terminal_connections:
            conn = self.terminal_connections[terminal_id]
            
            # Cancel tasks
            if conn['read_task']:
                conn['read_task'].cancel()
            if conn['write_task']:
                conn['write_task'].cancel()
            
            # Close file descriptor
            try:
                os.close(conn['master_fd'])
            except Exception as e:
                logger.warning(f"Error closing master fd: {e}")
            
            # Terminate process
            try:
                if conn['process'] and conn['process'].poll() is None:
                    # Send SIGTERM first
                    os.killpg(os.getpgid(conn['process'].pid), signal.SIGTERM)
                    
                    # Wait a bit, then force kill if needed
                    try:
                        conn['process'].wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        os.killpg(os.getpgid(conn['process'].pid), signal.SIGKILL)
                        conn['process'].wait()
            except Exception as e:
                logger.warning(f"Error terminating process: {e}")
            
            # Remove from connections
            del self.terminal_connections[terminal_id]
            logger.info(f"Terminal connection cleaned up: {terminal_id}")

    async def read_from_terminal(self, websocket: WebSocket, master_fd: int):
        """Read from terminal and send to WebSocket with optimized performance"""
        while True:
            try:
                # Use select with very low timeout for maximum responsiveness
                ready, _, _ = select.select([master_fd], [], [], 0.001)  # 1ms timeout for responsiveness
                if ready:
                    # Read available data with larger buffer for better performance
                    data = os.read(master_fd, 8192)  # Doubled buffer size
                    if data:
                        # Properly decode terminal data with better error handling
                        try:
                            decoded_data = data.decode('utf-8')
                        except UnicodeDecodeError:
                            # Fallback to latin-1 for binary data
                            decoded_data = data.decode('latin-1')
                        
                        # Send data to WebSocket immediately without buffering
                        try:
                            await websocket.send_text(decoded_data)
                        except Exception as send_error:
                            logger.error(f"Error sending data to WebSocket: {send_error}")
                            break
                    else:
                        # EOF reached
                        break
                else:
                    # No data available, yield control with minimal delay for responsiveness
                    await asyncio.sleep(0.001)  # 1ms sleep for maximum responsiveness
            except Exception as e:
                logger.error(f"Error reading from terminal: {e}")
                break

    async def write_to_terminal(self, websocket: WebSocket, master_fd: int):
        """Read from WebSocket and write to terminal with optimized performance"""
        while True:
            try:
                data = await websocket.receive_text()
                
                # Handle special messages
                if data.startswith('{"type":'):
                    message = json.loads(data)
                    if message.get('type') == 'resize':
                        # Handle terminal resize
                        cols = message.get('cols', 80)
                        rows = message.get('rows', 24)
                        try:
                            # Set terminal size
                            fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
                            logger.info(f"Terminal resized to {cols}x{rows}")
                        except Exception as e:
                            logger.error(f"Error resizing terminal: {e}")
                    continue
                
                # Regular terminal input - write directly for maximum performance
                try:
                    bytes_written = os.write(master_fd, data.encode('utf-8'))
                except BlockingIOError as e:
                    # Handle non-blocking write with minimal backoff for responsiveness
                    await asyncio.sleep(0.001)  # 1ms backoff for maximum responsiveness
                    try:
                        bytes_written = os.write(master_fd, data.encode('utf-8'))
                    except Exception as retry_error:
                        logger.error(f"Retry failed: {retry_error}")
                        pass
                except OSError as e:
                    logger.error(f"OSError writing to terminal: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error writing to terminal: {e}")
            except Exception as e:
                logger.error(f"Error in write_to_terminal loop: {e}")
                break

    def get_terminal_health(self) -> Dict[str, Any]:
        """Get terminal system health information"""
        try:
            # Test if PTY is available
            try:
                master_fd, slave_fd = pty.openpty()
                os.close(master_fd)
                os.close(slave_fd)
                pty_available = True
            except Exception:
                pty_available = False
            
            # Test if bash is available
            bash_available = any(os.path.exists(path) for path in ['/bin/bash', '/usr/bin/bash', '/usr/local/bin/bash'])
            
            return {
                "status": "healthy",
                "pty_available": pty_available,
                "bash_available": bash_available,
                "terminal_connections": len(self.terminal_connections)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "pty_available": False,
                "bash_available": False,
                "terminal_connections": len(self.terminal_connections)
            }


# Global terminal manager instance
terminal_manager = TerminalManager()