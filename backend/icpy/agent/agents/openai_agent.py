"""
OpenAIAgent - A generic AI agent powered by OpenAI models with tool support.
OpenAIStreamingHandler under the hood.
"""

import json
import logging
from typing import Dict, List, Generator, Any

# Configure logging
logger = logging.getLogger(__name__)

# Default model for OpenAI
MODEL_NAME = "gpt-5-mini"
AGENT_NAME = "OpenAIAgent"
AGENT_DESCRIPTION = "Generic AI assistant powered by OpenAI models with tool calling"

# Base system prompt template is centralized in helpers

from icpy.agent.helpers import (
    create_standard_agent_metadata,
    create_environment_reload_function,
    get_available_tools_summary,
    add_context_to_agent_prompt,
    flatten_message_content,
    normalize_history,
    BASE_SYSTEM_PROMPT_TEMPLATE,
)
from icpy.agent.core.llm.openai_client import OpenAIClientAdapter
from icpy.agent.core.runtime.general_agent import GeneralAgent
from icpy.agent.core.runtime.message_utils import build_safe_messages

DEPENDENCIES_AVAILABLE = True

AGENT_METADATA = create_standard_agent_metadata(
    name=AGENT_NAME,
    description=AGENT_DESCRIPTION,
    version="1.2.0",
    author="Icotes",
    model=MODEL_NAME,
)

reload_env = create_environment_reload_function([
    "icpy.agent.helpers",
    "icpy.agent.core.llm.openai_client",
    "icpy.agent.core.runtime.general_agent",
])


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

    # Build base system prompt with current tools summary and add dynamic context info
    tools_summary = get_available_tools_summary()
    base_system_prompt = BASE_SYSTEM_PROMPT_TEMPLATE.format(AGENT_NAME=AGENT_NAME, TOOLS_SUMMARY=tools_summary)
    system_prompt = add_context_to_agent_prompt(base_system_prompt)

    try:
        # Prepare messages using shared utility (preserves previous behavior)
        safe_messages = build_safe_messages(message, history)

        # Delegate to generalized agent using OpenAI adapter
        adapter = OpenAIClientAdapter()
        ga = GeneralAgent(adapter, model=MODEL_NAME)
        logger.info("OpenAIAgent: Starting chat with tools using GeneralAgent")
        yield from ga.run(system_prompt=system_prompt, messages=safe_messages)
        logger.info("OpenAIAgent: Chat completed successfully")

    except Exception as e:
        logger.error(f"Error in OpenAIAgent streaming: {e}")
        yield f"🚫 Error processing request: {str(e)}\n\nPlease check your OpenAI API key configuration (OPENAI_API_KEY)."


if __name__ == "__main__":
    # Simple smoke test (non-streaming display)
    for chunk in chat("Hello, what can you help me with?", []):
        print(chunk, end="")
    print()
