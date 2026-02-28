"""
MiniMax M2.5 Agent - AI agent powered by MiniMax's M2.5 model

This is a general-purpose AI assistant that can:
1. Answer questions and provide information
2. Help with coding and development tasks
3. Use various tools for file operations
4. Assist with data analysis and research
5. Provide creative writing and content generation

Uses MiniMax M2.5 through OpenAI-compatible API (direct or via icotesroute).
"""

import logging
from typing import Dict, List, Generator

# Configure logging
logger = logging.getLogger(__name__)

# Agent metadata
AGENT_NAME = "MiniMaxAgent"
AGENT_DESCRIPTION = "General-purpose AI assistant powered by MiniMax M2.5"
MODEL_NAME = "MiniMax-M2.5"  # Default MiniMax model

# Import required modules
from icpy.agent.core.llm.minimax_client import MiniMaxClientAdapter
from icpy.agent.core.runtime.general_agent import GeneralAgent
from icpy.agent.core.runtime.message_utils import build_safe_messages
from icpy.agent.helpers import (
    create_standard_agent_metadata,
    create_environment_reload_function,
    get_available_tools_summary,
    get_thinking_extra_params,
    ToolDefinitionLoader,
    add_context_to_agent_prompt,
    BASE_SYSTEM_PROMPT_TEMPLATE,
)

# Agent metadata using helper
AGENT_METADATA = create_standard_agent_metadata(
    name=AGENT_NAME,
    description=AGENT_DESCRIPTION,
    version="1.0.0",
    author="Icotes",
    model=MODEL_NAME,
)

# Environment reload function using helper
reload_env = create_environment_reload_function([
    "icpy.agent.helpers",
    "icpy.agent.core.llm.minimax_client",
    "icpy.agent.core.runtime.general_agent",
    "icpy.agent.core.runtime.message_utils",
])


def chat(message: str, history: List[Dict[str, str]]) -> Generator[str, None, None]:
    """
    Main chat function for MiniMaxAgent using MiniMax M2.5.

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

        # Delegate to generalized agent using MiniMax adapter
        adapter = MiniMaxClientAdapter()
        ga = GeneralAgent(adapter, model=MODEL_NAME)
        logger.info("MiniMaxAgent: Starting chat with tools using GeneralAgent")
        # Load tool definitions and pass through
        tools = []
        try:
            tools = ToolDefinitionLoader().get_openai_tools()
        except Exception:
            pass
        # Read thinkingMode from agents.json config
        extra_params = get_thinking_extra_params(AGENT_NAME)
        yield from ga.run(system_prompt=system_prompt, messages=safe_messages, tools=tools, extra_params=extra_params)
        logger.info("MiniMaxAgent: Chat completed successfully")

    except Exception as e:
        logger.error(f"Error in MiniMaxAgent streaming: {e}")
        yield f"🚫 Error processing request: {str(e)}\n\nPlease check your MINIMAX_API_KEY or icotesroute configuration."


if __name__ == "__main__":
    for chunk in chat("Briefly introduce yourself.", []):
        print(chunk, end="")
    print()
