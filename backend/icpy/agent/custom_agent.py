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

# List of available custom agents - this will be used by the frontend for the dropdown menu
CUSTOM_AGENTS = [
    "OpenAIDemoAgent",
]


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