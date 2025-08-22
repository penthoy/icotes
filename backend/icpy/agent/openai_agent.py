"""
OpenAI Demo Agent for ICUI Framework

This module provides OpenAI-based     logger.info("OpenAI agent chat() called")
    
    if not _is_openai_available():
        logger.warning("OpenAI not available, yielding error message")t functions that match the personal_agent.py format
for integration with the custom agent system.
"""

import json
import logging
from typing import Dict, Any, List

# Configure logging
logger = logging.getLogger(__name__)

# Import helper functions
try:
    from .helpers import create_simple_agent_chat_function, create_standard_agent_metadata
    from .clients import get_openai_client
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False


# Agent metadata
AGENT_METADATA = create_standard_agent_metadata(
    name="OpenAIAgent", 
    description="OpenAI-powered AI assistant for coding and development tasks",
    version="1.1.0",
    author="ICUI Framework"
) if DEPENDENCIES_AVAILABLE else {}


def get_system_prompt():
    """Get the system prompt for the OpenAI agent"""
    return "You are a helpful AI assistant. You are part of the ICUI framework, a powerful code editor and development environment. Help users with coding, development tasks, and general questions."


# Create the chat function using the helper if available
if DEPENDENCIES_AVAILABLE:
    chat = create_simple_agent_chat_function(
        agent_name="OpenAIAgent",
        system_prompt=get_system_prompt(),
        model_name="gpt-4o-mini"
    )


else:
    # Fallback chat function if helpers are not available
    def chat(message, history):
        """Fallback chat function when helpers are not available"""
        yield "🚫 Dependencies not available. Please check configuration."


if __name__ == "__main__":
    # Test the chat function
    result = chat("Hello, what can you help me with?", [])
    print(result)
