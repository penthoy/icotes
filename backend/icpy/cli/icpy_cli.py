"""
icpy CLI - Command Line Interface for icpy Backend

This module provides the main CLI interface for interacting with the icpy backend,
enabling external tools and AI agents to interact with the editor through CLI commands.

Key Features:
- File operations (open, save, list)
- Terminal management (create, list, input)
- Workspace operations (create, switch, list)
- Interactive mode for continuous operation
- Integration with icpy backend REST API
- Support for AI tool integration

Usage:
  icpy file.py                    # Open file in editor
  icpy --terminal                 # Create new terminal
  icpy --workspace list           # List workspaces
  icpy --interactive              # Enter interactive mode
  icpy --help                     # Show help

Author: GitHub Copilot
Date: July 16, 2025
"""

import argparse
import logging
import os
import sys
from typing import List, Optional

from .http_client import CliConfig
from .command_handlers import CommandHandlers

logger = logging.getLogger(__name__)


class IcpyCLI:
    """
    Main CLI class for icpy command-line interface
    
    Handles argument parsing, command routing, and overall CLI operation.
    """
    
    def __init__(self):
        """Initialize CLI with default configuration"""
        self.config = CliConfig()
        self.handlers = None
    
    def setup_logging(self, verbose: bool = False) -> None:
        """
        Set up logging configuration
        
        Args:
            verbose: Enable verbose logging
        """
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def create_parser(self) -> argparse.ArgumentParser:
        """
        Create argument parser for CLI
        
        Returns:
            Configured argument parser
        """
        parser = argparse.ArgumentParser(
            prog='icpy',
            description='Command-line interface for icpy backend',
            epilog='Examples:\n'
                   '  icpy file.py          # Open file in editor\n'
                   '  icpy --terminal       # Create new terminal\n'
                   '  icpy --workspace list # List workspaces\n'
                   '  icpy --interactive    # Enter interactive mode',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # File operations
        parser.add_argument(
            'file',
            nargs='?',
            help='File to open in editor'
        )
        
        # Terminal operations
        parser.add_argument(
            '--terminal',
            action='store_true',
            help='Create a new terminal session'
        )
        
        parser.add_argument(
            '--terminal-list',
            action='store_true',
            help='List active terminal sessions'
        )
        
        # Workspace operations
        parser.add_argument(
            '--workspace',
            choices=['list', 'info', 'create'],
            help='Workspace operations'
        )
        
        parser.add_argument(
            '--workspace-id',
            help='Workspace ID for operations'
        )
        
        # Directory operations
        parser.add_argument(
            '--list',
            metavar='DIRECTORY',
            help='List directory contents'
        )
        
        # Interactive mode
        parser.add_argument(
            '--interactive',
            action='store_true',
            help='Enter interactive mode'
        )
        
        # Status and diagnostics
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show backend connection status'
        )
        
        # Configuration options
        parser.add_argument(
            '--backend-url',
            default=f"http://{os.getenv('SITE_URL', '0.0.0.0')}:{os.getenv('PORT', '8000')}",
            help=f'Backend server URL (default: http://{os.getenv("SITE_URL", "0.0.0.0")}:{os.getenv("PORT", "8000")})'
        )
        
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Request timeout in seconds (default: 30)'
        )
        
        parser.add_argument(
            '--api-key',
            help='API key for authentication'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )
        
        return parser
    
    def update_config(self, args: argparse.Namespace) -> None:
        """
        Update configuration from command line arguments
        
        Args:
            args: Parsed command line arguments
        """
        self.config.backend_url = args.backend_url
        self.config.timeout = args.timeout
        self.config.api_key = args.api_key
        self.config.verbose = args.verbose
        
        # Initialize handlers with updated config
        self.handlers = CommandHandlers(self.config)
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """
        Run the CLI with provided arguments
        
        Args:
            args: Command line arguments (uses sys.argv if None)
            
        Returns:
            Exit code (0 for success, 1 for error)
        """
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)
        
        # Update configuration
        self.update_config(parsed_args)
        
        # Setup logging
        self.setup_logging(parsed_args.verbose)
        
        try:
            # Handle different command types
            success = True
            
            if parsed_args.file:
                # Open file command
                success = self.handlers.handle_file_open(
                    parsed_args.file,
                    parsed_args.workspace_id
                )
            
            elif parsed_args.terminal:
                # Create terminal command
                success = self.handlers.handle_terminal_create(
                    parsed_args.workspace_id
                )
            
            elif parsed_args.terminal_list:
                # List terminals command
                success = self.handlers.handle_terminal_list()
            
            elif parsed_args.workspace:
                # Workspace operations
                if parsed_args.workspace == 'list':
                    success = self.handlers.handle_workspace_list()
                elif parsed_args.workspace == 'info':
                    if not parsed_args.workspace_id:
                        print("Error: --workspace-id required for 'info' command")
                        success = False
                    else:
                        success = self.handlers.handle_workspace_info(
                            parsed_args.workspace_id
                        )
                elif parsed_args.workspace == 'create':
                    print("Workspace creation not yet implemented")
                    success = False
            
            elif parsed_args.list is not None:
                # List directory command
                success = self.handlers.handle_file_list(parsed_args.list)
            
            elif parsed_args.status:
                # Status command
                success = self.handlers.handle_status()
            
            elif parsed_args.interactive:
                # Interactive mode
                success = self.handlers.handle_interactive_mode()
            
            else:
                # No command provided, show help
                parser.print_help()
                success = True
            
            return 0 if success else 1
            
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return 1
        except Exception as e:
            print(f"Error: {e}")
            if parsed_args.verbose:
                logger.exception("CLI operation failed")
            return 1
        finally:
            # Cleanup resources
            if self.handlers:
                self.handlers.cleanup()


def main() -> int:
    """
    Main entry point for icpy CLI
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    cli = IcpyCLI()
    return cli.run()


if __name__ == '__main__':
    sys.exit(main())
