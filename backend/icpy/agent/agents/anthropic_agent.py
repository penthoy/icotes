"""
AnthropicAgent - Generic agent powered by Claude (Anthropic) with tool support.

Delegates streaming to the generalized runtime using the Anthropic adapter.
Shares message preparation logic with other agents to keep behavior consistent.
"""

import logging
from typing import Dict, List, Generator, Any

from icpy.agent.helpers import (
    create_standard_agent_metadata,
    create_environment_reload_function,
    get_available_tools_summary,
    add_context_to_agent_prompt,
    BASE_SYSTEM_PROMPT_TEMPLATE,
)
from icpy.agent.core.llm.anthropic_client import AnthropicClientAdapter
from icpy.agent.core.runtime.general_agent import GeneralAgent
from icpy.agent.core.runtime.message_utils import build_safe_messages


logger = logging.getLogger(__name__)

AGENT_NAME = "AnthropicAgent"
AGENT_DESCRIPTION = "Generic AI assistant powered by Claude (Anthropic) with tool calling"
# Default model (caller can override via environment or params in future evolutions)
MODEL_NAME = "claude-sonnet-4-20250514"

AGENT_METADATA = create_standard_agent_metadata(
    name=AGENT_NAME,
    description=AGENT_DESCRIPTION,
    version="1.0.0",
    author="Icotes",
    model=MODEL_NAME,
)

reload_env = create_environment_reload_function([
    "icpy.agent.helpers",
    "icpy.agent.core.llm.anthropic_client",
    "icpy.agent.core.runtime.general_agent",
    "icpy.agent.core.runtime.message_utils",
])


def chat(message: str, history: List[Dict[str, Any]]) -> Generator[str, None, None]:
    """
    Main chat function for AnthropicAgent with tool support.
    """
    try:
        tools_summary = get_available_tools_summary()
        base_system_prompt = BASE_SYSTEM_PROMPT_TEMPLATE.format(AGENT_NAME=AGENT_NAME, TOOLS_SUMMARY=tools_summary)
        system_prompt = add_context_to_agent_prompt(base_system_prompt)

        safe_messages = build_safe_messages(message, history)

        adapter = AnthropicClientAdapter()
        ga = GeneralAgent(adapter, model=MODEL_NAME)
        logger.info("AnthropicAgent: Starting chat with tools using GeneralAgent")
        yield from ga.run(system_prompt=system_prompt, messages=safe_messages)
        logger.info("AnthropicAgent: Chat completed successfully")
    except Exception as e:
        logger.error(f"Error in AnthropicAgent streaming: {e}")
        yield (
            "🚫 Error processing request: "
            + str(e)
            + "\n\nPlease check your Anthropic API key configuration (ANTHROPIC_API_KEY)."
        )


if __name__ == "__main__":
    for chunk in chat("Hello from Claude", []):
        print(chunk, end="")
    print()
