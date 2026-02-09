"""
YouTube Video Downloader Tool for agents

Downloads YouTube videos using yt-dlp with quality control and workspace integration.
Follows existing tool patterns with namespaced path support and progress reporting.

Requires: yt-dlp library (no API key needed)

Features:
- Multiple quality options (low/medium/high/audio_only)
- Format selection (mp4, webm, mkv)
- Automatic workspace storage
- Progress updates
- Metadata extraction
- Rate limiting
- Remote/hop support
"""

from __future__ import annotations

import os
import re
import logging
import hashlib
from typing import Any, Optional, Tuple, Dict
from datetime import datetime, timedelta
from pathlib import Path
import asyncio

from .base_tool import BaseTool, ToolResult
from .context_helpers import get_contextual_filesystem, get_current_context
from .generation_output_checks import verify_output_file

# Lazy import yt-dlp to avoid loading at startup
YT_DLP_AVAILABLE = False
_YT_DLP_IMPORT_ERROR: Optional[Exception] = None

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError as e:
    _YT_DLP_IMPORT_ERROR = e

logger = logging.getLogger(__name__)

# Quality presets mapping
QUALITY_PRESETS = {
    'low': {
        'format': 'best[height<=360]',
        'description': '360p or lower (~5-15MB)',
        'max_filesize': 15 * 1024 * 1024,  # 15MB
    },
    'medium': {
        'format': 'best[height<=720]',
        'description': '720p or lower (~20-50MB)',
        'max_filesize': 50 * 1024 * 1024,  # 50MB
    },
    'high': {
        'format': 'best[height<=1080]',
        'description': '1080p or lower (~50-200MB)',
        'max_filesize': 200 * 1024 * 1024,  # 200MB
    },
    'audio_only': {
        'format': 'bestaudio/best',
        'description': 'Audio only (~3-10MB)',
        'max_filesize': 10 * 1024 * 1024,  # 10MB
    },
}

# Cache settings
CACHE_TTL = 300  # 5 minutes for metadata cache
_metadata_cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}

# Rate limiting (similar to web_fetch_tool)
RATE_LIMIT_DOWNLOADS = 3  # downloads per minute
RATE_LIMIT_WINDOW = 60  # seconds
_rate_limit_tracker: list[float] = []


