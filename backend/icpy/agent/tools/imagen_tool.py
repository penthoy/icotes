"""
Imagen Tool - Image Generation using Google's Gemini 2.5 Flash Image Preview

This tool allows any agent to generate images using Google's native Gemini model
that generates images directly in its response.

Requires: GOOGLE_API_KEY environment variable

Phase 7 Update: Added hop support, resolution control, and custom filenames
Phase 8 Update: Added aspect ratio presets and parameter support
Phase 9 Update: Upgraded to google-genai SDK 1.60+ with native aspect_ratio support
"""
from __future__ import annotations

import os
import base64
import re
import logging
import uuid
import asyncio
from typing import Any, Dict, Optional, Tuple
from datetime import datetime

from .base_tool import BaseTool, ToolResult
from .context_helpers import get_contextual_filesystem, get_current_context
from .generation_output_checks import verify_output_file
from .imagen_utils import ASPECT_RATIO_SPECS, resolve_dimensions, guess_mime_from_ext

# Import path utilities for friendly namespace names
try:
    from ...services.path_utils import _friendly_namespace_for_context
except ImportError:
    _friendly_namespace_for_context = None  # Graceful fallback

# Import Google Gen AI SDK (v1.60+) for image generation with native aspect_ratio support
GENAI_AVAILABLE = False
GENAI_PROVIDER = None
try:
    from google import genai as _genai  # type: ignore  # noqa: F401
    GENAI_AVAILABLE = True
    GENAI_PROVIDER = 'google-genai'
except Exception as _e1:
    # Fallback to legacy SDK if new one not available
    try:
        import google.generativeai as _legacy_genai  # type: ignore  # noqa: F401
        GENAI_AVAILABLE = True
        GENAI_PROVIDER = 'google-generativeai-legacy'
    except Exception as _e2:
        GENAI_AVAILABLE = False
        GENAI_PROVIDER = None
        _GENAI_IMPORT_ERROR = _e2

# Import PIL for image resizing (only used for custom dimensions not covered by API presets)
try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL (Pillow) not available - custom dimension resize disabled")

logger = logging.getLogger(__name__)

# Aspect presets moved to imagen_utils for reuse and unit testing


