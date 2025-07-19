"""
Integration tests for TerminalService

Tests comprehensive terminal service functionality including:
- Terminal session creation and management
- PTY-based terminal sessions
- Event-driven communication through message broker
- WebSocket connections and I/O handling
- Terminal resizing and configuration
- Session cleanup and resource management

Author: GitHub Copilot
Date: July 16, 2025
"""

import asyncio
import json
import os
import pytest
import pytest_asyncio
import shutil
import signal
import tempfile
import time
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icpy.services.terminal_service import (
    TerminalService, TerminalSession, TerminalConfig, TerminalState,
    get_terminal_service, shutdown_terminal_service
)
from icpy.core.message_broker import get_message_broker, shutdown_message_broker
from icpy.core.connection_manager import get_connection_manager, shutdown_connection_manager


class TestTerminalService:
    """Test suite for TerminalService"""
    
    @pytest_asyncio.fixture
    async def terminal_service(self):
        """Create a fresh terminal service for each test"""
        # Reset global instances
        try:
            await shutdown_terminal_service()
        except RuntimeError:
            pass  # Event loop may already be closed
        try:
            await shutdown_message_broker()
        except RuntimeError:
            pass  # Event loop may already be closed
        try:
            await shutdown_connection_manager()
        except RuntimeError:
            pass  # Event loop may already be closed
        
        # Initialize message broker and connection manager
        from icpy.core.message_broker import get_message_broker
        from icpy.core.connection_manager import get_connection_manager
        
        message_broker = await get_message_broker()
        await message_broker.start()
        
        connection_manager = await get_connection_manager()
        await connection_manager.start()
        
        service = TerminalService()
        await service.initialize()
        
        yield service
        
        # Cleanup
        try:
            await service.shutdown()
        except RuntimeError:
            pass  # Event loop may already be closed
        try:
            await shutdown_terminal_service()
        except RuntimeError:
            pass  # Event loop may already be closed

    @pytest.mark.asyncio
    async def test_service_initialization(self, terminal_service):
        """Test terminal service initialization"""
        assert terminal_service is not None
        assert terminal_service.message_broker is not None
        assert terminal_service.connection_manager is not None
        assert terminal_service.max_sessions == 100
        assert terminal_service.session_timeout == 600
        assert len(terminal_service.sessions) == 0
        assert len(terminal_service.websocket_sessions) == 0
        
        # Check stats
        stats = await terminal_service.get_stats()
        assert stats['active_sessions'] == 0
        assert stats['websocket_connections'] == 0
        assert stats['sessions_created'] == 0
        assert stats['sessions_destroyed'] == 0
        assert stats['startup_time'] > 0

    @pytest.mark.asyncio
    async def test_session_creation(self, terminal_service):
        """Test terminal session creation"""
        # Create session with default config
        session_id = await terminal_service.create_session()
        
        assert session_id is not None
        assert session_id in terminal_service.sessions
        
        session = terminal_service.sessions[session_id]
        assert session.id == session_id
        assert session.name.startswith("Terminal")
        assert session.state == TerminalState.CREATED
        assert session.config.shell == "/bin/bash"
        assert session.config.cols == 80
        assert session.config.rows == 24
        
        # Check stats
        stats = await terminal_service.get_stats()
        assert stats['active_sessions'] == 1
        assert stats['sessions_created'] == 1

    @pytest.mark.asyncio
    async def test_session_creation_with_config(self, terminal_service):
        """Test terminal session creation with custom config"""
        config = TerminalConfig(
            shell="/bin/bash",
            term="xterm",
            cols=100,
            rows=30,
            env={"TEST_VAR": "test_value"},
            cwd="/tmp"
        )
        
        session_id = await terminal_service.create_session("Test Terminal", config)
        
        assert session_id is not None
        session = terminal_service.sessions[session_id]
        assert session.name == "Test Terminal"
        assert session.config.shell == "/bin/bash"
        assert session.config.term == "xterm"
        assert session.config.cols == 100
        assert session.config.rows == 30
        assert session.config.env["TEST_VAR"] == "test_value"
        assert session.config.cwd == "/tmp"

    @pytest.mark.asyncio
    async def test_session_start(self, terminal_service):
        """Test terminal session start"""
        session_id = await terminal_service.create_session()
        
        # Start session
        success = await terminal_service.start_session(session_id)
        assert success is True
        
        session = terminal_service.sessions[session_id]
        assert session.state == TerminalState.RUNNING
        assert session.master_fd is not None
        assert session.process is not None
        assert session.process.pid is not None
        
        # Check that process is actually running
        assert session.process.poll() is None

    @pytest.mark.asyncio
    async def test_session_start_nonexistent(self, terminal_service):
        """Test starting non-existent session"""
        success = await terminal_service.start_session("nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_session_start_wrong_state(self, terminal_service):
        """Test starting session in wrong state"""
        session_id = await terminal_service.create_session()
        
        # Start session first time
        success = await terminal_service.start_session(session_id)
        assert success is True
        
        # Try to start again
        success = await terminal_service.start_session(session_id)
        assert success is False

    @pytest.mark.asyncio
    async def test_session_stop(self, terminal_service):
        """Test terminal session stop"""
        session_id = await terminal_service.create_session()
        await terminal_service.start_session(session_id)
        
        # Stop session
        success = await terminal_service.stop_session(session_id)
        assert success is True
        
        session = terminal_service.sessions[session_id]
        assert session.state == TerminalState.STOPPED
        assert session.master_fd is None
        assert session.process is None

    @pytest.mark.asyncio
    async def test_session_destroy(self, terminal_service):
        """Test terminal session destroy"""
        session_id = await terminal_service.create_session()
        await terminal_service.start_session(session_id)
        
        # Destroy session
        success = await terminal_service.destroy_session(session_id)
        assert success is True
        
        assert session_id not in terminal_service.sessions
        
        # Check stats
        stats = await terminal_service.get_stats()
        assert stats['active_sessions'] == 0
        assert stats['sessions_destroyed'] == 1

    @pytest.mark.asyncio
    async def test_session_input_output(self, terminal_service):
        """Test terminal session input/output"""
        session_id = await terminal_service.create_session()
        await terminal_service.start_session(session_id)
        
        # Send echo command
        success = await terminal_service.send_input(session_id, "echo 'hello world'\n")
        assert success is True
        
        # Give some time for command to execute
        await asyncio.sleep(0.1)
        
        # Check stats
        stats = await terminal_service.get_stats()
        assert stats['total_input_bytes'] > 0

    @pytest.mark.asyncio
    async def test_session_resize(self, terminal_service):
        """Test terminal session resize"""
        session_id = await terminal_service.create_session()
        await terminal_service.start_session(session_id)
        
        # Resize terminal
        success = await terminal_service.resize_terminal(session_id, 120, 40)
        assert success is True
        
        session = terminal_service.sessions[session_id]
        assert session.config.cols == 120
        assert session.config.rows == 40
        
        # Check stats
        stats = await terminal_service.get_stats()
        assert stats['resize_operations'] == 1

    @pytest.mark.asyncio
    async def test_session_resize_nonexistent(self, terminal_service):
        """Test resizing non-existent session"""
        success = await terminal_service.resize_terminal("nonexistent", 80, 24)
        assert success is False

    @pytest.mark.asyncio
    async def test_session_resize_not_running(self, terminal_service):
        """Test resizing session not running"""
        session_id = await terminal_service.create_session()
        
        success = await terminal_service.resize_terminal(session_id, 80, 24)
        assert success is False

    @pytest.mark.asyncio
    async def test_get_session_info(self, terminal_service):
        """Test getting session information"""
        session_id = await terminal_service.create_session("Test Terminal")
        
        info = await terminal_service.get_session(session_id)
        assert info is not None
        assert info['id'] == session_id
        assert info['name'] == "Test Terminal"
        assert info['state'] == TerminalState.CREATED.value
        assert 'created_at' in info
        assert 'last_activity' in info

    @pytest.mark.asyncio
    async def test_get_session_info_nonexistent(self, terminal_service):
        """Test getting info for non-existent session"""
        info = await terminal_service.get_session("nonexistent")
        assert info is None

    @pytest.mark.asyncio
    async def test_list_sessions(self, terminal_service):
        """Test listing all sessions"""
        # Create multiple sessions
        session1 = await terminal_service.create_session("Terminal 1")
        session2 = await terminal_service.create_session("Terminal 2")
        
        sessions = await terminal_service.list_sessions()
        assert len(sessions) == 2
        
        session_ids = [s['id'] for s in sessions]
        assert session1 in session_ids
        assert session2 in session_ids

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, terminal_service):
        """Test listing sessions when none exist"""
        sessions = await terminal_service.list_sessions()
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_websocket_connection(self, terminal_service):
        """Test WebSocket connection to terminal session"""
        session_id = await terminal_service.create_session()
        await terminal_service.start_session(session_id)
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        mock_websocket.receive_text = AsyncMock(side_effect=asyncio.CancelledError())
        
        # Connect WebSocket
        success = await terminal_service.connect_websocket(mock_websocket, session_id)
        assert success is True
        
        # Verify WebSocket was accepted
        mock_websocket.accept.assert_called_once()
        
        # Check that websocket connection is tracked
        stats = await terminal_service.get_stats()
        assert stats['websocket_connections'] == 1
        
        # Give some time for tasks to be created
        await asyncio.sleep(0.1)
        
        session = terminal_service.sessions[session_id]
        assert session.read_task is not None
        assert session.write_task is not None

    @pytest.mark.asyncio
    async def test_websocket_connection_nonexistent_session(self, terminal_service):
        """Test WebSocket connection to non-existent session"""
        mock_websocket = AsyncMock()
        
        success = await terminal_service.connect_websocket(mock_websocket, "nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_websocket_connection_not_running(self, terminal_service):
        """Test WebSocket connection to session not running"""
        session_id = await terminal_service.create_session()
        mock_websocket = AsyncMock()
        
        success = await terminal_service.connect_websocket(mock_websocket, session_id)
        assert success is False

    @pytest.mark.asyncio
    async def test_session_lifecycle_events(self, terminal_service):
        """Test that session lifecycle events are published"""
        # Track events
        events = []
        
        async def event_handler(message):
            events.append((message.topic, message.payload))
        
        await terminal_service.message_broker.subscribe('terminal.*', event_handler)
        
        # Create session
        session_id = await terminal_service.create_session("Test Terminal")
        
        # Start session
        await terminal_service.start_session(session_id)
        
        # Stop session
        await terminal_service.stop_session(session_id)
        
        # Destroy session
        await terminal_service.destroy_session(session_id)
        
        # Give some time for events to be processed
        await asyncio.sleep(0.1)
        
        # Check events
        event_topics = [event[0] for event in events]
        assert 'terminal.session_created' in event_topics
        assert 'terminal.session_started' in event_topics
        assert 'terminal.session_stopped' in event_topics
        assert 'terminal.session_destroyed' in event_topics

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, terminal_service):
        """Test creating and managing multiple sessions"""
        # Create multiple sessions
        sessions = []
        for i in range(5):
            session_id = await terminal_service.create_session(f"Terminal {i+1}")
            sessions.append(session_id)
        
        # Start all sessions
        for session_id in sessions:
            success = await terminal_service.start_session(session_id)
            assert success is True
        
        # Check all sessions are running
        session_list = await terminal_service.list_sessions()
        assert len(session_list) == 5
        
        for session_info in session_list:
            assert session_info['state'] == TerminalState.RUNNING.value
        
        # Stop all sessions
        for session_id in sessions:
            success = await terminal_service.stop_session(session_id)
            assert success is True
        
        # Check all sessions are stopped
        session_list = await terminal_service.list_sessions()
        for session_info in session_list:
            assert session_info['state'] == TerminalState.STOPPED.value

    @pytest.mark.asyncio
    async def test_session_statistics(self, terminal_service):
        """Test session statistics tracking"""
        session_id = await terminal_service.create_session()
        await terminal_service.start_session(session_id)
        
        initial_stats = await terminal_service.get_stats()
        
        # Send some input
        await terminal_service.send_input(session_id, "echo 'test'\n")
        
        # Resize terminal
        await terminal_service.resize_terminal(session_id, 100, 30)
        
        final_stats = await terminal_service.get_stats()
        
        # Check stats were updated
        assert final_stats['total_input_bytes'] > initial_stats['total_input_bytes']
        assert final_stats['resize_operations'] > initial_stats['resize_operations']

    @pytest.mark.asyncio
    async def test_session_config_serialization(self, terminal_service):
        """Test session configuration serialization"""
        config = TerminalConfig(
            shell="/bin/bash",
            term="xterm",
            cols=100,
            rows=30,
            env={"TEST_VAR": "test_value"},
            cwd="/tmp"
        )
        
        session_id = await terminal_service.create_session("Test Terminal", config)
        
        # Get session info
        info = await terminal_service.get_session(session_id)
        assert info is not None
        
        # Check config serialization
        config_dict = info['config']
        assert config_dict['shell'] == "/bin/bash"
        assert config_dict['term'] == "xterm"
        assert config_dict['cols'] == 100
        assert config_dict['rows'] == 30
        assert config_dict['env']['TEST_VAR'] == "test_value"
        assert config_dict['cwd'] == "/tmp"

    @pytest.mark.asyncio
    async def test_error_handling(self, terminal_service):
        """Test error handling in terminal service"""
        # Test invalid shell
        config = TerminalConfig(shell="/nonexistent/shell")
        session_id = await terminal_service.create_session("Test Terminal", config)
        
        success = await terminal_service.start_session(session_id)
        assert success is False
        
        session = terminal_service.sessions[session_id]
        assert session.state == TerminalState.ERROR

    @pytest.mark.asyncio
    async def test_session_cleanup_on_process_death(self, terminal_service):
        """Test session cleanup when process dies"""
        session_id = await terminal_service.create_session()
        await terminal_service.start_session(session_id)
        
        session = terminal_service.sessions[session_id]
        
        # Kill the process
        if session.process:
            session.process.terminate()
            # Use asyncio to wait for process to die with timeout
            try:
                await asyncio.wait_for(
                    asyncio.create_task(asyncio.to_thread(session.process.wait)),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                # Force kill if terminate didn't work
                session.process.kill()
                await asyncio.to_thread(session.process.wait)
        
        # Give some time for process to be fully terminated
        await asyncio.sleep(0.1)
        
        # Simulate cleanup check
        sessions_to_cleanup = []
        for sid, sess in terminal_service.sessions.items():
            if sess.process and sess.process.poll() is not None:
                sessions_to_cleanup.append(sid)
        
        assert session_id in sessions_to_cleanup

    @pytest.mark.asyncio
    async def test_max_sessions_limit(self, terminal_service):
        """Test maximum sessions limit"""
        # Set a low limit for testing
        terminal_service.max_sessions = 2
        
        # Create sessions up to limit
        session1 = await terminal_service.create_session()
        session2 = await terminal_service.create_session()
        
        # Try to create one more
        try:
            await terminal_service.create_session()
            assert False, "Should have raised exception"
        except Exception as e:
            assert "Maximum number of sessions" in str(e)

    @pytest.mark.asyncio
    async def test_message_broker_integration(self, terminal_service):
        """Test message broker integration for terminal operations"""
        # Test create session via message broker
        await terminal_service.message_broker.publish('terminal.create_session', {
            'name': 'Test Terminal',
            'config': {
                'shell': '/bin/bash',
                'cols': 100,
                'rows': 30
            },
            'request_id': 'test-request'
        })
        
        # Give some time for event to be processed
        await asyncio.sleep(0.1)
        
        # Check that session was created
        sessions = await terminal_service.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]['name'] == 'Test Terminal'
        assert sessions[0]['config']['cols'] == 100
        assert sessions[0]['config']['rows'] == 30

    @pytest.mark.asyncio
    async def test_websocket_resize_handling(self, terminal_service):
        """Test WebSocket resize message handling"""
        session_id = await terminal_service.create_session()
        await terminal_service.start_session(session_id)
        
        # Mock WebSocket that sends resize message
        resize_message = json.dumps({
            'type': 'resize',
            'cols': 120,
            'rows': 40
        })
        
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        mock_websocket.receive_text = AsyncMock(side_effect=[resize_message, asyncio.CancelledError()])
        
        # Connect WebSocket
        success = await terminal_service.connect_websocket(mock_websocket, session_id)
        assert success is True
        
        # Give some time for resize to be processed
        await asyncio.sleep(0.1)
        
        # Check that terminal was resized
        session = terminal_service.sessions[session_id]
        assert session.config.cols == 120
        assert session.config.rows == 40

    @pytest.mark.asyncio
    async def test_service_health_check(self, terminal_service):
        """Test service health information"""
        stats = await terminal_service.get_stats()
        
        # Check required fields
        assert 'active_sessions' in stats
        assert 'websocket_connections' in stats
        assert 'sessions_created' in stats
        assert 'sessions_destroyed' in stats
        assert 'total_input_bytes' in stats
        assert 'total_output_bytes' in stats
        assert 'resize_operations' in stats
        assert 'startup_time' in stats
        assert 'max_sessions' in stats
        assert 'session_timeout' in stats
        assert 'timestamp' in stats

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, terminal_service):
        """Test concurrent terminal operations"""
        # Create multiple sessions concurrently
        tasks = []
        for i in range(10):
            tasks.append(terminal_service.create_session(f"Terminal {i+1}"))
        
        session_ids = await asyncio.gather(*tasks)
        assert len(session_ids) == 10
        
        # Start all sessions concurrently
        tasks = []
        for session_id in session_ids:
            tasks.append(terminal_service.start_session(session_id))
        
        results = await asyncio.gather(*tasks)
        assert all(results)
        
        # Check all sessions are running
        sessions = await terminal_service.list_sessions()
        assert len(sessions) == 10
        
        for session_info in sessions:
            assert session_info['state'] == TerminalState.RUNNING.value

    @pytest.mark.asyncio
    async def test_session_environment_variables(self, terminal_service):
        """Test session environment variable handling"""
        env_vars = {
            'TEST_VAR1': 'value1',
            'TEST_VAR2': 'value2',
            'CUSTOM_PATH': '/custom/path'
        }
        
        config = TerminalConfig(env=env_vars)
        session_id = await terminal_service.create_session("Test Terminal", config)
        
        # Get session info
        info = await terminal_service.get_session(session_id)
        assert info['config']['env'] == env_vars

    @pytest.mark.asyncio
    async def test_session_working_directory(self, terminal_service):
        """Test session working directory setting"""
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config = TerminalConfig(cwd=temp_dir)
            session_id = await terminal_service.create_session("Test Terminal", config)
            
            # Get session info
            info = await terminal_service.get_session(session_id)
            assert info['config']['cwd'] == temp_dir

    @pytest.mark.asyncio
    async def test_session_activity_tracking(self, terminal_service):
        """Test session activity tracking"""
        session_id = await terminal_service.create_session()
        await terminal_service.start_session(session_id)
        
        # Get initial activity time
        info = await terminal_service.get_session(session_id)
        initial_activity = info['last_activity']
        
        # Send input to update activity
        await terminal_service.send_input(session_id, "echo test\n")
        
        # Check activity was updated
        info = await terminal_service.get_session(session_id)
        assert info['last_activity'] > initial_activity
