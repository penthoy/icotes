"""
OpenAIAgent - A generic AI agent powered by OpenAI models with tool support.

This agent:
1) Streams responses via OpenAI-compatible client
2) Can call tools using the shared OpenAIStreamingHandler
3) Uses standard metadata and hot-reload helpers
"""

import json
import os
import logging
from typing import Dict, List, Generator

# Configure logging
logger = logging.getLogger(__name__)

# Default model for OpenAI
AGENT_MODEL_ID = "gpt-5-mini"
AGENT_NAME = "OpenAIAgent"
AGENT_DESCRIPTION = "Generic AI assistant powered by OpenAI models with tool calling"
MODEL_NAME = AGENT_MODEL_ID

# Import required modules and helpers
try:
    import sys
    backend_path = os.environ.get("ICOTES_BACKEND_PATH")
    if not backend_path:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        while current_dir and current_dir != '/':
            backend_candidate = os.path.join(current_dir, 'backend')
            if os.path.isdir(backend_candidate) and os.path.isdir(os.path.join(backend_candidate, 'icpy')):
                backend_path = backend_candidate
                break
            current_dir = os.path.dirname(current_dir)
        if not backend_path:
            backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend"))
    sys.path.append(backend_path)

    # Client + helpers
    from icpy.agent.clients import get_openai_client
    from icpy.agent.helpers import (
        create_standard_agent_metadata,
        create_environment_reload_function,
        get_available_tools_summary,
        OpenAIStreamingHandler,
        add_context_to_agent_prompt,
    )

    DEPENDENCIES_AVAILABLE = True
    logger.info("All dependencies available for OpenAIAgent")

    AGENT_METADATA = create_standard_agent_metadata(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        version="1.1.0",
        author="ICUI Framework",
        model=AGENT_MODEL_ID,
    )

    reload_env = create_environment_reload_function([
        "icpy.agent.helpers",
        "icpy.agent.clients",
    ])

except ImportError as e:
    logger.warning(f"Import error in OpenAIAgent: {e}")
    DEPENDENCIES_AVAILABLE = False
    AGENT_METADATA = {
        "AGENT_NAME": AGENT_NAME,
        "AGENT_DESCRIPTION": AGENT_DESCRIPTION,
        "AGENT_VERSION": "1.1.0",
        "AGENT_AUTHOR": "ICUI Framework",
        "MODEL_NAME": MODEL_NAME,
        "AGENT_MODEL_ID": AGENT_MODEL_ID,
        "status": "error",
        "error": f"Dependencies not available: {e}",
    }

    def reload_env():
        logger.info("OpenAIAgent: Environment reload requested")


def chat(message: str, history: List[Dict[str, str]]) -> Generator[str, None, None]:
    """
    Main chat function for OpenAIAgent with tool support.

    Args:
        message: User input message
        history: Conversation history as list of message dicts

    Yields:
        str: Response chunks as they arrive
    """
    if not DEPENDENCIES_AVAILABLE:
        yield "🚫 OpenAIAgent dependencies are not available. Please check your setup and try again."
        return

    base_system_prompt = f"""You are {AGENT_NAME}, a helpful and capable AI assistant powered by OpenAI models.

**Available Tools:**
{get_available_tools_summary()}

Follow best practices, be concise but helpful, and call tools when they improve your answer."""

    system_prompt = add_context_to_agent_prompt(base_system_prompt)

    try:
        client = get_openai_client()

        if isinstance(history, str):
            history = json.loads(history)

        system_message = {"role": "system", "content": system_prompt}
        messages = [system_message] + history + [{"role": "user", "content": message}]

        handler = OpenAIStreamingHandler(client, MODEL_NAME)
        logger.info("OpenAIAgent: Starting chat with tools using OpenAI client")
        yield from handler.stream_chat_with_tools(messages)
        logger.info("OpenAIAgent: Chat completed successfully")

    except Exception as e:
        logger.error(f"Error in OpenAIAgent streaming: {e}")
        yield f"🚫 Error processing request: {str(e)}\n\nPlease check your OpenAI API key configuration (OPENAI_API_KEY)."


if __name__ == "__main__":
    # Simple smoke test (non-streaming display)
    for chunk in chat("Hello, what can you help me with?", []):
        print(chunk, end="")
    print()
