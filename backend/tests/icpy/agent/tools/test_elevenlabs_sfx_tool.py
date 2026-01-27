"""
Tests for ElevenLabs Sound Effects Generation Tool

Tests:
- Sound effects generation with various parameters
- Duration validation
- Prompt influence and loop validation
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
from icpy.agent.tools.elevenlabs_sfx_tool import ElevenLabsSoundEffectsTool


@pytest.fixture
def sfx_tool():
    """Create a sound effects tool instance."""
    return ElevenLabsSoundEffectsTool()


@pytest.fixture
def mock_elevenlabs_client():
    """Mock ElevenLabs client."""
    mock_client = Mock()
    mock_sfx = Mock()
    
    # Mock convert method to return iterator of audio bytes
    def convert_side_effect(*args, **kwargs):
        # Return iterator of byte chunks
        return iter([b'sfx_chunk1', b'sfx_chunk2'])
    
    mock_sfx.convert = Mock(side_effect=convert_side_effect)
    mock_client.text_to_sound_effects = mock_sfx
    
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
# Test Sound Effects Generation
# ============================================================================


class TestSoundEffectsGeneration:
    """Test sound effects generation functionality."""
    
    @pytest.mark.asyncio
    async def test_generate_sfx_basic(self, sfx_tool, mock_elevenlabs_client):
        """Test basic sound effect generation."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_sfx_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_current_context', return_value={'contextId': 'local'}):
                    with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_contextual_filesystem', return_value=AsyncMock(root_path='/tmp')):
                        with patch('os.makedirs'):
                            with patch('builtins.open', create=True) as mock_open:
                                mock_open.return_value.__enter__ = Mock(return_value=Mock(write=Mock()))
                                mock_open.return_value.__exit__ = Mock(return_value=False)
                                
                                result = await sfx_tool.execute(
                                    text="Dog barking loudly",
                                    duration_seconds=2.0
                                )
        
        assert result.success is True
        assert result.data['text'] == "Dog barking loudly"
        assert result.data['duration_seconds'] == 2.0
        assert result.data['audio_size_bytes'] == len(b'sfx_chunk1sfx_chunk2')
    
    @pytest.mark.asyncio
    async def test_generate_sfx_with_loop(self, sfx_tool, mock_elevenlabs_client):
        """Test sound effect generation with loop enabled."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_sfx_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_current_context', return_value={'contextId': 'local'}):
                    with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_contextual_filesystem', return_value=AsyncMock(root_path='/tmp')):
                        with patch('os.makedirs'):
                            with patch('builtins.open', create=True) as mock_open:
                                mock_open.return_value.__enter__ = Mock(return_value=Mock(write=Mock()))
                                mock_open.return_value.__exit__ = Mock(return_value=False)
                                
                                result = await sfx_tool.execute(
                                    text="Ambient forest sounds",
                                    duration_seconds=3.0,
                                    loop=True
                                )
        
        assert result.success is True
        assert result.data['loop'] is True
        
        # Verify API was called with loop parameter
        mock_elevenlabs_client.text_to_sound_effects.convert.assert_called_once()
        call_kwargs = mock_elevenlabs_client.text_to_sound_effects.convert.call_args[1]
        assert call_kwargs['loop'] is True
    
    @pytest.mark.asyncio
    async def test_generate_sfx_custom_influence(self, sfx_tool, mock_elevenlabs_client):
        """Test sound effect generation with custom prompt influence."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_sfx_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_current_context', return_value={'contextId': 'local'}):
                    with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_contextual_filesystem', return_value=AsyncMock(root_path='/tmp')):
                        with patch('os.makedirs'):
                            with patch('builtins.open', create=True) as mock_open:
                                mock_open.return_value.__enter__ = Mock(return_value=Mock(write=Mock()))
                                mock_open.return_value.__exit__ = Mock(return_value=False)
                                
                                result = await sfx_tool.execute(
                                    text="Glass breaking",
                                    duration_seconds=1.5,
                                    prompt_influence=0.7
                                )
        
        assert result.success is True
        assert result.data['prompt_influence'] == 0.7
        
        # Verify API was called with correct parameters
        mock_elevenlabs_client.text_to_sound_effects.convert.assert_called_once()
        call_kwargs = mock_elevenlabs_client.text_to_sound_effects.convert.call_args[1]
        assert call_kwargs['prompt_influence'] == 0.7
    
    @pytest.mark.asyncio
    async def test_generate_sfx_minimum_duration(self, sfx_tool, mock_elevenlabs_client):
        """Test sound effect generation with minimum duration."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_sfx_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_current_context', return_value={'contextId': 'local'}):
                    with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_contextual_filesystem', return_value=AsyncMock(root_path='/tmp')):
                        with patch('os.makedirs'):
                            with patch('builtins.open', create=True) as mock_open:
                                mock_open.return_value.__enter__ = Mock(return_value=Mock(write=Mock()))
                                mock_open.return_value.__exit__ = Mock(return_value=False)
                                
                                result = await sfx_tool.execute(
                                    text="Short beep",
                                    duration_seconds=0.5
                                )
        
        assert result.success is True
        assert result.data['duration_seconds'] == 0.5
    
    @pytest.mark.asyncio
    async def test_generate_sfx_no_save(self, sfx_tool, mock_elevenlabs_client):
        """Test sound effect generation without saving."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_sfx_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                result = await sfx_tool.execute(
                    text="Test sound",
                    duration_seconds=1.0,
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
    async def test_missing_text(self, sfx_tool):
        """Test error when text is missing."""
        result = await sfx_tool.execute()
        
        assert result.success is False
        assert "'text' parameter is required" in result.error
    
    @pytest.mark.asyncio
    async def test_empty_text(self, sfx_tool):
        """Test error when text is empty."""
        result = await sfx_tool.execute(text="")
        
        assert result.success is False
        assert "'text' parameter is required" in result.error
    
    @pytest.mark.asyncio
    async def test_duration_too_short(self, sfx_tool):
        """Test error when duration is too short."""
        result = await sfx_tool.execute(
            text="Test sound",
            duration_seconds=0.1
        )
        
        assert result.success is False
        assert "Duration too short" in result.error
    
    @pytest.mark.asyncio
    async def test_duration_too_long(self, sfx_tool):
        """Test error when duration is too long."""
        result = await sfx_tool.execute(
            text="Test sound",
            duration_seconds=50
        )
        
        assert result.success is False
        assert "Duration too long" in result.error
    
    @pytest.mark.asyncio
    async def test_invalid_prompt_influence_low(self, sfx_tool):
        """Test error when prompt influence is below 0."""
        result = await sfx_tool.execute(
            text="Test sound",
            prompt_influence=-0.1
        )
        
        assert result.success is False
        assert "prompt_influence must be between 0.0 and 1.0" in result.error
    
    @pytest.mark.asyncio
    async def test_invalid_prompt_influence_high(self, sfx_tool):
        """Test error when prompt influence is above 1."""
        result = await sfx_tool.execute(
            text="Test sound",
            prompt_influence=1.5
        )
        
        assert result.success is False
        assert "prompt_influence must be between 0.0 and 1.0" in result.error


