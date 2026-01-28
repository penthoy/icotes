"""
Tests for ElevenLabs Music Generation Tool

Tests:
- Music generation with various parameters
- Duration validation
- Prompt influence validation
- File saving with custom and auto-generated filenames
- Error handling (API errors, missing API key)
- Hop-aware saving (local and remote contexts)
"""

import pytest
import os
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from pathlib import Path
from io import BytesIO

# Test imports
from icpy.agent.tools.elevenlabs_music_tool import ElevenLabsMusicTool


@pytest.fixture
def music_tool():
    """Create a music tool instance."""
    return ElevenLabsMusicTool()


@pytest.fixture
def mock_elevenlabs_client():
    """Mock ElevenLabs client."""
    mock_client = Mock()
    mock_music = Mock()
    
    # Mock compose method to return iterator of audio bytes
    def compose_side_effect(*args, **kwargs):
        # Return iterator of byte chunks
        return iter([b'chunk1', b'chunk2', b'chunk3'])
    
    mock_music.compose = Mock(side_effect=compose_side_effect)
    mock_client.music = mock_music
    
    return mock_client


@pytest.fixture
def mock_context_local():
    """Mock context for local workspace."""
    return {
        'contextId': 'local',
        'username': 'testuser',
        'cwd': '/home/testuser/icotes'
    }


@pytest.fixture
def mock_context_remote():
    """Mock context for remote workspace via hop."""
    return {
        'contextId': 'hop1',
        'username': 'remote_user',
        'workspaceRoot': '/home/remote_user/icotes'
    }


@pytest.fixture
def mock_filesystem_service():
    """Mock filesystem service."""
    mock_fs = AsyncMock()
    mock_fs.root_path = '/home/testuser/icotes'
    mock_fs.create_directory = AsyncMock()
    mock_fs.write_file_binary = AsyncMock()
    return mock_fs


# ============================================================================
# Test Music Generation
# ============================================================================


