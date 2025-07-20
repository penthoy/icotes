"""
Event Broadcasting System for icpy Backend
Provides advanced event broadcasting to connected clients with filtering, permissions, and history
Built on top of the Message Broker to provide client-specific event delivery
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Set, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import fnmatch
import weakref

# Internal imports
from .message_broker import MessageBroker, Message, MessageType, get_message_broker
from .connection_manager import ConnectionManager, ConnectionInfo, ConnectionType, get_connection_manager

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Event priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class DeliveryMode(Enum):
    """Event delivery modes"""
    BROADCAST = "broadcast"  # Deliver to all connected clients
    TARGETED = "targeted"   # Deliver to specific clients
    FILTERED = "filtered"   # Deliver based on client interests/permissions
    UNICAST = "unicast"     # Deliver to single client


@dataclass
class EventFilter:
    """Filter configuration for event delivery"""
    topic_patterns: List[str] = field(default_factory=list)
    client_types: Set[ConnectionType] = field(default_factory=set)
    permissions: Set[str] = field(default_factory=set)
    exclude_clients: Set[str] = field(default_factory=set)
    include_clients: Set[str] = field(default_factory=set)
    custom_filter: Optional[Callable[[str, Message], bool]] = None  # (client_id, message) -> bool
    
    def matches(self, client_id: str, client_info: ConnectionInfo, message: Message) -> bool:
        """Check if the filter matches for a specific client and message"""
        # Check exclusions first
        if client_id in self.exclude_clients:
            return False
        
        # Check inclusions
        if self.include_clients and client_id not in self.include_clients:
            return False
        
        # Check client type
        if self.client_types and client_info.connection_type not in self.client_types:
            return False
        
        # Check topic patterns
        if self.topic_patterns:
            topic_match = any(fnmatch.fnmatch(message.topic, pattern) for pattern in self.topic_patterns)
            if not topic_match:
                return False
        
        # Check permissions (look in metadata if permissions is not a direct field)
        if self.permissions:
            client_permissions = getattr(client_info, 'permissions', None)
            if client_permissions is None and hasattr(client_info, 'metadata'):
                # Check in metadata
                client_permissions = client_info.metadata.get('permissions', [])
            
            client_permissions = set(client_permissions or [])
            if not self.permissions.issubset(client_permissions):
                return False
        
        # Apply custom filter
        if self.custom_filter and not self.custom_filter(client_id, message):
            return False
        
        return True


@dataclass
class ClientInterest:
    """Client interest subscription for event filtering"""
    client_id: str
    topic_patterns: List[str] = field(default_factory=list)
    event_types: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    
    def matches_message(self, message: Message) -> bool:
        """Check if this interest matches a message"""
        # Check topic patterns
        if self.topic_patterns:
            topic_match = any(fnmatch.fnmatch(message.topic, pattern) for pattern in self.topic_patterns)
            if not topic_match:
                return False
        
        # Check event types
        if self.event_types:
            event_type = message.payload.get('event_type') if isinstance(message.payload, dict) else None
            if event_type not in self.event_types:
                return False
        
        return True


@dataclass
class BroadcastEvent:
    """Event to be broadcast to clients"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message: Optional[Message] = None
    priority: EventPriority = EventPriority.NORMAL
    delivery_mode: DeliveryMode = DeliveryMode.BROADCAST
    filter_config: Optional[EventFilter] = None
    target_clients: Set[str] = field(default_factory=set)
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    delivered_to: Set[str] = field(default_factory=set)
    failed_clients: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'event_id': self.event_id,
            'message': self.message.to_dict() if self.message else None,
            'priority': self.priority.value,
            'delivery_mode': self.delivery_mode.value,
            'target_clients': list(self.target_clients),
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'created_at': self.created_at,
            'delivered_to': list(self.delivered_to),
            'failed_clients': list(self.failed_clients)
        }