class YouTubeDownloadTool(BaseTool):
    """
    Download YouTube videos with quality control and workspace integration.
    
    Capabilities:
        - Download videos in multiple quality levels
        - Extract audio only
        - Automatic workspace storage
        - Progress updates
        - Metadata extraction (title, duration, uploader)
        - Hop-aware for remote server support
    
    Quality Options:
        - low: 360p or lower (~5-15MB)
        - medium: 720p or lower (~20-50MB) [default]
        - high: 1080p or lower (~50-200MB)
        - audio_only: Extract audio only (~3-10MB)
    """
    
    DEFAULT_OUTPUT_DIR = "videos"  # Subdirectory under workspace root
    
    def __init__(self):
        super().__init__()
        self.name = "youtube_download"
        self.description = (
            "Download YouTube videos with quality control. "
            "Supports multiple quality levels (low/medium/high) and audio-only extraction. "
            "Videos are automatically saved to your workspace. "
            "Returns file path and video metadata (title, duration, uploader). "
            "Use 'low' or 'medium' quality to conserve bandwidth and storage. "
            "Note: Large videos may take time to download."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": (
                        "YouTube video URL. Supports formats: "
                        "https://www.youtube.com/watch?v=VIDEO_ID, "
                        "https://youtu.be/VIDEO_ID, "
                        "https://www.youtube.com/watch?v=VIDEO_ID&t=123"
                    )
                },
                "quality": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "audio_only"],
                    "description": (
                        "Quality preset: "
                        "'low' (360p, ~5-15MB), "
                        "'medium' (720p, ~20-50MB, default), "
                        "'high' (1080p, ~50-200MB), "
                        "'audio_only' (audio extraction, ~3-10MB)"
                    )
                },
                "output_format": {
                    "type": "string",
                    "enum": ["mp4", "webm", "mkv", "m4a"],
                    "description": (
                        "Output file format. Default: 'mp4' for video, 'm4a' for audio. "
                        "Note: Some formats may require conversion."
                    )
                },
                "filename": {
                    "type": "string",
                    "description": (
                        "Optional custom filename (without extension). "
                        "If not provided, uses sanitized video title. "
                        "Example: 'my_video' will save as 'my_video.mp4'"
                    )
                },
            },
            "required": ["url"],
        }
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from various URL formats."""
        # Only process YouTube URLs
        if 'youtube.com' not in url and 'youtu.be' not in url:
            return None
        
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'^([0-9A-Za-z_-]{11})$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                # Verify it's exactly 11 characters
                if len(video_id) == 11:
                    return video_id
        
        return None
    
    def _check_rate_limit(self) -> Tuple[bool, Optional[str]]:
        """Check if download is within rate limit."""
        import time
        now = time.time()
        
        # Remove old requests outside the window
        global _rate_limit_tracker
        _rate_limit_tracker = [
            req_time for req_time in _rate_limit_tracker
            if now - req_time < RATE_LIMIT_WINDOW
        ]
        
        # Check if limit exceeded
        if len(_rate_limit_tracker) >= RATE_LIMIT_DOWNLOADS:
            wait_time = RATE_LIMIT_WINDOW - (now - _rate_limit_tracker[0])
            return False, f"Rate limit exceeded. Try again in {wait_time:.0f} seconds."
        
        # Record this request
        _rate_limit_tracker.append(now)
        return True, None
    
    async def _get_video_info(self, url: str, video_id: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Extract video metadata without downloading.
        Uses caching to avoid repeated API calls.
        """
        # Check cache
        cache_key = f"metadata_{video_id}"
        if cache_key in _metadata_cache:
            metadata, cached_at = _metadata_cache[cache_key]
            if datetime.now() - cached_at < timedelta(seconds=CACHE_TTL):
                logger.info(f"Using cached metadata for {video_id}")
                return True, metadata, None
        
        if not YT_DLP_AVAILABLE:
            return False, None, "yt-dlp library not available. Please install: pip install yt-dlp"
        
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            def extract_info():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            
            info = await loop.run_in_executor(None, extract_info)
            
            if not info:
                return False, None, "Failed to extract video information"
            
            metadata = {
                'video_id': video_id,
                'title': info.get('title', 'Unknown'),
                'uploader': info.get('uploader', 'Unknown'),
                'duration': info.get('duration', 0),
                'duration_string': info.get('duration_string', '0:00'),
                'view_count': info.get('view_count', 0),
                'upload_date': info.get('upload_date', 'Unknown'),
                'description': info.get('description', '')[:200],  # First 200 chars
            }
            
            # Cache the metadata
            _metadata_cache[cache_key] = (metadata, datetime.now())
            
            logger.info(f"Extracted metadata for {video_id}: {metadata['title']}")
            return True, metadata, None
            
        except Exception as e:
            logger.error(f"Error extracting video info: {e}")
            return False, None, f"Failed to get video information: {str(e)}"
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem usage."""
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Replace multiple spaces with single underscore
        filename = re.sub(r'\s+', '_', filename)
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        return filename or 'video'
    
    async def _download_video(
        self,
        url: str,
        video_id: str,
        quality: str,
        output_format: str,
        output_path: Path,
        filename: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Download the video using yt-dlp.
        
        Returns:
            (success, file_path_or_error, error_message)
        """
        if not YT_DLP_AVAILABLE:
            return False, None, "yt-dlp library not available. Please install: pip install yt-dlp"
        
        try:
            # Get quality preset
            preset = QUALITY_PRESETS.get(quality, QUALITY_PRESETS['medium'])
            
            # Determine output template
            if filename:
                safe_filename = self._sanitize_filename(filename)
            else:
                safe_filename = '%(title)s'  # yt-dlp will fill this in
            
            # Set extension based on format and quality
            if quality == 'audio_only':
                ext = 'm4a' if output_format == 'mp4' else output_format
            else:
                ext = output_format
            
            output_template = str(output_path / f"{safe_filename}.{ext}")
            
            # Configure yt-dlp options
            ydl_opts = {
                'format': preset['format'],
                'outtmpl': output_template,
                'quiet': False,
                'no_warnings': False,
                'extract_audio': quality == 'audio_only',
                'postprocessors': [],
                'prefer_ffmpeg': True,
                'keepvideo': False,
            }
            
            # Add audio extraction post-processor if needed
            if quality == 'audio_only':
                ydl_opts['postprocessors'].append({
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a' if ext == 'm4a' else 'mp3',
                    'preferredquality': '192',
                })
            
            # Add progress hook for logging
            def progress_hook(d):
                if d['status'] == 'downloading':
                    percent = d.get('_percent_str', '0%')
                    speed = d.get('_speed_str', 'N/A')
                    logger.info(f"Downloading {video_id}: {percent} at {speed}")
                elif d['status'] == 'finished':
                    logger.info(f"Download finished for {video_id}, processing...")
            
            ydl_opts['progress_hooks'] = [progress_hook]
            
            # Run download in executor
            loop = asyncio.get_event_loop()
            
            def download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            
            await loop.run_in_executor(None, download)
            
            # Find the downloaded file (yt-dlp may modify filename)
            downloaded_files = list(output_path.glob(f"{safe_filename if filename else '*'}.{ext}"))
            
            if not downloaded_files:
                # Try alternative extensions (sometimes yt-dlp uses different ext)
                downloaded_files = list(output_path.glob(f"{safe_filename if filename else '*'}.*"))
            
            if not downloaded_files:
                return False, None, "Download completed but file not found"
            
            # Use the first (most recent) file
            downloaded_file = downloaded_files[0]
            
            logger.info(f"Successfully downloaded: {downloaded_file}")
            return True, str(downloaded_file), None
            
        except Exception as e:
            logger.error(f"Error downloading video: {e}", exc_info=True)
            return False, None, f"Download failed: {str(e)}"
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute YouTube video download.
        
        Args:
            url: YouTube video URL (required)
            quality: Quality preset - low/medium/high/audio_only (default: medium)
            output_format: File format - mp4/webm/mkv/m4a (default: mp4)
            filename: Optional custom filename
        
        Returns:
            ToolResult with file path and metadata
        """
        url = kwargs.get('url')
        quality = kwargs.get('quality', 'medium')
        output_format = kwargs.get('output_format', 'mp4')
        filename = kwargs.get('filename')
        
        if not url:
            return ToolResult(
                success=False,
                error="Missing required parameter: url"
            )
        
        # Validate quality
        if quality not in QUALITY_PRESETS:
            return ToolResult(
                success=False,
                error=f"Invalid quality '{quality}'. Must be one of: {', '.join(QUALITY_PRESETS.keys())}"
            )
        
        # Extract video ID
        video_id = self._extract_video_id(url)
        if not video_id:
            return ToolResult(
                success=False,
                error="Invalid YouTube URL. Could not extract video ID."
            )
        
        # Check rate limit
        allowed, rate_error = self._check_rate_limit()
        if not allowed:
            return ToolResult(
                success=False,
                error=rate_error
            )
        
        # Get video metadata
        success, metadata, error = await self._get_video_info(url, video_id)
        if not success:
            return ToolResult(
                success=False,
                error=error or "Failed to get video information"
            )
        
        # Get contextual filesystem and current context
        fs = await get_contextual_filesystem()
        context = await get_current_context()
        context_id = context.get('contextId', 'local')
        
        # Determine workspace root based on context
        if context_id == 'local':
            workspace_root = getattr(fs, 'root_path', None)
            if not workspace_root:
                workspace_root = os.environ.get('WORKSPACE_ROOT') or os.getcwd()
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
        
        # Determine output directory
        output_dir = Path(workspace_root) / self.DEFAULT_OUTPUT_DIR
        
        # Create output directory if it doesn't exist
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to create output directory: {str(e)}"
            )
        
        # Download the video
        logger.info(f"Starting download: {url} (quality: {quality}, format: {output_format})")
        success, file_path, error = await self._download_video(
            url, video_id, quality, output_format, output_dir, filename
        )
        
        if not success:
            return ToolResult(
                success=False,
                error=error or "Download failed"
            )
        
        # Verify the output file
        try:
            file_size = os.path.getsize(file_path)
            file_path_obj = Path(file_path)
            relative_path = file_path_obj.relative_to(workspace_root)
        except Exception as e:
            logger.error(f"Error verifying output file: {e}")
            return ToolResult(
                success=False,
                error=f"Download completed but file verification failed: {str(e)}"
            )
        
        # Build result data
        result_data = {
            'file_path': str(relative_path),
            'absolute_path': file_path,
            'file_size_mb': round(file_size / (1024 * 1024), 2),
            'file_size_bytes': file_size,
            'quality': quality,
            'format': output_format,
            'video_id': video_id,
            'metadata': metadata,
            'context_id': context_id,
        }
        
        # Format success message
        quality_desc = QUALITY_PRESETS[quality]['description']
        message = (
            f"✅ Successfully downloaded: {metadata.get('title', 'video')}\n"
            f"📁 Saved to: {relative_path}\n"
            f"📊 Size: {result_data['file_size_mb']} MB\n"
            f"🎬 Quality: {quality} ({quality_desc})\n"
            f"⏱️ Duration: {metadata.get('duration_string', 'Unknown')}\n"
            f"👤 Uploader: {metadata.get('uploader', 'Unknown')}"
        )
        
        logger.info(f"Download successful: {file_path}")
        
        return ToolResult(
            success=True,
            data=result_data,
            error=message  # Using error field for success message (convention in other tools)
        )
