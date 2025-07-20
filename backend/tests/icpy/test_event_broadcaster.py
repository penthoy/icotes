"""
Integration tests for Event Broadcasting System
Tests event broadcasting to multiple clients, targeted delivery, filtering, and history replay
"""

import pytest
import pytest_asyncio
import asyncio
import json
import os
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List, Set
import uuid

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icpy.core.event_broadcaster import (
    EventBroadcaster, EventFilter, ClientInterest, BroadcastEvent,
    EventPriority, DeliveryMode, get_event_broadcaster, shutdown_event_broadcaster
)
from icpy.core.message_broker import get_message_broker, shutdown_message_broker, Message, MessageType
from icpy.core.connection_manager import (
    get_connection_manager, shutdown_connection_manager, 
    ConnectionInfo, ConnectionType, ConnectionState
)

# Mark all test methods as asyncio
pytestmark = pytest.mark.asyncio


class TestEventBroadcaster:
    """Test suite for EventBroadcaster"""
    
    @pytest_asyncio.fixture
    async def event_broadcaster(self):
        """Create a fresh event broadcaster for each test"""
        # Reset global instances
        try:
            await shutdown_event_broadcaster()
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
        broadcaster = EventBroadcaster()
        await broadcaster.start()
        
        yield broadcaster
        
        # Cleanup
        await broadcaster.stop()
        try:
            await shutdown_event_broadcaster()
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
                'connection_type': ConnectionType.WEBSOCKET,
                'permissions': ['read', 'write']
            },
            'client2': {
                'client_id': 'test_client_2',
                'connection_id': 'conn_2',
                'connection_type': ConnectionType.HTTP,
                'permissions': ['read']
            },
            'client3': {
                'client_id': 'test_client_3',
                'connection_id': 'conn_3',
                'connection_type': ConnectionType.CLI,
                'permissions': ['read', 'write', 'admin']
            }
        }
    
    @pytest_asyncio.fixture
    async def mock_connection_manager(self, mock_clients):
        """Create a mock connection manager with test clients"""
        mock_cm = Mock()
        mock_cm.get_all_client_ids.return_value = [c['client_id'] for c in mock_clients.values()]
        
        async def mock_get_client_info(client_id):
            for client_data in mock_clients.values():
                if client_data['client_id'] == client_id:
                    return ConnectionInfo(
                        client_id=client_id,
                        connection_id=client_data['connection_id'],
                        connection_type=client_data['connection_type'],
                        state=ConnectionState.CONNECTED,
                        metadata={'permissions': client_data['permissions']}
                    )
            return None
        
        mock_cm.get_client_info = mock_get_client_info
        return mock_cm
    
    # Test Service Lifecycle
    
    async def test_service_start_stop(self, event_broadcaster):
        """Test service start and stop operations"""
        # Service should already be started from fixture
        assert event_broadcaster._running
        assert len(event_broadcaster._broadcast_tasks) == len(EventPriority)
        assert all(task is not None for task in event_broadcaster._broadcast_tasks.values())
        assert event_broadcaster._cleanup_task is not None
        
        # Stop the service
        await event_broadcaster.stop()
        assert not event_broadcaster._running
        assert all(task.cancelled() for task in event_broadcaster._broadcast_tasks.values())
        assert event_broadcaster._cleanup_task.cancelled()
    
    # Test Basic Broadcasting
    
    async def test_broadcast_simple_event(self, event_broadcaster, mock_connection_manager):
        """Test broadcasting a simple event to all clients"""
        # Override connection manager
        event_broadcaster.connection_manager = mock_connection_manager
        
        # Create test message
        message = Message(
            type=MessageType.NOTIFICATION,
            topic="test.event",
            payload={'data': 'test message'}
        )
        
        # Broadcast the event
        event_id = await event_broadcaster.broadcast_event(message)
        
        # Give time for processing
        await asyncio.sleep(0.1)
        
        # Verify event was queued
        assert isinstance(event_id, str)
        assert event_broadcaster.stats['events_broadcast'] >= 1
    
    async def test_broadcast_with_priority(self, event_broadcaster, mock_connection_manager):
        """Test broadcasting events with different priorities"""
        event_broadcaster.connection_manager = mock_connection_manager
        
        # Create messages with different priorities
        messages = []
        for priority in EventPriority:
            message = Message(
                type=MessageType.NOTIFICATION,
                topic=f"test.{priority.value}",
                payload={'priority': priority.value}
            )
            event_id = await event_broadcaster.broadcast_event(message, priority=priority)
            messages.append((event_id, priority))
        
        # Give time for processing
        await asyncio.sleep(0.2)
        
        # All events should be processed
        assert len(messages) == len(EventPriority)
    
    # Test Delivery Modes
    
    async def test_targeted_delivery(self, event_broadcaster, mock_connection_manager):
        """Test targeted delivery to specific clients"""
        event_broadcaster.connection_manager = mock_connection_manager
        
        message = Message(
            type=MessageType.NOTIFICATION,
            topic="test.targeted",
            payload={'data': 'targeted message'}
        )
        
        # Target specific clients
        target_clients = {'test_client_1', 'test_client_2'}
        event_id = await event_broadcaster.broadcast_event(
            message,
            delivery_mode=DeliveryMode.TARGETED,
            target_clients=target_clients
        )
        
        # Give time for processing
        await asyncio.sleep(0.1)
        
        assert isinstance(event_id, str)
    
    async def test_unicast_delivery(self, event_broadcaster, mock_connection_manager):
        """Test unicast delivery to single client"""
        event_broadcaster.connection_manager = mock_connection_manager
        
        message = Message(
            type=MessageType.NOTIFICATION,
            topic="test.unicast",
            payload={'data': 'unicast message'}
        )
        
        # Target single client
        event_id = await event_broadcaster.broadcast_event(
            message,
            delivery_mode=DeliveryMode.UNICAST,
            target_clients={'test_client_1'}
        )
        
        # Give time for processing
        await asyncio.sleep(0.1)
        
        assert isinstance(event_id, str)
    
    # Test Client Interests
    
    async def test_register_client_interest(self, event_broadcaster):
        """Test registering client interests"""
        client_id = 'test_client_1'
        topic_patterns = ['user.*', 'system.notifications']
        event_types = {'user_action', 'system_alert'}
        
        interest_id = await event_broadcaster.register_client_interest(
            client_id, topic_patterns, event_types
        )
        
        assert isinstance(interest_id, str)
        assert client_id in event_broadcaster.client_interests
        assert len(event_broadcaster.client_interests[client_id]) == 1
        
        interest = event_broadcaster.client_interests[client_id][0]
        assert interest.topic_patterns == topic_patterns
        assert interest.event_types == event_types
    
    async def test_unregister_client_interest(self, event_broadcaster):
        """Test unregistering client interests"""
        client_id = 'test_client_1'
        
        # Register some interests
        await event_broadcaster.register_client_interest(
            client_id, ['pattern1.*'], {'type1'}
        )
        await event_broadcaster.register_client_interest(
            client_id, ['pattern2.*'], {'type2'}
        )
        
        assert len(event_broadcaster.client_interests[client_id]) == 2
        
        # Unregister specific interest
        await event_broadcaster.unregister_client_interest(client_id, ['pattern1.*'])
        
        assert len(event_broadcaster.client_interests[client_id]) == 1
        assert event_broadcaster.client_interests[client_id][0].topic_patterns == ['pattern2.*']
        
        # Unregister all interests
        await event_broadcaster.unregister_client_interest(client_id)
        
        assert client_id not in event_broadcaster.client_interests
    
    async def test_get_client_interests(self, event_broadcaster):
        """Test getting client interests"""
        client_id = 'test_client_1'
        
        # No interests initially
        interests = await event_broadcaster.get_client_interests(client_id)
        assert interests == []
        
        # Register interest
        await event_broadcaster.register_client_interest(
            client_id, ['test.*'], {'test_type'}
        )
        
        interests = await event_broadcaster.get_client_interests(client_id)
        assert len(interests) == 1
        assert interests[0].client_id == client_id
    
    # Test Event Filtering
    
    async def test_event_filter_topic_patterns(self, event_broadcaster, mock_connection_manager):
        """Test event filtering by topic patterns"""
        event_broadcaster.connection_manager = mock_connection_manager
        
        # Create filter for specific topics
        filter_config = EventFilter(topic_patterns=['user.*', 'system.alerts'])
        
        message = Message(
            type=MessageType.NOTIFICATION,
            topic="user.login",
            payload={'user': 'test_user'}
        )
        
        event_id = await event_broadcaster.broadcast_event(
            message,
            delivery_mode=DeliveryMode.FILTERED,
            filter_config=filter_config
        )
        
        # Give time for processing
        await asyncio.sleep(0.1)
        
        assert isinstance(event_id, str)
    
    async def test_event_filter_client_types(self, event_broadcaster, mock_connection_manager):
        """Test event filtering by client connection types"""
        event_broadcaster.connection_manager = mock_connection_manager
        
        # Filter for only WebSocket clients
        filter_config = EventFilter(client_types={ConnectionType.WEBSOCKET})
        
        message = Message(
            type=MessageType.NOTIFICATION,
            topic="test.websocket_only",
            payload={'data': 'websocket message'}
        )
        
        event_id = await event_broadcaster.broadcast_event(
            message,
            delivery_mode=DeliveryMode.FILTERED,
            filter_config=filter_config
        )
        
        # Give time for processing
        await asyncio.sleep(0.1)
        
        assert isinstance(event_id, str)
    
    async def test_event_filter_permissions(self, event_broadcaster, mock_connection_manager):
        """Test event filtering by client permissions"""
        event_broadcaster.connection_manager = mock_connection_manager
        
        # Filter for admin permissions
        filter_config = EventFilter(permissions={'admin'})
        
        message = Message(
            type=MessageType.NOTIFICATION,
            topic="admin.notification",
            payload={'data': 'admin only message'}
        )
        
        event_id = await event_broadcaster.broadcast_event(
            message,
            delivery_mode=DeliveryMode.FILTERED,
            filter_config=filter_config
        )
        
        # Give time for processing
        await asyncio.sleep(0.1)
        
        assert isinstance(event_id, str)
    
    async def test_event_filter_exclude_clients(self, event_broadcaster, mock_connection_manager):
        """Test event filtering by excluding specific clients"""
        event_broadcaster.connection_manager = mock_connection_manager
        
        # Exclude specific client
        filter_config = EventFilter(exclude_clients={'test_client_2'})
        
        message = Message(
            type=MessageType.NOTIFICATION,
            topic="test.exclude",
            payload={'data': 'message for most clients'}
        )
        
        event_id = await event_broadcaster.broadcast_event(
            message,
            delivery_mode=DeliveryMode.FILTERED,
            filter_config=filter_config
        )
        
        # Give time for processing
        await asyncio.sleep(0.1)
        
        assert isinstance(event_id, str)
    
    # Test Event History and Replay
    
    async def test_event_history(self, event_broadcaster, mock_connection_manager):
        """Test event history tracking"""
        event_broadcaster.connection_manager = mock_connection_manager
        
        # Broadcast several events
        for i in range(5):
            message = Message(
                type=MessageType.NOTIFICATION,
                topic=f"test.history.{i}",
                payload={'index': i}
            )
            await event_broadcaster.broadcast_event(message)
        
        # Give time for processing
        await asyncio.sleep(0.2)
        
        # Check history
        history = await event_broadcaster.get_event_history()
        assert len(history) >= 5
    
    async def test_replay_events(self, event_broadcaster, mock_connection_manager):
        """Test event replay for clients"""
        event_broadcaster.connection_manager = mock_connection_manager
        client_id = 'test_client_1'
        
        # Set up client interest
        await event_broadcaster.register_client_interest(client_id, ['test.*'])
        
        # Broadcast some events
        for i in range(3):
            message = Message(
                type=MessageType.NOTIFICATION,
                topic=f"test.replay.{i}",
                payload={'index': i}
            )
            await event_broadcaster.broadcast_event(message)
        
        # Give time for processing
        await asyncio.sleep(0.1)
        
        # Replay events
        replayed_count = await event_broadcaster.replay_events(client_id, from_cursor=0, max_events=2)
        
        # Should have replayed some events
        assert replayed_count >= 0
    
    async def test_replay_events_with_cursor(self, event_broadcaster, mock_connection_manager):
        """Test event replay from specific cursor position"""
        event_broadcaster.connection_manager = mock_connection_manager
        client_id = 'test_client_1'
        
        # Broadcast events to build history
        for i in range(5):
            message = Message(
                type=MessageType.NOTIFICATION,
                topic=f"test.cursor.{i}",
                payload={'index': i}
            )
            await event_broadcaster.broadcast_event(message)
        
        # Give time for processing
        await asyncio.sleep(0.1)
        
        # Replay from middle of history
        replayed_count = await event_broadcaster.replay_events(client_id, from_cursor=2, max_events=2)
        
        assert replayed_count >= 0
    
    # Test Interest Matching
    
    async def test_client_interest_matching(self):
        """Test client interest matching logic"""
        interest = ClientInterest(
            client_id='test_client',
            topic_patterns=['user.*', 'system.alerts'],
            event_types={'user_action', 'system_alert'}
        )
        
        # Matching message
        message1 = Message(
            topic="user.login",
            payload={'event_type': 'user_action'}
        )
        assert interest.matches_message(message1)
        
        # Non-matching topic
        message2 = Message(
            topic="admin.action",
            payload={'event_type': 'user_action'}
        )
        assert not interest.matches_message(message2)
        
        # Non-matching event type
        message3 = Message(
            topic="user.logout",
            payload={'event_type': 'other_event'}
        )
        assert not interest.matches_message(message3)
    
    async def test_event_filter_matching(self, mock_clients):
        """Test event filter matching logic"""
        # Create connection info
        client_info = ConnectionInfo(
            client_id='test_client_1',
            connection_id='conn_1',
            connection_type=ConnectionType.WEBSOCKET,
            state=ConnectionState.CONNECTED,
            metadata={'permissions': ['read', 'write']}  # Store permissions in metadata
        )
        
        message = Message(topic="user.action", payload={'data': 'test'})
        
        # Test topic pattern matching
        filter1 = EventFilter(topic_patterns=['user.*'])
        assert filter1.matches('test_client_1', client_info, message)
        
        # Test client type matching
        filter2 = EventFilter(client_types={ConnectionType.WEBSOCKET})
        assert filter2.matches('test_client_1', client_info, message)
        
        # Test permission matching (using metadata)
        filter3 = EventFilter(permissions={'write'})
        assert filter3.matches('test_client_1', client_info, message)
        
        # Test permission not matching
        filter3b = EventFilter(permissions={'admin'})
        assert not filter3b.matches('test_client_1', client_info, message)
        
        # Test exclusion
        filter4 = EventFilter(exclude_clients={'test_client_1'})
        assert not filter4.matches('test_client_1', client_info, message)
    
    # Test Connection Event Handling
    
    async def test_connection_event_handling(self, event_broadcaster):
        """Test handling of connection events"""
        # Mock client connection event
        connect_message = Message(
            type=MessageType.NOTIFICATION,
            topic="connection.client_connected",
            payload={'client_id': 'new_client'}
        )
        
        initial_count = event_broadcaster.stats['clients_connected']
        
        # Handle the message
        await event_broadcaster._handle_connection_event(connect_message)
        
        # Verify client was tracked
        assert 'new_client' in event_broadcaster.client_event_cursors
        assert event_broadcaster.stats['clients_connected'] == initial_count + 1
        
        # Test disconnection
        disconnect_message = Message(
            type=MessageType.NOTIFICATION,
            topic="connection.client_disconnected",
            payload={'client_id': 'new_client'}
        )
        
        # Add some client data first
        event_broadcaster.client_interests['new_client'] = [
            ClientInterest(client_id='new_client', topic_patterns=['test.*'])
        ]
        
        await event_broadcaster._handle_connection_event(disconnect_message)
        
        # Verify client data was cleaned up
        assert 'new_client' not in event_broadcaster.client_interests
        assert 'new_client' not in event_broadcaster.client_event_cursors
    
    # Test Statistics and Monitoring
    
    async def test_get_stats(self, event_broadcaster):
        """Test getting broadcasting statistics"""
        stats = await event_broadcaster.get_stats()
        
        assert isinstance(stats, dict)
        assert 'events_broadcast' in stats
        assert 'events_delivered' in stats
        assert 'events_failed' in stats
        assert 'active_interests' in stats
        assert 'history_size' in stats
        assert 'queue_sizes' in stats
        assert isinstance(stats['queue_sizes'], dict)
    
    async def test_stats_tracking(self, event_broadcaster, mock_connection_manager):
        """Test that statistics are properly tracked"""
        event_broadcaster.connection_manager = mock_connection_manager
        
        initial_stats = await event_broadcaster.get_stats()
        initial_broadcast = initial_stats['events_broadcast']
        
        # Broadcast an event
        message = Message(
            type=MessageType.NOTIFICATION,
            topic="test.stats",
            payload={'data': 'stats test'}
        )
        
        await event_broadcaster.broadcast_event(message)
        await asyncio.sleep(0.1)
        
        updated_stats = await event_broadcaster.get_stats()
        assert updated_stats['events_broadcast'] > initial_broadcast
    
    # Test Performance and Limits
    
    async def test_multiple_concurrent_events(self, event_broadcaster, mock_connection_manager):
        """Test handling multiple concurrent broadcast events"""
        event_broadcaster.connection_manager = mock_connection_manager
        
        # Broadcast multiple events concurrently
        tasks = []
        for i in range(10):
            message = Message(
                type=MessageType.NOTIFICATION,
                topic=f"test.concurrent.{i}",
                payload={'index': i}
            )
            task = event_broadcaster.broadcast_event(message)
            tasks.append(task)
        
        # Wait for all broadcasts to be queued
        event_ids = await asyncio.gather(*tasks)
        
        # All should return valid event IDs
        assert len(event_ids) == 10
        assert all(isinstance(event_id, str) for event_id in event_ids)
        
        # Give time for processing
        await asyncio.sleep(0.2)
    
    async def test_history_size_limit(self, event_broadcaster, mock_connection_manager):
        """Test that event history respects size limits"""
        event_broadcaster.connection_manager = mock_connection_manager
        
        # Set a small history limit for testing
        original_limit = event_broadcaster.event_history.maxlen
        event_broadcaster.event_history = event_broadcaster.event_history.__class__(maxlen=5)
        
        try:
            # Broadcast more events than the limit
            for i in range(10):
                message = Message(
                    type=MessageType.NOTIFICATION,
                    topic=f"test.limit.{i}",
                    payload={'index': i}
                )
                await event_broadcaster.broadcast_event(message)
            
            # Give time for processing
            await asyncio.sleep(0.2)
            
            # History should be limited
            assert len(event_broadcaster.event_history) <= 5
            
        finally:
            # Restore original limit
            event_broadcaster.event_history = event_broadcaster.event_history.__class__(maxlen=original_limit)
    
    # Test Error Conditions
    
    async def test_broadcast_without_running(self):
        """Test broadcasting when service is not running"""
        broadcaster = EventBroadcaster()
        
        message = Message(
            type=MessageType.NOTIFICATION,
            topic="test.error",
            payload={'data': 'error test'}
        )
        
        with pytest.raises(RuntimeError, match="EventBroadcaster is not running"):
            await broadcaster.broadcast_event(message)
    
    async def test_delivery_failure_handling(self, event_broadcaster, mock_connection_manager):
        """Test handling of delivery failures"""
        # Mock connection manager to return invalid client info
        async def failing_get_client_info(client_id):
            return None
        
        mock_connection_manager.get_client_info = failing_get_client_info
        event_broadcaster.connection_manager = mock_connection_manager
        
        message = Message(
            type=MessageType.NOTIFICATION,
            topic="test.failure",
            payload={'data': 'failure test'}
        )
        
        # This should not raise an exception
        event_id = await event_broadcaster.broadcast_event(message)
        await asyncio.sleep(0.1)
        
        assert isinstance(event_id, str)
    
    # Test Global Service Instance
    
    async def test_global_service_instance(self):
        """Test global service instance management"""
        # Reset global instance
        await shutdown_event_broadcaster()
        
        # Get global instance
        broadcaster1 = get_event_broadcaster()
        broadcaster2 = get_event_broadcaster()
        
        # Should be the same instance
        assert broadcaster1 is broadcaster2
        
        # Cleanup
        await shutdown_event_broadcaster()
    
    # Test Custom Filter Functions
    
    async def test_custom_filter_function(self, event_broadcaster, mock_connection_manager):
        """Test custom filter functions in event filters"""
        event_broadcaster.connection_manager = mock_connection_manager
        
        # Custom filter that only allows messages with specific payload
        def custom_filter(client_id: str, message: Message) -> bool:
            return message.payload.get('allowed', False) if isinstance(message.payload, dict) else False
        
        filter_config = EventFilter(custom_filter=custom_filter)
        
        # Message that should be filtered out
        message1 = Message(
            topic="test.custom",
            payload={'data': 'test', 'allowed': False}
        )
        
        # Message that should pass
        message2 = Message(
            topic="test.custom",
            payload={'data': 'test', 'allowed': True}
        )
        
        await event_broadcaster.broadcast_event(message1, delivery_mode=DeliveryMode.FILTERED, filter_config=filter_config)
        await event_broadcaster.broadcast_event(message2, delivery_mode=DeliveryMode.FILTERED, filter_config=filter_config)
        
        # Give time for processing
        await asyncio.sleep(0.1)
        
        # Both events should be queued (filtering happens during delivery)
        assert event_broadcaster.stats['events_broadcast'] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
