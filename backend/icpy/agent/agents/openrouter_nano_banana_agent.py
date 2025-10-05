"""
OpenRouter Nano Banana Agent - Image Generation AI Agent

This agent uses Google's Gemini 2.5 Flash Image Preview ("Nano Banana") model
via OpenRouter for direct image generation from text descriptions.

The model natively generates images as part of its response - no separate
image generation API needed!

Capabilities:
1. Text-to-image generation using Gemini's native capabilities
2. Understanding complex image descriptions
3. Multi-turn conversations about images
4. Image generation with contextual understanding
5. Generates images directly in base64 format

Model: google/gemini-2.5-flash-image-preview (Nano Banana) via OpenRouter
Pricing: $0.30/M input, $2.50/M output, $0.03/K output imgs
"""

import json
import os
import logging
import base64
import re
from typing import Dict, Any, List

# Configure logging
logger = logging.getLogger(__name__)

# Model configuration - using Gemini for native image generation
AGENT_MODEL_ID = "google/gemini-2.5-flash-image-preview"

# Import required modules and backend helpers
try:
    import sys
    backend_path = os.environ.get("ICOTES_BACKEND_PATH")
    if not backend_path:
        # Find the icotes root directory (should contain backend/ directory)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        while current_dir and current_dir != '/':
            backend_candidate = os.path.join(current_dir, 'backend')
            if os.path.isdir(backend_candidate) and os.path.isdir(os.path.join(backend_candidate, 'icpy')):
                backend_path = backend_candidate
                break
            current_dir = os.path.dirname(current_dir)
        
        if not backend_path:
            # Fallback to relative path from workspace/.icotes/plugins/
            backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend"))
    
    sys.path.append(backend_path)

    # Import OpenRouter client and streaming handler + shared helpers
    from icpy.agent.clients import get_openrouter_client
    from icpy.agent.helpers import (
        create_standard_agent_metadata,
        create_environment_reload_function,
        get_available_tools_summary,
        ToolDefinitionLoader,
        OpenAIStreamingHandler,
        add_context_to_agent_prompt,
    )

    DEPENDENCIES_AVAILABLE = True
    logger.info("All dependencies available for OpenRouterNanoBananaAgent")

    # Agent metadata using helper
    AGENT_METADATA = create_standard_agent_metadata(
        name="OpenRouterNanoBananaAgent",
        description="AI image generation agent powered by Google's Gemini 2.5 Flash Image Preview (Nano Banana) via OpenRouter",
        version="1.0.0",
        author="ICOTES",
        model=AGENT_MODEL_ID,
    )

    # Individual metadata fields for backward compatibility
    MODEL_NAME = AGENT_METADATA["MODEL_NAME"]
    AGENT_NAME = AGENT_METADATA["AGENT_NAME"]
    AGENT_DESCRIPTION = AGENT_METADATA["AGENT_DESCRIPTION"]
    AGENT_VERSION = AGENT_METADATA["AGENT_VERSION"]
    AGENT_AUTHOR = AGENT_METADATA["AGENT_AUTHOR"]

    # Create standardized reload function using helper
    reload_env = create_environment_reload_function([
        "icpy.agent.helpers",
        "icpy.agent.clients",
    ])

except ImportError as e:
    logger.warning(f"Dependencies not available for OpenRouterNanoBananaAgent: {e}")
    DEPENDENCIES_AVAILABLE = False

    # Fallback metadata if helpers are not available
    MODEL_NAME = AGENT_MODEL_ID
    AGENT_NAME = "OpenRouterNanoBananaAgent"
    AGENT_DESCRIPTION = "AI image generation agent powered by Google's Gemini 2.5 Flash Image Preview (Nano Banana) via OpenRouter"
    AGENT_VERSION = "1.0.0"
    AGENT_AUTHOR = "ICOTES"

    # Fallback reload function
    def reload_env():
        global DEPENDENCIES_AVAILABLE
        DEPENDENCIES_AVAILABLE = False
        logger.info("Dependencies still not available after reload")
        return False

    # Fallback metadata object with standard keys
    AGENT_METADATA = {
        "AGENT_NAME": AGENT_NAME,
        "AGENT_DESCRIPTION": AGENT_DESCRIPTION,
        "AGENT_VERSION": AGENT_VERSION,
        "AGENT_AUTHOR": AGENT_AUTHOR,
        "MODEL_NAME": MODEL_NAME,
        "AGENT_MODEL_ID": AGENT_MODEL_ID,
        "status": "error",
        "error": f"Dependencies not available: {e}",
    }


def get_tools():
    """
    Get available tools for OpenRouterNanoBananaAgent.
    
    Note: Gemini 2.5 Flash Image Preview does NOT support tool calling.
    It generates images directly as part of its response content.
    
    We return an empty tools list for now. Future versions may include
    file operations or other non-generation tools if needed.
    """
    tools = []
    
    logger.info(f"OpenRouterNanoBananaAgent: No tools needed - Gemini generates images natively")
    return tools


