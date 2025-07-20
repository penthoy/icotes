"""
State Synchronization Service for icpy Backend
Maintains client state mapping and synchronization across all connected clients
Handles state diffing, incremental updates, conflict resolution, and client presence awareness
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Set, Optional, Any, Callable, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
from datetime import datetime, timedelta
import weakref

# Internal imports
from ..core.message_broker import MessageBroker, Message, MessageType, get_message_broker
from ..core.connection_manager import ConnectionManager, get_connection_manager

logger = logging.getLogger(__name__)


class StateChangeType(Enum):
    """Types of state changes"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"
    RENAME = "rename"


class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    LAST_WRITER_WINS = "last_writer_wins"
    FIRST_WRITER_WINS = "first_writer_wins"
    MERGE = "merge"
    MANUAL = "manual"


@dataclass
class StateSnapshot:
    """A snapshot of client state at a specific point in time"""
    client_id: str
    timestamp: float
    state: Dict[str, Any]
    version: int
    checksum: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'client_id': self.client_id,
            'timestamp': self.timestamp,
            'state': self.state,
            'version': self.version,
            'checksum': self.checksum
        }


@dataclass
class StateChange:
    """Represents a state change"""
    change_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str = ""
    change_type: StateChangeType = StateChangeType.UPDATE
    path: str = ""  # JSON path to the changed property
    old_value: Any = None
    new_value: Any = None
    timestamp: float = field(default_factory=time.time)
    version: int = 0
    merged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'change_id': self.change_id,
            'client_id': self.client_id,
            'change_type': self.change_type.value,
            'path': self.path,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'timestamp': self.timestamp,
            'version': self.version,
            'merged': self.merged
        }


@dataclass
class ClientPresence:
    """Client presence information"""
    client_id: str
    connection_id: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    active_file: Optional[str] = None
    active_editor_selection: Optional[Dict[str, Any]] = None
    viewing_files: Set[str] = field(default_factory=set)
    last_activity: float = field(default_factory=time.time)
    cursor_position: Optional[Dict[str, Any]] = None
    status: str = "active"  # active, idle, away
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'client_id': self.client_id,
            'connection_id': self.connection_id,
            'user_id': self.user_id,
            'username': self.username,
            'active_file': self.active_file,
            'active_editor_selection': self.active_editor_selection,
            'viewing_files': list(self.viewing_files),
            'last_activity': self.last_activity,
            'cursor_position': self.cursor_position,
            'status': self.status
        }


@dataclass
class ConflictInfo:
    """Information about a detected conflict"""
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    path: str = ""
    changes: List[StateChange] = field(default_factory=list)
    resolution_strategy: ConflictResolution = ConflictResolution.LAST_WRITER_WINS
    resolved: bool = False
    resolution_timestamp: Optional[float] = None
    resolution_result: Any = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'conflict_id': self.conflict_id,
            'path': self.path,
            'changes': [change.to_dict() for change in self.changes],
            'resolution_strategy': self.resolution_strategy.value,
            'resolved': self.resolved,
            'resolution_timestamp': self.resolution_timestamp,
            'resolution_result': self.resolution_result
        }


