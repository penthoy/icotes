"""
Chat Service for icpy Backend
Manages chat interactions between users and AI agents with message persistence and real-time communication
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import sqlite3
import aiosqlite
from pathlib import Path

# Internal imports
from ..core.message_broker import MessageBroker, get_message_broker, Message, MessageType as BrokerMessageType
from ..core.connection_manager import ConnectionManager, get_connection_manager
from ..services.agent_service import AgentService, get_agent_service, AgentSessionStatus

# Custom agent imports
try:
    from ..agent.custom_agent import call_custom_agent_stream, get_available_custom_agents
except ImportError:
    # Fallback functions if custom agent module is not available
    call_custom_agent_stream = lambda agent, msg, hist: iter([f"Custom agent {agent} not available"])
    get_available_custom_agents = lambda: []

logger = logging.getLogger(__name__)


class MessageSender(Enum):
    """Who sent the message"""
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class ChatMessageType(Enum):
    """Type of message"""
    MESSAGE = "message"
    STATUS = "status"
    ERROR = "error"
    TYPING = "typing"


@dataclass
class ChatMessage:
    """A chat message with metadata"""
    id: str
    content: str
    sender: MessageSender
    timestamp: str
    type: ChatMessageType = ChatMessageType.MESSAGE
    metadata: Dict[str, Any] = field(default_factory=dict)
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'content': self.content,
            'sender': self.sender.value,
            'timestamp': self.timestamp,
            'type': self.type.value,
            'metadata': self.metadata,
            'agent_id': self.agent_id,
            'session_id': self.session_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """Create from dictionary"""
        return cls(
            id=data['id'],
            content=data['content'],
            sender=MessageSender(data['sender']),
            timestamp=data['timestamp'],
            type=ChatMessageType(data.get('type', 'message')),
            metadata=data.get('metadata', {}),
            agent_id=data.get('agent_id'),
            session_id=data.get('session_id')
        )


@dataclass
class AgentStatus:
    """Current status of an agent"""
    available: bool
    name: str
    type: str
    capabilities: List[str]
    agent_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'available': self.available,
            'name': self.name,
            'type': self.type,
            'capabilities': self.capabilities,
            'agent_id': self.agent_id
        }


@dataclass
class ChatConfig:
    """Chat configuration"""
    agent_id: Optional[str] = None
    agent_name: str = "Assistant"
    system_prompt: str = "You are a helpful AI assistant."
    max_messages: int = 1000
    auto_scroll: bool = True
    enable_typing_indicators: bool = True
    message_retention_days: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'system_prompt': self.system_prompt,
            'max_messages': self.max_messages,
            'auto_scroll': self.auto_scroll,
            'enable_typing_indicators': self.enable_typing_indicators,
            'message_retention_days': self.message_retention_days
        }


class ChatService:
    """
    Chat Service for managing user-agent conversations
    
    Features:
    - Real-time WebSocket communication
    - Message persistence with SQLite
    - Agent integration and status management
    - Typing indicators and status updates
    - Message history and pagination
    - Error handling and reconnection support
    """
    
    def __init__(self, db_path: str = "chat.db"):
        self.db_path = db_path
        self.message_broker = get_message_broker()
        self.connection_manager = get_connection_manager()
        self.agent_service: Optional[AgentService] = None
        
        # Chat sessions and configuration
        self.chat_sessions: Dict[str, str] = {}  # connection_id -> session_id
        self.active_connections: Set[str] = set()
        self.websocket_connections: Dict[str, Any] = {}  # connection_id -> websocket
        self.config = ChatConfig()
        
        # Initialize database (only if event loop is running)
        try:
            asyncio.create_task(self._initialize_database())
        except RuntimeError:
            # No event loop running, will initialize later
            pass
        
        # Setup message broker subscriptions (only if broker is available)
        if hasattr(self.message_broker, 'subscribe'):
            self.message_broker.subscribe(BrokerMessageType.AGENT_STATUS_UPDATED, self._handle_agent_status_update)
            self.message_broker.subscribe(BrokerMessageType.AGENT_MESSAGE, self._handle_agent_message)
        
        logger.info("Chat service initialized")
    
    async def _initialize_database(self):
        """Initialize SQLite database for message persistence"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        sender TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        type TEXT DEFAULT 'message',
                        metadata TEXT DEFAULT '{}',
                        agent_id TEXT,
                        session_id TEXT,
                        created_at REAL DEFAULT (julianday('now'))
                    )
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp ON chat_messages(timestamp DESC)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_session ON chat_messages(session_id)
                """)
                
                await db.commit()
                logger.info("Chat database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize chat database: {e}")
    
    async def connect_websocket(self, websocket_id: str) -> str:
        """Connect a WebSocket client to chat service"""
        session_id = str(uuid.uuid4())
        self.chat_sessions[websocket_id] = session_id
        self.active_connections.add(websocket_id)
        
        # Send initial status
        try:
            await self._send_agent_status(websocket_id)
        except Exception as e:
            logger.warning(f"Could not send initial agent status: {e}")
        
        logger.info(f"Chat WebSocket connected: {websocket_id} -> session {session_id}")
        return session_id
    
    async def disconnect_websocket(self, websocket_id: str):
        """Disconnect a WebSocket client from chat service"""
        if websocket_id in self.chat_sessions:
            session_id = self.chat_sessions.pop(websocket_id)
            logger.info(f"Chat WebSocket disconnected: {websocket_id} from session {session_id}")
        
        self.active_connections.discard(websocket_id)
    
    async def _send_websocket_message(self, websocket_id: str, message_data: dict):
        """Send a message to a specific WebSocket connection"""
        websocket = self.websocket_connections.get(websocket_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps(message_data))
            except Exception as e:
                logger.error(f"Failed to send WebSocket message to {websocket_id}: {e}")
                # Remove the failed connection
                if websocket_id in self.websocket_connections:
                    del self.websocket_connections[websocket_id]
                if websocket_id in self.chat_sessions:
                    del self.chat_sessions[websocket_id]
    
    async def handle_user_message(self, websocket_id: str, content: str, metadata: Dict[str, Any] = None) -> ChatMessage:
        """Handle a message from the user with support for agent routing"""
        session_id = self.chat_sessions.get(websocket_id)
        if not session_id:
            raise ValueError("WebSocket not connected to chat session")
        
        # Extract agent type from metadata for routing
        agent_type = None
        if metadata and 'agentType' in metadata:
            agent_type = metadata['agentType']
        
        # Create user message
        message = ChatMessage(
            id=str(uuid.uuid4()),
            content=content,
            sender=MessageSender.USER,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
            session_id=session_id
        )
        
        # Store message
        await self._store_message(message)
        
        # Send to connected clients
        await self._broadcast_message(message)
        
        # Process with appropriate agent based on type
        if agent_type and agent_type.lower() in ['personalagent', 'openaidemoagent', 'openrouteragent']:
            # Route to custom agent
            await self._process_with_custom_agent(message, agent_type)
        else:
            # Route to default ICPY agent service
            await self._process_with_agent(message)
        
        return message
    
    async def _process_with_agent(self, user_message: ChatMessage):
        """Process user message with the configured agent"""
        try:
            if not self.agent_service:
                self.agent_service = await get_agent_service()
            
            if not self.config.agent_id:
                logger.warning("⚠️ No agent ID configured, sending demo response")
                # Send default response if no agent configured - simple echo/demo response
                await self._send_ai_response(
                    user_message.session_id,
                    f"Echo: {user_message.content}\n\n(This is a demo response. To use AI agents, configure an agent in the system.)",
                    user_message.id
                )
                return
            
            # Send typing indicator
            await self._send_typing_indicator(user_message.session_id, True)
            
            # Get agent session
            agent_sessions = self.agent_service.get_agent_sessions()
            
            agent_session = None
            for session in agent_sessions:
                if session.agent_id == self.config.agent_id:
                    agent_session = session
                    break
            
            if not agent_session:
                logger.error(f"❌ No agent session found for agent_id: {self.config.agent_id}")
                await self._send_ai_response(
                    user_message.session_id,
                    "I'm sorry, the AI agent is currently unavailable. Please try again later.",
                    user_message.id
                )
                await self._send_typing_indicator(user_message.session_id, False)
                return
                
            if agent_session.status.value not in ['ready', 'running']:
                logger.error(f"❌ Agent session not ready. Status: {agent_session.status.value}")
                await self._send_ai_response(
                    user_message.session_id,
                    "I'm sorry, the AI agent is currently unavailable. Please try again later.",
                    user_message.id
                )
                await self._send_typing_indicator(user_message.session_id, False)
                return
            
            # Execute agent task with streaming
            logger.info(f"🚀 Executing streaming agent task for session: {agent_session.session_id}")
            task_description = user_message.content  # Use the user's message as the task
            task_context = {
                'type': 'chat_response',
                'session_id': user_message.session_id,
                'system_prompt': self.config.system_prompt,
                'user_message': user_message.content
            }
            logger.info(f"📝 Task description: {task_description}")
            logger.info(f"📝 Task context: {task_context}")
            
            # Stream the response using the new streaming method
            await self._execute_streaming_agent_task(
                agent_session.session_id,
                task_description,
                task_context,
                user_message.session_id,
                user_message.id
            )
            
            await self._send_typing_indicator(user_message.session_id, False)
            
        except Exception as e:
            logger.error(f"� Error processing message with agent: {e}")
            logger.exception("Full traceback:")
            await self._send_ai_response(
                user_message.session_id,
                f"I'm sorry, I encountered an error. Please try again. Error: {str(e)}",
                user_message.id
            )
            await self._send_typing_indicator(user_message.session_id, False)
    
    async def _execute_streaming_agent_task(self, agent_session_id: str, task: str, 
                                           context: dict, chat_session_id: str, reply_to_id: str):
        """Execute agent task with streaming response to chat"""
        try:
            # Get the agent instance
            agent = self.agent_service.active_agents.get(agent_session_id)
            if not agent:
                raise ValueError(f"Agent instance for session {agent_session_id} not found")
            
            # Update session status
            self.agent_service.agent_sessions[agent_session_id].status = AgentSessionStatus.RUNNING
            self.agent_service.agent_sessions[agent_session_id].last_activity = time.time()
            
            # Prepare streaming response
            full_content = ""
            message_id = str(uuid.uuid4())
            is_first_chunk = True
            
            # Execute task and stream results
            async for message in agent.execute(task, context):
                if message.message_type == "text":
                    # Send stream start for first chunk
                    if is_first_chunk:
                        await self._send_streaming_start(
                            chat_session_id, 
                            message_id,
                            reply_to_id
                        )
                        is_first_chunk = False
                    
                    # Send incremental update
                    await self._send_streaming_chunk(
                        chat_session_id,
                        message_id,
                        message.content,  # Send only the new chunk
                        reply_to_id
                    )
                    full_content += message.content
                elif message.message_type == "error":
                    logger.error(f"Agent error during streaming: {message.content}")
                    # Send error as part of streaming instead of separate message
                    error_content = f"I'm sorry, I encountered an error: {message.content}"
                    
                    # If no content streamed yet, start the stream
                    if is_first_chunk:
                        await self._send_streaming_start(
                            chat_session_id, 
                            message_id,
                            reply_to_id
                        )
                        is_first_chunk = False
                    
                    # Send error as streaming chunk
                    await self._send_streaming_chunk(
                        chat_session_id,
                        message_id,
                        error_content,
                        reply_to_id
                    )
                    full_content += error_content
                    
                    # End the stream and store the message
                    await self._send_streaming_end(
                        chat_session_id,
                        message_id,
                        reply_to_id
                    )
                    
                    # Store the final error message for persistence
                    final_message = ChatMessage(
                        id=message_id,
                        content=full_content,
                        sender=MessageSender.AI,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        agent_id=self.config.agent_id,
                        session_id=chat_session_id,
                        metadata={'reply_to': reply_to_id, 'streaming_complete': True, 'has_error': True}
                    )
                    await self._store_message(final_message)
                    return
            
            # Send stream end
            await self._send_streaming_end(
                chat_session_id,
                message_id,
                reply_to_id
            )
            
            # Store the final complete message for persistence (do not broadcast)
            # The frontend already has the complete message from streaming
            final_message = ChatMessage(
                id=message_id,
                content=full_content,
                sender=MessageSender.AI,
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent_id=self.config.agent_id,
                session_id=chat_session_id,
                metadata={'reply_to': reply_to_id, 'streaming_complete': True}
            )
            await self._store_message(final_message)
            # Note: We don't broadcast this final message since frontend already has it from streaming
            
            # Update session status back to ready
            self.agent_service.agent_sessions[agent_session_id].status = AgentSessionStatus.READY
            self.agent_service.agent_sessions[agent_session_id].last_activity = time.time()
            
        except Exception as e:
            logger.error(f"Streaming agent task failed: {e}")
            # Handle exception during streaming by sending error as stream instead of separate message
            error_content = f"I'm sorry, I encountered an error during streaming. Error: {str(e)}"
            
            # Try to send error as streaming if possible
            try:
                # If no content has been streamed yet, start the stream
                if is_first_chunk:
                    await self._send_streaming_start(
                        chat_session_id, 
                        message_id,
                        reply_to_id
                    )
                
                # Send error as streaming chunk
                await self._send_streaming_chunk(
                    chat_session_id,
                    message_id,
                    error_content,
                    reply_to_id
                )
                
                # End the stream
                await self._send_streaming_end(
                    chat_session_id,
                    message_id,
                    reply_to_id
                )
                
                # Store the error message for persistence
                final_message = ChatMessage(
                    id=message_id,
                    content=error_content,
                    sender=MessageSender.AI,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    agent_id=self.config.agent_id,
                    session_id=chat_session_id,
                    metadata={'reply_to': reply_to_id, 'streaming_complete': True, 'has_error': True}
                )
                await self._store_message(final_message)
                
            except Exception as stream_error:
                # If streaming fails too, fall back to regular error response
                logger.error(f"Failed to send streaming error response: {stream_error}")
                await self._send_ai_response(
                    chat_session_id,
                    error_content,
                    reply_to_id
                )
    
    async def _process_with_custom_agent(self, user_message: ChatMessage, agent_type: str):
        """Process user message with a custom agent using three-phase streaming protocol"""
        logger.info(f"🤖 Processing message with custom agent: {agent_type}")
        try:
            # Send typing indicator
            await self._send_typing_indicator(user_message.session_id, True)
            
            # Get message history for context
            history = await self.get_message_history(user_message.session_id, limit=10)
            history_list = []
            for msg in history:
                if msg.sender == MessageSender.USER:
                    history_list.append({"role": "user", "content": msg.content})
                elif msg.sender == MessageSender.AI:
                    history_list.append({"role": "assistant", "content": msg.content})
            
            # Prepare streaming response
            full_content = ""
            message_id = str(uuid.uuid4())
            is_first_chunk = True
            
            # Get custom agent stream
            custom_stream = call_custom_agent_stream(agent_type, user_message.content, history_list)
            
            # Process streaming response with three-phase protocol
            chunk_count = 0
            async for chunk in custom_stream:
                chunk_count += 1
                if chunk:  # Only process non-empty chunks
                    # Send stream start for first chunk
                    if is_first_chunk:
                        await self._send_streaming_start(
                            user_message.session_id,
                            message_id,
                            user_message.id,
                            agent_type=agent_type,
                            agent_id=agent_type,  # Use agent_type as agent_id for custom agents
                            agent_name=agent_type.title()  # Use capitalized agent_type as name
                        )
                        is_first_chunk = False
                    
                    # Send chunk
                    await self._send_streaming_chunk(
                        user_message.session_id,
                        message_id,
                        chunk,
                        user_message.id
                    )
                    full_content += chunk
                    
                    # Small delay to prevent WebSocket message batching and ensure real-time delivery
                    await asyncio.sleep(0.01)  # 10ms delay between chunks
            
            # Send stream end
            await self._send_streaming_end(
                user_message.session_id,
                message_id,
                user_message.id
            )
            
            # Store the final complete message for persistence
            final_message = ChatMessage(
                id=message_id,
                content=full_content,
                sender=MessageSender.AI,
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent_id=agent_type,
                session_id=user_message.session_id,
                metadata={'reply_to': user_message.id, 'streaming_complete': True, 'agentType': agent_type}
            )
            await self._store_message(final_message)
            
            await self._send_typing_indicator(user_message.session_id, False)
            logger.info(f"✅ Custom agent {agent_type} response completed")
            
        except Exception as e:
            logger.error(f"❌ Error processing message with custom agent {agent_type}: {e}")
            logger.exception("Full traceback:")
            
            # Send error as streaming response to maintain protocol consistency
            error_content = f"I'm sorry, I encountered an error. Please try again. Error: {str(e)}"
            
            try:
                # If no content has been streamed yet, start the stream
                if is_first_chunk:
                    await self._send_streaming_start(
                        user_message.session_id,
                        message_id,
                        user_message.id,
                        agent_type=agent_type,
                        agent_id=agent_type,
                        agent_name=agent_type.title()
                    )
                
                # Send error as streaming chunk
                await self._send_streaming_chunk(
                    user_message.session_id,
                    message_id,
                    error_content,
                    user_message.id
                )
                
                # End the stream
                await self._send_streaming_end(
                    user_message.session_id,
                    message_id,
                    user_message.id
                )
                
                # Store the error message for persistence
                final_message = ChatMessage(
                    id=message_id,
                    content=error_content,
                    sender=MessageSender.AI,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    agent_id=agent_type,
                    session_id=user_message.session_id,
                    metadata={'reply_to': user_message.id, 'streaming_complete': True, 'has_error': True, 'agentType': agent_type}
                )
                await self._store_message(final_message)
                
            except Exception as stream_error:
                # If streaming fails too, fall back to regular error response
                logger.error(f"Failed to send streaming error response: {stream_error}")
                await self._send_ai_response(
                    user_message.session_id,
                    error_content,
                    user_message.id
                )
            
            await self._send_typing_indicator(user_message.session_id, False)
    
    async def _send_streaming_start(self, session_id: str, message_id: str, reply_to_id: str = None, agent_type: str = None, agent_id: str = None, agent_name: str = None):
        """Send streaming start message"""
        try:
            # Use provided agent info or fall back to default OpenAI config
            final_agent_type = agent_type or 'openai'
            final_agent_id = agent_id or self.config.agent_id
            final_agent_name = agent_name or self.config.agent_name
            
            streaming_message = {
                'type': 'message_stream',
                'id': message_id,
                'sender': MessageSender.AI.value,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'agentId': final_agent_id,
                'agentName': final_agent_name,
                'agentType': final_agent_type,
                'session_id': session_id,
                'stream_start': True,
                'stream_chunk': False,
                'stream_end': False,
                'metadata': {
                    'reply_to': reply_to_id,
                    'streaming': True
                }
            }
            
            # Send to all connections in this session
            for websocket_id, ws_session_id in self.chat_sessions.items():
                if ws_session_id == session_id:
                    await self._send_websocket_message(websocket_id, streaming_message)
                    
        except Exception as e:
            logger.error(f"Failed to send streaming start: {e}")

    async def _send_streaming_chunk(self, session_id: str, message_id: str, content: str, reply_to_id: str = None):
        """Send streaming chunk message"""
        try:
            streaming_message = {
                'type': 'message_stream',
                'id': message_id,
                'chunk': content,
                'sender': MessageSender.AI.value,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'agentId': self.config.agent_id,
                'agentName': self.config.agent_name,
                'agentType': 'openai',
                'session_id': session_id,
                'stream_start': False,
                'stream_chunk': True,
                'stream_end': False,
                'metadata': {
                    'reply_to': reply_to_id,
                    'streaming': True
                }
            }
            
            # Send to all connections in this session
            for websocket_id, ws_session_id in self.chat_sessions.items():
                if ws_session_id == session_id:
                    await self._send_websocket_message(websocket_id, streaming_message)
                    
        except Exception as e:
            logger.error(f"Failed to send streaming chunk: {e}")

    async def _send_streaming_end(self, session_id: str, message_id: str, reply_to_id: str = None):
        """Send streaming end message"""
        try:
            streaming_message = {
                'type': 'message_stream',
                'id': message_id,
                'sender': MessageSender.AI.value,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'agentId': self.config.agent_id,
                'agentName': self.config.agent_name,
                'agentType': 'openai',
                'session_id': session_id,
                'stream_start': False,
                'stream_chunk': False,
                'stream_end': True,
                'metadata': {
                    'reply_to': reply_to_id,
                    'streaming': False
                }
            }
            
            # Send to all connections in this session
            for websocket_id, ws_session_id in self.chat_sessions.items():
                if ws_session_id == session_id:
                    await self._send_websocket_message(websocket_id, streaming_message)
                    
        except Exception as e:
            logger.error(f"Failed to send streaming end: {e}")

    async def _send_streaming_message(self, session_id: str, message_id: str, content: str, 
                                     reply_to_id: str = None, is_complete: bool = False):
        """Send a streaming message update (legacy method - use specific methods above)"""
        try:
            # Use frontend-compatible format
            streaming_message = {
                'type': 'message_stream',
                'id': message_id,
                'chunk': content,  # Frontend expects 'chunk' field
                'sender': MessageSender.AI.value,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'agentId': self.config.agent_id,  # Frontend expects camelCase
                'agentName': self.config.agent_name,
                'agentType': 'openai',  # Default agent type
                'session_id': session_id,
                'stream_chunk': True,  # Frontend expects this field
                'stream_start': False,  # Will be set to True for first chunk
                'stream_end': is_complete,  # Frontend expects this field
                'metadata': {
                    'reply_to': reply_to_id,
                    'is_complete': is_complete,
                    'streaming': True
                }
            }
            
            # Send to all connections in this session
            for websocket_id, ws_session_id in self.chat_sessions.items():
                if ws_session_id == session_id:
                    await self._send_websocket_message(websocket_id, streaming_message)
                    
        except Exception as e:
            logger.error(f"Failed to send streaming message: {e}")

    async def _send_ai_response(self, session_id: str, content: str, reply_to_id: str = None):
        """Send an AI response message"""
        message = ChatMessage(
            id=str(uuid.uuid4()),
            content=content,
            sender=MessageSender.AI,
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_id=self.config.agent_id,
            session_id=session_id,
            metadata={'reply_to': reply_to_id} if reply_to_id else {}
        )
        
        await self._store_message(message)
        await self._broadcast_message(message)
    
    async def _send_typing_indicator(self, session_id: str, is_typing: bool):
        """Send typing indicator status"""
        if not self.config.enable_typing_indicators:
            return
        
        try:
            typing_message = {
                'type': 'typing',
                'session_id': session_id,
                'is_typing': is_typing,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Send to all connections in this session
            for websocket_id, ws_session_id in self.chat_sessions.items():
                if ws_session_id == session_id:
                    await self._send_websocket_message(websocket_id, typing_message)
        except Exception as e:
            logger.warning(f"Could not send typing indicator: {e}")
    
    async def _send_agent_status(self, websocket_id: str):
        """Send current agent status to a WebSocket connection"""
        try:
            agent_status = await self.get_agent_status()
            status_message = {
                'type': 'agent_status',
                'agent': agent_status.to_dict(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            await self._send_websocket_message(websocket_id, status_message)
        except Exception as e:
            logger.warning(f"Could not send agent status to {websocket_id}: {e}")
    
    async def _broadcast_message(self, message: ChatMessage):
        """Broadcast a message to all connected WebSocket clients in the same session"""
        try:
            message_dict = message.to_dict()
            
            for websocket_id, session_id in self.chat_sessions.items():
                if hasattr(message, 'session_id') and session_id == message.session_id:
                    await self._send_websocket_message(websocket_id, message_dict)
                elif not hasattr(message, 'session_id'):
                    # Broadcast to all if no session_id specified
                    await self._send_websocket_message(websocket_id, message_dict)
        except Exception as e:
            logger.warning(f"Could not broadcast message: {e}")
    
    async def _store_message(self, message: ChatMessage):
        """Store a message in the database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO chat_messages 
                    (id, content, sender, timestamp, type, metadata, agent_id, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message.id,
                        message.content,
                        message.sender.value,
                        message.timestamp,
                        message.type.value,
                        json.dumps(message.metadata),
                        message.agent_id,
                        message.session_id
                    )
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to store message: {e}")
    
    async def get_message_history(self, session_id: str = None, limit: int = 50, offset: int = 0) -> List[ChatMessage]:
        """Get message history with pagination"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if session_id:
                    cursor = await db.execute(
                        """
                        SELECT id, content, sender, timestamp, type, metadata, agent_id, session_id
                        FROM chat_messages 
                        WHERE session_id = ?
                        ORDER BY timestamp DESC 
                        LIMIT ? OFFSET ?
                        """,
                        (session_id, limit, offset)
                    )
                else:
                    cursor = await db.execute(
                        """
                        SELECT id, content, sender, timestamp, type, metadata, agent_id, session_id
                        FROM chat_messages 
                        ORDER BY timestamp DESC 
                        LIMIT ? OFFSET ?
                        """,
                        (limit, offset)
                    )
                
                rows = await cursor.fetchall()
                messages = []
                
                for row in rows:
                    messages.append(ChatMessage(
                        id=row[0],
                        content=row[1],
                        sender=MessageSender(row[2]),
                        timestamp=row[3],
                        type=ChatMessageType(row[4]),
                        metadata=json.loads(row[5] or '{}'),
                        agent_id=row[6],
                        session_id=row[7]
                    ))
                
                # Reverse to get chronological order
                messages.reverse()
                return messages
                
        except Exception as e:
            logger.error(f"Failed to retrieve message history: {e}")
            return []
    
    async def clear_message_history(self, session_id: str = None) -> bool:
        """Clear message history for a session or all messages"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if session_id:
                    await db.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
                else:
                    await db.execute("DELETE FROM chat_messages")
                await db.commit()
                logger.info(f"Cleared message history for session: {session_id or 'all'}")
                return True
        except Exception as e:
            logger.error(f"Failed to clear message history: {e}")
            return False
    
    async def get_agent_status(self) -> AgentStatus:
        """Get current agent status"""
        try:
            if not self.agent_service:
                self.agent_service = await get_agent_service()
            
            if not self.config.agent_id:
                return AgentStatus(
                    available=False,
                    name="No Agent Configured",
                    type="none",
                    capabilities=[]
                )
            
            # Get agent sessions
            agent_sessions = self.agent_service.get_agent_sessions()
            for session in agent_sessions:
                if session.agent_id == self.config.agent_id:
                    return AgentStatus(
                        available=session.status.value in ['ready', 'running'],
                        name=session.agent_name,
                        type=session.framework,
                        capabilities=session.capabilities,
                        agent_id=session.agent_id
                    )
            
            return AgentStatus(
                available=False,
                name="Agent Not Found",
                type="unknown",
                capabilities=[],
                agent_id=self.config.agent_id
            )
            
        except Exception as e:
            logger.error(f"Failed to get agent status: {e}")
            return AgentStatus(
                available=False,
                name="Agent Status Error",
                type="error",
                capabilities=[]
            )
    
    async def update_config(self, config_updates: Dict[str, Any]):
        """Update chat configuration"""
        for key, value in config_updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Broadcast config changes
        await self._broadcast_config_update()
        logger.info(f"Chat config updated: {config_updates}")
    
    async def _broadcast_config_update(self):
        """Broadcast configuration update to all connected clients"""
        try:
            config_message = {
                'type': 'config_update',
                'config': self.config.to_dict(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            for websocket_id in self.active_connections:
                await self._send_websocket_message(websocket_id, config_message)
        except Exception as e:
            logger.warning(f"Could not broadcast config update: {e}")
    
    async def _handle_agent_status_update(self, message: Message):
        """Handle agent status updates from message broker"""
        try:
            # Broadcast status update to all connected clients
            for websocket_id in self.active_connections:
                await self._send_agent_status(websocket_id)
        except Exception as e:
            logger.error(f"Error handling agent status update: {e}")
    
    async def _handle_agent_message(self, message: Message):
        """Handle agent messages from message broker"""
        try:
            # This can be used for agent-initiated messages
            # Currently not implemented but ready for future use
            pass
        except Exception as e:
            logger.error(f"Error handling agent message: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get chat service statistics"""
        return {
            'active_connections': len(self.active_connections),
            'chat_sessions': len(self.chat_sessions),
            'agent_configured': self.config.agent_id is not None,
            'database_path': self.db_path,
            'config': self.config.to_dict()
        }


# Global instance
_chat_service = None


def get_chat_service() -> ChatService:
    """Get the global chat service instance"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


async def shutdown_chat_service():
    """Shutdown the chat service"""
    global _chat_service
    if _chat_service:
        # Close any pending operations
        logger.info("Chat service shutdown")
        _chat_service = None
