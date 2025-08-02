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
from .personal_agent import chat as personal_agent_chat
from .openai_agent import chat as openai_agent_chat
from .openrouter_agent import chat as openrouter_agent_chat

def build_agent_registry():
    """Register a custom agent with its chat functions (all streaming by default)
    """
    # Registry of available custom agents and their chat functions
    CUSTOM_AGENTS_REGISTRY: Dict[str, Dict[str, Callable]] = {}
    CUSTOM_AGENTS_REGISTRY["PersonalAgent"] = {"chat": personal_agent_chat}
    CUSTOM_AGENTS_REGISTRY["OpenAIDemoAgent"] = {"chat": openai_agent_chat}
    CUSTOM_AGENTS_REGISTRY["OpenRouterAgent"] = {"chat": openrouter_agent_chat}
    return CUSTOM_AGENTS_REGISTRY


def get_available_custom_agents() -> List[str]:
    """Get list of available custom agent names for frontend dropdown menu"""
    return list(build_agent_registry().keys())


def get_agent_chat_function(agent_name: str) -> Callable:
    """Get chat function for specified agent name (all functions support streaming)"""
    agent = build_agent_registry().get(agent_name)
    if not agent:
        return None
    
    return agent["chat"]


def call_custom_agent(agent_name: str, message: str, history: List[Dict[str, Any]]) -> str:
    """Call custom agent with message and history, returns response (streaming generator)"""
    chat_function = get_agent_chat_function(agent_name)
    if not chat_function:
        raise ValueError(f"Unknown custom agent: {agent_name}")
    
    return chat_function(message, history)


async def call_custom_agent_stream(agent_name: str, message: str, history: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
    """Call custom agent with streaming support"""
    chat_function = get_agent_chat_function(agent_name)
    if not chat_function:
        raise ValueError(f"Unknown custom agent: {agent_name}")
    
    # Handle both sync and async generators
    if hasattr(chat_function, '__call__'):
        for chunk in chat_function(message, history):
            yield chunk