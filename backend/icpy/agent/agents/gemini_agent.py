"""
GeminiAgent - Generic agent powered by Google's Gemini with tool support.

Uses the native Google GenAI SDK for proper thought signature handling in Gemini 3.
The native SDK automatically handles thought signatures, which are required for
multi-turn tool calling conversations with Gemini 3 models.
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
    get_model_name_for_agent,
)
from icpy.agent.core.llm.gemini_native_client import GeminiNativeClientAdapter
from icpy.agent.core.runtime.message_utils import build_safe_messages


logger = logging.getLogger(__name__)

AGENT_NAME = "GeminiAgent"
AGENT_DESCRIPTION = "Generic AI assistant powered by Google Gemini 3 Pro with tool calling"
# Available models (December 2025):
# gemini-3-pro-preview - Latest flagship with advanced reasoning
# gemini-2.5-flash - Fast and intelligent
# gemini-2.5-pro - State-of-the-art thinking model
MODEL_NAME = "gemini-3-pro-preview"

# Gemini 3: Feature flags for thought signature support
# Default ON - thought signatures are critical for Gemini 3 multi-step reasoning
# See: https://ai.google.dev/gemini-api/docs/thought-signatures
GEMINI_THOUGHT_SIGNATURES = os.getenv('GEMINI_THOUGHT_SIGNATURES', 'on').lower() not in ('off', 'false', '0')
# Note: thinking_budget is deprecated in Gemini 3, use thinking_level instead
GEMINI_THINKING_LEVEL = os.getenv('GEMINI_THINKING_LEVEL', 'high')  # low, medium(unsupported), high
GEMINI_INCLUDE_THOUGHT_SUMMARIES = os.getenv('GEMINI_INCLUDE_THOUGHT_SUMMARIES', 'false').lower() in ('true', '1')

# Gemini 3: Optimized system prompt for Gemini 3's reasoning capabilities
# Gemini 3 responds best to direct, clear instructions (no verbose chain-of-thought prompting)
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
    version="1.1.0",
    author="Icotes",
    model=MODEL_NAME,
)

reload_env = create_environment_reload_function([
    "icpy.agent.helpers",
    "icpy.agent.core.llm.gemini_native_client",
    "icpy.agent.core.runtime.message_utils",
])


def chat(message: str, history: List[Dict[str, Any]]) -> Generator[str, None, None]:
    """Main chat function for GeminiAgent with native SDK tool support."""
    try:
        tools_summary = get_available_tools_summary()
        base_system_prompt = BASE_SYSTEM_PROMPT_TEMPLATE.format(AGENT_NAME=AGENT_NAME, TOOLS_SUMMARY=tools_summary)
        
        # Gemini 3: Add context prompt for better multi-step task handling
        if GEMINI_THOUGHT_SIGNATURES:
            base_system_prompt += f"\n\n{GEMINI_CONTEXT_PROMPT}"
            logger.info("[GEMINI-3] Added context tracking prompt (thought signatures enabled)")
        
        system_prompt = add_context_to_agent_prompt(base_system_prompt)

        safe_messages = build_safe_messages(message, history)

        # Get model name from config or use fallback
        model = get_model_name_for_agent(AGENT_NAME, MODEL_NAME)

        # Use native Gemini SDK client for proper thought signature handling
        adapter = GeminiNativeClientAdapter()
        
        logger.info(
            f"GeminiAgent: Starting chat with model={model} using native SDK | "
            f"thought_signatures={GEMINI_THOUGHT_SIGNATURES} | "
            f"thinking_level={GEMINI_THINKING_LEVEL}"
        )
        
        # Load tool definitions
        tools = []
        try:
            tools = ToolDefinitionLoader().get_openai_tools()
            logger.info(f"GeminiAgent: Loaded {len(tools)} tools")
        except Exception as e:
            logger.warning(f"GeminiAgent: Failed to load tools: {e}")
        
        # Build the messages list with system prompt
        messages = [{"role": "system", "content": system_prompt}] + safe_messages
        
        # Stream directly from the native adapter
        yield from adapter.stream_chat(
            model=model,
            messages=messages,
            tools=tools
        )
        
        logger.info("GeminiAgent: Chat completed successfully")
    except Exception as e:
        logger.error(f"Error in GeminiAgent streaming: {e}", exc_info=True)
        yield (
            "🚫 Error processing request: "
            + str(e)
            + "\n\nPlease check your Google API key configuration (GOOGLE_API_KEY)."
        )


if __name__ == "__main__":
    for chunk in chat("Hello from Gemini", []):
        print(chunk, end="")
    print()
