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

def register_custom_agent():
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
    return list(register_custom_agent().keys())


def get_agent_chat_function(agent_name: str) -> Callable:
    """Get chat function for specified agent name (all functions support streaming)"""
    agent = register_custom_agent().get(agent_name)
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
    import time
    
    start_time = time.time()
    logger.info(f"� [DEBUG] Custom agent {agent_name} starting stream")
    logger.info(f"�🚀 [BACKEND] Starting agent stream for {agent_name} at {time.time()}")
    
    chat_function = get_agent_chat_function(agent_name)
    if not chat_function:
        raise ValueError(f"Unknown custom agent: {agent_name}")
    
    logger.info(f"📞 [BACKEND] Calling {agent_name} chat function after {(time.time() - start_time)*1000:.2f}ms")
    
    # Handle both sync and async generators
    if hasattr(chat_function, '__call__'):
        first_chunk = True
        chunk_count = 0
        for chunk in chat_function(message, history):
            chunk_count += 1
            if first_chunk:
                logger.info(f"🔧 [DEBUG] FIRST CHUNK from {agent_name}: '{chunk[:30]}...' (len={len(chunk)})")
                logger.info(f"🎯 [BACKEND] FIRST CHUNK from {agent_name} after {(time.time() - start_time)*1000:.2f}ms")
                first_chunk = False
            else:
                logger.info(f"🔧 [DEBUG] Chunk {chunk_count}: '{chunk[:30]}...' (len={len(chunk)})")
            yield chunk
        
        logger.info(f"🔧 [DEBUG] Stream complete. Total chunks: {chunk_count}")
        logger.info(f"✅ [BACKEND] Stream complete for {agent_name} after {(time.time() - start_time)*1000:.2f}ms")