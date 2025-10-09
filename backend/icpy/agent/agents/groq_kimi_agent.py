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
            ToolDefinitionLoader,  # For minimal tool name list
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

    # Build system prompt with essential tool usage instructions
    # Keep it compact for Groq's token limits but include critical guidance for proper tool usage
    system_prompt = (
        f"You are {AGENT_NAME}, a helpful AI assistant with access to tools for generating/editing images, "
        "reading files, searching, and executing code.\n\n"
        "CRITICAL - Image Handling:\n"
        "- User messages may include [Attached images: ...] sections listing file paths to images they've shared.\n"
        "- When user asks to modify/edit/change an attached image (e.g., 'add a hat', 'make it 3D'), "
        "use generate_image tool with image_data parameter set to the file path from the attachment.\n"
        "- Set mode='edit' when modifying existing images, mode='generate' for new images.\n"
        "- Look for imageUrl fields in previous assistant responses for file:// paths from prior generations.\n\n"
        "Keep responses clear and concise."
    )

    try:
        client = get_groq_client()

        # Normalize history (handles JSON string input and content flattening)
        normalized_history = normalize_history(history)
        
        # Aggressively trim history. Keep only last 3 user/assistant exchange pairs (≈6 msgs)
        if len(normalized_history) > 6:
            logger.info(
                f"GroqKimiAgent: Trimming history from {len(normalized_history)} to 6 messages for Groq compact mode"
            )
            normalized_history = normalized_history[-6:]

        # Base conversation messages
        system_message = {"role": "system", "content": system_prompt}
        messages: List[Dict[str, Any]] = [system_message] + normalized_history

        # Append current user message only if non-empty
        if isinstance(message, str) and message.strip():
            messages.append({"role": "user", "content": message})
        else:
            logger.info("GroqKimiAgent: Skipping trailing user message because it's empty (provided by caller as \"\")")

        # Convert multimodal content to plain text (Groq API requirement)
        def _is_rich_parts(val: Any) -> bool:
            return isinstance(val, list) and any(
                isinstance(p, dict) and p.get("type") in ("text", "image_url") for p in val
            )

        def _extract_text_from_rich(parts: List[Dict[str, Any]]) -> str:
            """Extract text and file paths from rich content array for Groq."""
            text_parts = []
            image_paths = []
            
            for part in parts:
                if not isinstance(part, dict):
                    continue
                    
                ptype = part.get("type")
                if ptype == "text":
                    text = part.get("text", "")
                    if text:
                        text_parts.append(text)
                elif ptype == "image_url":
                    # Extract file path from image_url for tool usage
                    img = part.get("image_url")
                    if isinstance(img, dict):
                        url = img.get("url", "")
                    elif isinstance(img, str):
                        url = img
                    else:
                        url = ""
                    
                    # Extract actual file path from data URL or file:// URL
                    if url.startswith("data:"):
                        # Data URL - can't extract path, just note it
                        image_paths.append("[embedded image data]")
                    elif url.startswith("file://"):
                        # File URL - extract path
                        file_path = url[7:]  # Remove "file://" prefix
                        image_paths.append(file_path)
                    elif url.startswith("/"):
                        # Absolute or API path
                        image_paths.append(url)
            
            # Build final text with image context
            result = " ".join(text_parts)
            if image_paths:
                paths_str = "\n".join([f"- {p}" for p in image_paths])
                result += f"\n\n[Attached images:\n{paths_str}\n]"
            
            return result.strip()

        safe_messages: List[Dict[str, Any]] = []
        dropped = 0
        for i, m in enumerate(messages):
            c = m.get("content", "")
            role = m.get("role")
            
            # Convert rich content to plain text (Groq requirement)
            if role == "user" and _is_rich_parts(c):
                text_content = _extract_text_from_rich(c)
                if not text_content:
                    dropped += 1
                    logger.warning(f"GroqKimiAgent: Removing empty rich user message at position {i}")
                    continue
                safe_messages.append({**m, "content": text_content})
                continue
            
            # For other cases, coerce to string (system/assistant/tool) or plain user text
            if not isinstance(c, str):
                m = {**m, "content": flatten_message_content(c)}
            # Drop empty user strings
            if role == "user" and (not m["content"] or not str(m["content"]).strip()):
                dropped += 1
                logger.warning(f"GroqKimiAgent: Removing empty user message at position {i}")
                continue
            safe_messages.append(m)
        if dropped:
            logger.info(f"GroqKimiAgent: Dropped {dropped} empty user message(s) before request")

        # Log message count for debugging
        logger.debug(f"GroqKimiAgent: Prepared {len(safe_messages)} messages for Groq API")

        # Use compact tools mode to save tokens while preserving full functionality
        handler = OpenAIStreamingHandler(client, MODEL_NAME, use_compact_tools=True)
        yield from handler.stream_chat_with_tools(safe_messages, max_tokens=None, auto_continue=False)

    except Exception as e:
        logger.error(f"Error in GroqKimiAgent streaming: {e}")
        yield f"🚫 Error processing request: {str(e)}\n\nPlease check your GROQ_API_KEY configuration."


if __name__ == "__main__":
    # Simple smoke test (non-streaming display)
    for chunk in chat("Hello, what can you help me with?", []):
        print(chunk, end="")
    print()