# ============================================================================
# Test File Saving
# ============================================================================


class TestFileSaving:
    """Test file saving functionality."""
    
    @pytest.mark.asyncio
    async def test_save_with_custom_filename(self, sfx_tool, mock_elevenlabs_client):
        """Test saving sound effect with custom filename."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_sfx_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_current_context', return_value={'contextId': 'local'}):
                    with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_contextual_filesystem', return_value=AsyncMock(root_path='/tmp')):
                        with patch('os.makedirs'):
                            with patch('builtins.open', create=True) as mock_open:
                                mock_file = Mock()
                                mock_open.return_value.__enter__ = Mock(return_value=mock_file)
                                mock_open.return_value.__exit__ = Mock(return_value=False)
                                
                                result = await sfx_tool.execute(
                                    text="Test sound",
                                    duration_seconds=1.0,
                                    filename="my_custom_sfx"
                                )
        
        assert result.success is True
        assert result.data['saved'] is True
        assert 'my_custom_sfx.mp3' in result.data['file_path']
    
    @pytest.mark.asyncio
    async def test_save_auto_filename(self, sfx_tool, mock_elevenlabs_client):
        """Test saving sound effect with auto-generated filename."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_sfx_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_current_context', return_value={'contextId': 'local'}):
                    with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_contextual_filesystem', return_value=AsyncMock(root_path='/tmp')):
                        with patch('os.makedirs'):
                            with patch('builtins.open', create=True) as mock_open:
                                mock_file = Mock()
                                mock_open.return_value.__enter__ = Mock(return_value=mock_file)
                                mock_open.return_value.__exit__ = Mock(return_value=False)
                                
                                result = await sfx_tool.execute(
                                    text="Dog barking loudly in the distance",
                                    duration_seconds=2.0
                                )
        
        assert result.success is True
        assert result.data['saved'] is True
        assert 'sfx_' in result.data['file_path']
        assert '.mp3' in result.data['file_path']
    
    @pytest.mark.asyncio
    async def test_save_sanitizes_filename(self, sfx_tool, mock_elevenlabs_client):
        """Test that special characters are sanitized from filename."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_sfx_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_current_context', return_value={'contextId': 'local'}):
                    with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_contextual_filesystem', return_value=AsyncMock(root_path='/tmp')):
                        with patch('os.makedirs'):
                            with patch('builtins.open', create=True) as mock_open:
                                mock_file = Mock()
                                mock_open.return_value.__enter__ = Mock(return_value=mock_file)
                                mock_open.return_value.__exit__ = Mock(return_value=False)
                                
                                result = await sfx_tool.execute(
                                    text="Test! Sound@ #$%^",
                                    duration_seconds=1.0,
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
    async def test_missing_api_key(self, sfx_tool):
        """Test error when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove ELEVENLABS_API_KEY
            result = await sfx_tool.execute(
                text="Test sound",
                duration_seconds=1.0
            )
        
        assert result.success is False
        assert "ELEVENLABS_API_KEY" in result.error
    
    @pytest.mark.asyncio
    async def test_api_error(self, sfx_tool, mock_elevenlabs_client):
        """Test handling of API error."""
        # Mock API error
        mock_elevenlabs_client.text_to_sound_effects.convert.side_effect = Exception("API error: Invalid request")
        
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_sfx_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                result = await sfx_tool.execute(
                    text="Test sound",
                    duration_seconds=1.0
                )
        
        assert result.success is False
        assert "Failed to generate sound effect" in result.error
    
    @pytest.mark.asyncio
    async def test_no_sound_data_received(self, sfx_tool, mock_elevenlabs_client):
        """Test error when no sound data is received."""
        # Mock empty response
        mock_elevenlabs_client.text_to_sound_effects.convert = Mock(return_value=iter([]))
        
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_sfx_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                result = await sfx_tool.execute(
                    text="Test sound",
                    duration_seconds=1.0,
                    save_to_workspace=False
                )
        
        assert result.success is False
        assert "No sound data received" in result.error


