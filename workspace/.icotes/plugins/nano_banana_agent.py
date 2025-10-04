"""
Nano Banana Agent - Image Generation AI Agent

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

Model: google/gemini-2.5-flash-image-preview (Nano Banana)
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
    logger.info("All dependencies available for NanoBananaAgent")

    # Agent metadata using helper
    AGENT_METADATA = create_standard_agent_metadata(
        name="NanoBananaAgent",
        description="AI image generation agent powered by Google's Gemini 2.5 Flash Image Preview (Nano Banana)",
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
    logger.warning(f"Dependencies not available for NanoBananaAgent: {e}")
    DEPENDENCIES_AVAILABLE = False

    # Fallback metadata if helpers are not available
    MODEL_NAME = AGENT_MODEL_ID
    AGENT_NAME = "NanoBananaAgent"
    AGENT_DESCRIPTION = "AI image generation agent powered by Google's Gemini 2.5 Flash Image Preview (Nano Banana)"
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
    Get available tools for NanoBananaAgent.
    
    Note: Gemini 2.5 Flash Image Preview does NOT support tool calling.
    It generates images directly as part of its response content.
    
    We return an empty tools list for now. Future versions may include
    file operations or other non-generation tools if needed.
    """
    tools = []
    
    logger.info(f"NanoBananaAgent: No tools needed - Gemini generates images natively")
    return tools


def extract_image_from_response(response):
    """
    Extract base64 image data from Gemini's response.
    
    The OpenAI SDK stores Gemini images in message.images field (not content).
    The images field contains a list of image objects with base64 data.
    """
    try:
        # Get the message
        if not hasattr(response, 'choices') or not response.choices:
            logger.error("No choices in response")
            return None
            
        message = response.choices[0].message
        
        # Check if message has images field
        if not hasattr(message, 'images'):
            logger.error("Message has no images field")
            return None
            
        images = message.images
        
        # Images should be a list
        if not isinstance(images, list):
            logger.error(f"Images field is not a list: {type(images)}")
            return None
            
        # Check if we have at least one image
        if len(images) == 0:
            logger.error("Images list is empty")
            return None
            
        # Get the first image
        # The image might be a dict with different structures or might have direct data access
        first_image = images[0]
        
        # Try to extract base64 data
        if isinstance(first_image, dict):
            # Try image_url format first (actual API response)
            if 'image_url' in first_image:
                img_url_field = first_image['image_url']
                if isinstance(img_url_field, dict) and 'url' in img_url_field:
                    data = img_url_field['url']
                    if data and data.startswith('data:image/'):
                        return data
                elif isinstance(img_url_field, str) and img_url_field.startswith('data:image/'):
                    return img_url_field
            
            # Try image_data format (backward compatibility)
            if 'image_data' in first_image:
                img_data_field = first_image['image_data']
                if isinstance(img_data_field, dict) and 'data' in img_data_field:
                    data = img_data_field['data']
                    if data and data.startswith('data:image/'):
                        return data
                elif isinstance(img_data_field, str) and img_data_field.startswith('data:image/'):
                    return img_data_field
            
            # Try direct 'data' key (another fallback)
            data = first_image.get('data', '')
            if data and data.startswith('data:image/'):
                return data
                
        elif isinstance(first_image, str):
            if first_image.startswith('data:image/'):
                return first_image
        
        # If image is an object, try to access data attribute
        if hasattr(first_image, 'data'):
            data = first_image.data
            if data and data.startswith('data:image/'):
                return data
                
        logger.error(f"Could not extract base64 data from image: {type(first_image)}")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting image from response: {e}")
        return None


