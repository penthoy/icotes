"""
Command-line interface functionality for main.py.

This module contains CLI argument parsing and clipboard handling functions
that were previously in main.py.
"""

import argparse
import asyncio
import logging
import os
import sys

logger = logging.getLogger(__name__)

try:
    from icpy.services.clipboard_service import clipboard_service
    ICPY_AVAILABLE = True
except ImportError:
    logger.warning("icpy clipboard service not available for CLI")
    ICPY_AVAILABLE = False
    clipboard_service = None


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="icotes Backend Server")
    
    # Host configuration priority: BACKEND_HOST -> SITE_URL -> HOST -> default
    default_host = os.getenv('BACKEND_HOST') or os.getenv('SITE_URL') or os.getenv('HOST') or '0.0.0.0'
    parser.add_argument("--host", default=default_host, help="Host to bind to")
    
    # Port configuration priority: BACKEND_PORT -> PORT -> default
    default_port = int(os.getenv('BACKEND_PORT') or os.getenv('PORT') or '8000')
    parser.add_argument("--port", type=int, default=default_port, help="Port to bind to")
    
    parser.add_argument("--stdin-to-clipboard", action="store_true", 
                       help="Read stdin and copy to clipboard")
    parser.add_argument("--clipboard-to-stdout", action="store_true",
                       help="Read clipboard and output to stdout")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    return parser.parse_args()


async def handle_stdin_to_clipboard():
    """Handle --stdin-to-clipboard command."""
    try:
        # Read from stdin
        stdin_data = sys.stdin.read()
        
        if stdin_data:
            # Write to clipboard using icpy clipboard service
            if ICPY_AVAILABLE and clipboard_service:
                result = await clipboard_service.write_clipboard(stdin_data)
                success = result["success"]
            else:
                logger.error("Clipboard service not available")
                print("✗ Clipboard service not available", file=sys.stderr)
                sys.exit(1)
            
            if success:
                logger.info(f"✓ Copied {len(stdin_data)} characters to clipboard")
                print(f"✓ Copied {len(stdin_data)} characters to clipboard", file=sys.stderr)
                sys.exit(0)
            else:
                logger.error("✗ Failed to copy to clipboard")
                print("✗ Failed to copy to clipboard", file=sys.stderr)
                sys.exit(1)
        else:
            logger.info("No input data received")
            print("No input data received", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error in stdin-to-clipboard: {e}")
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_clipboard_to_stdout():
    """Handle --clipboard-to-stdout command."""
    try:
        # Read from clipboard using icpy clipboard service
        if ICPY_AVAILABLE and clipboard_service:
            result = await clipboard_service.read_clipboard()
            clipboard_data = result.get("content", "") if result["success"] else ""
        else:
            logger.error("Clipboard service not available")
            print("✗ Clipboard service not available", file=sys.stderr)
            sys.exit(1)
        
        if clipboard_data:
            # Write to stdout
            sys.stdout.write(clipboard_data)
            sys.stdout.flush()
            logger.info(f"✓ Successfully read {len(clipboard_data)} characters from clipboard")
            sys.exit(0)
        else:
            logger.info("Clipboard is empty")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Error in clipboard-to-stdout: {e}")
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_clipboard_commands(args):
    """Handle clipboard-related CLI commands."""
    if args.stdin_to_clipboard:
        asyncio.run(handle_stdin_to_clipboard())
        return True
    elif args.clipboard_to_stdout:
        asyncio.run(handle_clipboard_to_stdout())
        return True
    return False