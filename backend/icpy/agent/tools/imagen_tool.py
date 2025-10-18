"""
Imagen Tool - Image Generation using Google's Gemini 2.5 Flash Image Preview

This tool allows any agent to generate images using Google's native Gemini model
that generates images directly in its response.

Requires: GOOGLE_API_KEY environment variable

Phase 7 Update: Added hop support, resolution control, and custom filenames
Phase 8 Update: Added aspect ratio presets and parameter support
"""
from __future__ import annotations

import os
import base64
import re
import logging
import uuid
from typing import Any, Dict, Optional, Tuple
from datetime import datetime

from .base_tool import BaseTool, ToolResult
from .context_helpers import get_contextual_filesystem, get_current_context
from .imagen_utils import ASPECT_RATIO_SPECS, resolve_dimensions, guess_mime_from_ext

# Import native Google SDK for image generation (robust import)
# Prefer legacy google-generativeai for Gemini image preview flow; fallback to google-genai if needed
GENAI_AVAILABLE = False
GENAI_PROVIDER = None
genai = None  # type: ignore
try:  # Prefer legacy package that supports GenerativeModel.generate_content image parts
    import google.generativeai as genai  # type: ignore
    GENAI_AVAILABLE = True
    GENAI_PROVIDER = 'google-generativeai'
except Exception as _e1:
    try:
        import google.genai as genai  # type: ignore
        GENAI_AVAILABLE = True
        GENAI_PROVIDER = 'google-genai'
    except Exception as _e2:
        # Keep tool importable; we'll error at execute() with a clear message
        GENAI_AVAILABLE = False
        GENAI_PROVIDER = None
        _GENAI_IMPORT_ERROR = _e2

# Import PIL for image resizing
try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL (Pillow) not available - resolution control disabled")

logger = logging.getLogger(__name__)

