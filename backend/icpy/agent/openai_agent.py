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

# Import OpenAI client
try:
    from .clients import get_openai_client
    OPENAI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"OpenAI client not available: {e}")
    OPENAI_AVAILABLE = False


# def chat_deprecate(message, history):
#     """
#     OpenAI Demo Agent chat function matching personal_agent.py format
    
#     Args:
#         message: User message string
#         history: List of message dicts with 'role' and 'content' keys
        
#     Returns:
#         String response from OpenAI
#     """
#     if not OPENAI_AVAILABLE:
#         return "OpenAI client not available. Please check configuration."
    
#     try:
#         if isinstance(history, str):
#             history = json.loads(history)
        
#         # Build conversation messages
#         system_message = {
#             "role": "system", 
#             "content": "You are a helpful AI assistant. You are part of the ICUI framework, a powerful code editor and development environment. Help users with coding, development tasks, and general questions."
#         }
        
#         messages = [system_message] + history + [{"role": "user", "content": message}]
        
#         # Call OpenAI API
#         client = get_openai_client()
#         response = client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=messages,
#             temperature=0.7,
#             max_tokens=2000
#         )
        
#         return response.choices[0].message.content
        
#     except Exception as e:
#         logger.error(f"Error in OpenAI Demo Agent: {e}")
#         return f"Error processing request: {str(e)}"


def chat(message, history):
    """
    OpenAI Demo Agent streaming chat function matching personal_agent.py format
    
    Args:
        message: User message string
        history: List of message dicts with 'role' and 'content' keys
        
    Yields:
        String chunks of the streaming response
    """
    logger.info(f"🤖 [DEBUG] OpenAI agent chat() called with message: '{message[:50]}...'")
    if not OPENAI_AVAILABLE:
        logger.warning(f"🤖 [DEBUG] OpenAI not available, yielding error message")
        yield "OpenAI client not available. Please check configuration."
        return
    
    try:
        if isinstance(history, str):
            history = json.loads(history)
        
        # Build conversation messages
        system_message = {
            "role": "system", 
            "content": "You are a helpful AI assistant. You are part of the ICUI framework, a powerful code editor and development environment. Help users with coding, development tasks, and general questions."
        }
        
        messages = [system_message] + history + [{"role": "user", "content": message}]
        
        # Call OpenAI streaming API
        logger.info(f"🤖 [DEBUG] Creating OpenAI streaming call")
        client = get_openai_client()
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            stream=True
        )
        
        logger.info(f"🤖 [DEBUG] Starting OpenAI stream iteration")
        chunk_count = 0
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                chunk_count += 1
                content = chunk.choices[0].delta.content
                if chunk_count == 1:
                    logger.info(f"🤖 [DEBUG] OpenAI FIRST chunk: '{content[:20]}...'")
                elif chunk_count <= 5:
                    logger.info(f"🤖 [DEBUG] OpenAI chunk {chunk_count}: '{content[:20]}...'")
                yield content
        
        logger.info(f"🤖 [DEBUG] OpenAI stream complete. Total chunks: {chunk_count}")
                
    except Exception as e:
        logger.error(f"Error in OpenAI Demo Agent streaming: {e}")
        yield f"Error processing streaming request: {str(e)}"


if __name__ == "__main__":
    # Test the chat function
    result = chat("Hello, what can you help me with?", [])
    print(result)
