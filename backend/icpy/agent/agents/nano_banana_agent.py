"""
Nano Banana Agent - Image Generation and Editing AI Agent

This agent uses Google's Gemini 2.5 Flash Image Preview ("Nano Banana") model
directly via Google's native API for image generation and editing.

The model natively generates and edits images as part of its response - no separate
image generation API needed!

Capabilities:
1. Text-to-image generation using Gemini's native capabilities
2. Image editing (modify existing images based on text descriptions)
3. Image understanding and analysis
4. Multi-turn conversations about images
5. Image generation with contextual understanding
6. Multimodal input support (text + images)
7. Generates images directly in base64 format

Model: gemini-2.5-flash-image-preview (Google Native API)
"""

import json
import os
import logging
import base64
import re
from typing import Dict, Any, List

# Configure logging
logger = logging.getLogger(__name__)

# Model configuration - using Google's native Gemini model
AGENT_MODEL_ID = "gemini-2.5-flash-image-preview"

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

    # Import native Google SDK for image generation
    import google.generativeai as genai
    from icpy.agent.helpers import (
        create_standard_agent_metadata,
        create_environment_reload_function,
        get_available_tools_summary,
        ToolDefinitionLoader,
        OpenAIStreamingHandler,
        add_context_to_agent_prompt,
        get_workspace_path,
    )

    DEPENDENCIES_AVAILABLE = True
    logger.info("All dependencies available for NanoBananaAgent")

    # Agent metadata using helper
    AGENT_METADATA = create_standard_agent_metadata(
        name="NanoBananaAgent",
        description="AI image generation agent powered by Google's Gemini native API",
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
    AGENT_DESCRIPTION = "AI image generation agent powered by Google's Gemini native API"
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
    
    Note: Gemini 2.0 Flash generates images directly in response.
    We return an empty tools list for this specialized agent.
    """
    tools = []
    
    logger.info(f"NanoBananaAgent: No tools needed - Gemini generates images natively")
    return tools


def extract_image_from_native_response(response):
    """
    Extract binary image data from native Google SDK response.
    
    Native SDK returns images in response.parts with inline_data containing
    binary image bytes (not base64 encoded).
    
    Returns: tuple of (image_bytes, mime_type) or (None, None)
    """
    try:
        if not hasattr(response, 'parts'):
            logger.error("Native response has no parts")
            return None, None
        
        # Iterate through parts to find image data
        for part in response.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                inline = part.inline_data
                if hasattr(inline, 'data') and inline.data:
                    mime_type = getattr(inline, 'mime_type', 'image/png')
                    logger.info(f"Found inline_data with {len(inline.data)} bytes, mime={mime_type}")
                    return inline.data, mime_type
        
        logger.warning("No inline_data found in any response parts")
        return None, None
        
    except Exception as e:
        logger.error(f"Error extracting image from native response: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def chat(message, history):
    """
    Nano Banana Agent streaming chat function with native image generation and editing.

    Uses Google's Gemini model which generates images directly in the response content
    and can also understand input images for editing tasks.

    Args:
        message: str or dict - User message (can be multimodal with images)
        history: List[Dict] or str (JSON) - Conversation history

    Yields:
        str - Response chunks for streaming, including widget data for images
    """
    if not DEPENDENCIES_AVAILABLE:
        yield "🚫 Dependencies not available for NanoBananaAgent. Please check your Google API configuration."
        return

    # System prompt for Gemini-native image generation and editing
    base_system_prompt = """You are Nano Banana 🍌, an advanced AI image generation and editing assistant powered by Google's Gemini.

🎨 Your Core Capabilities:
1. **Image Generation**: You can GENERATE IMAGES DIRECTLY as part of your response!
2. **Image Editing**: You can SEE and EDIT images provided by users!
3. **Image Understanding**: You can analyze and describe images in detail.

📝 How Image Generation Works:
- When a user requests an image, simply generate it directly
- Your response will naturally contain the generated image
- You can create photorealistic, artistic, or stylized images
- You understand complex scene descriptions and compositions

�️ How Image Editing Works:
- When a user provides an image with an edit request (e.g., "add a hat to this cat"), you can:
  1. Understand what's in the image
  2. Apply the requested modifications
  3. Generate a new version with the changes
- You maintain the style and context of the original while applying edits

�💡 Best Practices:
- Listen carefully to what the user wants
- Be creative and specific in your generations
- For edits, preserve the original style unless asked otherwise
- Consider composition, lighting, colors, and style
- You can have multi-turn conversations about the images
- Ask clarifying questions if needed

Example Requests:
- "Create a sunset over mountains"
- "Draw a cute robot"
- "Add a hat to this cat" (with image)
- "Make this photo look like a painting" (with image)
- "Change the background to a beach" (with image)

Always be helpful, creative, and focused on creating or editing images that match the user's vision!"""

    # Add context information to the system prompt
    system_prompt = add_context_to_agent_prompt(base_system_prompt)

    try:
        # Initialize native Google SDK
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            yield "🚫 GOOGLE_API_KEY not set. Please configure your Google API key."
            return
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(MODEL_NAME)
        
        logger.info(f"NanoBananaAgent: Initialized native SDK with model {MODEL_NAME}")
        
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
        
        # If message is empty, try to get the latest user message from history
        if not message or (isinstance(message, str) and not message.strip()):
            logger.info("NanoBananaAgent: Empty message received, checking history for latest user message")
            if history:
                # Get the last user message from history
                for hist_item in reversed(history):
                    if isinstance(hist_item, dict) and hist_item.get("role") == "user":
                        message = hist_item.get("content", "")
                        logger.info(f"NanoBananaAgent: Retrieved message from history: {str(message)[:100]}")
                        break
        
        # Process message - it may be multimodal (list with text and images)
        text_prompt = ""
        input_images = []
        
        if isinstance(message, list):
            # Multimodal content - extract text and images
            for item in message:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_prompt = item.get("text", "")
                    elif item.get("type") == "image_url":
                        # Extract image URL (can be data URI or regular URL)
                        img_data = item.get("image_url", {})
                        if isinstance(img_data, dict):
                            url = img_data.get("url", "")
                        else:
                            url = img_data if isinstance(img_data, str) else ""
                        
                        if url:
                            # Handle data URI (base64 encoded images)
                            if url.startswith("data:image/"):
                                try:
                                    # Extract base64 data after comma
                                    base64_data = url.split(",", 1)[1] if "," in url else url
                                    image_bytes = base64.b64decode(base64_data)
                                    
                                    # Use PIL to create image object for Gemini
                                    from PIL import Image
                                    import io
                                    pil_image = Image.open(io.BytesIO(image_bytes))
                                    input_images.append(pil_image)
                                    logger.info(f"NanoBananaAgent: Loaded image from data URI ({len(image_bytes)} bytes)")
                                except Exception as e:
                                    logger.error(f"Error decoding image data URI: {e}")
                            else:
                                # Regular URL - Gemini can handle URLs directly
                                input_images.append(url)
                                logger.info(f"NanoBananaAgent: Added image URL: {url[:50]}...")
                elif isinstance(item, str):
                    text_prompt += item
        elif isinstance(message, str):
            text_prompt = message
        else:
            text_prompt = str(message)
        
        # Validate that we have a prompt
        if not text_prompt or not text_prompt.strip():
            logger.error("NanoBananaAgent: Empty prompt received")
            yield "🚫 Error: Empty prompt. Please provide a description of the image you want to generate."
            return
        
        # Build the prompt content for Gemini
        if input_images:
            # Image editing/analysis mode
            logger.info(f"NanoBananaAgent: Processing {len(input_images)} input image(s) with prompt: {text_prompt[:100]}")
            
            # Build multimodal prompt: system context + user request + images
            full_prompt = f"""{system_prompt}

User request: {text_prompt}

Please analyze the provided image(s) and fulfill the user's request. If they want edits, generate a new image with those changes applied."""
            
            # Gemini expects content as list: [text, image, text, ...] or [image, text]
            prompt_parts = [full_prompt]
            prompt_parts.extend(input_images)
            
            response = model.generate_content(prompt_parts)
        else:
            # Text-only image generation mode
            full_prompt = f"""{system_prompt}

User request: {text_prompt}

Please create an image that exactly matches what the user described. Be precise and creative."""
            
            logger.info(f"NanoBananaAgent: Starting native image generation for: {text_prompt[:100]}")
            response = model.generate_content(full_prompt)
        
        logger.info("NanoBananaAgent: Received response from native SDK")
        
        # Extract text content first (if any)
        try:
            if hasattr(response, 'text') and response.text:
                text_content = response.text
                yield text_content + "\n\n"
                logger.info(f"NanoBananaAgent: Yielded text content ({len(text_content)} chars)")
        except Exception as text_err:
            logger.debug(f"No text content in response: {text_err}")
        
        # Extract image data from native response
        image_bytes, mime_type = extract_image_from_native_response(response)
        
        if image_bytes and len(image_bytes) > 0:
            logger.info(f"NanoBananaAgent: Successfully extracted image ({len(image_bytes)} bytes, {mime_type})")
            
            # Convert binary image to base64 data URI
            image_data_uri = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
            
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
                        # Sanitize prompt for filename (use text_prompt which is always a string)
                        prompt_for_filename = text_prompt if text_prompt else "image"
                        safe_prompt = re.sub(r'[^\w\s-]', '', prompt_for_filename[:30]).strip().replace(' ', '_')
                        if not safe_prompt:
                            safe_prompt = "image"
                        filename = f"nano_banana_{safe_prompt}_{timestamp}.png"
                        
                        # Save to workspace folder using helper function
                        workspace_dir = get_workspace_path()
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
                
                # Provide raw base64 (without data URI prefix) to reduce duplication.
                # Still include a data URI variant if needed later (can be reconstructed client-side).
                raw_b64 = image_data_uri.split(',', 1)[1] if ',' in image_data_uri else image_data_uri
                tool_call_output = {
                    "success": True,
                    "imageData": raw_b64,  # raw base64 ONLY
                    "mimeType": "image/png",
                    "prompt": text_prompt[:200],  # Use text_prompt string
                    "filePath": saved_file_path,
                    "note": "imageData truncated from history in future turns to control context size"
                }
                
                # Format as a tool execution block that the frontend parser recognizes
                # Important: emit input with prompt so widget displays it
                tool_input = {
                    "prompt": text_prompt,  # Use text_prompt string for display
                    "size": "1024x1024",
                    "style": "natural"
                }
                
                yield "\n\n🔧 **Executing tools...**\n\n"
                yield f"📋 **generate_image**: {json.dumps(tool_input)}\n"
                # Output just JSON without decoration for frontend parsing
                yield json.dumps(tool_call_output) + "\n"
                yield "\n🔧 **Tool execution complete. Continuing...**\n\n"
                
                logger.info("NanoBananaAgent: Yielded image tool call with input")
            else:
                logger.warning("NanoBananaAgent: Could not extract image data")
        else:
            logger.info("NanoBananaAgent: No images found in response")
        
        logger.info("NanoBananaAgent: Chat completed")

    except Exception as e:
        logger.error(f"Error in NanoBananaAgent: {e}")
        import traceback
        traceback.print_exc()
        yield f"🚫 Error processing request: {str(e)}\n\nPlease check your Google API key configuration and ensure google-generativeai is installed."


if __name__ == "__main__":
    # Simple local test harness
    print("Testing NanoBananaAgent wiring...")
    print(f"Agent: {AGENT_NAME}")
    print(f"Model: {MODEL_NAME}")
    print(f"Description: {AGENT_DESCRIPTION}")
    print("Tools available:", len(get_tools()))
    print("Test completed! (Use the UI to chat and generate images)")