def extract_image_from_response(response):
    """Robustly extract a data:image/... base64 URI from an OpenRouter Gemini response.

    Tries several known response shapes:
      - message.images: list of dicts/objects containing image_url/url OR image_data/data
      - message.content: list of parts (dicts) that may embed image data
    Writes a diagnostic dump if extraction fails (once per response) to aid debugging.
    """
    try:
        if not hasattr(response, 'choices') or not response.choices:
            logger.warning("extract_image_from_response: response has no choices")
            return None

        message = response.choices[0].message

        def _extract_from_obj(obj):
            try:
                if isinstance(obj, dict):
                    # image_url variant
                    if 'image_url' in obj:
                        iu = obj['image_url']
                        if isinstance(iu, dict) and 'url' in iu and isinstance(iu['url'], str) and iu['url'].startswith('data:image/'):
                            return iu['url']
                        if isinstance(iu, str) and iu.startswith('data:image/'):
                            return iu
                    # image_data variant
                    if 'image_data' in obj:
                        id_ = obj['image_data']
                        if isinstance(id_, dict) and 'data' in id_ and isinstance(id_['data'], str) and id_['data'].startswith('data:image/'):
                            return id_['data']
                        if isinstance(id_, str) and id_.startswith('data:image/'):
                            return id_
                    # direct data key
                    data_val = obj.get('data') if hasattr(obj, 'get') else None
                    if isinstance(data_val, str) and data_val.startswith('data:image/'):
                        return data_val
                elif isinstance(obj, str) and obj.startswith('data:image/'):
                    return obj
                elif hasattr(obj, 'data') and isinstance(obj.data, str) and obj.data.startswith('data:image/'):
                    return obj.data
            except Exception as _e:  # noqa: BLE001
                logger.debug(f"_extract_from_obj error: {_e}")
            return None

        # Path 1: message.images list
        if hasattr(message, 'images') and isinstance(getattr(message, 'images'), list) and message.images:
            candidate = _extract_from_obj(message.images[0])
            if candidate:
                return candidate
            for extra in message.images[1:5]:  # limit attempts
                candidate = _extract_from_obj(extra)
                if candidate:
                    return candidate

        # Path 2: message.content list of parts (dicts)
        content = getattr(message, 'content', None)
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    candidate = _extract_from_obj(part)
                    if candidate:
                        logger.info("extract_image_from_response: extracted from message.content part")
                        return candidate

        # If we reach here, dump diagnostics once
        try:
            dump = message.model_dump() if hasattr(message, 'model_dump') else {}
            workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            diag_path = os.path.join(workspace_dir, "nano_banana_last_response.json")
            import json as _json
            with open(diag_path, 'w') as f:
                try:
                    _json.dump(dump, f, indent=2)
                except Exception:
                    f.write(str(dump)[:5000])
            logger.warning(f"extract_image_from_response: failed to find image. Wrote diagnostics to {diag_path}")
        except Exception as diag_err:  # noqa: BLE001
            logger.debug(f"extract_image_from_response: failed writing diagnostic dump: {diag_err}")
        return None
    except Exception as e:  # noqa: BLE001
        logger.error(f"extract_image_from_response: unexpected error: {e}")
        return None


