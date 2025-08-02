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
from typing import Dict, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class TerminalManager:
    """Manages terminal sessions and PTY connections"""
    
    def __init__(self):
        self.terminal_connections: Dict[str, Dict] = {}
    
    async def connect_terminal(self, websocket: WebSocket, terminal_id: str):
        """Create a new terminal session with PTY support"""
        try:
            await websocket.accept()
            
            # Debug logging for production troubleshooting
            logger.info(f"WebSocket client: {websocket.client}")
            logger.info(f"WebSocket headers: {websocket.headers}")
            
            # Create a new terminal session
            logger.info(f"Creating PTY for terminal {terminal_id}")
            master_fd, slave_fd = pty.openpty()
            logger.info(f"PTY created: master_fd={master_fd}, slave_fd={slave_fd}")
            
            # Set terminal size (default to 80x24 if not specified)
            try:
                fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
            except Exception as e:
                logger.warning(f"Could not set terminal size: {e}")
            
            # Set terminal attributes for maximum responsiveness and low latency
            try:
                attrs = termios.tcgetattr(slave_fd)
                # Disable canonical mode for character-by-character input
                attrs[3] &= ~termios.ICANON  # Disable canonical mode
                attrs[3] |= termios.ISIG  # Enable signal processing (keep Ctrl+C, etc.)
                # Removed line disabling kernel echo; we will now rely on the backend PTY to echo characters
                # attrs[3] &= ~termios.ECHO
                # Set input/output processing for low latency
                attrs[0] |= termios.ICRNL  # Map CR to NL on input
                attrs[1] |= termios.ONLCR  # Map NL to CR-NL on output
                # Configure for immediate response with zero latency
                attrs[6][termios.VMIN] = 1  # Minimum characters (1 for immediate processing)
                attrs[6][termios.VTIME] = 0  # Timeout (0 for immediate return)
                termios.tcsetattr(slave_fd, termios.TCSANOW, attrs)
            except Exception as e:
                logger.warning(f"Could not set terminal attributes: {e}")
            
            # Set environment variables for proper login shell behavior
            env = os.environ.copy()
            
            # Get current working directory for icotes paths
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            clipboard_path = os.path.join(current_dir, 'icotes-clipboard')
            startup_script = os.path.join(current_dir, 'backend', 'terminal_startup.sh')
            # CRITICAL FIX: Use custom inputrc for proper arrow key handling
            inputrc_path = os.path.join(current_dir, 'backend', '.inputrc')
            
            env.update({
                'TERM': 'xterm-256color',  # Critical for colors and many commands
                'SHELL': '/bin/bash',
                'HOME': os.path.expanduser('~'),
                'PATH': env.get('PATH', '/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin'),
                'LANG': 'C.UTF-8',
                'LC_ALL': 'C.UTF-8',
                'PS1': '\\[\\033[01;32m\\]\\u@\\h\\[\\033[00m\\]:\\[\\033[01;34m\\]\\w\\[\\033[00m\\]\\$ ',
                'USER': env.get('USER', os.getlogin() if hasattr(os, 'getlogin') else 'app'),
                'LOGNAME': env.get('LOGNAME', os.getlogin() if hasattr(os, 'getlogin') else 'app'),
                # Force loading of user's profile and aliases
                'BASH_ENV': os.path.expanduser('~/.bashrc'),
                # Add icotes clipboard path for immediate availability
                'ICOTES_CLIPBOARD_PATH': clipboard_path,
                # Set startup script for terminal initialization
                'ICOTES_STARTUP_SCRIPT': startup_script,
                # CRITICAL FIX: Use custom inputrc with arrow key bindings
                'INPUTRC': inputrc_path,
            })
            
            # Find bash executable
            bash_path = None
            for path in ['/bin/bash', '/usr/bin/bash', '/usr/local/bin/bash']:
                if os.path.exists(path):
                    bash_path = path
                    break
            
            if not bash_path:
                raise Exception("Bash executable not found")
                
            logger.info(f"Using bash at: {bash_path}")
            logger.info(f"Starting login shell with TERM={env.get('TERM')}")
            
            # Start bash as a login shell (-l) and interactive (-i)
            # This ensures all startup files are loaded and aliases are available
            def preexec():
                # Set the process group and controlling terminal
                os.setsid()
                # Set the controlling terminal
                try:
                    import fcntl
                    fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
                except:
                    pass
            
            # After determining startup_script, ensure it is a valid, readable file before passing it to bash. This prevents cases where an empty
            # or invalid string (e.g. "--") could be interpreted by bash as a CLI argument and cause it to exit with the
            # "--: invalid option" error that was reported from the frontend terminal.
            if os.path.isfile(startup_script):
                bash_args = [bash_path, "--rcfile", startup_script, "-i"]
            else:
                # Fallback to a plain interactive shell – we still pass -l so that the user's normal
                # startup files ( /etc/profile, ~/.bash_profile, ~/.bashrc ) are loaded.
                logger.warning(f"Startup script '{startup_script}' not found – launching bash without --rcfile")
                bash_args = [bash_path, "-il"]  # -i interactive, -l login

            logger.info(f"Starting bash with args: {bash_args}")

            # Spawn bash process using the constructed arguments
            proc = subprocess.Popen(
                bash_args,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                preexec_fn=preexec,
                env=env,
                cwd=os.path.expanduser('~')
            )
            logger.info(f"Bash process started with PID: {proc.pid}")
            
            # Close slave fd in parent process
            os.close(slave_fd)
            
            # Set master fd to non-blocking for better performance
            try:
                flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
                fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            except Exception as e:
                logger.warning(f"Could not set master fd to non-blocking: {e}")
            
            # Store terminal connection info
            self.terminal_connections[terminal_id] = {
                'websocket': websocket,
                'master_fd': master_fd,
                'process': proc,
                'read_task': None,
                'write_task': None
            }
            
            logger.info(f"Terminal connection established: {terminal_id}")
            return master_fd, proc
            
        except Exception as e:
            logger.error(f"Error creating terminal session: {e}")
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
                    os.write(master_fd, data.encode('utf-8'))
                except BlockingIOError:
                    # Handle non-blocking write with minimal backoff for responsiveness
                    await asyncio.sleep(0.001)  # 1ms backoff for maximum responsiveness
                    try:
                        os.write(master_fd, data.encode('utf-8'))
                    except:
                        pass
            except Exception as e:
                logger.error(f"Error writing to terminal: {e}")
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