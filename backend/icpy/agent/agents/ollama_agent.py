"""
Ollama Agent - A generic AI agent powered by local Ollama models

This is a general-purpose AI assistant that can:
1. Answer questions and provide information
2. Help with coding and development tasks
3. Use various tools for file operations
4. Assist with data analysis and research
5. Provide creative writing and content generation

Uses local Ollama models for privacy-focused AI assistance.
"""

import json
import os
import logging
from typing import Dict, List, Generator

# Configure logging
logger = logging.getLogger(__name__)

# Model selection identifier for UI/router consumption
AGENT_MODEL_ID = "qwen3:14b"

# Agent metadata
AGENT_NAME = "OllamaAgent"
AGENT_DESCRIPTION = "General-purpose AI assistant powered by local Ollama models"
MODEL_NAME = "qwen3:14b"  # Default Ollama model, can be changed

# Import required modules
try:
    import sys
    backend_path = os.environ.get("ICOTES_BACKEND_PATH")
    if not backend_path:
        # Find the icotes root directory (should contain backend/ directory)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        while current_dir and current_dir != '/':
            backend_candidate = os.path.join(current_dir, 'backend')
            if os.path.isdir(backend_candidate) and os.path.isdir(os.path.join(backend_candidate, 'icpy')):
                backend_path = backend_candidate
                break
            current_dir = os.path.dirname(current_dir)
        
        if not backend_path:
            # Fallback to relative path from workspace/.icotes/plugins/
            backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend"))
    
    sys.path.append(backend_path)

    # Import Ollama client and streaming handler + shared helpers
    from icpy.agent.clients import get_ollama_client
    from icpy.agent.helpers import (
        create_standard_agent_metadata,
        create_environment_reload_function,
        get_available_tools_summary,
        OpenAIStreamingHandler,
        add_context_to_agent_prompt,
    )

    DEPENDENCIES_AVAILABLE = True
    logger.info("All dependencies available for OllamaAgent")

    # Agent metadata using helper (after import)
    AGENT_METADATA = create_standard_agent_metadata(
        name="OllamaAgent", 
        description="General-purpose AI assistant powered by local Ollama models",
        version="1.0.0",
        author="Hot Reload System",
        model=AGENT_MODEL_ID,
    )

    # Environment reload function using helper
    reload_env = create_environment_reload_function([
        "icpy.agent.helpers",
        "icpy.agent.clients",
    ])

except ImportError as e:
    logger.warning(f"Import error in OllamaAgent: {e}")
    DEPENDENCIES_AVAILABLE = False
    AGENT_METADATA = {
        "AGENT_NAME": AGENT_NAME,
        "AGENT_DESCRIPTION": AGENT_DESCRIPTION,
        "AGENT_VERSION": "1.0.0",
        "AGENT_AUTHOR": "Hot Reload System",
        "MODEL_NAME": MODEL_NAME if 'MODEL_NAME' in globals() else AGENT_MODEL_ID,
        "AGENT_MODEL_ID": AGENT_MODEL_ID,
        "status": "error",
        "error": f"Dependencies not available: {e}",
    }

    def reload_env():
        """Fallback reload function"""
        logger.info("OllamaAgent: Environment reload requested")


def chat(message: str, history: List[Dict[str, str]]) -> Generator[str, None, None]:
    """
    Main chat function for OllamaAgent using local Ollama models.
    
    Args:
        message: User input message
        history: Conversation history as list of message dicts
        
    Yields:
        str: Response chunks as they arrive
    """
    if not DEPENDENCIES_AVAILABLE:
        yield "🚫 OllamaAgent dependencies are not available. Please check your setup and try again."
        return

    # Base system prompt for general-purpose assistant
    base_system_prompt = f"""You are OllamaAgent, a helpful and versatile AI assistant running locally via Ollama.

**Available Tools:**
{get_available_tools_summary()}

You can help users with:
1. **General Questions**: Answer questions on a wide range of topics
2. **Programming Help**: Write, debug, and explain code in various languages
3. **File Operations**: Read, write, and modify files using available tools
4. **Data Analysis**: Help analyze and process data
5. **Research**: Search for information and provide comprehensive answers
6. **Writing**: Assist with creative writing, documentation, and content creation
7. **Problem Solving**: Break down complex problems and provide solutions

**Core Behavior:**
1. Be helpful, accurate, and informative in your responses
2. Use tools when appropriate to provide better assistance
3. Explain your reasoning and approach clearly
4. Ask for clarification when requests are ambiguous
5. Provide practical, actionable advice
6. Respect user privacy (you run locally)

**Tool Usage:**
- Use file tools (read_file, create_file, replace_string_in_file) for file operations
- Use run_in_terminal for executing commands and scripts
- Use semantic_search to find relevant information in the workspace
- Always explain briefly what you're doing before using a tool

**Response Style:**
- Be concise but thorough
- Use clear formatting and structure
- Provide examples when helpful
- Acknowledge limitations when relevant

**Local AI Advantages:**
- Complete privacy - your data stays on your machine
- No internet dependency for basic operations
- Customizable model selection based on your hardware
- Cost-effective for extensive usage

Focus on being genuinely helpful while leveraging your local processing capabilities and the available tools effectively."""
    
    # Add context information to the system prompt with dynamic workspace detection
    system_prompt = add_context_to_agent_prompt(base_system_prompt)
    
    try:
        # Get Ollama client
        client = get_ollama_client()
        
        # Handle JSON string history (gradio compatibility)  
        if isinstance(history, str):
            history = json.loads(history)
        
        # Build conversation messages
        system_message = {"role": "system", "content": system_prompt}
        messages = [system_message] + history + [{"role": "user", "content": message}]
        
        # Create streaming handler and process
        handler = OpenAIStreamingHandler(client, MODEL_NAME)
        
        logger.info("OllamaAgent: Starting chat with tools using Ollama client")
        # Enable auto-continue by default with sane limits
        yield from handler.stream_chat_with_tools(messages)
        logger.info("OllamaAgent: Chat completed successfully")
                
    except Exception as e:
        logger.error(f"Error in OllamaAgent streaming: {e}")
        yield f"🚫 Error processing request: {str(e)}\n\nPlease check your Ollama setup and ensure it's running (OLLAMA_URL: {os.getenv('OLLAMA_URL', 'http://localhost:11434/v1')})."


if __name__ == "__main__":
    # Test the chat function locally
    test_message = "Hello, OllamaAgent! Can you introduce yourself and tell me about the benefits of using local AI?"
    test_history = []
    
    print("Testing OllamaAgent:")
    print("\nTest completed!")
