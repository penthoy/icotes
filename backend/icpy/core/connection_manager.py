"""
Connection Manager for icpy Backend
Manages WebSocket, HTTP, and CLI connections with session tracking
Handles client authentication, authorization, and connection lifecycle
"""

import asyncio
import json
import logging
import time
import uuid
import weakref
from typing import Dict, List, Set, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict
from contextlib import asynccontextmanager

# WebSocket support
try:
    from fastapi import WebSocket, WebSocketDisconnect
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    WebSocket = None
    WebSocketDisconnect = None

logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    """Types of client connections"""
    WEBSOCKET = "websocket"
    HTTP = "http"
    CLI = "cli"


class ConnectionState(Enum):
    """Connection states"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class ConnectionInfo:
    """Information about a client connection"""
    connection_id: str
    connection_type: ConnectionType
    state: ConnectionState = ConnectionState.CONNECTING
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    
    # Client information
    client_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Connection metadata
    remote_addr: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Connection-specific data
    websocket: Optional[Any] = None  # WebSocket instance
    http_session: Optional[str] = None  # HTTP session identifier
    cli_process: Optional[str] = None  # CLI process identifier
    
    # Health monitoring
    ping_count: int = 0
    last_ping: Optional[float] = None
    last_pong: Optional[float] = None
    
    def is_active(self) -> bool:
        """Check if connection is active"""
        return self.state in [ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED]
    
    def is_expired(self, timeout: float = 300.0) -> bool:
        """Check if connection has expired due to inactivity"""
        return time.time() - self.last_activity > timeout
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = time.time()


@dataclass
class ConnectionPool:
    """Pool of connections with management capabilities"""
    connections: Dict[str, ConnectionInfo] = field(default_factory=dict)
    connections_by_type: Dict[ConnectionType, Set[str]] = field(default_factory=lambda: defaultdict(set))
    connections_by_session: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    connections_by_user: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    
    def add_connection(self, connection: ConnectionInfo):
        """Add a connection to the pool"""
        self.connections[connection.connection_id] = connection
        self.connections_by_type[connection.connection_type].add(connection.connection_id)
        
        if connection.session_id:
            self.connections_by_session[connection.session_id].add(connection.connection_id)
        
        if connection.user_id:
            self.connections_by_user[connection.user_id].add(connection.connection_id)
    
    def remove_connection(self, connection_id: str):
        """Remove a connection from the pool"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        
        # Remove from type mapping
        self.connections_by_type[connection.connection_type].discard(connection_id)
        
        # Remove from session mapping
        if connection.session_id:
            self.connections_by_session[connection.session_id].discard(connection_id)
            if not self.connections_by_session[connection.session_id]:
                del self.connections_by_session[connection.session_id]
        
        # Remove from user mapping
        if connection.user_id:
            self.connections_by_user[connection.user_id].discard(connection_id)
            if not self.connections_by_user[connection.user_id]:
                del self.connections_by_user[connection.user_id]
        
        # Remove main connection
        del self.connections[connection_id]
    
    def get_connections_by_type(self, connection_type: ConnectionType) -> List[ConnectionInfo]:
        """Get all connections of a specific type"""
        connection_ids = self.connections_by_type[connection_type]
        return [self.connections[cid] for cid in connection_ids if cid in self.connections]
    
    def get_connections_by_session(self, session_id: str) -> List[ConnectionInfo]:
        """Get all connections for a session"""
        connection_ids = self.connections_by_session.get(session_id, set())
        return [self.connections[cid] for cid in connection_ids if cid in self.connections]
    
    def get_connections_by_user(self, user_id: str) -> List[ConnectionInfo]:
        """Get all connections for a user"""
        connection_ids = self.connections_by_user.get(user_id, set())
        return [self.connections[cid] for cid in connection_ids if cid in self.connections]
    
    def get_active_connections(self) -> List[ConnectionInfo]:
        """Get all active connections"""
        return [conn for conn in self.connections.values() if conn.is_active()]
    
    def get_expired_connections(self, timeout: float = 300.0) -> List[ConnectionInfo]:
        """Get all expired connections"""
        return [conn for conn in self.connections.values() if conn.is_expired(timeout)]


