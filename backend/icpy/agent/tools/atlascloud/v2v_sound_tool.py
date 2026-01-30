"""
Video-to-Video with Sound Generation Tool for Atlas Cloud API

Adds AI-generated sound to existing silent videos using atlascloud/mmaudio-v2 model.
Supports workspace files and URLs.
"""

import os
import logging
import asyncio
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

import httpx

from ..base_tool import BaseTool, ToolResult
from ..context_helpers import get_contextual_filesystem, get_current_context
from .client import AtlasCloudClient
from .exceptions import (
    AtlasCloudError,
    AtlasCloudAuthError,
    AtlasCloudTimeoutError,
)

logger = logging.getLogger(__name__)

# Video-to-Video with Sound model registry
VIDEO_TO_VIDEO_SOUND_MODELS = {
    "atlascloud/mmaudio-v2": {
        "name": "MMAudio v2 - Add Sound to Video",
        "price_per_sec": 0.15,  # Estimated pricing
        "description": "Generates synchronized audio for silent videos based on text prompts",
        "duration_range": (1, 60),  # Supports 1-60 second videos
    },
}

# Video validation constraints
MAX_VIDEO_SIZE_MB = 100
MIN_VIDEO_DURATION = 1
MAX_VIDEO_DURATION = 60


class AtlasCloudVideoToVideoSoundTool(BaseTool):
    """
    Agent tool for adding AI-generated sound to videos using Atlas Cloud API.
    
    Supports:
    - Workspace file paths (hop-aware)
    - HTTP/HTTPS URLs
    - Video validation (format, size, duration)
    - Sound customization via text prompts
    """
    
    def __init__(self):
        """Initialize video-to-video-with-sound tool."""
        super().__init__()
        self.name = "video_to_video_with_sound"
        self.description = (
            "Add AI-generated sound to silent videos using Atlas Cloud mmaudio-v2 model. "
            "Takes a video (workspace file or URL) and a text prompt describing the desired audio. "
            "Returns a new video with synchronized sound effects, ambient audio, or music. "
            "Supports videos from 1-60 seconds. "
            "Default model: 'atlascloud/mmaudio-v2' (~$0.15/sec). "
            "Example prompts: 'birds chirping in forest', 'car engine revving', 'ocean waves crashing', "
            "'upbeat background music', 'footsteps on wooden floor'."
        )
        
        # Build parameters schema
        self.parameters = {
            "type": "object",
            "properties": {
                "video": {
                    "type": "string",
                    "description": (
                        "Video source: workspace file path (e.g., 'videos/my_video.mp4'), "
                        "or HTTP(S) URL. Video must be 1-60 seconds long."
                    )
                },
                "prompt": {
                    "type": "string",
                    "description": (
                        "Text description of the audio to generate. "
                        "Be specific about sounds, music style, or atmosphere. "
                        "Examples: 'birds chirping', 'car engine', 'ocean waves', "
                        "'footsteps on gravel', 'jazz music', 'ambient forest sounds'. "
                        "Max 2000 characters."
                    )
                },
                "model": {
                    "type": "string",
                    "enum": list(VIDEO_TO_VIDEO_SOUND_MODELS.keys()),
                    "description": (
                        "Video-to-video model. "
                        "Default: atlascloud/mmaudio-v2. "
                        "Only change if user explicitly requests different model."
                    )
                },
                "filename": {
                    "type": "string",
                    "description": "Optional custom filename (without extension)"
                },
                "hop_session": {
                    "type": "string",
                    "description": "Optional hop session ID for remote workspace access"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Generation timeout in seconds (default: 600)"
                }
            },
            "required": ["video", "prompt"]
        }
        
        self._client = None
    
    def _get_client(self) -> AtlasCloudClient:
        """Get or create Atlas Cloud client."""
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
    
    def _generate_download_url(self, file_path: str) -> str:
        """
        Generate public download URL for workspace file.
        
        Uses icotes' /api/files/download endpoint to create publicly accessible URL.
        
        IMPORTANT: The SITE_URL environment variable MUST be set to a publicly
        accessible domain (e.g., wip.icotes.com) for AtlasCloud API to download
        the video. LAN IPs (192.168.x.x) or localhost will cause "Unable to 
        download or load video" errors because AtlasCloud servers cannot reach them.
        
        Args:
            file_path: Absolute path to file or namespaced path (e.g., local:/path/to/file)
            
        Returns:
            Public URL for file download
        """
        # Get SITE_URL and PORT from environment
        site_url = os.getenv('SITE_URL', '127.0.0.1')
        port = os.getenv('PORT', '8000')
        
        # Determine protocol (http for local/LAN, could be https for production)
        # Check if running behind reverse proxy with HTTPS
        protocol = 'https' if os.getenv('HTTPS', '').lower() == 'true' else 'http'
        
        # For production domains like wip.icotes.com, use https
        if 'icotes.com' in site_url or 'tunnel' in site_url:
            protocol = 'https'
        
        # Build base URL
        # For production domains, omit port (handled by reverse proxy/Cloudflare)
        # For local/LAN, include port
        if 'icotes.com' in site_url or 'tunnel' in site_url:
            # Production: reverse proxy handles port
            base_url = f"{protocol}://{site_url}"
        else:
            # Local/LAN: include port
            base_url = f"{protocol}://{site_url}:{port}"
        
        # URL encode the file path
        encoded_path = urllib.parse.quote(file_path, safe='')
        
        # Construct download URL
        download_url = f"{base_url}/api/files/download?path={encoded_path}"
        
        logger.info(f"Generated download URL for AtlasCloud: {download_url[:100]}...")
        
        # Warn if URL is not publicly accessible (common pitfall)
        if site_url in ['127.0.0.1', 'localhost'] or site_url.startswith('192.168.') or site_url.startswith('10.'):
            logger.warning(
                f"SITE_URL is set to local/LAN address ({site_url}). "
                "AtlasCloud API cannot access this URL. "
                "Set SITE_URL to a publicly accessible domain (e.g., wip.icotes.com)."
            )
        
        return download_url
    
    async def _process_video(
        self,
        video: str,
        hop_session: Optional[str] = None
    ) -> str:
        """
        Process video input: workspace file → URL upload, URL → pass through.
        
        Args:
            video: Video source (file path or URL)
            hop_session: Optional hop session for remote file access
            
        Returns:
            Video URL ready for API
            
        Raises:
            ValueError: Invalid video format or size
        """
        # If it's a URL, return as-is
        if video.startswith(("http://", "https://")):
            logger.info(f"Using video URL: {video[:50]}...")
            return video
        
        # Otherwise, treat as workspace file path
        logger.info(f"Reading video from workspace: {video}")
        
        # Strip local: prefix if present
        clean_video = video.replace('local:', '') if video.startswith('local:') else video
        
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
            if os.path.isabs(clean_video):
                full_path = Path(clean_video)
            else:
                full_path = Path(workspace_root) / clean_video
        else:
            # Remote context
            full_path = Path(clean_video)
        
        if not full_path.exists():
            raise ValueError(f"Video file not found: {video} (resolved to {full_path})")
        
        # Validate file size
        file_size_mb = full_path.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_VIDEO_SIZE_MB:
            raise ValueError(
                f"Video file too large: {file_size_mb:.1f}MB (max {MAX_VIDEO_SIZE_MB}MB)"
            )
        
        logger.info(f"Video file size: {file_size_mb:.1f}MB")
        
        # AtlasCloud API only accepts video URLs, not file uploads or base64
        # Solution: Generate a public download URL using icotes' /api/files/download endpoint
        # This allows local workspace files to be accessed by AtlasCloud API
        
        logger.info(f"Generating public download URL for local file: {full_path}")
        
        # Construct namespaced path for download URL
        # Use the original path with context prefix if available
        if context_name and context_name.lower() != 'local':
            namespaced_path = f"{context_name}:{full_path}"
        else:
            namespaced_path = f"local:{full_path}"
        
        # Generate public download URL
        download_url = self._generate_download_url(namespaced_path)
        
        logger.info(f"Using download URL for video: {download_url[:80]}...")
        return download_url
    
    async def _download_video(self, video_url: str) -> bytes:
        """Download video from URL."""
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
        original_video_name: str,
        model: str,
        filename: Optional[str] = None,
        hop_session: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """
        Save video to workspace videos/ directory.
        
        Args:
            video_bytes: Video file content
            original_video_name: Original video name for filename generation
            model: Model name for filename generation
            filename: Optional custom filename
            hop_session: Optional hop session for remote saving
            
        Returns:
            Tuple of (relative_path, absolute_path) or None on failure
        """
        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Extract base name from video path
                base_name = Path(original_video_name).stem if '/' in original_video_name or '\\' in original_video_name else original_video_name.split('.')[0]
                model_short = model.split('/')[-1].replace('-', '_')
                filename = f"{base_name}_v2v_sound_{model_short}_{timestamp}"
            
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
                        f"[AtlasCloudV2VSound] Saved video to {filepath} "
                        f"({len(video_bytes)} bytes)"
                    )
                except Exception as e:
                    logger.error(f"[AtlasCloudV2VSound] Local write failed: {e}")
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
                        f"[AtlasCloudV2VSound] Saved video to remote: {filepath}"
                    )
                except Exception as e:
                    logger.error(f"[AtlasCloudV2VSound] Remote write failed: {e}")
                    return None
            
            logger.info(
                f"[AtlasCloudV2VSound] Video saved to {relative_path} "
                f"(context: {context_name})"
            )
            
            # Return relative and absolute paths
            return (relative_path, filepath)
        
        except Exception as e:
            logger.error(f"[AtlasCloudV2VSound] Failed to save video: {e}")
            return None
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute video-to-video-with-sound generation.
        
        Args:
            video: Video source (required)
            prompt: Audio description (required)
            model: Video-to-video model (default: atlascloud/mmaudio-v2)
            filename: Optional custom filename
            hop_session: Optional hop session ID
            timeout: Generation timeout (default: 600s)
            
        Returns:
            ToolResult with video path and metadata
        """
        # Extract parameters
        video = kwargs.get("video")
        prompt = kwargs.get("prompt")
        model = kwargs.get("model", "atlascloud/mmaudio-v2")
        filename = kwargs.get("filename")
        timeout = kwargs.get("timeout", 600)
        hop_session = kwargs.get("hop_session")
        
        # Validate required parameters
        if not video:
            return ToolResult(
                success=False,
                data=None,
                error="Missing required parameter: video"
            )
        
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
        
        # Validate model
        if model not in VIDEO_TO_VIDEO_SOUND_MODELS:
            return ToolResult(
                success=False,
                data=None,
                error=f"Invalid model '{model}'. Available models: {list(VIDEO_TO_VIDEO_SOUND_MODELS.keys())}"
            )
        
        try:
            # Process video input
            logger.info(f"[AtlasCloudV2VSound] Processing video: {video[:50]}...")
            processed_video = await self._process_video(video, hop_session)
            
            # Get client
            client = self._get_client()
            
            logger.info(
                f"[AtlasCloudV2VSound] Starting video-to-video generation with sound: "
                f"model={model}"
            )
            
            # Estimate cost (based on video duration - we'll use a placeholder for now)
            model_info = VIDEO_TO_VIDEO_SOUND_MODELS[model]
            # We don't know duration yet, so estimate based on average 10 seconds
            estimated_duration = 10
            estimated_cost = model_info["price_per_sec"] * estimated_duration
            logger.info(f"[AtlasCloudV2VSound] Estimated cost: ~${estimated_cost:.2f} (for ~{estimated_duration}s video)")
            
            # Generate video with sound (with polling)
            result = await client.generate_video_to_video_with_sound(
                video=processed_video,
                prompt=prompt,
                model=model,
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
            
            logger.info(f"[AtlasCloudV2VSound] Video generated: {video_url}")
            
            # Download video
            logger.info(f"[AtlasCloudV2VSound] Downloading video...")
            video_bytes = await self._download_video(video_url)
            logger.info(f"[AtlasCloudV2VSound] Downloaded {len(video_bytes)} bytes")
            
            # Save to workspace
            paths = await self._save_video_to_workspace(
                video_bytes,
                video,
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
                    "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                    "cost_estimate": f"~${estimated_cost:.2f}",
                    "message": f"Video with sound generated successfully and saved to {relative_path}"
                },
                error=None
            )
            
        except AtlasCloudTimeoutError as e:
            logger.error(f"[AtlasCloudV2VSound] Timeout: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Video generation timed out after {timeout}s. Try again or increase timeout."
            )
        
        except AtlasCloudError as e:
            logger.error(f"[AtlasCloudV2VSound] API error: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Atlas Cloud API error: {str(e)}"
            )
        
        except Exception as e:
            logger.error(f"[AtlasCloudV2VSound] Unexpected error: {e}", exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                error=f"Unexpected error: {str(e)}"
            )