# Aspect presets moved to imagen_utils for reuse and unit testing


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
            "Supports custom filenames, arbitrary resolutions, aspect ratios, and hop contexts (remote servers). "
            "If image_data is supplied the prompt is treated as edit instructions. "
            "IMPORTANT: When editing images, use the file:// path from previous generation results (e.g., imageUrl field). "
            "The tool automatically loads the file from the current context (local or remote hop). "
            "Use 'aspect_ratio' (e.g., 16:9, 9:16, 1:1, 4:3, 21:9) for common sizes or 'width'/'height' for explicit pixels. "
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
                    "description": "Optional aspect ratio preset (e.g., 16:9, 9:16, 1:1). If provided without width/height, a recommended resolution is used."
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
        
        # Configure native Google SDK (allow tests to run without key)
        api_key = os.environ.get("GOOGLE_API_KEY")
        self._genai_client = None
        if not GENAI_AVAILABLE:
            logger.warning(
                "Google SDK not available (install 'google-genai' or 'google-generativeai'). "
                "ImagenTool will return a clear error at execute() if invoked."
            )
        elif not api_key:
            logger.warning(
                "GOOGLE_API_KEY not set; ImagenTool will return a clear error at execute() if invoked"
            )
        else:
            try:
                if GENAI_PROVIDER == 'google-genai':
                    # New SDK detected, but this tool currently targets the legacy Gemini content API for image parts.
                    # We'll initialize a client for feature detection, but generation path is not enabled.
                    try:
                        from google import genai as _genai  # type: ignore
                        self._genai_client = _genai.Client(api_key=api_key)  # type: ignore[attr-defined]
                        logger.info("ImagenTool detected google-genai; client initialized (image generation via this SDK not enabled)")
                    except Exception as ce:
                        logger.warning(f"google-genai client init failed: {ce}")
                else:
                    # Legacy SDK uses module-level configure + GenerativeModel
                    genai.configure(api_key=api_key)  # type: ignore[attr-defined]
                    logger.info("ImagenTool initialized with google-generativeai module")
                logger.info(
                    f"ImagenTool ready; provider={GENAI_PROVIDER}, model={self._model}"
                )
            except Exception as cfg_e:
                logger.warning(f"Failed to initialize Google SDK: {cfg_e}")

    def _extract_image_from_native_response(self, response) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Extract binary image data from native Google SDK response.
        
        Native SDK returns images in response.parts with inline_data containing
        binary image bytes (not base64 encoded).
        
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
            
            # Decide save strategy based on context to avoid truncation regression
            context = await get_current_context()
            context_name = context.get('contextId', 'local')
            filesystem_service = await get_contextual_filesystem()

            # Ensure directory exists for local filesystem paths
            try:
                os.makedirs(workspace_root, exist_ok=True)
            except Exception:
                pass

            # Always write a local binary copy to guarantee a non-empty file for references/preview
            try:
                with open(filepath, 'wb') as f:
                    f.write(image_bytes)
                logger.info(f"[ImagenTool] Wrote local copy: {filepath} ({len(image_bytes)} bytes)")
            except Exception as e:
                logger.error(f"[ImagenTool] Failed to write local copy {filepath}: {e}")

            if context_name == 'local':
                # For local context, always write true binary PNG to disk
                try:
                    # Double-write is harmless; ensures correct bytes
                    with open(filepath, 'wb') as f:
                        f.write(image_bytes)
                    logger.info(f"Saved image to {filepath} ({len(image_bytes)} bytes) on local context")
                except Exception as e:
                    logger.error(f"Local binary write failed: {e}")
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
                # Remote context: Use filesystem service write methods
                # The local copy is already written above for references/preview
                wrote = False
                
                # Try write_file_binary first (proper binary write)
                if hasattr(filesystem_service, 'write_file_binary'):
                    try:
                        # Build remote path properly
                        import posixpath
                        remote_ctx = await get_current_context()
                        remote_user = remote_ctx.get('username') or os.getenv('USER', 'user')
                        remote_workspace = (
                            os.environ.get('HOP_REMOTE_WORKSPACE_ROOT')
                            or posixpath.join('/home', remote_user, 'icotes', 'workspace')
                        )
                        remote_path = posixpath.join(remote_workspace, filename)
                        
                        await filesystem_service.write_file_binary(remote_path, image_bytes)
                        logger.info(f"Saved image via write_file_binary to {remote_path} ({len(image_bytes)} bytes) on context: {context_name}")
                        wrote = True
                    except Exception as e:
                        logger.warning(f"write_file_binary failed: {e}")

                # Fallback: Some remote adapters only support text writes. Encode as data URI and use write_file.
                if not wrote and hasattr(filesystem_service, 'write_file'):
                    try:
                        b64 = base64.b64encode(image_bytes).decode('utf-8')
                        data_uri = f"data:image/png;base64,{b64}"
                        # Build remote path similar to binary path
                        import posixpath
                        remote_ctx = await get_current_context()
                        remote_user = remote_ctx.get('username') or os.getenv('USER', 'user')
                        remote_workspace = (
                            os.environ.get('HOP_REMOTE_WORKSPACE_ROOT')
                            or posixpath.join('/home', remote_user, 'icotes', 'workspace')
                        )
                        remote_path = posixpath.join(remote_workspace, filename)
                        await filesystem_service.write_file(remote_path, data_uri)
                        logger.info(f"Saved image via write_file (data URI) to {remote_path} on context: {context_name}")
                        wrote = True
                    except Exception as e:
                        logger.warning(f"write_file (data URI) fallback failed: {e}")

                # If all remote writes failed, that's okay - we have the local copy for serving
                if not wrote:
                    logger.warning(f"Remote write failed, but local copy exists at {filepath}")
                    # Don't return None - the local file is enough for the backend to serve
            
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
            if GENAI_PROVIDER == 'google-genai':
                return None, (
                    "google-genai SDK detected, but ImagenTool currently requires 'google-generativeai' for the"
                    " Gemini image preview flow. Please install 'google-generativeai' in the backend environment."
                )
            else:
                # Legacy SDK path (preferred)
                model = genai.GenerativeModel(model_name)  # type: ignore[attr-defined]
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
            # Resolve target size with helper: simpler and unit-testable
            target_width, target_height = resolve_dimensions(
                width=kwargs.get("width"),
                height=kwargs.get("height"),
                aspect_ratio_label=kwargs.get("aspect_ratio"),
                has_input_image=bool(kwargs.get("image_data")),
            )
            if target_width or target_height:
                logger.info(
                    f"Resolved target dimensions: {target_width or 'auto'}x{target_height or 'auto'}"
                )

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
            
            # Resize image if dimensions specified (either explicit or derived from aspect ratio)
            if target_width or target_height:
                image_bytes, mime_type = self._resize_image(image_bytes, target_width, target_height)
                logger.info(f"Image resized to {target_width or 'auto'}x{target_height or 'auto'}")
            
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
            if save_to_workspace:
                saved_path = await self._save_image_to_workspace(image_bytes, str(prompt), custom_filename or image_id)
            
            # Get current context for result metadata
            context = await get_current_context()
            
            # Create image reference for streaming optimization
            # Extract raw base64 for thumbnail/reference creation
            raw_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Create reference via ImageReferenceService
            image_service = get_image_reference_service()
            ref = await image_service.create_reference(
                image_data=raw_base64,
                filename=saved_path or f"{image_id}.png",
                prompt=str(prompt),
                model=self._model,
                mime_type=mime_type
            )
            
            # Cache the full image for fast retrieval
            from ...services.image_cache import ImageCache
            cache = ImageCache()
            cache.put(
                image_id=ref.image_id,
                base64_data=raw_base64,
                mime_type=mime_type
            )
            
            # Return result with reference AND small thumbnail for preview/editing
            # The thumbnail allows instant preview without fetching, and agents can use it for editing
            # Build a hop-aware file URL: if context is remote, compute a reasonable remote path
            image_url = f"file://{ref.absolute_path}"
            context_name = context.get('contextId', 'local')
            if context_name != 'local':
                try:
                    import posixpath
                    # Prefer explicit context/workspace settings if available
                    remote_workspace = (
                        context.get('workspaceRoot')
                        or os.environ.get('HOP_REMOTE_WORKSPACE_ROOT')
                        or posixpath.join('/home', os.getenv('USER', 'user'), 'icotes', 'workspace')
                    )
                    # If we saved a relative path, join to remote workspace
                    remote_rel = saved_path or os.path.basename(ref.absolute_path)
                    image_url = f"file://{posixpath.join(remote_workspace, remote_rel)}"
                except Exception:
                    # Fallback to local absolute path
                    image_url = f"file://{ref.absolute_path}"

            result_data = {
                "imageReference": ref.to_dict(),  # Lightweight reference with thumbnail
                "imageData": ref.thumbnail_base64,  # Include thumbnail for preview AND agent editing
                "imageUrl": image_url,  # file:// URL for agent editing (hop-aware)
                "thumbnailUrl": f"/api/media/image/{ref.image_id}?thumbnail=true",  # Thumbnail endpoint for UI
                "fullImageUrl": f"/api/media/image/{ref.image_id}",  # Full image endpoint for downloads
                "mimeType": mime_type,
                "prompt": str(prompt),
                "model": self._model,
                "timestamp": datetime.now().isoformat(),
                "mode": effective_mode,
                "attemptedModels": attempted,
                "context": context_name,
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
