"""
Global pytest configuration and fixtures for icpy backend tests
"""

import os
import glob
import shutil
import pytest
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_workspaces():
    """Clean up any remaining temporary workspace directories after all tests"""
    # Setup (before tests)
    yield
    
    # Teardown (after all tests)
    try:
        # Find the workspace directory relative to the backend/tests directory
        tests_dir = Path(__file__).parent
        workspace_root = tests_dir.parent.parent / 'workspace'
        
        if workspace_root.exists():
            # Clean up temporary icotes directories
            temp_dirs = list(workspace_root.glob('.icotes_tmp*'))
            for temp_dir in temp_dirs:
                try:
                    shutil.rmtree(temp_dir)
                    print(f"Cleaned up temporary workspace: {temp_dir}")
                except Exception as e:
                    print(f"Warning: Failed to clean up {temp_dir}: {e}")
            
            # Also clean up any session files in the main .icotes directory
            icotes_dir = workspace_root / '.icotes'
            if icotes_dir.exists():
                chat_history_dir = icotes_dir / 'chat_history'
                if chat_history_dir.exists():
                    # Clean up session files that look like test artifacts
                    session_files = list(chat_history_dir.glob('session_*.meta.json'))
                    for session_file in session_files:
                        try:
                            session_file.unlink()
                            print(f"Cleaned up session file: {session_file}")
                        except Exception as e:
                            print(f"Warning: Failed to clean up {session_file}: {e}")
                    
                    # Clean up jsonl files that look like test artifacts
                    jsonl_files = list(chat_history_dir.glob('*_session-*.jsonl'))
                    for jsonl_file in jsonl_files:
                        try:
                            jsonl_file.unlink()
                            print(f"Cleaned up jsonl file: {jsonl_file}")
                        except Exception as e:
                            print(f"Warning: Failed to clean up {jsonl_file}: {e}")
                            
    except Exception as e:
        print(f"Warning: Error during workspace cleanup: {e}")


@pytest.fixture(autouse=True)
async def cleanup_chat_service():
    """Ensure chat service is properly cleaned up after each test"""
    yield
    # Clean up after each test
    try:
        from icpy.services.chat_service import shutdown_chat_service
        await shutdown_chat_service()
    except Exception as e:
        print(f"Warning: Error during chat service cleanup: {e}")