"""
ElevenLabs Music Generation Tool for agents

Generates music from text prompts using ElevenLabs Music API.
Follows existing tool patterns with namespaced path support.

Requires: ELEVENLABS_API_KEY environment variable (paid users only)

References:
- https://elevenlabs.io/docs/developers/guides/cookbooks/music/quickstart
"""

from __future__ import annotations

import os
import re
import logging
from typing import Any, Optional, Tuple
from datetime import datetime

from .base_tool import BaseTool, ToolResult
from .context_helpers import get_contextual_filesystem, get_current_context

# Lazy import ElevenLabs SDK to avoid loading at startup
ELEVENLABS_AVAILABLE = False
_ELEVENLABS_IMPORT_ERROR: Optional[Exception] = None

try:
    from elevenlabs.client import ElevenLabs
    ELEVENLABS_AVAILABLE = True
except ImportError as e:
    _ELEVENLABS_IMPORT_ERROR = e

logger = logging.getLogger(__name__)


class ElevenLabsMusicTool(BaseTool):
    """
    Generate music from text prompts using ElevenLabs Music API.
    
    Capabilities:
        - Text-to-music generation with detailed prompts
        - Configurable music length (0.5s to 120s)
        - Automatic saving to workspace
        - Hop-aware for remote server support
    
    Important Notes:
        - Music API is only available to paid ElevenLabs users
        - Do NOT mention copyrighted material (artists, bands, songs, games)
        - Describe the musical STYLE instead of referencing copyrighted works
    """
    
    # Conservative defaults to minimize credit usage
    DEFAULT_MUSIC_LENGTH_MS = 5000  # 5 seconds (short test)
    MIN_MUSIC_LENGTH_MS = 500       # 0.5 seconds
    MAX_MUSIC_LENGTH_MS = 120000    # 120 seconds (2 minutes)
    
    def __init__(self):
        super().__init__()
        self.name = "text_to_music"
        self.description = (
            "Generate music from text prompts using ElevenLabs Music API. "
            "Creates custom music tracks based on detailed descriptions. "
            "Describe the style, tempo, instruments, mood, and structure. "
            "Examples: 'Upbeat electronic dance music with synth pads, 120 BPM', "
            "'Calm acoustic guitar with soft piano, relaxing atmosphere'. "
            "Generated music is saved to workspace and can be played in the media player. "
            "CRITICAL: Do NOT mention copyrighted artists, bands, song names, or game titles (e.g., avoid 'Final Fantasy', 'Beatles', 'Mozart'). "
            "Instead, describe the STYLE and characteristics (e.g., 'epic orchestral piano with emotional melodies'). "
            "IMPORTANT: Use short durations (5-10 seconds) for testing to conserve credits. "
            "Music API requires a paid ElevenLabs subscription."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "Detailed description of the music to generate. "
                        "Include style, tempo, instruments, mood, energy level, etc. "
                        "CRITICAL: Do NOT mention copyrighted material (artist names, band names, song titles, game titles). "
                        "Describe the STYLE instead (e.g., 'epic orchestral' not 'Final Fantasy style'). "
                        "Be specific for better results. "
                        "Example: 'Fast-paced electronic track with driving synth arpeggios, "
                        "punchy drums, 130 BPM, high energy'"
                    )
                },
                "duration_seconds": {
                    "type": "number",
                    "description": (
                        "Duration of the music in seconds. "
                        "Min: 0.5, Max: 120, Default: 5 seconds (conservative for testing). "
                        "Use short durations to conserve credits."
                    )
                },
                "filename": {
                    "type": "string",
                    "description": (
                        "Optional custom filename (without extension). "
                        "If not provided, auto-generates from prompt and timestamp."
                    )
                },
                "save_to_workspace": {
                    "type": "boolean",
                    "description": "Whether to save the music to workspace (default: true)."
                }
            },
            "required": ["prompt"]
        }
        
        # Initialize client lazily
        self._client: Optional[Any] = None
        self._api_key: Optional[str] = None
    
    def _get_client(self):
        """Get or create ElevenLabs client lazily."""
        if self._client is not None:
            return self._client
        
        if not ELEVENLABS_AVAILABLE:
            raise RuntimeError(
                f"ElevenLabs SDK not available. Install with: pip install elevenlabs. "
                f"Error: {_ELEVENLABS_IMPORT_ERROR}"
            )
        
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY environment variable not set. "
                "Get your API key from https://elevenlabs.io/app/settings/api-keys"
            )
        
        self._api_key = api_key
        self._client = ElevenLabs(api_key=api_key)
        logger.info("ElevenLabs client initialized for Music")
        return self._client
    
    async def _save_music_to_workspace(
        self,
        music_bytes: bytes,
        prompt: str,
        custom_filename: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """
        Save music bytes to workspace folder (hop-aware).
        
        Args:
            music_bytes: Binary music data
            prompt: Original prompt (used for auto-generated filename)
            custom_filename: Optional custom filename (without extension)
            
        Returns:
            Tuple of (relative_path, absolute_path) if successful, None otherwise.
        """
        try:
            # Generate filename
            if custom_filename:
                # Sanitize custom filename
                safe_name = re.sub(r'[^\w\s-]', '', custom_filename).strip().replace(' ', '_')
                filename = f"{safe_name}.mp3"
            else:
                # Auto-generate from prompt and timestamp
                timestamp = int(datetime.now().timestamp())
                # Take first 30 chars of prompt for filename
                safe_prompt = re.sub(r'[^\w\s-]', '', prompt[:30]).strip().replace(' ', '_')
                if not safe_prompt:
                    safe_prompt = "music"
                filename = f"music_{safe_prompt}_{timestamp}.mp3"
            
            # Get context for hop-aware saving
            context = await get_current_context()
            context_name = context.get('contextId', 'local')
            filesystem_service = await get_contextual_filesystem()
            
            # Determine workspace root based on context
            if context_name == 'local':
                workspace_root = getattr(filesystem_service, 'root_path', None)
                if not workspace_root:
                    workspace_root = os.environ.get('WORKSPACE_ROOT') or os.getcwd()
                
                # Ensure sounds directory exists
                sounds_dir = os.path.join(workspace_root, 'sounds')
                os.makedirs(sounds_dir, exist_ok=True)
                
                filepath = os.path.join(sounds_dir, filename)
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
                sounds_dir = posixpath.join(workspace_root, 'sounds')
                filepath = posixpath.join(sounds_dir, filename)
            
            logger.info(
                f"[ElevenLabsMusic] Target context: {context_name}, "
                f"filepath: {filepath}"
            )
            
            if context_name == 'local':
                # Write directly to local filesystem
                try:
                    with open(filepath, 'wb') as f:
                        f.write(music_bytes)
                    logger.info(
                        f"[ElevenLabsMusic] Saved music to {filepath} "
                        f"({len(music_bytes)} bytes)"
                    )
                except Exception as e:
                    logger.error(f"[ElevenLabsMusic] Local write failed: {e}")
                    return None
            else:
                # Remote context: Write via SFTP
                try:
                    if hasattr(filesystem_service, 'write_file_binary'):
                        # Ensure remote directory exists
                        if hasattr(filesystem_service, 'create_directory'):
                            await filesystem_service.create_directory(sounds_dir)
                        await filesystem_service.write_file_binary(filepath, music_bytes)
                        logger.info(
                            f"[ElevenLabsMusic] Saved music to remote: {filepath}"
                        )
                    else:
                        logger.error(
                            "[ElevenLabsMusic] Remote filesystem doesn't support binary write"
                        )
                        return None
                except Exception as e:
                    logger.error(f"[ElevenLabsMusic] Remote write failed: {e}")
                    return None
            
            # Return relative and absolute paths
            relative_path = f"sounds/{filename}"
            return (relative_path, filepath)
            
        except Exception as e:
            logger.error(f"[ElevenLabsMusic] Failed to save music: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute music generation.
        
        Args:
            prompt: Description of music to generate (required)
            duration_seconds: Length in seconds (default: 5)
            filename: Custom filename (without extension)
            save_to_workspace: Whether to save music (default: True)
            
        Returns:
            ToolResult with music file path and metadata
        """
        # Extract parameters
        prompt = kwargs.get("prompt", "")
        duration_seconds = kwargs.get("duration_seconds", self.DEFAULT_MUSIC_LENGTH_MS / 1000)
        custom_filename = kwargs.get("filename")
        save_to_workspace = kwargs.get("save_to_workspace", True)
        
        # Validate required parameters
        if not prompt:
            return ToolResult(
                success=False,
                error="'prompt' parameter is required"
            )
        
        # Convert duration to milliseconds
        duration_ms = int(duration_seconds * 1000)
        
        # Validate duration
        if duration_ms < self.MIN_MUSIC_LENGTH_MS:
            return ToolResult(
                success=False,
                error=f"Duration too short. Minimum is {self.MIN_MUSIC_LENGTH_MS/1000} seconds."
            )
        
        if duration_ms > self.MAX_MUSIC_LENGTH_MS:
            return ToolResult(
                success=False,
                error=f"Duration too long. Maximum is {self.MAX_MUSIC_LENGTH_MS/1000} seconds."
            )
        
        try:
            # Get client
            client = self._get_client()
            
            logger.info(
                f"[ElevenLabsMusic] Generating music: "
                f"duration={duration_ms}ms, "
                f"prompt_length={len(prompt)}"
            )
            
            # Generate music using ElevenLabs Music API
            # The compose method returns an iterator of audio bytes
            # Note: API only accepts prompt and music_length_ms parameters
            music_iterator = client.music.compose(
                prompt=prompt,
                music_length_ms=duration_ms
            )
            
            # Collect all music bytes from iterator
            music_bytes = b"".join(music_iterator)
            
            if not music_bytes:
                return ToolResult(
                    success=False,
                    error="No music data received from ElevenLabs API"
                )
            
            logger.info(
                f"[ElevenLabsMusic] Received {len(music_bytes)} bytes of music"
            )
            
            # Prepare response data
            response_data = {
                "prompt": prompt,
                "duration_seconds": duration_seconds,
                "duration_ms": duration_ms,
                "audio_size_bytes": len(music_bytes),
            }
            
            # Save to workspace if requested
            if save_to_workspace:
                save_result = await self._save_music_to_workspace(
                    music_bytes=music_bytes,
                    prompt=prompt,
                    custom_filename=custom_filename
                )
                
                if save_result:
                    relative_path, absolute_path = save_result
                    response_data["saved"] = True
                    response_data["file_path"] = relative_path
                    response_data["absolute_path"] = absolute_path
                    response_data["audio_url"] = f"file://{absolute_path}"
                    logger.info(
                        f"[ElevenLabsMusic] Music saved to: {absolute_path}"
                    )
                else:
                    response_data["saved"] = False
                    response_data["save_error"] = "Failed to save music to workspace"
                    logger.warning(
                        "[ElevenLabsMusic] Failed to save music, returning metadata only"
                    )
            else:
                response_data["saved"] = False
            
            return ToolResult(
                success=True,
                data=response_data
            )
            
        except RuntimeError as e:
            # Client initialization errors
            return ToolResult(
                success=False,
                error=str(e)
            )
        except Exception as e:
            logger.error(f"[ElevenLabsMusic] Error: {e}")
            import traceback
            traceback.print_exc()
            
            # Check for specific error types
            error_msg = str(e)
            
            # Try to extract prompt suggestion from API error
            if "bad_prompt" in error_msg.lower():
                # Try to extract suggested prompt from error body
                suggested_prompt = None
                try:
                    if hasattr(e, 'body') and isinstance(e.body, dict):
                        detail = e.body.get('detail', {})
                        if isinstance(detail, dict):
                            data = detail.get('data', {})
                            suggested_prompt = data.get('prompt_suggestion')
                except:
                    pass
                
                if suggested_prompt:
                    return ToolResult(
                        success=False,
                        error=(
                            f"Prompt contains copyrighted material. "
                            f"Try this instead: '{suggested_prompt}'"
                        )
                    )
                else:
                    return ToolResult(
                        success=False,
                        error=(
                            f"Prompt rejected (likely copyrighted material). "
                            f"Avoid mentioning artist/band/game names. Describe the style instead. "
                            f"Error: {error_msg}"
                        )
                    )
            elif "subscription" in error_msg.lower() or "paid" in error_msg.lower():
                return ToolResult(
                    success=False,
                    error="Music API requires a paid ElevenLabs subscription"
                )
            
            return ToolResult(
                success=False,
                error=f"Failed to generate music: {error_msg}"
            )
