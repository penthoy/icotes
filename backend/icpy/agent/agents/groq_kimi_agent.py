"""
GroqKimiAgent - A generic AI agent powered by Groq models (Kimi K2) with tool support.

This agent:
1) Streams responses via Groq client adapter
2) Can call tools using GeneralAgent runtime
3) Uses standard metadata and hot-reload helpers
4) Uses advanced prompting with dynamic tools summary and environment context
5) Uses build_safe_messages for history normalization
"""

import logging
from typing import Dict, List, Generator

# Configure logging
logger = logging.getLogger(__name__)

# Default model for Groq (Kimi K2 as per Groq docs: moonshotai/kimi-k2-instruct-0905)
MODEL_NAME = "moonshotai/kimi-k2-instruct-0905"
AGENT_NAME = "GroqKimiAgent"
AGENT_DESCRIPTION = "Generic AI assistant powered by Groq (Kimi K2) with tool calling"

# Import required modules and helpers
from icpy.agent.core.llm.groq_client import GroqClientAdapter
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

AGENT_METADATA = create_standard_agent_metadata(
    name=AGENT_NAME,
    description=AGENT_DESCRIPTION,
    version="1.0.0",
    author="Icotes",
    model=MODEL_NAME,
)

reload_env = create_environment_reload_function([
    "icpy.agent.helpers",
    "icpy.agent.core.llm.groq_client",
    "icpy.agent.core.runtime.general_agent",
    "icpy.agent.core.runtime.message_utils",
])


def chat(message: str, history: List[Dict[str, str]]) -> Generator[str, None, None]:
    """
    Main chat function for GroqKimiAgent with tool support.

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

        # Delegate to generalized agent using Groq adapter
        adapter = GroqClientAdapter()
        ga = GeneralAgent(adapter, model=MODEL_NAME)
        logger.info("GroqKimiAgent: Starting chat with tools using GeneralAgent")
        # Load tool definitions and pass through
        tools = []
        try:
            tools = ToolDefinitionLoader().get_openai_tools()
        except Exception:
            pass
        yield from ga.run(system_prompt=system_prompt, messages=safe_messages, tools=tools)
        logger.info("GroqKimiAgent: Chat completed successfully")

    except Exception as e:
        logger.error(f"Error in GroqKimiAgent streaming: {e}")
        yield f"🚫 Error processing request: {str(e)}\n\nPlease check your GROQ_API_KEY configuration."


if __name__ == "__main__":
    # Simple smoke test (non-streaming display)
    for chunk in chat("Hello, what can you help me with?", []):
        print(chunk, end="")
    print()
