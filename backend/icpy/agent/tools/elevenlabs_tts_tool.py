"""
ElevenLabs Text-to-Speech Tool for agents

Converts text to lifelike speech using ElevenLabs API.
Follows existing tool patterns with namespaced path support.

Requires: ELEVENLABS_API_KEY environment variable

References:
- https://elevenlabs.io/docs/developers/guides/cookbooks/text-to-speech/quickstart
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

# Available voice IDs from ElevenLabs
# Default voices provided by ElevenLabs (can be expanded with custom voices)
DEFAULT_VOICES = {
    "george": "JBFqnCBsd6RMkjVDRZzb",  # Default male voice
    "rachel": "21m00Tcm4TlvDq8ikWAM",  # Female voice
    "adam": "pNInz6obpgDQGcFmaJgB",    # Male voice
    "antoni": "ErXwobaYiN019PkySvjV",  # Male voice
    "arnold": "VR6AewLTigWG4xSOukaG",  # Male voice
    "bella": "EXAVITQu4vr4xnSDxMaL",   # Female voice
    "domi": "AZnzlk1XvdvUeBnXmlld",    # Female voice
    "elli": "MF3mGyEYCl7XYWbV9V6O",    # Female voice
    "josh": "TxGEqnHWrfWFTfGW9XjX",    # Male voice
    "sam": "yoZ06aMxZJJ28mfd3POQ",     # Male voice
}

# Available models
AVAILABLE_MODELS = {
    "eleven_multilingual_v2": "Latest multilingual model, supports 29 languages",
    "eleven_turbo_v2_5": "Fastest English model, optimized for low latency",
    "eleven_turbo_v2": "Fast English model",
    "eleven_monolingual_v1": "Legacy English-only model",
    "eleven_multilingual_v1": "Legacy multilingual model",
}

# Output format options
OUTPUT_FORMATS = {
    "mp3_44100_128": "MP3 at 44.1kHz, 128kbps (default, good quality)",
    "mp3_44100_192": "MP3 at 44.1kHz, 192kbps (high quality)",
    "pcm_16000": "PCM at 16kHz (raw audio)",
    "pcm_22050": "PCM at 22.05kHz (raw audio)",
    "pcm_24000": "PCM at 24kHz (raw audio)",
    "pcm_44100": "PCM at 44.1kHz (raw audio)",
    "ulaw_8000": "μ-law at 8kHz (telephony)",
}


class ElevenLabsTTSTool(BaseTool):
    """
    Generate lifelike speech from text using ElevenLabs API.
    
    Capabilities:
        - Text-to-speech with multiple voice options
        - Multiple language support (with multilingual models)
        - Various output formats (MP3, PCM, etc.)
        - Save to workspace with custom filenames
        - Hop-aware for remote server support
    """
    
    def __init__(self):
        super().__init__()
        self.name = "text_to_speech"
        self.description = (
            "Generate lifelike speech from text using ElevenLabs API. "
            "Converts text to audio with natural-sounding voices. "
            "Supports multiple voices (built-in and custom), languages (with multilingual models), and output formats. "
            "Generated audio is saved to workspace and can be played in the media player. "
            "Use 'voice' parameter with voice name (e.g., 'george', 'rachel', 'bella', or custom voice names like 'tao2'). "
            "The tool will automatically look up custom voice names from your account. "
            "Alternatively, use 'voice_id' for direct voice ID if known. "
            "Use 'model_id' for language support - 'eleven_multilingual_v2' supports 29 languages. "
            "Returns file path to the generated audio file."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to convert to speech. Can be up to 5000 characters."
                },
                "voice": {
                    "type": "string",
                    "description": (
                        "Voice to use for speech. Can be a built-in voice name (george, rachel, bella, adam, etc.) "
                        "or a custom voice name from your ElevenLabs account (e.g., 'tao2'). "
                        "The tool automatically fetches and resolves custom voice names to IDs. "
                        "Default: 'george'."
                    )
                },
                "voice_id": {
                    "type": "string",
                    "description": "Optional explicit voice ID (overrides 'voice' parameter if provided)."
                },
                "model_id": {
                    "type": "string",
                    "enum": list(AVAILABLE_MODELS.keys()),
                    "description": (
                        "Model to use. 'eleven_multilingual_v2' for multi-language, "
                        "'eleven_turbo_v2_5' for fastest English. Default: 'eleven_multilingual_v2'."
                    )
                },
                "output_format": {
                    "type": "string",
                    "enum": list(OUTPUT_FORMATS.keys()),
                    "description": "Audio output format. Default: 'mp3_44100_128' (good quality MP3)."
                },
                "filename": {
                    "type": "string",
                    "description": (
                        "Optional custom filename (without extension). "
                        "If not provided, auto-generates from text and timestamp."
                    )
                },
                "save_to_workspace": {
                    "type": "boolean",
                    "description": "Whether to save the audio to workspace (default: true)."
                },
                "stability": {
                    "type": "number",
                    "description": (
                        "Voice stability (0.0-1.0). Higher = more consistent, "
                        "lower = more expressive. Default: 0.5."
                    )
                },
                "similarity_boost": {
                    "type": "number",
                    "description": (
                        "Voice clarity and similarity boost (0.0-1.0). "
                        "Higher = clearer, may reduce naturalness. Default: 0.75."
                    )
                },
                "style": {
                    "type": "number",
                    "description": (
                        "Style exaggeration (0.0-1.0). Higher = more expressive. "
                        "Only for multilingual v2 model. Default: 0.0."
                    )
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
        logger.info("ElevenLabs client initialized")
        return self._client
    
    def _fetch_available_voices(self) -> Dict[str, str]:
        """
        Fetch all available voices from the API (including custom voices).
        Returns a mapping of voice names (lowercase) to voice IDs.
        """
        try:
            client = self._get_client()
            
            # Get all voices from the API
            response = client.voices.get_all()
            
            # Build a name->ID mapping
            voice_map = {}
            if hasattr(response, 'voices'):
                for voice in response.voices:
                    if hasattr(voice, 'name') and hasattr(voice, 'voice_id'):
                        # Store lowercase name for case-insensitive lookup
                        voice_map[voice.name.lower()] = voice.voice_id
                        logger.debug(f"Found voice: {voice.name} -> {voice.voice_id}")
            
            logger.info(f"Fetched {len(voice_map)} voices from ElevenLabs API")
            return voice_map
            
        except Exception as e:
            logger.warning(f"Failed to fetch voices from API: {e}")
            return {}
    
    def _resolve_voice_id(self, voice: Optional[str], voice_id: Optional[str]) -> str:
        """
        Resolve voice name or ID to actual voice ID.
        
        Tries multiple strategies:
        1. Explicit voice_id parameter
        2. Default voices (built-in names)
        3. Fetch from API (for custom voices)
        4. Assume it's already a voice ID
        
        Args:
            voice: Voice name (e.g., 'george', 'rachel', 'tao2') or custom ID
            voice_id: Explicit voice ID (takes precedence)
            
        Returns:
            Resolved voice ID
        """
        # Explicit voice_id takes precedence
        if voice_id:
            return voice_id
        
        # No voice specified - use default
        if not voice:
            return DEFAULT_VOICES["george"]
        
        # Check if it's a known default voice name (case-insensitive)
        voice_lower = voice.lower()
        if voice_lower in DEFAULT_VOICES:
            return DEFAULT_VOICES[voice_lower]
        
        # Try to fetch from API for custom voices
        try:
            api_voices = self._fetch_available_voices()
            if voice_lower in api_voices:
                logger.info(f"Resolved custom voice '{voice}' to ID: {api_voices[voice_lower]}")
                return api_voices[voice_lower]
        except Exception as e:
            logger.warning(f"Could not fetch custom voices: {e}")
        
        # Assume it's already a custom voice ID (fallback)
        logger.info(f"Treating '{voice}' as a voice ID directly")
        return voice
    
    def _get_file_extension(self, output_format: str) -> str:
        """Get appropriate file extension for output format."""
        if output_format.startswith("mp3"):
            return ".mp3"
        elif output_format.startswith("pcm"):
            return ".wav"  # PCM is typically saved as WAV
        elif output_format.startswith("ulaw"):
            return ".ulaw"
        return ".mp3"  # Default
    
    async def _save_audio_to_workspace(
        self,
        audio_bytes: bytes,
        text: str,
        output_format: str,
        custom_filename: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """
        Save audio bytes to workspace folder (hop-aware).
        
        Args:
            audio_bytes: Binary audio data
            text: Original text (used for auto-generated filename)
            output_format: Audio format (determines file extension)
            custom_filename: Optional custom filename (without extension)
            
        Returns:
            Tuple of (relative_path, absolute_path) if successful, None otherwise.
        """
        try:
            # Determine file extension
            extension = self._get_file_extension(output_format)
            
            # Generate filename
            if custom_filename:
                # Sanitize custom filename
                safe_name = re.sub(r'[^\w\s-]', '', custom_filename).strip().replace(' ', '_')
                filename = f"{safe_name}{extension}"
            else:
                # Auto-generate from text and timestamp
                timestamp = int(datetime.now().timestamp())
                # Take first 30 chars of text for filename
                safe_text = re.sub(r'[^\w\s-]', '', text[:30]).strip().replace(' ', '_')
                if not safe_text:
                    safe_text = "speech"
                filename = f"tts_{safe_text}_{timestamp}{extension}"
            
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
                f"[ElevenLabsTTS] Target context: {context_name}, "
                f"filepath: {filepath}"
            )
            
            if context_name == 'local':
                # Write directly to local filesystem
                try:
                    with open(filepath, 'wb') as f:
                        f.write(audio_bytes)
                    logger.info(
                        f"[ElevenLabsTTS] Saved audio to {filepath} "
                        f"({len(audio_bytes)} bytes)"
                    )
                except Exception as e:
                    logger.error(f"[ElevenLabsTTS] Local write failed: {e}")
                    return None
            else:
                # Remote context: Write via SFTP
                try:
                    if hasattr(filesystem_service, 'write_file_binary'):
                        # Ensure remote directory exists
                        if hasattr(filesystem_service, 'create_directory'):
                            await filesystem_service.create_directory(sounds_dir)
                        await filesystem_service.write_file_binary(filepath, audio_bytes)
                        logger.info(
                            f"[ElevenLabsTTS] Saved audio to remote: {filepath}"
                        )
                    else:
                        logger.error(
                            "[ElevenLabsTTS] Remote filesystem doesn't support binary write"
                        )
                        return None
                except Exception as e:
                    logger.error(f"[ElevenLabsTTS] Remote write failed: {e}")
                    return None
            
            # Return relative and absolute paths
            relative_path = f"sounds/{filename}"
            return (relative_path, filepath)
            
        except Exception as e:
            logger.error(f"[ElevenLabsTTS] Failed to save audio: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute text-to-speech conversion.
        
        Args:
            text: Text to convert to speech (required)
            voice: Voice name or ID (default: 'george')
            voice_id: Explicit voice ID (overrides voice)
            model_id: Model to use (default: 'eleven_multilingual_v2')
            output_format: Audio format (default: 'mp3_44100_128')
            filename: Custom filename (without extension)
            save_to_workspace: Whether to save audio (default: True)
            stability: Voice stability 0.0-1.0 (default: 0.5)
            similarity_boost: Clarity boost 0.0-1.0 (default: 0.75)
            style: Style exaggeration 0.0-1.0 (default: 0.0)
            
        Returns:
            ToolResult with audio file path and metadata
        """
        # Extract parameters
        text = kwargs.get("text", "")
        voice = kwargs.get("voice")
        voice_id_param = kwargs.get("voice_id")
        model_id = kwargs.get("model_id", "eleven_multilingual_v2")
        output_format = kwargs.get("output_format", "mp3_44100_128")
        custom_filename = kwargs.get("filename")
        save_to_workspace = kwargs.get("save_to_workspace", True)
        stability = kwargs.get("stability", 0.5)
        similarity_boost = kwargs.get("similarity_boost", 0.75)
        style = kwargs.get("style", 0.0)
        
        # Validate required parameters
        if not text:
            return ToolResult(
                success=False,
                error="'text' parameter is required"
            )
        
        if len(text) > 5000:
            return ToolResult(
                success=False,
                error=f"Text too long ({len(text)} chars). Maximum is 5000 characters."
            )
        
        # Validate output format
        if output_format not in OUTPUT_FORMATS:
            return ToolResult(
                success=False,
                error=f"Invalid output_format. Valid options: {list(OUTPUT_FORMATS.keys())}"
            )
        
        # Validate model
        if model_id not in AVAILABLE_MODELS:
            return ToolResult(
                success=False,
                error=f"Invalid model_id. Valid options: {list(AVAILABLE_MODELS.keys())}"
            )
        
        try:
            # Get client
            client = self._get_client()
            
            # Resolve voice ID
            resolved_voice_id = self._resolve_voice_id(voice, voice_id_param)
            
            logger.info(
                f"[ElevenLabsTTS] Generating speech: "
                f"text_length={len(text)}, voice={resolved_voice_id}, "
                f"model={model_id}, format={output_format}"
            )
            
            # Generate speech using ElevenLabs API
            # The convert method returns an iterator of audio bytes
            audio_iterator = client.text_to_speech.convert(
                text=text,
                voice_id=resolved_voice_id,
                model_id=model_id,
                output_format=output_format,
                voice_settings={
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                    "style": style if model_id == "eleven_multilingual_v2" else 0.0,
                }
            )
            
            # Collect all audio bytes from iterator
            audio_bytes = b"".join(audio_iterator)
            
            if not audio_bytes:
                return ToolResult(
                    success=False,
                    error="No audio data received from ElevenLabs API"
                )
            
            logger.info(
                f"[ElevenLabsTTS] Received {len(audio_bytes)} bytes of audio"
            )
            
            # Prepare response data
            response_data = {
                "text_length": len(text),
                "voice_id": resolved_voice_id,
                "model_id": model_id,
                "output_format": output_format,
                "audio_size_bytes": len(audio_bytes),
            }
            
            # Save to workspace if requested
            if save_to_workspace:
                save_result = await self._save_audio_to_workspace(
                    audio_bytes=audio_bytes,
                    text=text,
                    output_format=output_format,
                    custom_filename=custom_filename
                )
                
                if save_result:
                    relative_path, absolute_path = save_result
                    response_data["saved"] = True
                    response_data["file_path"] = relative_path
                    response_data["absolute_path"] = absolute_path
                    response_data["audio_url"] = f"file://{absolute_path}"
                    logger.info(
                        f"[ElevenLabsTTS] Audio saved to: {absolute_path}"
                    )
                else:
                    response_data["saved"] = False
                    response_data["save_error"] = "Failed to save audio to workspace"
                    logger.warning(
                        "[ElevenLabsTTS] Failed to save audio, returning metadata only"
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
            logger.error(f"[ElevenLabsTTS] Error: {e}")
            import traceback
            traceback.print_exc()
            return ToolResult(
                success=False,
                error=f"Failed to generate speech: {str(e)}"
            )


# Export available voices and models for reference
def get_available_voices() -> Dict[str, str]:
    """Get dictionary of available voice names and their IDs."""
    return DEFAULT_VOICES.copy()


def get_available_models() -> Dict[str, str]:
    """Get dictionary of available models and their descriptions."""
    return AVAILABLE_MODELS.copy()


def get_output_formats() -> Dict[str, str]:
    """Get dictionary of available output formats and their descriptions."""
    return OUTPUT_FORMATS.copy()
