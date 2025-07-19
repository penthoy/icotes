"""
Integration tests for Workspace Service
Tests state management, persistence, event publishing, and multi-client synchronization
"""

import pytest
import pytest_asyncio
import asyncio
import json
import os
import tempfile
import shutil
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
import uuid

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icpy.services.workspace_service import (
    WorkspaceService, WorkspaceState, FileInfo, PanelInfo, TerminalInfo,
    WorkspaceLayout, PanelType, PanelState, get_workspace_service, shutdown_workspace_service
)
from icpy.core.message_broker import get_message_broker, shutdown_message_broker
from icpy.core.connection_manager import get_connection_manager, shutdown_connection_manager


class TestWorkspaceService:
    """Test suite for WorkspaceService"""
    
    @pytest_asyncio.fixture
    async def workspace_service(self):
        """Create a fresh workspace service for each test"""
        # Reset global instances
        try:
            await shutdown_workspace_service()
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
        
        # Create temporary directory for testing
        temp_dir = tempfile.mkdtemp()
        
        service = WorkspaceService(workspace_dir=temp_dir)
        await service.initialize()
        
        yield service
        
        # Cleanup
        try:
            await service.shutdown()
        except RuntimeError:
            pass  # Event loop may already be closed
        try:
            await shutdown_workspace_service()
        except RuntimeError:
            pass  # Event loop may already be closed
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest_asyncio.fixture
    async def sample_workspace(self, workspace_service):
        """Create a sample workspace for testing"""
        workspace = await workspace_service.create_workspace(
            name="Test Workspace",
            root_path="/tmp/test_workspace"
        )
        await workspace_service.switch_workspace(workspace.workspace_id)
        return workspace
    
    @pytest.mark.asyncio
    async def test_workspace_service_initialization(self, workspace_service):
        """Test workspace service initialization"""
        assert workspace_service is not None
        assert workspace_service.message_broker is not None
        assert workspace_service.connection_manager is not None
        assert workspace_service.workspace_dir is not None
        assert os.path.exists(workspace_service.workspace_dir)
        
        # Check statistics
        stats = await workspace_service.get_stats()
        assert 'workspace_switches' in stats
        assert 'files_opened' in stats
        assert 'panels_created' in stats
    
    @pytest.mark.asyncio
    async def test_create_workspace(self, workspace_service):
        """Test workspace creation"""
        # Create workspace
        workspace = await workspace_service.create_workspace(
            name="Test Workspace",
            root_path="/tmp/test"
        )
        
        # Verify workspace properties
        assert workspace is not None
        assert workspace.name == "Test Workspace"
        assert workspace.root_path == "/tmp/test"
        assert workspace.workspace_id is not None
        assert workspace.current_layout is not None
        assert workspace.current_layout.name == "Default Layout"
        assert len(workspace.preferences) > 0
        
        # Verify workspace is cached
        assert workspace.workspace_id in workspace_service.workspace_cache
        
        # Verify workspace is saved to disk
        workspace_file = os.path.join(
            workspace_service.workspace_dir,
            f"{workspace.workspace_id}.json"
        )
        assert os.path.exists(workspace_file)
        
        # Verify statistics
        stats = await workspace_service.get_stats()
        assert stats['workspace_switches'] >= 1
    
    @pytest.mark.asyncio
    async def test_load_workspace(self, workspace_service):
        """Test workspace loading"""
        # Create workspace
        original_workspace = await workspace_service.create_workspace(
            name="Load Test",
            root_path="/tmp/load_test"
        )
        workspace_id = original_workspace.workspace_id
        
        # Clear cache
        workspace_service.workspace_cache.clear()
        
        # Load workspace
        loaded_workspace = await workspace_service.load_workspace(workspace_id)
        
        # Verify loaded workspace
        assert loaded_workspace is not None
        assert loaded_workspace.workspace_id == workspace_id
        assert loaded_workspace.name == "Load Test"
        assert loaded_workspace.root_path == "/tmp/load_test"
        
        # Verify workspace is cached again
        assert workspace_id in workspace_service.workspace_cache
    
    @pytest.mark.asyncio
    async def test_switch_workspace(self, workspace_service):
        """Test workspace switching"""
        # Create two workspaces
        workspace1 = await workspace_service.create_workspace(
            name="Workspace 1",
            root_path="/tmp/ws1"
        )
        workspace2 = await workspace_service.create_workspace(
            name="Workspace 2",
            root_path="/tmp/ws2"
        )
        
        # Switch to workspace 1
        success = await workspace_service.switch_workspace(workspace1.workspace_id)
        assert success
        assert workspace_service.current_workspace.workspace_id == workspace1.workspace_id
        
        # Switch to workspace 2
        success = await workspace_service.switch_workspace(workspace2.workspace_id)
        assert success
        assert workspace_service.current_workspace.workspace_id == workspace2.workspace_id
        
        # Try switching to non-existent workspace
        success = await workspace_service.switch_workspace("non-existent")
        assert not success
    
    @pytest.mark.asyncio
    async def test_workspace_list(self, workspace_service):
        """Test getting workspace list"""
        # Create multiple workspaces
        workspace1 = await workspace_service.create_workspace("WS1", "/tmp/ws1")
        workspace2 = await workspace_service.create_workspace("WS2", "/tmp/ws2")
        workspace3 = await workspace_service.create_workspace("WS3", "/tmp/ws3")
        
        # Get workspace list
        workspaces = await workspace_service.get_workspace_list()
        
        # Verify list
        assert len(workspaces) == 3
        workspace_ids = [ws['workspace_id'] for ws in workspaces]
        assert workspace1.workspace_id in workspace_ids
        assert workspace2.workspace_id in workspace_ids
        assert workspace3.workspace_id in workspace_ids
        
        # Verify structure
        for ws in workspaces:
            assert 'workspace_id' in ws
            assert 'name' in ws
            assert 'root_path' in ws
            assert 'last_accessed' in ws
            assert 'created_at' in ws
    
    @pytest.mark.asyncio
    async def test_delete_workspace(self, workspace_service):
        """Test workspace deletion"""
        # Create workspace
        workspace = await workspace_service.create_workspace(
            name="Delete Test",
            root_path="/tmp/delete_test"
        )
        workspace_id = workspace.workspace_id
        
        # Verify workspace exists
        workspace_file = os.path.join(
            workspace_service.workspace_dir,
            f"{workspace_id}.json"
        )
        assert os.path.exists(workspace_file)
        
        # Delete workspace
        success = await workspace_service.delete_workspace(workspace_id)
        assert success
        
        # Verify workspace is removed
        assert not os.path.exists(workspace_file)
        assert workspace_id not in workspace_service.workspace_cache
        
        # Try deleting non-existent workspace
        success = await workspace_service.delete_workspace("non-existent")
        assert success  # Should not fail
    
    @pytest.mark.asyncio
    async def test_workspace_persistence(self, workspace_service):
        """Test workspace state persistence"""
        # Create workspace
        workspace = await workspace_service.create_workspace(
            name="Persistence Test",
            root_path="/tmp/persist_test"
        )
        await workspace_service.switch_workspace(workspace.workspace_id)
        
        # Modify workspace state
        await workspace_service.open_file("/tmp/test.py")
        await workspace_service.create_panel(PanelType.TERMINAL, "Terminal 1")
        await workspace_service.create_terminal("Test Terminal")
        
        # Save state
        success = await workspace_service.save_workspace_state()
        assert success
        
        # Clear current workspace
        workspace_service.current_workspace = None
        workspace_service.workspace_cache.clear()
        
        # Load workspace again
        loaded_workspace = await workspace_service.load_workspace(workspace.workspace_id)
        assert loaded_workspace is not None
        
        # Verify state is restored
        assert len(loaded_workspace.open_files) == 1
        assert "/tmp/test.py" in loaded_workspace.open_files
        assert len(loaded_workspace.panels) == 1
        assert len(loaded_workspace.terminals) == 1
    
    @pytest.mark.asyncio
    async def test_file_management(self, workspace_service, sample_workspace):
        """Test file management operations"""
        # Create test file
        test_file = "/tmp/test_file.py"
        with open(test_file, 'w') as f:
            f.write("print('Hello World')")
        
        try:
            # Open file
            success = await workspace_service.open_file(test_file)
            assert success
            
            # Verify file is opened
            open_files = await workspace_service.get_open_files()
            assert len(open_files) == 1
            assert open_files[0]['file_path'] == test_file
            assert open_files[0]['file_name'] == "test_file.py"
            
            # Verify active file
            assert workspace_service.current_workspace.active_file_path == test_file
            
            # Update file state
            success = await workspace_service.update_file_state(
                test_file,
                is_dirty=True,
                cursor_position={'line': 1, 'column': 5}
            )
            assert success
            
            # Verify state update
            file_info = workspace_service.current_workspace.open_files[test_file]
            assert file_info.is_dirty
            assert file_info.cursor_position == {'line': 1, 'column': 5}
            
            # Set active file
            success = await workspace_service.set_active_file(test_file)
            assert success
            
            # Close file
            success = await workspace_service.close_file(test_file)
            assert success
            
            # Verify file is closed
            open_files = await workspace_service.get_open_files()
            assert len(open_files) == 0
            assert workspace_service.current_workspace.active_file_path is None
            
            # Try opening non-existent file
            success = await workspace_service.open_file("/non/existent/file.py")
            assert not success
            
        finally:
            # Clean up
            if os.path.exists(test_file):
                os.remove(test_file)
    
    @pytest.mark.asyncio
    async def test_panel_management(self, workspace_service, sample_workspace):
        """Test panel management operations"""
        # Create panel
        panel_id = await workspace_service.create_panel(
            PanelType.EDITOR,
            "Editor Panel",
            position={'x': 0, 'y': 0},
            size={'width': 800, 'height': 600},
            metadata={'theme': 'dark'}
        )
        assert panel_id != ""
        
        # Verify panel is created
        panels = await workspace_service.get_panels()
        assert len(panels) == 1
        assert panels[0]['panel_id'] == panel_id
        assert panels[0]['panel_type'] == 'editor'
        assert panels[0]['title'] == "Editor Panel"
        
        # Set active panel
        success = await workspace_service.set_active_panel(panel_id)
        assert success
        assert workspace_service.current_workspace.active_panel_id == panel_id
        
        # Update panel state
        success = await workspace_service.update_panel_state(
            panel_id,
            state=PanelState.MAXIMIZED,
            size={'width': 1200, 'height': 800}
        )
        assert success
        
        # Verify state update
        panel_info = workspace_service.current_workspace.panels[panel_id]
        assert panel_info.state == PanelState.MAXIMIZED
        assert panel_info.size == {'width': 1200, 'height': 800}
        
        # Close panel
        success = await workspace_service.close_panel(panel_id)
        assert success
        
        # Verify panel is closed
        panels = await workspace_service.get_panels()
        assert len(panels) == 0
        assert workspace_service.current_workspace.active_panel_id is None
    
    @pytest.mark.asyncio
    async def test_terminal_management(self, workspace_service, sample_workspace):
        """Test terminal management operations"""
        # Create terminal
        terminal_id = await workspace_service.create_terminal(
            "Test Terminal",
            working_directory="/tmp",
            shell="/bin/bash",
            environment={'TEST_VAR': 'test_value'}
        )
        assert terminal_id != ""
        
        # Verify terminal is created
        terminals = await workspace_service.get_terminals()
        assert len(terminals) == 1
        assert terminals[0]['terminal_id'] == terminal_id
        assert terminals[0]['title'] == "Test Terminal"
        assert terminals[0]['working_directory'] == "/tmp"
        assert terminals[0]['shell'] == "/bin/bash"
        assert terminals[0]['environment'] == {'TEST_VAR': 'test_value'}
        
        # Close terminal
        success = await workspace_service.close_terminal(terminal_id)
        assert success
        
        # Verify terminal is closed
        terminals = await workspace_service.get_terminals()
        assert len(terminals) == 0
    
    @pytest.mark.asyncio
    async def test_layout_management(self, workspace_service, sample_workspace):
        """Test layout management operations"""
        # Create some panels
        panel1_id = await workspace_service.create_panel(PanelType.EDITOR, "Editor")
        panel2_id = await workspace_service.create_panel(PanelType.TERMINAL, "Terminal")
        
        # Save layout
        layout_id = await workspace_service.save_layout("Custom Layout")
        assert layout_id != ""
        
        # Verify layout is saved
        layout = workspace_service.current_workspace.saved_layouts[layout_id]
        assert layout.name == "Custom Layout"
        assert len(layout.panels) == 2
        
        # Create new panel
        panel3_id = await workspace_service.create_panel(PanelType.OUTPUT, "Output")
        
        # Load previous layout
        success = await workspace_service.load_layout(layout_id)
        assert success
        
        # Verify layout is loaded
        current_layout = workspace_service.current_workspace.current_layout
        assert current_layout.layout_id == layout_id
        assert current_layout.name == "Custom Layout"
        
        # Delete layout
        success = await workspace_service.delete_layout(layout_id)
        assert success
        
        # Verify layout is deleted
        assert layout_id not in workspace_service.current_workspace.saved_layouts
    
    @pytest.mark.asyncio
    async def test_preferences_management(self, workspace_service, sample_workspace):
        """Test preferences management"""
        # Get default preferences
        prefs = await workspace_service.get_preferences()
        assert len(prefs) > 0
        assert 'theme' in prefs
        
        # Update preferences
        new_prefs = {
            'theme': 'light',
            'font_size': 16,
            'custom_setting': 'value'
        }
        success = await workspace_service.update_preferences(new_prefs)
        assert success
        
        # Verify preferences are updated
        updated_prefs = await workspace_service.get_preferences()
        assert updated_prefs['theme'] == 'light'
        assert updated_prefs['font_size'] == 16
        assert updated_prefs['custom_setting'] == 'value'
        
        # Verify original preferences are preserved
        assert 'word_wrap' in updated_prefs  # Should still be there
    
    @pytest.mark.asyncio
    async def test_workspace_state_access(self, workspace_service, sample_workspace):
        """Test workspace state access methods"""
        # Add some content
        await workspace_service.open_file("/tmp/test.py")
        panel_id = await workspace_service.create_panel(PanelType.EDITOR, "Editor")
        terminal_id = await workspace_service.create_terminal("Terminal")
        
        # Get complete state
        state = await workspace_service.get_workspace_state()
        assert state is not None
        assert 'workspace_id' in state
        assert 'name' in state
        assert 'open_files' in state
        assert 'panels' in state
        assert 'terminals' in state
        
        # Get individual components
        open_files = await workspace_service.get_open_files()
        panels = await workspace_service.get_panels()
        terminals = await workspace_service.get_terminals()
        
        assert len(open_files) == 1
        assert len(panels) == 1
        assert len(terminals) == 1
    
    @pytest.mark.asyncio
    async def test_event_publishing(self, workspace_service):
        """Test event publishing"""
        # Mock message broker to capture events
        events_captured = []
        
        async def capture_event(message):
            events_captured.append((message.topic, message.payload))
        
        # Subscribe to all workspace events
        await workspace_service.message_broker.subscribe('workspace.*', capture_event)
        
        # Create workspace
        workspace = await workspace_service.create_workspace("Event Test", "/tmp/event_test")
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Verify event was published
        assert len(events_captured) > 0
        
        # Find workspace created event
        workspace_created_events = [
            (topic, msg) for topic, msg in events_captured
            if topic == 'workspace.created'
        ]
        assert len(workspace_created_events) > 0
        
        event_topic, event_message = workspace_created_events[0]
        assert event_message['name'] == "Event Test"
        assert event_message['root_path'] == "/tmp/event_test"
    
    @pytest.mark.asyncio
    async def test_statistics(self, workspace_service, sample_workspace):
        """Test statistics collection"""
        # Get initial stats
        initial_stats = await workspace_service.get_stats()
        initial_files = initial_stats['files_opened']
        initial_panels = initial_stats['panels_created']
        initial_terminals = initial_stats['terminals_created']
        
        # Perform operations
        await workspace_service.open_file("/tmp/test.py")
        await workspace_service.create_panel(PanelType.EDITOR, "Editor")
        await workspace_service.create_terminal("Terminal")
        
        # Get updated stats
        updated_stats = await workspace_service.get_stats()
        
        # Verify statistics are updated
        assert updated_stats['files_opened'] == initial_files + 1
        assert updated_stats['panels_created'] == initial_panels + 1
        assert updated_stats['terminals_created'] == initial_terminals + 1
        assert updated_stats['current_workspace'] == sample_workspace.workspace_id
        assert 'timestamp' in updated_stats
    
    @pytest.mark.asyncio
    async def test_recent_files(self, workspace_service, sample_workspace):
        """Test recent files functionality"""
        # Create test files
        test_files = ["/tmp/file1.py", "/tmp/file2.py", "/tmp/file3.py"]
        for file_path in test_files:
            with open(file_path, 'w') as f:
                f.write("test content")
        
        try:
            # Open files in order
            for file_path in test_files:
                await workspace_service.open_file(file_path)
            
            # Verify recent files order
            recent_files = workspace_service.current_workspace.recent_files
            assert len(recent_files) == 3
            assert recent_files[0] == "/tmp/file3.py"  # Most recent
            assert recent_files[1] == "/tmp/file2.py"
            assert recent_files[2] == "/tmp/file1.py"
            
            # Open first file again
            await workspace_service.open_file("/tmp/file1.py")
            
            # Verify it's moved to the front
            recent_files = workspace_service.current_workspace.recent_files
            assert recent_files[0] == "/tmp/file1.py"
            assert recent_files[1] == "/tmp/file3.py"
            assert recent_files[2] == "/tmp/file2.py"
            
        finally:
            # Clean up
            for file_path in test_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, workspace_service, sample_workspace):
        """Test concurrent workspace operations"""
        # Create multiple operations concurrently
        async def create_file_panel(i):
            await workspace_service.open_file(f"/tmp/file_{i}.py")
            return await workspace_service.create_panel(PanelType.EDITOR, f"Editor {i}")
        
        # Run operations concurrently
        tasks = [create_file_panel(i) for i in range(10)]
        panel_ids = await asyncio.gather(*tasks)
        
        # Verify all operations completed
        assert len(panel_ids) == 10
        assert all(panel_id != "" for panel_id in panel_ids)
        
        # Verify workspace state
        open_files = await workspace_service.get_open_files()
        panels = await workspace_service.get_panels()
        
        assert len(open_files) == 10
        assert len(panels) == 10
    
    @pytest.mark.asyncio
    async def test_error_handling(self, workspace_service):
        """Test error handling"""
        # Test operations without current workspace
        success = await workspace_service.open_file("/tmp/test.py")
        assert not success
        
        panel_id = await workspace_service.create_panel(PanelType.EDITOR, "Editor")
        assert panel_id == ""
        
        terminal_id = await workspace_service.create_terminal("Terminal")
        assert terminal_id == ""
        
        # Test invalid operations
        success = await workspace_service.close_file("/non/existent/file.py")
        assert not success
        
        success = await workspace_service.close_panel("non-existent-panel")
        assert not success
        
        success = await workspace_service.close_terminal("non-existent-terminal")
        assert not success
    
    @pytest.mark.asyncio
    async def test_workspace_recovery(self, workspace_service):
        """Test workspace recovery from corruption"""
        # Create workspace
        workspace = await workspace_service.create_workspace("Recovery Test", "/tmp/recovery")
        workspace_id = workspace.workspace_id
        
        # Corrupt workspace file
        workspace_file = os.path.join(workspace_service.workspace_dir, f"{workspace_id}.json")
        with open(workspace_file, 'w') as f:
            f.write("invalid json")
        
        # Clear cache to force reload from disk
        workspace_service.workspace_cache.clear()
        
        # Try to load corrupted workspace
        loaded_workspace = await workspace_service.load_workspace(workspace_id)
        assert loaded_workspace is None
        
        # Verify error handling doesn't crash the service
        stats = await workspace_service.get_stats()
        assert stats is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
