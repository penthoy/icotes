"""
GeminiAgent - Generic agent powered by Google's Gemini with tool support.

Delegates streaming to the generalized runtime using the Gemini adapter.
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
from icpy.agent.core.llm.gemini_client import GeminiClientAdapter
from icpy.agent.core.runtime.general_agent import GeneralAgent
from icpy.agent.core.runtime.message_utils import build_safe_messages


logger = logging.getLogger(__name__)

AGENT_NAME = "GeminiAgent"
AGENT_DESCRIPTION = "Generic AI assistant powered by Google Gemini with tool calling"
"""
gemini-2.5-flash
gemini-2.5-pro
"""
MODEL_NAME = "gemini-2.5-pro"

AGENT_METADATA = create_standard_agent_metadata(
    name=AGENT_NAME,
    description=AGENT_DESCRIPTION,
    version="1.0.0",
    author="Icotes",
    model=MODEL_NAME,
)

reload_env = create_environment_reload_function([
    "icpy.agent.helpers",
    "icpy.agent.core.llm.gemini_client",
    "icpy.agent.core.runtime.general_agent",
    "icpy.agent.core.runtime.message_utils",
])


def chat(message: str, history: List[Dict[str, Any]]) -> Generator[str, None, None]:
    """Main chat function for GeminiAgent with tool support."""
    try:
        tools_summary = get_available_tools_summary()
        base_system_prompt = BASE_SYSTEM_PROMPT_TEMPLATE.format(AGENT_NAME=AGENT_NAME, TOOLS_SUMMARY=tools_summary)
        system_prompt = add_context_to_agent_prompt(base_system_prompt)

        safe_messages = build_safe_messages(message, history)

        adapter = GeminiClientAdapter()
        ga = GeneralAgent(adapter, model=MODEL_NAME)
        logger.info("GeminiAgent: Starting chat with tools using GeneralAgent")
        yield from ga.run(system_prompt=system_prompt, messages=safe_messages)
        logger.info("GeminiAgent: Chat completed successfully")
    except Exception as e:
        logger.error(f"Error in GeminiAgent streaming: {e}")
        yield (
            "🚫 Error processing request: "
            + str(e)
            + "\n\nPlease check your Google API key configuration (GOOGLE_API_KEY)."
        )


if __name__ == "__main__":
    for chunk in chat("Hello from Gemini", []):
        print(chunk, end="")
    print()
