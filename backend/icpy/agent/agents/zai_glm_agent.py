"""
ZaiGlmAgent - AI agent powered by Z.AI GLM 4.7 via Cerebras Inference with tool support.

This agent:
1) Streams responses via Cerebras client adapter
2) Can call tools using GeneralAgent runtime
3) Uses standard metadata and hot-reload helpers
4) Uses advanced prompting with dynamic tools summary and environment context
5) Uses build_safe_messages for history normalization

GLM 4.7 features:
- Enhanced coding performance and agentic tool usage
- Stronger reasoning capabilities
- 131k context window, up to 40k max output tokens
- Top open-source model on Artificial Analysis Intelligence Index
"""

import logging
from typing import Dict, List, Generator

# Configure logging
logger = logging.getLogger(__name__)

# Model id from Cerebras: zai-glm-4.7
# Reference: https://inference-docs.cerebras.ai/resources/glm-47-migration
MODEL_NAME = "zai-glm-4.7"
AGENT_NAME = "ZaiGlmAgent"
AGENT_DESCRIPTION = "AI assistant powered by Z.AI GLM 4.7 via Cerebras with enhanced coding and reasoning"

from icpy.agent.core.llm.cerebras_client import CerebrasClientAdapter
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
    "icpy.agent.core.llm.cerebras_client",
    "icpy.agent.core.runtime.general_agent",
    "icpy.agent.core.runtime.message_utils",
])


def chat(message: str, history: List[Dict[str, str]]) -> Generator[str, None, None]:
    """
    Main chat function for ZaiGlmAgent with tool support.

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

        # Delegate to generalized agent using Cerebras adapter
        adapter = CerebrasClientAdapter()
        ga = GeneralAgent(adapter, model=MODEL_NAME)
        logger.info("ZaiGlmAgent: Starting chat with tools using GeneralAgent")
        # Load tool definitions and pass through
        tools = []
        try:
            tools = ToolDefinitionLoader().get_openai_tools()
        except Exception:
            pass
        yield from ga.run(system_prompt=system_prompt, messages=safe_messages, tools=tools)
        logger.info("ZaiGlmAgent: Chat completed successfully")

    except Exception as e:
        logger.error(f"Error in ZaiGlmAgent streaming: {e}")
        yield f"🚫 Error processing request: {str(e)}\n\nPlease check your CEREBRAS_API_KEY configuration."


if __name__ == "__main__":
    for chunk in chat("Briefly introduce yourself.", []):
        print(chunk, end="")
    print()
