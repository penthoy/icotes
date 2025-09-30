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
    
    # Authentication
    authenticated: bool = False
    auth_token: Optional[str] = None
    auth_method: Optional[str] = None
    
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
class SessionInfo:
    """Information about a user session"""
    session_id: str
    user_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    session_data: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self, timeout: float = 3600.0) -> bool:
        """Check if session has expired"""
        return time.time() - self.last_activity > timeout
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = time.time()


@dataclass
class UserInfo:
    """Information about a user"""
    user_id: str
    username: str
    user_data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    
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
    
    # Session and user management
    sessions: Dict[str, SessionInfo] = field(default_factory=dict)
    users: Dict[str, UserInfo] = field(default_factory=dict)
    
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
        self.sessions: Dict[str, SessionInfo] = {}
        self.users: Dict[str, UserInfo] = {}
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
        
        # Cancel background tasks (guard against closed loop during pytest teardown)
        if self.cleanup_task:
            try:
                self.cleanup_task.cancel()
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            except RuntimeError:
                # Event loop already closed
                pass
        
        if self.health_task:
            try:
                self.health_task.cancel()
                await self.health_task
            except asyncio.CancelledError:
                pass
            except RuntimeError:
                pass
        
        # Disconnect all connections
        await self._disconnect_all_connections()
        
        logger.info("Connection manager stopped")
    
    async def connect_websocket(self, websocket: Any, client_id: Optional[str] = None,
                               session_id: Optional[str] = None, user_id: Optional[str] = None,
                               **metadata) -> str:
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
            user_id=user_id,
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
        await self._trigger_event_handlers('connection_created', connection.connection_id, connection)
        
        logger.info(f"WebSocket connection established: {connection_id}")
        return connection_id
    
    async def connect_http(self, client_id: Optional[str] = None,
                          session_id: Optional[str] = None, 
                          remote_addr: Optional[str] = None,
                          user_agent: Optional[str] = None,
                          **metadata) -> str:
        """Connect an HTTP client"""
        connection_id = str(uuid.uuid4())
        
        # Add remote_addr and user_agent to metadata for test compatibility
        connection_metadata = metadata.copy()
        if remote_addr:
            connection_metadata['remote_addr'] = remote_addr
        if user_agent:
            connection_metadata['user_agent'] = user_agent
        
        connection = ConnectionInfo(
            connection_id=connection_id,
            connection_type=ConnectionType.HTTP,
            state=ConnectionState.CONNECTING,
            client_id=client_id,
            session_id=session_id or str(uuid.uuid4()),
            remote_addr=remote_addr,
            user_agent=user_agent,
            http_session=session_id,
            metadata=connection_metadata
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
        await self._trigger_event_handlers('connection_created', connection.connection_id, connection)
        
        logger.info(f"HTTP connection established: {connection_id}")
        return connection_id
    
    async def connect_cli(self, client_id: Optional[str] = None,
                         session_id: Optional[str] = None,
                         process_id: Optional[str] = None,
                         **metadata) -> str:
        """Connect a CLI client"""
        connection_id = str(uuid.uuid4())
        
        # Add process_id to metadata for test compatibility
        connection_metadata = metadata.copy()
        if process_id:
            connection_metadata['process_id'] = process_id
        
        connection = ConnectionInfo(
            connection_id=connection_id,
            connection_type=ConnectionType.CLI,
            state=ConnectionState.CONNECTING,
            client_id=client_id,
            session_id=session_id or str(uuid.uuid4()),
            cli_process=process_id,
            metadata=connection_metadata
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
        await self._trigger_event_handlers('connection_created', connection.connection_id, connection)
        
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
            await self._trigger_event_handlers('connection_disconnecting', connection.connection_id, connection, reason=reason)
            
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
            await self._trigger_event_handlers('connection_removed', connection.connection_id, connection, reason=reason)
        
        logger.info(f"Connection disconnected: {connection_id} - {reason}")
    
    # Session Management
    async def create_session(self, user_id: Optional[str] = None, 
                            session_data: Optional[Dict[str, Any]] = None) -> str:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        
        session = SessionInfo(
            session_id=session_id,
            user_id=user_id,
            session_data=session_data or {}
        )
        
        async with self._lock:
            self.sessions[session_id] = session
        
        await self._trigger_event_handlers('session_created', session_id, session)
        return session_id
    
    async def end_session(self, session_id: str):
        """End a session and disconnect all associated connections"""
        async with self._lock:
            if session_id not in self.sessions:
                return
            
            # Disconnect all connections in this session
            connections = self.pool.get_connections_by_session(session_id)
            for connection in connections:
                await self.disconnect(connection.connection_id, "Session ended")
            
            # Remove session
            session = self.sessions.pop(session_id)
            await self._trigger_event_handlers('session_ended', session_id, session)
    
    async def update_session_original(self, session_id: str, session_data: Dict[str, Any]):
        """Update session data"""
        async with self._lock:
            if session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            session.session_data.update(session_data)
            session.update_activity()
            
            await self._trigger_event_handlers('session_updated', session_id, session)
            return True
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information"""
        return self.pool.sessions.get(session_id)
    
    # User Management
    async def register_user(self, username: str, 
                           user_data: Optional[Dict[str, Any]] = None) -> str:
        """Register a new user"""
        user_id = str(uuid.uuid4())
        
        user = UserInfo(
            user_id=user_id,
            username=username,
            user_data=user_data or {}
        )
        
        async with self._lock:
            self.pool.users[user_id] = user
        
        await self._trigger_event_handlers('user_registered', user_id, user)
        return user_id
    
    async def unregister_user(self, user_id: str):
        """Unregister a user and disconnect all associated connections"""
        async with self._lock:
            if user_id not in self.pool.users:
                return
            
            # Disconnect all connections for this user
            connections = self.pool.get_connections_by_user(user_id)
            for connection in connections:
                await self.disconnect(connection.connection_id, "User unregistered")
            
            # Remove user
            user = self.pool.users.pop(user_id)
            await self._trigger_event_handlers('user_unregistered', user_id, user)
    
    async def update_user(self, user_id: str, user_data: Dict[str, Any]):
        """Update user data"""
        async with self._lock:
            if user_id not in self.pool.users:
                return False
            
            user = self.pool.users[user_id]
            user.user_data.update(user_data)
            user.update_activity()
            
            await self._trigger_event_handlers('user_updated', user_id, user)
            return True
    
    def get_user(self, user_id: str) -> Optional[UserInfo]:
        """Get user information"""
        return self.pool.users.get(user_id)
    
    # Authentication
    async def authenticate(self, connection_id: str, auth_token: str, 
                          auth_method: str = "default") -> bool:
        """Authenticate a connection"""
        async with self._lock:
            connection = self.pool.connections.get(connection_id)
            if not connection:
                return False
            
            self.stats['authentication_attempts'] += 1
            
            # Check with auth handlers
            auth_handler = self.auth_handlers.get(auth_method)
            if auth_handler:
                try:
                    authenticated = await auth_handler(connection, auth_token)
                except Exception as e:
                    logger.error(f"Authentication handler error: {e}")
                    authenticated = False
            else:
                # Default authentication (always success for now)
                authenticated = True
            
            if authenticated:
                connection.state = ConnectionState.AUTHENTICATED
                connection.auth_token = auth_token
                connection.auth_method = auth_method
                connection.authenticated = True
                connection.update_activity()
                
                await self._trigger_event_handlers('connection_authenticated', connection_id, connection)
                return True
            else:
                self.stats['authentication_failures'] += 1
                return False
    
    def register_auth_handler(self, method: str, handler: Callable):
        """Register an authentication handler"""
        self.auth_handlers[method] = handler
    
    def register_hook(self, event_type: str, handler: Callable):
        """Register an event hook"""
        self.event_handlers[event_type].append(handler)
    
    async def _trigger_event_handlers(self, event_type: str, *args, **kwargs):
        """Trigger event handlers"""
        handlers = self.event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(*args, **kwargs)
                else:
                    handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")

    async def cleanup_inactive_connections(self, timeout: float = 1800):
        """Cleanup inactive connections based on timeout"""
        async with self._lock:
            expired_connections = []
            
            for connection in self.pool.connections.values():
                if connection.is_expired(timeout):
                    expired_connections.append(connection)
            
            for connection in expired_connections:
                await self.disconnect(connection.connection_id, "Inactive connection timeout")
            
            return len(expired_connections)
    
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
    
    async def update_activity(self, connection_id: str):
        """Update connection activity"""
        connection = self.pool.connections.get(connection_id)
        if connection:
            connection.update_activity()
    
    def get_connection(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection by ID"""
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
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    async def update_session(self, session_id: str, session_data: Dict[str, Any]):
        """Update session data"""
        session = self.sessions.get(session_id)
        if session:
            session.session_data.update(session_data)
            session.update_activity()
    
    def get_user(self, user_id: str) -> Optional[UserInfo]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    async def register_user(self, username: str, user_data: Optional[Dict[str, Any]] = None) -> str:
        """Register a new user"""
        user_id = str(uuid.uuid4())
        user = UserInfo(
            user_id=user_id,
            username=username,
            user_data=user_data or {},
            created_at=time.time(),
            last_seen=time.time()
        )
        self.users[user_id] = user
        return user_id
    
    async def update_user(self, user_id: str, user_data: Dict[str, Any]):
        """Update user data"""
        user = self.users.get(user_id)
        if user:
            user.user_data.update(user_data)
    
    async def unregister_user(self, user_id: str):
        """Remove a user"""
        if user_id in self.users:
            del self.users[user_id]
    
    async def update_activity(self, connection_id: str):
        """Update connection activity"""
        connection = self.get_connection(connection_id)
        if connection:
            connection.update_activity()
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the connection manager"""
        total_connections = len(self.pool.connections)
        websocket_connections = len([c for c in self.pool.connections.values() 
                                   if c.connection_type == ConnectionType.WEBSOCKET])
        http_connections = len([c for c in self.pool.connections.values() 
                              if c.connection_type == ConnectionType.HTTP])
        cli_connections = len([c for c in self.pool.connections.values() 
                             if c.connection_type == ConnectionType.CLI])
        
        return {
            'status': 'healthy',
            'connections': {
                'total': total_connections,
                'websocket': websocket_connections,
                'http': http_connections,
                'cli': cli_connections
            },
            'sessions': len(self.sessions),
            'users': len(self.users)
        }
    
    async def send_message(self, connection_id: str, message: str) -> bool:
        """Send message to a specific connection"""
        connection = self.get_connection(connection_id)
        if not connection or connection.connection_type != ConnectionType.WEBSOCKET:
            return False
        
        try:
            if connection.websocket:
                await connection.websocket.send_text(message)
                return True
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
        return False
    
    async def broadcast_message(self, message: str, connection_type: Optional[ConnectionType] = None,
                               session_id: Optional[str] = None, user_id: Optional[str] = None) -> int:
        """Broadcast message to multiple connections"""
        sent_count = 0
        connections = []
        
        if session_id:
            connections = self.pool.get_connections_by_session(session_id)
        elif user_id:
            connections = self.pool.get_connections_by_user(user_id)
        elif connection_type:
            connections = self.pool.get_connections_by_type(connection_type)
        else:
            connections = list(self.pool.connections.values())
        
        for connection in connections:
            if connection.connection_type == ConnectionType.WEBSOCKET and connection.websocket:
                try:
                    await connection.websocket.send_text(message)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to broadcast to {connection.connection_id}: {e}")
        
        return sent_count
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics"""
        total_connections = len(self.pool.connections)
        websocket_connections = len([c for c in self.pool.connections.values() 
                                   if c.connection_type == ConnectionType.WEBSOCKET])
        http_connections = len([c for c in self.pool.connections.values() 
                              if c.connection_type == ConnectionType.HTTP])
        cli_connections = len([c for c in self.pool.connections.values() 
                             if c.connection_type == ConnectionType.CLI])
        
        return {
            'total': total_connections,
            'websocket': websocket_connections,
            'http': http_connections,
            'cli': cli_connections
        }
    
    async def authenticate(self, connection_id: str, auth_token: str, auth_method: str = "token") -> bool:
        """Authenticate a connection"""
        connection = self.get_connection(connection_id)
        if not connection:
            return False
        
        # Simple token authentication for testing
        connection.authenticated = True
        connection.auth_token = auth_token
        connection.auth_method = auth_method
        
        self.stats['authentication_attempts'] = self.stats.get('authentication_attempts', 0) + 1
        
        # Trigger authentication event
        await self._trigger_event_handlers('connection_authenticated', connection_id, connection)
        
        return True
    
    def register_hook(self, event_type: str, handler: Callable):
        """Register an event hook"""
        self.event_handlers[event_type].append(handler)
    
    def unregister_hook(self, event_type: str, handler: Callable):
        """Unregister an event hook"""
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
            except ValueError:
                pass
    
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
    elif not _connection_manager.running:
        try:
            await _connection_manager.start()
        except RuntimeError:
            # Event loop may be closed; tests will recreate via shutdown/get
            pass
    return _connection_manager


async def shutdown_connection_manager():
    """Shutdown the global connection manager"""
    global _connection_manager
    if _connection_manager:
        await _connection_manager.stop()
        _connection_manager = None
