"""
OpenRouterAgent - A generic AI agent powered by OpenRouter models with tool support.

This agent mirrors the structure of KimiAgent/OllamaAgent:
- Streaming via OpenAI-compatible client (OpenRouter)
- Tool execution handled by OpenAIStreamingHandler
- Standard metadata and environment reload hooks
"""

import json
import os
import logging
from typing import Dict, List, Generator

logger = logging.getLogger(__name__)

AGENT_MODEL_ID = "qwen/qwen3-coder:free"
AGENT_NAME = "OpenRouterAgent"
AGENT_DESCRIPTION = "Generic AI assistant powered by OpenRouter models with tool calling"
MODEL_NAME = AGENT_MODEL_ID

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

    from icpy.agent.clients import get_openrouter_client
    from icpy.agent.helpers import (
        create_standard_agent_metadata,
        create_environment_reload_function,
        get_available_tools_summary,
        OpenAIStreamingHandler,
        add_context_to_agent_prompt,
    )

    DEPENDENCIES_AVAILABLE = True
    logger.info("All dependencies available for OpenRouterAgent")

    AGENT_METADATA = create_standard_agent_metadata(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        version="1.0.0",
        author="Hot Reload System",
        model=AGENT_MODEL_ID,
    )

    reload_env = create_environment_reload_function([
        "icpy.agent.helpers",
        "icpy.agent.clients",
    ])

except ImportError as e:
    logger.warning(f"Import error in OpenRouterAgent: {e}")
    DEPENDENCIES_AVAILABLE = False
    AGENT_METADATA = {
        "AGENT_NAME": AGENT_NAME,
        "AGENT_DESCRIPTION": AGENT_DESCRIPTION,
        "AGENT_VERSION": "1.0.0",
        "AGENT_AUTHOR": "Hot Reload System",
        "MODEL_NAME": MODEL_NAME,
        "AGENT_MODEL_ID": AGENT_MODEL_ID,
        "status": "error",
        "error": f"Dependencies not available: {e}",
    }

    def reload_env():
        logger.info("OpenRouterAgent: Environment reload requested")


def chat(message: str, history: List[Dict[str, str]]) -> Generator[str, None, None]:
    """
    Main chat function for OpenRouterAgent with tool support.
    """
    if not DEPENDENCIES_AVAILABLE:
        yield "🚫 OpenRouterAgent dependencies are not available. Please check your setup and try again."
        return

    base_system_prompt = f"""You are {AGENT_NAME}, a helpful and versatile AI assistant powered by OpenRouter models.

**Available Tools:**
{get_available_tools_summary()}

Use tools when they improve your answer; be concise and practical."""

    system_prompt = add_context_to_agent_prompt(base_system_prompt)

    try:
        client = get_openrouter_client()

        if isinstance(history, str):
            history = json.loads(history)

        system_message = {"role": "system", "content": system_prompt}
        messages = [system_message] + history + [{"role": "user", "content": message}]

        handler = OpenAIStreamingHandler(client, MODEL_NAME)
        logger.info("OpenRouterAgent: Starting chat with tools using OpenRouter client")
        yield from handler.stream_chat_with_tools(messages)
        logger.info("OpenRouterAgent: Chat completed successfully")

    except Exception as e:
        logger.error(f"Error in OpenRouterAgent streaming: {e}")
        yield f"🚫 Error processing request: {str(e)}\n\nPlease check your OpenRouter API key configuration (OPENROUTER_API_KEY)."


if __name__ == "__main__":
    for chunk in chat("Hello from OpenRouterAgent!", []):
        print(chunk, end="")
    print()
