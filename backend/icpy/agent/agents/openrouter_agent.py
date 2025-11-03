"""
OpenRouterAgent - A generic AI agent powered by OpenRouter models with tool support.

This agent delegates to GeneralAgent with OpenRouterClientAdapter for:
- Streaming via OpenRouter's OpenAI-compatible API
- Tool execution through the unified runtime
- Standard metadata and environment reload hooks
"""

import logging
from typing import Dict, List, Generator

logger = logging.getLogger(__name__)

MODEL_NAME = "qwen/qwen3-coder:free"
AGENT_NAME = "OpenRouterAgent"
AGENT_DESCRIPTION = "Generic AI assistant powered by OpenRouter models with tool calling"

from icpy.agent.core.llm.openrouter_client import OpenRouterClientAdapter
from icpy.agent.core.runtime.general_agent import GeneralAgent
from icpy.agent.core.runtime.message_utils import build_safe_messages
from icpy.agent.helpers import (
    create_standard_agent_metadata,
    create_environment_reload_function,
    get_available_tools_summary,
    add_context_to_agent_prompt,
    BASE_SYSTEM_PROMPT_TEMPLATE,
)

AGENT_METADATA = create_standard_agent_metadata(
    name=AGENT_NAME,
    description=AGENT_DESCRIPTION,
    version="1.0.0",
    author="Hot Reload System",
    model=MODEL_NAME,
)

reload_env = create_environment_reload_function([
    "icpy.agent.helpers",
    "icpy.agent.core.llm.openrouter_client",
    "icpy.agent.core.runtime.general_agent",
    "icpy.agent.core.runtime.message_utils",
])


def chat(message: str, history: List[Dict[str, str]]) -> Generator[str, None, None]:
    """
    Main chat function for OpenRouterAgent with tool support.
    """
    # Build base system prompt with current tools summary and add dynamic context info
    tools_summary = get_available_tools_summary()
    base_system_prompt = BASE_SYSTEM_PROMPT_TEMPLATE.format(AGENT_NAME=AGENT_NAME, TOOLS_SUMMARY=tools_summary)
    system_prompt = add_context_to_agent_prompt(base_system_prompt)

    try:
        # Prepare messages using shared utility
        safe_messages = build_safe_messages(message, history)

        # Delegate to generalized agent using OpenRouter adapter
        adapter = OpenRouterClientAdapter()
        ga = GeneralAgent(adapter, model=MODEL_NAME)
        logger.info("OpenRouterAgent: Starting chat with tools using GeneralAgent")
        yield from ga.run(system_prompt=system_prompt, messages=safe_messages)
        logger.info("OpenRouterAgent: Chat completed successfully")

    except Exception as e:
        logger.error(f"Error in OpenRouterAgent streaming: {e}")
        yield f"🚫 Error processing request: {str(e)}\n\nPlease check your OpenRouter API key configuration (OPENROUTER_API_KEY)."


if __name__ == "__main__":
    for chunk in chat("Hello from OpenRouterAgent!", []):
        print(chunk, end="")
    print()
