"""
ElevenLabs Speech-to-Text Tool for agents

Converts spoken audio to text using ElevenLabs Scribe API.
Follows existing tool patterns with namespaced path support.

Requires: ELEVENLABS_API_KEY environment variable

References:
- https://elevenlabs.io/docs/developers/guides/cookbooks/speech-to-text/quickstart
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional
from io import BytesIO

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

# Available models for speech-to-text
AVAILABLE_MODELS = {
    "scribe_v2": "Latest Scribe model - best accuracy, supports 99 languages",
    "scribe_v1": "Legacy Scribe model",
}

# Supported audio formats
SUPPORTED_AUDIO_FORMATS = [
    ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".wma", ".webm"
]

# Common language codes (subset of 99 supported languages)
COMMON_LANGUAGE_CODES = {
    "eng": "English",
    "spa": "Spanish",
    "fra": "French",
    "deu": "German",
    "ita": "Italian",
    "por": "Portuguese",
    "rus": "Russian",
    "jpn": "Japanese",
    "kor": "Korean",
    "zho": "Chinese",
    "ara": "Arabic",
    "hin": "Hindi",
    "tha": "Thai",
    "vie": "Vietnamese",
    "nld": "Dutch",
    "pol": "Polish",
    "tur": "Turkish",
    "swe": "Swedish",
    "dan": "Danish",
    "fin": "Finnish",
    "nor": "Norwegian",
    "ell": "Greek",
    "heb": "Hebrew",
    "ind": "Indonesian",
    "ukr": "Ukrainian",
}


class ElevenLabsSTTTool(BaseTool):
    """
    Transcribe audio to text using ElevenLabs Scribe API.
    
    Capabilities:
        - Speech-to-text transcription with high accuracy
        - Support for 99 languages with auto-detection
        - Speaker diarization (who is speaking)
        - Audio event tagging (laughter, applause, etc.)
        - Timestamp generation for each word/segment
        - Hop-aware for reading files from remote servers
    """
    
    def __init__(self):
        super().__init__()
        self.name = "speech_to_text"
        self.description = (
            "Transcribe audio files to text using ElevenLabs Scribe API. "
            "Converts spoken audio into accurate text transcription. "
            "Supports 99 languages with auto-detection (omit language_code parameter) or explicit language selection. "
            "Input: path to audio file (mp3, wav, m4a, ogg, flac, aac, wma, webm). "
            "For specific language, use 'language_code' (e.g., 'eng', 'spa', 'fra'). "
            "For auto-detection, do not include language_code parameter at all. "
            "Returns transcribed text with optional timestamps and speaker labels."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "filePath": {
                    "type": "string",
                    "description": (
                        "Path to the audio file to transcribe. "
                        "Accepts optional namespace prefix (e.g., local:/audio.mp3, hop1:/recordings/meeting.wav). "
                        "Supported formats: mp3, wav, m4a, ogg, flac, aac, wma, webm."
                    )
                },
                "model_id": {
                    "type": "string",
                    "enum": list(AVAILABLE_MODELS.keys()),
                    "description": "Model to use. 'scribe_v2' (default) is the latest with best accuracy."
                },
                "language_code": {
                    "type": "string",
                    "description": (
                        "Language code (ISO 639-3) of the audio. Examples: 'eng' (English), "
                        "'spa' (Spanish), 'fra' (French), 'deu' (German), 'jpn' (Japanese). "
                        "IMPORTANT: Omit this parameter entirely (do not include it in the request) "
                        "for automatic language detection. Do not pass empty string."
                    )
                },
                "diarize": {
                    "type": "boolean",
                    "description": (
                        "Enable speaker diarization to identify who is speaking. "
                        "Default: false. Set to true for multi-speaker audio."
                    )
                },
                "tag_audio_events": {
                    "type": "boolean",
                    "description": (
                        "Tag audio events like laughter, applause, music, etc. "
                        "Default: false."
                    )
                },
                "timestamps": {
                    "type": "string",
                    "enum": ["none", "word", "segment"],
                    "description": (
                        "Timestamp granularity: 'none' (default), 'word' (per word), "
                        "or 'segment' (per sentence/segment)."
                    )
                },
                "return_raw": {
                    "type": "boolean",
                    "description": (
                        "Return raw API response with all metadata. "
                        "Default: false (returns simplified text output)."
                    )
                }
            },
            "required": ["filePath"]
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
        logger.info("ElevenLabs client initialized for STT")
        return self._client
    
    def _is_supported_format(self, file_path: str) -> bool:
        """Check if the file format is supported."""
        ext = os.path.splitext(file_path.lower())[1]
        return ext in SUPPORTED_AUDIO_FORMATS
    
    async def _read_audio_file(self, file_path: str, context_id: str) -> Optional[bytes]:
        """
        Read audio file bytes from local or remote context.
        
        Args:
            file_path: Absolute path to the audio file
            context_id: Context identifier (local or hop name)
            
        Returns:
            Audio bytes if successful, None otherwise
        """
        try:
            if context_id == 'local':
                # Read from local filesystem
                if not os.path.exists(file_path):
                    logger.error(f"[ElevenLabsSTT] File not found: {file_path}")
                    return None
                
                with open(file_path, 'rb') as f:
                    audio_bytes = f.read()
                
                logger.info(f"[ElevenLabsSTT] Read {len(audio_bytes)} bytes from {file_path}")
                return audio_bytes
            else:
                # Read from remote context via SFTP
                filesystem_service = await get_contextual_filesystem()
                
                if hasattr(filesystem_service, 'read_file_binary'):
                    audio_bytes = await filesystem_service.read_file_binary(file_path)
                    logger.info(
                        f"[ElevenLabsSTT] Read {len(audio_bytes)} bytes from remote: {file_path}"
                    )
                    return audio_bytes
                else:
                    logger.error(
                        "[ElevenLabsSTT] Remote filesystem doesn't support binary read"
                    )
                    return None
                    
        except Exception as e:
            logger.error(f"[ElevenLabsSTT] Failed to read audio file: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _format_transcription(
        self,
        transcription: Any,
        include_timestamps: str,
        include_speakers: bool
    ) -> Dict[str, Any]:
        """
        Format transcription response into structured output.
        
        Args:
            transcription: Raw API response
            include_timestamps: Timestamp granularity
            include_speakers: Whether to include speaker labels
            
        Returns:
            Formatted transcription data
        """
        result: Dict[str, Any] = {}
        
        # Extract main text
        if hasattr(transcription, 'text'):
            result["text"] = transcription.text
        elif isinstance(transcription, dict) and 'text' in transcription:
            result["text"] = transcription['text']
        else:
            result["text"] = str(transcription)
        
        # Extract language info
        if hasattr(transcription, 'language_code'):
            result["language_code"] = transcription.language_code
        if hasattr(transcription, 'language_probability'):
            result["language_confidence"] = transcription.language_probability
        
        # Extract words with timestamps if requested
        if include_timestamps != "none" and hasattr(transcription, 'words'):
            words_data = []
            for word in transcription.words:
                word_info = {
                    "text": getattr(word, 'text', str(word)),
                }
                if hasattr(word, 'start'):
                    word_info["start"] = word.start
                if hasattr(word, 'end'):
                    word_info["end"] = word.end
                if include_speakers and hasattr(word, 'speaker_id'):
                    word_info["speaker"] = word.speaker_id
                words_data.append(word_info)
            
            if include_timestamps == "word":
                result["words"] = words_data
            elif include_timestamps == "segment":
                # Group words into segments
                result["segments"] = self._group_into_segments(words_data)
        
        # Extract audio events if present
        if hasattr(transcription, 'audio_events') and transcription.audio_events:
            result["audio_events"] = [
                {
                    "type": getattr(event, 'type', 'unknown'),
                    "start": getattr(event, 'start', None),
                    "end": getattr(event, 'end', None),
                }
                for event in transcription.audio_events
            ]
        
        # Extract speakers if diarization was enabled
        if hasattr(transcription, 'speakers') and transcription.speakers:
            result["speakers"] = [
                {
                    "id": getattr(speaker, 'speaker_id', f'speaker_{i}'),
                    "name": getattr(speaker, 'name', None),
                }
                for i, speaker in enumerate(transcription.speakers)
            ]
        
        return result
    
    def _group_into_segments(self, words: List[Dict]) -> List[Dict]:
        """Group words into sentence-like segments based on pauses."""
        if not words:
            return []
        
        segments = []
        current_segment = {
            "text": "",
            "words": [],
            "start": words[0].get("start"),
        }
        
        for i, word in enumerate(words):
            current_segment["words"].append(word)
            current_segment["text"] += word["text"] + " "
            
            # Check for segment break (pause > 0.5s or punctuation)
            is_last = i == len(words) - 1
            has_pause = False
            
            if not is_last and "end" in word and "start" in words[i + 1]:
                pause = words[i + 1]["start"] - word["end"]
                has_pause = pause > 0.5
            
            has_punctuation = word["text"].rstrip().endswith(('.', '!', '?', ':', ';'))
            
            if is_last or has_pause or has_punctuation:
                current_segment["text"] = current_segment["text"].strip()
                current_segment["end"] = word.get("end")
                segments.append(current_segment)
                
                if not is_last:
                    current_segment = {
                        "text": "",
                        "words": [],
                        "start": words[i + 1].get("start"),
                    }
        
        return segments
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute speech-to-text transcription.
        
        Args:
            filePath: Path to audio file (required)
            model_id: Model to use (default: 'scribe_v2')
            language_code: Language code or None for auto-detection
            diarize: Enable speaker diarization (default: False)
            tag_audio_events: Tag audio events (default: False)
            timestamps: Timestamp granularity: 'none', 'word', 'segment'
            return_raw: Return raw API response (default: False)
            
        Returns:
            ToolResult with transcribed text and metadata
        """
        # Extract parameters
        file_path = kwargs.get("filePath", "")
        model_id = kwargs.get("model_id", "scribe_v2")
        language_code = kwargs.get("language_code")
        diarize = kwargs.get("diarize", False)
        tag_audio_events = kwargs.get("tag_audio_events", False)
        timestamps = kwargs.get("timestamps", "none")
        return_raw = kwargs.get("return_raw", False)
        
        # Validate required parameters
        if not file_path:
            return ToolResult(
                success=False,
                error="'filePath' parameter is required"
            )
        
        # Validate model
        if model_id not in AVAILABLE_MODELS:
            return ToolResult(
                success=False,
                error=f"Invalid model_id. Valid options: {list(AVAILABLE_MODELS.keys())}"
            )
        
        # Validate timestamps option
        if timestamps not in ["none", "word", "segment"]:
            return ToolResult(
                success=False,
                error="Invalid timestamps option. Valid options: 'none', 'word', 'segment'"
            )
        
        try:
            # Parse namespaced path
            ctx_id, abs_path = await self._parse_path_parameter(file_path)
            
            logger.info(
                f"[ElevenLabsSTT] Transcribing: {abs_path} (context: {ctx_id})"
            )
            
            # Check file format
            if not self._is_supported_format(abs_path):
                return ToolResult(
                    success=False,
                    error=f"Unsupported audio format. Supported: {', '.join(SUPPORTED_AUDIO_FORMATS)}"
                )
            
            # Read audio file
            audio_bytes = await self._read_audio_file(abs_path, ctx_id)
            
            if not audio_bytes:
                return ToolResult(
                    success=False,
                    error=f"Failed to read audio file: {abs_path}"
                )
            
            # Get client
            client = self._get_client()
            
            # Prepare audio data
            audio_data = BytesIO(audio_bytes)
            
            # Get filename for the API
            filename = os.path.basename(abs_path)
            
            logger.info(
                f"[ElevenLabsSTT] Sending {len(audio_bytes)} bytes to API: "
                f"model={model_id}, language={language_code or 'auto'}, "
                f"diarize={diarize}, tag_events={tag_audio_events}"
            )
            
            # Call ElevenLabs Speech-to-Text API
            transcription = client.speech_to_text.convert(
                file=audio_data,
                model_id=model_id,
                language_code=language_code,  # None for auto-detection
                diarize=diarize,
                tag_audio_events=tag_audio_events,
            )
            
            logger.info("[ElevenLabsSTT] Transcription received")
            
            # Format response
            if return_raw:
                # Return raw response (convert to dict if needed)
                if hasattr(transcription, 'model_dump'):
                    response_data = transcription.model_dump()
                elif hasattr(transcription, '__dict__'):
                    response_data = transcription.__dict__
                else:
                    response_data = {"raw": str(transcription)}
            else:
                # Format nicely
                response_data = self._format_transcription(
                    transcription=transcription,
                    include_timestamps=timestamps,
                    include_speakers=diarize
                )
            
            # Add metadata
            response_data["source_file"] = abs_path
            response_data["model_id"] = model_id
            response_data["audio_size_bytes"] = len(audio_bytes)
            
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
            logger.error(f"[ElevenLabsSTT] Error: {e}")
            import traceback
            traceback.print_exc()
            return ToolResult(
                success=False,
                error=f"Failed to transcribe audio: {str(e)}"
            )


# Export helper functions
def get_supported_formats() -> List[str]:
    """Get list of supported audio formats."""
    return SUPPORTED_AUDIO_FORMATS.copy()


def get_available_models() -> Dict[str, str]:
    """Get dictionary of available models and their descriptions."""
    return AVAILABLE_MODELS.copy()


def get_common_language_codes() -> Dict[str, str]:
    """Get dictionary of common language codes and their names."""
    return COMMON_LANGUAGE_CODES.copy()
