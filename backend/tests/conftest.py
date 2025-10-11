"""
Global pytest configuration and fixtures for icpy backend tests
"""

import os
import glob
import shutil
import pytest
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def limit_message_broker_memory():
    """Cap MessageBroker in-memory history to avoid test-time RAM spikes.
    Uses environment variables consumed by MessageBroker.
    """
    os.environ.setdefault('MB_MAX_HISTORY', '200')
    os.environ.setdefault('MB_MAX_PAYLOAD_HISTORY_BYTES', str(256 * 1024))  # 256KB per message payload in history
    yield

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
            
            # Also clean up any TEST-GENERATED session files in the main .icotes directory
            icotes_dir = workspace_root / '.icotes'
            if icotes_dir.exists():
                chat_history_dir = icotes_dir / 'chat_history'
                if chat_history_dir.exists():
                    # Only clean up session files that are clearly test artifacts
                    # Look for recent files (created in last 5 minutes) or files with test markers
                    import time
                    current_time = time.time()
                    
                    session_files = list(chat_history_dir.glob('session_*.meta.json'))
                    for session_file in session_files:
                        try:
                            # Only delete files modified in the last 5 minutes (likely test artifacts)
                            file_mtime = session_file.stat().st_mtime
                            age_seconds = current_time - file_mtime
                            
                            if age_seconds < 300:  # 5 minutes
                                session_file.unlink()
                                print(f"Cleaned up recent test session file: {session_file}")
                        except Exception as e:
                            print(f"Warning: Failed to clean up {session_file}: {e}")
                    
                    # Clean up jsonl files that look like test artifacts (recent only)
                    jsonl_files = list(chat_history_dir.glob('*_session-*.jsonl'))
                    for jsonl_file in jsonl_files:
                        try:
                            file_mtime = jsonl_file.stat().st_mtime
                            age_seconds = current_time - file_mtime
                            
                            if age_seconds < 300:  # 5 minutes
                                jsonl_file.unlink()
                                print(f"Cleaned up recent test jsonl file: {jsonl_file}")
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


@pytest.fixture(autouse=True)
async def cleanup_broker_and_connections():
    """Aggressively tear down broker and connection manager after each test to free memory."""
    yield
    try:
        from icpy.core.message_broker import shutdown_message_broker
        await shutdown_message_broker()
    except Exception as e:
        print(f"Warning: Error during message broker cleanup: {e}")
    try:
        from icpy.core.connection_manager import shutdown_connection_manager
        await shutdown_connection_manager()
    except Exception as e:
        print(f"Warning: Error during connection manager cleanup: {e}")