class StateSyncService:
    """
    Service for synchronizing state across multiple connected clients
    
    This service maintains a consistent view of the application state across all clients,
    handles incremental updates, resolves conflicts, and provides presence awareness.
    """
    
    def __init__(self, message_broker: Optional[MessageBroker] = None,
                 connection_manager: Optional[ConnectionManager] = None):
        """
        Initialize the state synchronization service
        
        Args:
            message_broker: Message broker for event communication
            connection_manager: Connection manager for client tracking
        """
        self.message_broker = message_broker
        self.connection_manager = connection_manager
        
        # Client state tracking
        self.client_states: Dict[str, StateSnapshot] = {}
        self.client_presence: Dict[str, ClientPresence] = {}
        
        # State history and versioning
        self.state_history: List[StateChange] = []
        self.global_version: int = 0
        self.state_checkpoints: Dict[int, Dict[str, Any]] = {}
        
        # Conflict detection and resolution
        self.conflicts: Dict[str, ConflictInfo] = {}
        self.conflict_resolution_strategy = ConflictResolution.LAST_WRITER_WINS
        
        # Synchronization settings
        self.sync_batch_size = 50
        self.sync_interval = 0.1  # 100ms
        self.presence_timeout = 300  # 5 minutes
        self.history_retention = 1000  # Keep last 1000 changes
        
        # Internal state
        self._running = False
        self._sync_task: Optional[asyncio.Task] = None
        self._presence_task: Optional[asyncio.Task] = None
        self._subscribers: Dict[str, Set[Callable]] = defaultdict(set)
        
        logger.info("StateSyncService initialized")
    
    async def start(self) -> None:
        """Start the state synchronization service"""
        if self._running:
            return
        
        # Initialize message broker and connection manager if not provided
        if self.message_broker is None:
            self.message_broker = await get_message_broker()
        if self.connection_manager is None:
            self.connection_manager = await get_connection_manager()
        
        self._running = True
        
        # Subscribe to connection events
        await self.message_broker.subscribe("connection.*", self._handle_connection_event)
        
        # Subscribe to state change events
        await self.message_broker.subscribe("state.*", self._handle_state_event)
        
        # Start background tasks
        self._sync_task = asyncio.create_task(self._sync_loop())
        self._presence_task = asyncio.create_task(self._presence_loop())
        
        logger.info("StateSyncService started")
    
    async def stop(self) -> None:
        """Stop the state synchronization service"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel background tasks
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        
        if self._presence_task:
            self._presence_task.cancel()
            try:
                await self._presence_task
            except asyncio.CancelledError:
                pass
        
        # Unsubscribe from events
        await self.message_broker.unsubscribe("connection.*", self._handle_connection_event)
        await self.message_broker.unsubscribe("state.*", self._handle_state_event)
        
        logger.info("StateSyncService stopped")
    
    async def register_client(self, client_id: str, connection_id: str, 
                            initial_state: Optional[Dict[str, Any]] = None,
                            user_info: Optional[Dict[str, Any]] = None) -> None:
        """
        Register a new client for state synchronization
        
        Args:
            client_id: Unique client identifier
            connection_id: Connection identifier
            initial_state: Initial state from the client
            user_info: User information (user_id, username, etc.)
        """
        logger.info(f"Registering client {client_id} with connection {connection_id}")
        
        # Create client state snapshot
        state = initial_state or {}
        snapshot = StateSnapshot(
            client_id=client_id,
            timestamp=time.time(),
            state=state,
            version=self.global_version,
            checksum=self._calculate_checksum(state)
        )
        self.client_states[client_id] = snapshot
        
        # Create client presence
        presence = ClientPresence(
            client_id=client_id,
            connection_id=connection_id,
            user_id=user_info.get('user_id') if user_info else None,
            username=user_info.get('username') if user_info else None
        )
        self.client_presence[client_id] = presence
        
        # Send current state to the new client
        await self._send_state_sync(client_id, self._get_merged_state())
        
        # Notify other clients about presence change
        await self._broadcast_presence_update(client_id)
        
        logger.info(f"Client {client_id} registered successfully")
    
    async def unregister_client(self, client_id: str) -> None:
        """
        Unregister a client from state synchronization
        
        Args:
            client_id: Client identifier to unregister
        """
        logger.info(f"Unregistering client {client_id}")
        
        # Remove client state and presence
        self.client_states.pop(client_id, None)
        self.client_presence.pop(client_id, None)
        
        # Notify other clients about presence change
        await self._broadcast_presence_removal(client_id)
        
        logger.info(f"Client {client_id} unregistered successfully")
    
    async def apply_state_change(self, client_id: str, change: StateChange) -> bool:
        """
        Apply a state change from a client
        
        Args:
            client_id: Client that initiated the change
            change: State change to apply
            
        Returns:
            True if change was applied successfully, False if conflict detected
        """
        logger.debug(f"Applying state change from {client_id}: {change.path}")
        
        # Validate client exists
        if client_id not in self.client_states:
            logger.warning(f"Unknown client {client_id} attempting state change")
            return False
        
        # Update change metadata
        change.client_id = client_id
        change.version = self.global_version + 1
        change.timestamp = time.time()
        
        # Check for conflicts
        conflict = await self._detect_conflicts(change)
        if conflict:
            logger.info(f"Conflict detected for path {change.path}")
            # Handle conflict based on resolution strategy
            resolved_change = await self._resolve_conflict(conflict)
            if resolved_change:
                change = resolved_change
            else:
                return False
        
        # Apply the change
        success = await self._apply_change_to_state(change)
        if success:
            # Update global version
            self.global_version += 1
            
            # Add to history
            self.state_history.append(change)
            self._trim_history()
            
            # Update client state
            await self._update_client_state(client_id, change)
            
            # Broadcast to other clients
            await self._broadcast_state_change(change)
            
            logger.debug(f"State change applied successfully: {change.path}")
            return True
        
        logger.warning(f"Failed to apply state change: {change.path}")
        return False
    
    async def get_client_state(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current state for a specific client
        
        Args:
            client_id: Client identifier
            
        Returns:
            Client state dictionary or None if client not found
        """
        snapshot = self.client_states.get(client_id)
        return snapshot.state if snapshot else None
    
    async def get_merged_state(self) -> Dict[str, Any]:
        """
        Get the current merged state across all clients
        
        Returns:
            Merged state dictionary
        """
        return self._get_merged_state()
    
    async def get_client_presence(self, client_id: str) -> Optional[ClientPresence]:
        """
        Get presence information for a specific client
        
        Args:
            client_id: Client identifier
            
        Returns:
            Client presence information or None if client not found
        """
        return self.client_presence.get(client_id)
    
    async def get_all_presence(self) -> List[ClientPresence]:
        """
        Get presence information for all connected clients
        
        Returns:
            List of client presence information
        """
        return list(self.client_presence.values())
    
    async def update_client_presence(self, client_id: str, presence_data: Dict[str, Any]) -> None:
        """
        Update presence information for a client
        
        Args:
            client_id: Client identifier
            presence_data: Updated presence data
        """
        if client_id not in self.client_presence:
            logger.warning(f"Unknown client {client_id} updating presence")
            return
        
        presence = self.client_presence[client_id]
        
        # Update presence fields
        if 'active_file' in presence_data:
            presence.active_file = presence_data['active_file']
        if 'active_editor_selection' in presence_data:
            presence.active_editor_selection = presence_data['active_editor_selection']
        if 'viewing_files' in presence_data:
            presence.viewing_files = set(presence_data['viewing_files'])
        if 'cursor_position' in presence_data:
            presence.cursor_position = presence_data['cursor_position']
        if 'status' in presence_data:
            presence.status = presence_data['status']
        
        presence.last_activity = time.time()
        
        # Broadcast presence update
        await self._broadcast_presence_update(client_id)
    
    async def create_checkpoint(self, label: Optional[str] = None) -> int:
        """
        Create a state checkpoint for rollback purposes
        
        Args:
            label: Optional label for the checkpoint
            
        Returns:
            Checkpoint version number
        """
        checkpoint_version = self.global_version
        self.state_checkpoints[checkpoint_version] = {
            'state': self._get_merged_state(),
            'timestamp': time.time(),
            'label': label or f"checkpoint_{checkpoint_version}"
        }
        
        logger.info(f"Created state checkpoint at version {checkpoint_version}")
        return checkpoint_version
    
    async def rollback_to_checkpoint(self, checkpoint_version: int) -> bool:
        """
        Rollback state to a specific checkpoint
        
        Args:
            checkpoint_version: Checkpoint version to rollback to
            
        Returns:
            True if rollback was successful
        """
        if checkpoint_version not in self.state_checkpoints:
            logger.warning(f"Checkpoint version {checkpoint_version} not found")
            return False
        
        checkpoint = self.state_checkpoints[checkpoint_version]
        
        # Create rollback change
        rollback_change = StateChange(
            change_type=StateChangeType.UPDATE,
            path="",  # Root path for full state replacement
            old_value=self._get_merged_state(),
            new_value=checkpoint['state'],
            version=self.global_version + 1,
            client_id="system"
        )
        
        # Apply rollback
        success = await self._apply_change_to_state(rollback_change)
        if success:
            self.global_version += 1
            self.state_history.append(rollback_change)
            
            # Update all client states
            for client_id in self.client_states.keys():
                await self._update_client_state(client_id, rollback_change)
            
            # Broadcast rollback to all clients
            await self._broadcast_state_change(rollback_change)
            
            logger.info(f"Successfully rolled back to checkpoint {checkpoint_version}")
            return True
        
        logger.error(f"Failed to rollback to checkpoint {checkpoint_version}")
        return False
    
    # Private methods
    
    async def _handle_connection_event(self, message: Message) -> None:
        """Handle connection events from the connection manager"""
        if message.topic == "connection.client_connected":
            client_id = message.payload.get('client_id')
            connection_id = message.payload.get('connection_id')
            user_info = message.payload.get('user_info', {})
            if client_id and connection_id:
                await self.register_client(client_id, connection_id, user_info=user_info)
        
        elif message.topic == "connection.client_disconnected":
            client_id = message.payload.get('client_id')
            if client_id:
                await self.unregister_client(client_id)
    
    async def _handle_state_event(self, message: Message) -> None:
        """Handle state change events"""
        if message.topic == "state.change_request":
            client_id = message.payload.get('client_id')
            change_data = message.payload.get('change')
            
            if client_id and change_data:
                # Convert string change_type to enum if necessary
                if 'change_type' in change_data and isinstance(change_data['change_type'], str):
                    try:
                        change_data['change_type'] = StateChangeType(change_data['change_type'])
                    except ValueError:
                        logger.warning(f"Invalid change_type: {change_data['change_type']}")
                        return
                
                change = StateChange(**change_data)
                await self.apply_state_change(client_id, change)
        
        elif message.topic == "state.presence_update":
            client_id = message.payload.get('client_id')
            presence_data = message.payload.get('presence_data')
            
            if client_id and presence_data:
                await self.update_client_presence(client_id, presence_data)
    
    async def _sync_loop(self) -> None:
        """Background task for state synchronization"""
        while self._running:
            try:
                # Perform periodic synchronization tasks
                await self._cleanup_stale_presence()
                await self._optimize_state_storage()
                
                await asyncio.sleep(self.sync_interval)
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                await asyncio.sleep(1.0)
    
    async def _presence_loop(self) -> None:
        """Background task for presence management"""
        while self._running:
            try:
                current_time = time.time()
                stale_clients = []
                
                for client_id, presence in self.client_presence.items():
                    if current_time - presence.last_activity > self.presence_timeout:
                        stale_clients.append(client_id)
                
                # Mark stale clients as away
                for client_id in stale_clients:
                    if self.client_presence[client_id].status != "away":
                        self.client_presence[client_id].status = "away"
                        await self._broadcast_presence_update(client_id)
                
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in presence loop: {e}")
                await asyncio.sleep(5.0)
    
    def _get_merged_state(self) -> Dict[str, Any]:
        """Get the current merged state from all clients"""
        if not self.client_states:
            return {}
        
        # For now, use a simple merge strategy
        # In a real implementation, this would be more sophisticated
        merged = {}
        
        # Get the most recent state
        latest_state = None
        latest_timestamp = 0
        
        for snapshot in self.client_states.values():
            if snapshot.timestamp > latest_timestamp:
                latest_timestamp = snapshot.timestamp
                latest_state = snapshot.state
        
        return latest_state or {}
    
    def _calculate_checksum(self, state: Dict[str, Any]) -> str:
        """Calculate a checksum for state data"""
        import hashlib
        state_json = json.dumps(state, sort_keys=True)
        return hashlib.md5(state_json.encode()).hexdigest()
    
    async def _detect_conflicts(self, change: StateChange) -> Optional[ConflictInfo]:
        """Detect conflicts with pending changes"""
        # Look for recent changes to the same path
        recent_changes = [
            c for c in self.state_history[-10:]  # Check last 10 changes
            if c.path == change.path and c.client_id != change.client_id
            and time.time() - c.timestamp < 5.0  # Within 5 seconds
        ]
        
        if recent_changes:
            conflict = ConflictInfo(
                path=change.path,
                changes=recent_changes + [change],
                resolution_strategy=self.conflict_resolution_strategy
            )
            self.conflicts[conflict.conflict_id] = conflict
            return conflict
        
        return None
    
    async def _resolve_conflict(self, conflict: ConflictInfo) -> Optional[StateChange]:
        """Resolve a detected conflict"""
        if conflict.resolution_strategy == ConflictResolution.LAST_WRITER_WINS:
            # Return the most recent change
            latest_change = max(conflict.changes, key=lambda c: c.timestamp)
            conflict.resolved = True
            conflict.resolution_timestamp = time.time()
            conflict.resolution_result = latest_change.new_value
            return latest_change
        
        elif conflict.resolution_strategy == ConflictResolution.FIRST_WRITER_WINS:
            # Return the earliest change
            earliest_change = min(conflict.changes, key=lambda c: c.timestamp)
            conflict.resolved = True
            conflict.resolution_timestamp = time.time()
            conflict.resolution_result = earliest_change.new_value
            return earliest_change
        
        # For other strategies, manual resolution would be required
        return None
    
    async def _apply_change_to_state(self, change: StateChange) -> bool:
        """Apply a change to the global state"""
        try:
            # This is a simplified implementation
            # In a real system, this would handle complex JSON path updates
            logger.debug(f"Applying change: {change.change_type.value} at {change.path}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply state change: {e}")
            return False
    
    async def _update_client_state(self, client_id: str, change: StateChange) -> None:
        """Update a client's state snapshot"""
        if client_id in self.client_states:
            snapshot = self.client_states[client_id]
            snapshot.version = change.version
            snapshot.timestamp = change.timestamp
            # In a real implementation, apply the change to snapshot.state
            snapshot.checksum = self._calculate_checksum(snapshot.state)
    
    async def _broadcast_state_change(self, change: StateChange) -> None:
        """Broadcast a state change to all connected clients except the originator"""
        # Send to all clients except the one that made the change
        for client_id in self.client_states.keys():
            if client_id != change.client_id:
                message = Message(
                    type=MessageType.NOTIFICATION,
                    topic=f"client.{client_id}.state.change_broadcast",
                    payload={
                        'change': change.to_dict(),
                        'global_version': self.global_version
                    }
                )
                await self.message_broker.publish(
                    f"client.{client_id}.state.change_broadcast",
                    {
                        'change': change.to_dict(),
                        'global_version': self.global_version
                    }
                )
    
    async def _broadcast_presence_update(self, client_id: str) -> None:
        """Broadcast presence update to all clients"""
        if client_id not in self.client_presence:
            return
        
        presence = self.client_presence[client_id]
        await self.message_broker.publish(
            "state.presence_update_broadcast",
            {
                'client_id': client_id,
                'presence': presence.to_dict()
            }
        )
    
    async def _broadcast_presence_removal(self, client_id: str) -> None:
        """Broadcast presence removal to all clients"""
        await self.message_broker.publish(
            "state.presence_removed",
            {'client_id': client_id}
        )
    
    async def _send_state_sync(self, client_id: str, state: Dict[str, Any]) -> None:
        """Send complete state synchronization to a specific client"""
        await self.message_broker.publish(
            f"client.{client_id}.state.full_sync",
            {
                'state': state,
                'version': self.global_version,
                'timestamp': time.time()
            }
        )
    
    def _trim_history(self) -> None:
        """Trim state history to maintain reasonable size"""
        if len(self.state_history) > self.history_retention:
            self.state_history = self.state_history[-self.history_retention:]
    
    async def _cleanup_stale_presence(self) -> None:
        """Clean up stale presence information"""
        current_time = time.time()
        stale_clients = []
        
        for client_id, presence in self.client_presence.items():
            if current_time - presence.last_activity > self.presence_timeout * 2:
                stale_clients.append(client_id)
        
        for client_id in stale_clients:
            await self.unregister_client(client_id)
    
    async def _optimize_state_storage(self) -> None:
        """Optimize state storage by cleaning up old checkpoints"""
        if len(self.state_checkpoints) > 10:  # Keep only last 10 checkpoints
            sorted_versions = sorted(self.state_checkpoints.keys())
            for version in sorted_versions[:-10]:
                del self.state_checkpoints[version]


# Global service instance
_state_sync_service: Optional[StateSyncService] = None


def get_state_sync_service() -> StateSyncService:
    """Get the global state synchronization service instance"""
    global _state_sync_service
    if _state_sync_service is None:
        _state_sync_service = StateSyncService()
    return _state_sync_service


async def shutdown_state_sync_service() -> None:
    """Shutdown the global state synchronization service"""
    global _state_sync_service
    if _state_sync_service is not None:
        await _state_sync_service.stop()
        _state_sync_service = None
