"""
Atlas Cloud Text-to-Video Tool for agents

Generates videos from text descriptions using Atlas Cloud's unified API.
Supports multiple video generation models (Seedance, Kling, Veo, Wan, etc.).
Follows existing tool patterns with hop-aware workspace saving.

Requires: ATLASCLOUD_API_KEY environment variable

References:
- https://www.atlascloud.ai/docs/openapi-index
- https://www.atlascloud.ai/docs/more-models/bytedance/seedance-v1-lite-t2v-480p/generateVideo
"""

from __future__ import annotations

import os
import re
import logging
from typing import Any, Optional, Tuple
from datetime import datetime

import httpx

from ..base_tool import BaseTool, ToolResult
from ..context_helpers import get_contextual_filesystem, get_current_context
from .client import AtlasCloudClient
from .exceptions import AtlasCloudError, AtlasCloudTimeoutError

logger = logging.getLogger(__name__)

# Available models for text-to-video (sorted by cost)
TEXT_TO_VIDEO_MODELS = {
    # ByteDance Seedance (cheapest)
    "bytedance/seedance-v1-lite-t2v-480p": {
        "description": "Fastest, cheapest text-to-video (480p, $0.04/sec)",
        "resolution": "480p",
        "tier": "lite",
        "price_per_sec": 0.04,
    },
    "bytedance/seedance-v1-lite-t2v-720p": {
        "description": "Fast text-to-video (720p, $0.04/sec)",
        "resolution": "720p",
        "tier": "lite",
        "price_per_sec": 0.04,
    },
    "bytedance/seedance-v1-lite-t2v-1080p": {
        "description": "Fast text-to-video (1080p, $0.04/sec)",
        "resolution": "1080p",
        "tier": "lite",
        "price_per_sec": 0.04,
    },
    "bytedance/seedance-v1-pro-t2v-480p": {
        "description": "Pro quality text-to-video (480p, ~$0.22/sec)",
        "resolution": "480p",
        "tier": "pro",
        "price_per_sec": 0.22,
    },
    "bytedance/seedance-v1-pro-t2v-720p": {
        "description": "Pro quality text-to-video (720p, ~$0.22/sec)",
        "resolution": "720p",
        "tier": "pro",
        "price_per_sec": 0.22,
    },
    "bytedance/seedance-v1-pro-t2v-1080p": {
        "description": "Pro quality text-to-video (1080p, ~$0.22/sec)",
        "resolution": "1080p",
        "tier": "pro",
        "price_per_sec": 0.22,
    },
    # Alibaba Wan (good quality/price balance)
    "alibaba/wan-2.5/text-to-video": {
        "description": "Alibaba Wan 2.5 text-to-video with audio (~$0.25/sec)",
        "resolution": "720p/1080p",
        "tier": "standard",
        "price_per_sec": 0.25,
    },
    "alibaba/wan-2.6/text-to-video": {
        "description": "Alibaba Wan 2.6 text-to-video with audio (~$0.075/sec)",
        "resolution": "720p/1080p",
        "tier": "standard",
        "price_per_sec": 0.075,
    },
}

# Supported aspect ratios
ASPECT_RATIOS = ["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"]


