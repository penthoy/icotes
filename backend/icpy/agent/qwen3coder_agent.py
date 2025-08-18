"""
OpenAI Demo Agent for ICUI Framework

This module provides OpenAI-based chat functions that match the personal_agent.py format
for integration with the custom agent system.
"""

import json
import logging
from typing import Dict, Any, List

# Configure logging
logger = logging.getLogger(__name__)

# Import OpenRouter client
try:
    from .clients import get_openrouter_client
    OPENAI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"OpenAI client not available: {e}")
    OPENAI_AVAILABLE = False


def chat(message, history):
    """
    OpenAI Demo Agent streaming chat function
    
    Args:
        message: User message string
        history: List of message dicts with 'role' and 'content' keys
        
    Yields:
        String chunks of the streaming response
    """
    if not OPENAI_AVAILABLE:
        yield "OpenAI client not available. Please check configuration."
        return
    
    try:
        if isinstance(history, str):
            history = json.loads(history)
        
        # Build conversation messages
        system_message = {
            "role": "system", 
            "content": "You are a helpful AI assistant."
        }
        
        messages = [system_message] + history + [{"role": "user", "content": message}]

        # Call OpenRouter streaming API
        client = get_openrouter_client()
        stream = client.chat.completions.create(
            model="qwen/qwen3-coder:free",  # Much faster model
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            stream=True
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
                
    except Exception as e:
        logger.error(f"Error in OpenAI Demo Agent streaming: {e}")
        yield f"Error processing streaming request: {str(e)}"


if __name__ == "__main__":
    # Test the chat function
    result = chat("Hello, what can you help me with?", [])
    print(result)
