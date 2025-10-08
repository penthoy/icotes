"""
Imagen Tool - Image Generation using Google's Gemini 2.5 Flash Image Preview

This tool allows any agent to generate images using Google's native Gemini model
that generates images directly in its response.

Requires: GOOGLE_API_KEY environment variable

Phase 7 Update: Added hop support, resolution control, and custom filenames
"""
from __future__ import annotations

import os
import base64
import re
import logging
from typing import Any, Dict, Optional, Tuple
from datetime import datetime

from .base_tool import BaseTool, ToolResult
from .context_helpers import get_contextual_filesystem, get_current_context

# Import native Google SDK for image generation
import google.generativeai as genai

# Import PIL for image resizing
try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL (Pillow) not available - resolution control disabled")

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
            "Supports custom filenames, arbitrary resolutions, and hop contexts (remote servers). "
            "If image_data is supplied the prompt is treated as edit instructions. "
            "IMPORTANT: When editing images, use the file:// path from previous generation results (e.g., imageUrl field). "
            "The tool automatically loads the file from the current context (local or remote hop). "
            "Use 'width' and 'height' parameters to generate images at specific resolutions. "
            "Use 'filename' parameter to specify a custom filename (without extension)."
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
                },
                "filename": {
                    "type": "string",
                    "description": "Optional custom filename (without extension). If not provided, auto-generates from prompt and timestamp"
                },
                "width": {
                    "type": "integer",
                    "description": "Desired image width in pixels (requires Pillow). Generated image will be resized to this width maintaining aspect ratio"
                },
                "height": {
                    "type": "integer",
                    "description": "Desired image height in pixels (requires Pillow). Generated image will be resized to this height maintaining aspect ratio"
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

    async def _save_image_to_workspace(
        self, 
        image_bytes: bytes, 
        prompt: str, 
        custom_filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Save image bytes to workspace folder (hop-aware).
        
        Phase 7: Uses ContextRouter to save to current context (local or remote).
        
        Args:
            image_bytes: Binary image data
            prompt: Generation prompt (used for auto-generated filename)
            custom_filename: Optional custom filename (without extension)
            
        Returns:
            Relative file path if successful, None otherwise.
        """
        try:
            # Generate filename
            if custom_filename:
                # Sanitize custom filename
                safe_name = re.sub(r'[^\w\s-]', '', custom_filename).strip().replace(' ', '_')
                filename = f"{safe_name}.png"
            else:
                # Auto-generate from prompt and timestamp
                timestamp = int(datetime.now().timestamp())
                safe_prompt = re.sub(r'[^\w\s-]', '', prompt[:30]).strip().replace(' ', '_')
                filename = f"generated_image_{safe_prompt}_{timestamp}.png"
            
            # Determine workspace root
            workspace_root = os.environ.get('WORKSPACE_ROOT')
            if not workspace_root:
                # Default to workspace directory relative to backend
                current_file = os.path.abspath(__file__)
                # Go up: tools -> agent -> icpy -> backend -> icotes root
                icotes_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))
                workspace_root = os.path.join(icotes_root, "workspace")
            
            filepath = os.path.join(workspace_root, filename)
            
            # Get current context
            context = await get_current_context()
            context_name = context.get('contextId', 'local')
            
            # Check if we're on remote context
            if context_name != 'local':
                # Use filesystem service for remote (hop-aware)
                # Remote filesystem expects string content, so we base64 encode
                filesystem_service = await get_contextual_filesystem()
                # For remote, we need to write using SFTP which handles bytes
                # Get the SFTP connection and write directly
                try:
                    from icpy.services.context_router import get_context_router
                    router = await get_context_router()
                    fs = await router.get_filesystem()
                    
                    # Check if this is RemoteFileSystemAdapter
                    if hasattr(fs, '_sftp'):
                        # Direct SFTP write for binary data
                        sftp = fs._sftp()
                        if sftp:
                            import posixpath
                            remote_path = posixpath.join('/home', 'penthoy', 'icotes', 'workspace', filename)
                            async with sftp.open(remote_path, 'wb') as f:
                                await f.write(image_bytes)
                            logger.info(f"Saved image to {remote_path} ({len(image_bytes)} bytes) on remote context: {context_name}")
                        else:
                            raise Exception("SFTP connection not available")
                    else:
                        # Fallback: base64 encode and write as text
                        base64_content = base64.b64encode(image_bytes).decode('utf-8')
                        await filesystem_service.write_file(filepath, base64_content)
                        logger.info(f"Saved image (base64) to {filepath} on context: {context_name}")
                except Exception as e:
                    logger.error(f"Remote write failed: {e}, falling back to local")
                    # Fall through to local write
                    context_name = 'local'
            
            if context_name == 'local':
                # For local, write bytes directly to file
                # Ensure directory exists
                os.makedirs(workspace_root, exist_ok=True)
                
                # Write binary file directly
                with open(filepath, 'wb') as f:
                    f.write(image_bytes)
                
                logger.info(f"Saved image to {filepath} ({len(image_bytes)} bytes) on local context")
            
            # Return relative path for display
            return filename
            
        except Exception as e:
            logger.error(f"Error saving image to workspace: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def _decode_image_input(self, image_data: str, explicit_mime: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Decode image input (data URI, raw base64, or file:// path) into dict expected by Gemini SDK.
        
        Phase 7 Update: Hop-aware file loading using ContextRouter.
        
        Returns None on failure.
        """
        logger.info(f"_decode_image_input called: data length={len(image_data) if image_data else 0}")
        if not image_data:
            logger.warning("_decode_image_input: image_data is empty/None")
            return None
        try:
            mime_type = explicit_mime or "image/png"
            image_bytes = None
            
            # Handle file:// paths (hop-aware)
            if image_data.startswith("file://"):
                logger.info(f"_decode_image_input: Detected file:// path")
                file_path = image_data.replace("file://", "")
                logger.info(f"_decode_image_input: Resolved to {file_path}")
                
                # Use contextual filesystem to load file (works for both local and remote)
                try:
                    filesystem_service = await get_contextual_filesystem()
                    
                    # Try to read as binary first (proper way for images)
                    if hasattr(filesystem_service, 'read_file_binary'):
                        image_bytes = await filesystem_service.read_file_binary(file_path)
                        if image_bytes is None:
                            logger.error(f"Failed to read binary file: {file_path}")
                            return None
                    else:
                        # Fallback to text read with base64 conversion (for older FS implementations)
                        image_bytes = await filesystem_service.read_file(file_path)
                        
                        # Convert string to bytes if needed (some FS services return str)
                        if isinstance(image_bytes, str):
                            # If it's a base64 string, decode it
                            if image_bytes.startswith('data:image/'):
                                # Extract base64 part
                                _, b64_data = image_bytes.split(',', 1)
                                image_bytes = base64.b64decode(b64_data)
                            else:
                                # Assume it's raw base64
                                image_bytes = base64.b64decode(image_bytes)
                        elif image_bytes is None:
                            logger.error(f"Failed to read file: {file_path}")
                            return None
                            
                except FileNotFoundError:
                    logger.error(f"File does not exist: {file_path}")
                    return None
                    
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

    def _get_image_dimensions(self, image_bytes: bytes) -> Optional[Tuple[int, int]]:
        """
        Extract actual dimensions from image bytes.
        
        Returns:
            Tuple of (width, height) or None if unable to determine
        """
        if not PIL_AVAILABLE:
            return None
        
        try:
            img = Image.open(io.BytesIO(image_bytes))
            return img.size  # Returns (width, height)
        except Exception as e:
            logger.error(f"Failed to get image dimensions: {e}")
            return None

    def _resize_image(
        self, 
        image_bytes: bytes, 
        width: Optional[int] = None, 
        height: Optional[int] = None
    ) -> Tuple[bytes, str]:
        """
        Resize image to specified dimensions.
        
        Args:
            image_bytes: Original image bytes
            width: Target width (optional)
            height: Target height (optional)
            
        Returns:
            Tuple of (resized_image_bytes, mime_type)
            
        Note: If only one dimension is provided, maintains aspect ratio.
              If both provided, resizes to exact dimensions.
        """
        if not PIL_AVAILABLE:
            logger.warning("PIL not available, returning original image")
            return image_bytes, "image/png"
        
        if not width and not height:
            return image_bytes, "image/png"
        
        try:
            # Open image from bytes
            img = Image.open(io.BytesIO(image_bytes))
            original_width, original_height = img.size
            
            # Calculate target dimensions
            if width and height:
                # Both dimensions specified - resize to exact
                target_size = (width, height)
            elif width:
                # Only width specified - maintain aspect ratio
                aspect_ratio = original_height / original_width
                target_size = (width, int(width * aspect_ratio))
            else:
                # Only height specified - maintain aspect ratio
                aspect_ratio = original_width / original_height
                target_size = (int(height * aspect_ratio), height)
            
            # Resize with high-quality LANCZOS resampling
            resized = img.resize(target_size, Image.Resampling.LANCZOS)
            
            # Convert back to bytes
            output = io.BytesIO()
            resized.save(output, format='PNG')
            resized_bytes = output.getvalue()
            
            logger.info(f"Resized image from {original_width}x{original_height} to {target_size[0]}x{target_size[1]}")
            
            return resized_bytes, "image/png"
            
        except Exception as e:
            logger.error(f"Error resizing image: {e}")
            import traceback
            traceback.print_exc()
            # Return original on error
            return image_bytes, "image/png"

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
        
        Phase 7 Update: Added hop support, resolution control, and custom filenames.
        
        Args:
            prompt: Text description of image to generate
            save_to_workspace: Whether to save image to workspace (default: True)
            filename: Optional custom filename (without extension)
            width: Optional target width in pixels
            height: Optional target height in pixels
            
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
            custom_filename = kwargs.get("filename")
            target_width = kwargs.get("width")
            target_height = kwargs.get("height")

            image_part = None
            if (mode in ("auto", "edit")) and input_image_data:
                logger.info(f"ImagenTool: Attempting to decode image_data (mode={mode}, length={len(input_image_data)})")
                image_part = await self._decode_image_input(input_image_data, input_image_mime)
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
            
            # Resize image if dimensions specified
            if target_width or target_height:
                image_bytes, mime_type = self._resize_image(image_bytes, target_width, target_height)
                logger.info(f"Image resized to {target_width or 'auto'}x{target_height or 'auto'}")
            
            # Get actual image dimensions for widget display
            actual_dimensions = self._get_image_dimensions(image_bytes)
            if actual_dimensions:
                actual_width, actual_height = actual_dimensions
                logger.info(f"Final image dimensions: {actual_width}x{actual_height}")
            
            # Convert binary image to base64 data URI
            image_data_uri = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
            
            # Optionally save to workspace (hop-aware)
            saved_path = None
            if save_to_workspace:
                saved_path = await self._save_image_to_workspace(image_bytes, str(prompt), custom_filename)
            
            # Extract raw base64 (without data URI prefix) for response
            raw_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Get current context for result metadata
            context = await get_current_context()
            
            # Return successful result with image data
            result_data = {
                "imageData": raw_base64,  # Raw base64 for UI
                "imageUrl": image_data_uri,  # Full data URI if needed
                "mimeType": mime_type,
                "prompt": str(prompt),
                "model": self._model,
                "timestamp": datetime.now().isoformat(),
                "mode": effective_mode,
                "attemptedModels": attempted,
                "context": context.get('contextId', 'local'),
                "contextHost": context.get('host')
            }
            
            # Add actual dimensions for widget display
            if actual_dimensions:
                result_data["size"] = f"{actual_dimensions[0]}x{actual_dimensions[1]}"
                result_data["width"] = actual_dimensions[0]
                result_data["height"] = actual_dimensions[1]
            
            if image_part:
                result_data["sourceImageProvided"] = True
            
            if target_width or target_height:
                result_data["resizedTo"] = f"{target_width or 'auto'}x{target_height or 'auto'}"
            
            if saved_path:
                result_data["filePath"] = saved_path
                context_name = context.get('contextId', 'local')
                if context_name != 'local':
                    result_data["message"] = f"Image generated and saved to workspace/{saved_path} on {context_name}"
                else:
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
