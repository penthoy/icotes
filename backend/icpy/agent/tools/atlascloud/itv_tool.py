"""
Image-to-Video Generation Tool for Atlas Cloud API

Converts images into videos using AI models via Atlas Cloud.
Supports workspace files, URLs, and base64 images.
"""

import os
import base64
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

import httpx
from PIL import Image
from io import BytesIO

from ..base_tool import BaseTool, ToolResult
from ..context_helpers import get_contextual_filesystem, get_current_context
from .client import AtlasCloudClient
from .exceptions import (
    AtlasCloudError,
    AtlasCloudAuthError,
    AtlasCloudTimeoutError,
)

logger = logging.getLogger(__name__)

# Image-to-Video model registry with pricing
IMAGE_TO_VIDEO_MODELS = {
    "bytedance/seedance-v1-lite-i2v-480p": {
        "name": "Seedance Lite 480p (cheapest)",
        "price_per_sec": 0.04,
        "resolution": "480p",
        "duration_range": (5, 10),
    },
    "bytedance/seedance-v1-lite-i2v-720p": {
        "name": "Seedance Lite 720p",
        "price_per_sec": 0.04,
        "resolution": "720p",
        "duration_range": (5, 10),
    },
    "bytedance/seedance-v1-pro-i2v-480p": {
        "name": "Seedance Pro 480p",
        "price_per_sec": 0.22,
        "resolution": "480p",
        "duration_range": (5, 10),
    },
    "bytedance/seedance-v1-pro-i2v-720p": {
        "name": "Seedance Pro 720p",
        "price_per_sec": 0.22,
        "resolution": "720p",
        "duration_range": (5, 10),
    },
    "bytedance/seedance-v1-pro-i2v-1080p": {
        "name": "Seedance Pro 1080p",
        "price_per_sec": 0.22,
        "resolution": "1080p",
        "duration_range": (5, 10),
    },
    "kling/v2.5/image-to-video": {
        "name": "Kling v2.5",
        "price_per_sec": 0.10,
        "resolution": "1080p",
        "duration_range": (5, 10),
    },
}

# Supported aspect ratios
ASPECT_RATIOS = ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"]

# Image validation constraints
MAX_IMAGE_SIZE_MB = 10
MIN_IMAGE_RESOLUTION = 300
MAX_IMAGE_RESOLUTION = 4096


