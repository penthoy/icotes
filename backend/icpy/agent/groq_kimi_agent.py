"""
GroqKimiAgent - A generic AI agent powered by Groq models (Kimi K2) with tool support.

This agent:
1) Streams responses via Groq OpenAI-compatible client
2) Can call tools using the shared OpenAIStreamingHandler
3) Uses standard metadata and hot-reload helpers
4) Uses advanced prompting with dynamic tools summary and environment context
5) Normalizes history and filters empty messages to prevent provider errors
"""

import json
import os
import logging
from typing import Dict, List, Generator, Any

# Configure logging
logger = logging.getLogger(__name__)

# Default model for Groq (Kimi K2 as per Groq docs: moonshotai/kimi-k2-instruct-0905)
AGENT_MODEL_ID = "moonshotai/kimi-k2-instruct-0905"
AGENT_NAME = "GroqKimiAgent"
AGENT_DESCRIPTION = "Generic AI assistant powered by Groq (Kimi K2) with tool calling"
MODEL_NAME = AGENT_MODEL_ID

# Base system prompt template is centralized in helpers

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
    from icpy.agent.clients import get_groq_client
    from icpy.agent.helpers import (
        create_standard_agent_metadata,
        create_environment_reload_function,
        get_available_tools_summary,
        OpenAIStreamingHandler,
        add_context_to_agent_prompt,
        flatten_message_content,
        normalize_history,
        BASE_SYSTEM_PROMPT_TEMPLATE,
    )

    DEPENDENCIES_AVAILABLE = True
    logger.info("All dependencies available for GroqKimiAgent")

    AGENT_METADATA = create_standard_agent_metadata(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        version="1.0.0",
        author="ICUI Framework",
        model=AGENT_MODEL_ID,
    )

    reload_env = create_environment_reload_function([
        "icpy.agent.helpers",
        "icpy.agent.clients",
    ])

except ImportError as e:
    logger.warning(f"Import error in GroqKimiAgent: {e}")
    DEPENDENCIES_AVAILABLE = False
    AGENT_METADATA = {
        "AGENT_NAME": AGENT_NAME,
        "AGENT_DESCRIPTION": AGENT_DESCRIPTION,
        "AGENT_VERSION": "1.0.0",
        "AGENT_AUTHOR": "ICUI Framework",
        "MODEL_NAME": MODEL_NAME,
        "AGENT_MODEL_ID": AGENT_MODEL_ID,
        "status": "error",
        "error": f"Dependencies not available: {e}",
    }

    def reload_env():
        logger.info("GroqKimiAgent: Environment reload requested")


def chat(message: str, history: List[Dict[str, str]]) -> Generator[str, None, None]:
    """
    Main chat function for GroqKimiAgent with tool support.

    Args:
        message: User input message
        history: Conversation history as list of message dicts

    Yields:
        str: Response chunks as they arrive
    """
    if not DEPENDENCIES_AVAILABLE:
        yield "🚫 GroqKimiAgent dependencies are not available. Please check your setup and try again."
        return

    # Build base system prompt with current tools summary and add dynamic context info
    tools_summary = get_available_tools_summary()
    base_system_prompt = BASE_SYSTEM_PROMPT_TEMPLATE.format(AGENT_NAME=AGENT_NAME, TOOLS_SUMMARY=tools_summary)
    system_prompt = add_context_to_agent_prompt(base_system_prompt)

    try:
        client = get_groq_client()

        # Normalize history (handles JSON string input and content flattening)
        normalized_history = normalize_history(history)

        # Base conversation messages
        system_message = {"role": "system", "content": system_prompt}
        messages: List[Dict[str, Any]] = [system_message] + normalized_history

        # Append current user message only if non-empty
        if isinstance(message, str) and message.strip():
            messages.append({"role": "user", "content": message})
        else:
            logger.info("GroqKimiAgent: Skipping trailing user message because it's empty (provided by caller as \"\")")

        # Final safety filter before sending
        safe_messages: List[Dict[str, Any]] = []
        dropped = 0
        for i, m in enumerate(messages):
            c = m.get("content", "")
            if m.get("role") == "user" and (not isinstance(c, str) or not c.strip()):
                dropped += 1
                logger.warning(f"GroqKimiAgent: Removing empty user message at position {i}")
                continue
            if not isinstance(c, str):
                m = {**m, "content": flatten_message_content(c)}
            safe_messages.append(m)
        if dropped:
            logger.info(f"GroqKimiAgent: Dropped {dropped} empty user message(s) before request")

        # Debug preview: roles and content lengths
        try:
            preview = "\n".join([f"{i}: {m['role']} len={len(m.get('content','') or '')}" for i, m in enumerate(safe_messages)])
            logger.debug("GroqKimiAgent: Outbound messages preview\n" + preview)
        except Exception:
            pass

        handler = OpenAIStreamingHandler(client, MODEL_NAME)
        logger.info("GroqKimiAgent: Starting chat with tools using Groq client")
        yield from handler.stream_chat_with_tools(safe_messages)
        logger.info("GroqKimiAgent: Chat completed successfully")

    except Exception as e:
        logger.error(f"Error in GroqKimiAgent streaming: {e}")
        yield f"🚫 Error processing request: {str(e)}\n\nPlease check your GROQ_API_KEY configuration."


if __name__ == "__main__":
    # Simple smoke test (non-streaming display)
    for chunk in chat("Hello, what can you help me with?", []):
        print(chunk, end="")
    print()
