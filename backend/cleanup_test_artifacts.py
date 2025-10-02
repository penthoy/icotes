#!/usr/bin/env python3
"""
Cleanup utility for icpy backend test artifacts
"""

import os
import sys
import glob
import shutil
from pathlib import Path


def cleanup_temp_workspaces(workspace_root=None):
    """Clean up temporary workspace directories created by tests"""
    if workspace_root is None:
        # Default to workspace directory relative to this script
        script_dir = Path(__file__).parent
        workspace_root = script_dir.parent / 'workspace'
    else:
        workspace_root = Path(workspace_root)
    
    cleaned_count = 0
    
    if not workspace_root.exists():
        print(f"Workspace directory does not exist: {workspace_root}")
        return cleaned_count
    
    print(f"Cleaning temporary workspaces in: {workspace_root}")
    
    # Clean up temporary icotes directories
    temp_dirs = list(workspace_root.glob('.icotes_tmp*'))
    for temp_dir in temp_dirs:
        try:
            shutil.rmtree(temp_dir)
            print(f"✓ Removed: {temp_dir}")
            cleaned_count += 1
        except Exception as e:
            print(f"✗ Failed to remove {temp_dir}: {e}")
    
    # Clean up per-test isolated workspaces created by ChatService
    test_dirs = list(workspace_root.glob('.icotes_test_*'))
    for d in test_dirs:
        try:
            shutil.rmtree(d)
            print(f"✓ Removed test workspace: {d}")
            cleaned_count += 1
        except Exception as e:
            print(f"✗ Failed to remove {d}: {e}")

    # Clean up session files in main .icotes directory
    icotes_dir = workspace_root / '.icotes'
    if icotes_dir.exists():
        chat_history_dir = icotes_dir / 'chat_history'
        if chat_history_dir.exists():
            # Clean up session meta files
            session_files = list(chat_history_dir.glob('session_*.meta.json'))
            for session_file in session_files:
                try:
                    session_file.unlink()
                    print(f"✓ Removed session file: {session_file}")
                    cleaned_count += 1
                except Exception as e:
                    print(f"✗ Failed to remove {session_file}: {e}")
            
            # Clean up jsonl files
            jsonl_files = list(chat_history_dir.glob('*_session-*.jsonl'))
            for jsonl_file in jsonl_files:
                try:
                    jsonl_file.unlink()
                    print(f"✓ Removed jsonl file: {jsonl_file}")
                    cleaned_count += 1
                except Exception as e:
                    print(f"✗ Failed to remove {jsonl_file}: {e}")
    
    return cleaned_count


if __name__ == '__main__':
    workspace_root = sys.argv[1] if len(sys.argv) > 1 else None
    count = cleanup_temp_workspaces(workspace_root)
    print(f"\nCleaned up {count} files/directories")