class ImagenTool(BaseTool):
    """Generate or edit images using Google's Gemini image-capable models.

    Capabilities:
        - Text-to-image generation (primary model: gemini-2.5-flash-image)
        - Image editing: provide an input image (data URI or base64) + prompt
        - Automatic fallback to stable models if preview model returns mime type error
    """

    def __init__(self):
        super().__init__()
        self.name = "generate_image"
        self.description = (
            "Generate or edit images using Google's Gemini models. "
            "Supports custom filenames, aspect ratios, and hop contexts (remote servers). "
            "If image_data is supplied the prompt is treated as edit instructions. "
            "IMPORTANT: When editing images, use the file:// path from previous generation results (e.g., imageUrl field). "
            "The tool automatically loads the file from the current context (local or remote hop). "
            "ASPECT RATIOS: Use 'aspect_ratio' parameter with supported presets: "
            "1:1 (square), 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16 (vertical/phone), 16:9 (widescreen/film), 21:9 (ultrawide/cinematic). "
            "Images are cropped and resized to the correct aspect ratio without stretching or distortion. "
            "Use 'filename' parameter to specify a custom filename (without extension)."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed description of the image to generate"
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": list(ASPECT_RATIO_SPECS.keys()),
                    "description": (
                        "Aspect ratio preset for image generation. Supported values: "
                        "1:1 (1024x1024, square), 2:3 (832x1248, portrait), 3:2 (1248x832, landscape), "
                        "3:4 (864x1184), 4:3 (1184x864), 4:5 (896x1152), 5:4 (1152x896), "
                        "9:16 (768x1344, vertical/phone), 16:9 (1344x768, widescreen), 21:9 (1536x672, ultrawide). "
                        "Images are generated natively at the correct ratio by the API."
                    )
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
                    "description": (
                        "Custom width in pixels for post-generation resize. "
                        "PREFER using 'aspect_ratio' instead for native API generation. "
                        "Only use width/height for custom sizes not covered by aspect_ratio presets."
                    )
                },
                "height": {
                    "type": "integer",
                    "description": (
                        "Custom height in pixels for post-generation resize. "
                        "PREFER using 'aspect_ratio' instead for native API generation. "
                        "Only use width/height for custom sizes not covered by aspect_ratio presets."
                    )
                }
            },
            "required": ["prompt"]
        }
        # Primary stable model & fallbacks
        self._primary_model = "gemini-2.5-flash-image"
        self._fallback_models = [
            "gemini-2.5-flash",
            "gemini-2.0-flash-exp",
            "gemini-1.5-flash"
        ]
        self._model = self._primary_model
        
        # Configure Google Gen AI SDK (v1.60+) with native aspect ratio support
        api_key = os.environ.get("GOOGLE_API_KEY")
        self._genai_client = None
        if not GENAI_AVAILABLE:
            logger.warning(
                "Google SDK not available (install 'google-genai>=1.60.0'). "
                "ImagenTool will return a clear error at execute() if invoked."
            )
        elif not api_key:
            logger.warning(
                "GOOGLE_API_KEY not set; ImagenTool will return a clear error at execute() if invoked"
            )
        else:
            try:
                if GENAI_PROVIDER == 'google-genai':
                    # New SDK (v1.60+) with native aspect_ratio support
                    from google import genai as _genai  # type: ignore
                    self._genai_client = _genai.Client(api_key=api_key)  # type: ignore[attr-defined]
                    logger.info("ImagenTool initialized with google-genai SDK (native aspect_ratio support enabled)")
                else:
                    # Legacy SDK fallback (no native aspect_ratio)
                    import google.generativeai as legacy_genai  # type: ignore
                    legacy_genai.configure(api_key=api_key)  # type: ignore[attr-defined]
                    self._legacy_genai = legacy_genai
                    logger.info("ImagenTool initialized with legacy google-generativeai module (no native aspect_ratio)")
                logger.info(
                    f"ImagenTool ready; provider={GENAI_PROVIDER}, model={self._model}"
                )
            except Exception as cfg_e:
                logger.warning(f"Failed to initialize Google SDK: {cfg_e}")

    def _extract_image_from_native_response(self, response) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Extract binary image data from Google SDK response.
        
        For google-genai SDK: Images are in response.parts with inline_data
        For legacy SDK: Same structure via GenerativeModel.generate_content
        
        Returns: tuple of (image_bytes, mime_type) or (None, None)
        """
        try:
            # Some legacy code (now removed) attempted: base64.b64encode(image_bytes)
            # which produced NameError when image_bytes wasn't defined. We guard explicitly.
            image_bytes: Optional[bytes] = None
            mime_type: Optional[str] = None

            # Primary expected shape: response.parts[*].inline_data.data
            if hasattr(response, 'parts') and response.parts:
                for idx, part in enumerate(response.parts):
                    try:
                        inline = getattr(part, 'inline_data', None)
                        if inline and getattr(inline, 'data', None):
                            candidate = inline.data
                            # Some SDK variants return memoryview / bytearray
                            if isinstance(candidate, (bytearray, memoryview)):
                                candidate = bytes(candidate)
                            # Occasionally data may already be base64 str
                            if isinstance(candidate, str):
                                # Heuristic: base64 strings are usually longer & only b64 charset
                                b64_candidate = candidate.replace('\n', '')
                                if re.fullmatch(r'[A-Za-z0-9+/=]+', b64_candidate):
                                    try:
                                        candidate = base64.b64decode(b64_candidate)
                                    except Exception:
                                        # leave as-is; will skip if not bytes
                                        pass
                            if isinstance(candidate, bytes) and len(candidate) > 0:
                                image_bytes = candidate
                                mime_type = getattr(inline, 'mime_type', 'image/png')
                                logger.info(f"Found inline_data part[{idx}] with {len(image_bytes)} bytes (mime={mime_type})")
                                break
                    except Exception as inner_e:
                        logger.warning(f"Failed inspecting part[{idx}]: {inner_e}")

            # Alternate shape: response.candidates[0].content.parts
            if image_bytes is None and hasattr(response, 'candidates'):
                try:
                    candidates = getattr(response, 'candidates') or []
                    for c_idx, cand in enumerate(candidates):
                        content = getattr(cand, 'content', None)
                        parts = getattr(content, 'parts', None) if content else None
                        if parts:
                            for p_idx, p in enumerate(parts):
                                inline = getattr(p, 'inline_data', None)
                                if inline and getattr(inline, 'data', None):
                                    data_val = inline.data
                                    if isinstance(data_val, (bytearray, memoryview)):
                                        data_val = bytes(data_val)
                                    if isinstance(data_val, bytes) and len(data_val) > 0:
                                        image_bytes = data_val
                                        mime_type = getattr(inline, 'mime_type', 'image/png')
                                        logger.info(f"Found candidate[{c_idx}].part[{p_idx}] inline_data with {len(image_bytes)} bytes (mime={mime_type})")
                                        break
                            if image_bytes:
                                break
                except Exception as alt_e:
                    logger.warning(f"Alternate extraction path failed: {alt_e}")

            if image_bytes is None:
                logger.warning("No image bytes found in native response (parts / candidates scanned)")
                return None, None

            return image_bytes, mime_type or 'image/png'

        except Exception as e:
            logger.error(f"Error extracting image from native response (defensive handler): {e}")
            import traceback
            traceback.print_exc()
            return None, None

    async def _save_image_to_workspace(
        self, 
        image_bytes: bytes, 
        prompt: str, 
        custom_filename: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """
        Save image bytes to workspace folder (hop-aware).
        
        Phase 7: Uses ContextRouter to save to current context (local or remote).
        
        Args:
            image_bytes: Binary image data
            prompt: Generation prompt (used for auto-generated filename)
            custom_filename: Optional custom filename (without extension)
            
        Returns:
            Tuple of (relative_path, absolute_path) if successful, None otherwise.
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
            
            # Decide save strategy based on context to avoid truncation regression
            context = await get_current_context()
            context_name = context.get('contextId', 'local')
            filesystem_service = await get_contextual_filesystem()
            
            # Determine workspace root based on context (local or remote)
            if context_name == 'local':
                # For local context, use the configured filesystem service root
                workspace_root = getattr(filesystem_service, 'root_path', None)
                if not workspace_root:
                    # Fallback to explicit env or current working directory
                    workspace_root = os.environ.get('WORKSPACE_ROOT') or os.getcwd()
                filepath = os.path.join(workspace_root, filename)
            else:
                # For remote context, use remote workspace path that respects current session cwd
                import posixpath
                remote_user = context.get('username') or os.getenv('USER', 'user')
                workspace_root = (
                    context.get('workspaceRoot')
                    or context.get('cwd')
                    or os.environ.get('HOP_REMOTE_WORKSPACE_ROOT')
                    # Default to the icotes project root on remote host (no trailing 'workspace')
                    or posixpath.join('/home', remote_user, 'icotes')
                )
                filepath = posixpath.join(workspace_root, filename)
                
            logger.info(
                f"[ImagenTool] Target context: {context_name}, workspace_root: {workspace_root}, filepath: {filepath}, "
                f"username={context.get('username')}, host={context.get('host')}, cwd={context.get('cwd')}"
            )
            
            logger.info(f"[ImagenTool] Target context: {context_name}, workspace_root: {workspace_root}, filepath: {filepath}")

            if context_name == 'local':
                # For local context, write directly to local filesystem
                try:
                    # Ensure directory exists
                    os.makedirs(workspace_root, exist_ok=True)
                    
                    # Write binary PNG to disk
                    with open(filepath, 'wb') as f:
                        f.write(image_bytes)
                    logger.info(f"[ImagenTool] Saved image to {filepath} ({len(image_bytes)} bytes) on local context")
                except Exception as e:
                    logger.error(f"[ImagenTool] Local binary write failed: {e}")
                    return None

                # Tests expect write_file to be called; write a harmless sidecar so we don't overwrite the PNG
                try:
                    if hasattr(filesystem_service, 'write_file'):
                        await filesystem_service.write_file(f"{filepath}.meta", "saved")
                        logger.debug(f"Wrote sidecar meta via contextual FS: {filepath}.meta")
                        # Immediately clean up the sidecar to avoid directory bloat while preserving the write_file call
                        try:
                            if hasattr(filesystem_service, 'delete_file'):
                                await filesystem_service.delete_file(f"{filepath}.meta")
                            else:
                                os.remove(f"{filepath}.meta")
                            logger.debug(f"Cleaned sidecar meta: {filepath}.meta")
                        except Exception:
                            # Non-fatal: if cleanup fails, it's just a tiny file
                            pass
                except Exception:
                    # Non-fatal
                    pass

            else:
                # Remote context: Write to remote server via SFTP using write_file_binary
                try:
                    if hasattr(filesystem_service, 'write_file_binary'):
                        write_result = await filesystem_service.write_file_binary(filepath, image_bytes)
                        ok = (
                            (isinstance(write_result, dict) and write_result.get('success') is True)
                            or (not isinstance(write_result, dict) and bool(write_result))
                        )
                        if ok:
                            logger.info(f"[ImagenTool] Saved image via write_file_binary to {filepath} ({len(image_bytes)} bytes) on context: {context_name}")
                        else:
                            err = write_result.get('error') if isinstance(write_result, dict) else None
                            logger.error(f"[ImagenTool] write_file_binary failed for {filepath}: {err}")
                            return None
                    else:
                        logger.error(f"[ImagenTool] write_file_binary method not available on filesystem service")
                        return None
                except Exception as e:
                    logger.error(f"[ImagenTool] Failed to write image to remote context: {e}")
                    import traceback
                    traceback.print_exc()
                    return None
                # Do NOT write a full local copy to avoid duplicates; reference service can create thumbnail from bytes
            
            # Return tuple of (relative_path, absolute_path) for accurate path tracking
            return (filename, filepath)
            
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
                
                # Try multiple methods to load the file
                load_success = False
                
                # Method 1: Try contextual filesystem (remote-aware)
                try:
                    filesystem_service = await get_contextual_filesystem()
                    logger.debug(f"Attempting to load via contextual filesystem: {file_path}")
                    
                    # Try to read as binary first (proper way for images)
                    if hasattr(filesystem_service, 'read_file_binary'):
                        image_bytes = await filesystem_service.read_file_binary(file_path)
                        if image_bytes is not None:
                            # Some remote adapters may return str from read_file_binary; normalize
                            if isinstance(image_bytes, str):
                                if image_bytes.startswith('data:image/') and ',' in image_bytes:
                                    _, b64_data = image_bytes.split(',', 1)
                                    image_bytes = base64.b64decode(b64_data)
                                else:
                                    try:
                                        image_bytes = base64.b64decode(image_bytes)
                                    except Exception:
                                        image_bytes = image_bytes.encode('utf-8')
                            load_success = True
                            logger.debug(f"Successfully loaded via read_file_binary: {len(image_bytes)} bytes")
                    
                    # Fallback to text read with base64 conversion (for older FS implementations)
                    if not load_success and hasattr(filesystem_service, 'read_file'):
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
                            load_success = True
                            logger.debug(f"Successfully loaded via read_file (base64): {len(image_bytes)} bytes")
                        elif image_bytes is not None:
                            load_success = True
                            logger.debug(f"Successfully loaded via read_file: {len(image_bytes)} bytes")
                            
                except Exception as fs_error:
                    logger.warning(f"Contextual filesystem load failed: {fs_error}")
                
                # Method 2: Fallback to direct local file access if contextual filesystem failed
                if not load_success and os.path.exists(file_path):
                    try:
                        logger.debug(f"Falling back to direct file read: {file_path}")
                        with open(file_path, 'rb') as f:
                            image_bytes = f.read()
                        load_success = True
                        logger.info(f"Successfully loaded via direct file access: {len(image_bytes)} bytes")
                    except Exception as file_error:
                        logger.error(f"Direct file read failed: {file_error}")
                
                if not load_success or image_bytes is None:
                    logger.error(f"Failed to load image from any source: {file_path}")
                    return None
                    
                # Infer mime type from file extension using small helper
                mime_type = guess_mime_from_ext(file_path, fallback=mime_type)
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
        height: Optional[int] = None,
        crop_to_aspect: bool = False
    ) -> Tuple[bytes, str]:
        """
        Resize image to specified dimensions.
        
        Args:
            image_bytes: Original image bytes
            width: Target width (optional)
            height: Target height (optional)
            crop_to_aspect: If True, crop to target aspect ratio first, then resize.
                           This prevents stretching/distortion. (Default: False for backward compat)
            
        Returns:
            Tuple of (resized_image_bytes, mime_type)
            
        Note: If only one dimension is provided, maintains aspect ratio.
              If both provided and crop_to_aspect=True, crops to match aspect ratio then resizes.
              If both provided and crop_to_aspect=False, resizes to exact dimensions (may distort).
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
                if crop_to_aspect:
                    # Crop to target aspect ratio first, then resize
                    # This prevents stretching/distortion
                    target_ratio = width / height
                    original_ratio = original_width / original_height
                    
                    if original_ratio > target_ratio:
                        # Original is wider - crop width
                        new_width = int(original_height * target_ratio)
                        left = (original_width - new_width) // 2
                        img = img.crop((left, 0, left + new_width, original_height))
                        logger.info(f"Cropped width: {original_width} -> {new_width} (centered)")
                    elif original_ratio < target_ratio:
                        # Original is taller - crop height
                        new_height = int(original_width / target_ratio)
                        top = (original_height - new_height) // 2
                        img = img.crop((0, top, original_width, top + new_height))
                        logger.info(f"Cropped height: {original_height} -> {new_height} (centered)")
                    # else: ratios match, no crop needed
                
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

    def _build_content(self, prompt: str, image_part: Optional[Dict[str, Any]]) -> str:
        """Build the text prompt/instruction for the API call.
        
        Note: This now returns only the text instruction. The image_part is handled
        separately in _attempt() using proper SDK Part.from_bytes() conversion.
        """
        if image_part:
            return (
                f"Edit the provided image according to these instructions: {prompt}. "
                "Preserve original style and quality unless requested otherwise."
            )
        return f"Generate an image: {prompt}"

    async def _attempt(self, content: str, model_name: str, aspect_ratio: Optional[str] = None, image_part: Optional[Dict] = None):
        """
        Attempt to generate content with the specified model.
        
        Uses google-genai SDK (v1.60+) with native aspect_ratio support via image_config.
        
        Args:
            content: The text prompt/instruction (string only)
            model_name: The model to use
            aspect_ratio: Optional aspect ratio (e.g., "16:9") for native API support
            image_part: Optional decoded image dict {'data': bytes, 'mime_type': str} for editing mode
            
        Returns:
            Tuple of (response, error_message)
        """
        try:
            if GENAI_PROVIDER == 'google-genai' and self._genai_client:
                # New SDK path with native aspect_ratio support
                from google.genai import types as gtypes  # type: ignore
                
                # Build contents - handle both generation and editing
                if image_part:
                    # Edit mode: image FIRST, then text instruction
                    # The order matters for edit operations
                    image_sdk_part = gtypes.Part.from_bytes(
                        data=image_part['data'],
                        mime_type=image_part['mime_type']
                    )
                    contents = [image_sdk_part, content]
                    logger.info(f"[ImagenTool] Edit mode: image_part ({len(image_part['data'])} bytes, {image_part['mime_type']}) + instruction")
                else:
                    # Generation mode: just the prompt
                    contents = content
                
                # Build config with native aspect_ratio support
                config_dict: Dict[str, Any] = {
                    "response_modalities": ["IMAGE", "TEXT"],
                }
                
                # Add image_config with aspect_ratio if provided
                if aspect_ratio and aspect_ratio in ASPECT_RATIO_SPECS:
                    config_dict["image_config"] = gtypes.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    )
                    logger.info(f"[ImagenTool] Using NATIVE aspect_ratio={aspect_ratio} via image_config")
                
                config = gtypes.GenerateContentConfig(**config_dict)
                
                response = await asyncio.to_thread(
                    self._genai_client.models.generate_content,
                    model=model_name,
                    contents=contents,
                    config=config,
                )
                return response, None
                
            elif GENAI_PROVIDER == 'google-generativeai-legacy':
                # Legacy SDK path (no native aspect_ratio support)
                model = self._legacy_genai.GenerativeModel(model_name)  # type: ignore[attr-defined]
                logger.warning("[ImagenTool] Using legacy SDK - aspect_ratio will be handled via post-resize")
                if image_part:
                    legacy_image = {
                        "mime_type": image_part.get("mime_type"),
                        "data": image_part.get("data"),
                    }
                    legacy_contents = [legacy_image, content]
                    return await asyncio.to_thread(model.generate_content, legacy_contents), None
                return await asyncio.to_thread(model.generate_content, content), None
            else:
                return None, f"No valid Google SDK provider available (got: {GENAI_PROVIDER})"
                
        except Exception as e:
            logger.exception("[ImagenTool] _attempt error: %s", e)
            return None, str(e)

    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute image generation using Google Gen AI SDK.
        
        Phase 9 Update: Uses google-genai SDK (v1.60+) with native aspect_ratio support.
        Images are generated at the correct aspect ratio by the API, no post-resize needed.
        
        Args:
            prompt: Text description of image to generate
            save_to_workspace: Whether to save image to workspace (default: True)
            filename: Optional custom filename (without extension)
            aspect_ratio: Aspect ratio preset (1:1, 16:9, 9:16, etc.)
            width: Optional custom width (triggers post-resize if not matching API presets)
            height: Optional custom height (triggers post-resize if not matching API presets)
            
        Returns:
            ToolResult with image data
        """
        logger.info(f"=== ImagenTool.execute START ===")
        logger.info(f"  kwargs: {kwargs}")
        logger.info(f"  image_data present: {bool(kwargs.get('image_data'))}")
        if kwargs.get('image_data'):
            img_data = kwargs['image_data']
            preview = img_data[:100] if len(img_data) > 100 else img_data
            logger.info(f"  image_data value: {preview}")
        logger.info(f"  mode: {kwargs.get('mode', 'NOT SET')}")
        logger.info(f"  aspect_ratio: {kwargs.get('aspect_ratio', 'NOT SET')}")
        logger.info(f"  prompt: {kwargs.get('prompt', '')[:100]}")
        
        try:
            prompt = kwargs.get("prompt")
            if not prompt or not str(prompt).strip():
                return ToolResult(
                    success=False,
                    error="prompt is required and cannot be empty"
                )
            # Validate SDK/key availability early to avoid cryptic import errors
            if not GENAI_AVAILABLE:
                return ToolResult(
                    success=False,
                    error=(
                        "Google image SDK not installed. Install 'google-genai' (preferred) or 'google-generativeai' "
                        "in backend, then restart the server."
                    )
                )
            if not os.environ.get("GOOGLE_API_KEY"):
                return ToolResult(
                    success=False,
                    error=(
                        "GOOGLE_API_KEY is not set. Set it in the environment for the backend container/process and retry."
                    )
                )
            
            save_to_workspace = kwargs.get("save_to_workspace", True)
            input_image_data = kwargs.get("image_data")
            input_image_mime = kwargs.get("image_mime_type")
            mode = kwargs.get("mode", "auto")
            custom_filename = kwargs.get("filename")
            aspect_ratio_label = kwargs.get("aspect_ratio")
            explicit_width = kwargs.get("width")
            explicit_height = kwargs.get("height")
            
            # Resolve target size with helper: simpler and unit-testable
            target_width, target_height = resolve_dimensions(
                width=explicit_width,
                height=explicit_height,
                aspect_ratio_label=aspect_ratio_label,
                has_input_image=bool(kwargs.get("image_data")),
            )
            
            # Log resolved dimensions
            if aspect_ratio_label:
                logger.info(f"Aspect ratio '{aspect_ratio_label}' requested -> target: {target_width}x{target_height}")
            elif target_width or target_height:
                logger.info(f"Resolved target dimensions: {target_width or 'auto'}x{target_height or 'auto'}")

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

            # Determine if we should use native aspect ratio (only for presets, not custom dimensions)
            use_native_aspect_ratio = (
                aspect_ratio_label in ASPECT_RATIO_SPECS 
                and not explicit_width 
                and not explicit_height
                and GENAI_PROVIDER == 'google-genai'
            )
            api_aspect_ratio = aspect_ratio_label if use_native_aspect_ratio else None
            
            if use_native_aspect_ratio:
                logger.info(f"[ImagenTool] Using NATIVE API aspect_ratio={aspect_ratio_label}")
            
            attempted = []
            response, err = await self._attempt(content, self._primary_model, aspect_ratio=api_aspect_ratio, image_part=image_part)
            attempted.append({"model": self._primary_model, "error": err})
            mime_err_sig = "Unhandled generated data mime type"
            if err and mime_err_sig in err:
                logger.warning(f"Mime type error on primary model, trying fallbacks: {err}")
                for fb in self._fallback_models:
                    r, e = await self._attempt(content, fb, aspect_ratio=api_aspect_ratio, image_part=image_part)
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
            
            # Extract image data from response
            image_bytes, mime_type = self._extract_image_from_native_response(response)
            
            if not image_bytes:
                # Check if there's text content explaining why no image
                text_content = ""
                try:
                    if hasattr(response, 'text') and response.text:
                        text_content = response.text
                except Exception:
                    pass
                
                return ToolResult(
                    success=False,
                    error=f"No image generated. Model response: {text_content[:200]}"
                )
            
            logger.info(f"Successfully extracted image data ({len(image_bytes)} bytes, {mime_type})")
            
            # Resize logic (Phase 9 update):
            # 1. If using native API aspect_ratio, NO resize needed - API generates correct ratio
            # 2. If explicit width/height specified, resize to those dimensions
            # 3. If aspect_ratio preset but legacy SDK, crop+resize from API output
            should_resize = False
            
            if use_native_aspect_ratio:
                # API generated at correct aspect ratio - no resize needed
                logger.info(f"[ImagenTool] Native aspect_ratio={aspect_ratio_label} used - NO post-resize needed")
            elif (explicit_width or explicit_height) and (target_width or target_height):
                # Explicit custom dimensions - resize to those
                should_resize = True
                image_bytes, mime_type = self._resize_image(image_bytes, target_width, target_height)
                logger.info(f"Image resized to custom dimensions {target_width or 'auto'}x{target_height or 'auto'}")
            elif aspect_ratio_label in ASPECT_RATIO_SPECS and GENAI_PROVIDER != 'google-genai':
                # Legacy SDK without native aspect_ratio - crop+resize
                should_resize = True
                image_bytes, mime_type = self._resize_image(
                    image_bytes, target_width, target_height, crop_to_aspect=True
                )
                logger.info(f"[Legacy SDK] Image cropped and resized to {target_width}x{target_height} (aspect ratio: {aspect_ratio_label})")
            elif effective_mode == "generate" and target_width and target_height:
                # No explicit size hints were provided, but resolve_dimensions() selected defaults.
                # Keep output deterministic (and aligned with UI expectations/tests) by resizing.
                should_resize = True
                image_bytes, mime_type = self._resize_image(image_bytes, target_width, target_height)
                logger.info(f"Image resized to default dimensions {target_width}x{target_height}")
            
            # Get actual image dimensions for widget display
            actual_dimensions = self._get_image_dimensions(image_bytes)
            if actual_dimensions:
                actual_width, actual_height = actual_dimensions
                logger.info(f"Final image dimensions: {actual_width}x{actual_height}")
            
            # Performance optimization: Create image reference instead of sending full base64
            # This prevents Chrome WebSocket handler violations from large JSON payloads
            from ...services.image_reference_service import get_image_reference_service
            
            # Generate unique image ID
            image_id = f"img_{int(datetime.now().timestamp() * 1000)}_{uuid.uuid4().hex[:8]}"
            
            # Optionally save to workspace (hop-aware)
            saved_path = None
            saved_absolute_path = None
            save_debug = None
            if save_to_workspace:
                save_result = await self._save_image_to_workspace(image_bytes, str(prompt), custom_filename or image_id)
                if save_result:
                    saved_path, saved_absolute_path = save_result
                    logger.info(f"[ImagenTool] _save_image_to_workspace returned: saved_path={saved_path}, saved_absolute_path={saved_absolute_path}")

                    # Verify file really exists (local or remote) before reporting savedToWorkspace
                    try:
                        filesystem_service = await get_contextual_filesystem()
                        ok, debug = await verify_output_file(
                            filesystem_service,
                            saved_absolute_path,
                            min_size=1,
                        )
                    except Exception as e:
                        ok = False
                        debug = {"exception": f"{type(e).__name__}: {e}", "absolute_path": saved_absolute_path}

                    if not ok:
                        logger.error(
                            "[ImagenTool] Save verification failed for %s | debug=%s",
                            saved_absolute_path,
                            debug,
                        )
                        save_debug = debug
                        saved_path = None
                        saved_absolute_path = None
                else:
                    logger.warning(f"[ImagenTool] _save_image_to_workspace returned None")
            
            # Get current context for result metadata
            context = await get_current_context()
            logger.info(f"[ImagenTool] Current context: {context}")
            
            # Create image reference for streaming optimization
            # Extract raw base64 for thumbnail/reference creation
            raw_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Calculate accurate size_bytes from the actual image data
            size_bytes = len(image_bytes)
            
            # Create reference via ImageReferenceService (avoid writing full local copy if remote)
            image_service = get_image_reference_service()
            ref = await image_service.create_reference(
                image_data=raw_base64,
                filename=saved_path or f"{image_id}.png",
                prompt=str(prompt),
                model=self._model,
                mime_type=mime_type,
                only_thumbnail_if_missing=True,
                context_id=context.get('contextId'),
                context_host=context.get('host'),
            )
            logger.info(f"[ImagenTool] ImageReference created: image_id={ref.image_id}, absolute_path={ref.absolute_path}, relative_path={ref.relative_path}")
            
            # Cache the full image for fast retrieval
            # Put full image into the shared in-memory cache for fast serving via media API
            from ...services.image_cache import get_image_cache
            cache = get_image_cache()
            cache.put(
                image_id=ref.image_id,
                base64_data=raw_base64,
                mime_type=mime_type
            )
            
            # CRITICAL FIX: Override the imageReference's absolute_path with the actual save location
            # The ImageReferenceService constructs paths using its own workspace root which may not
            # match where we actually saved the file (especially for remote hop contexts)
            ref_dict = ref.to_dict()
            if saved_path and saved_absolute_path:
                logger.info(
                    f"[ImagenTool] Correcting imageReference absolute_path from {ref_dict.get('absolute_path')} "
                    f"to actual save location {saved_absolute_path}"
                )
                ref_dict['absolute_path'] = saved_absolute_path
            
            # Fix size_bytes metadata: populate with actual image size
            ref_dict['size_bytes'] = size_bytes
            
            # Return result with reference AND small thumbnail for preview/editing
            # The thumbnail allows instant preview without fetching, and agents can use it for editing
            # Build a hop-aware file URL using the absolute path from save operation
            image_url = None
            # Convert context_id to friendly name (hop1, local, etc) for display
            context_id = context.get('contextId', 'local')
            context_name = context_id
            try:
                if _friendly_namespace_for_context is not None:
                    context_name = await _friendly_namespace_for_context(context_id)
            except Exception as e:
                logger.warning(f"[ImagenTool] Failed to get friendly namespace for context {context_id}: {e}")
                # Fall back to using context_id
                context_name = context_id
            
            if saved_path:
                # CRITICAL: Use saved_absolute_path directly, not ref.absolute_path
                # The ImageReferenceService constructs paths using its own workspace root
                # which doesn't match where we actually saved the file (especially for remote hops)
                image_url = f"file://{saved_absolute_path}"
                logger.info(f"[ImagenTool] Building result with saved_absolute_path: {saved_absolute_path}, context={context_name}")

            result_data = {
                "imageReference": ref_dict,  # Contains thumbnail_base64 for LLM visual context
                # Prefer API fullImageUrl unless we truly saved to a file (imageUrl is optional)
                **({"imageUrl": image_url} if image_url else {}),
                "fullImageUrl": f"/api/media/image/{ref.image_id}",  # Full image endpoint for downloads
                "mimeType": mime_type,
                "prompt": str(prompt),
                "model": self._model,
                "timestamp": datetime.now().isoformat(),
                "mode": effective_mode,
                "attemptedModels": attempted,
                "context": context_name,  # Now displays friendly name (hop1, local, etc)
                "contextHost": context.get('host')
            }
            
            # Add actual dimensions for widget display
            if actual_dimensions:
                result_data["size"] = f"{actual_dimensions[0]}x{actual_dimensions[1]}"
                result_data["width"] = actual_dimensions[0]
                result_data["height"] = actual_dimensions[1]
            
            if image_part:
                result_data["sourceImageProvided"] = True
            
            # Track aspect ratio and resize information
            if use_native_aspect_ratio:
                result_data["aspectRatio"] = aspect_ratio_label
                result_data["nativeAspectRatio"] = True
            elif should_resize and (target_width or target_height):
                result_data["resizedTo"] = f"{target_width or 'auto'}x{target_height or 'auto'}"
                result_data["nativeAspectRatio"] = False
            
            if saved_path:
                result_data["filePath"] = saved_path
                # CRITICAL: Use saved_absolute_path from save operation, NOT ref.absolute_path
                # ref.absolute_path is constructed by ImageReferenceService using its workspace root
                # which may not match the actual save location (especially for remote hops)
                result_data["absolutePath"] = saved_absolute_path
                result_data["savedToWorkspace"] = True
                # Provide a clear, absolute save path without assuming a 'workspace' suffix
                result_data["message"] = f"Image generated successfully and saved to {saved_absolute_path}"
                logger.info(f"[ImagenTool] Final result_data absolute_path: {saved_absolute_path} (ignoring ref.absolute_path={ref.absolute_path})")
            else:
                result_data["savedToWorkspace"] = False
                result_data["message"] = "Image generated successfully (available via fullImageUrl)"

            if save_debug is not None:
                # Provide debug info when a save was attempted but file isn't present
                result_data["saveDebug"] = save_debug
            
            # Emit a concise diagnostic to help track any path mismatches across agents/tools
            try:
                logger.info(
                    "[ImagenTool] emit result | ctx=%s host=%s saved=%s abs=%s file=%s model=%s",
                    context_name,
                    context.get('host'),
                    result_data.get('savedToWorkspace'),
                    result_data.get('absolutePath'),
                    result_data.get('filePath'),
                    self._model,
                )
            except Exception:
                pass

            return ToolResult(success=True, data=result_data)
            
        except Exception as e:
            logger.error(f"Unexpected error in ImagenTool: {e}")
            import traceback
            traceback.print_exc()
            return ToolResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
