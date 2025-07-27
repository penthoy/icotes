"""
Custom Agent for ICUI Framework

This module provides custom agent implementations that can be used in the ICUI chat system.
Each agent can take chat input and produce chat output with full support for tool/function 
calling using AI frameworks like OpenAI SDK, CrewAI, and LangChain/LangGraph.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator

from .base_agent import BaseAgent, AgentConfig
from ..services import get_agent_service, get_chat_service

# Configure logging
logger = logging.getLogger(__name__)

# Try to import demo agent for demonstration purposes
try:
    from demo_agent import DemoAgent
    DEMO_AGENT_AVAILABLE = True
except ImportError:
    logger.warning("demo_agent module not available")
    DEMO_AGENT_AVAILABLE = False
    DemoAgent = None

# List of available custom agents - this will be used by the frontend for the dropdown menu
CUSTOM_AGENTS = [
    "OpenAIDemoAgent",
]

if DEMO_AGENT_AVAILABLE:
    CUSTOM_AGENTS.append("DemoAgent")


class CustomAgentBase(ABC):
    """
    Base class for custom agents with chat input/output capabilities
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def process_chat_input(self, input_message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process chat input and return chat output
        
        Args:
            input_message: The user's chat message
            context: Optional context information
            
        Returns:
            The agent's response message
        """
        pass
    
    @abstractmethod
    async def process_chat_stream(self, input_message: str, context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """
        Process chat input and return streaming chat output
        
        Args:
            input_message: The user's chat message
            context: Optional context information
            
        Yields:
            Chunks of the agent's response message
        """
        pass


class OpenAIDemoAgent(CustomAgentBase):
    """
    OpenAI Demo Agent for ICUI Framework
    
    This agent demonstrates OpenAI capabilities within the ICUI framework
    with support for tool/function calling and streaming responses.
    """
    
    def __init__(self):
        super().__init__(
            name="OpenAI Demo Agent",
            description="An agent that demonstrates OpenAI capabilities within the ICUI framework with tool calling support."
        )
        self.capabilities = ["chat", "reasoning", "code_generation", "tool_calling"]
        self.model = "gpt-4o-mini"
        self.temperature = 0.7
        self.max_tokens = 2000
    
    async def process_chat_input(self, input_message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process chat input using OpenAI API with tool calling capabilities
        """
        try:
            # For now, return a simple response - this will be enhanced with actual OpenAI API calls
            # and tool calling in future iterations
            response = f"OpenAI Demo Agent received: {input_message}\n\n"
            response += "This is a demonstration response. In a full implementation, this would:\n"
            response += "1. Use OpenAI API for intelligent responses\n"
            response += "2. Support tool/function calling\n"
            response += "3. Maintain conversation context\n"
            response += "4. Handle code generation and reasoning tasks"
            
            logger.info(f"OpenAI Demo Agent processed input: {input_message[:50]}...")
            return response
            
        except Exception as e:
            logger.error(f"Error in OpenAI Demo Agent: {e}")
            return f"Error processing request: {str(e)}"
    
    async def process_chat_stream(self, input_message: str, context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """
        Process chat input and return streaming response
        """
        try:
            # Simulate streaming response - in a full implementation this would use OpenAI's streaming API
            response_parts = [
                "OpenAI Demo Agent is processing your request...\n\n",
                f"Input received: {input_message}\n\n",
                "This is a streaming demonstration. ",
                "Each chunk would come from the OpenAI API. ",
                "The agent supports:\n",
                "• Tool and function calling\n",
                "• Code generation and analysis\n",
                "• Reasoning and problem solving\n",
                "• Context-aware responses\n\n",
                "Ready for full implementation with actual AI capabilities!"
            ]
            
            for part in response_parts:
                yield part
                # Small delay to simulate streaming
                import asyncio
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in OpenAI Demo Agent streaming: {e}")
            yield f"Error processing streaming request: {str(e)}"


async def auto_initialize_chat_agent():
    """
    Automatically create a default agent and configure chat service on startup.
    
    This function has been abstracted from main.py to provide better separation of concerns
    and allow for custom agent implementations.
    """
    try:
        logger.info("🚀 Auto-initializing chat agent...")
        
        # Get agent and chat services
        agent_service = await get_agent_service()
        chat_service = get_chat_service()
        
        # Check if an agent is already configured
        if chat_service.config.agent_id:
            logger.info(f"✅ Chat agent already configured: {chat_service.config.agent_id}")
            return
        
        # Check if there are existing agent sessions
        existing_sessions = agent_service.get_agent_sessions()
        if existing_sessions:
            # Use the first available agent
            first_agent = existing_sessions[0]
            logger.info(f"🔄 Using existing agent: {first_agent.agent_name} ({first_agent.agent_id})")
            await chat_service.update_config({"agent_id": first_agent.agent_id})
            return
        
        # Create a new default agent using AgentConfig
        logger.info("🤖 Creating default OpenAI agent...")
        
        agent_config = AgentConfig(
            name="default_chat_agent",
            framework="openai",
            role="assistant",
            goal="Help users with questions, code assistance, and general tasks",
            backstory="I am a helpful AI assistant powered by OpenAI's GPT-4o-mini model",
            capabilities=["chat", "reasoning", "code_generation"],
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=2000,
            custom_config={
                "stream": True
            }
        )
        
        # Create the agent
        agent_session_id = await agent_service.create_agent(agent_config)
        
        # Get the agent ID from the session
        sessions = agent_service.get_agent_sessions()
        agent_id = None
        for session in sessions:
            if session.session_id == agent_session_id:
                agent_id = session.agent_id
                break
        
        if agent_id:
            logger.info(f"✅ Created default agent: {agent_id}")
            
            # Configure chat service to use this agent
            await chat_service.update_config({"agent_id": agent_id})
            logger.info(f"✅ Chat service configured with agent: {agent_id}")
        else:
            logger.error("❌ Failed to get agent ID after creation")
            
    except Exception as e:
        logger.error(f"💥 Error during auto-initialization: {e}")
        logger.exception("Full traceback:")


def get_available_custom_agents() -> List[str]:
    """
    Get list of available custom agent names for frontend dropdown menu
    
    Returns:
        List of custom agent class names
    """
    return CUSTOM_AGENTS.copy()


def create_custom_agent(agent_name: str) -> Optional[CustomAgentBase]:
    """
    Factory function to create custom agent instances
    
    Args:
        agent_name: Name of the agent class to create
        
    Returns:
        Custom agent instance or None if not found
    """
    try:
        if agent_name == "OpenAIDemoAgent":
            return OpenAIDemoAgent()
        else:
            logger.warning(f"Unknown custom agent: {agent_name}")
            return None
    except Exception as e:
        logger.error(f"Error creating custom agent {agent_name}: {e}")
        return None