class AtlasCloudImageToVideoTool(BaseTool):
    """
    Agent tool for generating videos from images using Atlas Cloud API.
    
    Supports:
    - Workspace file paths (hop-aware)
    - HTTP/HTTPS URLs
    - Base64-encoded images
    - Image validation (format, size, resolution)
    - Video customization (duration, aspect ratio, prompt)
    """
    
    def __init__(self):
        """
        Create and configure the Atlas Cloud image-to-video tool instance.
        
        Sets the tool name, user-facing description, and JSON-schema parameters for image-to-video generation (including image source, prompt, model, duration, aspect_ratio, last_image, seed, filename, and timeout). Initializes the internal AtlasCloudClient cache to None and logs tool initialization.
        """
        super().__init__()
        self.name = "image_to_video"
        self.description = (
            "Generate videos from images using Atlas Cloud AI models. "
            "Supports workspace files, URLs, and base64 images. "
            "Default model: 'bytedance/seedance-v1-lite-i2v-480p' ($0.04/sec). "
            "Only change model if user explicitly requests. "
            "Generated videos are saved to workspace/videos/ and can be played in the media player. "
            "Generation takes 2-3 minutes."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "image": {
                    "type": "string",
                    "description": (
                        "Image source: workspace file path (e.g., 'images/photo.jpg'), "
                        "HTTP/HTTPS URL, or base64-encoded image data"
                    )
                },
                "prompt": {
                    "type": "string",
                    "description": (
                        "Optional text prompt to guide video generation. "
                        "Describes desired motion or effects. Max 2000 characters."
                    )
                },
                "model": {
                    "type": "string",
                    "enum": list(IMAGE_TO_VIDEO_MODELS.keys()),
                    "description": (
                        "Video model. Default: 'bytedance/seedance-v1-lite-i2v-480p' ($0.04/sec). "
                        "Only change if user explicitly requests a different model."
                    )
                },
                "duration": {
                    "type": "integer",
                    "description": "Video duration in seconds (5-10). Default: 5",
                    "minimum": 5,
                    "maximum": 10
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ASPECT_RATIOS,
                    "description": f"Video aspect ratio. Options: {', '.join(ASPECT_RATIOS)}. Default: 16:9"
                },
                "last_image": {
                    "type": "string",
                    "description": (
                        "Optional end frame image for video interpolation. "
                        "Same format options as 'image' parameter."
                    )
                },
                "seed": {
                    "type": "integer",
                    "description": "Random seed for reproducibility. Default: random"
                },
                "filename": {
                    "type": "string",
                    "description": "Custom filename (without extension). Default: auto-generated"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Max wait time in seconds. Default: 300"
                }
            },
            "required": ["image"]
        }
        self._client: Optional[AtlasCloudClient] = None
        logger.info("Atlas Cloud Image-to-Video tool initialized")
    
    def _get_client(self) -> AtlasCloudClient:
        """
        Return the cached AtlasCloudClient, creating it from ATLASCLOUD_API_KEY if necessary.
        
        Returns:
            AtlasCloudClient: The initialized Atlas Cloud client instance.
        
        Raises:
            AtlasCloudAuthError: If `ATLASCLOUD_API_KEY` is not set in the environment.
        """
        if self._client is None:
            api_key = os.getenv("ATLASCLOUD_API_KEY")
            if not api_key:
                raise AtlasCloudAuthError(
                    "ATLASCLOUD_API_KEY environment variable not set. "
                    "Get your API key from https://console.atlascloud.ai/settings"
                )
            self._client = AtlasCloudClient(api_key=api_key)
        return self._client
    
    async def _process_image(
        self,
        image: str,
        hop_session: Optional[str] = None
    ) -> str:
        """
        Convert an image input (workspace path, HTTP/HTTPS URL, or base64 data URL) into a form ready for the Atlas Cloud API.
        
        Parameters:
            image (str): Image source; can be an HTTP/HTTPS URL, a `data:image/...;base64,...` data URL, or a workspace file path (optionally prefixed with `local:`).
            hop_session (Optional[str]): Optional hop session identifier used for remote workspace file access.
        
        Returns:
            str: Either the original HTTP/HTTPS URL or a `data:`-URL containing the image encoded as base64 suitable for API submission.
        
        Raises:
            ValueError: If the workspace file is not found, exceeds size limits, has unsupported format, or its resolution is outside allowed bounds; also raised for invalid base64 image data.
        """
        # If it's a URL, return as-is
        if image.startswith(("http://", "https://")):
            logger.info(f"Using image URL: {image[:50]}...")
            return image
        
        # If it's already base64, validate and return
        if image.startswith("data:image/"):
            logger.info("Using provided base64 image")
            self._validate_base64_image(image)
            return image
        
        # Otherwise, treat as workspace file path
        logger.info(f"Reading image from workspace: {image}")
        
        # Strip local: prefix if present
        clean_image = image.replace('local:', '') if image.startswith('local:') else image
        
        # Get context-aware filesystem and current context
        filesystem_service = await get_contextual_filesystem()
        context = await get_current_context()
        context_name = context.get('contextId', 'local')
        
        # Build full path
        if context_name == 'local':
            # Local filesystem
            workspace_root = getattr(filesystem_service, 'root_path', None)
            if not workspace_root:
                workspace_root = os.environ.get('WORKSPACE_ROOT') or os.getcwd()
            
            # If path is already absolute, use it as-is, otherwise join with workspace root
            if os.path.isabs(clean_image):
                full_path = Path(clean_image)
            else:
                full_path = Path(workspace_root) / clean_image
        else:
            # Remote context
            full_path = Path(clean_image)
        
        if not full_path.exists():
            raise ValueError(f"Image file not found: {image} (resolved to {full_path})")
        
        # Validate file size
        file_size_mb = full_path.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_IMAGE_SIZE_MB:
            raise ValueError(
                f"Image file too large: {file_size_mb:.1f}MB (max {MAX_IMAGE_SIZE_MB}MB)"
            )
        
        # Read and validate image
        with open(full_path, 'rb') as f:
            image_bytes = f.read()
        
        # Validate image with PIL
        try:
            img = Image.open(BytesIO(image_bytes))
            width, height = img.size
            
            # Validate resolution
            if width < MIN_IMAGE_RESOLUTION or height < MIN_IMAGE_RESOLUTION:
                raise ValueError(
                    f"Image too small: {width}x{height} "
                    f"(minimum {MIN_IMAGE_RESOLUTION}x{MIN_IMAGE_RESOLUTION})"
                )
            
            if width > MAX_IMAGE_RESOLUTION or height > MAX_IMAGE_RESOLUTION:
                raise ValueError(
                    f"Image too large: {width}x{height} "
                    f"(maximum {MAX_IMAGE_RESOLUTION}x{MAX_IMAGE_RESOLUTION})"
                )
            
            # Validate format
            if img.format.lower() not in ['jpeg', 'jpg', 'png']:
                raise ValueError(
                    f"Unsupported image format: {img.format}. "
                    "Supported formats: JPEG, PNG"
                )
            
            logger.info(f"Image validated: {width}x{height}, {img.format}, {file_size_mb:.1f}MB")
            
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Invalid image file: {e}")
        
        # Convert to base64
        base64_str = base64.b64encode(image_bytes).decode('utf-8')
        mime_type = "image/jpeg" if img.format.lower() in ['jpeg', 'jpg'] else "image/png"
        data_url = f"data:{mime_type};base64,{base64_str}"
        
        logger.info(f"Image converted to base64: {len(base64_str)} chars")
        return data_url
    
    def _validate_base64_image(self, data_url: str):
        """
        Validate that a data URL contains a base64-encoded image and that the image meets minimum resolution requirements.
        
        This function expects a data URL containing ';base64,' and verifies the decoded image can be parsed and has width and height each greater than or equal to MIN_IMAGE_RESOLUTION.
        
        Parameters:
            data_url (str): A data URL with a base64-encoded image (e.g., "data:image/png;base64,...").
        
        Raises:
            ValueError: If the data URL is malformed, the base64 cannot be decoded or parsed as an image, or the image dimensions are smaller than MIN_IMAGE_RESOLUTION.
        """
        try:
            # Extract base64 data
            if ';base64,' in data_url:
                base64_data = data_url.split(';base64,')[1]
            else:
                raise ValueError("Invalid data URL format")
            
            # Decode and validate with PIL
            image_bytes = base64.b64decode(base64_data)
            img = Image.open(BytesIO(image_bytes))
            
            width, height = img.size
            if width < MIN_IMAGE_RESOLUTION or height < MIN_IMAGE_RESOLUTION:
                raise ValueError(
                    f"Image too small: {width}x{height} "
                    f"(minimum {MIN_IMAGE_RESOLUTION}x{MIN_IMAGE_RESOLUTION})"
                )
            
        except Exception as e:
            raise ValueError(f"Invalid base64 image: {e}")
    
    async def _download_video(self, video_url: str) -> bytes:
        """
        Download video content from the given URL.
        
        Returns:
            bytes: Raw video bytes downloaded from the URL.
        
        Raises:
            AtlasCloudError: If the HTTP request fails or the response has an error status.
        """
        try:
            # Determine if URL needs authentication
            if any(pattern in video_url for pattern in ['/api/', '/model/', '/prediction/']):
                # API endpoint - use authenticated client
                client = self._get_client()
                await client._ensure_client()
                response = await client._client.get(video_url)
            else:
                # Direct file URL - no auth needed
                async with httpx.AsyncClient() as http_client:
                    response = await http_client.get(video_url)
            
            response.raise_for_status()
            return response.content
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to download video from {video_url}: {e}")
            raise AtlasCloudError(f"Video download failed: {e}") from e
    
    async def _save_video_to_workspace(
        self,
        video_bytes: bytes,
        image_name: str,
        model: str,
        filename: Optional[str] = None,
        hop_session: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """
        Save the provided video bytes into the workspace's videos/ directory and return its paths.
        
        Parameters:
            video_bytes (bytes): Raw video file content to write.
            image_name (str): Source image name or path used to generate a default filename when `filename` is not provided.
            model (str): Model identifier used to include a short model name in the default filename.
            filename (Optional[str]): Optional custom filename (with or without `.mp4` extension); if omitted a timestamped name is generated.
            hop_session (Optional[str]): Optional hop/remote session identifier used when saving to a remote workspace context.
        
        Returns:
            Optional[Tuple[str, str]]: Tuple (relative_path, absolute_path) on success, where `relative_path` is "videos/{filename}" and `absolute_path` is the saved file's full path; returns `None` on failure.
        """
        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Extract base name from image path
                base_name = Path(image_name).stem if '/' in image_name or '\\' in image_name else image_name.split('.')[0]
                model_short = model.split('/')[-1].replace('-', '_')
                filename = f"{base_name}_i2v_{model_short}_{timestamp}"
            
            # Ensure .mp4 extension
            if not filename.endswith('.mp4'):
                filename = f"{filename}.mp4"
            
            relative_path = f"videos/{filename}"
            
            # Get context for hop-aware saving
            context = await get_current_context()
            context_name = context.get('contextId', 'local')
            filesystem_service = await get_contextual_filesystem()
            
            # Determine workspace root based on context
            if context_name == 'local':
                workspace_root = getattr(filesystem_service, 'root_path', None)
                if not workspace_root:
                    workspace_root = os.environ.get('WORKSPACE_ROOT') or os.getcwd()
                
                # Build absolute path
                filepath = os.path.join(workspace_root, 'videos', filename)
                
                # Ensure videos directory exists
                videos_dir = os.path.join(workspace_root, 'videos')
                os.makedirs(videos_dir, exist_ok=True)
                
                # Write directly to local filesystem
                try:
                    with open(filepath, 'wb') as f:
                        f.write(video_bytes)
                    logger.info(
                        f"[AtlasCloudITV] Saved video to {filepath} "
                        f"({len(video_bytes)} bytes)"
                    )
                except Exception as e:
                    logger.error(f"[AtlasCloudITV] Local write failed: {e}")
                    return None
            else:
                # Remote context via hop
                import posixpath
                remote_user = context.get('username') or os.getenv('USER', 'user')
                workspace_root = (
                    context.get('workspaceRoot')
                    or context.get('cwd')
                    or os.environ.get('HOP_REMOTE_WORKSPACE_ROOT')
                    or posixpath.join('/home', remote_user, 'icotes')
                )
                videos_dir = posixpath.join(workspace_root, 'videos')
                filepath = posixpath.join(videos_dir, filename)
                
                # Remote context: Write via filesystem service
                try:
                    # Ensure remote directory exists
                    await filesystem_service.create_directory(videos_dir)
                    
                    # Write binary file
                    if hasattr(filesystem_service, 'write_file_binary'):
                        await filesystem_service.write_file_binary(filepath, video_bytes)
                    else:
                        # Fallback: base64 encode and write as text
                        import base64
                        encoded = base64.b64encode(video_bytes).decode('utf-8')
                        await filesystem_service.write_file(filepath, encoded)
                    
                    logger.info(
                        f"[AtlasCloudITV] Saved video to remote: {filepath}"
                    )
                except Exception as e:
                    logger.error(f"[AtlasCloudITV] Remote write failed: {e}")
                    return None
            
            logger.info(
                f"[AtlasCloudITV] Video saved to {relative_path} "
                f"(context: {context_name})"
            )
            
            # Return relative and absolute paths
            return (relative_path, filepath)
        
        except Exception as e:
            logger.error(f"[AtlasCloudITV] Failed to save video: {e}")
            return None
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        Generate a video from an input image using Atlas Cloud and save the result to the workspace.
        
        Processes the provided image source (workspace path, HTTP/HTTPS URL, or base64 data URL), validates inputs, submits an image-to-video generation request to Atlas Cloud, waits for completion, downloads the resulting MP4, and writes it to the workspace (local or remote). Returns a structured ToolResult describing success or failure.
        
        Parameters:
            image (str): Required image source (workspace path, http(s) URL, or data URL). Must be provided.
            prompt (str, optional): Text prompt for generation (max 2000 characters).
            model (str, optional): Model identifier (defaults to "bytedance/seedance-v1-lite-i2v-480p"); must be one of IMAGE_TO_VIDEO_MODELS keys.
            duration (int, optional): Video duration in seconds (5–10, default 5).
            aspect_ratio (str, optional): Aspect ratio (e.g., "16:9", default "16:9"); must be one of ASPECT_RATIOS.
            last_image (str, optional): Optional end-frame image (same formats as `image`).
            seed (int, optional): Optional randomness seed for generation.
            filename (str, optional): Optional custom output filename (without extension); otherwise a name is generated.
            timeout (int, optional): Maximum wait time in seconds for generation (default 300).
            hop_session (str, optional): Optional hop/session identifier for remote workspace operations.
        
        Returns:
            ToolResult: On success, `data` contains keys:
                - video_path: relative workspace path to the saved video (e.g., "videos/…").
                - absolute_path: absolute path to the saved video in the current context.
                - request_id: Atlas Cloud request identifier.
                - model: model used.
                - duration: duration in seconds.
                - aspect_ratio: aspect ratio used.
                - cost_estimate: human-readable estimated cost (e.g., "$0.25").
                - message: success message.
            On failure, `success` is False and `error` contains a descriptive message.
        """
        # Extract parameters
        image = kwargs.get("image")
        if not image:
            return ToolResult(
                success=False,
                data=None,
                error="Parameter 'image' is required"
            )
        
        prompt = kwargs.get("prompt")
        if prompt and len(prompt) > 2000:
            return ToolResult(
                success=False,
                data=None,
                error=f"Prompt too long: {len(prompt)} chars (max 2000)"
            )
        
        model = kwargs.get("model", "bytedance/seedance-v1-lite-i2v-480p")
        if model not in IMAGE_TO_VIDEO_MODELS:
            return ToolResult(
                success=False,
                data=None,
                error=f"Invalid model: {model}. Choose from: {list(IMAGE_TO_VIDEO_MODELS.keys())}"
            )
        
        duration = kwargs.get("duration", 5)
        aspect_ratio = kwargs.get("aspect_ratio", "16:9")
        last_image = kwargs.get("last_image")
        seed = kwargs.get("seed")
        filename = kwargs.get("filename")
        timeout = kwargs.get("timeout", 300)
        hop_session = kwargs.get("hop_session")
        
        try:
            # Process image input
            logger.info(f"[AtlasCloudITV] Processing image: {image[:50]}...")
            processed_image = await self._process_image(image, hop_session)
            
            # Process last_image if provided
            processed_last_image = None
            if last_image:
                logger.info(f"[AtlasCloudITV] Processing end frame: {last_image[:50]}...")
                processed_last_image = await self._process_image(last_image, hop_session)
            
            # Get client
            client = self._get_client()
            
            logger.info(
                f"[AtlasCloudITV] Starting video generation: "
                f"model={model}, duration={duration}s, aspect_ratio={aspect_ratio}"
            )
            
            # Estimate cost
            model_info = IMAGE_TO_VIDEO_MODELS[model]
            estimated_cost = model_info["price_per_sec"] * duration
            logger.info(f"[AtlasCloudITV] Estimated cost: ${estimated_cost:.2f}")
            
            # Generate video (with polling)
            result = await client.generate_image_to_video(
                image=processed_image,
                prompt=prompt,
                model=model,
                duration=duration,
                aspect_ratio=aspect_ratio,
                last_image=processed_last_image,
                seed=seed,
                wait_for_completion=True,
                timeout=timeout,
                poll_interval=2.0,
            )
            
            if not result.is_complete:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Video generation incomplete. Status: {result.status}"
                )
            
            video_url = result.video_url
            if not video_url:
                return ToolResult(
                    success=False,
                    data={"status": result.status},
                    error=f"Video generation completed but no output URL found. Status: {result.status}"
                )
            
            logger.info(f"[AtlasCloudITV] Video generated: {video_url}")
            
            # Download video
            logger.info(f"[AtlasCloudITV] Downloading video...")
            video_bytes = await self._download_video(video_url)
            logger.info(f"[AtlasCloudITV] Downloaded {len(video_bytes)} bytes")
            
            # Save to workspace
            paths = await self._save_video_to_workspace(
                video_bytes,
                image,
                model,
                filename,
                hop_session
            )
            
            if not paths:
                return ToolResult(
                    success=False,
                    data=None,
                    error="Failed to save video to workspace"
                )
            
            relative_path, absolute_path = paths
            
            # Build success response
            return ToolResult(
                success=True,
                data={
                    "video_path": relative_path,
                    "absolute_path": absolute_path,
                    "request_id": result.id,
                    "model": model,
                    "duration": duration,
                    "aspect_ratio": aspect_ratio,
                    "cost_estimate": f"${estimated_cost:.2f}",
                    "message": f"Video generated successfully and saved to {relative_path}"
                },
                error=None
            )
            
        except AtlasCloudTimeoutError as e:
            logger.error(f"[AtlasCloudITV] Timeout: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Video generation timed out after {timeout}s. Try again or increase timeout."
            )
        
        except AtlasCloudError as e:
            logger.error(f"[AtlasCloudITV] API error: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Atlas Cloud API error: {str(e)}"
            )
        
        except Exception as e:
            logger.error(f"[AtlasCloudITV] Unexpected error: {e}", exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                error=f"Unexpected error: {str(e)}"
            )