class EventBroadcaster:
    """
    Advanced event broadcasting system for real-time client communication
    
    Provides targeted event delivery, client interest-based filtering,
    permission-based routing, and event history with replay capabilities.
    """
    
    def __init__(self, message_broker: Optional[MessageBroker] = None,
                 connection_manager: Optional[ConnectionManager] = None):
        """
        Initialize the event broadcaster
        
        Args:
            message_broker: Message broker for internal communication
            connection_manager: Connection manager for client tracking
        """
        self.message_broker = message_broker
        self.connection_manager = connection_manager
        
        # Client interest tracking
        self.client_interests: Dict[str, List[ClientInterest]] = defaultdict(list)
        
        # Event history and replay
        self.event_history: deque = deque(maxlen=1000)  # Keep last 1000 events
        self.client_event_cursors: Dict[str, int] = {}  # Track what events clients have seen
        
        # Broadcasting queues by priority
        self.broadcast_queues: Dict[EventPriority, asyncio.Queue] = {
            priority: asyncio.Queue() for priority in EventPriority
        }
        
        # Performance and statistics
        self.stats = {
            'events_broadcast': 0,
            'events_delivered': 0,
            'events_failed': 0,
            'clients_connected': 0,
            'average_delivery_time': 0.0
        }
        
        # Configuration
        self.max_history_size = 1000
        self.max_retry_attempts = 3
        self.delivery_timeout = 5.0  # seconds
        self.replay_batch_size = 50
        
        # Internal state
        self._running = False
        self._broadcast_tasks: Dict[EventPriority, Optional[asyncio.Task]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("EventBroadcaster initialized")
    
    async def start(self) -> None:
        """Start the event broadcasting system"""
        if self._running:
            return
        
        # Initialize dependencies if not provided
        if self.message_broker is None:
            self.message_broker = await get_message_broker()
        if self.connection_manager is None:
            self.connection_manager = await get_connection_manager()
        
        self._running = True
        
        # Subscribe to connection events
        await self.message_broker.subscribe("connection.*", self._handle_connection_event)
        
        # Start broadcast workers for each priority level
        for priority in EventPriority:
            self._broadcast_tasks[priority] = asyncio.create_task(
                self._broadcast_worker(priority)
            )
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("EventBroadcaster started")
    
    async def stop(self) -> None:
        """Stop the event broadcasting system"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel all broadcast workers
        for priority, task in self._broadcast_tasks.items():
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Unsubscribe from events
        await self.message_broker.unsubscribe("connection.*", self._handle_connection_event)
        
        logger.info("EventBroadcaster stopped")
    
    async def broadcast_event(self, message: Message, 
                            delivery_mode: DeliveryMode = DeliveryMode.BROADCAST,
                            priority: EventPriority = EventPriority.NORMAL,
                            target_clients: Optional[Set[str]] = None,
                            filter_config: Optional[EventFilter] = None) -> str:
        """
        Broadcast an event to connected clients
        
        Args:
            message: Message to broadcast
            delivery_mode: How to deliver the event
            priority: Event priority level
            target_clients: Specific clients to target (for targeted/unicast mode)
            filter_config: Filtering configuration
            
        Returns:
            Event ID for tracking
        """
        if not self._running:
            raise RuntimeError("EventBroadcaster is not running")
        
        # Create broadcast event
        broadcast_event = BroadcastEvent(
            message=message,
            priority=priority,
            delivery_mode=delivery_mode,
            filter_config=filter_config,
            target_clients=target_clients or set()
        )
        
        # Add to appropriate priority queue
        await self.broadcast_queues[priority].put(broadcast_event)
        
        logger.debug(f"Queued event {broadcast_event.event_id} for broadcasting")
        return broadcast_event.event_id
    
    async def register_client_interest(self, client_id: str, 
                                     topic_patterns: List[str],
                                     event_types: Optional[Set[str]] = None,
                                     metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Register a client's interest in specific events
        
        Args:
            client_id: Client identifier
            topic_patterns: List of topic patterns to match
            event_types: Optional set of event types to filter
            metadata: Optional metadata for the interest
            
        Returns:
            Interest ID
        """
        interest = ClientInterest(
            client_id=client_id,
            topic_patterns=topic_patterns,
            event_types=event_types or set(),
            metadata=metadata or {}
        )
        
        self.client_interests[client_id].append(interest)
        
        logger.info(f"Registered interest for client {client_id}: {topic_patterns}")
        return f"interest_{client_id}_{len(self.client_interests[client_id])}"
    
    async def unregister_client_interest(self, client_id: str, 
                                       topic_patterns: Optional[List[str]] = None) -> None:
        """
        Unregister client interests
        
        Args:
            client_id: Client identifier
            topic_patterns: Specific patterns to remove, or None for all
        """
        if client_id not in self.client_interests:
            return
        
        if topic_patterns is None:
            # Remove all interests for this client
            del self.client_interests[client_id]
        else:
            # Remove specific interests
            self.client_interests[client_id] = [
                interest for interest in self.client_interests[client_id]
                if not any(pattern in interest.topic_patterns for pattern in topic_patterns)
            ]
            
            # Clean up empty entries
            if not self.client_interests[client_id]:
                del self.client_interests[client_id]
        
        logger.info(f"Unregistered interests for client {client_id}")
    
    async def replay_events(self, client_id: str, 
                          from_cursor: Optional[int] = None,
                          max_events: Optional[int] = None) -> int:
        """
        Replay historical events to a client
        
        Args:
            client_id: Client to replay events to
            from_cursor: Starting position in event history
            max_events: Maximum number of events to replay
            
        Returns:
            Number of events replayed
        """
        if client_id not in self.client_event_cursors:
            self.client_event_cursors[client_id] = 0
        
        start_cursor = from_cursor if from_cursor is not None else self.client_event_cursors[client_id]
        max_replay = max_events or self.replay_batch_size
        
        events_to_replay = list(self.event_history)[start_cursor:start_cursor + max_replay]
        replayed_count = 0
        
        for event in events_to_replay:
            if isinstance(event, BroadcastEvent) and event.message:
                # Check if client should receive this event
                if await self._should_deliver_to_client(client_id, event):
                    await self._deliver_to_client(client_id, event.message)
                    replayed_count += 1
        
        # Update cursor
        self.client_event_cursors[client_id] = start_cursor + replayed_count
        
        logger.info(f"Replayed {replayed_count} events to client {client_id}")
        return replayed_count
    
    async def get_client_interests(self, client_id: str) -> List[ClientInterest]:
        """Get all interests for a specific client"""
        return self.client_interests.get(client_id, [])
    
    async def get_event_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get event history"""
        history = list(self.event_history)
        if limit:
            history = history[-limit:]
        return [event.to_dict() if hasattr(event, 'to_dict') else event for event in history]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get broadcasting statistics"""
        return {
            **self.stats,
            'active_interests': sum(len(interests) for interests in self.client_interests.values()),
            'history_size': len(self.event_history),
            'queue_sizes': {
                priority.value: self.broadcast_queues[priority].qsize()
                for priority in EventPriority
            }
        }
    
    # Private methods
    
    async def _broadcast_worker(self, priority: EventPriority) -> None:
        """Worker task for broadcasting events of a specific priority"""
        logger.info(f"Started broadcast worker for {priority.value} priority events")
        
        while self._running:
            try:
                # Get event from queue with timeout
                try:
                    event = await asyncio.wait_for(
                        self.broadcast_queues[priority].get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the broadcast event
                start_time = time.time()
                await self._process_broadcast_event(event)
                delivery_time = time.time() - start_time
                
                # Update statistics
                self.stats['events_broadcast'] += 1
                self.stats['average_delivery_time'] = (
                    (self.stats['average_delivery_time'] * (self.stats['events_broadcast'] - 1) + delivery_time)
                    / self.stats['events_broadcast']
                )
                
                # Add to history
                self.event_history.append(event)
                
            except Exception as e:
                logger.error(f"Error in broadcast worker for {priority.value}: {e}")
                await asyncio.sleep(1.0)
        
        logger.info(f"Stopped broadcast worker for {priority.value} priority events")
    
    async def _process_broadcast_event(self, event: BroadcastEvent) -> None:
        """Process a single broadcast event"""
        if not event.message:
            return
        
        # Get target clients based on delivery mode
        target_clients = await self._get_target_clients(event)
        
        # Deliver to each target client
        delivery_tasks = []
        for client_id in target_clients:
            task = asyncio.create_task(self._deliver_to_client(client_id, event.message))
            delivery_tasks.append((client_id, task))
        
        # Wait for all deliveries and track results
        for client_id, task in delivery_tasks:
            try:
                await asyncio.wait_for(task, timeout=self.delivery_timeout)
                event.delivered_to.add(client_id)
                self.stats['events_delivered'] += 1
            except Exception as e:
                event.failed_clients.add(client_id)
                self.stats['events_failed'] += 1
                logger.warning(f"Failed to deliver event {event.event_id} to client {client_id}: {e}")
        
        logger.debug(f"Broadcast event {event.event_id} completed: "
                    f"delivered to {len(event.delivered_to)}, failed {len(event.failed_clients)}")
    
    async def _get_target_clients(self, event: BroadcastEvent) -> Set[str]:
        """Get the set of target clients for an event based on delivery mode"""
        if event.delivery_mode == DeliveryMode.UNICAST:
            # Single target client
            return set(list(event.target_clients)[:1]) if event.target_clients else set()
        
        elif event.delivery_mode == DeliveryMode.TARGETED:
            # Specific target clients
            return event.target_clients
        
        elif event.delivery_mode == DeliveryMode.BROADCAST:
            # All connected clients
            return set(self.connection_manager.get_all_client_ids())
        
        elif event.delivery_mode == DeliveryMode.FILTERED:
            # Filtered based on interests and permissions
            all_clients = self.connection_manager.get_all_client_ids()
            filtered_clients = set()
            
            for client_id in all_clients:
                if await self._should_deliver_to_client(client_id, event):
                    filtered_clients.add(client_id)
            
            return filtered_clients
        
        return set()
    
    async def _should_deliver_to_client(self, client_id: str, event: BroadcastEvent) -> bool:
        """Check if an event should be delivered to a specific client"""
        if not event.message:
            return False
        
        # Get client connection info
        try:
            client_info = await self.connection_manager.get_client_info(client_id)
            if not client_info:
                return False
        except Exception:
            return False
        
        # Apply filter configuration if provided
        if event.filter_config:
            if not event.filter_config.matches(client_id, client_info, event.message):
                return False
        
        # Check client interests
        client_interests = self.client_interests.get(client_id, [])
        if client_interests:
            # At least one interest must match
            interest_match = any(
                interest.matches_message(event.message)
                for interest in client_interests
            )
            if not interest_match:
                return False
        
        return True
    
    async def _deliver_to_client(self, client_id: str, message: Message) -> None:
        """Deliver a message to a specific client"""
        try:
            # Get client connection info
            client_info = await self.connection_manager.get_client_info(client_id)
            if not client_info:
                raise Exception(f"Client {client_id} not found")
            
            # Use message broker to publish to client-specific topic
            await self.message_broker.publish(
                f"client.{client_id}.events",
                message.payload,
                message_type=message.type,
                sender=message.sender,
                correlation_id=message.correlation_id
            )
            
        except Exception as e:
            logger.error(f"Failed to deliver message to client {client_id}: {e}")
            raise
    
    async def _handle_connection_event(self, message: Message) -> None:
        """Handle connection events from the connection manager"""
        if message.topic == "connection.client_connected":
            client_id = message.payload.get('client_id')
            if client_id:
                self.client_event_cursors[client_id] = len(self.event_history)
                self.stats['clients_connected'] += 1
                
        elif message.topic == "connection.client_disconnected":
            client_id = message.payload.get('client_id')
            if client_id:
                # Clean up client data
                self.client_interests.pop(client_id, None)
                self.client_event_cursors.pop(client_id, None)
                if self.stats['clients_connected'] > 0:
                    self.stats['clients_connected'] -= 1
    
    async def _cleanup_loop(self) -> None:
        """Background task for cleanup operations"""
        while self._running:
            try:
                # Clean up old interests
                current_time = time.time()
                for client_id, interests in list(self.client_interests.items()):
                    self.client_interests[client_id] = [
                        interest for interest in interests
                        if current_time - interest.last_updated < 3600  # 1 hour timeout
                    ]
                    
                    if not self.client_interests[client_id]:
                        del self.client_interests[client_id]
                
                # Clean up old event cursors for disconnected clients
                active_clients = set(self.connection_manager.get_all_client_ids())
                for client_id in list(self.client_event_cursors.keys()):
                    if client_id not in active_clients:
                        del self.client_event_cursors[client_id]
                
                await asyncio.sleep(60)  # Cleanup every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(5.0)


# Global service instance
_event_broadcaster: Optional[EventBroadcaster] = None


def get_event_broadcaster() -> EventBroadcaster:
    """Get the global event broadcaster instance"""
    global _event_broadcaster
    if _event_broadcaster is None:
        _event_broadcaster = EventBroadcaster()
    return _event_broadcaster


async def shutdown_event_broadcaster() -> None:
    """Shutdown the global event broadcaster"""
    global _event_broadcaster
    if _event_broadcaster is not None:
        await _event_broadcaster.stop()
        _event_broadcaster = None