class TestMusicGeneration:
    """Test music generation functionality."""
    
    @pytest.mark.asyncio
    async def test_generate_music_basic(self, music_tool, mock_elevenlabs_client):
        """Test basic music generation."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_music_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                with patch('icpy.agent.tools.elevenlabs_music_tool.get_current_context', return_value={'contextId': 'local'}):
                    with patch('icpy.agent.tools.elevenlabs_music_tool.get_contextual_filesystem', return_value=AsyncMock(root_path='/tmp')):
                        with patch('os.makedirs'):
                            with patch('builtins.open', create=True) as mock_open:
                                mock_open.return_value.__enter__ = Mock(return_value=Mock(write=Mock()))
                                mock_open.return_value.__exit__ = Mock(return_value=False)
                                
                                result = await music_tool.execute(
                                    prompt="Upbeat electronic music with synth pads",
                                    duration_seconds=5.0
                                )
        
        assert result.success is True
        assert result.data['prompt'] == "Upbeat electronic music with synth pads"
        assert result.data['duration_seconds'] == 5.0
        assert result.data['duration_ms'] == 5000
        assert result.data['audio_size_bytes'] == len(b'chunk1chunk2chunk3')
    
    @pytest.mark.asyncio
    async def test_generate_music_minimum_duration(self, music_tool, mock_elevenlabs_client):
        """Test music generation with minimum duration."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_music_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                with patch('icpy.agent.tools.elevenlabs_music_tool.get_current_context', return_value={'contextId': 'local'}):
                    with patch('icpy.agent.tools.elevenlabs_music_tool.get_contextual_filesystem', return_value=AsyncMock(root_path='/tmp')):
                        with patch('os.makedirs'):
                            with patch('builtins.open', create=True) as mock_open:
                                mock_open.return_value.__enter__ = Mock(return_value=Mock(write=Mock()))
                                mock_open.return_value.__exit__ = Mock(return_value=False)
                                
                                result = await music_tool.execute(
                                    prompt="Short beep",
                                    duration_seconds=0.5
                                )
        
        assert result.success is True
        assert result.data['duration_ms'] == 500
    
    @pytest.mark.asyncio
    async def test_generate_music_no_save(self, music_tool, mock_elevenlabs_client):
        """Test music generation without saving."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_music_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                result = await music_tool.execute(
                    prompt="Ambient soundscape",
                    duration_seconds=5.0,
                    save_to_workspace=False
                )
        
        assert result.success is True
        assert result.data['saved'] is False
        assert 'file_path' not in result.data


# ============================================================================
# Test Parameter Validation
# ============================================================================


class TestParameterValidation:
    """Test parameter validation."""
    
    @pytest.mark.asyncio
    async def test_missing_prompt(self, music_tool):
        """Test error when prompt is missing."""
        result = await music_tool.execute()
        
        assert result.success is False
        assert "'prompt' parameter is required" in result.error
    
    @pytest.mark.asyncio
    async def test_empty_prompt(self, music_tool):
        """Test error when prompt is empty."""
        result = await music_tool.execute(prompt="")
        
        assert result.success is False
        assert "'prompt' parameter is required" in result.error
    
    @pytest.mark.asyncio
    async def test_duration_too_short(self, music_tool):
        """Test error when duration is too short."""
        result = await music_tool.execute(
            prompt="Test music",
            duration_seconds=0.1
        )
        
        assert result.success is False
        assert "Duration too short" in result.error
    
    @pytest.mark.asyncio
    async def test_duration_too_long(self, music_tool):
        """Test error when duration is too long."""
        result = await music_tool.execute(
            prompt="Test music",
            duration_seconds=200
        )
        
        assert result.success is False
        assert "Duration too long" in result.error


# ============================================================================
# Test File Saving
# ============================================================================


class TestFileSaving:
    """Test file saving functionality."""
    
    @pytest.mark.asyncio
    async def test_save_with_custom_filename(self, music_tool, mock_elevenlabs_client):
        """Test saving music with custom filename."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_music_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                with patch('icpy.agent.tools.elevenlabs_music_tool.get_current_context', return_value={'contextId': 'local'}):
                    with patch('icpy.agent.tools.elevenlabs_music_tool.get_contextual_filesystem', return_value=AsyncMock(root_path='/tmp')):
                        with patch('os.makedirs'):
                            with patch('builtins.open', create=True) as mock_open:
                                mock_file = Mock()
                                mock_open.return_value.__enter__ = Mock(return_value=mock_file)
                                mock_open.return_value.__exit__ = Mock(return_value=False)
                                
                                result = await music_tool.execute(
                                    prompt="Test music",
                                    duration_seconds=5.0,
                                    filename="my_custom_music"
                                )
        
        assert result.success is True
        assert result.data['saved'] is True
        assert 'my_custom_music.mp3' in result.data['file_path']
    
    @pytest.mark.asyncio
    async def test_save_auto_filename(self, music_tool, mock_elevenlabs_client):
        """Test saving music with auto-generated filename."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_music_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                with patch('icpy.agent.tools.elevenlabs_music_tool.get_current_context', return_value={'contextId': 'local'}):
                    with patch('icpy.agent.tools.elevenlabs_music_tool.get_contextual_filesystem', return_value=AsyncMock(root_path='/tmp')):
                        with patch('os.makedirs'):
                            with patch('builtins.open', create=True) as mock_open:
                                mock_file = Mock()
                                mock_open.return_value.__enter__ = Mock(return_value=mock_file)
                                mock_open.return_value.__exit__ = Mock(return_value=False)
                                
                                result = await music_tool.execute(
                                    prompt="Upbeat electronic dance music",
                                    duration_seconds=5.0
                                )
        
        assert result.success is True
        assert result.data['saved'] is True
        assert 'music_' in result.data['file_path']
        assert '.mp3' in result.data['file_path']
    
    @pytest.mark.asyncio
    async def test_save_sanitizes_filename(self, music_tool, mock_elevenlabs_client):
        """Test that special characters are sanitized from filename."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_music_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                with patch('icpy.agent.tools.elevenlabs_music_tool.get_current_context', return_value={'contextId': 'local'}):
                    with patch('icpy.agent.tools.elevenlabs_music_tool.get_contextual_filesystem', return_value=AsyncMock(root_path='/tmp')):
                        with patch('os.makedirs'):
                            with patch('builtins.open', create=True) as mock_open:
                                mock_file = Mock()
                                mock_open.return_value.__enter__ = Mock(return_value=mock_file)
                                mock_open.return_value.__exit__ = Mock(return_value=False)
                                
                                result = await music_tool.execute(
                                    prompt="Test! Music@ #$%^",
                                    duration_seconds=5.0,
                                    filename="special!@#chars"
                                )
        
        assert result.success is True
        # Should sanitize special characters
        assert '!' not in result.data['file_path']
        assert '@' not in result.data['file_path']
        assert '#' not in result.data['file_path']


