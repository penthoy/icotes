"""
Custom Agent Registry for ICUI Framework

Simple entry point for custom agents that provides a registry of available chat functions.
This module acts as a bridge between the main.py API and individual agent implementations.
"""

import logging
from typing import List, Dict, Callable, Any, AsyncGenerator

# Configure logging
logger = logging.getLogger(__name__)

# Import available agent chat functions
from .personal_agent import chat as personal_agent_chat, chat_stream as personal_agent_chat_stream
from .openai_agent import chat as openai_agent_chat, chat_stream as openai_agent_chat_stream

def register_custom_agent():
    """Register a custom agent with its chat and optional chat_stream functions
    """
    # Registry of available custom agents and their chat functions
    CUSTOM_AGENTS_REGISTRY: Dict[str, Dict[str, Callable]] = {}
    CUSTOM_AGENTS_REGISTRY["PersonalAgent"] = {
        "chat": personal_agent_chat,
        "chat_stream": personal_agent_chat_stream
    }

    CUSTOM_AGENTS_REGISTRY["OpenAIDemoAgent"] = {
        "chat": openai_agent_chat,
        "chat_stream": openai_agent_chat_stream
    }
    return CUSTOM_AGENTS_REGISTRY


def get_available_custom_agents() -> List[str]:
    """Get list of available custom agent names for frontend dropdown menu"""
    return list(register_custom_agent().keys())


def get_agent_chat_function(agent_name: str, streaming: bool = False) -> Callable:
    """Get chat function for specified agent name"""
    agent = register_custom_agent().get(agent_name)
    if not agent:
        return None
    
    if streaming and "chat_stream" in agent:
        return agent["chat_stream"]
    else:
        return agent["chat"]


def call_custom_agent(agent_name: str, message: str, history: List[Dict[str, Any]]) -> str:
    """Call custom agent with message and history, returns response"""
    chat_function = get_agent_chat_function(agent_name, streaming=False)
    if not chat_function:
        raise ValueError(f"Unknown custom agent: {agent_name}")
    
    return chat_function(message, history)


async def call_custom_agent_stream(agent_name: str, message: str, history: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
    """Call custom agent with streaming support"""
    chat_function = get_agent_chat_function(agent_name, streaming=True)
    if not chat_function:
        raise ValueError(f"Unknown custom agent: {agent_name}")
    
    # Handle both sync and async generators
    if hasattr(chat_function, '__call__'):
        for chunk in chat_function(message, history):
            yield chunk