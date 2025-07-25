"""
Base Agent Interface for ICPY Agentic Workflows

This module provides the foundational interface for all agents in the ICPY system,
extending the framework compatibility layer with workflow-specific capabilities.
"""

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, AsyncGenerator

from ..core.framework_compatibility import FrameworkCompatibilityLayer, FrameworkType


class AgentStatus(Enum):
    """Agent lifecycle status"""
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class AgentConfig:
    """Configuration for agent creation and behavior"""
    name: str
    framework: str  # 'openai', 'crewai', 'langchain', 'langgraph'
    role: str = "assistant"
    goal: str = "Help the user with their tasks"
    backstory: str = "I am a helpful AI assistant"
    capabilities: List[str] = field(default_factory=list)
    memory_enabled: bool = True
    context_window: int = 4000
    temperature: float = 0.7
    model: str = "gpt-4"
    max_tokens: Optional[int] = None
    custom_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMessage:
    """Message structure for agent communication"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    content: str = ""
    message_type: str = "text"  # text, system, error, tool_use, tool_result
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Base agent interface extending framework compatibility layer
    
    Provides common interface for all agents regardless of underlying framework,
    with support for workflow execution, memory management, and capability registration.
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = str(uuid.uuid4())
        self.status = AgentStatus.CREATED
        self.framework_manager = FrameworkCompatibilityLayer()
        self.native_agent = None
        self.memory = {}
        self.context = []
        self.capabilities = set(config.capabilities)
        self.message_handlers = []
        self.error_handlers = []
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        
    async def initialize(self) -> bool:
        """Initialize the agent with its framework"""
        try:
            self.status = AgentStatus.INITIALIZING
            
            # Convert framework string to FrameworkType
            framework_map = {
                'openai': FrameworkType.OPENAI,
                'crewai': FrameworkType.CREWAI,
                'langchain': FrameworkType.LANGCHAIN,
                'langgraph': FrameworkType.LANGGRAPH
            }
            
            framework_type = framework_map.get(self.config.framework)
            if not framework_type:
                raise ValueError(f"Unsupported framework: {self.config.framework}")
            
            # Create framework-compatible config
            from ..core.framework_compatibility import AgentConfig as FrameworkConfig
            framework_config = FrameworkConfig(
                framework=framework_type,
                name=self.config.name,
                role=self.config.role,
                goal=self.config.goal,
                backstory=self.config.backstory,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                additional_config=self.config.custom_config
            )
            
            # Create native agent using framework compatibility layer
            self.native_agent = await self.framework_manager.create_agent(framework_config)
            
            if not self.native_agent:
                raise Exception("Failed to create native agent")
            
            # Initialize capabilities
            await self._initialize_capabilities()
            
            # Setup memory if enabled
            if self.config.memory_enabled:
                await self._initialize_memory()
            
            self.status = AgentStatus.READY
            return True
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            await self._handle_error(f"Agent initialization failed: {str(e)}")
            return False
    
    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[AgentMessage, None]:
        """Execute a task and yield messages as they're generated"""
        if self.status not in [AgentStatus.READY, AgentStatus.RUNNING]:
            yield AgentMessage(
                agent_id=self.agent_id,
                content=f"Agent not ready. Status: {self.status.value}",
                message_type="error"
            )
            return
        
        try:
            self.status = AgentStatus.RUNNING
            self.last_activity = datetime.utcnow()
            
            # Add context to agent memory
            if context:
                self.context.append(context)
            
            # Execute using framework compatibility layer
            async for chunk in self.native_agent.execute_streaming(task, context):
                message = AgentMessage(
                    agent_id=self.agent_id,
                    content=chunk,
                    message_type="text",
                    metadata={"task": task, "context": context}
                )
                yield message
                
            self.status = AgentStatus.READY
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            error_message = AgentMessage(
                agent_id=self.agent_id,
                content=f"Execution error: {str(e)}",
                message_type="error"
            )
            yield error_message
            await self._handle_error(str(e))
    
    async def pause(self) -> bool:
        """Pause agent execution"""
        if self.status == AgentStatus.RUNNING:
            self.status = AgentStatus.PAUSED
            return True
        elif self.status == AgentStatus.READY:
            # Allow pausing ready agents
            self.status = AgentStatus.PAUSED
            return True
        return False
    
    async def resume(self) -> bool:
        """Resume agent execution"""
        if self.status == AgentStatus.PAUSED:
            self.status = AgentStatus.READY
            return True
        return False
    
    async def start(self) -> bool:
        """Start agent execution"""
        if self.status in [AgentStatus.READY, AgentStatus.PAUSED]:
            self.status = AgentStatus.RUNNING
            return True
        return False
    
    async def stop(self) -> bool:
        """Stop agent and cleanup resources"""
        try:
            self.status = AgentStatus.STOPPING
            
            # Cleanup framework-specific resources
            if self.native_agent:
                await self._cleanup_native_agent()
            
            # Save memory state
            if self.config.memory_enabled:
                await self._save_memory_state()
            
            self.status = AgentStatus.STOPPED
            return True
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            await self._handle_error(f"Agent stop failed: {str(e)}")
            return False
    
    def add_capability(self, capability: str) -> bool:
        """Add a capability to the agent"""
        self.capabilities.add(capability)
        return True
    
    def remove_capability(self, capability: str) -> bool:
        """Remove a capability from the agent"""
        self.capabilities.discard(capability)
        return True
    
    def has_capability(self, capability: str) -> bool:
        """Check if agent has a specific capability"""
        return capability in self.capabilities
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status and metadata"""
        return {
            'agent_id': self.agent_id,
            'name': self.config.name,
            'framework': self.config.framework,
            'status': self.status.value,
            'capabilities': list(self.capabilities),
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'memory_enabled': self.config.memory_enabled,
            'context_size': len(self.context)
        }
    
    def add_message_handler(self, handler: Callable[[AgentMessage], None]):
        """Add a message handler for agent communication"""
        self.message_handlers.append(handler)
    
    def add_error_handler(self, handler: Callable[[str], None]):
        """Add an error handler for agent errors"""
        self.error_handlers.append(handler)
    
    # Abstract methods for subclass implementation
    async def _initialize_capabilities(self):
        """Initialize agent-specific capabilities"""
        # Default implementation - subclasses can override
        pass
    
    async def _initialize_memory(self):
        """Initialize agent memory system"""
        # Default implementation - subclasses can override
        pass
    
    async def _cleanup_native_agent(self):
        """Cleanup framework-specific agent resources"""
        # Default implementation - subclasses can override
        pass
    
    async def _save_memory_state(self):
        """Save agent memory state for persistence"""
        # Default implementation - subclasses can override
        pass
    
    # Private helper methods
    async def _handle_error(self, error: str):
        """Handle agent errors"""
        print(f"Agent {self.agent_id} error: {error}")
        for handler in self.error_handlers:
            try:
                handler(error)
            except Exception as e:
                print(f"Error handler failed: {e}")
    
    async def _emit_message(self, message: AgentMessage):
        """Emit message to all registered handlers"""
        for handler in self.message_handlers:
            try:
                handler(message)
            except Exception as e:
                print(f"Message handler failed: {e}")


class DefaultAgent(BaseAgent):
    """
    Default implementation of BaseAgent for common use cases
    """
    
    async def _initialize_capabilities(self):
        """Initialize default capabilities"""
        default_capabilities = ['text_generation', 'conversation', 'reasoning']
        for cap in default_capabilities:
            self.add_capability(cap)
    
    async def _initialize_memory(self):
        """Initialize simple memory system"""
        self.memory = {
            'conversation_history': [],
            'facts': {},
            'preferences': {}
        }
    
    async def _cleanup_native_agent(self):
        """Cleanup default agent resources"""
        if self.native_agent:
            await self.native_agent.cleanup()
    
    async def _save_memory_state(self):
        """Save memory state to agent context"""
        if self.memory:
            self.context.append({
                'type': 'memory_state',
                'timestamp': datetime.utcnow().isoformat(),
                'memory': self.memory
            })