# ============================================================================
# Test Hop-Aware Saving
# ============================================================================


class TestHopAwareSaving:
    """Test hop-aware saving functionality."""
    
    @pytest.mark.asyncio
    async def test_save_local_context(self, sfx_tool, mock_elevenlabs_client, mock_context_local):
        """Test saving sound effect in local context."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_sfx_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_current_context', return_value=mock_context_local):
                    with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_contextual_filesystem', return_value=AsyncMock(root_path='/home/testuser/icotes')):
                        with patch('os.makedirs'):
                            with patch('builtins.open', create=True) as mock_open:
                                mock_file = Mock()
                                mock_open.return_value.__enter__ = Mock(return_value=mock_file)
                                mock_open.return_value.__exit__ = Mock(return_value=False)
                                
                                result = await sfx_tool.execute(
                                    text="Local sound",
                                    duration_seconds=1.0
                                )
        
        assert result.success is True
        assert result.data['saved'] is True
        assert 'sounds/' in result.data['file_path']
    
    @pytest.mark.asyncio
    async def test_save_remote_context(self, sfx_tool, mock_elevenlabs_client, mock_context_remote, mock_filesystem_service):
        """Test saving sound effect in remote context via hop."""
        with patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test_api_key'}):
            with patch('icpy.agent.tools.elevenlabs_sfx_tool.ElevenLabs', return_value=mock_elevenlabs_client):
                with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_current_context', return_value=mock_context_remote):
                    with patch('icpy.agent.tools.elevenlabs_sfx_tool.get_contextual_filesystem', return_value=mock_filesystem_service):
                        result = await sfx_tool.execute(
                            text="Remote sound",
                            duration_seconds=1.0
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
    
    def test_tool_name(self, sfx_tool):
        """Test tool name."""
        assert sfx_tool.name == "text_to_sound_effects"
    
    def test_tool_description(self, sfx_tool):
        """Test tool has description."""
        assert len(sfx_tool.description) > 0
        assert "sound effect" in sfx_tool.description.lower()
    
    def test_tool_parameters(self, sfx_tool):
        """Test tool parameters are correctly defined."""
        params = sfx_tool.parameters
        
        assert params['type'] == 'object'
        assert 'properties' in params
        assert 'required' in params
        
        # Check required parameters
        assert 'text' in params['required']
        
        # Check parameter definitions
        props = params['properties']
        assert 'text' in props
        assert 'duration_seconds' in props
        assert 'prompt_influence' in props
        assert 'loop' in props
        assert 'filename' in props
        assert 'save_to_workspace' in props
    
    def test_openai_function_format(self, sfx_tool):
        """Test tool can be converted to OpenAI function format."""
        function_def = sfx_tool.to_openai_function()
        
        assert function_def['name'] == 'text_to_sound_effects'
        assert 'description' in function_def
        assert 'parameters' in function_def
