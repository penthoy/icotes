"""
Integration tests for State Synchronization Service
Tests multi-client state synchronization, conflict resolution, and presence awareness
"""

import pytest
import pytest_asyncio
import asyncio
import json
import os
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
import uuid

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icpy.services.state_sync_service import (
    StateSyncService, StateChange, StateChangeType, ClientPresence, StateSnapshot,
    ConflictInfo, ConflictResolution, get_state_sync_service, shutdown_state_sync_service
)
from icpy.core.message_broker import get_message_broker, shutdown_message_broker, Message, MessageType
from icpy.core.connection_manager import get_connection_manager, shutdown_connection_manager

# Mark all test methods as asyncio
pytestmark = pytest.mark.asyncio


class TestStateSyncService:
    """Test suite for StateSyncService"""
    
    @pytest_asyncio.fixture
    async def state_sync_service(self):
        """Create a fresh state sync service for each test"""
        # Reset global instances
        try:
            await shutdown_state_sync_service()
        except RuntimeError:
            pass
        try:
            await shutdown_message_broker()
        except RuntimeError:
            pass
        try:
            await shutdown_connection_manager()
        except RuntimeError:
            pass
        
        # Create fresh instances
        service = StateSyncService()
        await service.start()
        
        yield service
        
        # Cleanup
        await service.stop()
        try:
            await shutdown_state_sync_service()
        except RuntimeError:
            pass
        try:
            await shutdown_message_broker()
        except RuntimeError:
            pass
        try:
            await shutdown_connection_manager()
        except RuntimeError:
            pass
    
    @pytest_asyncio.fixture
    async def mock_clients(self):
        """Create mock client data for testing"""
        return {
            'client1': {
                'client_id': 'test_client_1',
                'connection_id': 'conn_1',
                'user_info': {'user_id': 'user1', 'username': 'testuser1'},
                'initial_state': {'file1.js': {'content': 'console.log("hello");', 'cursor': 0}}
            },
            'client2': {
                'client_id': 'test_client_2',
                'connection_id': 'conn_2',
                'user_info': {'user_id': 'user2', 'username': 'testuser2'},
                'initial_state': {'file2.py': {'content': 'print("world")', 'cursor': 0}}
            },
            'client3': {
                'client_id': 'test_client_3',
                'connection_id': 'conn_3',
                'user_info': {'user_id': 'user3', 'username': 'testuser3'},
                'initial_state': {}
            }
        }
    
    # Test Service Lifecycle
    
    async def test_service_start_stop(self, state_sync_service):
        """Test service start and stop operations"""
        # Service should already be started from fixture
        assert state_sync_service._running
        assert state_sync_service._sync_task is not None
        assert state_sync_service._presence_task is not None
        
        # Stop the service
        await state_sync_service.stop()
        assert not state_sync_service._running
        assert state_sync_service._sync_task.cancelled()
        assert state_sync_service._presence_task.cancelled()
    
    # Test Client Registration
    
    async def test_client_registration(self, state_sync_service, mock_clients):
        """Test client registration with state sync service"""
        client_data = mock_clients['client1']
        
        # Register client
        await state_sync_service.register_client(
            client_data['client_id'],
            client_data['connection_id'],
            client_data['initial_state'],
            client_data['user_info']
        )
        
        # Verify client is registered
        assert client_data['client_id'] in state_sync_service.client_states
        assert client_data['client_id'] in state_sync_service.client_presence
        
        # Check client state
        client_state = await state_sync_service.get_client_state(client_data['client_id'])
        assert client_state == client_data['initial_state']
        
        # Check client presence
        presence = await state_sync_service.get_client_presence(client_data['client_id'])
        assert presence.client_id == client_data['client_id']
        assert presence.connection_id == client_data['connection_id']
        assert presence.user_id == client_data['user_info']['user_id']
        assert presence.username == client_data['user_info']['username']
    
    async def test_client_unregistration(self, state_sync_service, mock_clients):
        """Test client unregistration from state sync service"""
        client_data = mock_clients['client1']
        
        # Register and then unregister client
        await state_sync_service.register_client(
            client_data['client_id'],
            client_data['connection_id'],
            client_data['initial_state'],
            client_data['user_info']
        )
        
        assert client_data['client_id'] in state_sync_service.client_states
        
        await state_sync_service.unregister_client(client_data['client_id'])
        
        # Verify client is unregistered
        assert client_data['client_id'] not in state_sync_service.client_states
        assert client_data['client_id'] not in state_sync_service.client_presence
        
        # Check client state is None
        client_state = await state_sync_service.get_client_state(client_data['client_id'])
        assert client_state is None
        
        # Check client presence is None
        presence = await state_sync_service.get_client_presence(client_data['client_id'])
        assert presence is None
    
    # Test Multi-Client Registration
    
    async def test_multiple_client_registration(self, state_sync_service, mock_clients):
        """Test registration of multiple clients"""
        # Register all clients
        for client_data in mock_clients.values():
            await state_sync_service.register_client(
                client_data['client_id'],
                client_data['connection_id'],
                client_data['initial_state'],
                client_data['user_info']
            )
        
        # Verify all clients are registered
        assert len(state_sync_service.client_states) == 3
        assert len(state_sync_service.client_presence) == 3
        
        # Check all presence information
        all_presence = await state_sync_service.get_all_presence()
        assert len(all_presence) == 3
        
        client_ids = [p.client_id for p in all_presence]
        for client_data in mock_clients.values():
            assert client_data['client_id'] in client_ids
    
    # Test State Changes
    
    async def test_state_change_application(self, state_sync_service, mock_clients):
        """Test applying state changes from clients"""
        client_data = mock_clients['client1']
        
        # Register client
        await state_sync_service.register_client(
            client_data['client_id'],
            client_data['connection_id'],
            client_data['initial_state'],
            client_data['user_info']
        )
        
        # Create and apply state change
        change = StateChange(
            change_type=StateChangeType.UPDATE,
            path='file1.js.content',
            old_value='console.log("hello");',
            new_value='console.log("hello world");',
            client_id=client_data['client_id']
        )
        
        success = await state_sync_service.apply_state_change(client_data['client_id'], change)
        assert success
        
        # Verify change is in history
        assert len(state_sync_service.state_history) == 1
        assert state_sync_service.state_history[0].path == 'file1.js.content'
        assert state_sync_service.state_history[0].new_value == 'console.log("hello world");'
        
        # Verify global version incremented
        assert state_sync_service.global_version == 1
    
    async def test_state_change_unknown_client(self, state_sync_service):
        """Test applying state change from unknown client"""
        change = StateChange(
            change_type=StateChangeType.UPDATE,
            path='file1.js.content',
            old_value='old',
            new_value='new',
            client_id='unknown_client'
        )
        
        success = await state_sync_service.apply_state_change('unknown_client', change)
        assert not success
        
        # Verify no changes in history
        assert len(state_sync_service.state_history) == 0
        assert state_sync_service.global_version == 0
    
    # Test Conflict Detection and Resolution
    
    async def test_conflict_detection(self, state_sync_service, mock_clients):
        """Test detection of conflicting state changes"""
        client1_data = mock_clients['client1']
        client2_data = mock_clients['client2']
        
        # Register two clients
        await state_sync_service.register_client(
            client1_data['client_id'],
            client1_data['connection_id'],
            client1_data['initial_state'],
            client1_data['user_info']
        )
        await state_sync_service.register_client(
            client2_data['client_id'],
            client2_data['connection_id'],
            client2_data['initial_state'],
            client2_data['user_info']
        )
        
        # Apply first change
        change1 = StateChange(
            change_type=StateChangeType.UPDATE,
            path='shared_file.txt.content',
            old_value='original',
            new_value='client1_edit',
            client_id=client1_data['client_id']
        )
        
        success1 = await state_sync_service.apply_state_change(client1_data['client_id'], change1)
        assert success1
        
        # Apply conflicting change from different client
        change2 = StateChange(
            change_type=StateChangeType.UPDATE,
            path='shared_file.txt.content',
            old_value='original',
            new_value='client2_edit',
            client_id=client2_data['client_id']
        )
        
        # This should still succeed due to last-writer-wins resolution
        success2 = await state_sync_service.apply_state_change(client2_data['client_id'], change2)
        assert success2
        
        # Check that conflicts were detected and resolved
        assert len(state_sync_service.conflicts) > 0
    
    async def test_conflict_resolution_last_writer_wins(self, state_sync_service, mock_clients):
        """Test last-writer-wins conflict resolution strategy"""
        client1_data = mock_clients['client1']
        client2_data = mock_clients['client2']
        
        # Set resolution strategy
        state_sync_service.conflict_resolution_strategy = ConflictResolution.LAST_WRITER_WINS
        
        # Register clients
        await state_sync_service.register_client(
            client1_data['client_id'],
            client1_data['connection_id'],
            client1_data['initial_state'],
            client1_data['user_info']
        )
        await state_sync_service.register_client(
            client2_data['client_id'],
            client2_data['connection_id'],
            client2_data['initial_state'],
            client2_data['user_info']
        )
        
        # Apply changes with slight delay
        change1 = StateChange(
            change_type=StateChangeType.UPDATE,
            path='conflict_file.txt.content',
            old_value='original',
            new_value='first_edit',
            client_id=client1_data['client_id'],
            timestamp=time.time()
        )
        
        await state_sync_service.apply_state_change(client1_data['client_id'], change1)
        
        # Small delay to ensure different timestamp
        await asyncio.sleep(0.01)
        
        change2 = StateChange(
            change_type=StateChangeType.UPDATE,
            path='conflict_file.txt.content',
            old_value='original',
            new_value='second_edit',
            client_id=client2_data['client_id'],
            timestamp=time.time()
        )
        
        await state_sync_service.apply_state_change(client2_data['client_id'], change2)
        
        # The second change should win (last writer wins)
        latest_change = state_sync_service.state_history[-1]
        assert latest_change.new_value == 'second_edit'
    
    # Test Presence Management
    
    async def test_presence_update(self, state_sync_service, mock_clients):
        """Test updating client presence information"""
        client_data = mock_clients['client1']
        
        # Register client
        await state_sync_service.register_client(
            client_data['client_id'],
            client_data['connection_id'],
            client_data['initial_state'],
            client_data['user_info']
        )
        
        # Update presence
        presence_data = {
            'active_file': 'newfile.js',
            'cursor_position': {'line': 10, 'column': 5},
            'viewing_files': ['file1.js', 'file2.js'],
            'status': 'active'
        }
        
        await state_sync_service.update_client_presence(client_data['client_id'], presence_data)
        
        # Verify presence update
        presence = await state_sync_service.get_client_presence(client_data['client_id'])
        assert presence.active_file == 'newfile.js'
        assert presence.cursor_position == {'line': 10, 'column': 5}
        assert presence.viewing_files == {'file1.js', 'file2.js'}
        assert presence.status == 'active'
        assert presence.last_activity <= time.time()
    
    async def test_presence_unknown_client(self, state_sync_service):
        """Test updating presence for unknown client"""
        presence_data = {
            'active_file': 'test.js',
            'status': 'active'
        }
        
        # Should not raise error, just log warning
        await state_sync_service.update_client_presence('unknown_client', presence_data)
        
        # Verify no presence was created
        presence = await state_sync_service.get_client_presence('unknown_client')
        assert presence is None
    
    async def test_presence_multiple_clients(self, state_sync_service, mock_clients):
        """Test presence management with multiple clients"""
        # Register all clients
        for client_data in mock_clients.values():
            await state_sync_service.register_client(
                client_data['client_id'],
                client_data['connection_id'],
                client_data['initial_state'],
                client_data['user_info']
            )
        
        # Update presence for each client
        for i, (key, client_data) in enumerate(mock_clients.items()):
            presence_data = {
                'active_file': f'file{i}.js',
                'status': 'active',
                'viewing_files': [f'file{i}.js']
            }
            await state_sync_service.update_client_presence(client_data['client_id'], presence_data)
        
        # Verify all presence information
        all_presence = await state_sync_service.get_all_presence()
        assert len(all_presence) == 3
        
        # Check each client has correct presence
        for i, presence in enumerate(sorted(all_presence, key=lambda p: p.client_id)):
            assert presence.active_file == f'file{i}.js'
            assert presence.viewing_files == {f'file{i}.js'}
    
    # Test State Checkpoints
    
    async def test_create_checkpoint(self, state_sync_service, mock_clients):
        """Test creating state checkpoints"""
        client_data = mock_clients['client1']
        
        # Register client and make some changes
        await state_sync_service.register_client(
            client_data['client_id'],
            client_data['connection_id'],
            client_data['initial_state'],
            client_data['user_info']
        )
        
        # Apply some state changes
        change = StateChange(
            change_type=StateChangeType.UPDATE,
            path='file1.js.content',
            old_value='old',
            new_value='new',
            client_id=client_data['client_id']
        )
        await state_sync_service.apply_state_change(client_data['client_id'], change)
        
        # Create checkpoint
        checkpoint_version = await state_sync_service.create_checkpoint("test_checkpoint")
        
        assert checkpoint_version == state_sync_service.global_version
        assert checkpoint_version in state_sync_service.state_checkpoints
        
        checkpoint = state_sync_service.state_checkpoints[checkpoint_version]
        assert checkpoint['label'] == "test_checkpoint"
        assert 'state' in checkpoint
        assert 'timestamp' in checkpoint
    
    async def test_rollback_to_checkpoint(self, state_sync_service, mock_clients):
        """Test rolling back to a state checkpoint"""
        client_data = mock_clients['client1']
        
        # Register client
        await state_sync_service.register_client(
            client_data['client_id'],
            client_data['connection_id'],
            client_data['initial_state'],
            client_data['user_info']
        )
        
        # Create initial checkpoint
        initial_version = await state_sync_service.create_checkpoint("initial")
        
        # Make some changes
        change1 = StateChange(
            change_type=StateChangeType.UPDATE,
            path='file1.js.content',
            old_value='original',
            new_value='modified1',
            client_id=client_data['client_id']
        )
        await state_sync_service.apply_state_change(client_data['client_id'], change1)
        
        change2 = StateChange(
            change_type=StateChangeType.UPDATE,
            path='file1.js.content',
            old_value='modified1',
            new_value='modified2',
            client_id=client_data['client_id']
        )
        await state_sync_service.apply_state_change(client_data['client_id'], change2)
        
        # Version should have increased
        assert state_sync_service.global_version > initial_version
        
        # Rollback to initial checkpoint
        success = await state_sync_service.rollback_to_checkpoint(initial_version)
        assert success
        
        # Check that rollback change was added to history
        rollback_change = state_sync_service.state_history[-1]
        assert rollback_change.client_id == "system"
        assert rollback_change.change_type == StateChangeType.UPDATE
    
    async def test_rollback_invalid_checkpoint(self, state_sync_service):
        """Test rolling back to invalid checkpoint"""
        success = await state_sync_service.rollback_to_checkpoint(999)
        assert not success
    
    # Test State Merging
    
    async def test_get_merged_state(self, state_sync_service, mock_clients):
        """Test getting merged state across all clients"""
        # Register multiple clients
        for client_data in mock_clients.values():
            await state_sync_service.register_client(
                client_data['client_id'],
                client_data['connection_id'],
                client_data['initial_state'],
                client_data['user_info']
            )
        
        # Get merged state
        merged_state = await state_sync_service.get_merged_state()
        
        # Should return some state (exact merging logic depends on implementation)
        assert isinstance(merged_state, dict)
    
    async def test_get_merged_state_no_clients(self, state_sync_service):
        """Test getting merged state when no clients are connected"""
        merged_state = await state_sync_service.get_merged_state()
        assert merged_state == {}
    
    # Test Message Handling
    
    async def test_connection_event_handling(self, state_sync_service):
        """Test handling of connection events"""
        # Mock connection event message
        connect_message = Message(
            type=MessageType.NOTIFICATION,
            topic="connection.client_connected",
            payload={
                'client_id': 'test_client',
                'connection_id': 'test_conn',
                'user_info': {'user_id': 'test_user', 'username': 'testuser'}
            }
        )
        
        # Handle the message
        await state_sync_service._handle_connection_event(connect_message)
        
        # Verify client was registered
        assert 'test_client' in state_sync_service.client_states
        assert 'test_client' in state_sync_service.client_presence
        
        # Test disconnection
        disconnect_message = Message(
            type=MessageType.NOTIFICATION,
            topic="connection.client_disconnected",
            payload={'client_id': 'test_client'}
        )
        
        await state_sync_service._handle_connection_event(disconnect_message)
        
        # Verify client was unregistered
        assert 'test_client' not in state_sync_service.client_states
        assert 'test_client' not in state_sync_service.client_presence
    
    async def test_state_event_handling(self, state_sync_service, mock_clients):
        """Test handling of state change events"""
        client_data = mock_clients['client1']
        
        # Register client first
        await state_sync_service.register_client(
            client_data['client_id'],
            client_data['connection_id'],
            client_data['initial_state'],
            client_data['user_info']
        )
        
        # Mock state change event
        change_message = Message(
            type=MessageType.NOTIFICATION,
            topic="state.change_request",
            payload={
                'client_id': client_data['client_id'],
                'change': {
                    'change_type': 'update',
                    'path': 'test.js.content',
                    'old_value': 'old',
                    'new_value': 'new'
                }
            }
        )
        
        # Handle the message
        await state_sync_service._handle_state_event(change_message)
        
        # Verify change was applied
        assert len(state_sync_service.state_history) == 1
        assert state_sync_service.state_history[0].path == 'test.js.content'
    
    # Test Global Service Instance
    
    async def test_global_service_instance(self):
        """Test global service instance management"""
        # Reset global instance
        await shutdown_state_sync_service()
        
        # Get global instance
        service1 = get_state_sync_service()
        service2 = get_state_sync_service()
        
        # Should be the same instance
        assert service1 is service2
        
        # Cleanup
        await shutdown_state_sync_service()
    
    # Test Error Conditions
    
    async def test_service_error_handling(self, state_sync_service, mock_clients):
        """Test error handling in various scenarios"""
        # Test with invalid change data
        invalid_change = StateChange(
            change_type=StateChangeType.UPDATE,
            path="",  # Empty path
            old_value=None,
            new_value=None,
            client_id=""  # Empty client ID
        )
        
        success = await state_sync_service.apply_state_change("", invalid_change)
        assert not success
    
    async def test_concurrent_operations(self, state_sync_service, mock_clients):
        """Test concurrent state operations"""
        client_data = mock_clients['client1']
        
        # Register client
        await state_sync_service.register_client(
            client_data['client_id'],
            client_data['connection_id'],
            client_data['initial_state'],
            client_data['user_info']
        )
        
        # Create multiple concurrent state changes
        changes = []
        for i in range(10):
            change = StateChange(
                change_type=StateChangeType.UPDATE,
                path=f'file{i}.js.content',
                old_value=f'old{i}',
                new_value=f'new{i}',
                client_id=client_data['client_id']
            )
            changes.append(change)
        
        # Apply changes concurrently
        tasks = [
            state_sync_service.apply_state_change(client_data['client_id'], change)
            for change in changes
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All changes should succeed
        assert all(result is True for result in results)
        
        # Verify all changes are in history
        assert len(state_sync_service.state_history) == 10
    
    # Test Performance and Limits
    
    async def test_history_trimming(self, state_sync_service, mock_clients):
        """Test that state history is properly trimmed"""
        client_data = mock_clients['client1']
        
        # Set small history retention for testing
        state_sync_service.history_retention = 5
        
        # Register client
        await state_sync_service.register_client(
            client_data['client_id'],
            client_data['connection_id'],
            client_data['initial_state'],
            client_data['user_info']
        )
        
        # Apply more changes than retention limit
        for i in range(10):
            change = StateChange(
                change_type=StateChangeType.UPDATE,
                path=f'file{i}.js.content',
                old_value=f'old{i}',
                new_value=f'new{i}',
                client_id=client_data['client_id']
            )
            await state_sync_service.apply_state_change(client_data['client_id'], change)
        
        # History should be trimmed to retention limit
        assert len(state_sync_service.state_history) == 5
        
        # Should contain the most recent changes
        assert state_sync_service.state_history[-1].new_value == 'new9'
    
    async def test_checkpoint_cleanup(self, state_sync_service, mock_clients):
        """Test that old checkpoints are cleaned up"""
        client_data = mock_clients['client1']
        
        # Register client
        await state_sync_service.register_client(
            client_data['client_id'],
            client_data['connection_id'],
            client_data['initial_state'],
            client_data['user_info']
        )
        
        # Create many checkpoints
        for i in range(15):
            # Make a change to increment version
            change = StateChange(
                change_type=StateChangeType.UPDATE,
                path=f'file{i}.js.content',
                old_value=f'old{i}',
                new_value=f'new{i}',
                client_id=client_data['client_id']
            )
            await state_sync_service.apply_state_change(client_data['client_id'], change)
            
            # Create checkpoint
            await state_sync_service.create_checkpoint(f"checkpoint_{i}")
        
        # Trigger cleanup
        await state_sync_service._optimize_state_storage()
        
        # Should keep only the last 10 checkpoints
        assert len(state_sync_service.state_checkpoints) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
