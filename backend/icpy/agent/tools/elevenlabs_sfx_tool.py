"""
ElevenLabs Sound Effects Generation Tool for agents

Generates sound effects from text prompts using ElevenLabs Sound Effects API.
Follows existing tool patterns with namespaced path support.

Requires: ELEVENLABS_API_KEY environment variable

References:
- https://elevenlabs.io/docs/api-reference/sound-generation
- https://elevenlabs.io/docs/developers/guides/cookbooks/sound-effects
"""

from __future__ import annotations

import os
import re
import logging
from typing import Any, Dict, Optional, Tuple
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


class ElevenLabsSoundEffectsTool(BaseTool):
    """
    Generate sound effects from text descriptions using ElevenLabs Sound Effects API.
    
    Capabilities:
        - Text-to-sound-effects generation
        - Configurable duration (0.5s to 30s)
        - Prompt influence control for variability
        - Optional looping
        - Automatic saving to workspace
        - Hop-aware for remote server support
    """
    
    # Conservative defaults to minimize credit usage
    DEFAULT_DURATION_SECONDS = 1.0  # 1 second (short test)
    MIN_DURATION_SECONDS = 0.5      # 0.5 seconds
    MAX_DURATION_SECONDS = 30.0     # 30 seconds
    DEFAULT_MODEL = "eleven_text_to_sound_v2"
    
    def __init__(self):
        super().__init__()
        self.name = "text_to_sound_effects"
        self.description = (
            "Generate sound effects from text descriptions using ElevenLabs Sound Effects API. "
            "Create realistic or fantastical sound effects for games, videos, or applications. "
            "Describe the sound clearly including source, duration, intensity, and environment. "
            "Examples: 'Dog barking loudly in distance', 'Door creaking open slowly', "
            "'Thunder rumbling with rain', 'Glass breaking into pieces', "
            "'Footsteps on wooden floor', 'Explosion with debris falling'. "
            "Generated sound effects are saved to workspace and can be played in the media player. "
            "IMPORTANT: Use short durations (1-2 seconds) for testing to conserve credits."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": (
                        "Detailed description of the sound effect to generate. "
                        "Include the sound source, action, intensity, environment, and any modifiers. "
                        "Be specific and descriptive for better results. "
                        "Example: 'Heavy footsteps on wooden floor, slow pace, creaking wood'"
                    )
                },
                "duration_seconds": {
                    "type": "number",
                    "description": (
                        "Duration of the sound effect in seconds. "
                        "Min: 0.5, Max: 30, Default: 1.0 second (conservative for testing). "
                        "Use short durations to conserve credits."
                    )
                },
                "prompt_influence": {
                    "type": "number",
                    "description": (
                        "How closely to follow the prompt (0.0-1.0). "
                        "Higher = more faithful to description but less variable. "
                        "Lower = more creative interpretation. Default: 0.3."
                    )
                },
                "loop": {
                    "type": "boolean",
                    "description": (
                        "Whether the generated sound should loop seamlessly. "
                        "Useful for ambient sounds, background noise, etc. Default: false."
                    )
                },
                "filename": {
                    "type": "string",
                    "description": (
                        "Optional custom filename (without extension). "
                        "If not provided, auto-generates from description and timestamp."
                    )
                },
                "save_to_workspace": {
                    "type": "boolean",
                    "description": "Whether to save the sound effect to workspace (default: true)."
                }
            },
            "required": ["text"]
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
        logger.info("ElevenLabs client initialized for Sound Effects")
        return self._client
    
    async def _save_sfx_to_workspace(
        self,
        sfx_bytes: bytes,
        text: str,
        custom_filename: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """
        Save sound effect bytes to workspace folder (hop-aware).
        
        Args:
            sfx_bytes: Binary sound data
            text: Original description (used for auto-generated filename)
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
                # Auto-generate from text and timestamp
                timestamp = int(datetime.now().timestamp())
                # Take first 30 chars of text for filename
                safe_text = re.sub(r'[^\w\s-]', '', text[:30]).strip().replace(' ', '_')
                if not safe_text:
                    safe_text = "sfx"
                filename = f"sfx_{safe_text}_{timestamp}.mp3"
            
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
                f"[ElevenLabsSFX] Target context: {context_name}, "
                f"filepath: {filepath}"
            )
            
            if context_name == 'local':
                # Write directly to local filesystem
                try:
                    with open(filepath, 'wb') as f:
                        f.write(sfx_bytes)
                    logger.info(
                        f"[ElevenLabsSFX] Saved sound effect to {filepath} "
                        f"({len(sfx_bytes)} bytes)"
                    )
                except Exception as e:
                    logger.error(f"[ElevenLabsSFX] Local write failed: {e}")
                    return None
            else:
                # Remote context: Write via SFTP
                try:
                    if hasattr(filesystem_service, 'write_file_binary'):
                        # Ensure remote directory exists
                        if hasattr(filesystem_service, 'create_directory'):
                            await filesystem_service.create_directory(sounds_dir)
                        await filesystem_service.write_file_binary(filepath, sfx_bytes)
                        logger.info(
                            f"[ElevenLabsSFX] Saved sound effect to remote: {filepath}"
                        )
                    else:
                        logger.error(
                            "[ElevenLabsSFX] Remote filesystem doesn't support binary write"
                        )
                        return None
                except Exception as e:
                    logger.error(f"[ElevenLabsSFX] Remote write failed: {e}")
                    return None
            
            # Return relative and absolute paths
            relative_path = f"sounds/{filename}"
            return (relative_path, filepath)
            
        except Exception as e:
            logger.error(f"[ElevenLabsSFX] Failed to save sound effect: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute sound effect generation.
        
        Args:
            text: Description of sound effect to generate (required)
            duration_seconds: Length in seconds (default: 1.0)
            prompt_influence: How closely to follow prompt 0.0-1.0 (default: 0.3)
            loop: Whether sound should loop seamlessly (default: False)
            filename: Custom filename (without extension)
            save_to_workspace: Whether to save sound (default: True)
            
        Returns:
            ToolResult with sound effect file path and metadata
        """
        # Extract parameters
        text = kwargs.get("text", "")
        duration_seconds = kwargs.get("duration_seconds", self.DEFAULT_DURATION_SECONDS)
        prompt_influence = kwargs.get("prompt_influence", 0.3)
        loop = kwargs.get("loop", False)
        custom_filename = kwargs.get("filename")
        save_to_workspace = kwargs.get("save_to_workspace", True)
        
        # Validate required parameters
        if not text:
            return ToolResult(
                success=False,
                error="'text' parameter is required"
            )
        
        # Validate duration
        if duration_seconds < self.MIN_DURATION_SECONDS:
            return ToolResult(
                success=False,
                error=f"Duration too short. Minimum is {self.MIN_DURATION_SECONDS} seconds."
            )
        
        if duration_seconds > self.MAX_DURATION_SECONDS:
            return ToolResult(
                success=False,
                error=f"Duration too long. Maximum is {self.MAX_DURATION_SECONDS} seconds."
            )
        
        # Validate prompt influence
        if not (0.0 <= prompt_influence <= 1.0):
            return ToolResult(
                success=False,
                error="prompt_influence must be between 0.0 and 1.0"
            )
        
        try:
            # Get client
            client = self._get_client()
            
            logger.info(
                f"[ElevenLabsSFX] Generating sound effect: "
                f"duration={duration_seconds}s, influence={prompt_influence}, "
                f"loop={loop}, text_length={len(text)}"
            )
            
            # Generate sound effect using ElevenLabs Sound Effects API
            # The convert method returns an iterator of audio bytes
            sfx_iterator = client.text_to_sound_effects.convert(
                text=text,
                duration_seconds=duration_seconds,
                prompt_influence=prompt_influence,
                loop=loop
            )
            
            # Collect all sound bytes from iterator
            sfx_bytes = b"".join(sfx_iterator)
            
            if not sfx_bytes:
                return ToolResult(
                    success=False,
                    error="No sound data received from ElevenLabs API"
                )
            
            logger.info(
                f"[ElevenLabsSFX] Received {len(sfx_bytes)} bytes of sound"
            )
            
            # Prepare response data
            response_data = {
                "text": text,
                "duration_seconds": duration_seconds,
                "prompt_influence": prompt_influence,
                "loop": loop,
                "audio_size_bytes": len(sfx_bytes),
            }
            
            # Save to workspace if requested
            if save_to_workspace:
                save_result = await self._save_sfx_to_workspace(
                    sfx_bytes=sfx_bytes,
                    text=text,
                    custom_filename=custom_filename
                )
                
                if save_result:
                    relative_path, absolute_path = save_result
                    response_data["saved"] = True
                    response_data["file_path"] = relative_path
                    response_data["absolute_path"] = absolute_path
                    response_data["audio_url"] = f"file://{absolute_path}"
                    logger.info(
                        f"[ElevenLabsSFX] Sound effect saved to: {absolute_path}"
                    )
                else:
                    response_data["saved"] = False
                    response_data["save_error"] = "Failed to save sound effect to workspace"
                    logger.warning(
                        "[ElevenLabsSFX] Failed to save sound, returning metadata only"
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
            logger.error(f"[ElevenLabsSFX] Error: {e}")
            import traceback
            traceback.print_exc()
            
            return ToolResult(
                success=False,
                error=f"Failed to generate sound effect: {str(e)}"
            )
