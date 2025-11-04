"""
GeminiAgent - Generic agent powered by Google's Gemini with tool support.

Delegates streaming to the generalized runtime using the Gemini adapter.
Shares message preparation logic with other agents to keep behavior consistent.
"""

import logging
import os
from typing import Dict, List, Generator, Any

from icpy.agent.helpers import (
    create_standard_agent_metadata,
    create_environment_reload_function,
    get_available_tools_summary,
    ToolDefinitionLoader,
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

# Phase 5: Feature flags for thought signature support
# Default ON - thought signatures solve premature task completion in Gemini 2.5
GEMINI_THOUGHT_SIGNATURES = os.getenv('GEMINI_THOUGHT_SIGNATURES', 'on').lower() not in ('off', 'false', '0')
GEMINI_USE_GOOGLE_SDK = os.getenv('GEMINI_USE_GOOGLE_SDK', 'auto').lower()
GEMINI_THINKING_BUDGET = os.getenv('GEMINI_THINKING_BUDGET')  # Optional int
GEMINI_INCLUDE_THOUGHT_SUMMARIES = os.getenv('GEMINI_INCLUDE_THOUGHT_SUMMARIES', 'false').lower() in ('true', '1')

# Phase 5: Gemini-specific system prompt addition for better statefulness
GEMINI_CONTEXT_PROMPT = """
When working on multi-step tasks:
1. At the start of each thinking phase, briefly recap your current progress and remaining steps
2. Do not conclude or say "done" until ALL requested steps are verified complete
3. If using tools multiple times, track which operations succeeded and what remains

Formatting guidelines:
- Present information in clear, natural prose using standard markdown formatting
- Use headings, lists, and emphasis naturally without adding meta-labels
- For code blocks, use standard markdown code fences with language specifiers
- Avoid redundant content-type labels (like 'text', 'code', etc.) in your responses
"""

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
        
        # Phase 5: Add Gemini-specific context prompt for better multi-step task handling
        if GEMINI_THOUGHT_SIGNATURES:
            base_system_prompt += f"\n\n{GEMINI_CONTEXT_PROMPT}"
            logger.info("[GEMINI-DEBUG] Added context tracking prompt (thought signatures enabled)")
        
        system_prompt = add_context_to_agent_prompt(base_system_prompt)

        safe_messages = build_safe_messages(message, history)

        adapter = GeminiClientAdapter()
        ga = GeneralAgent(adapter, model=MODEL_NAME)
        
        logger.info(
            f"GeminiAgent: Starting chat with tools using GeneralAgent | "
            f"thought_signatures={GEMINI_THOUGHT_SIGNATURES} | "
            f"use_sdk={GEMINI_USE_GOOGLE_SDK} | "
            f"thinking_budget={GEMINI_THINKING_BUDGET}"
        )
        
        # Load tool definitions and pass through
        tools = []
        try:
            tools = ToolDefinitionLoader().get_openai_tools()
        except Exception:
            pass
        yield from ga.run(system_prompt=system_prompt, messages=safe_messages, tools=tools)
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
