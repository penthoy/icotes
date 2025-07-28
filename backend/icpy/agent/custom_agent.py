"""
Custom Agent Registry for ICUI Framework

Simple entry point for custom agents that provides a registry of available chat functions.
This module acts as a bridge between the main.py API and individual agent implementations.
"""

import logging
from typing import List, Dict, Callable, Any

# Configure logging
logger = logging.getLogger(__name__)

# Import available agent chat functions
try:
    from .personal_agent import chat as personal_agent_chat
    PERSONAL_AGENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Personal agent not available: {e}")
    PERSONAL_AGENT_AVAILABLE = False

# Registry of available custom agents and their chat functions
CUSTOM_AGENTS_REGISTRY: Dict[str, Callable] = {}

if PERSONAL_AGENT_AVAILABLE:
    CUSTOM_AGENTS_REGISTRY["PersonalAgent"] = personal_agent_chat

def get_available_custom_agents() -> List[str]:
    """Get list of available custom agent names for frontend dropdown menu"""
    return list(CUSTOM_AGENTS_REGISTRY.keys())

def get_agent_chat_function(agent_name: str) -> Callable:
    """Get chat function for specified agent name"""
    return CUSTOM_AGENTS_REGISTRY.get(agent_name)

def call_custom_agent(agent_name: str, message: str, history: List[Dict[str, Any]]) -> str:
    """Call custom agent with message and history, returns response"""
    chat_function = get_agent_chat_function(agent_name)
    if not chat_function:
        raise ValueError(f"Unknown custom agent: {agent_name}")
    
    return chat_function(message, history)