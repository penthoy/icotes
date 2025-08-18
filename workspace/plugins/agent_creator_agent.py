"""
Agent Creator - An AI agent that helps create other custom agents

This agent specializes in:
1. Creating custom agent code
2. Agent architecture design
3. Integration patterns
4. Best practices for agent development
"""

import json
import os
import logging
from typing import Dict, List, Any

# Configure logging
logger = logging.getLogger(__name__)

# Agent metadata
AGENT_NAME = "AgentCreator"
AGENT_DESCRIPTION = "An AI agent that helps you create other custom agents"
AGENT_VERSION = "1.0.0"
AGENT_AUTHOR = "Hot Reload System"

# Import OpenAI client
try:
    import sys
    backend_path = os.environ.get("ICOTES_BACKEND_PATH")
    if not backend_path:
        # Default to ../backend relative to this file
        backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
    sys.path.append(backend_path)
    from icpy.agent.clients import get_openai_client
    OPENAI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"OpenAI client not available: {e}")
    OPENAI_AVAILABLE = False

def chat(message, history):
    """
    Agent Creator streaming chat function using OpenAI
    
    Args:
        message: str - User message
        history: List[Dict] or str (JSON) - Conversation history
        
    Yields:
        str - Response chunks for streaming
    """
    if not OPENAI_AVAILABLE:
        yield "🚫 OpenAI client not available. Please check your OPENAI_API_KEY configuration."
        return
    
    try:
        # Handle JSON string history (gradio compatibility)
        if isinstance(history, str):
            history = json.loads(history)
        
        # Build conversation messages with specialized system prompt
        system_message = {
            "role": "system", 
            "content": """You are AgentCreator, an expert AI agent specialized in helping developers create custom agents for the icotes. 

Your expertise includes:
- Python agent development patterns
- Gradio-compatible chat functions
- Hot reload agent architecture
- Environment variable management
- Agent metadata and configuration
- Integration with ICUI's custom agent system

You help users:
1. Design agent architectures and workflows
2. Write clean, maintainable agent code
3. Implement proper error handling and logging
4. Follow ICUI agent conventions and best practices
5. Create agents that work seamlessly with the hot reload system

Always provide practical, working code examples when requested. Focus on the ICUI agent format with:
- A `chat(message, history)` function that yields response chunks
- Proper metadata (AGENT_NAME, AGENT_DESCRIPTION, etc.)
- Optional `reload_env()` function for environment reloading
- Gradio-compatible interface patterns

Be helpful, concise, and focus on actionable guidance for agent creation."""
        }
        
        messages = [system_message] + history + [{"role": "user", "content": message}]
        
        # Call OpenAI streaming API
        logger.info("AgentCreator: Creating OpenAI streaming call")
        client = get_openai_client()
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            stream=True
        )
        
        logger.info("AgentCreator: Starting OpenAI stream iteration")
        chunk_count = 0
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                chunk_count += 1
                content = chunk.choices[0].delta.content
                yield content
        
        logger.info(f"AgentCreator: OpenAI stream complete. Total chunks: {chunk_count}")
                
    except Exception as e:
        logger.error(f"Error in AgentCreator streaming: {e}")
        yield f"🚫 Error processing request: {str(e)}\n\nPlease check your OpenAI API key configuration."

def reload_env():
    """Called when environment variables are reloaded"""
    pass

if __name__ == "__main__":
    # Test the chat function locally
    test_message = "Hello, AgentCreator! Can you help me create a simple agent?"
    test_history = []
    
    print("Testing AgentCreator:")
    for chunk in chat(test_message, test_history):
        print(chunk, end="")
    print("\n\nTest completed!") 