class ConnectionManager:
    """
    Manages client connections with session tracking, authentication, and health monitoring
    """
    
    def __init__(self, 
                 connection_timeout: float = 300.0,
                 ping_interval: float = 30.0,
                 max_connections_per_user: int = 10):
        self.connection_timeout = connection_timeout
        self.ping_interval = ping_interval
        self.max_connections_per_user = max_connections_per_user
        
        self.pool = ConnectionPool()
        self.auth_handlers: Dict[str, Callable] = {}
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self.health_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Statistics
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'connections_by_type': defaultdict(int),
            'authentication_attempts': 0,
            'authentication_failures': 0,
            'disconnections': 0,
            'cleanup_runs': 0
        }
        
        # Thread safety
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Start the connection manager"""
        if self.running:
            return
        
        self.running = True
        
        # Start background tasks
        self.cleanup_task = asyncio.create_task(self._cleanup_expired_connections())
        self.health_task = asyncio.create_task(self._health_monitoring())
        
        logger.info("Connection manager started")
    
    async def stop(self):
        """Stop the connection manager"""
        if not self.running:
            return
        
        self.running = False
        
        # Cancel background tasks
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.health_task:
            self.health_task.cancel()
            try:
                await self.health_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all connections
        await self._disconnect_all_connections()
        
        logger.info("Connection manager stopped")
    
    async def connect_websocket(self, websocket: Any, client_id: Optional[str] = None,
                               session_id: Optional[str] = None, **metadata) -> str:
        """Connect a WebSocket client"""
        if not WEBSOCKET_AVAILABLE:
            raise RuntimeError("WebSocket support not available")
        
        connection_id = str(uuid.uuid4())
        
        # Extract connection info
        remote_addr = getattr(websocket.client, 'host', None) if hasattr(websocket, 'client') else None
        user_agent = websocket.headers.get('user-agent') if hasattr(websocket, 'headers') else None
        
        connection = ConnectionInfo(
            connection_id=connection_id,
            connection_type=ConnectionType.WEBSOCKET,
            state=ConnectionState.CONNECTING,
            client_id=client_id,
            session_id=session_id or str(uuid.uuid4()),
            remote_addr=remote_addr,
            user_agent=user_agent,
            websocket=websocket,
            metadata=metadata
        )
        
        async with self._lock:
            # Check connection limits
            if connection.session_id:
                existing_connections = self.pool.get_connections_by_session(connection.session_id)
                if len(existing_connections) >= self.max_connections_per_user:
                    raise ConnectionError(f"Maximum connections per session exceeded: {self.max_connections_per_user}")
            
            # Add to pool
            self.pool.add_connection(connection)
            
            # Update statistics
            self.stats['total_connections'] += 1
            self.stats['active_connections'] += 1
            self.stats['connections_by_type'][ConnectionType.WEBSOCKET] += 1
        
        # Set connection state
        connection.state = ConnectionState.CONNECTED
        connection.update_activity()
        
        # Fire connection event
        await self._fire_event('connection_established', connection)
        
        logger.info(f"WebSocket connection established: {connection_id}")
        return connection_id
    
    async def connect_http(self, client_id: Optional[str] = None,
                          session_id: Optional[str] = None, 
                          remote_addr: Optional[str] = None,
                          user_agent: Optional[str] = None,
                          **metadata) -> str:
        """Connect an HTTP client"""
        connection_id = str(uuid.uuid4())
        
        connection = ConnectionInfo(
            connection_id=connection_id,
            connection_type=ConnectionType.HTTP,
            state=ConnectionState.CONNECTING,
            client_id=client_id,
            session_id=session_id or str(uuid.uuid4()),
            remote_addr=remote_addr,
            user_agent=user_agent,
            http_session=session_id,
            metadata=metadata
        )
        
        async with self._lock:
            # Check connection limits
            if connection.session_id:
                existing_connections = self.pool.get_connections_by_session(connection.session_id)
                if len(existing_connections) >= self.max_connections_per_user:
                    raise ConnectionError(f"Maximum connections per session exceeded: {self.max_connections_per_user}")
            
            # Add to pool
            self.pool.add_connection(connection)
            
            # Update statistics
            self.stats['total_connections'] += 1
            self.stats['active_connections'] += 1
            self.stats['connections_by_type'][ConnectionType.HTTP] += 1
        
        # Set connection state
        connection.state = ConnectionState.CONNECTED
        connection.update_activity()
        
        # Fire connection event
        await self._fire_event('connection_established', connection)
        
        logger.info(f"HTTP connection established: {connection_id}")
        return connection_id
    
    async def connect_cli(self, client_id: Optional[str] = None,
                         session_id: Optional[str] = None,
                         process_id: Optional[str] = None,
                         **metadata) -> str:
        """Connect a CLI client"""
        connection_id = str(uuid.uuid4())
        
        connection = ConnectionInfo(
            connection_id=connection_id,
            connection_type=ConnectionType.CLI,
            state=ConnectionState.CONNECTING,
            client_id=client_id,
            session_id=session_id or str(uuid.uuid4()),
            cli_process=process_id,
            metadata=metadata
        )
        
        async with self._lock:
            # Check connection limits
            if connection.session_id:
                existing_connections = self.pool.get_connections_by_session(connection.session_id)
                if len(existing_connections) >= self.max_connections_per_user:
                    raise ConnectionError(f"Maximum connections per session exceeded: {self.max_connections_per_user}")
            
            # Add to pool
            self.pool.add_connection(connection)
            
            # Update statistics
            self.stats['total_connections'] += 1
            self.stats['active_connections'] += 1
            self.stats['connections_by_type'][ConnectionType.CLI] += 1
        
        # Set connection state
        connection.state = ConnectionState.CONNECTED
        connection.update_activity()
        
        # Fire connection event
        await self._fire_event('connection_established', connection)
        
        logger.info(f"CLI connection established: {connection_id}")
        return connection_id
    
    async def disconnect(self, connection_id: str, reason: str = "Normal disconnection"):
        """Disconnect a client"""
        async with self._lock:
            if connection_id not in self.pool.connections:
                return
            
            connection = self.pool.connections[connection_id]
            connection.state = ConnectionState.DISCONNECTING
            
            # Fire disconnection event
            await self._fire_event('connection_disconnecting', connection, reason=reason)
            
            # Close connection based on type
            if connection.connection_type == ConnectionType.WEBSOCKET and connection.websocket:
                try:
                    await connection.websocket.close()
                except Exception as e:
                    logger.warning(f"Error closing WebSocket: {e}")
            
            # Remove from pool
            self.pool.remove_connection(connection_id)
            
            # Update statistics
            self.stats['active_connections'] -= 1
            self.stats['disconnections'] += 1
            self.stats['connections_by_type'][connection.connection_type] -= 1
            
            connection.state = ConnectionState.DISCONNECTED
            
            # Fire disconnected event
            await self._fire_event('connection_disconnected', connection, reason=reason)
        
        logger.info(f"Connection disconnected: {connection_id} - {reason}")
    
    async def authenticate(self, connection_id: str, auth_token: str, 
                          auth_method: str = "default") -> bool:
        """Authenticate a connection"""
        async with self._lock:
            if connection_id not in self.pool.connections:
                return False
            
            connection = self.pool.connections[connection_id]
            
            # Update statistics
            self.stats['authentication_attempts'] += 1
            
            # Get auth handler
            auth_handler = self.auth_handlers.get(auth_method)
            if not auth_handler:
                logger.warning(f"No auth handler for method: {auth_method}")
                self.stats['authentication_failures'] += 1
                return False
            
            try:
                # Call auth handler
                auth_result = await auth_handler(connection, auth_token)
                
                if auth_result:
                    connection.state = ConnectionState.AUTHENTICATED
                    connection.update_activity()
                    
                    # Fire authentication event
                    await self._fire_event('connection_authenticated', connection)
                    
                    logger.info(f"Connection authenticated: {connection_id}")
                    return True
                else:
                    self.stats['authentication_failures'] += 1
                    logger.warning(f"Authentication failed: {connection_id}")
                    return False
                    
            except Exception as e:
                self.stats['authentication_failures'] += 1
                logger.error(f"Authentication error: {e}")
                return False
    
    async def update_activity(self, connection_id: str):
        """Update connection activity timestamp"""
        async with self._lock:
            if connection_id in self.pool.connections:
                self.pool.connections[connection_id].update_activity()
    
    async def send_message(self, connection_id: str, message: str) -> bool:
        """Send a message to a connection"""
        async with self._lock:
            if connection_id not in self.pool.connections:
                return False
            
            connection = self.pool.connections[connection_id]
            
            if not connection.is_active():
                return False
            
            try:
                if connection.connection_type == ConnectionType.WEBSOCKET and connection.websocket:
                    await connection.websocket.send_text(message)
                    connection.update_activity()
                    return True
                else:
                    # For HTTP and CLI, messages are typically handled differently
                    # This is a placeholder for future implementation
                    logger.warning(f"Message sending not implemented for {connection.connection_type}")
                    return False
                    
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                # Connection might be broken, schedule for cleanup
                await self.disconnect(connection_id, f"Send error: {str(e)}")
                return False
    
    async def broadcast_message(self, message: str, 
                               connection_type: Optional[ConnectionType] = None,
                               session_id: Optional[str] = None,
                               user_id: Optional[str] = None) -> int:
        """Broadcast a message to multiple connections"""
        sent_count = 0
        
        # Get target connections
        if session_id:
            connections = self.pool.get_connections_by_session(session_id)
        elif user_id:
            connections = self.pool.get_connections_by_user(user_id)
        elif connection_type:
            connections = self.pool.get_connections_by_type(connection_type)
        else:
            connections = self.pool.get_active_connections()
        
        # Send to all target connections
        for connection in connections:
            if await self.send_message(connection.connection_id, message):
                sent_count += 1
        
        return sent_count
    
    def get_connection(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection information"""
        return self.pool.connections.get(connection_id)
    
    def get_connections_by_type(self, connection_type: ConnectionType) -> List[ConnectionInfo]:
        """Get connections by type"""
        return self.pool.get_connections_by_type(connection_type)
    
    def get_connections_by_session(self, session_id: str) -> List[ConnectionInfo]:
        """Get connections by session"""
        return self.pool.get_connections_by_session(session_id)
    
    def get_connections_by_user(self, user_id: str) -> List[ConnectionInfo]:
        """Get connections by user"""
        return self.pool.get_connections_by_user(user_id)
    
    def register_auth_handler(self, method: str, handler: Callable):
        """Register an authentication handler"""
        self.auth_handlers[method] = handler
        logger.info(f"Registered auth handler: {method}")
    
    def register_event_handler(self, event: str, handler: Callable):
        """Register an event handler"""
        self.event_handlers[event].append(handler)
        logger.info(f"Registered event handler: {event}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics"""
        async with self._lock:
            return {
                **self.stats,
                'active_connections': len(self.pool.get_active_connections()),
                'total_connections_in_pool': len(self.pool.connections),
                'connections_by_type': {
                    str(conn_type): len(self.pool.get_connections_by_type(conn_type))
                    for conn_type in ConnectionType
                },
                'sessions': len(self.pool.connections_by_session),
                'users': len(self.pool.connections_by_user)
            }
    
    async def _fire_event(self, event: str, connection: ConnectionInfo, **kwargs):
        """Fire an event to all registered handlers"""
        handlers = self.event_handlers.get(event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(connection, **kwargs)
                else:
                    handler(connection, **kwargs)
            except Exception as e:
                logger.error(f"Error in event handler {event}: {e}")
    
    async def _cleanup_expired_connections(self):
        """Background task to cleanup expired connections"""
        while self.running:
            try:
                expired_connections = self.pool.get_expired_connections(self.connection_timeout)
                
                for connection in expired_connections:
                    await self.disconnect(connection.connection_id, "Connection timeout")
                
                if expired_connections:
                    logger.info(f"Cleaned up {len(expired_connections)} expired connections")
                
                self.stats['cleanup_runs'] += 1
                await asyncio.sleep(60)  # Run cleanup every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(10)
    
    async def _health_monitoring(self):
        """Background task for health monitoring and ping/pong"""
        while self.running:
            try:
                # Send pings to WebSocket connections
                websocket_connections = self.pool.get_connections_by_type(ConnectionType.WEBSOCKET)
                
                for connection in websocket_connections:
                    if connection.is_active() and connection.websocket:
                        try:
                            # Send ping
                            await connection.websocket.ping()
                            connection.ping_count += 1
                            connection.last_ping = time.time()
                            
                        except Exception as e:
                            logger.warning(f"Ping failed for {connection.connection_id}: {e}")
                            await self.disconnect(connection.connection_id, f"Ping failed: {str(e)}")
                
                await asyncio.sleep(self.ping_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(10)
    
    async def _disconnect_all_connections(self):
        """Disconnect all connections"""
        connection_ids = list(self.pool.connections.keys())
        for connection_id in connection_ids:
            await self.disconnect(connection_id, "Server shutdown")


# Global connection manager instance
_connection_manager: Optional[ConnectionManager] = None


async def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
        await _connection_manager.start()
    return _connection_manager


async def shutdown_connection_manager():
    """Shutdown the global connection manager"""
    global _connection_manager
    if _connection_manager:
        await _connection_manager.stop()
        _connection_manager = None