def chat(message, history):
    """Chat entrypoint for the OpenRouter Nano Banana (Gemini image) agent.

    Strategy:
      1. Sanitize prior history to strip large base64 payloads
      2. Prepend a system prompt to the first user turn
      3. Make a NON-streaming completion so image data appears in message.images
      4. Extract & save image (if any) then emit a tool-style block the UI already parses
    """
    if not DEPENDENCIES_AVAILABLE:
        yield "🚫 Dependencies not available for OpenRouterNanoBananaAgent. Please check your OpenRouter configuration."
        return

    base_system_prompt = """You are Nano Banana 🍌, an advanced AI image generation assistant powered by Google's Gemini 2.5 Flash Image Preview model (via OpenRouter).

You can generate high-quality images directly. When the user asks for (or implies) an image, respond with the image plus concise accompanying text if helpful. Avoid re-sending huge base64 image data back in later turns."""

    system_prompt = add_context_to_agent_prompt(base_system_prompt)

    try:
        client = get_openrouter_client()

        # Normalize history
        if isinstance(history, str):
            try:
                history = json.loads(history) or []
            except json.JSONDecodeError:
                logger.warning("OpenRouterNanoBananaAgent: history JSON decode failed; using empty list")
                history = []
        if not isinstance(history, list):
            history = []

        def _sanitize_content(content: str) -> str:
            if not isinstance(content, str) or not content:
                return content
            original_len = len(content)
            content = re.sub(
                r"data:image/([a-zA-Z0-9.+-]+);base64,[A-Za-z0-9+/=\n\r]+",
                r"data:image/\1;base64,[OMITTED]",
                content,
            )
            def _image_data_repl(m):
                b64 = m.group(2)
                if len(b64) <= 2048:
                    return m.group(0)
                return f'"imageData": "[OMITTED_{len(b64)}chars]"'
            content = re.sub(r'("imageData"\s*:\s*")([A-Za-z0-9+/=\n\r]+)(")', lambda m: _image_data_repl(m), content)
            MAX_LEN = 150_000
            if len(content) > MAX_LEN:
                head = content[:50_000]
                tail = content[-50_000:]
                content = head + f"\n...[OMITTED_{len(content)-100_000}_CHARS]...\n" + tail
            if len(content) != original_len:
                logger.debug(f"OpenRouterNanoBananaAgent: Sanitized msg from {original_len} to {len(content)}")
            return content

        sanitized_history: List[Dict[str, Any]] = []
        for h in history:
            if isinstance(h, dict) and 'role' in h and 'content' in h:
                sanitized_history.append({
                    'role': h['role'],
                    'content': _sanitize_content(h.get('content', ''))
                })

        if not sanitized_history:  # first turn
            enhanced_user = f"{system_prompt}\n\nUser request: {message}"
        else:
            enhanced_user = message

        messages_for_model = [*sanitized_history, {"role": "user", "content": enhanced_user}]

        logger.info("OpenRouterNanoBananaAgent: Starting chat with image-capable model (non-stream)")
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages_for_model,
            stream=False,
        )
        logger.info(f"OpenRouterNanoBananaAgent: Received {len(getattr(response, 'choices', []))} choices")

        if not getattr(response, 'choices', None):
            yield "🚫 No response from model"
            return

        msg_obj = response.choices[0].message
        text_content = getattr(msg_obj, 'content', '') or ''
        if text_content:
            yield text_content
            logger.info(f"OpenRouterNanoBananaAgent: Yielded text ({len(text_content)} chars)")

        image_data_uri = extract_image_from_response(response)
        if image_data_uri:
            logger.info(f"OpenRouterNanoBananaAgent: Extracted image data ({len(image_data_uri)} chars)")
            saved_file_path = None
            try:
                if image_data_uri.startswith('data:image/') and ',' in image_data_uri:
                    b64_part = image_data_uri.split(',', 1)[1]
                    image_bytes = base64.b64decode(b64_part)
                    import time
                    ts = int(time.time())
                    safe = re.sub(r'[^\w\s-]', '', message[:30]).strip().replace(' ', '_') or 'image'
                    filename = f"openrouter_nano_banana_{safe}_{ts}.png"
                    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                    filepath = os.path.join(workspace_dir, filename)
                    with open(filepath, 'wb') as f:
                        f.write(image_bytes)
                    saved_file_path = filename
                    logger.info(f"OpenRouterNanoBananaAgent: Saved image {filename} ({len(image_bytes)} bytes)")
                else:
                    logger.warning("OpenRouterNanoBananaAgent: Image data URI unexpected format; skipping save")
            except Exception as save_err:  # noqa: BLE001
                logger.error(f"OpenRouterNanoBananaAgent: Failed saving image: {save_err}")

            raw_b64 = image_data_uri.split(',', 1)[1] if ',' in image_data_uri else image_data_uri
            tool_call_output = {
                "success": True,
                "imageData": raw_b64,
                "mimeType": "image/png",
                # Include the original (sanitized) prompt so the widget can show it even if not in input section
                "prompt": message[:200],
                "filePath": saved_file_path,
                "note": "imageData will be truncated from future context to control size"
            }
            yield "\n\n🔧 **Executing tools...**\n\n"
            yield f"📋 **generate_image**: {json.dumps({'prompt': message[:200]})}\n"
            yield f"✅ **Success**: {json.dumps(tool_call_output)}\n"
            yield "\n🔧 **Tool execution complete. Continuing...**\n\n"
            logger.info("OpenRouterNanoBananaAgent: Emitted image tool block")
        else:
            logger.info("OpenRouterNanoBananaAgent: No images found in response")

        logger.info("OpenRouterNanoBananaAgent: Chat completed")
    except Exception as e:  # noqa: BLE001
        logger.error(f"OpenRouterNanoBananaAgent: Error in chat: {e}")
        import traceback
        traceback.print_exc()
        yield f"🚫 Error processing request: {e}\n\nPlease check your OpenRouter API key configuration."


if __name__ == "__main__":
    # Simple local test harness
    print("Testing OpenRouterNanoBananaAgent wiring...")
    print(f"Agent: {AGENT_NAME}")
    print(f"Model: {MODEL_NAME}")
    print(f"Description: {AGENT_DESCRIPTION}")
    print("Tools available:", len(get_tools()))
    print("Test completed! (Use the UI to chat and generate images)")
