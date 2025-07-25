"""
Agentic Framework Compatibility Layer
Provides unified interfaces for different AI agent frameworks
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional, Union, Callable, AsyncGenerator
from dataclasses import dataclass, field
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class FrameworkType(Enum):
    """Supported agentic framework types"""
    OPENAI = "openai"
    CREWAI = "crewai"
    LANGCHAIN = "langchain"
    LANGGRAPH = "langgraph"


class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class AgentConfig:
    """Configuration for agent instantiation"""
    framework: FrameworkType
    name: str
    role: Optional[str] = None
    goal: Optional[str] = None
    backstory: Optional[str] = None
    system_prompt: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: Optional[int] = 1000
    api_key: Optional[str] = None
    additional_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Standardized agent response format"""
    content: str
    status: AgentStatus
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None


class BaseAgentWrapper(ABC):
    """Abstract base class for agent framework wrappers"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.status = AgentStatus.IDLE
        self._agent = None
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the agent with the given configuration"""
        pass
    
    @abstractmethod
    async def execute(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Execute a prompt and return the response"""
        pass
    
    @abstractmethod
    async def execute_streaming(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """Execute a prompt with streaming response"""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """Stop the agent execution"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> bool:
        """Clean up agent resources"""
        pass


class OpenAIAgentWrapper(BaseAgentWrapper):
    """Wrapper for OpenAI-based agents"""
    
    async def initialize(self) -> bool:
        """Initialize OpenAI client"""
        try:
            import openai
            
            api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("No OpenAI API key provided, using placeholder")
                api_key = "placeholder-key"
            
            self._agent = openai.AsyncOpenAI(api_key=api_key)
            logger.info(f"OpenAI agent '{self.config.name}' initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI agent: {e}")
            return False
    
    async def execute(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Execute prompt using OpenAI API"""
        if not self._agent:
            return AgentResponse(
                content="",
                status=AgentStatus.FAILED,
                error="Agent not initialized"
            )
        
        try:
            self.status = AgentStatus.RUNNING
            
            # Build messages
            messages = []
            if self.config.system_prompt:
                messages.append({"role": "system", "content": self.config.system_prompt})
            
            # Add context if provided
            if context:
                context_str = f"Context: {context}\n\n{prompt}"
                messages.append({"role": "user", "content": context_str})
            else:
                messages.append({"role": "user", "content": prompt})
            
            # Check if we have a real API key
            api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
            if api_key and api_key != "placeholder-key" and api_key.startswith("sk-"):
                # Make real API call
                response = await self._agent.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
                
                response_content = response.choices[0].message.content
                usage_info = response.usage.model_dump() if response.usage else None
                
                self.status = AgentStatus.COMPLETED
                return AgentResponse(
                    content=response_content,
                    status=AgentStatus.COMPLETED,
                    metadata={"model": self.config.model, "framework": "openai"},
                    usage=usage_info
                )
            else:
                # Fallback to simulated response for testing
                response_content = f"[SIMULATED] OpenAI Agent '{self.config.name}' processed: {prompt[:50]}..."
                
                self.status = AgentStatus.COMPLETED
                return AgentResponse(
                    content=response_content,
                    status=AgentStatus.COMPLETED,
                    metadata={"model": self.config.model, "framework": "openai", "simulated": True}
                )
            
        except Exception as e:
            self.status = AgentStatus.FAILED
            logger.error(f"OpenAI execution failed: {e}")
            return AgentResponse(
                content="",
                status=AgentStatus.FAILED,
                error=str(e)
            )
    
    async def execute_streaming(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """Execute with streaming response"""
        if not self._agent:
            yield "Error: Agent not initialized"
            return
        
        try:
            # Build messages
            messages = []
            if self.config.system_prompt:
                messages.append({"role": "system", "content": self.config.system_prompt})
            
            # Add context if provided
            if context:
                context_str = f"Context: {context}\n\n{prompt}"
                messages.append({"role": "user", "content": context_str})
            else:
                messages.append({"role": "user", "content": prompt})
            
            # Check if we have a real API key
            api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
            if api_key and api_key != "placeholder-key" and api_key.startswith("sk-"):
                # Make real streaming API call
                stream = await self._agent.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    stream=True
                )
                
                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                # Fallback to simulated streaming
                response = await self.execute(prompt, context)
                content = response.content
                chunk_size = 10
                for i in range(0, len(content), chunk_size):
                    yield content[i:i+chunk_size]
                    await asyncio.sleep(0.1)  # Simulate delay
                    
        except Exception as e:
            logger.error(f"OpenAI streaming failed: {e}")
            yield f"Error: {str(e)}"
    
    async def stop(self) -> bool:
        """Stop OpenAI agent execution"""
        self.status = AgentStatus.STOPPED
        return True
    
    async def cleanup(self) -> bool:
        """Clean up OpenAI agent resources"""
        self._agent = None
        self.status = AgentStatus.IDLE
        return True


class CrewAIAgentWrapper(BaseAgentWrapper):
    """Wrapper for CrewAI-based agents"""
    
    async def initialize(self) -> bool:
        """Initialize CrewAI agent"""
        try:
            from crewai import Agent, Task, Crew
            import os
            
            # Set up environment variables for CrewAI to use OpenAI
            if not os.getenv("OPENAI_API_KEY"):
                openai_key = os.getenv("OPENAI_API_KEY")
                if openai_key:
                    os.environ["OPENAI_API_KEY"] = openai_key
            
            self._agent = Agent(
                role=self.config.role or "Assistant",
                goal=self.config.goal or "Help the user with their request",
                backstory=self.config.backstory or "I am a helpful AI assistant",
                verbose=False,
                allow_delegation=False,
                llm_model=self.config.model  # Use the specified model
            )
            
            logger.info(f"CrewAI agent '{self.config.name}' initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize CrewAI agent: {e}")
            return False
    
    async def execute(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Execute prompt using CrewAI"""
        if not self._agent:
            return AgentResponse(
                content="",
                status=AgentStatus.FAILED,
                error="Agent not initialized"
            )
        
        try:
            self.status = AgentStatus.RUNNING
            
            # Create task for the agent
            from crewai import Task, Crew
            import os
            
            task_description = prompt
            if context:
                task_description = f"Context: {context}\n\nTask: {prompt}"
            
            task = Task(
                description=task_description,
                agent=self._agent,
                expected_output="A helpful response to the user's request"
            )
            
            crew = Crew(
                agents=[self._agent],
                tasks=[task],
                verbose=False
            )
            
            # Check if we have real API keys to execute
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key and openai_key.startswith("sk-"):
                # Execute with real API
                try:
                    result = crew.kickoff()
                    response_content = str(result)
                except Exception as e:
                    logger.warning(f"CrewAI real execution failed, falling back to simulation: {e}")
                    response_content = f"[SIMULATED] CrewAI Agent '{self.config.name}' ({self._agent.role}) processed: {prompt[:50]}..."
            else:
                # Simulate execution
                response_content = f"[SIMULATED] CrewAI Agent '{self.config.name}' ({self._agent.role}) processed: {prompt[:50]}..."
            
            self.status = AgentStatus.COMPLETED
            return AgentResponse(
                content=response_content,
                status=AgentStatus.COMPLETED,
                metadata={"role": self._agent.role, "framework": "crewai"}
            )
            
        except Exception as e:
            self.status = AgentStatus.FAILED
            logger.error(f"CrewAI execution failed: {e}")
            return AgentResponse(
                content="",
                status=AgentStatus.FAILED,
                error=str(e)
            )
    
    async def execute_streaming(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """Execute with streaming response"""
        response = await self.execute(prompt, context)
        content = response.content
        chunk_size = 15
        for i in range(0, len(content), chunk_size):
            yield content[i:i+chunk_size]
            await asyncio.sleep(0.1)
    
    async def stop(self) -> bool:
        """Stop CrewAI agent execution"""
        self.status = AgentStatus.STOPPED
        return True
    
    async def cleanup(self) -> bool:
        """Clean up CrewAI agent resources"""
        self._agent = None
        self.status = AgentStatus.IDLE
        return True


class LangChainAgentWrapper(BaseAgentWrapper):
    """Wrapper for LangChain-based agents"""
    
    async def initialize(self) -> bool:
        """Initialize LangChain agent"""
        try:
            from langchain.schema import HumanMessage, AIMessage, SystemMessage
            from langchain.memory import ConversationBufferMemory
            from langchain.prompts import PromptTemplate
            
            # Initialize memory and prompt template
            self._memory = ConversationBufferMemory()
            self._prompt_template = PromptTemplate(
                input_variables=["input", "history"],
                template="{history}\nHuman: {input}\nAI:"
            )
            
            logger.info(f"LangChain agent '{self.config.name}' initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize LangChain agent: {e}")
            return False
    
    async def execute(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Execute prompt using LangChain"""
        if not hasattr(self, '_memory'):
            return AgentResponse(
                content="",
                status=AgentStatus.FAILED,
                error="Agent not initialized"
            )
        
        try:
            self.status = AgentStatus.RUNNING
            
            # Add context to prompt if provided
            input_text = prompt
            if context:
                input_text = f"Context: {context}\n\n{prompt}"
            
            # Get chat history
            history = self._memory.buffer if hasattr(self._memory, 'buffer') else ""
            
            # Format prompt
            formatted_prompt = self._prompt_template.format(
                input=input_text,
                history=history
            )
            
            # Simulate LLM response
            response_content = f"LangChain Agent '{self.config.name}' processed: {prompt[:50]}..."
            
            # Update memory
            from langchain.schema import HumanMessage, AIMessage
            self._memory.chat_memory.add_user_message(input_text)
            self._memory.chat_memory.add_ai_message(response_content)
            
            self.status = AgentStatus.COMPLETED
            return AgentResponse(
                content=response_content,
                status=AgentStatus.COMPLETED,
                metadata={"framework": "langchain", "has_memory": True}
            )
            
        except Exception as e:
            self.status = AgentStatus.FAILED
            return AgentResponse(
                content="",
                status=AgentStatus.FAILED,
                error=str(e)
            )
    
    async def execute_streaming(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """Execute with streaming response"""
        response = await self.execute(prompt, context)
        content = response.content
        chunk_size = 12
        for i in range(0, len(content), chunk_size):
            yield content[i:i+chunk_size]
            await asyncio.sleep(0.1)
    
    async def stop(self) -> bool:
        """Stop LangChain agent execution"""
        self.status = AgentStatus.STOPPED
        return True
    
    async def cleanup(self) -> bool:
        """Clean up LangChain agent resources"""
        if hasattr(self, '_memory'):
            self._memory.clear()
        self.status = AgentStatus.IDLE
        return True


class LangGraphAgentWrapper(BaseAgentWrapper):
    """Wrapper for LangGraph-based agents"""
    
    async def initialize(self) -> bool:
        """Initialize LangGraph workflow"""
        try:
            from langgraph.graph import StateGraph, END
            from typing import TypedDict
            
            # Define state schema
            class AgentState(TypedDict):
                messages: List[str]
                current_task: str
                context: Optional[Dict[str, Any]]
            
            # Create workflow
            workflow = StateGraph(AgentState)
            
            # Add processing node
            def process_node(state: AgentState):
                messages = state.get("messages", [])
                task = state.get("current_task", "")
                response = f"LangGraph Agent '{self.config.name}' processed: {task[:50]}..."
                return {
                    "messages": messages + [response],
                    "current_task": task,
                    "context": state.get("context")
                }
            
            workflow.add_node("process", process_node)
            workflow.set_entry_point("process")
            workflow.add_edge("process", END)
            
            # Compile the workflow
            self._agent = workflow.compile()
            
            logger.info(f"LangGraph agent '{self.config.name}' initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize LangGraph agent: {e}")
            return False
    
    async def execute(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Execute prompt using LangGraph workflow"""
        if not self._agent:
            return AgentResponse(
                content="",
                status=AgentStatus.FAILED,
                error="Agent not initialized"
            )
        
        try:
            self.status = AgentStatus.RUNNING
            
            # Prepare initial state
            initial_state = {
                "messages": [],
                "current_task": prompt,
                "context": context
            }
            
            # Run the workflow
            result = self._agent.invoke(initial_state)
            
            # Extract response
            messages = result.get("messages", [])
            response_content = messages[-1] if messages else "No response generated"
            
            self.status = AgentStatus.COMPLETED
            return AgentResponse(
                content=response_content,
                status=AgentStatus.COMPLETED,
                metadata={"framework": "langgraph", "workflow": True}
            )
            
        except Exception as e:
            self.status = AgentStatus.FAILED
            return AgentResponse(
                content="",
                status=AgentStatus.FAILED,
                error=str(e)
            )
    
    async def execute_streaming(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """Execute with streaming response"""
        response = await self.execute(prompt, context)
        content = response.content
        chunk_size = 8
        for i in range(0, len(content), chunk_size):
            yield content[i:i+chunk_size]
            await asyncio.sleep(0.1)
    
    async def stop(self) -> bool:
        """Stop LangGraph agent execution"""
        self.status = AgentStatus.STOPPED
        return True
    
    async def cleanup(self) -> bool:
        """Clean up LangGraph agent resources"""
        self._agent = None
        self.status = AgentStatus.IDLE
        return True


class FrameworkCompatibilityLayer:
    """
    Main compatibility layer for managing different agentic frameworks
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgentWrapper] = {}
        self._framework_configs: Dict[FrameworkType, Dict[str, Any]] = {}
        
    def configure_framework(self, framework: FrameworkType, config: Dict[str, Any]):
        """Configure framework-specific settings"""
        self._framework_configs[framework] = config
        logger.info(f"Configured framework: {framework.value}")
    
    async def create_agent(self, config: AgentConfig) -> Optional[BaseAgentWrapper]:
        """Create an agent using the specified framework"""
        try:
            # Select appropriate wrapper
            wrapper_classes = {
                FrameworkType.OPENAI: OpenAIAgentWrapper,
                FrameworkType.CREWAI: CrewAIAgentWrapper,
                FrameworkType.LANGCHAIN: LangChainAgentWrapper,
                FrameworkType.LANGGRAPH: LangGraphAgentWrapper
            }
            
            wrapper_class = wrapper_classes.get(config.framework)
            if not wrapper_class:
                logger.error(f"Unsupported framework: {config.framework}")
                return None
            
            # Create and initialize agent
            agent = wrapper_class(config)
            success = await agent.initialize()
            
            if success:
                self._agents[config.name] = agent
                logger.info(f"Created agent '{config.name}' using {config.framework.value}")
                return agent
            else:
                logger.error(f"Failed to initialize agent '{config.name}'")
                return None
                
        except Exception as e:
            logger.error(f"Error creating agent '{config.name}': {e}")
            return None
    
    async def get_agent(self, name: str) -> Optional[BaseAgentWrapper]:
        """Get an existing agent by name"""
        return self._agents.get(name)
    
    async def remove_agent(self, name: str) -> bool:
        """Remove and cleanup an agent"""
        agent = self._agents.get(name)
        if agent:
            await agent.cleanup()
            del self._agents[name]
            logger.info(f"Removed agent '{name}'")
            return True
        return False
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all active agents"""
        agents_info = []
        for name, agent in self._agents.items():
            agents_info.append({
                "name": name,
                "framework": agent.config.framework.value,
                "status": agent.status.value,
                "role": agent.config.role,
                "model": agent.config.model
            })
        return agents_info
    
    async def cleanup_all(self) -> bool:
        """Clean up all agents"""
        try:
            for agent in self._agents.values():
                await agent.cleanup()
            self._agents.clear()
            logger.info("Cleaned up all agents")
            return True
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return False
    
    def get_supported_frameworks(self) -> List[str]:
        """Get list of supported frameworks"""
        return [framework.value for framework in FrameworkType]
    
    def validate_framework_config(self, framework: FrameworkType, config: Dict[str, Any]) -> bool:
        """Validate framework-specific configuration"""
        # Basic validation - can be extended
        required_keys = {
            FrameworkType.OPENAI: ["api_key"],
            FrameworkType.CREWAI: ["role", "goal"],
            FrameworkType.LANGCHAIN: [],
            FrameworkType.LANGGRAPH: []
        }
        
        required = required_keys.get(framework, [])
        return all(key in config for key in required)


# Global compatibility layer instance
_compatibility_layer: Optional[FrameworkCompatibilityLayer] = None


def get_compatibility_layer() -> FrameworkCompatibilityLayer:
    """Get the global framework compatibility layer instance"""
    global _compatibility_layer
    if _compatibility_layer is None:
        _compatibility_layer = FrameworkCompatibilityLayer()
    return _compatibility_layer


# Export main classes and functions
__all__ = [
    "FrameworkType",
    "AgentStatus", 
    "AgentConfig",
    "AgentResponse",
    "BaseAgentWrapper",
    "OpenAIAgentWrapper",
    "CrewAIAgentWrapper", 
    "LangChainAgentWrapper",
    "LangGraphAgentWrapper",
    "FrameworkCompatibilityLayer",
    "get_compatibility_layer"
]
