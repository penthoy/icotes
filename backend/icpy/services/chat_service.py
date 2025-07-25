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
from ..services.agent_service import AgentService, get_agent_service

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
    
    async def _send_websocket_message(self, websocket_id: str, message_data: Dict[str, Any]):
        """Send a message directly to a WebSocket connection"""
        try:
            if websocket_id in self.websocket_connections:
                websocket = self.websocket_connections[websocket_id]
                await websocket.send_json(message_data)
            else:
                logger.warning(f"WebSocket {websocket_id} not found in connections")
        except Exception as e:
            logger.error(f"Failed to send message to WebSocket {websocket_id}: {e}")
    
    async def handle_user_message(self, websocket_id: str, content: str, metadata: Dict[str, Any] = None) -> ChatMessage:
        """Handle a message from the user"""
        session_id = self.chat_sessions.get(websocket_id)
        if not session_id:
            raise ValueError("WebSocket not connected to chat session")
        
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
        
        # Process with agent if available
        await self._process_with_agent(message)
        
        return message
    
    async def _process_with_agent(self, user_message: ChatMessage):
        """Process user message with the configured agent"""
        logger.info(f"🔄 Processing message with agent. Agent ID: {self.config.agent_id}")
        try:
            if not self.agent_service:
                logger.info("🔧 Getting agent service...")
                self.agent_service = await get_agent_service()
                logger.info(f"✅ Agent service obtained: {type(self.agent_service)}")
            
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
            logger.info("📝 Sending typing indicator...")
            await self._send_typing_indicator(user_message.session_id, True)
            
            # Get agent session
            logger.info("🔍 Getting agent sessions...")
            agent_sessions = self.agent_service.get_agent_sessions()
            logger.info(f"📋 Found {len(agent_sessions)} agent sessions")
            
            agent_session = None
            for session in agent_sessions:
                logger.info(f"🤖 Checking session - Agent ID: {session.agent_id}, Status: {session.status}, Name: {session.agent_name}")
                if session.agent_id == self.config.agent_id:
                    agent_session = session
                    logger.info(f"✅ Found matching agent session: {session.agent_name}")
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
            
            # Execute agent task
            logger.info(f"🚀 Executing agent task for session: {agent_session.session_id}")
            task_description = user_message.content  # Use the user's message as the task
            task_context = {
                'type': 'chat_response',
                'session_id': user_message.session_id,
                'system_prompt': self.config.system_prompt,
                'user_message': user_message.content
            }
            logger.info(f"📝 Task description: {task_description}")
            logger.info(f"📝 Task context: {task_context}")
            
            result = await self.agent_service.execute_agent_task(
                agent_session.session_id,
                task_description,
                task_context
            )
            logger.info(f"📤 Agent execution result: {result}")
            
            # Handle both dict and string results
            if isinstance(result, dict):
                # Send agent response
                if result.get('success') and result.get('result'):
                    logger.info(f"✅ Sending successful agent response: {result['result'][:100]}...")
                    await self._send_ai_response(
                        user_message.session_id,
                        result['result'],
                        user_message.id
                    )
                else:
                    logger.error(f"❌ Agent execution failed. Result: {result}")
                    await self._send_ai_response(
                        user_message.session_id,
                        f"I'm sorry, I encountered an error processing your message. Error details: {result}",
                        user_message.id
                    )
            elif isinstance(result, str):
                # Result is a string - this is the actual AI response content!
                logger.info(f"✅ Sending successful agent response (string): {result[:100]}...")
                await self._send_ai_response(
                    user_message.session_id,
                    result,
                    user_message.id
                )
            else:
                logger.error(f"❌ Unexpected result type: {type(result)}")
                await self._send_ai_response(
                    user_message.session_id,
                    f"I'm sorry, I encountered an unexpected error. Result type: {type(result)}",
                    user_message.id
                )
            
            await self._send_typing_indicator(user_message.session_id, False)
            
        except Exception as e:
            logger.error(f"💥 Error processing message with agent: {e}")
            logger.exception("Full traceback:")
            await self._send_ai_response(
                user_message.session_id,
                f"I'm sorry, I encountered an error. Please try again. Error: {str(e)}",
                user_message.id
            )
            await self._send_typing_indicator(user_message.session_id, False)
    
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
