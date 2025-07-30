#!/usr/bin/env python3
"""
icpy CLI Entry Point

This script provides the main entry point for the icpy command-line interface,
allowing users to interact with the icpy backend from the command line.

Usage:
  icpy file.py                    # Open file in editor
  icpy --terminal                 # Create new terminal
  icpy --workspace list           # List workspaces
  icpy --interactive              # Enter interactive mode
  icpy --help                     # Show help

"""

import sys
import os

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

try:
    from icpy.cli.icpy_cli import main
    
    if __name__ == '__main__':
        sys.exit(main())
        
except ImportError as e:
    print(f"Error: Failed to import icpy CLI modules: {e}")
    print("Make sure you're running from the backend directory and all dependencies are installed.")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