def chat(message, history):
    """
    Nano Banana Agent streaming chat function with native image generation.

    Uses Google's Gemini 2.5 Flash Image Preview model which generates images
    directly in the response content (no tool calling needed).

    Args:
        message: str - User message
        history: List[Dict] or str (JSON) - Conversation history

    Yields:
        str - Response chunks for streaming, including widget data for images
    """
    if not DEPENDENCIES_AVAILABLE:
        yield "🚫 Dependencies not available for NanoBananaAgent. Please check your OpenRouter configuration."
        return

    # System prompt for Gemini-native image generation
    base_system_prompt = """You are Nano Banana 🍌, an advanced AI image generation assistant powered by Google's Gemini 2.5 Flash Image Preview model.

🎨 Your Core Capability:
You can GENERATE IMAGES DIRECTLY as part of your response! When users ask for images, you create them naturally without needing any external tools.

📝 How Image Generation Works:
- When a user requests an image, simply generate it directly
- Your response will naturally contain the generated image
- You can create photorealistic, artistic, or stylized images
- You understand complex scene descriptions and compositions

💡 Best Practices:
- Listen carefully to what the user wants
- Be creative and specific in your generations
- Consider composition, lighting, colors, and style
- You can have multi-turn conversations about the images
- Ask clarifying questions if needed

Example Requests:
- "Create a sunset over mountains"
- "Draw a cute robot"
- "Generate a cyberpunk city scene"
- "Make a logo for my coffee shop"

Always be helpful, creative, and focused on creating images that match the user's vision!"""

    # Add context information to the system prompt
    system_prompt = add_context_to_agent_prompt(base_system_prompt)

    try:
        # Initialize OpenRouter client
        client = get_openrouter_client()

        # Handle JSON string history (gradio compatibility)
        if isinstance(history, str):
            try:
                history = json.loads(history) or []
            except json.JSONDecodeError:
                logger.warning("Invalid JSON for history; defaulting to empty list")
                history = []
        if not isinstance(history, list):
            logger.warning(f"Unexpected history type {type(history)}; defaulting to []")
            history = []

        # --- Sanitization Helpers -------------------------------------------------
        def _sanitize_content(content: str) -> str:
            """Remove/placeholder large embedded image data from prior assistant messages.

            We replace:
              1. data:image/...;base64,<very long base64>
              2. JSON "imageData": "<very long base64>" values

            This prevents context length explosions when prior assistant
            messages containing full image base64 are echoed back to the model.
            """
            if not content or not isinstance(content, str):
                return content

            original_len = len(content)

            # Pattern 1: data URI (keep mime, strip payload)
            content = re.sub(
                r"data:image/([a-zA-Z0-9.+-]+);base64,[A-Za-z0-9+/=\n\r]+",
                r"data:image/\1;base64,[OMITTED]",
                content,
            )

            # Pattern 2: "imageData": "...." (allow small ones < 2k chars)
            def _image_data_repl(match):
                b64 = match.group(2)
                if len(b64) <= 2048:
                    return match.group(0)  # keep small inline icons, etc.
                return f'"imageData": "[OMITTED_{len(b64)}chars]"'

            content = re.sub(
                r'("imageData"\s*:\s*")([A-Za-z0-9+/=\n\r]+)(")',
                lambda m: _image_data_repl(m),
                content,
            )

            # Extreme fallback: if message still huge (>150k chars) just truncate middle
            MAX_LEN = 150_000
            if len(content) > MAX_LEN:
                head = content[:50_000]
                tail = content[-50_000:]
                content = head + f"\n...[OMITTED_{len(content)-100_000}_CHARS]...\n" + tail

            if len(content) != original_len:
                logger.debug(
                    f"NanoBananaAgent: Sanitized message content from {original_len} to {len(content)} chars"
                )
            return content

        # Build sanitized history for model input (do NOT mutate original history object)
        sanitized_history: List[Dict[str, Any]] = []
        for h in history or []:
            if isinstance(h, dict) and 'role' in h and 'content' in h:
                sanitized_history.append({
                    'role': h['role'],
                    'content': _sanitize_content(h.get('content', ''))
                })
            else:
                # Skip malformed entries silently
                continue

        # Prepend system prompt ONLY to first user message (embed as part of content)
        if not sanitized_history:
            enhanced_message = f"{system_prompt}\n\nUser request: {message}"
        else:
            enhanced_message = message

        user_msg = {"role": "user", "content": enhanced_message}
        messages_for_model = [*sanitized_history, user_msg]

        # The original (unsanitized) history is preserved implicitly by the caller / UI; we do not echo
        # large base64 blobs back to the model now.
        messages = messages_for_model  # keep variable name expected below

        logger.info("NanoBananaAgent: Starting chat with native image generation")
        
        # Get the FULL response (NOT streaming) because Gemini images come in message.images
        # after the stream completes, not during streaming
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            stream=False,  # IMPORTANT: Must be False to get images in message.images
        )
        
        logger.info(f"NanoBananaAgent: Received response with {len(response.choices)} choices")
        
        if not response.choices:
            yield "🚫 No response from model"
            return
            
        message_obj = response.choices[0].message
        text_content = message_obj.content or ""
        
        # First, yield the text content
        if text_content:
            yield text_content
            logger.info(f"NanoBananaAgent: Yielded text content ({len(text_content)} chars)")
        
        # Check for images in message.images field (this is where Gemini puts them!)
        if hasattr(message_obj, 'images') and message_obj.images:
            logger.info(f"NanoBananaAgent: Found {len(message_obj.images)} images in message.images")
            
            # Extract image data using our helper function
            image_data_uri = extract_image_from_response(response)
            
            if image_data_uri:
                logger.info(f"NanoBananaAgent: Successfully extracted image data ({len(image_data_uri)} chars)")
                
                # Save the image to workspace folder
                saved_file_path = None
                try:
                    # Parse the data URI to get the base64 data
                    if image_data_uri.startswith('data:image/'):
                        # Extract base64 data after the comma
                        base64_data = image_data_uri.split(',', 1)[1] if ',' in image_data_uri else image_data_uri
                        
                        # Decode base64 to binary
                        image_bytes = base64.b64decode(base64_data)
                        
                        # Generate filename with timestamp
                        import time
                        timestamp = int(time.time())
                        # Sanitize prompt for filename
                        safe_prompt = re.sub(r'[^\w\s-]', '', message[:30]).strip().replace(' ', '_')
                        filename = f"nano_banana_{safe_prompt}_{timestamp}.png"
                        
                        # Save to workspace folder (parent of .icotes)
                        workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                        filepath = os.path.join(workspace_dir, filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(image_bytes)
                        
                        logger.info(f"NanoBananaAgent: Saved image to {filepath} ({len(image_bytes)} bytes)")
                        
                        # Use relative path for display
                        saved_file_path = filename
                        
                    else:
                        logger.warning(f"NanoBananaAgent: Unexpected image data format: {image_data_uri[:100]}")
                        
                except Exception as e:
                    logger.error(f"NanoBananaAgent: Error saving image to disk: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Use the standard tool call format that the frontend understands
                # This follows the same pattern as other tools (file operations, etc.)
                # Provide raw base64 (without data URI prefix) to reduce duplication.
                # Still include a data URI variant if needed later (can be reconstructed client-side).
                raw_b64 = image_data_uri.split(',', 1)[1] if ',' in image_data_uri else image_data_uri
                tool_call_output = {
                    "success": True,
                    "imageData": raw_b64,  # raw base64 ONLY
                    "mimeType": "image/png",
                    "prompt": message[:200],
                    "filePath": saved_file_path,
                    "note": "imageData truncated from history in future turns to control context size"
                }
                
                # Format as a tool execution block that the frontend parser recognizes
                yield "\n\n🔧 **Executing tools...**\n\n"
                yield f"📋 **generate_image**: {json.dumps({'prompt': message[:200]})}\n"
                yield f"✅ **Success**: {json.dumps(tool_call_output)}\n"
                yield "\n🔧 **Tool execution complete. Continuing...**\n\n"
                
                logger.info("NanoBananaAgent: Yielded image tool call")
            else:
                logger.warning("NanoBananaAgent: Could not extract image data")
        else:
            logger.info("NanoBananaAgent: No images found in response")
        
        logger.info("NanoBananaAgent: Chat completed")

    except Exception as e:
        logger.error(f"Error in NanoBananaAgent streaming: {e}")
        import traceback
        traceback.print_exc()
        yield f"🚫 Error processing request: {str(e)}\n\nPlease check your OpenRouter API key configuration."


if __name__ == "__main__":
    # Simple local test harness
    print("Testing NanoBananaAgent wiring...")
    print(f"Agent: {AGENT_NAME}")
    print(f"Model: {MODEL_NAME}")
    print(f"Description: {AGENT_DESCRIPTION}")
    print("Tools available:", len(get_tools()))
    print("Test completed! (Use the UI to chat and generate images)")