class AtlasCloudTextToVideoTool(BaseTool):
    """
    Generate videos from text descriptions using Atlas Cloud API.
    
    Capabilities:
        - Text-to-video with multiple model options
        - Configurable duration (5-10 seconds)
        - Multiple aspect ratios (16:9, 1:1, etc.)
        - Save to workspace with custom filenames
        - Hop-aware for remote server support
        - Automatic polling for completion
    """
    
    def __init__(self):
        super().__init__()
        self.name = "text_to_video"
        self.description = (
            "Generate a video from a text description using Atlas Cloud AI models. "
            "Default model: 'bytedance/seedance-v1-lite-t2v-480p' ($0.04/sec - cheapest). "
            "Only use other models if user explicitly requests them (2-6x more expensive). "
            "Generated videos are saved to workspace/videos/ and can be played in the media player. "
            "Generation takes 2-3 minutes."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "Detailed text description of the video to generate (max 2000 characters). "
                        "Be specific about scene details, actions, camera movements, lighting, and style. "
                        "Example: 'A serene sunset over snow-capped mountains, with gentle clouds drifting by. "
                        "Camera slowly pans right to reveal a peaceful lake reflecting the orange sky.'"
                    )
                },
                "model": {
                    "type": "string",
                    "enum": list(TEXT_TO_VIDEO_MODELS.keys()),
                    "description": (
                        "Video model. Default: 'bytedance/seedance-v1-lite-t2v-480p' ($0.04/sec). "
                        "Only change if user explicitly requests a different model."
                    )
                },
                "duration": {
                    "type": "integer",
                    "description": "Video duration in seconds (5-10). Default: 5 seconds. Longer = higher cost.",
                    "minimum": 5,
                    "maximum": 10
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ASPECT_RATIOS,
                    "description": (
                        "Video aspect ratio. Default: '16:9' (widescreen). "
                        "Options: 21:9 (ultrawide), 16:9 (widescreen), 4:3 (standard), "
                        "1:1 (square), 3:4 (vertical), 9:16 (mobile portrait)"
                    )
                },
                "seed": {
                    "type": "integer",
                    "description": (
                        "Random seed for reproducibility. Use the same seed with same prompt "
                        "to generate similar videos. Default: -1 (random)"
                    )
                },
                "filename": {
                    "type": "string",
                    "description": (
                        "Optional custom filename (without extension). "
                        "If not provided, auto-generates from prompt and timestamp."
                    )
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum wait time in seconds. Default: 300 (5 minutes)",
                    "minimum": 60,
                    "maximum": 600
                }
            },
            "required": ["prompt"]
        }
        
        # Initialize client lazily
        self._client: Optional[AtlasCloudClient] = None
    
    def _get_client(self) -> AtlasCloudClient:
        """Get or create Atlas Cloud client lazily."""
        if self._client is not None:
            return self._client
        
        api_key = os.environ.get("ATLASCLOUD_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ATLASCLOUD_API_KEY environment variable not set. "
                "Get your API key from https://console.atlascloud.ai/settings"
            )
        
        self._client = AtlasCloudClient(api_key=api_key)
        logger.info("Atlas Cloud client initialized")
        return self._client
    
    async def _download_video(self, video_url: str) -> bytes:
        """
        Download video from URL.
        
        Args:
            video_url: URL of the generated video
            
        Returns:
            Video bytes
            
        Raises:
            AtlasCloudError: Download failed
        """
        try:
            # Check if this is an API endpoint that needs authentication
            needs_auth = '/api/' in video_url or '/model/' in video_url or '/prediction/' in video_url
            
            if needs_auth:
                # Use the authenticated client - _get_client is synchronous
                client = self._get_client()
                await client._ensure_client()
                response = await client._client.get(video_url)
                response.raise_for_status()
                return response.content
            else:
                # Direct file URL, no auth needed
                async with httpx.AsyncClient(timeout=60.0) as http_client:
                    response = await http_client.get(video_url)
                    response.raise_for_status()
                    return response.content
        except Exception as e:
            logger.error(f"Failed to download video from {video_url}: {e}")
            raise AtlasCloudError(f"Video download failed: {e}") from e
    
    async def _save_video_to_workspace(
        self,
        video_bytes: bytes,
        prompt: str,
        model: str,
        custom_filename: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """
        Save video bytes to workspace folder (hop-aware).
        
        Args:
            video_bytes: Binary video data
            prompt: Original prompt (used for auto-generated filename)
            model: Model name (included in filename)
            custom_filename: Optional custom filename (without extension)
            
        Returns:
            Tuple of (relative_path, absolute_path) if successful, None otherwise.
        """
        try:
            # Determine file extension (always .mp4 for video)
            extension = ".mp4"
            
            # Generate filename
            if custom_filename:
                # Sanitize custom filename
                safe_name = re.sub(r'[^\w\s-]', '', custom_filename).strip().replace(' ', '_')
                filename = f"{safe_name}{extension}"
            else:
                # Auto-generate from prompt and timestamp
                timestamp = int(datetime.now().timestamp())
                # Take first 30 chars of prompt for filename
                safe_prompt = re.sub(r'[^\w\s-]', '', prompt[:30]).strip().replace(' ', '_')
                if not safe_prompt:
                    safe_prompt = "video"
                
                # Extract model short name (e.g., "seedance-lite-480p")
                model_short = model.split('/')[-1] if '/' in model else model
                model_short = model_short.replace('bytedance-', '').replace('alibaba-', '')
                
                filename = f"ttv_{safe_prompt}_{model_short}_{timestamp}{extension}"
            
            # Get context for hop-aware saving
            context = await get_current_context()
            context_name = context.get('contextId', 'local')
            filesystem_service = await get_contextual_filesystem()
            
            # Determine workspace root based on context
            if context_name == 'local':
                workspace_root = getattr(filesystem_service, 'root_path', None)
                if not workspace_root:
                    workspace_root = os.environ.get('WORKSPACE_ROOT') or os.getcwd()
                
                # Ensure videos directory exists
                videos_dir = os.path.join(workspace_root, 'videos')
                os.makedirs(videos_dir, exist_ok=True)
                
                filepath = os.path.join(videos_dir, filename)
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
            
            logger.info(
                f"[AtlasCloudTTV] Target context: {context_name}, "
                f"filepath: {filepath}"
            )
            
            if context_name == 'local':
                # Write directly to local filesystem
                try:
                    with open(filepath, 'wb') as f:
                        f.write(video_bytes)
                    logger.info(
                        f"[AtlasCloudTTV] Saved video to {filepath} "
                        f"({len(video_bytes)} bytes)"
                    )
                except Exception as e:
                    logger.error(f"[AtlasCloudTTV] Local write failed: {e}")
                    return None
            else:
                # Remote context: Write via SFTP
                try:
                    if hasattr(filesystem_service, 'write_file_binary'):
                        # Ensure remote directory exists
                        if hasattr(filesystem_service, 'create_directory'):
                            await filesystem_service.create_directory(videos_dir)
                        await filesystem_service.write_file_binary(filepath, video_bytes)
                        logger.info(
                            f"[AtlasCloudTTV] Saved video to remote: {filepath}"
                        )
                    else:
                        logger.error(
                            "[AtlasCloudTTV] Remote filesystem doesn't support binary write"
                        )
                        return None
                except Exception as e:
                    logger.error(f"[AtlasCloudTTV] Remote write failed: {e}")
                    return None
            
            # Return relative and absolute paths
            relative_path = f"videos/{filename}"
            return (relative_path, filepath)
            
        except Exception as e:
            logger.error(f"[AtlasCloudTTV] Failed to save video: {e}")
            return None
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute text-to-video generation.
        
        Args:
            prompt: Text description of video
            model: Model to use (default: bytedance/seedance-v1-lite-t2v-480p)
            duration: Video duration in seconds (default: 5)
            aspect_ratio: Video aspect ratio (default: 16:9)
            seed: Random seed (default: -1)
            filename: Optional custom filename
            timeout: Max wait time in seconds (default: 300)
            
        Returns:
            ToolResult with video file path or error
        """
        prompt = kwargs.get("prompt")
        if not prompt:
            return ToolResult(
                success=False,
                data=None,
                error="Missing required parameter: prompt"
            )
        
        # Validate prompt length
        if len(prompt) > 2000:
            return ToolResult(
                success=False,
                data=None,
                error=f"Prompt too long ({len(prompt)} chars). Maximum is 2000 characters."
            )
        
        # Get parameters with defaults
        model = kwargs.get("model", "bytedance/seedance-v1-lite-t2v-480p")
        duration = kwargs.get("duration", 5)
        aspect_ratio = kwargs.get("aspect_ratio", "16:9")
        seed = kwargs.get("seed", -1)
        filename = kwargs.get("filename")
        timeout = kwargs.get("timeout", 300)
        
        # Validate model
        if model not in TEXT_TO_VIDEO_MODELS:
            return ToolResult(
                success=False,
                data=None,
                error=f"Invalid model '{model}'. Available models: {list(TEXT_TO_VIDEO_MODELS.keys())}"
            )
        
        # Validate aspect ratio
        if aspect_ratio not in ASPECT_RATIOS:
            return ToolResult(
                success=False,
                data=None,
                error=f"Invalid aspect_ratio '{aspect_ratio}'. Available: {ASPECT_RATIOS}"
            )
        
        try:
            client = self._get_client()
            
            logger.info(
                f"[AtlasCloudTTV] Starting video generation: "
                f"model={model}, duration={duration}s, aspect_ratio={aspect_ratio}"
            )
            
            # Estimate cost
            model_info = TEXT_TO_VIDEO_MODELS[model]
            estimated_cost = model_info["price_per_sec"] * duration
            logger.info(f"[AtlasCloudTTV] Estimated cost: ${estimated_cost:.2f}")
            
            # Generate video (with polling)
            result = await client.generate_text_to_video(
                prompt=prompt,
                model=model,
                duration=duration,
                aspect_ratio=aspect_ratio,
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
            
            logger.info(f"[AtlasCloudTTV] Video generated: {video_url}")
            
            # Download video
            logger.info("[AtlasCloudTTV] Downloading video...")
            video_bytes = await self._download_video(video_url)
            logger.info(f"[AtlasCloudTTV] Downloaded {len(video_bytes)} bytes")
            
            # Save to workspace
            paths = await self._save_video_to_workspace(
                video_bytes,
                prompt,
                model,
                filename
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
                    "file_path": relative_path,
                    "absolute_path": absolute_path,
                    "video_url": video_url,
                    "model": model,
                    "duration": duration,
                    "aspect_ratio": aspect_ratio,
                    "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                    "estimated_cost": f"${estimated_cost:.2f}",
                    "file_size_bytes": len(video_bytes),
                },
                error=None
            )
            
        except AtlasCloudTimeoutError as e:
            logger.error(f"[AtlasCloudTTV] Timeout: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Video generation timed out after {timeout} seconds. The video may still be generating - check Atlas Cloud dashboard."
            )
        except AtlasCloudError as e:
            logger.error(f"[AtlasCloudTTV] API error: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Atlas Cloud API error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"[AtlasCloudTTV] Unexpected error: {e}", exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                error=f"Unexpected error during video generation: {str(e)}"
            )
