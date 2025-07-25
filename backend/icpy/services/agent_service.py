"""
Agent Service for icpy Backend
Manages agentic workflow instances and exposes them through REST and WebSocket APIs
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import weakref

# Internal imports
from ..core.message_broker import MessageBroker, get_message_broker, Message, MessageType
from ..core.connection_manager import ConnectionManager, get_connection_manager
from ..agent.base_agent import BaseAgent, DefaultAgent, AgentConfig, AgentStatus, AgentMessage
from ..agent.workflows.workflow_engine import WorkflowEngine, WorkflowConfig, WorkflowStatus
from ..agent.registry.capability_registry import CapabilityRegistry, get_capability_registry
from ..agent.memory.context_manager import ContextManager, get_context_manager
from ..agent.configs.agent_templates import template_manager
from ..core.framework_compatibility import FrameworkCompatibilityLayer

logger = logging.getLogger(__name__)


class AgentSessionStatus(Enum):
    """Status of an agent session"""
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    DESTROYED = "destroyed"


@dataclass
class AgentSessionInfo:
    """Information about an agent session"""
    session_id: str
    agent_id: str
    agent_name: str
    framework: str
    status: AgentSessionStatus
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'session_id': self.session_id,
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'framework': self.framework,
            'status': self.status.value,
            'capabilities': self.capabilities,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'last_activity': self.last_activity,
            'performance_metrics': self.performance_metrics
        }


@dataclass
class WorkflowSessionInfo:
    """Information about a workflow session"""
    session_id: str
    workflow_id: str
    workflow_name: str
    status: WorkflowStatus
    agent_sessions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    progress: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'session_id': self.session_id,
            'workflow_id': self.workflow_id,
            'workflow_name': self.workflow_name,
            'status': self.status.value,
            'agent_sessions': self.agent_sessions,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'last_activity': self.last_activity,
            'progress': self.progress
        }


class AgentService:
    """Service for managing agent instances and workflows"""
    
    def __init__(self):
        self.message_broker: Optional[MessageBroker] = None
        self.connection_manager: Optional[ConnectionManager] = None
        self.capability_registry: Optional[CapabilityRegistry] = None
        self.context_manager: Optional[ContextManager] = None
        
        # Agent and workflow management
        self.agent_sessions: Dict[str, AgentSessionInfo] = {}
        self.workflow_sessions: Dict[str, WorkflowSessionInfo] = {}
        self.active_agents: Dict[str, BaseAgent] = {}
        self.active_workflows: Dict[str, WorkflowEngine] = {}
        
        # Performance monitoring
        self.resource_usage: Dict[str, Any] = {}
        self.performance_metrics: Dict[str, Any] = {}
        
        # Event handling
        self.event_handlers: Dict[str, List[Callable]] = {}
        self._shutdown_event = asyncio.Event()
        self._monitoring_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize the agent service"""
        try:
            # Get required components
            self.message_broker = await get_message_broker()
            self.connection_manager = await get_connection_manager()
            self.capability_registry = await get_capability_registry()
            self.context_manager = await get_context_manager()
            
            # Subscribe to relevant message topics
            await self.message_broker.subscribe("agent.*", self._handle_agent_message)
            await self.message_broker.subscribe("workflow.*", self._handle_workflow_message)
            await self.message_broker.subscribe("capability.*", self._handle_capability_message)
            
            # Start monitoring task
            self._monitoring_task = asyncio.create_task(self._monitor_resources())
            
            logger.info("Agent service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent service: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the agent service"""
        try:
            # Signal shutdown
            self._shutdown_event.set()
            
            # Cancel monitoring task
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # Stop all active agents
            for agent_id in list(self.active_agents.keys()):
                await self.stop_agent(agent_id)
            
            # Cancel all active workflows
            for workflow_id in list(self.active_workflows.keys()):
                await self.cancel_workflow(workflow_id)
            
            logger.info("Agent service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during agent service shutdown: {e}")
    
    # Agent Lifecycle Management
    
    async def create_agent(self, config: AgentConfig, session_metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new agent session"""
        try:
            import os
            session_id = str(uuid.uuid4())
            
            # Enhance config with environment API keys if not provided
            enhanced_config = AgentConfig(
                name=config.name,
                framework=config.framework,
                role=config.role,
                goal=config.goal,
                backstory=config.backstory,
                capabilities=config.capabilities,
                memory_enabled=config.memory_enabled,
                context_window=config.context_window,
                temperature=config.temperature,
                model=config.model,
                max_tokens=config.max_tokens,
                custom_config=config.custom_config
            )
            
            # Add API key from environment if not specified
            if not hasattr(config, 'api_key') or not config.custom_config.get('api_key'):
                if 'openai' in config.framework.lower() or config.framework.lower() == 'crewai':
                    api_key = os.getenv('OPENAI_API_KEY')
                    if api_key:
                        enhanced_config.custom_config['api_key'] = api_key
                elif 'anthropic' in config.framework.lower():
                    api_key = os.getenv('ANTHROPIC_API_KEY')
                    if api_key:
                        enhanced_config.custom_config['api_key'] = api_key
                elif 'groq' in config.framework.lower():
                    api_key = os.getenv('GROQ_API_KEY')
                    if api_key:
                        enhanced_config.custom_config['api_key'] = api_key
            
            # Create agent instance
            agent = DefaultAgent(enhanced_config)
            
            # Initialize agent
            success = await agent.initialize()
            if not success:
                raise Exception("Failed to initialize agent")
            
            # Create session info
            session_info = AgentSessionInfo(
                session_id=session_id,
                agent_id=agent.agent_id,
                agent_name=enhanced_config.name,
                framework=enhanced_config.framework,
                status=AgentSessionStatus.READY,
                capabilities=list(agent.capabilities),
                metadata=session_metadata or {}
            )
            
            # Store session and agent
            self.agent_sessions[session_id] = session_info
            self.active_agents[session_id] = agent
            
            # Attach capabilities from registry
            await self._attach_agent_capabilities(agent)
            
            # Emit creation event
            await self._emit_agent_event("agent.created", {
                "session_id": session_id,
                "agent_id": agent.agent_id,
                "name": config.name,
                "framework": config.framework
            })
            
            logger.info(f"Created agent session {session_id} with ID {agent.agent_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            raise
    
    async def create_agent_from_template(self, template_name: str, agent_name: str, 
                                       custom_config: Optional[Dict[str, Any]] = None,
                                       session_metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create agent from a template"""
        config = template_manager.create_agent_from_template(template_name, agent_name, custom_config)
        if not config:
            raise ValueError(f"Template '{template_name}' not found")
        
        return await self.create_agent(config, session_metadata)
    
    async def start_agent(self, session_id: str) -> bool:
        """Start an agent session"""
        if session_id not in self.agent_sessions:
            raise ValueError(f"Agent session {session_id} not found")
        
        agent = self.active_agents.get(session_id)
        if not agent:
            raise ValueError(f"Agent instance for session {session_id} not found")
        
        try:
            success = await agent.start()
            if success:
                self.agent_sessions[session_id].status = AgentSessionStatus.RUNNING
                self.agent_sessions[session_id].last_activity = time.time()
                
                await self._emit_agent_event("agent.started", {
                    "session_id": session_id,
                    "agent_id": agent.agent_id
                })
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to start agent {session_id}: {e}")
            self.agent_sessions[session_id].status = AgentSessionStatus.ERROR
            return False
    
    async def stop_agent(self, session_id: str) -> bool:
        """Stop an agent session"""
        if session_id not in self.agent_sessions:
            raise ValueError(f"Agent session {session_id} not found")
        
        agent = self.active_agents.get(session_id)
        if not agent:
            return True  # Already stopped
        
        try:
            success = await agent.stop()
            if success:
                self.agent_sessions[session_id].status = AgentSessionStatus.STOPPED
                self.agent_sessions[session_id].last_activity = time.time()
                
                await self._emit_agent_event("agent.stopped", {
                    "session_id": session_id,
                    "agent_id": agent.agent_id
                })
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to stop agent {session_id}: {e}")
            return False
    
    async def destroy_agent(self, session_id: str) -> bool:
        """Destroy an agent session"""
        if session_id not in self.agent_sessions:
            return True  # Already destroyed
        
        try:
            # Stop agent first
            await self.stop_agent(session_id)
            
            # Remove from active agents
            if session_id in self.active_agents:
                del self.active_agents[session_id]
            
            # Update session status
            self.agent_sessions[session_id].status = AgentSessionStatus.DESTROYED
            
            await self._emit_agent_event("agent.destroyed", {
                "session_id": session_id
            })
            
            # Remove session after a delay (for cleanup)
            asyncio.create_task(self._cleanup_session(session_id, delay=60))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to destroy agent {session_id}: {e}")
            return False
    
    async def execute_agent_task(self, session_id: str, task: str, 
                                context: Optional[Dict[str, Any]] = None) -> str:
        """Execute a task with an agent"""
        if session_id not in self.agent_sessions:
            raise ValueError(f"Agent session {session_id} not found")
        
        agent = self.active_agents.get(session_id)
        if not agent:
            raise ValueError(f"Agent instance for session {session_id} not found")
        
        try:
            # Update session status
            self.agent_sessions[session_id].status = AgentSessionStatus.RUNNING
            self.agent_sessions[session_id].last_activity = time.time()
            
            # Execute task and collect results
            result = ""
            async for message in agent.execute(task, context):
                if message.message_type == "text":
                    result += message.content
                elif message.message_type == "error":
                    raise Exception(message.content)
                
                # Stream message to connected clients
                await self._stream_agent_message(session_id, message)
            
            # Update session status back to ready
            self.agent_sessions[session_id].status = AgentSessionStatus.READY
            self.agent_sessions[session_id].last_activity = time.time()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute task for agent {session_id}: {e}")
            self.agent_sessions[session_id].status = AgentSessionStatus.ERROR
            raise
    
    # Workflow Management
    
    async def create_workflow(self, config: WorkflowConfig, 
                            session_metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new workflow session"""
        try:
            session_id = str(uuid.uuid4())
            
            # Create workflow engine
            engine = WorkflowEngine(config)
            success = await engine.initialize()
            if not success:
                raise Exception("Failed to initialize workflow")
            
            # Create session info
            session_info = WorkflowSessionInfo(
                session_id=session_id,
                workflow_id=engine.workflow_id,
                workflow_name=config.name,
                status=engine.state.status,
                metadata=session_metadata or {}
            )
            
            # Store session and workflow
            self.workflow_sessions[session_id] = session_info
            self.active_workflows[session_id] = engine
            
            # Emit creation event
            await self._emit_workflow_event("workflow.created", {
                "session_id": session_id,
                "workflow_id": engine.workflow_id,
                "name": config.name
            })
            
            logger.info(f"Created workflow session {session_id} with ID {engine.workflow_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create workflow: {e}")
            raise
    
    async def create_workflow_from_template(self, template_name: str, workflow_name: str,
                                          session_metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create workflow from a template"""
        config = template_manager.create_workflow_from_template(template_name, workflow_name)
        if not config:
            raise ValueError(f"Workflow template '{template_name}' not found")
        
        return await self.create_workflow(config, session_metadata)
    
    async def execute_workflow(self, session_id: str) -> bool:
        """Execute a workflow"""
        if session_id not in self.workflow_sessions:
            raise ValueError(f"Workflow session {session_id} not found")
        
        engine = self.active_workflows.get(session_id)
        if not engine:
            raise ValueError(f"Workflow engine for session {session_id} not found")
        
        try:
            # Start execution
            success = await engine.execute()
            
            # Update session info
            self.workflow_sessions[session_id].status = engine.state.status
            self.workflow_sessions[session_id].last_activity = time.time()
            self.workflow_sessions[session_id].progress = engine.get_status()
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to execute workflow {session_id}: {e}")
            self.workflow_sessions[session_id].status = WorkflowStatus.FAILED
            raise
    
    async def pause_workflow(self, session_id: str) -> bool:
        """Pause a workflow"""
        engine = self.active_workflows.get(session_id)
        if not engine:
            return False
        
        success = await engine.pause()
        if success:
            self.workflow_sessions[session_id].status = engine.state.status
            self.workflow_sessions[session_id].last_activity = time.time()
        
        return success
    
    async def resume_workflow(self, session_id: str) -> bool:
        """Resume a workflow"""
        engine = self.active_workflows.get(session_id)
        if not engine:
            return False
        
        success = await engine.resume()
        if success:
            self.workflow_sessions[session_id].status = engine.state.status
            self.workflow_sessions[session_id].last_activity = time.time()
        
        return success
    
    async def cancel_workflow(self, session_id: str) -> bool:
        """Cancel a workflow"""
        engine = self.active_workflows.get(session_id)
        if not engine:
            return True  # Already cancelled
        
        success = await engine.cancel()
        if success:
            self.workflow_sessions[session_id].status = engine.state.status
            self.workflow_sessions[session_id].last_activity = time.time()
            
            # Remove from active workflows
            del self.active_workflows[session_id]
        
        return success
    
    # Query and Status Methods
    
    def get_agent_sessions(self) -> List[AgentSessionInfo]:
        """Get all agent sessions"""
        return list(self.agent_sessions.values())
    
    def get_agent_session(self, session_id: str) -> Optional[AgentSessionInfo]:
        """Get specific agent session"""
        return self.agent_sessions.get(session_id)
    
    def get_workflow_sessions(self) -> List[WorkflowSessionInfo]:
        """Get all workflow sessions"""
        return list(self.workflow_sessions.values())
    
    def get_workflow_session(self, session_id: str) -> Optional[WorkflowSessionInfo]:
        """Get specific workflow session"""
        return self.workflow_sessions.get(session_id)
    
    def get_available_templates(self) -> Dict[str, Any]:
        """Get available agent and workflow templates"""
        return {
            "agent_templates": [t.to_dict() if hasattr(t, 'to_dict') else {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "framework": t.framework,
                "capabilities": t.capabilities,
                "tags": t.tags
            } for t in template_manager.list_templates()],
            "workflow_templates": [t.to_dict() if hasattr(t, 'to_dict') else {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "framework": t.framework,
                "workflow_tasks": len(t.workflow_tasks),
                "tags": t.tags
            } for t in template_manager.list_templates() if t.workflow_tasks]
        }
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage statistics"""
        return {
            "total_agents": len(self.active_agents),
            "total_workflows": len(self.active_workflows),
            "resource_usage": self.resource_usage.copy(),
            "performance_metrics": self.performance_metrics.copy()
        }
    
    # Private Helper Methods
    
    async def _attach_agent_capabilities(self, agent: BaseAgent):
        """Attach capabilities from registry to agent"""
        try:
            if self.capability_registry:
                # Get available capabilities
                capabilities = self.capability_registry.list_capabilities()
                
                # Attach relevant capabilities based on agent config
                for capability in capabilities:
                    if capability.name in agent.capabilities:
                        await self.capability_registry.attach_capability(
                            agent.agent_id, capability.name
                        )
        except Exception as e:
            logger.warning(f"Failed to attach capabilities to agent {agent.agent_id}: {e}")
    
    async def _stream_agent_message(self, session_id: str, message: AgentMessage):
        """Stream agent message to connected clients"""
        try:
            if self.connection_manager:
                # Use broadcast_message instead of broadcast_to_topic
                message_data = {
                    "type": "agent_stream",
                    "session_id": session_id,
                    "message": {
                        "agent_id": message.agent_id,
                        "content": message.content,
                        "message_type": message.message_type,
                        "timestamp": message.timestamp.isoformat() if hasattr(message.timestamp, 'isoformat') else str(message.timestamp),
                        "metadata": message.metadata
                    }
                }
                
                # Broadcast to all WebSocket connections
                await self.connection_manager.broadcast_message(
                    json.dumps(message_data),
                    connection_type=None  # Send to all connections
                )
        except Exception as e:
            logger.warning(f"Failed to stream agent message: {e}")
    
    async def _emit_agent_event(self, event_type: str, payload: Dict[str, Any]):
        """Emit agent-related events"""
        try:
            if self.message_broker:
                await self.message_broker.publish(
                    topic=event_type,
                    payload=payload,
                    sender="agent_service"
                )
        except Exception as e:
            logger.warning(f"Failed to emit agent event {event_type}: {e}")
    
    async def _emit_workflow_event(self, event_type: str, payload: Dict[str, Any]):
        """Emit workflow-related events"""
        try:
            if self.message_broker:
                await self.message_broker.publish(
                    topic=event_type,
                    payload=payload,
                    sender="agent_service"
                )
        except Exception as e:
            logger.warning(f"Failed to emit workflow event {event_type}: {e}")
    
    async def _handle_agent_message(self, message: Message):
        """Handle agent-related messages"""
        try:
            # Custom message handling can be implemented here
            pass
        except Exception as e:
            logger.error(f"Error handling agent message: {e}")
    
    async def _handle_workflow_message(self, message: Message):
        """Handle workflow-related messages"""
        try:
            # Custom message handling can be implemented here
            pass
        except Exception as e:
            logger.error(f"Error handling workflow message: {e}")
    
    async def _handle_capability_message(self, message: Message):
        """Handle capability-related messages"""
        try:
            # Custom message handling can be implemented here
            pass
        except Exception as e:
            logger.error(f"Error handling capability message: {e}")
    
    async def _monitor_resources(self):
        """Monitor resource usage and performance"""
        while not self._shutdown_event.is_set():
            try:
                # Update resource usage metrics
                self.resource_usage = {
                    "timestamp": time.time(),
                    "active_agents": len(self.active_agents),
                    "active_workflows": len(self.active_workflows),
                    "total_sessions": len(self.agent_sessions) + len(self.workflow_sessions)
                }
                
                # Update performance metrics for each agent
                for session_id, agent in self.active_agents.items():
                    if session_id in self.agent_sessions:
                        status = agent.get_status()
                        self.agent_sessions[session_id].performance_metrics = {
                            "status": status.get("status"),
                            "last_activity": status.get("last_activity"),
                            "context_size": status.get("context_size", 0)
                        }
                
                # Sleep before next monitoring cycle
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                await asyncio.sleep(30)
    
    async def _cleanup_session(self, session_id: str, delay: int = 60):
        """Clean up session after delay"""
        await asyncio.sleep(delay)
        
        if session_id in self.agent_sessions:
            del self.agent_sessions[session_id]
        
        if session_id in self.workflow_sessions:
            del self.workflow_sessions[session_id]


# Global agent service instance
_agent_service: Optional[AgentService] = None


async def get_agent_service() -> AgentService:
    """Get the global agent service instance"""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
        await _agent_service.initialize()
    return _agent_service


async def shutdown_agent_service():
    """Shutdown the global agent service"""
    global _agent_service
    if _agent_service:
        await _agent_service.shutdown()
        _agent_service = None
