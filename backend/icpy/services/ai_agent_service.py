"""
AI Agent Integration Service for icpy Backend
Provides high-level API for AI tools to interact with workspace components
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import weakref

# Internal imports
from ..core.message_broker import MessageBroker, Message, MessageType, get_message_broker
from .filesystem_service import FileSystemService
from .code_execution_service import CodeExecutionService, Language, ExecutionStatus
from .lsp_service import LSPService
from .terminal_service import TerminalService
from .workspace_service import WorkspaceService
from .clipboard_service import ClipboardService

logger = logging.getLogger(__name__)


class AgentCapability(Enum):
    """AI Agent capability types"""
    FILE_OPERATIONS = "file_operations"
    CODE_EXECUTION = "code_execution"
    TERMINAL_CONTROL = "terminal_control"
    LSP_INTELLIGENCE = "lsp_intelligence"
    WORKSPACE_NAVIGATION = "workspace_navigation"
    CLIPBOARD_ACCESS = "clipboard_access"
    REAL_TIME_EDITING = "real_time_editing"
    CONTEXT_AWARENESS = "context_awareness"


class AgentActionType(Enum):
    """Types of actions an AI agent can perform"""
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    CREATE_FILE = "create_file"
    DELETE_FILE = "delete_file"
    EXECUTE_CODE = "execute_code"
    TERMINAL_COMMAND = "terminal_command"
    GET_COMPLETIONS = "get_completions"
    GET_DIAGNOSTICS = "get_diagnostics"
    GET_HOVER_INFO = "get_hover_info"
    NAVIGATE_TO_DEFINITION = "navigate_to_definition"
    FIND_REFERENCES = "find_references"
    SET_WORKSPACE = "set_workspace"
    GET_WORKSPACE_FILES = "get_workspace_files"
    COPY_TO_CLIPBOARD = "copy_to_clipboard"
    PASTE_FROM_CLIPBOARD = "paste_from_clipboard"
    SET_ACTIVE_FILE = "set_active_file"
    GET_ACTIVE_FILE = "get_active_file"
    SET_CURSOR_POSITION = "set_cursor_position"
    GET_SELECTION = "get_selection"


@dataclass
class AgentContext:
    """Current context state for AI agent"""
    agent_id: str
    active_file: Optional[str] = None
    cursor_position: Optional[Tuple[int, int]] = None  # (line, column)
    selection: Optional[Dict[str, Any]] = None  # Selection range and content
    workspace_path: Optional[str] = None
    open_files: List[str] = field(default_factory=list)
    terminal_sessions: List[str] = field(default_factory=list)
    capabilities: Set[AgentCapability] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)


@dataclass
class AgentAction:
    """Represents an action performed by an AI agent"""
    action_id: str
    agent_id: str
    action_type: AgentActionType
    parameters: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class AgentEvent:
    """Event notification for AI agents"""
    event_id: str
    event_type: str
    source: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    target_agents: Optional[List[str]] = None  # None means broadcast to all


class AIAgentService:
    """
    AI Agent Integration Service
    
    Provides a unified API for AI tools to interact with workspace components,
    manage context, and perform complex operations across multiple services.
    """

    def __init__(self, message_broker: Optional[MessageBroker] = None):
        self.message_broker = message_broker
        self.active_agents: Dict[str, AgentContext] = {}
        self.action_history: List[AgentAction] = []
        self.event_subscribers: Dict[str, Set[str]] = {}  # event_type -> agent_ids
        
        # Service references
        self._filesystem_service: Optional[FileSystemService] = None
        self._code_execution_service: Optional[CodeExecutionService] = None
        self._lsp_service: Optional[LSPService] = None
        self._terminal_service: Optional[TerminalService] = None
        self._workspace_service: Optional[WorkspaceService] = None
        self._clipboard_service: Optional[ClipboardService] = None
        
        # Setup message broker subscriptions if broker is provided
        if self.message_broker:
            self._setup_subscriptions()
        
        logger.info("AI Agent Integration Service initialized")

    async def register_agent(
        self,
        agent_id: str,
        capabilities: Optional[Set[AgentCapability]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentContext:
        """Register a new AI agent with the service"""
        if agent_id in self.active_agents:
            raise ValueError(f"Agent {agent_id} is already registered")
        
        context = AgentContext(
            agent_id=agent_id,
            capabilities=capabilities or set(),
            metadata=metadata or {}
        )
        
        self.active_agents[agent_id] = context
        
        # Notify about new agent registration
        await self._broadcast_event("agent.registered", {
            "agent_id": agent_id,
            "capabilities": [cap.value for cap in context.capabilities],
            "metadata": context.metadata
        })
        
        logger.info(f"Registered AI agent: {agent_id}")
        return context

    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an AI agent"""
        if agent_id not in self.active_agents:
            return False
        
        # Clean up subscriptions
        for event_type, subscribers in self.event_subscribers.items():
            subscribers.discard(agent_id)
        
        # Remove agent context
        del self.active_agents[agent_id]
        
        # Notify about agent removal
        await self._broadcast_event("agent.unregistered", {
            "agent_id": agent_id
        })
        
        logger.info(f"Unregistered AI agent: {agent_id}")
        return True

    async def execute_action(
        self,
        agent_id: str,
        action_type: AgentActionType,
        parameters: Dict[str, Any]
    ) -> AgentAction:
        """Execute an action on behalf of an AI agent"""
        if agent_id not in self.active_agents:
            raise ValueError(f"Agent {agent_id} is not registered")
        
        action = AgentAction(
            action_id=str(uuid.uuid4()),
            agent_id=agent_id,
            action_type=action_type,
            parameters=parameters
        )
        
        try:
            # Update agent activity
            self.active_agents[agent_id].last_activity = time.time()
            
            # Execute the action
            action.result = await self._execute_action_impl(action)
            action.status = "completed"
            
        except Exception as e:
            action.status = "failed"
            action.error = str(e)
            logger.error(f"Action {action.action_id} failed: {e}")
        
        # Store action in history
        self.action_history.append(action)
        
        # Notify about action completion
        await self._broadcast_event("agent.action_completed", {
            "action_id": action.action_id,
            "agent_id": agent_id,
            "action_type": action_type.value,
            "status": action.status,
            "error": action.error
        })
        
        return action

    async def update_context(
        self,
        agent_id: str,
        **context_updates
    ) -> AgentContext:
        """Update the context for an AI agent"""
        if agent_id not in self.active_agents:
            raise ValueError(f"Agent {agent_id} is not registered")
        
        context = self.active_agents[agent_id]
        
        # Update context fields
        for key, value in context_updates.items():
            if hasattr(context, key):
                setattr(context, key, value)
        
        context.last_activity = time.time()
        
        # Notify about context update
        await self._broadcast_event("agent.context_updated", {
            "agent_id": agent_id,
            "updates": context_updates
        })
        
        return context

    async def get_context(self, agent_id: str) -> Optional[AgentContext]:
        """Get the current context for an AI agent"""
        return self.active_agents.get(agent_id)

    async def subscribe_to_events(
        self,
        agent_id: str,
        event_types: List[str]
    ) -> bool:
        """Subscribe an agent to specific event types"""
        if agent_id not in self.active_agents:
            return False
        
        for event_type in event_types:
            if event_type not in self.event_subscribers:
                self.event_subscribers[event_type] = set()
            self.event_subscribers[event_type].add(agent_id)
        
        logger.info(f"Agent {agent_id} subscribed to events: {event_types}")
        return True

    async def unsubscribe_from_events(
        self,
        agent_id: str,
        event_types: List[str]
    ) -> bool:
        """Unsubscribe an agent from specific event types"""
        if agent_id not in self.active_agents:
            return False
        
        for event_type in event_types:
            if event_type in self.event_subscribers:
                self.event_subscribers[event_type].discard(agent_id)
        
        logger.info(f"Agent {agent_id} unsubscribed from events: {event_types}")
        return True

    async def get_workspace_intelligence(
        self,
        agent_id: str,
        file_path: str,
        intelligence_type: str = "all"
    ) -> Dict[str, Any]:
        """Get code intelligence information for a file"""
        if agent_id not in self.active_agents:
            raise ValueError(f"Agent {agent_id} is not registered")
        
        lsp_service = await self._get_lsp_service()
        if not lsp_service:
            return {"error": "LSP service not available"}
        
        result = {}
        
        if intelligence_type in ["all", "diagnostics"]:
            try:
                diagnostics = await lsp_service.get_diagnostics(file_path)
                result["diagnostics"] = diagnostics
            except Exception as e:
                result["diagnostics_error"] = str(e)
        
        if intelligence_type in ["all", "symbols"]:
            try:
                symbols = await lsp_service.get_document_symbols(file_path)
                result["symbols"] = symbols
            except Exception as e:
                result["symbols_error"] = str(e)
        
        return result

    async def execute_code_with_context(
        self,
        agent_id: str,
        code: str,
        language: Language,
        context_files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute code with additional context from workspace files"""
        if agent_id not in self.active_agents:
            raise ValueError(f"Agent {agent_id} is not registered")
        
        code_service = await self._get_code_execution_service()
        if not code_service:
            return {"error": "Code execution service not available"}
        
        # Add context files to the execution environment
        execution_code = code
        if context_files:
            context_imports = []
            for file_path in context_files:
                try:
                    filesystem_service = await self._get_filesystem_service()
                    if filesystem_service:
                        file_content = await filesystem_service.read_file(file_path)
                        # Add context as comments or imports depending on language
                        if language == Language.PYTHON:
                            context_imports.append(f"# Context from {file_path}")
                        elif language == Language.JAVASCRIPT:
                            context_imports.append(f"// Context from {file_path}")
                except Exception as e:
                    logger.warning(f"Could not load context file {file_path}: {e}")
            
            if context_imports:
                execution_code = "\n".join(context_imports) + "\n\n" + code
        
        # Execute the code
        try:
            result = await code_service.execute_code(execution_code, language)
            return result
        except Exception as e:
            return {"error": str(e)}

    async def get_active_agents(self) -> List[Dict[str, Any]]:
        """Get information about all active agents"""
        agents_info = []
        for agent_id, context in self.active_agents.items():
            agents_info.append({
                "agent_id": agent_id,
                "capabilities": [cap.value for cap in context.capabilities],
                "active_file": context.active_file,
                "workspace_path": context.workspace_path,
                "open_files": context.open_files,
                "created_at": context.created_at,
                "last_activity": context.last_activity,
                "metadata": context.metadata
            })
        return agents_info

    async def get_action_history(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get action history, optionally filtered by agent"""
        actions = self.action_history
        
        if agent_id:
            actions = [a for a in actions if a.agent_id == agent_id]
        
        # Return most recent actions first
        actions = sorted(actions, key=lambda a: a.timestamp, reverse=True)[:limit]
        
        return [
            {
                "action_id": action.action_id,
                "agent_id": action.agent_id,
                "action_type": action.action_type.value,
                "parameters": action.parameters,
                "timestamp": action.timestamp,
                "status": action.status,
                "result": action.result,
                "error": action.error
            }
            for action in actions
        ]

    # Service getters with lazy initialization
    async def _get_filesystem_service(self) -> Optional[FileSystemService]:
        """Get filesystem service instance"""
        if self._filesystem_service is None:
            try:
                from .filesystem_service import FileSystemService
                self._filesystem_service = FileSystemService(self.message_broker)
            except Exception as e:
                logger.error(f"Could not initialize filesystem service: {e}")
        return self._filesystem_service

    async def _get_code_execution_service(self) -> Optional[CodeExecutionService]:
        """Get code execution service instance"""
        if self._code_execution_service is None:
            try:
                from .code_execution_service import CodeExecutionService
                self._code_execution_service = CodeExecutionService(self.message_broker)
            except Exception as e:
                logger.error(f"Could not initialize code execution service: {e}")
        return self._code_execution_service

    async def _get_lsp_service(self) -> Optional[LSPService]:
        """Get LSP service instance"""
        if self._lsp_service is None:
            try:
                from .lsp_service import LSPService
                self._lsp_service = LSPService(self.message_broker)
            except Exception as e:
                logger.error(f"Could not initialize LSP service: {e}")
        return self._lsp_service

    async def _get_terminal_service(self) -> Optional[TerminalService]:
        """Get terminal service instance"""
        if self._terminal_service is None:
            try:
                from .terminal_service import TerminalService
                self._terminal_service = TerminalService(self.message_broker)
            except Exception as e:
                logger.error(f"Could not initialize terminal service: {e}")
        return self._terminal_service

    async def _get_workspace_service(self) -> Optional[WorkspaceService]:
        """Get workspace service instance"""
        if self._workspace_service is None:
            try:
                from .workspace_service import WorkspaceService
                self._workspace_service = WorkspaceService(self.message_broker)
            except Exception as e:
                logger.error(f"Could not initialize workspace service: {e}")
        return self._workspace_service

    async def _get_clipboard_service(self) -> Optional[ClipboardService]:
        """Get clipboard service instance"""
        if self._clipboard_service is None:
            try:
                from .clipboard_service import ClipboardService
                self._clipboard_service = ClipboardService(self.message_broker)
            except Exception as e:
                logger.error(f"Could not initialize clipboard service: {e}")
        return self._clipboard_service

    async def _execute_action_impl(self, action: AgentAction) -> Any:
        """Internal implementation of action execution"""
        action_type = action.action_type
        params = action.parameters
        
        # File operations
        if action_type == AgentActionType.READ_FILE:
            service = await self._get_filesystem_service()
            if service:
                return await service.read_file(params["path"])
            return None  # Service unavailable
            
        elif action_type == AgentActionType.WRITE_FILE:
            service = await self._get_filesystem_service()
            if service:
                return await service.write_file(params["path"], params["content"])
            return None  # Service unavailable
            
        elif action_type == AgentActionType.CREATE_FILE:
            service = await self._get_filesystem_service()
            if service:
                return await service.create_file(params["path"], params.get("content", ""))
            return None  # Service unavailable
            
        elif action_type == AgentActionType.DELETE_FILE:
            service = await self._get_filesystem_service()
            if service:
                return await service.delete_file(params["path"])
            return None  # Service unavailable
        
        # Code execution
        elif action_type == AgentActionType.EXECUTE_CODE:
            service = await self._get_code_execution_service()
            if service:
                language = Language(params["language"])
                return await service.execute_code(params["code"], language)
            return None  # Service unavailable
        
        # Terminal operations
        elif action_type == AgentActionType.TERMINAL_COMMAND:
            service = await self._get_terminal_service()
            if service:
                return await service.execute_command(params["command"])
            return None  # Service unavailable
        
        # LSP operations
        elif action_type == AgentActionType.GET_COMPLETIONS:
            service = await self._get_lsp_service()
            if service:
                return await service.get_completion(
                    params["file_path"],
                    params["line"],
                    params["character"]
                )
            return None  # Service unavailable
            
        elif action_type == AgentActionType.GET_DIAGNOSTICS:
            service = await self._get_lsp_service()
            if service:
                return await service.get_diagnostics(params["file_path"])
            return None  # Service unavailable
            
        elif action_type == AgentActionType.GET_HOVER_INFO:
            service = await self._get_lsp_service()
            if service:
                return await service.get_hover(
                    params["file_path"],
                    params["line"],
                    params["character"]
                )
            return None  # Service unavailable
        
        # Workspace operations
        elif action_type == AgentActionType.SET_WORKSPACE:
            service = await self._get_workspace_service()
            if service:
                return await service.set_workspace(params["path"])
            return None  # Service unavailable
            
        elif action_type == AgentActionType.GET_WORKSPACE_FILES:
            service = await self._get_workspace_service()
            if service:
                return await service.list_files(params.get("pattern", "**/*"))
            return None  # Service unavailable
        
        # Clipboard operations
        elif action_type == AgentActionType.COPY_TO_CLIPBOARD:
            service = await self._get_clipboard_service()
            if service:
                return await service.copy(params["content"])
            return None  # Service unavailable
            
        elif action_type == AgentActionType.PASTE_FROM_CLIPBOARD:
            service = await self._get_clipboard_service()
            if service:
                return await service.paste()
            return None  # Service unavailable
        
        # Context operations
        elif action_type == AgentActionType.SET_ACTIVE_FILE:
            await self.update_context(
                action.agent_id,
                active_file=params["file_path"]
            )
            return {"active_file": params["file_path"]}
            
        elif action_type == AgentActionType.GET_ACTIVE_FILE:
            context = await self.get_context(action.agent_id)
            return {"active_file": context.active_file if context else None}
            
        elif action_type == AgentActionType.SET_CURSOR_POSITION:
            await self.update_context(
                action.agent_id,
                cursor_position=(params["line"], params["character"])
            )
            return {"cursor_position": [params["line"], params["character"]]}
            
        elif action_type == AgentActionType.GET_SELECTION:
            context = await self.get_context(action.agent_id)
            return {"selection": context.selection if context else None}
        
        raise ValueError(f"Unknown action type: {action_type}")

    def _setup_subscriptions(self):
        """Setup message broker subscriptions for relevant events"""
        if not self.message_broker:
            return
            
        # Subscribe to file system events
        self.message_broker.subscribe("fs.*", self._handle_filesystem_event)
        
        # Subscribe to terminal events
        self.message_broker.subscribe("terminal.*", self._handle_terminal_event)
        
        # Subscribe to LSP events
        self.message_broker.subscribe("lsp.*", self._handle_lsp_event)
        
        # Subscribe to workspace events
        self.message_broker.subscribe("workspace.*", self._handle_workspace_event)

    async def _handle_filesystem_event(self, message: Message):
        """Handle filesystem events and forward to interested agents"""
        await self._forward_event_to_agents("filesystem", message.type, message.data)

    async def _handle_terminal_event(self, message: Message):
        """Handle terminal events and forward to interested agents"""
        await self._forward_event_to_agents("terminal", message.type, message.data)

    async def _handle_lsp_event(self, message: Message):
        """Handle LSP events and forward to interested agents"""
        await self._forward_event_to_agents("lsp", message.type, message.data)

    async def _handle_workspace_event(self, message: Message):
        """Handle workspace events and forward to interested agents"""
        await self._forward_event_to_agents("workspace", message.type, message.data)

    async def _forward_event_to_agents(self, source: str, event_type: str, data: Dict[str, Any]):
        """Forward events to subscribed agents"""
        subscribers = self.event_subscribers.get(event_type, set())
        
        if subscribers and self.message_broker:
            # Broadcast event to subscribed agents
            await self.message_broker.publish(
                topic=f"ai_agent.event_forwarded",
                payload={
                    "event": event_type,
                    "source": source,
                    "data": data,
                    "target_agents": list(subscribers)
                }
            )

    async def _broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Broadcast an event to all agents"""
        if self.message_broker:
            await self.message_broker.publish(
                topic=f"ai_agent.{event_type}",
                payload={
                    "event": event_type,
                    "data": data
                }
            )


# Global service instance
_ai_agent_service: Optional[AIAgentService] = None


async def get_ai_agent_service(message_broker: Optional[MessageBroker] = None) -> AIAgentService:
    """Get the global AI Agent service instance"""
    global _ai_agent_service
    if _ai_agent_service is None:
        if message_broker is None:
            message_broker = await get_message_broker()
        _ai_agent_service = AIAgentService(message_broker)
    return _ai_agent_service


# Export main classes and functions
__all__ = [
    "AIAgentService",
    "AgentCapability",
    "AgentActionType",
    "AgentContext",
    "AgentAction",
    "AgentEvent",
    "get_ai_agent_service"
]