# ============================================================================
# Test Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling."""
    
    @pytest.mark.asyncio
    async def test_missing_api_key(self, music_tool):
        """Test error when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove ELEVENLABS_API_KEY
            result = await music_tool.execute(
                prompt="Test music",
                duration_seconds=5.0
            )
        
        assert result.success is False
        assert "ELEVENLABS_API_KEY" in result.error
    
    @pytest.mark.asyncio
    async def test_api_error_bad_prompt(self, music_tool, mock_elevenlabs_client):
        """Test handling of API error for bad prompt."""
        # Mock API error
        mock_elevenlabs_client.music.compose.side_effect = Exception("bad_prompt: Contains copyrighted material")
        
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_music_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                result = await music_tool.execute(
                    prompt="Copyrighted song",
                    duration_seconds=5.0
                )
        
        assert result.success is False
        assert "copyrighted material" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_api_error_bad_prompt_with_suggestion(self, music_tool, mock_elevenlabs_client):
        """Test handling of bad prompt error with suggested alternative."""
        # Mock API error with suggestion
        error = Exception("bad_prompt: Contains copyrighted material")
        error.body = {
            'detail': {
                'status': 'bad_prompt',
                'data': {
                    'prompt_suggestion': 'A melodic piano piece with emotional arpeggios'
                }
            }
        }
        mock_elevenlabs_client.music.compose.side_effect = error
        
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_music_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                result = await music_tool.execute(
                    prompt="Final Fantasy music",
                    duration_seconds=5.0
                )
        
        assert result.success is False
        assert "Try this instead" in result.error
        assert "melodic piano piece" in result.error
    
    @pytest.mark.asyncio
    async def test_api_error_subscription(self, music_tool, mock_elevenlabs_client):
        """Test handling of API error for subscription required."""
        # Mock API error
        mock_elevenlabs_client.music.compose.side_effect = Exception("subscription required: Music API requires paid plan")
        
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_music_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                result = await music_tool.execute(
                    prompt="Test music",
                    duration_seconds=5.0
                )
        
        assert result.success is False
        assert "paid" in result.error.lower() or "subscription" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_no_music_data_received(self, music_tool, mock_elevenlabs_client):
        """Test error when no music data is received."""
        # Mock empty response
        mock_elevenlabs_client.music.compose = Mock(return_value=iter([]))
        
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_music_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                result = await music_tool.execute(
                    prompt="Test music",
                    duration_seconds=5.0,
                    save_to_workspace=False
                )
        
        assert result.success is False
        assert "No music data received" in result.error


# ============================================================================
# Test Hop-Aware Saving
# ============================================================================


class TestHopAwareSaving:
    """Test hop-aware saving functionality."""
    
    @pytest.mark.asyncio
    async def test_save_local_context(self, music_tool, mock_elevenlabs_client, mock_context_local):
        """Test saving music in local context."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_music_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                with patch('icpy.agent.tools.elevenlabs_music_tool.get_current_context', return_value=mock_context_local):
                    with patch('icpy.agent.tools.elevenlabs_music_tool.get_contextual_filesystem', return_value=AsyncMock(root_path='/home/testuser/icotes')):
                        with patch('os.makedirs'):
                            with patch('builtins.open', create=True) as mock_open:
                                mock_file = Mock()
                                mock_open.return_value.__enter__ = Mock(return_value=mock_file)
                                mock_open.return_value.__exit__ = Mock(return_value=False)
                                
                                result = await music_tool.execute(
                                    prompt="Local music",
                                    duration_seconds=5.0
                                )
        
        assert result.success is True
        assert result.data['saved'] is True
        assert 'sounds/' in result.data['file_path']
    
    @pytest.mark.asyncio
    async def test_save_remote_context(self, music_tool, mock_elevenlabs_client, mock_context_remote, mock_filesystem_service):
        """Test saving music in remote context via hop."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_music_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                with patch('icpy.agent.tools.elevenlabs_music_tool.get_current_context', return_value=mock_context_remote):
                    with patch('icpy.agent.tools.elevenlabs_music_tool.get_contextual_filesystem', return_value=mock_filesystem_service):
                        result = await music_tool.execute(
                            prompt="Remote music",
                            duration_seconds=5.0
                        )
        
        assert result.success is True
        assert result.data['saved'] is True
        assert 'sounds/' in result.data['file_path']
        
        # Verify remote write was called
        mock_filesystem_service.write_file_binary.assert_called_once()


# ============================================================================
# Test Tool Metadata
# ============================================================================


class TestToolMetadata:
    """Test tool metadata and OpenAI function format."""
    
    def test_tool_name(self, music_tool):
        """Test tool name."""
        assert music_tool.name == "text_to_music"
    
    def test_tool_description(self, music_tool):
        """Test tool has description."""
        assert len(music_tool.description) > 0
        assert "music" in music_tool.description.lower()
    
    def test_tool_parameters(self, music_tool):
        """Test tool parameters are correctly defined."""
        params = music_tool.parameters
        
        assert params['type'] == 'object'
        assert 'properties' in params
        assert 'required' in params
        
        # Check required parameters
        assert 'prompt' in params['required']
        
        # Check parameter definitions
        props = params['properties']
        assert 'prompt' in props
        assert 'duration_seconds' in props
        assert 'filename' in props
        assert 'save_to_workspace' in props
    
    def test_openai_function_format(self, music_tool):
        """Test tool can be converted to OpenAI function format."""
        function_def = music_tool.to_openai_function()
        
        assert function_def['name'] == 'text_to_music'
        assert 'description' in function_def
        assert 'parameters' in function_def
