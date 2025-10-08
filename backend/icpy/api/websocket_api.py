"""
WebSocket API for icpy Backend

This module provides enhanced WebSocket functionality that integrates with the
message broker for real-time communication, supports multiple concurrent connections
with state synchronization, and includes connection recovery and message replay.

Key Features:
- Message broker integration for real-time communication
- Multiple concurrent connections with state synchronization
- Connection recovery and message replay capabilities
- JSON-RPC protocol support over WebSocket
- Session management and authentication
- Real-time event broadcasting
- Connection health monitoring

"""

import asyncio
import fnmatch
import json
import logging
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, Set, Callable, Deque
from fastapi import WebSocket, WebSocketDisconnect, status
from fastapi.websockets import WebSocketState

from ..core.message_broker import get_message_broker
from ..core.connection_manager import get_connection_manager
from ..core.protocol import JsonRpcRequest, JsonRpcResponse, ProtocolError, ErrorCode
from ..services import get_workspace_service, get_filesystem_service, get_terminal_service, get_code_execution_service, get_preview_service

logger = logging.getLogger(__name__)

# Global service instance
_websocket_api = None


class WebSocketConnectionState(Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class WebSocketMessage:
    """Represents a WebSocket message."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "message"
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    session_id: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class WebSocketConnection:
    """Represents a WebSocket connection."""
    id: str
    websocket: WebSocket
    state: WebSocketConnectionState
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    message_queue: Deque[WebSocketMessage] = field(default_factory=lambda: deque(maxlen=100))
    subscriptions: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert connection to dictionary representation."""
        return {
            'id': self.id,
            'state': self.state.value,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'created_at': self.created_at,
            'last_activity': self.last_activity,
            'message_queue_size': len(self.message_queue),
            'subscriptions': list(self.subscriptions)
        }


class WebSocketAPI:
    """Enhanced WebSocket API with message broker integration.
    
    This class provides comprehensive WebSocket functionality including:
    - Message broker integration for real-time communication
    - Multiple concurrent connections with state synchronization
    - Connection recovery and message replay capabilities
    - JSON-RPC protocol support over WebSocket
    - Session management and authentication
    - Real-time event broadcasting
    - Connection health monitoring
    """

    def __init__(self):
        """Initialize the WebSocket API."""
        self.message_broker = None
        self.connection_manager = None
        
        # Services
        self.workspace_service = None
        self.filesystem_service = None
        self.terminal_service = None
        
        # Active connections
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)  # user_id -> connection_ids
        self.session_connections: Dict[str, Set[str]] = defaultdict(set)  # session_id -> connection_ids
        
        # Message history for replay
        self.message_history: Dict[str, Deque[WebSocketMessage]] = defaultdict(lambda: deque(maxlen=1000))
        
        # Statistics
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'reconnections': 0,
            'authentication_attempts': 0,
            'authentication_successes': 0,
            'startup_time': 0.0
        }
        
        # Configuration
        self.max_connections = 1000
        self.message_timeout = 30.0
        self.connection_timeout = 3600.0  # 1 hour
        self.cleanup_interval = 300.0  # 5 minutes
        
        logger.info("WebSocketAPI initialized")

    async def initialize(self):
        """Initialize the WebSocket API.
        
        Sets up message broker connections and initializes services.
        """
        start_time = time.time()
        
        # Get dependencies
        self.message_broker = await get_message_broker()
        self.connection_manager = await get_connection_manager()
        
        # Get services
        self.workspace_service = await get_workspace_service()
        self.filesystem_service = await get_filesystem_service()
        self.terminal_service = await get_terminal_service()
        
        # Subscribe to message broker events
        await self.message_broker.subscribe('ws.*', self._handle_websocket_event)
        await self.message_broker.subscribe('workspace.*', self._handle_workspace_event)
        await self.message_broker.subscribe('fs.*', self._handle_filesystem_event)
        await self.message_broker.subscribe('terminal.*', self._handle_terminal_event)
        await self.message_broker.subscribe('agents.*', self._handle_agent_event)
        # Subscribe to hop events for SSH context switching notifications
        await self.message_broker.subscribe('hop.*', self._handle_hop_event)
        await self.message_broker.subscribe('scm.*', self._handle_scm_event)
        
        # Start background tasks
        asyncio.create_task(self._cleanup_connections_task())
        asyncio.create_task(self._heartbeat_task())
        
        # Publish initialization event
        await self.message_broker.publish('websocket.service_initialized', {
            'service': 'websocket',
            'timestamp': time.time(),
            'max_connections': self.max_connections
        })
        
        self.stats['startup_time'] = time.time() - start_time
        logger.info(f"WebSocketAPI initialized in {self.stats['startup_time']:.3f}s")

    async def shutdown(self):
        """Shutdown the WebSocket API.
        
        Disconnects all connections and cleans up resources.
        """
        logger.info("Shutting down WebSocketAPI...")
        
        # Close all connections
        connection_ids = list(self.connections.keys())
        for connection_id in connection_ids:
            await self.disconnect_websocket(connection_id)
        
        # Clear data structures
        self.connections.clear()
        self.user_connections.clear()
        self.session_connections.clear()
        self.message_history.clear()
        
        # Publish shutdown event
        if self.message_broker:
            await self.message_broker.publish('websocket.service_shutdown', {
                'service': 'websocket',
                'timestamp': time.time()
            })
        
        logger.info("WebSocketAPI shutdown complete")

    async def connect_websocket(self, websocket: WebSocket, session_id: str = None, user_id: str = None) -> str:
        """Connect a WebSocket and initialize the connection.
        
        Args:
            websocket: The WebSocket connection
            session_id: Optional session ID
            user_id: Optional user ID
            
        Returns:
            Connection ID
            
        Raises:
            Exception: If connection fails
        """
        if len(self.connections) >= self.max_connections:
            raise Exception(f"Maximum number of connections ({self.max_connections}) reached")
        
        try:
            await websocket.accept()
            
            # Generate connection ID
            connection_id = str(uuid.uuid4())
            
            # Create connection object
            connection = WebSocketConnection(
                id=connection_id,
                websocket=websocket,
                state=WebSocketConnectionState.CONNECTED,
                session_id=session_id,
                user_id=user_id
            )
            
            # Store connection
            self.connections[connection_id] = connection
            if user_id:
                self.user_connections[user_id].add(connection_id)
            if session_id:
                self.session_connections[session_id].add(connection_id)
            
            # Apply safe default subscriptions so clients receive critical events even
            # if they miss initial subscribe timing on first load/reconnect.
            # Keep this conservative: filesystem events are needed by Explorer UI.
            # hop.* is needed for SSH Hop panel to maintain connection state across reconnects.
            default_topics = {"fs.*", "hop.*"}
            connection.subscriptions.update(default_topics)
            logger.info(f"[WS] Connection {connection_id} auto-subscribed to defaults: {sorted(default_topics)}")

            # Update statistics
            self.stats['total_connections'] += 1
            self.stats['active_connections'] = len(self.connections)
            
            # Send welcome message
            await self.send_message(connection_id, {
                'type': 'welcome',
                'connection_id': connection_id,
                'session_id': session_id,
                'user_id': user_id,
                'timestamp': time.time()
            })
            
            # Replay recent messages if session exists
            if session_id and session_id in self.message_history:
                await self._replay_messages(connection_id, session_id)
            
            # Publish connection event
            await self.message_broker.publish('websocket.connection_established', {
                'connection_id': connection_id,
                'session_id': session_id,
                'user_id': user_id,
                'timestamp': time.time()
            })
            
            logger.info(f"WebSocket connected: {connection_id} (session: {session_id}, user: {user_id})")
            return connection_id
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket: {e}")
            raise

    async def disconnect_websocket(self, connection_id: str):
        """Disconnect a WebSocket connection.
        
        Args:
            connection_id: The connection ID
        """
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        
        try:
            # Close WebSocket if still open
            if connection.websocket.client_state == WebSocketState.CONNECTED:
                await connection.websocket.close()
            
            # Remove from tracking
            if connection.user_id:
                self.user_connections[connection.user_id].discard(connection_id)
                if not self.user_connections[connection.user_id]:
                    del self.user_connections[connection.user_id]
            
            if connection.session_id:
                self.session_connections[connection.session_id].discard(connection_id)
                if not self.session_connections[connection.session_id]:
                    del self.session_connections[connection.session_id]
            
            # Remove connection
            del self.connections[connection_id]
            
            # Update statistics
            self.stats['active_connections'] = len(self.connections)
            
            # Publish disconnection event
            await self.message_broker.publish('websocket.connection_closed', {
                'connection_id': connection_id,
                'session_id': connection.session_id,
                'user_id': connection.user_id,
                'timestamp': time.time()
            })
            
            logger.info(f"WebSocket disconnected: {connection_id}")
            
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket {connection_id}: {e}")

    async def handle_websocket_message(self, connection_id: str, message: str):
        """Handle incoming WebSocket message.
        
        Args:
            connection_id: The connection ID
            message: The message string
        """
        if connection_id not in self.connections:
            logger.error(f"Message from unknown connection: {connection_id}")
            return
        
        connection = self.connections[connection_id]
        connection.last_activity = time.time()
        
        try:
            # Parse message
            data = json.loads(message)
            
            # Update statistics
            self.stats['messages_received'] += 1
            
            # Handle different message types
            message_type = data.get('type', 'unknown')
            logger.debug(f"[WebSocketAPI] Processing message type: {message_type} from connection {connection_id}")
            
            if message_type == 'ping':
                await self._handle_ping(connection_id, data)
            elif message_type == 'subscribe':
                logger.debug(f"[WebSocketAPI] Handling subscription request: {data}")
                await self._handle_subscribe(connection_id, data)
            elif message_type == 'unsubscribe':
                await self._handle_unsubscribe(connection_id, data)
            elif message_type == 'json-rpc':
                await self._handle_jsonrpc_message(connection_id, data)
            elif message_type == 'jsonrpc':
                await self._handle_jsonrpc(connection_id, data)
            elif message_type == 'authenticate':
                await self._handle_authenticate(connection_id, data)
            elif message_type == 'execute':
                await self._handle_execute(connection_id, data)
            elif message_type == 'execute_streaming':
                await self._handle_execute_streaming(connection_id, data)
            elif message_type == 'preview':
                await self._handle_preview(connection_id, data)
            else:
                # Generic message handling
                logger.debug(f"[WebSocketAPI] Handling generic message: {data}")
                await self._handle_generic_message(connection_id, data)
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from connection {connection_id}: {message}")
            await self.send_error(connection_id, "Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {e}")
            await self.send_error(connection_id, f"Internal error: {str(e)}")

    async def send_message(self, connection_id: str, data: Dict[str, Any]) -> bool:
        """Send a message to a specific connection.
        
        Args:
            connection_id: The connection ID
            data: The message data
            
        Returns:
            True if successful, False otherwise
        """
        if connection_id not in self.connections:
            logger.error(f"Attempted to send message to unknown connection: {connection_id}")
            return False
        
        connection = self.connections[connection_id]
        
        try:
            # Create message object
            message = WebSocketMessage(
                data=data,
                session_id=connection.session_id,
                user_id=connection.user_id
            )
            
            # Add to connection queue
            connection.message_queue.append(message)
            
            # Add to session history
            if connection.session_id:
                self.message_history[connection.session_id].append(message)
            
            # Send message
            await connection.websocket.send_text(json.dumps(data))
            
            # Update statistics
            self.stats['messages_sent'] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            await self.disconnect_websocket(connection_id)
            return False

    async def send_error(self, connection_id: str, error_message: str):
        """Send an error message to a connection.
        
        Args:
            connection_id: The connection ID
            error_message: The error message
        """
        await self.send_message(connection_id, {
            'type': 'error',
            'message': error_message,
            'timestamp': time.time()
        })

    async def broadcast_message(self, data: Dict[str, Any], user_id: str = None, session_id: str = None):
        """Broadcast a message to multiple connections.
        
        Args:
            data: The message data
            user_id: Optional user ID to broadcast to
            session_id: Optional session ID to broadcast to
        """
        target_connections = set()
        
        if user_id:
            target_connections.update(self.user_connections.get(user_id, set()))
        elif session_id:
            target_connections.update(self.session_connections.get(session_id, set()))
        else:
            # Broadcast to all connections
            target_connections.update(self.connections.keys())
        
        # Send to all target connections
        for connection_id in target_connections:
            await self.send_message(connection_id, data)

    async def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a connection.
        
        Args:
            connection_id: The connection ID
            
        Returns:
            Connection information or None if not found
        """
        if connection_id not in self.connections:
            return None
        
        connection = self.connections[connection_id]
        return connection.to_dict()

    async def list_connections(self, user_id: str = None, session_id: str = None) -> List[Dict[str, Any]]:
        """List connections.
        
        Args:
            user_id: Optional user ID filter
            session_id: Optional session ID filter
            
        Returns:
            List of connection information
        """
        connections = []
        
        for connection in self.connections.values():
            if user_id and connection.user_id != user_id:
                continue
            if session_id and connection.session_id != session_id:
                continue
            connections.append(connection.to_dict())
        
        return connections

    async def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket API statistics.
        
        Returns:
            Dictionary containing service statistics
        """
        return {
            **self.stats,
            'active_connections': len(self.connections),
            'user_connections': len(self.user_connections),
            'session_connections': len(self.session_connections),
            'max_connections': self.max_connections,
            'message_history_size': sum(len(history) for history in self.message_history.values()),
            'timestamp': time.time()
        }

    async def _handle_ping(self, connection_id: str, data: Dict[str, Any]):
        """Handle ping message."""
        await self.send_message(connection_id, {
            'type': 'pong',
            'timestamp': time.time()
        })

    async def _handle_subscribe(self, connection_id: str, data: Dict[str, Any]):
        """Handle subscription message."""
        logger.debug(f"[WebSocketAPI] Processing subscription for connection {connection_id}: {data}")
        
        if connection_id not in self.connections:
            logger.warning(f"[WebSocketAPI] Connection {connection_id} not found for subscription")
            return
        
        connection = self.connections[connection_id]
        topics = data.get('topics', [])
        
        if isinstance(topics, str):
            topics = [topics]
        
        logger.debug(f"[WebSocketAPI] Adding subscriptions {topics} to connection {connection_id}")
        
        for topic in topics:
            connection.subscriptions.add(topic)
        
        logger.info(f"[WS] Connection {connection_id} subscribed to topics: {topics}")
        
        await self.send_message(connection_id, {
            'type': 'subscribed',
            'topics': topics,
            'timestamp': time.time()
        })

    async def _handle_unsubscribe(self, connection_id: str, data: Dict[str, Any]):
        """Handle unsubscription message."""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        topics = data.get('topics', [])
        
        if isinstance(topics, str):
            topics = [topics]
        
        for topic in topics:
            connection.subscriptions.discard(topic)
        
        await self.send_message(connection_id, {
            'type': 'unsubscribed',
            'topics': topics,
            'timestamp': time.time()
        })

    async def _handle_jsonrpc_message(self, connection_id: str, data: Dict[str, Any]):
        """Handle JSON-RPC message from frontend WebSocket service."""
        try:
            payload = data.get('payload', {})
            method = payload.get('method')
            params = payload.get('params', {})
            
            # Handle JSON-RPC notifications
            if method == 'subscribe':
                await self._handle_subscribe(connection_id, params)
            elif method == 'unsubscribe':
                await self._handle_unsubscribe(connection_id, params)
            else:
                # For other JSON-RPC methods, use the existing handler
                await self._handle_jsonrpc(connection_id, data)
                
        except Exception as e:
            logger.error(f"Error handling JSON-RPC message from {connection_id}: {e}")
            await self.send_error(connection_id, f"Invalid JSON-RPC message: {str(e)}")

    async def _handle_jsonrpc(self, connection_id: str, data: Dict[str, Any]):
        """Handle JSON-RPC message."""
        try:
            # Parse JSON-RPC request
            request = JsonRpcRequest.from_dict(data.get('request', {}))
            
            # Process through connection manager
            response = await self.connection_manager.handle_request(request)
            
            # Send response
            await self.send_message(connection_id, {
                'type': 'jsonrpc_response',
                'response': response.to_dict(),
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.error(f"Error handling JSON-RPC from {connection_id}: {e}")
            error_response = ProtocolError(
                code=ErrorCode.INTERNAL_ERROR.value,
                message=str(e)
            )
            await self.send_message(connection_id, {
                'type': 'jsonrpc_response',
                'response': error_response.to_dict(),
                'timestamp': time.time()
            })

    async def _handle_authenticate(self, connection_id: str, data: Dict[str, Any]):
        """Handle authentication message."""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        
        # Update statistics
        self.stats['authentication_attempts'] += 1
        
        # Simple authentication (would be more complex in production)
        user_id = data.get('user_id')
        session_id = data.get('session_id')
        
        if user_id and session_id:
            # Update connection
            connection.user_id = user_id
            connection.session_id = session_id
            connection.state = WebSocketConnectionState.AUTHENTICATED
            
            # Update tracking
            self.user_connections[user_id].add(connection_id)
            self.session_connections[session_id].add(connection_id)
            
            # Update statistics
            self.stats['authentication_successes'] += 1
            
            await self.send_message(connection_id, {
                'type': 'authenticated',
                'user_id': user_id,
                'session_id': session_id,
                'timestamp': time.time()
            })
            
            # Replay messages
            await self._replay_messages(connection_id, session_id)
        else:
            await self.send_error(connection_id, "Authentication failed: missing user_id or session_id")

    async def _handle_execute(self, connection_id: str, data: Dict[str, Any]):
        """Handle code execution message."""
        if connection_id not in self.connections:
            return
        
        try:
            # Extract execution parameters
            code = data.get('code', '')
            language = data.get('language', 'python')
            config_data = data.get('config', {})
            execution_id = data.get('execution_id', str(uuid.uuid4()))
            
            if not code:
                await self.send_error(connection_id, "No code provided for execution")
                return
            
            # Get code execution service
            code_execution_service = get_code_execution_service()
            
            # Ensure service is running
            if not code_execution_service.running:
                await code_execution_service.start()
            
            # Create execution config if provided
            execution_config = None
            if config_data:
                from ..services.code_execution_service import ExecutionConfig
                execution_config = ExecutionConfig(
                    timeout=config_data.get('timeout', 30.0),
                    max_output_size=config_data.get('max_output_size', 1024 * 1024),
                    working_directory=config_data.get('working_directory'),
                    environment=config_data.get('environment'),
                    sandbox=config_data.get('sandbox', True),
                    capture_output=config_data.get('capture_output', True),
                    real_time=False
                )
            
            # Execute code
            result = await code_execution_service.execute_code(
                code=code,
                language=language,
                config=execution_config
            )
            
            # Send result back
            await self.send_message(connection_id, {
                'type': 'execution_result',
                'execution_id': execution_id,
                'status': result.status.value,
                'output': result.output,
                'errors': result.errors,
                'execution_time': result.execution_time,
                'exit_code': result.exit_code,
                'language': result.language.value,
                'timestamp': time.time()
            })
            
            # Broadcast execution event to subscribers
            await self._broadcast_to_subscribers('code_execution.*', {
                'type': 'code_execution_completed',
                'execution_id': execution_id,
                'connection_id': connection_id,
                'status': result.status.value,
                'language': result.language.value,
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.error(f"Error executing code for connection {connection_id}: {e}")
            await self.send_error(connection_id, f"Code execution error: {str(e)}")

    async def _handle_execute_streaming(self, connection_id: str, data: Dict[str, Any]):
        """Handle streaming code execution message."""
        if connection_id not in self.connections:
            return
        
        try:
            # Extract execution parameters
            code = data.get('code', '')
            language = data.get('language', 'python')
            config_data = data.get('config', {})
            execution_id = data.get('execution_id', str(uuid.uuid4()))
            
            if not code:
                await self.send_error(connection_id, "No code provided for execution")
                return
            
            # Get code execution service
            code_execution_service = get_code_execution_service()
            
            # Ensure service is running
            if not code_execution_service.running:
                await code_execution_service.start()
            
            # Create execution config for streaming
            execution_config = None
            if config_data:
                from ..services.code_execution_service import ExecutionConfig
                execution_config = ExecutionConfig(
                    timeout=config_data.get('timeout', 30.0),
                    max_output_size=config_data.get('max_output_size', 1024 * 1024),
                    working_directory=config_data.get('working_directory'),
                    environment=config_data.get('environment'),
                    sandbox=config_data.get('sandbox', True),
                    capture_output=config_data.get('capture_output', True),
                    real_time=True
                )
            
            # Send execution started event
            await self.send_message(connection_id, {
                'type': 'execution_started',
                'execution_id': execution_id,
                'language': language,
                'timestamp': time.time()
            })
            
            # Execute code with streaming
            async for update in code_execution_service.execute_code_streaming(
                code=code,
                language=language,
                config=execution_config
            ):
                # Send streaming update
                await self.send_message(connection_id, {
                    'type': 'execution_update',
                    'execution_id': execution_id,
                    'update': update,
                    'timestamp': time.time()
                })
                
                # Broadcast streaming updates to subscribers
                await self._broadcast_to_subscribers('code_execution.*', {
                    'type': 'code_execution_update',
                    'execution_id': execution_id,
                    'connection_id': connection_id,
                    'update': update,
                    'timestamp': time.time()
                })
            
        except Exception as e:
            logger.error(f"Error in streaming execution for connection {connection_id}: {e}")
            await self.send_error(connection_id, f"Streaming execution error: {str(e)}")

    async def _handle_preview(self, connection_id: str, data: Dict[str, Any]):
        """Handle preview message."""
        if connection_id not in self.connections:
            return
        
        try:
            action = data.get('action', '')
            preview_id = data.get('preview_id')
            
            # Get preview service
            preview_service = get_preview_service()
            
            if action == 'create':
                files = data.get('files', {})
                project_type = data.get('project_type')
                
                if not files:
                    await self.send_error(connection_id, "No files provided for preview creation")
                    return
                
                # Create preview
                new_preview_id = await preview_service.create_preview(files, project_type)
                
                # Send success response
                await self.send_message(connection_id, {
                    'type': 'preview',
                    'action': 'created',
                    'preview_id': new_preview_id,
                    'timestamp': time.time()
                })
                
            elif action == 'update':
                if not preview_id:
                    await self.send_error(connection_id, "No preview_id provided for update")
                    return
                
                files = data.get('files', {})
                if not files:
                    await self.send_error(connection_id, "No files provided for preview update")
                    return
                
                # Update preview
                success = await preview_service.update_preview(preview_id, files)
                
                if success:
                    await self.send_message(connection_id, {
                        'type': 'preview',
                        'action': 'updated',
                        'preview_id': preview_id,
                        'timestamp': time.time()
                    })
                else:
                    await self.send_error(connection_id, f"Failed to update preview {preview_id}")
                    
            elif action == 'status':
                if not preview_id:
                    await self.send_error(connection_id, "No preview_id provided for status")
                    return
                
                # Get preview status
                status = await preview_service.get_preview_status(preview_id)
                
                if status:
                    await self.send_message(connection_id, {
                        'type': 'preview',
                        'action': 'status',
                        'preview_id': preview_id,
                        'status': status,
                        'timestamp': time.time()
                    })
                else:
                    await self.send_error(connection_id, f"Preview {preview_id} not found")
                    
            elif action == 'delete':
                if not preview_id:
                    await self.send_error(connection_id, "No preview_id provided for deletion")
                    return
                
                # Delete preview
                success = await preview_service.delete_preview(preview_id)
                
                if success:
                    await self.send_message(connection_id, {
                        'type': 'preview',
                        'action': 'deleted',
                        'preview_id': preview_id,
                        'timestamp': time.time()
                    })
                else:
                    await self.send_error(connection_id, f"Failed to delete preview {preview_id}")
                    
            else:
                await self.send_error(connection_id, f"Unknown preview action: {action}")
                
        except Exception as e:
            logger.error(f"Error handling preview message for connection {connection_id}: {e}")
            await self.send_error(connection_id, f"Preview error: {str(e)}")

    async def _handle_generic_message(self, connection_id: str, data: Dict[str, Any]):
        """Handle generic message by broadcasting to message broker."""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        
        # Publish to message broker
        await self.message_broker.publish('websocket.message_received', {
            'connection_id': connection_id,
            'user_id': connection.user_id,
            'session_id': connection.session_id,
            'data': data,
            'timestamp': time.time()
        })

    async def _replay_messages(self, connection_id: str, session_id: str):
        """Replay recent messages for a connection."""
        if session_id not in self.message_history:
            return
        
        messages = list(self.message_history[session_id])
        
        if messages:
            await self.send_message(connection_id, {
                'type': 'message_replay',
                'messages': [msg.data for msg in messages],
                'count': len(messages),
                'timestamp': time.time()
            })

    async def _handle_websocket_event(self, message):
        """Handle WebSocket-related events."""
        try:
            topic = message.topic
            data = message.payload
            
            if topic == 'websocket.broadcast':
                await self.broadcast_message(
                    data.get('data', {}),
                    user_id=data.get('user_id'),
                    session_id=data.get('session_id')
                )
            
        except Exception as e:
            logger.error(f"Error handling WebSocket event {message.topic}: {e}")

    async def _handle_workspace_event(self, message):
        """Handle workspace-related events."""
        try:
            # Broadcast workspace events to subscribed connections
            await self._broadcast_to_subscribers('workspace.*', {
                'type': 'workspace_event',
                'event': message.topic,
                'data': message.payload,
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.error(f"Error handling workspace event {message.topic}: {e}")

    async def _handle_filesystem_event(self, message):
        """Handle filesystem-related events."""
        try:
            logger.info(f"[WS] Handling filesystem event: {message.topic} - {message.payload}")
            
            # Broadcast filesystem events to subscribed connections
            await self._broadcast_to_subscribers('fs.*', {
                'type': 'filesystem_event',
                'event': message.topic,
                'data': message.payload,
                'timestamp': time.time()
            })
            
            logger.info(f"[WS] Filesystem event broadcasted: {message.topic}")
            
        except Exception as e:
            logger.error(f"[WS] Error handling filesystem event {message.topic}: {e}")

    async def _handle_terminal_event(self, message):
        """Handle terminal-related events."""
        try:
            # Broadcast terminal events to subscribed connections
            await self._broadcast_to_subscribers('terminal.*', {
                'type': 'terminal_event',
                'event': message.topic,
                'data': message.payload,
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.error(f"Error handling terminal event {message.topic}: {e}")

    async def _handle_agent_event(self, message):
        """Handle agent-related events."""
        try:
            logger.info(f"[WebSocketAPI] Handling agent event: {message.topic} - {message.payload}")
            
            # Broadcast agent events to all connected clients
            await self.broadcast_message({
                'type': 'agent_event',
                'event': message.topic,
                'data': message.payload,
                'timestamp': time.time()
            })
            
            logger.info(f"[WebSocketAPI] Agent event broadcasted: {message.topic}")
            
        except Exception as e:
            logger.error(f"Error handling agent event {message.topic}: {e}")

    async def _handle_hop_event(self, message):
        """Handle hop (SSH) events by broadcasting to interested clients.
        Allows frontend to subscribe to hop.* and receive status/credential changes.
        """
        try:
            await self._broadcast_to_subscribers('hop.*', {
                'type': 'hop_event',
                'event': message.topic,
                'data': message.payload,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"Error handling hop event {message.topic}: {e}")

    async def _handle_scm_event(self, message):
        """Handle source control (SCM) events by broadcasting to interested clients."""
        try:
            await self._broadcast_to_subscribers('scm.*', {
                'type': 'scm_event',
                'event': message.topic,
                'data': message.payload,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"Error handling SCM event {message.topic}: {e}")

    async def _broadcast_to_subscribers(self, topic_pattern: str, data: Dict[str, Any]):
        """Broadcast message to connections subscribed to a topic pattern."""
        logger.info(f"[WS] Broadcasting to subscribers of pattern '{topic_pattern}': {data}")
        
        sent_count = 0
        for connection in self.connections.values():
            for subscription in connection.subscriptions:
                # Subscriptions are usually exact topics; allow wildcard match either way
                matched = self._matches_pattern(subscription, topic_pattern) or self._matches_pattern(topic_pattern, subscription)
                if matched:
                    logger.info(f"[WS] Sending to connection {connection.id} (subscription: {subscription})")
                    await self.send_message(connection.id, data)
                    sent_count += 1
                    break
        
        logger.info(f"[WS] Broadcast sent to {sent_count} connections")

    def _matches_pattern(self, subscription: str, pattern: str) -> bool:
        """Check if subscription matches pattern."""
        import fnmatch
        # Check if the pattern matches the subscription
        # For example: pattern='fs.*' should match subscription='fs.file_created'
        return fnmatch.fnmatch(subscription, pattern)

    async def _cleanup_connections_task(self):
        """Background task to cleanup inactive connections."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                current_time = time.time()
                connections_to_cleanup = []
                
                for connection_id, connection in self.connections.items():
                    # Check for timeout
                    if current_time - connection.last_activity > self.connection_timeout:
                        connections_to_cleanup.append(connection_id)
                    
                    # Check if WebSocket is still open
                    if connection.websocket.client_state == WebSocketState.DISCONNECTED:
                        connections_to_cleanup.append(connection_id)
                
                # Cleanup connections
                for connection_id in connections_to_cleanup:
                    logger.info(f"Cleaning up inactive connection: {connection_id}")
                    await self.disconnect_websocket(connection_id)
                    
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

    async def _heartbeat_task(self):
        """Background task to send heartbeat messages."""
        while True:
            try:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                
                # Send heartbeat to all connections
                for connection_id in list(self.connections.keys()):
                    await self.send_message(connection_id, {
                        'type': 'heartbeat',
                        'timestamp': time.time()
                    })
                    
            except Exception as e:
                logger.error(f"Error in heartbeat task: {e}")


async def get_websocket_api() -> WebSocketAPI:
    """Get the global WebSocket API instance.
    
    Returns:
        The WebSocket API instance
    """
    global _websocket_api
    if _websocket_api is None:
        _websocket_api = WebSocketAPI()
        await _websocket_api.initialize()
    return _websocket_api


async def shutdown_websocket_api():
    """Shutdown the global WebSocket API instance."""
    global _websocket_api
    if _websocket_api is not None:
        await _websocket_api.shutdown()
        _websocket_api = None
