"""
Tests for ElevenLabs Speech-to-Text Tool

Tests STT functionality including:
- Audio file format validation
- Model validation
- Language code handling
- Transcription processing
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import os
from io import BytesIO

from icpy.agent.tools.elevenlabs_stt_tool import (
    ElevenLabsSTTTool,
    AVAILABLE_MODELS,
    SUPPORTED_AUDIO_FORMATS,
    COMMON_LANGUAGE_CODES,
    get_supported_formats,
    get_available_models,
    get_common_language_codes,
)
from icpy.agent.tools.base_tool import ToolResult


class TestElevenLabsSTTToolProperties:
    """Test tool initialization and properties"""
    
    def test_tool_properties(self):
        """Test tool has correct properties"""
        tool = ElevenLabsSTTTool()
        assert tool.name == "speech_to_text"
        assert "transcribe" in tool.description.lower() or "audio" in tool.description.lower()
        assert tool.parameters["type"] == "object"
        assert "filePath" in tool.parameters["properties"]
        assert "model_id" in tool.parameters["properties"]
        assert "language_code" in tool.parameters["properties"]
        assert "diarize" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["filePath"]
    
    def test_openai_function_format(self):
        """Test tool converts to OpenAI function format"""
        tool = ElevenLabsSTTTool()
        func = tool.to_openai_function()
        
        assert func["name"] == "speech_to_text"
        assert "description" in func
        assert "parameters" in func
        assert func["parameters"]["required"] == ["filePath"]
    
    def test_model_enum_in_parameters(self):
        """Test that model_id parameter has correct enum values"""
        tool = ElevenLabsSTTTool()
        model_param = tool.parameters["properties"]["model_id"]
        assert "enum" in model_param
        assert set(model_param["enum"]) == set(AVAILABLE_MODELS.keys())
    
    def test_timestamps_enum_in_parameters(self):
        """Test that timestamps parameter has correct enum values"""
        tool = ElevenLabsSTTTool()
        ts_param = tool.parameters["properties"]["timestamps"]
        assert "enum" in ts_param
        assert set(ts_param["enum"]) == {"none", "word", "segment"}


class TestAudioFormatValidation:
    """Test audio format detection and validation"""
    
    def test_supported_mp3_format(self):
        """Test MP3 is supported"""
        tool = ElevenLabsSTTTool()
        assert tool._is_supported_format("/path/to/audio.mp3") is True
        assert tool._is_supported_format("/path/to/audio.MP3") is True
    
    def test_supported_wav_format(self):
        """Test WAV is supported"""
        tool = ElevenLabsSTTTool()
        assert tool._is_supported_format("/path/to/audio.wav") is True
        assert tool._is_supported_format("/path/to/audio.WAV") is True
    
    def test_supported_other_formats(self):
        """Test other supported formats"""
        tool = ElevenLabsSTTTool()
        assert tool._is_supported_format("/path/audio.m4a") is True
        assert tool._is_supported_format("/path/audio.ogg") is True
        assert tool._is_supported_format("/path/audio.flac") is True
        assert tool._is_supported_format("/path/audio.aac") is True
        assert tool._is_supported_format("/path/audio.webm") is True
    
    def test_unsupported_format(self):
        """Test unsupported formats are rejected"""
        tool = ElevenLabsSTTTool()
        assert tool._is_supported_format("/path/to/video.mp4") is False
        assert tool._is_supported_format("/path/to/document.pdf") is False
        assert tool._is_supported_format("/path/to/image.png") is False
        assert tool._is_supported_format("/path/to/file.txt") is False


class TestInputValidation:
    """Test input validation"""
    
    @pytest.mark.asyncio
    async def test_missing_filepath(self):
        """Test error when filePath is missing"""
        tool = ElevenLabsSTTTool()
        result = await tool.execute()
        
        assert result.success is False
        assert "'filePath' parameter is required" in result.error
    
    @pytest.mark.asyncio
    async def test_empty_filepath(self):
        """Test error when filePath is empty"""
        tool = ElevenLabsSTTTool()
        result = await tool.execute(filePath="")
        
        assert result.success is False
        assert "'filePath' parameter is required" in result.error
    
    @pytest.mark.asyncio
    async def test_invalid_model(self):
        """Test error for invalid model"""
        tool = ElevenLabsSTTTool()
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/test/audio.mp3")):
            result = await tool.execute(filePath="/test/audio.mp3", model_id="invalid_model")
        
        assert result.success is False
        assert "Invalid model_id" in result.error
    
    @pytest.mark.asyncio
    async def test_invalid_timestamps_option(self):
        """Test error for invalid timestamps option"""
        tool = ElevenLabsSTTTool()
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/test/audio.mp3")):
            result = await tool.execute(filePath="/test/audio.mp3", timestamps="invalid")
        
        assert result.success is False
        assert "Invalid timestamps option" in result.error
    
    @pytest.mark.asyncio
    async def test_unsupported_audio_format(self):
        """Test error for unsupported audio format"""
        tool = ElevenLabsSTTTool()
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/test/file.pdf")):
            result = await tool.execute(filePath="/test/file.pdf")
        
        assert result.success is False
        assert "Unsupported audio format" in result.error


class TestClientInitialization:
    """Test ElevenLabs client initialization"""
    
    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        """Test error when API key is missing"""
        tool = ElevenLabsSTTTool()
        
        with patch.dict(os.environ, {}, clear=True):
            with patch('icpy.agent.tools.elevenlabs_stt_tool.ELEVENLABS_AVAILABLE', True):
                with patch.object(tool, '_parse_path_parameter', return_value=("local", "/test/audio.mp3")):
                    with patch.object(tool, '_read_audio_file', return_value=b"fake_audio"):
                        result = await tool.execute(filePath="/test/audio.mp3")
        
        assert result.success is False
        assert "ELEVENLABS_API_KEY" in result.error
    
    @pytest.mark.asyncio
    async def test_sdk_not_available(self):
        """Test error when ElevenLabs SDK is not installed"""
        tool = ElevenLabsSTTTool()
        
        with patch('icpy.agent.tools.elevenlabs_stt_tool.ELEVENLABS_AVAILABLE', False):
            with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_key'}):
                with patch.object(tool, '_parse_path_parameter', return_value=("local", "/test/audio.mp3")):
                    with patch.object(tool, '_read_audio_file', return_value=b"fake_audio"):
                        result = await tool.execute(filePath="/test/audio.mp3")
        
        assert result.success is False
        assert "ElevenLabs SDK not available" in result.error


class TestTranscription:
    """Test transcription functionality"""
    
    @pytest.mark.asyncio
    async def test_successful_transcription(self):
        """Test successful transcription"""
        tool = ElevenLabsSTTTool()
        
        # Mock transcription response
        mock_transcription = MagicMock()
        mock_transcription.text = "Hello world, this is a test."
        mock_transcription.language_code = "eng"
        mock_transcription.language_probability = 0.98
        mock_transcription.words = []
        mock_transcription.audio_events = []
        mock_transcription.speakers = []
        
        mock_client = MagicMock()
        mock_client.speech_to_text.convert.return_value = mock_transcription
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            with patch.object(tool, '_parse_path_parameter', return_value=("local", "/test/audio.mp3")):
                with patch.object(tool, '_read_audio_file', return_value=b"fake_audio_bytes"):
                    result = await tool.execute(filePath="/test/audio.mp3")
        
        assert result.success is True
        assert result.data["text"] == "Hello world, this is a test."
        assert result.data["language_code"] == "eng"
        assert result.data["model_id"] == "scribe_v2"
    
    @pytest.mark.asyncio
    async def test_transcription_with_language_code(self):
        """Test transcription with specific language"""
        tool = ElevenLabsSTTTool()
        
        mock_transcription = MagicMock()
        mock_transcription.text = "Hola mundo"
        mock_transcription.language_code = "spa"
        mock_transcription.words = []
        mock_transcription.audio_events = []
        mock_transcription.speakers = []
        
        mock_client = MagicMock()
        mock_client.speech_to_text.convert.return_value = mock_transcription
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            with patch.object(tool, '_parse_path_parameter', return_value=("local", "/test/audio.mp3")):
                with patch.object(tool, '_read_audio_file', return_value=b"fake_audio"):
                    result = await tool.execute(
                        filePath="/test/audio.mp3",
                        language_code="spa"
                    )
        
        assert result.success is True
        assert result.data["text"] == "Hola mundo"
        
        # Verify language_code was passed to API
        call_kwargs = mock_client.speech_to_text.convert.call_args[1]
        assert call_kwargs["language_code"] == "spa"
    
    @pytest.mark.asyncio
    async def test_transcription_with_diarization(self):
        """Test transcription with speaker diarization"""
        tool = ElevenLabsSTTTool()
        
        mock_transcription = MagicMock()
        mock_transcription.text = "Hello. Hi there."
        mock_transcription.language_code = "eng"
        mock_transcription.words = []
        mock_transcription.audio_events = []
        
        # Mock speakers
        speaker1 = MagicMock()
        speaker1.speaker_id = "speaker_1"
        speaker1.name = None
        speaker2 = MagicMock()
        speaker2.speaker_id = "speaker_2"
        speaker2.name = None
        mock_transcription.speakers = [speaker1, speaker2]
        
        mock_client = MagicMock()
        mock_client.speech_to_text.convert.return_value = mock_transcription
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            with patch.object(tool, '_parse_path_parameter', return_value=("local", "/test/audio.mp3")):
                with patch.object(tool, '_read_audio_file', return_value=b"fake_audio"):
                    result = await tool.execute(
                        filePath="/test/audio.mp3",
                        diarize=True
                    )
        
        assert result.success is True
        assert "speakers" in result.data
        assert len(result.data["speakers"]) == 2
        
        # Verify diarize was passed to API
        call_kwargs = mock_client.speech_to_text.convert.call_args[1]
        assert call_kwargs["diarize"] is True
    
    @pytest.mark.asyncio
    async def test_transcription_with_audio_events(self):
        """Test transcription with audio event tagging"""
        tool = ElevenLabsSTTTool()
        
        mock_transcription = MagicMock()
        mock_transcription.text = "That was funny [laughter]"
        mock_transcription.language_code = "eng"
        mock_transcription.words = []
        mock_transcription.speakers = []
        
        # Mock audio events
        event = MagicMock()
        event.type = "laughter"
        event.start = 2.5
        event.end = 3.5
        mock_transcription.audio_events = [event]
        
        mock_client = MagicMock()
        mock_client.speech_to_text.convert.return_value = mock_transcription
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            with patch.object(tool, '_parse_path_parameter', return_value=("local", "/test/audio.mp3")):
                with patch.object(tool, '_read_audio_file', return_value=b"fake_audio"):
                    result = await tool.execute(
                        filePath="/test/audio.mp3",
                        tag_audio_events=True
                    )
        
        assert result.success is True
        assert "audio_events" in result.data
        assert len(result.data["audio_events"]) == 1
        assert result.data["audio_events"][0]["type"] == "laughter"
    
    @pytest.mark.asyncio
    async def test_transcription_with_word_timestamps(self):
        """Test transcription with word-level timestamps"""
        tool = ElevenLabsSTTTool()
        
        mock_transcription = MagicMock()
        mock_transcription.text = "Hello world"
        mock_transcription.language_code = "eng"
        mock_transcription.audio_events = []
        mock_transcription.speakers = []
        
        # Mock words with timestamps
        word1 = MagicMock()
        word1.text = "Hello"
        word1.start = 0.0
        word1.end = 0.5
        word2 = MagicMock()
        word2.text = "world"
        word2.start = 0.6
        word2.end = 1.0
        mock_transcription.words = [word1, word2]
        
        mock_client = MagicMock()
        mock_client.speech_to_text.convert.return_value = mock_transcription
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            with patch.object(tool, '_parse_path_parameter', return_value=("local", "/test/audio.mp3")):
                with patch.object(tool, '_read_audio_file', return_value=b"fake_audio"):
                    result = await tool.execute(
                        filePath="/test/audio.mp3",
                        timestamps="word"
                    )
        
        assert result.success is True
        assert "words" in result.data
        assert len(result.data["words"]) == 2
        assert result.data["words"][0]["text"] == "Hello"
        assert result.data["words"][0]["start"] == 0.0
    
    @pytest.mark.asyncio
    async def test_file_read_failure(self):
        """Test error when file cannot be read"""
        tool = ElevenLabsSTTTool()
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/test/audio.mp3")):
            with patch.object(tool, '_read_audio_file', return_value=None):
                result = await tool.execute(filePath="/test/audio.mp3")
        
        assert result.success is False
        assert "Failed to read audio file" in result.error


class TestSegmentGrouping:
    """Test segment grouping logic"""
    
    def test_group_words_into_segments(self):
        """Test grouping words into segments"""
        tool = ElevenLabsSTTTool()
        
        words = [
            {"text": "Hello", "start": 0.0, "end": 0.3},
            {"text": "world.", "start": 0.4, "end": 0.8},
            {"text": "How", "start": 1.5, "end": 1.7},  # Pause > 0.5s
            {"text": "are", "start": 1.8, "end": 2.0},
            {"text": "you?", "start": 2.1, "end": 2.5},
        ]
        
        segments = tool._group_into_segments(words)
        
        # Should create segments based on punctuation and pauses
        assert len(segments) >= 2
        assert "Hello" in segments[0]["text"]
    
    def test_empty_words_returns_empty_segments(self):
        """Test empty words list returns empty segments"""
        tool = ElevenLabsSTTTool()
        segments = tool._group_into_segments([])
        assert segments == []


class TestHelperFunctions:
    """Test module-level helper functions"""
    
    def test_get_supported_formats(self):
        """Test getting supported formats"""
        formats = get_supported_formats()
        
        assert isinstance(formats, list)
        assert ".mp3" in formats
        assert ".wav" in formats
        assert ".m4a" in formats
    
    def test_get_available_models(self):
        """Test getting available models"""
        models = get_available_models()
        
        assert isinstance(models, dict)
        assert "scribe_v2" in models
        assert "scribe_v1" in models
    
    def test_get_common_language_codes(self):
        """Test getting common language codes"""
        languages = get_common_language_codes()
        
        assert isinstance(languages, dict)
        assert "eng" in languages
        assert languages["eng"] == "English"
        assert "spa" in languages
        assert "fra" in languages


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test handling of API errors"""
        tool = ElevenLabsSTTTool()
        
        mock_client = MagicMock()
        mock_client.speech_to_text.convert.side_effect = Exception("API Error: Rate limit exceeded")
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            with patch.object(tool, '_parse_path_parameter', return_value=("local", "/test/audio.mp3")):
                with patch.object(tool, '_read_audio_file', return_value=b"fake_audio"):
                    result = await tool.execute(filePath="/test/audio.mp3")
        
        assert result.success is False
        assert "Failed to transcribe audio" in result.error


class TestRawOutput:
    """Test raw output mode"""
    
    @pytest.mark.asyncio
    async def test_return_raw_response(self):
        """Test returning raw API response"""
        tool = ElevenLabsSTTTool()
        
        mock_transcription = MagicMock()
        mock_transcription.text = "Hello world"
        mock_transcription.model_dump.return_value = {
            "text": "Hello world",
            "language_code": "eng",
            "raw_field": "some_value"
        }
        
        mock_client = MagicMock()
        mock_client.speech_to_text.convert.return_value = mock_transcription
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            with patch.object(tool, '_parse_path_parameter', return_value=("local", "/test/audio.mp3")):
                with patch.object(tool, '_read_audio_file', return_value=b"fake_audio"):
                    result = await tool.execute(
                        filePath="/test/audio.mp3",
                        return_raw=True
                    )
        
        assert result.success is True
        # Raw response should include model_dump output
        assert "text" in result.data
