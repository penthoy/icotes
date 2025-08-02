"""
Command Handlers for icpy CLI

This module provides handlers for different CLI commands, implementing the actual
business logic for file operations, terminal management, and workspace operations.

Key Features:
- File operation handlers (open, save, list, etc.)
- Terminal management handlers (create, input, list, etc.)
- Workspace operation handlers (create, switch, list, etc.)
- Interactive mode handlers for continuous operation
- Error handling and user feedback

Author: GitHub Copilot
Date: July 16, 2025
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from .http_client import HttpClient, CliConfig

logger = logging.getLogger(__name__)


class CommandHandlers:
    """
    Command handlers for icpy CLI operations
    
    Provides methods for handling different CLI commands including file operations,
    terminal management, and workspace operations.
    """
    
    def __init__(self, config: CliConfig):
        """
        Initialize command handlers with configuration
        
        Args:
            config: CLI configuration object
        """
        self.config = config
        self.client = HttpClient(config)
        self.current_workspace_id = None
    
    def handle_file_open(self, file_path: str, workspace_id: Optional[str] = None) -> bool:
        """
        Handle file open command
        
        Args:
            file_path: Path to file to open
            workspace_id: Optional workspace ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert relative path to absolute
            abs_path = os.path.abspath(file_path)
            
            # Check if file exists
            if not os.path.exists(abs_path):
                print(f"Error: File does not exist: {abs_path}")
                return False
            
            # Check backend connection
            if not self.client.check_connection():
                print("Error: Cannot connect to icpy backend. Make sure the backend is running.")
                return False
            
            # Open file via REST API
            result = self.client.open_file(abs_path, workspace_id or self.current_workspace_id)
            
            if self.config.verbose:
                print(f"File opened successfully: {abs_path}")
                print(f"Result: {json.dumps(result, indent=2)}")
            else:
                print(f"Opened: {abs_path}")
            
            return True
            
        except Exception as e:
            print(f"Error opening file: {e}")
            if self.config.verbose:
                logger.exception("File open failed")
            return False
    
    def handle_terminal_create(self, workspace_id: Optional[str] = None) -> bool:
        """
        Handle terminal creation command
        
        Args:
            workspace_id: Optional workspace ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check backend connection
            if not self.client.check_connection():
                print("Error: Cannot connect to icpy backend. Make sure the backend is running.")
                return False
            
            # Create terminal via REST API
            result = self.client.create_terminal(workspace_id or self.current_workspace_id)
            
            terminal_id = result.get('terminal_id')
            if terminal_id:
                print(f"Terminal created: {terminal_id}")
                if self.config.verbose:
                    print(f"Terminal info: {json.dumps(result, indent=2)}")
            else:
                print("Error: Failed to create terminal")
                return False
            
            return True
            
        except Exception as e:
            print(f"Error creating terminal: {e}")
            if self.config.verbose:
                logger.exception("Terminal creation failed")
            return False
    
    def handle_terminal_list(self) -> bool:
        """
        Handle terminal list command
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check backend connection
            if not self.client.check_connection():
                print("Error: Cannot connect to icpy backend. Make sure the backend is running.")
                return False
            
            # Get terminal list via REST API
            terminals = self.client.get_terminal_list()
            
            if not terminals:
                print("No active terminals found.")
                return True
            
            print(f"Active terminals ({len(terminals)}):")
            for terminal in terminals:
                terminal_id = terminal.get('id', 'unknown')
                status = terminal.get('state', 'unknown')
                name = terminal.get('name', 'unnamed')
                pid = terminal.get('pid', 'N/A')
                print(f"  {terminal_id} ({name}) - Status: {status}, PID: {pid}")
            
            return True
            
        except Exception as e:
            print(f"Error listing terminals: {e}")
            if self.config.verbose:
                logger.exception("Terminal listing failed")
            return False
    
    def handle_workspace_list(self) -> bool:
        """
        Handle workspace list command
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check backend connection
            if not self.client.check_connection():
                print("Error: Cannot connect to icpy backend. Make sure the backend is running.")
                return False
            
            # Get workspace list via REST API
            workspaces = self.client.get_workspace_list()
            
            if not workspaces:
                print("No workspaces found.")
                return True
            
            print(f"Available workspaces ({len(workspaces)}):")
            for workspace in workspaces:
                workspace_id = workspace.get('workspace_id', 'unknown')
                name = workspace.get('name', 'Unnamed')
                active = workspace.get('active', False)
                status = " (active)" if active else ""
                print(f"  {workspace_id} - {name}{status}")
            
            return True
            
        except Exception as e:
            print(f"Error listing workspaces: {e}")
            if self.config.verbose:
                logger.exception("Workspace listing failed")
            return False
    
    def handle_workspace_info(self, workspace_id: str) -> bool:
        """
        Handle workspace info command
        
        Args:
            workspace_id: Workspace ID to get info for
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check backend connection
            if not self.client.check_connection():
                print("Error: Cannot connect to icpy backend. Make sure the backend is running.")
                return False
            
            # Get workspace info via REST API
            workspace_info = self.client.get_workspace_info(workspace_id)
            
            print(f"Workspace: {workspace_id}")
            print(f"Name: {workspace_info.get('name', 'Unknown')}")
            print(f"Status: {workspace_info.get('status', 'Unknown')}")
            
            # Show open files
            files = workspace_info.get('files', [])
            if files:
                print(f"Open files ({len(files)}):")
                for file_info in files:
                    file_path = file_info.get('path', 'Unknown')
                    modified = " (modified)" if file_info.get('modified', False) else ""
                    print(f"  {file_path}{modified}")
            else:
                print("No open files.")
            
            # Show active terminals
            terminals = workspace_info.get('terminals', [])
            if terminals:
                print(f"Active terminals ({len(terminals)}):")
                for terminal_info in terminals:
                    terminal_id = terminal_info.get('terminal_id', 'Unknown')
                    status = terminal_info.get('status', 'Unknown')
                    print(f"  {terminal_id} - Status: {status}")
            else:
                print("No active terminals.")
            
            return True
            
        except Exception as e:
            print(f"Error getting workspace info: {e}")
            if self.config.verbose:
                logger.exception("Workspace info failed")
            return False
    
    def handle_file_list(self, dir_path: str = ".") -> bool:
        """
        Handle file list command
        
        Args:
            dir_path: Directory path to list
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert relative path to absolute
            abs_path = os.path.abspath(dir_path)
            
            # Check if directory exists
            if not os.path.exists(abs_path):
                print(f"Error: Directory does not exist: {abs_path}")
                return False
            
            # Check backend connection
            if not self.client.check_connection():
                print("Error: Cannot connect to icpy backend. Make sure the backend is running.")
                return False
            
            # List directory via REST API
            contents = self.client.list_directory(abs_path)
            
            if not contents:
                print(f"Directory is empty: {abs_path}")
                return True
            
            print(f"Contents of {abs_path}:")
            for item in contents:
                item_name = item.get('name', 'Unknown')
                item_type = item.get('type', 'unknown')
                size = item.get('size', 0)
                
                if item_type == 'directory':
                    print(f"  {item_name}/")
                else:
                    print(f"  {item_name} ({size} bytes)")
            
            return True
            
        except Exception as e:
            print(f"Error listing directory: {e}")
            if self.config.verbose:
                logger.exception("Directory listing failed")
            return False
    
    def handle_status(self) -> bool:
        """
        Handle status command - show backend and connection status
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("icpy CLI Status")
            print("===============")
            print(f"Backend URL: {self.config.backend_url}")
            print(f"Timeout: {self.config.timeout}s")
            print(f"Verbose: {self.config.verbose}")
            
            # Check backend connection
            if self.client.check_connection():
                print("Backend: Connected ✓")
                
                # Try to get some basic info
                try:
                    workspaces = self.client.get_workspace_list()
                    print(f"Workspaces: {len(workspaces)} available")
                    
                    terminals = self.client.get_terminal_list()
                    print(f"Terminals: {len(terminals)} active")
                    
                except Exception as e:
                    print(f"Backend: Connected but API error: {e}")
                    return False
            else:
                print("Backend: Disconnected ✗")
                return False
            
            return True
            
        except Exception as e:
            print(f"Error checking status: {e}")
            if self.config.verbose:
                logger.exception("Status check failed")
            return False
    
    def handle_interactive_mode(self) -> bool:
        """
        Handle interactive mode - continuous CLI operation
        
        Returns:
            bool: True if successful, False otherwise
        """
        print("Entering interactive mode. Type 'help' for commands, 'exit' to quit.")
        
        while True:
            try:
                command = input("icpy> ").strip()
                
                if not command:
                    continue
                
                if command.lower() in ['exit', 'quit']:
                    print("Goodbye!")
                    break
                
                if command.lower() == 'help':
                    self._show_interactive_help()
                    continue
                
                # Parse and execute command
                parts = command.split()
                if not parts:
                    continue
                
                cmd = parts[0].lower()
                args = parts[1:]
                
                if cmd == 'open' and args:
                    self.handle_file_open(args[0])
                elif cmd == 'terminal':
                    if args and args[0] == 'create':
                        self.handle_terminal_create()
                    elif args and args[0] == 'list':
                        self.handle_terminal_list()
                    else:
                        print("Usage: terminal create|list")
                elif cmd == 'workspace':
                    if args and args[0] == 'list':
                        self.handle_workspace_list()
                    elif args and args[0] == 'info' and len(args) > 1:
                        self.handle_workspace_info(args[1])
                    else:
                        print("Usage: workspace list|info <workspace_id>")
                elif cmd == 'list':
                    dir_path = args[0] if args else "."
                    self.handle_file_list(dir_path)
                elif cmd == 'status':
                    self.handle_status()
                else:
                    print(f"Unknown command: {cmd}. Type 'help' for available commands.")
                
            except KeyboardInterrupt:
                print("\nUse 'exit' to quit.")
                continue
            except EOFError:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
                if self.config.verbose:
                    logger.exception("Interactive command failed")
        
        return True
    
    def _show_interactive_help(self) -> None:
        """Show help for interactive mode commands"""
        help_text = """
Available commands:
  open <file>              Open a file in the editor
  terminal create          Create a new terminal
  terminal list            List active terminals
  workspace list           List available workspaces
  workspace info <id>      Show workspace information
  list [directory]         List directory contents
  status                   Show backend connection status
  help                     Show this help message
  exit                     Exit interactive mode
        """
        print(help_text.strip())
    
    def cleanup(self) -> None:
        """
        Cleanup resources and close connections
        """
        if self.client:
            self.client.close()
