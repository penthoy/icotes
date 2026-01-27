"""
Tests for ElevenLabs Text-to-Speech Tool

Tests TTS functionality including:
- Voice selection and resolution
- Model validation
- Output format handling
- Audio generation and saving
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import os

from icpy.agent.tools.elevenlabs_tts_tool import (
    ElevenLabsTTSTool,
    DEFAULT_VOICES,
    AVAILABLE_MODELS,
    OUTPUT_FORMATS,
    get_available_voices,
    get_available_models,
    get_output_formats,
)
from icpy.agent.tools.base_tool import ToolResult


class TestElevenLabsTTSToolProperties:
    """Test tool initialization and properties"""
    
    def test_tool_properties(self):
        """Test tool has correct properties"""
        tool = ElevenLabsTTSTool()
        assert tool.name == "text_to_speech"
        assert "ElevenLabs" in tool.description
        assert "speech" in tool.description.lower()
        assert tool.parameters["type"] == "object"
        assert "text" in tool.parameters["properties"]
        assert "voice" in tool.parameters["properties"]
        assert "model_id" in tool.parameters["properties"]
        assert "output_format" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["text"]
    
    def test_openai_function_format(self):
        """Test tool converts to OpenAI function format"""
        tool = ElevenLabsTTSTool()
        func = tool.to_openai_function()
        
        assert func["name"] == "text_to_speech"
        assert "description" in func
        assert "parameters" in func
        assert func["parameters"]["required"] == ["text"]
    
    def test_model_enum_in_parameters(self):
        """Test that model_id parameter has correct enum values"""
        tool = ElevenLabsTTSTool()
        model_param = tool.parameters["properties"]["model_id"]
        assert "enum" in model_param
        assert set(model_param["enum"]) == set(AVAILABLE_MODELS.keys())
    
    def test_output_format_enum_in_parameters(self):
        """Test that output_format parameter has correct enum values"""
        tool = ElevenLabsTTSTool()
        format_param = tool.parameters["properties"]["output_format"]
        assert "enum" in format_param
        assert set(format_param["enum"]) == set(OUTPUT_FORMATS.keys())


class TestVoiceResolution:
    """Test voice name/ID resolution"""
    
    def test_resolve_voice_by_name(self):
        """Test resolving voice by name"""
        tool = ElevenLabsTTSTool()
        
        # Test known voice names
        assert tool._resolve_voice_id("george", None) == DEFAULT_VOICES["george"]
        assert tool._resolve_voice_id("rachel", None) == DEFAULT_VOICES["rachel"]
        assert tool._resolve_voice_id("bella", None) == DEFAULT_VOICES["bella"]
    
    def test_resolve_voice_case_insensitive(self):
        """Test voice names are case-insensitive"""
        tool = ElevenLabsTTSTool()
        
        assert tool._resolve_voice_id("George", None) == DEFAULT_VOICES["george"]
        assert tool._resolve_voice_id("RACHEL", None) == DEFAULT_VOICES["rachel"]
        assert tool._resolve_voice_id("BeLLa", None) == DEFAULT_VOICES["bella"]
    
    def test_resolve_explicit_voice_id(self):
        """Test explicit voice_id takes precedence"""
        tool = ElevenLabsTTSTool()
        custom_id = "custom_voice_123"
        
        # voice_id should override voice name
        assert tool._resolve_voice_id("george", custom_id) == custom_id
        assert tool._resolve_voice_id(None, custom_id) == custom_id
    
    def test_resolve_custom_voice_id(self):
        """Test unknown voice names are treated as custom IDs"""
        tool = ElevenLabsTTSTool()
        custom_id = "my_custom_voice_xyz"
        
        # Unknown voice name should be treated as ID
        assert tool._resolve_voice_id(custom_id, None) == custom_id
    
    def test_fetch_custom_voice_from_api(self):
        """Test fetching custom voice from API"""
        tool = ElevenLabsTTSTool()
        
        # Mock the API response
        mock_voice = MagicMock()
        mock_voice.name = "Tao2"
        mock_voice.voice_id = "custom_voice_id_123"
        
        mock_response = MagicMock()
        mock_response.voices = [mock_voice]
        
        mock_client = MagicMock()
        mock_client.voices.get_all.return_value = mock_response
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            voice_id = tool._resolve_voice_id("tao2", None)
        
        # Should resolve to the custom voice ID
        assert voice_id == "custom_voice_id_123"
    
    def test_resolve_default_voice(self):
        """Test default voice when none specified"""
        tool = ElevenLabsTTSTool()
        
        # No voice specified should return default (george)
        assert tool._resolve_voice_id(None, None) == DEFAULT_VOICES["george"]


class TestFileExtensionResolution:
    """Test file extension determination"""
    
    def test_mp3_extension(self):
        """Test MP3 formats return .mp3"""
        tool = ElevenLabsTTSTool()
        
        assert tool._get_file_extension("mp3_44100_128") == ".mp3"
        assert tool._get_file_extension("mp3_44100_192") == ".mp3"
    
    def test_pcm_extension(self):
        """Test PCM formats return .wav"""
        tool = ElevenLabsTTSTool()
        
        assert tool._get_file_extension("pcm_16000") == ".wav"
        assert tool._get_file_extension("pcm_22050") == ".wav"
        assert tool._get_file_extension("pcm_44100") == ".wav"
    
    def test_ulaw_extension(self):
        """Test μ-law format returns .ulaw"""
        tool = ElevenLabsTTSTool()
        
        assert tool._get_file_extension("ulaw_8000") == ".ulaw"
    
    def test_unknown_extension_default(self):
        """Test unknown format defaults to .mp3"""
        tool = ElevenLabsTTSTool()
        
        assert tool._get_file_extension("unknown_format") == ".mp3"


class TestInputValidation:
    """Test input validation"""
    
    @pytest.mark.asyncio
    async def test_missing_text(self):
        """Test error when text is missing"""
        tool = ElevenLabsTTSTool()
        result = await tool.execute()
        
        assert result.success is False
        assert "'text' parameter is required" in result.error
    
    @pytest.mark.asyncio
    async def test_empty_text(self):
        """Test error when text is empty"""
        tool = ElevenLabsTTSTool()
        result = await tool.execute(text="")
        
        assert result.success is False
        assert "'text' parameter is required" in result.error
    
    @pytest.mark.asyncio
    async def test_text_too_long(self):
        """Test error when text exceeds 5000 characters"""
        tool = ElevenLabsTTSTool()
        long_text = "x" * 5001
        result = await tool.execute(text=long_text)
        
        assert result.success is False
        assert "Text too long" in result.error
        assert "5001 chars" in result.error
    
    @pytest.mark.asyncio
    async def test_invalid_output_format(self):
        """Test error for invalid output format"""
        tool = ElevenLabsTTSTool()
        result = await tool.execute(text="Hello", output_format="invalid_format")
        
        assert result.success is False
        assert "Invalid output_format" in result.error
    
    @pytest.mark.asyncio
    async def test_invalid_model(self):
        """Test error for invalid model"""
        tool = ElevenLabsTTSTool()
        result = await tool.execute(text="Hello", model_id="invalid_model")
        
        assert result.success is False
        assert "Invalid model_id" in result.error


class TestClientInitialization:
    """Test ElevenLabs client initialization"""
    
    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        """Test error when API key is missing"""
        tool = ElevenLabsTTSTool()
        
        # Ensure API key is not set
        with patch.dict(os.environ, {}, clear=True):
            with patch('icpy.agent.tools.elevenlabs_tts_tool.ELEVENLABS_AVAILABLE', True):
                result = await tool.execute(text="Hello world")
        
        assert result.success is False
        assert "ELEVENLABS_API_KEY" in result.error
    
    @pytest.mark.asyncio
    async def test_sdk_not_available(self):
        """Test error when ElevenLabs SDK is not installed"""
        tool = ElevenLabsTTSTool()
        
        with patch('icpy.agent.tools.elevenlabs_tts_tool.ELEVENLABS_AVAILABLE', False):
            with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_key'}):
                result = await tool.execute(text="Hello world")
        
        assert result.success is False
        assert "ElevenLabs SDK not available" in result.error


class TestSpeechGeneration:
    """Test speech generation functionality"""
    
    @pytest.mark.asyncio
    async def test_successful_generation(self):
        """Test successful speech generation"""
        tool = ElevenLabsTTSTool()
        
        # Mock audio data
        mock_audio = b"fake_audio_data_bytes"
        
        # Mock client and its convert method
        mock_client = MagicMock()
        mock_client.text_to_speech.convert.return_value = [mock_audio]
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            with patch.object(tool, '_save_audio_to_workspace', return_value=("sounds/test.mp3", "/workspace/sounds/test.mp3")):
                result = await tool.execute(
                    text="Hello world",
                    voice="george",
                    model_id="eleven_multilingual_v2"
                )
        
        assert result.success is True
        assert result.data["text_length"] == 11
        assert result.data["voice_id"] == DEFAULT_VOICES["george"]
        assert result.data["model_id"] == "eleven_multilingual_v2"
        assert result.data["saved"] is True
        assert result.data["file_path"] == "sounds/test.mp3"
    
    @pytest.mark.asyncio
    async def test_generation_with_custom_voice_id(self):
        """Test generation with custom voice ID"""
        tool = ElevenLabsTTSTool()
        custom_voice = "custom_voice_abc123"
        mock_audio = b"fake_audio_data"
        
        mock_client = MagicMock()
        mock_client.text_to_speech.convert.return_value = [mock_audio]
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            with patch.object(tool, '_save_audio_to_workspace', return_value=None):
                result = await tool.execute(
                    text="Test",
                    voice_id=custom_voice,
                    save_to_workspace=False
                )
        
        assert result.success is True
        assert result.data["voice_id"] == custom_voice
    
    @pytest.mark.asyncio
    async def test_generation_without_saving(self):
        """Test generation without saving to workspace"""
        tool = ElevenLabsTTSTool()
        mock_audio = b"fake_audio_data"
        
        mock_client = MagicMock()
        mock_client.text_to_speech.convert.return_value = [mock_audio]
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            result = await tool.execute(
                text="Hello",
                save_to_workspace=False
            )
        
        assert result.success is True
        assert result.data["saved"] is False
        assert "file_path" not in result.data
    
    @pytest.mark.asyncio
    async def test_voice_settings_passed_correctly(self):
        """Test voice settings are passed to API"""
        tool = ElevenLabsTTSTool()
        mock_audio = b"fake_audio"
        
        mock_client = MagicMock()
        mock_client.text_to_speech.convert.return_value = [mock_audio]
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            with patch.object(tool, '_save_audio_to_workspace', return_value=None):
                await tool.execute(
                    text="Test",
                    stability=0.8,
                    similarity_boost=0.6,
                    style=0.3,
                    save_to_workspace=False
                )
        
        # Verify voice_settings were passed
        call_kwargs = mock_client.text_to_speech.convert.call_args[1]
        assert call_kwargs["voice_settings"]["stability"] == 0.8
        assert call_kwargs["voice_settings"]["similarity_boost"] == 0.6
        assert call_kwargs["voice_settings"]["style"] == 0.3
    
    @pytest.mark.asyncio
    async def test_empty_audio_response(self):
        """Test error when API returns no audio"""
        tool = ElevenLabsTTSTool()
        
        mock_client = MagicMock()
        mock_client.text_to_speech.convert.return_value = []  # Empty response
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            result = await tool.execute(text="Hello")
        
        assert result.success is False
        assert "No audio data received" in result.error


class TestAudioSaving:
    """Test audio file saving"""
    
    @pytest.mark.asyncio
    async def test_save_with_custom_filename(self):
        """Test saving with custom filename"""
        tool = ElevenLabsTTSTool()
        audio_bytes = b"test_audio_data"
        
        mock_context = {'contextId': 'local'}
        mock_fs = MagicMock()
        mock_fs.root_path = "/workspace"
        
        with patch('icpy.agent.tools.elevenlabs_tts_tool.get_current_context', return_value=mock_context):
            with patch('icpy.agent.tools.elevenlabs_tts_tool.get_contextual_filesystem', return_value=mock_fs):
                with patch('os.makedirs'):
                    with patch('builtins.open', mock_open()):
                        result = await tool._save_audio_to_workspace(
                            audio_bytes=audio_bytes,
                            text="Hello world",
                            output_format="mp3_44100_128",
                            custom_filename="my_custom_audio"
                        )
        
        assert result is not None
        relative_path, absolute_path = result
        assert "my_custom_audio.mp3" in relative_path
        assert "sounds" in relative_path
    
    @pytest.mark.asyncio
    async def test_save_auto_generated_filename(self):
        """Test saving with auto-generated filename"""
        tool = ElevenLabsTTSTool()
        audio_bytes = b"test_audio_data"
        
        mock_context = {'contextId': 'local'}
        mock_fs = MagicMock()
        mock_fs.root_path = "/workspace"
        
        with patch('icpy.agent.tools.elevenlabs_tts_tool.get_current_context', return_value=mock_context):
            with patch('icpy.agent.tools.elevenlabs_tts_tool.get_contextual_filesystem', return_value=mock_fs):
                with patch('os.makedirs'):
                    with patch('builtins.open', mock_open()):
                        result = await tool._save_audio_to_workspace(
                            audio_bytes=audio_bytes,
                            text="Hello world test message",
                            output_format="mp3_44100_128",
                            custom_filename=None
                        )
        
        assert result is not None
        relative_path, _ = result
        assert "tts_" in relative_path
        assert ".mp3" in relative_path
    
    @pytest.mark.asyncio
    async def test_save_wav_format(self):
        """Test saving PCM format as .wav"""
        tool = ElevenLabsTTSTool()
        audio_bytes = b"test_pcm_data"
        
        mock_context = {'contextId': 'local'}
        mock_fs = MagicMock()
        mock_fs.root_path = "/workspace"
        
        with patch('icpy.agent.tools.elevenlabs_tts_tool.get_current_context', return_value=mock_context):
            with patch('icpy.agent.tools.elevenlabs_tts_tool.get_contextual_filesystem', return_value=mock_fs):
                with patch('os.makedirs'):
                    with patch('builtins.open', mock_open()):
                        result = await tool._save_audio_to_workspace(
                            audio_bytes=audio_bytes,
                            text="Hello",
                            output_format="pcm_44100",
                            custom_filename="pcm_audio"
                        )
        
        assert result is not None
        relative_path, _ = result
        assert ".wav" in relative_path


class TestHelperFunctions:
    """Test module-level helper functions"""
    
    def test_get_available_voices(self):
        """Test getting available voices"""
        voices = get_available_voices()
        
        assert isinstance(voices, dict)
        assert "george" in voices
        assert "rachel" in voices
        assert voices["george"] == DEFAULT_VOICES["george"]
    
    def test_get_available_models(self):
        """Test getting available models"""
        models = get_available_models()
        
        assert isinstance(models, dict)
        assert "eleven_multilingual_v2" in models
        assert "eleven_turbo_v2_5" in models
    
    def test_get_output_formats(self):
        """Test getting output formats"""
        formats = get_output_formats()
        
        assert isinstance(formats, dict)
        assert "mp3_44100_128" in formats
        assert "pcm_44100" in formats


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test handling of API errors"""
        tool = ElevenLabsTTSTool()
        
        mock_client = MagicMock()
        mock_client.text_to_speech.convert.side_effect = Exception("API Error: Rate limit exceeded")
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            result = await tool.execute(text="Hello")
        
        assert result.success is False
        assert "Failed to generate speech" in result.error
    
    @pytest.mark.asyncio
    async def test_save_failure_continues(self):
        """Test that save failure doesn't fail entire operation"""
        tool = ElevenLabsTTSTool()
        mock_audio = b"fake_audio"
        
        mock_client = MagicMock()
        mock_client.text_to_speech.convert.return_value = [mock_audio]
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            with patch.object(tool, '_save_audio_to_workspace', return_value=None):
                result = await tool.execute(text="Hello", save_to_workspace=True)
        
        # Should still succeed but with save_error
        assert result.success is True
        assert result.data["saved"] is False
        assert "save_error" in result.data
