"""
Imagen Tool - Image Generation using Google's Gemini 2.5 Flash Image Preview

This tool allows any agent to generate images using Google's native Gemini model
that generates images directly in its response.

Requires: GOOGLE_API_KEY environment variable
"""
from __future__ import annotations

import os
import base64
import re
import logging
from typing import Any, Dict, Optional, Tuple
from datetime import datetime

from .base_tool import BaseTool, ToolResult

# Import native Google SDK for image generation
import google.generativeai as genai

logger = logging.getLogger(__name__)


class ImagenTool(BaseTool):
    """Generate or edit images using Google's Gemini image-capable models.

    Capabilities:
        - Text-to-image generation (primary model: gemini-2.5-flash-image-preview)
        - Image editing: provide an input image (data URI or base64) + prompt
        - Automatic fallback to stable models if preview model returns mime type error
    """

    def __init__(self):
        super().__init__()
        self.name = "generate_image"
        self.description = (
            "Generate or edit images using Google's Gemini models. "
            "If image_data is supplied the prompt is treated as edit instructions. "
            "IMPORTANT: When editing images, use the file:// path from previous generation results (e.g., imageUrl field). "
            "The tool automatically loads the file."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed description of the image to generate"
                },
                "image_data": {
                    "type": "string",
                    "description": "Optional source image for editing. Can be: base64, data URI, or file:// path (from previous generation)"
                },
                "image_mime_type": {
                    "type": "string",
                    "description": "Optional mime type of provided image (inferred from data URI if omitted)"
                },
                "mode": {
                    "type": "string",
                    "enum": ["auto", "generate", "edit"],
                    "description": "Force 'generate' or 'edit'; default 'auto' infers from presence of image_data"
                },
                "save_to_workspace": {
                    "type": "boolean",
                    "description": "Whether to save the generated image to workspace (default: true)"
                }
            },
            "required": ["prompt"]
        }
        # Primary preview model & fallbacks
        self._primary_model = "gemini-2.5-flash-image-preview"
        self._fallback_models = [
            "gemini-2.5-flash",
            "gemini-2.0-flash-exp",
            "gemini-1.5-flash"
        ]
        self._model = self._primary_model
        
        # Configure native Google SDK
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        genai.configure(api_key=api_key)
        
        logger.info(f"ImagenTool initialized with native Google SDK, model: {self._model}")

    def _extract_image_from_native_response(self, response) -> Tuple[Optional[bytes], Optional[str]]:
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

    def _save_image_to_workspace(self, data_uri: str, prompt: str) -> Optional[str]:
        """
        Save image data URI to workspace folder.
        
        Returns the relative file path if successful, None otherwise.
        """
        try:
            if not data_uri.startswith('data:image/'):
                logger.error("Invalid data URI format")
                return None
                
            # Extract base64 data after the comma
            base64_data = data_uri.split(',', 1)[1] if ',' in data_uri else data_uri
            
            # Decode base64 to binary
            image_bytes = base64.b64decode(base64_data)
            
            # Generate filename with timestamp
            timestamp = int(datetime.now().timestamp())
            # Sanitize prompt for filename (max 30 chars)
            safe_prompt = re.sub(r'[^\w\s-]', '', prompt[:30]).strip().replace(' ', '_')
            filename = f"generated_image_{safe_prompt}_{timestamp}.png"
            
            # Save to workspace folder (assuming we're in backend/icpy/agent/tools/)
            # Navigate up to icotes root, then to workspace
            current_file = os.path.abspath(__file__)
            # Go up: tools -> agent -> icpy -> backend -> icotes root
            icotes_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))
            workspace_dir = os.path.join(icotes_root, "workspace")
            
            if not os.path.exists(workspace_dir):
                os.makedirs(workspace_dir, exist_ok=True)
            
            filepath = os.path.join(workspace_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            logger.info(f"Saved image to {filepath} ({len(image_bytes)} bytes)")
            
            # Return relative path for display
            return filename
            
        except Exception as e:
            logger.error(f"Error saving image to workspace: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _decode_image_input(self, image_data: str, explicit_mime: Optional[str]) -> Optional[Dict[str, Any]]:
        """Decode image input (data URI, raw base64, or file:// path) into dict expected by Gemini SDK.
        Returns None on failure."""
        logger.info(f"_decode_image_input called: data length={len(image_data) if image_data else 0}")
        if not image_data:
            logger.warning("_decode_image_input: image_data is empty/None")
            return None
        try:
            mime_type = explicit_mime or "image/png"
            image_bytes = None
            
            # Handle file:// paths (from Phase 1 storage optimization)
            if image_data.startswith("file://"):
                logger.info(f"_decode_image_input: Detected file:// path")
                file_path = image_data.replace("file://", "")
                logger.info(f"_decode_image_input: Resolved to {file_path}")
                if not os.path.exists(file_path):
                    logger.error(f"File does not exist: {file_path}")
                    return None
                    
                with open(file_path, 'rb') as f:
                    image_bytes = f.read()
                    
                # Infer mime type from file extension
                ext = os.path.splitext(file_path)[1].lower()
                mime_map = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.webp': 'image/webp',
                    '.gif': 'image/gif'
                }
                mime_type = mime_map.get(ext, mime_type)
                logger.info(f"Loaded image from file: {file_path} ({len(image_bytes)} bytes, {mime_type})")
                
            # Handle data URI
            elif image_data.startswith("data:image/"):
                header, b64 = image_data.split(',', 1) if ',' in image_data else (image_data, '')
                mt = re.match(r"data:([^;]+);base64", header)
                if mt:
                    mime_type = mt.group(1)
                raw_b64 = re.sub(r"\s+", "", b64)
                image_bytes = base64.b64decode(raw_b64)
                
            # Handle raw base64
            else:
                raw_b64 = re.sub(r"\s+", "", image_data)
                image_bytes = base64.b64decode(raw_b64)
                
            if not image_bytes:
                return None
            return {"mime_type": mime_type, "data": image_bytes}
        except Exception as e:
            logger.error(f"Failed to decode input image: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _build_content(self, prompt: str, image_part: Optional[Dict[str, Any]]) -> Any:
        if image_part:
            instruction = (
                f"Edit the provided image according to these instructions: {prompt}. "
                "Preserve original style and quality unless requested otherwise."
            )
            return [image_part, instruction]
        return f"Generate an image: {prompt}"

    def _attempt(self, content: Any, model_name: str):
        try:
            model = genai.GenerativeModel(model_name)
            return model.generate_content(content), None
        except Exception as e:
            return None, str(e)

    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute image generation using native Google SDK.
        
        Args:
            prompt: Text description of image to generate
            save_to_workspace: Whether to save image to workspace (default: True)
            
        Returns:
            ToolResult with image data
        """
        logger.info(f"=== ImagenTool.execute START ===")
        logger.info(f"  kwargs keys: {list(kwargs.keys())}")
        logger.info(f"  image_data present: {bool(kwargs.get('image_data'))}")
        if kwargs.get('image_data'):
            img_data = kwargs['image_data']
            preview = img_data[:100] if len(img_data) > 100 else img_data
            logger.info(f"  image_data preview: {preview}")
        logger.info(f"  mode: {kwargs.get('mode', 'NOT SET')}")
        logger.info(f"  prompt length: {len(kwargs.get('prompt', ''))}")
        
        try:
            prompt = kwargs.get("prompt")
            if not prompt or not str(prompt).strip():
                return ToolResult(
                    success=False,
                    error="prompt is required and cannot be empty"
                )
            
            save_to_workspace = kwargs.get("save_to_workspace", True)
            input_image_data = kwargs.get("image_data")
            input_image_mime = kwargs.get("image_mime_type")
            mode = kwargs.get("mode", "auto")

            image_part = None
            if (mode in ("auto", "edit")) and input_image_data:
                logger.info(f"ImagenTool: Attempting to decode image_data (mode={mode}, length={len(input_image_data)})")
                image_part = self._decode_image_input(input_image_data, input_image_mime)
                logger.info(f"ImagenTool: Decode result: image_part is {'None' if image_part is None else 'valid'}")
                if image_part is None and mode == "edit":
                    return ToolResult(success=False, error="Failed to decode provided image for editing")

            effective_mode = "edit" if image_part else "generate"
            logger.info(f"ImagenTool mode={effective_mode} prompt_len={len(prompt)} model={self._primary_model}")
            content = self._build_content(prompt, image_part)

            attempted = []
            response, err = self._attempt(content, self._primary_model)
            attempted.append({"model": self._primary_model, "error": err})
            mime_err_sig = "Unhandled generated data mime type"
            if err and mime_err_sig in err:
                logger.warning(f"Mime type error on primary model, trying fallbacks: {err}")
                for fb in self._fallback_models:
                    r, e = self._attempt(content, fb)
                    attempted.append({"model": fb, "error": e})
                    if r and not e:
                        response = r
                        self._model = fb
                        logger.info(f"Fallback model succeeded: {fb}")
                        break
            else:
                self._model = self._primary_model

            if response is None:
                return ToolResult(success=False, error=f"Image generation API call failed: {err}", data={"attemptedModels": attempted})
            
            # Extract image data from native response
            image_bytes, mime_type = self._extract_image_from_native_response(response)
            
            if not image_bytes:
                # Check if there's text content explaining why no image
                text_content = ""
                try:
                    if hasattr(response, 'text') and response.text:
                        text_content = response.text
                except:
                    pass
                
                return ToolResult(
                    success=False,
                    error=f"No image generated. Model response: {text_content[:200]}"
                )
            
            logger.info(f"Successfully extracted image data ({len(image_bytes)} bytes, {mime_type})")
            
            # Convert binary image to base64 data URI
            image_data_uri = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
            
            # Optionally save to workspace
            saved_path = None
            if save_to_workspace:
                saved_path = self._save_image_to_workspace(image_data_uri, str(prompt))
            
            # Extract raw base64 (without data URI prefix) for response
            raw_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Return successful result with image data
            result_data = {
                "imageData": raw_base64,  # Raw base64 for UI
                "imageUrl": image_data_uri,  # Full data URI if needed
                "mimeType": mime_type,
                "prompt": str(prompt),
                "model": self._model,
                "timestamp": datetime.now().isoformat(),
                "mode": effective_mode,
                "attemptedModels": attempted
            }
            if image_part:
                result_data["sourceImageProvided"] = True
            
            if saved_path:
                result_data["filePath"] = saved_path
                result_data["message"] = f"Image generated successfully and saved to workspace/{saved_path}"
            else:
                result_data["message"] = "Image generated successfully"
            
            return ToolResult(success=True, data=result_data)
            
        except Exception as e:
            logger.error(f"Unexpected error in ImagenTool: {e}")
            import traceback
            traceback.print_exc()
            return ToolResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
