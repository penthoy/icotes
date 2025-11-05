"""
Ollama Agent - A generic AI agent powered by local Ollama models

This is a general-purpose AI assistant that can:
Uses local Ollama models for privacy-focused AI assistance.
"""

import logging
from typing import Dict, List, Generator

# Configure logging
logger = logging.getLogger(__name__)

# Agent metadata
AGENT_NAME = "OllamaAgent"
AGENT_DESCRIPTION = "General-purpose AI assistant powered by local Ollama models"
MODEL_NAME = "qwen3:14b"  # Default Ollama model, can be changed

# Import required modules
from icpy.agent.core.llm.ollama_client import OllamaClientAdapter
from icpy.agent.core.runtime.general_agent import GeneralAgent
from icpy.agent.core.runtime.message_utils import build_safe_messages
from icpy.agent.helpers import (
    create_standard_agent_metadata,
    create_environment_reload_function,
    get_available_tools_summary,
    ToolDefinitionLoader,
    add_context_to_agent_prompt,
    BASE_SYSTEM_PROMPT_TEMPLATE,
)

# Agent metadata using helper
AGENT_METADATA = create_standard_agent_metadata(
    name="OllamaAgent", 
    description="General-purpose AI assistant powered by local Ollama models",
    version="1.0.0",
    author="Hot Reload System",
    model=MODEL_NAME,
)

# Environment reload function using helper
reload_env = create_environment_reload_function([
    "icpy.agent.helpers",
    "icpy.agent.core.llm.ollama_client",
    "icpy.agent.core.runtime.general_agent",
    "icpy.agent.core.runtime.message_utils",
])


def chat(message: str, history: List[Dict[str, str]]) -> Generator[str, None, None]:
    """
    Main chat function for OllamaAgent using local Ollama models.
    
    Args:
        message: User input message
        history: Conversation history as list of message dicts
        
    Yields:
        str: Response chunks as they arrive
    """
    # Build base system prompt with current tools summary and add dynamic context info
    tools_summary = get_available_tools_summary()
    base_system_prompt = BASE_SYSTEM_PROMPT_TEMPLATE.format(AGENT_NAME=AGENT_NAME, TOOLS_SUMMARY=tools_summary)
    system_prompt = add_context_to_agent_prompt(base_system_prompt)

    try:
        # Prepare messages using shared utility
        safe_messages = build_safe_messages(message, history)

        # Delegate to generalized agent using Ollama adapter
        adapter = OllamaClientAdapter()
        ga = GeneralAgent(adapter, model=MODEL_NAME)
        logger.info("OllamaAgent: Starting chat with tools using GeneralAgent")
        # Load tool definitions and pass through
        tools = []
        try:
            tools = ToolDefinitionLoader().get_openai_tools()
        except Exception:
            pass
        yield from ga.run(system_prompt=system_prompt, messages=safe_messages, tools=tools)
        logger.info("OllamaAgent: Chat completed successfully")

    except Exception as e:
        logger.error(f"Error in OllamaAgent streaming: {e}")
        import os
        yield f"🚫 Error processing request: {str(e)}\n\nPlease check your Ollama setup and ensure it's running (OLLAMA_URL: {os.getenv('OLLAMA_URL', 'http://localhost:11434/v1')})."


if __name__ == "__main__":
    # Test the chat function locally
    test_message = "Hello, OllamaAgent! Can you introduce yourself and tell me about the benefits of using local AI?"
    test_history = []
    
    print("Testing OllamaAgent:")
    print("\nTest completed!")
