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
import os
import shutil
import mimetypes
from urllib.parse import quote

# Internal imports
from ..core.message_broker import MessageBroker, get_message_broker, Message, MessageType as BrokerMessageType
from ..core.connection_manager import ConnectionManager, get_connection_manager
from ..services.agent_service import AgentService, get_agent_service, AgentSessionStatus
from ..services.media_service import get_media_service

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
    # Phase 0 media groundwork: list of attachment metadata dicts
    # Each attachment dict (Phase 1+) will contain: id, filename, mime_type, size, url (or relative path), and optional thumbnail
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    
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
            'session_id': self.session_id,
            'attachments': self.attachments
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
            session_id=data.get('session_id'),
            attachments=data.get('attachments', [])
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
    - Message persistence with JSONL per-session (deprecates SQLite chat.db)
    - Agent integration and status management
    - Typing indicators and status updates
    - Message history and pagination
    - Error handling and reconnection support
    """
    
    def __init__(self, db_path: str = "chat.db"):
        self.db_path = db_path
        # Unique instance id for isolating on-disk artifacts (prevents test cross-talk)
        self._instance_id = uuid.uuid4().hex[:8]
        # Lazy references; can be coroutine functions, resolve when used
        self.message_broker = get_message_broker()
        # Note: tests patch get_connection_manager to return a Mock manager. We call it here so
        # connection_manager is an object with patchable attributes (e.g. send_to_connection).
        # In normal runtime this import is async; when unpatched it returns a coroutine. We'll
        # store whatever is returned and resolve it lazily in _send_typing_indicator.
        self.connection_manager = get_connection_manager()
        self.agent_service: Optional[AgentService] = None
        
        # Chat sessions and configuration
        self.chat_sessions: Dict[str, str] = {}  # connection_id -> session_id
        self.active_connections: Set[str] = set()
        self.websocket_connections: Dict[str, Any] = {}  # connection_id -> websocket
        self.config = ChatConfig()
        # Feature flags (env-driven) for performance tuning
        self.enable_chunk_batching: bool = os.getenv('ENABLE_CHAT_BATCHING', '0') in ('1', 'true', 'True')
        try:
            self.batch_interval_ms: int = int(os.getenv('CHAT_BATCH_INTERVAL_MS', '100'))
        except ValueError:
            logger.warning("Invalid CHAT_BATCH_INTERVAL_MS value, using default 100")
            self.batch_interval_ms = 100
        try:
            self.min_chunk_size: int = int(os.getenv('CHAT_MIN_CHUNK_SIZE', '64'))
        except ValueError:
            logger.warning("Invalid CHAT_MIN_CHUNK_SIZE value, using default 64")
            self.min_chunk_size = 64
        # Buffered JSONL persistence (flush timer)
        self.enable_buffered_store: bool = os.getenv('CHAT_BUFFERED_STORE', '0') in ('1', 'true', 'True')
        self._persist_buffer: Dict[str, List[ChatMessage]] = {}
        self._persist_lock = asyncio.Lock()
        self._persist_task: Optional[asyncio.Task] = None
        self._persist_interval: float = float(int(os.getenv('CHAT_STORE_FLUSH_MS', '250')))/1000.0
        
        # JSONL history root (workspace/.icotes/chat_history)
        try:
            # Base workspace root
            base_workspace_root = os.environ.get('WORKSPACE_ROOT')
            db_path_obj = Path(self.db_path)
            db_dir = db_path_obj.parent
            stem = db_path_obj.stem

            # Always isolate per ChatService instance when running under pytest or when db_path
            # isn't the default 'chat.db' (e.g., tests pass a temp file). This prevents cross-test
            # contamination when WORKSPACE_ROOT is set globally by other services.
            import uuid as _uuid
            needs_isolation = (
                os.environ.get('PYTEST_CURRENT_TEST') is not None or
                Path(self.db_path).name != 'chat.db'
            )

            if not base_workspace_root:
                # Derive from db location when no explicit WORKSPACE_ROOT
                try:
                    base_workspace_root = str(db_dir)
                except Exception:
                    backend_dir = os.path.dirname(os.path.abspath(__file__))
                    base_workspace_root = os.path.join(os.path.dirname(os.path.dirname(backend_dir)), 'workspace')

            # Apply per-instance isolation suffix when needed
            if needs_isolation:
                workspace_root = str(Path(base_workspace_root) / f'.icotes_{stem}_{_uuid.uuid4().hex[:8]}')
                self._temp_workspace = workspace_root  # Track for cleanup
            else:
                workspace_root = base_workspace_root
                self._temp_workspace = None  # Not a temp workspace

            history_root = Path(workspace_root) / 'chat_history'
            history_root.mkdir(parents=True, exist_ok=True)
            self.history_root = history_root
            self._temp_workspace = None  # Track for cleanup
        except Exception:
            # Fallback to local directory if workspace resolution fails
            self.history_root = Path('.icotes/chat_history')
            self.history_root.mkdir(parents=True, exist_ok=True)
        
        # Database initialization is optional (JSONL is the primary store). We no longer
        # auto-start a background init task here to avoid pytest teardown warnings when the
        # event loop closes. Tests and callers can call _initialize_database() explicitly.
        
        # Setup message broker subscriptions (only if broker is available)
        if hasattr(self.message_broker, 'subscribe'):
            self.message_broker.subscribe(BrokerMessageType.AGENT_STATUS_UPDATED, self._handle_agent_status_update)
            self.message_broker.subscribe(BrokerMessageType.AGENT_MESSAGE, self._handle_agent_message)
        
        # Ensure connection_manager is patchable: tests use patch.object(chat_service.connection_manager,
        # 'send_to_connection', ...). If we currently hold a coroutine or an object without that
        # attribute, wrap with a simple proxy exposing the attribute.
        try:
            cm_obj = self.connection_manager
            needs_proxy = asyncio.iscoroutine(cm_obj) or not hasattr(cm_obj, 'send_to_connection')
        except Exception:
            needs_proxy = True
        if needs_proxy:
            class _CMProxy:
                def __init__(self, outer):
                    self._outer = outer
                async def send_to_connection(self, connection_id: str, data: str):
                    try:
                        payload = json.loads(data)
                    except Exception:
                        payload = data
                    await self._outer._send_websocket_message(connection_id, payload)
            self.connection_manager = _CMProxy(self)

        logger.info("Chat service initialized (JSONL storage)")
        # Start persistence flusher if enabled
        if self.enable_buffered_store:
            try:
                self._persist_task = asyncio.create_task(self._flush_loop())
            except RuntimeError:
                self._persist_task = None
    
    def _normalize_attachments(self, raw_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize various frontend attachment shapes into a standard dict.

        Accepted input shapes (best-effort):
        - From /media/upload: { id, rel_path, mime, size, type? }
        - From UI model: { id, kind: 'image'|'audio'|'file', path, mime, size }
        - From legacy: { id, relative_path, mime_type, size_bytes, kind }

        Returns list of dicts with fields:
        { id, filename, mime_type, size_bytes, relative_path, kind, url? }
        """
        normalized: List[Dict[str, Any]] = []
        try:
            for item in raw_list:
                if not isinstance(item, dict):
                    continue
                att_id = str(item.get('id') or item.get('attachment_id') or '')
                # Determine path fields (preserve absolute path separately to allow secure local embedding)
                orig_path = item.get('path') or ''
                rel_path = item.get('relative_path') or item.get('rel_path') or ''
                abs_path: str = ''
                try:
                    if isinstance(orig_path, str) and orig_path:
                        # Absolute OS path? keep separate; else treat as storage-relative
                        from pathlib import Path as _P
                        if _P(orig_path).is_absolute():
                            abs_path = orig_path
                        else:
                            # If caller only provided a relative path, consider it as storage-relative
                            if not rel_path:
                                rel_path = orig_path
                except Exception as e:
                    logger.debug("Attachment path normalization issue: %s", e)
                mime = item.get('mime_type') or item.get('mime') or 'application/octet-stream'
                size = item.get('size_bytes') or item.get('size') or 0
                kind = item.get('kind') or item.get('type') or ''

                # Infer kind from mime if not provided
                if not kind:
                    if isinstance(mime, str) and mime.startswith('image/'):
                        kind = 'images'
                    elif isinstance(mime, str) and mime.startswith('audio/'):
                        kind = 'audio'
                    else:
                        kind = 'files'
                # Map UI kind names to backend folder names
                if kind in ('image', 'img'): kind = 'images'
                if kind in ('file',): kind = 'files'

                # Derive filename from rel_path if present
                filename = ''
                if isinstance(rel_path, str) and rel_path:
                    try:
                        filename = Path(rel_path).name
                        # If storage scheme prefixes uuid_, strip it for display filename
                        if '_' in filename:
                            filename = filename.split('_', 1)[-1]
                    except Exception:
                        filename = rel_path
                # Fallback to absolute path filename if no rel-based name available
                if not filename and isinstance(abs_path, str) and abs_path:
                    try:
                        filename = Path(abs_path).name
                    except Exception:
                        filename = abs_path

                # Fallback filename from metadata
                if not filename:
                    # Prefer nested meta.filename if present
                    meta = item.get('meta') or {}
                    if isinstance(meta, dict) and meta.get('filename'):
                        filename = str(meta['filename'])
                    if not filename:
                        filename = item.get('filename') or item.get('name') or att_id or 'attachment'

                # Build URL helper (served via /api/media/file/{id} if we have a proper id)
                url = None
                if att_id and not str(att_id).startswith('explorer-'):
                    # Use media file endpoint; UI will call getAttachmentUrl too
                    url = f"/api/media/file/{quote(att_id)}"

                normalized.append({
                    'id': att_id or None,
                    'filename': filename,
                    'mime_type': mime,
                    'size_bytes': int(size) if isinstance(size, (int, float, str)) and str(size).isdigit() else size,
                    'relative_path': rel_path,
                    # Preserve absolute path for explorer references so downstream can embed as data URL
                    'absolute_path': abs_path or None,
                    'kind': kind,
                    'url': url
                })
        except Exception as e:
            logger.warning(f"Attachment normalization error: {e}")
        return normalized

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
        # Prefer explicit session_id from metadata if provided (allows client-side session switching)
        session_id = None
        if metadata and isinstance(metadata, dict) and metadata.get('session_id'):
            session_id = str(metadata['session_id'])
            # Update mapping so subsequent messages on this connection use this session
            self.chat_sessions[websocket_id] = session_id
        else:
            session_id = self.chat_sessions.get(websocket_id)
        if not session_id:
            raise ValueError("WebSocket not connected to chat session")
        
        # Extract agent type from metadata for routing
        agent_type = None
        if metadata and 'agentType' in metadata:
            agent_type = metadata['agentType']
        
        # Normalize media attachments from metadata (if any)
        attachments: List[Dict[str, Any]] = []
        try:
            raw_attachments = []
            if metadata and isinstance(metadata, dict):
                raw_attachments = metadata.get('attachments') or []
            if isinstance(raw_attachments, list):
                attachments = self._normalize_attachments(raw_attachments)
        except Exception as e:
            logger.warning(f"Failed to normalize attachments: {e}")
            attachments = []

        # Create user message including normalized attachments
        message = ChatMessage(
            id=str(uuid.uuid4()),
            content=content,
            sender=MessageSender.USER,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
            session_id=session_id,
            attachments=attachments
        )
        
        # Store message
        await self._store_message(message)
        
        # Tests expect broadcasting of user messages as well
        await self._broadcast_message(message)
        
        # Process with appropriate agent based on type
        # Check if agent_type is a custom agent (dynamic check)
        is_custom_agent = False
        if agent_type:
            try:
                from icpy.agent.custom_agent import get_available_custom_agents
                available_custom_agents = get_available_custom_agents()
                is_custom_agent = agent_type in available_custom_agents
            except Exception as e:
                logger.warning(f"Failed to check custom agents: {e}")
                # Fallback to hardcoded list for backward compatibility
                is_custom_agent = agent_type.lower() in ['personalagent', 'openaidemoagent', 'openrouteragent', 'agentcreator', 'qwen3coderagent']
        
        if is_custom_agent:
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
                'user_message': user_message.content,
                # Include attachments for agent/tooling consumption
                'attachments': user_message.attachments or []
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
            
            # Execute task and stream results, with optional batching and cooperative yield
            buffer: List[str] = []
            last_emit = time.time()
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
                    # Accumulate or emit depending on batching settings
                    chunk = message.content or ""
                    if self.enable_chunk_batching:
                        if chunk:
                            buffer.append(chunk)
                        now = time.time()
                        size = sum(len(c) for c in buffer)
                        if size >= self.min_chunk_size or (now - last_emit) >= (self.batch_interval_ms/1000.0):
                            batched = ''.join(buffer)
                            if batched:
                                await self._send_streaming_chunk(chat_session_id, message_id, batched, reply_to_id)
                                full_content += batched
                                buffer.clear()
                                last_emit = now
                        # Cooperative yield to avoid tight loop starvation
                        await asyncio.sleep(0)
                    else:
                        # Immediate emit path
                        await self._send_streaming_chunk(
                            chat_session_id,
                            message_id,
                            chunk,
                            reply_to_id
                        )
                        full_content += chunk
                        # Small yield to let event loop flush WS
                        await asyncio.sleep(0)
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
            
            # Flush any remaining buffered chunks before ending
            if self.enable_chunk_batching and buffer:
                batched = ''.join(buffer)
                if batched:
                    await self._send_streaming_chunk(chat_session_id, message_id, batched, reply_to_id)
                    full_content += batched
                buffer.clear()
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
        """Process user message with a custom agent"""
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

            # Append current user message as multimodal (include image attachments) so custom agents can see them
            try:
                # Build message content with attachment information
                message_text = user_message.content
                
                # Add file attachment information to the message text for non-image files
                if user_message.attachments:
                    non_image_attachments = []
                    for att in user_message.attachments:
                        kind = att.get('kind')
                        mime = att.get('mime_type') or att.get('mime') or ''
                        filename = att.get('filename') or 'unknown file'
                        
                        # Skip images as they'll be processed as multimodal content
                        if not ((isinstance(mime, str) and mime.startswith('image/')) or kind in ('image', 'images')):
                            rel_path = att.get('relative_path') or att.get('rel_path') or att.get('path') or ''
                            abs_path = att.get('absolute_path') or ''
                            
                            # Determine the path to show to the agent
                            display_path = abs_path if abs_path else (rel_path if rel_path else filename)
                            
                            non_image_attachments.append({
                                'filename': filename,
                                'path': display_path,
                                'mime_type': mime,
                                'size': att.get('size_bytes') or att.get('size') or 0
                            })
                    
                    # Append attachment information to message text if there are non-image files
                    if non_image_attachments:
                        attachment_info = "\n\n[Attached files:"
                        for att_info in non_image_attachments:
                            size_str = f" ({att_info['size']} bytes)" if att_info['size'] else ""
                            attachment_info += f"\n- {att_info['filename']} (path: {att_info['path']}){size_str}"
                        attachment_info += "]"
                        message_text += attachment_info
                
                content_parts: List[Dict[str, Any]] = [{"type": "text", "text": message_text}]
                if user_message.attachments:
                    media = get_media_service()
                    # Configurable caps to avoid heavy processing and nested-loop overhead
                    import os as _os
                    try:
                        max_imgs = int(_os.getenv('CHAT_MAX_IMAGE_ATTACHMENTS', '4'))
                    except Exception:
                        max_imgs = 4
                    try:
                        max_img_mb = float(_os.getenv('CHAT_MAX_IMAGE_SIZE_MB', '3'))
                    except Exception:
                        max_img_mb = 3.0

                    added_images = 0
                    for att in user_message.attachments:
                        try:
                            logger.debug(
                                "Custom agent: Processing attachment id=%s kind=%s mime=%s rel=%s has_abs=%s size=%s",
                                att.get('id'),
                                att.get('kind'),
                                att.get('mime_type') or att.get('mime'),
                                att.get('relative_path') or att.get('rel_path'),
                                bool(att.get('absolute_path')),
                                att.get('size_bytes') or att.get('size'),
                            )
                            kind = att.get('kind')
                            mime = att.get('mime_type') or att.get('mime') or ''
                            # Fast reject for non-image
                            if not ((isinstance(mime, str) and mime.startswith('image/')) or kind in ('image', 'images')):
                                continue
                            # Early termination if we've added enough images
                            if added_images >= max_imgs:
                                break
                            # Prefer embedding as data URL from media service or workspace path
                            rel = att.get('relative_path') or att.get('rel_path') or att.get('path')
                            absolute_field = att.get('absolute_path')
                            data_url = None
                            
                            # Try media service first (for uploaded files)
                            if isinstance(rel, str) and rel:
                                try:
                                    abs_path = (media.base_dir / rel).resolve()
                                    abs_path.relative_to(media.base_dir)
                                    if abs_path.exists() and abs_path.is_file():
                                        # Skip overly large images to reduce memory pressure
                                        try:
                                            size_bytes = abs_path.stat().st_size
                                            if size_bytes > int(max_img_mb * 1024 * 1024):
                                                # Link via URL instead of embedding
                                                raise ValueError('image_too_large')
                                        except Exception:
                                            # If stat fails fall back to attempt embed
                                            pass
                                        import base64
                                        with open(abs_path, 'rb') as f:
                                            b64 = base64.b64encode(f.read()).decode('ascii')
                                        data_url = f"data:{mime};base64,{b64}"
                                except Exception:
                                    data_url = None
                            
                            # Try workspace absolute path (for explorer-dropped files)
                            if not data_url and isinstance(absolute_field, str) and absolute_field:
                                try:
                                    logger.info(f"Custom agent: Attempting to embed explorer image from absolute path")
                                    import os
                                    from pathlib import Path
                                    ws_root = os.environ.get('WORKSPACE_ROOT')
                                    abs_path = Path(absolute_field).resolve()
                                    # Require WORKSPACE_ROOT and enforce sandbox
                                    if not ws_root:
                                        raise PermissionError('WORKSPACE_ROOT not set; absolute paths are not allowed')
                                    ws_root_p = Path(ws_root).resolve()
                                    abs_path.relative_to(ws_root_p)  # raises if outside
                                    if not abs_path.is_file():
                                        raise FileNotFoundError('Invalid path')
                                    if abs_path.exists() and abs_path.is_file():
                                        # Skip overly large images to reduce memory pressure
                                        try:
                                            size_bytes = abs_path.stat().st_size
                                            if size_bytes > int(max_img_mb * 1024 * 1024):
                                                # Link via URL instead of embedding
                                                raise ValueError('image_too_large')
                                        except Exception:
                                            # If stat fails fall back to attempt embed
                                            pass
                                        import base64
                                        with open(abs_path, 'rb') as f:
                                            b64 = base64.b64encode(f.read()).decode('ascii')
                                        data_url = f"data:{mime};base64,{b64}"
                                        logger.info(f"Custom agent: Successfully embedded explorer image as data URL (length: {len(data_url)})")
                                except Exception as e:
                                    logger.warning(f"Custom agent: Failed to embed explorer image: {e}")
                                    data_url = None
                            if not data_url:
                                att_id = att.get('id')
                                if att_id:
                                    data_url = f"/api/media/file/{att_id}"
                            if data_url:
                                content_parts.append({"type": "image_url", "image_url": {"url": data_url}})
                                added_images += 1
                        except Exception:
                            continue
                history_list.append({"role": "user", "content": content_parts})
            except Exception as e:
                logger.warning(f"Failed to attach multimodal content for custom agent: {e}")
            
            # Prepare streaming response
            full_content = ""
            message_id = str(uuid.uuid4())
            is_first_chunk = True
            
            # Get custom agent stream
            # We pass an empty live message because we've already appended the user's content (with attachments) to history
            custom_stream = call_custom_agent_stream(agent_type, "", history_list)
            
            # Process streaming response
            async for chunk in custom_stream:
                if chunk:  # Only process non-empty chunks
                    # Send stream start for first chunk
                    if is_first_chunk:
                        await self._send_streaming_start(
                            user_message.session_id,
                            message_id,
                            user_message.id,
                            agent_type=agent_type,
                            agent_id=agent_type,
                            agent_name=agent_type.title()
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
                    
                    # CRITICAL FIX: Prevent WebSocket message batching
                    await asyncio.sleep(0.01)  # 10ms delay between chunks

            # Send stream end
            await self._send_streaming_end(
                user_message.session_id,
                message_id,
                user_message.id
            )
            
            # Store the final complete message for persistence
            if full_content.strip():
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
            await self._send_typing_indicator(user_message.session_id, False)
            await self._send_ai_response(
                user_message.session_id,
                f"Sorry, there was an error processing your request with {agent_type}.",
                user_message.id
            )
    
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
            # Resolve connection manager instance if a coroutine or factory was stored.
            conn_mgr = self.connection_manager
            # If it's an awaitable (coroutine object), await it
            if asyncio.iscoroutine(conn_mgr):
                conn_mgr = await conn_mgr
            # If it's a callable factory that doesn't expose send_to_connection, try calling it
            if not hasattr(conn_mgr, 'send_to_connection') and callable(conn_mgr):
                try:
                    maybe = conn_mgr()
                    if asyncio.iscoroutine(maybe):
                        conn_mgr = await maybe
                    else:
                        conn_mgr = maybe
                except Exception:
                    # Fall back to internal WS sender
                    conn_mgr = None
            typing_message = {
                'type': 'typing',
                'session_id': session_id,
                'is_typing': is_typing,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Send to all connections in this session using connection manager when available
            for websocket_id, ws_session_id in self.chat_sessions.items():
                if ws_session_id == session_id:
                    try:
                        # Prefer connection manager's transport when present (tests patch this)
                        if conn_mgr and hasattr(conn_mgr, 'send_to_connection'):
                            await conn_mgr.send_to_connection(websocket_id, json.dumps(typing_message))
                        else:
                            await self._send_websocket_message(websocket_id, typing_message)
                    except Exception as e:
                        logger.debug(f"Typing indicator send fallback for {websocket_id}: {e}")
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
        """Store a message to JSONL per session (deprecates SQLite)."""
        try:
            session_id = message.session_id or "default"
            if self.enable_buffered_store:
                async with self._persist_lock:
                    self._persist_buffer.setdefault(session_id, []).append(message)
            else:
                file_path = self.history_root / f"{self._instance_id}_{session_id}.jsonl"
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(message.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to store message (JSONL): {e}")

    async def _flush_loop(self):
        """Periodic flusher for buffered persistence."""
        while True:
            try:
                await asyncio.sleep(self._persist_interval)
                await self._flush_now()
            except asyncio.CancelledError:
                # Final flush on cancel
                await self._flush_now()
                break
            except Exception as e:
                logger.warning(f"Buffered store flush error: {e}")

    async def _flush_now(self):
        tmp: Dict[str, List[ChatMessage]] = {}
        async with self._persist_lock:
            if not self._persist_buffer:
                return
            tmp = self._persist_buffer
            self._persist_buffer = {}
        # Write outside lock
        for session_id, items in tmp.items():
            if not items:
                continue
            file_path = self.history_root / f"{self._instance_id}_{session_id}.jsonl"
            try:
                with open(file_path, 'a', encoding='utf-8') as f:
                    for msg in items:
                        f.write(json.dumps(msg.to_dict(), ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error(f"Failed writing batch for session {session_id}: {e}")
    
    async def get_message_history(self, session_id: str = None, limit: int = 50, offset: int = 0) -> List[ChatMessage]:
        """Get message history with pagination from JSONL files.
        If session_id is None, aggregates across all sessions, sorted by timestamp."""
        try:
            messages: List[ChatMessage] = []
            if session_id:
                file_path = self.history_root / f"{self._instance_id}_{session_id}.jsonl"
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                                messages.append(ChatMessage.from_dict(data))
                            except Exception:
                                pass
            else:
                # Aggregate across all sessions
                for file in self.history_root.glob(f'{self._instance_id}_*.jsonl'):
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue
                                data = json.loads(line)
                                messages.append(ChatMessage.from_dict(data))
                    except Exception:
                        continue
            # Sort chronologically by timestamp ascending
            messages.sort(key=lambda m: m.timestamp)
            # Apply offset/limit from the beginning per tests' expectation
            slice_start = offset if offset >= 0 else 0
            slice_end = slice_start + limit if limit is not None else None
            return messages[slice_start:slice_end]
        except Exception as e:
            logger.error(f"Failed to retrieve message history (JSONL): {e}")
            return []
    
    async def clear_message_history(self, session_id: str = None) -> bool:
        """Clear message history for a session or all sessions (JSONL)."""
        try:
            if session_id:
                file_path = self.history_root / f"{self._instance_id}_{session_id}.jsonl"
                if file_path.exists():
                    file_path.unlink()
            else:
                for file in self.history_root.glob(f'{self._instance_id}_*.jsonl'):
                    try:
                        file.unlink()
                    except Exception:
                        pass
            logger.info(f"Cleared message history for session: {session_id or 'all'} (JSONL)")
            return True
        except Exception as e:
            logger.error(f"Failed to clear message history (JSONL): {e}")
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
            
            # Get agent sessions (tests mock list_agent_sessions)
            try:
                agent_sessions = self.agent_service.list_agent_sessions()
            except AttributeError:
                agent_sessions = []
            for session in list(agent_sessions) if agent_sessions is not None else []:
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
                'type': 'config',
                'config': self.config.to_dict(),
                'timestamp': time.time()
            }
            
            for connection_id, websocket in self.websocket_connections.items():
                try:
                    await websocket.send_json(config_message)
                except Exception as e:
                    logger.error(f"Failed to send config update to connection {connection_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to broadcast config update: {e}")

    # Session CRUD operations
    async def get_sessions(self) -> List[Dict[str, Any]]:
        """Get list of all chat sessions with metadata."""
        try:
            sessions = []
            for file in self.history_root.glob(f'{self._instance_id}_*.jsonl'):
                session_id = file.stem
                if session_id.startswith(f"{self._instance_id}_"):
                    session_id = session_id[len(self._instance_id)+1:]
                try:
                    stat = file.stat()
                    # Count messages in session
                    message_count = 0
                    last_message_time = None
                    with open(file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                message_count += 1
                                try:
                                    data = json.loads(line)
                                    last_message_time = data.get('timestamp')
                                except:
                                    pass
                    
                    # Try reading metadata sidecar for display name
                    meta_name = None
                    meta_path = self.history_root / f"{session_id}.meta.json"
                    if meta_path.exists():
                        try:
                            with open(meta_path, 'r', encoding='utf-8') as mf:
                                meta = json.load(mf)
                                meta_name = meta.get('name') or None
                        except Exception:
                            meta_name = None
                    
                    sessions.append({
                        'id': session_id,
                        'name': meta_name or session_id,  # Default to session ID as name
                        'created': stat.st_ctime,
                        'updated': stat.st_mtime,
                        'message_count': message_count,
                        'last_message_time': last_message_time
                    })
                except Exception as e:
                    logger.error(f"Error processing session {session_id}: {e}")
                    continue
            
            # Sort by updated time, newest first
            sessions.sort(key=lambda s: s['updated'], reverse=True)
            return sessions
        except Exception as e:
            logger.error(f"Failed to get sessions: {e}")
            return []
    
    async def create_session(self, name: str = None) -> str:
        """Create a new chat session."""
        try:
            session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            
            # Create empty JSONL file to establish the session
            file_path = self.history_root / f"{self._instance_id}_{session_id}.jsonl"
            file_path.touch()
            
            # Persist display name if provided
            if name:
                meta_path = self.history_root / f"{session_id}.meta.json"
                with open(meta_path, 'w', encoding='utf-8') as mf:
                    json.dump({'id': session_id, 'name': name}, mf, ensure_ascii=False)
            
            logger.info(f"Created new chat session: {session_id}")
            return session_id
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    async def update_session(self, session_id: str, name: str) -> bool:
        """Update session metadata (rename)."""
        try:
            file_path = self.history_root / f"{self._instance_id}_{session_id}.jsonl"
            if not file_path.exists():
                return False
            
            meta_path = self.history_root / f"{session_id}.meta.json"
            with open(meta_path, 'w', encoding='utf-8') as mf:
                json.dump({'id': session_id, 'name': name}, mf, ensure_ascii=False)
            
            logger.info(f"Session {session_id} renamed to: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed writing metadata for session {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a chat session and its history."""
        try:
            file_path = self.history_root / f"{session_id}.jsonl"
            if not file_path.exists():
                return False
            
            file_path.unlink()
            # Remove sidecar metadata if present
            try:
                meta_path = self.history_root / f"{session_id}.meta.json"
                if meta_path.exists():
                    meta_path.unlink()
            except Exception:
                pass
            logger.info(f"Deleted chat session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
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

    async def stop_streaming(self, session_id: str) -> bool:
        """Stop/interrupt current streaming response for a session"""
        try:
            logger.info(f"Stop streaming requested for session: {session_id}")
            
            # Try to stop any running agents for this session
            try:
                from .agent_service import get_agent_service
                agent_service = await get_agent_service()
                
                # Stop any agent sessions for this chat session
                for agent_session_id in list(agent_service.agent_sessions.keys()):
                    agent_session = agent_service.agent_sessions.get(agent_session_id)
                    if agent_session and agent_session.session_id == session_id:
                        logger.info(f"Stopping agent session {agent_session_id} for chat session {session_id}")
                        await agent_service.stop_agent(agent_session_id)
            except Exception as e:
                logger.warning(f"Failed to stop agent sessions for chat session {session_id}: {e}")
            
            # Send stop/interrupt message to all connections in this session
            stop_message = {
                'type': 'stream_stopped',
                'session_id': session_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'message': 'Streaming interrupted by user'
            }
            
            # Send to all connections in this session
            stopped = False
            for websocket_id, ws_session_id in self.chat_sessions.items():
                if ws_session_id == session_id:
                    await self._send_websocket_message(websocket_id, stop_message)
                    stopped = True
            
            # Also send typing indicator to stop
            await self._send_typing_indicator(session_id, False)
            
            return stopped
            
        except Exception as e:
            logger.error(f"Failed to stop streaming for session {session_id}: {e}")
            return False
    
    async def cleanup(self):
        """Clean up temporary workspace directories and files created by this instance"""
        try:
            # Stop any pending persist tasks
            if self._persist_task and not self._persist_task.done():
                self._persist_task.cancel()
                try:
                    await self._persist_task
                except asyncio.CancelledError:
                    pass
            
            # Flush any remaining buffered messages
            if self._persist_buffer:
                await self._flush_persist_buffer()
            
            # Clean up temporary workspace if we created one
            if hasattr(self, '_temp_workspace') and self._temp_workspace and Path(self._temp_workspace).exists():
                try:
                    shutil.rmtree(self._temp_workspace)
                    logger.info(f"Cleaned up temporary workspace: {self._temp_workspace}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary workspace {self._temp_workspace}: {e}")
            
        except Exception as e:
            logger.error(f"Error during chat service cleanup: {e}")
    
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
        # Clean up temporary files and directories
        await _chat_service.cleanup()
        # Close any pending operations
        logger.info("Chat service shutdown")
        _chat_service = None
