"""
Unit tests for Atlas Cloud Text-to-Video Tool

Tests tool initialization, parameter validation, video generation,
file saving (local and hop), and error handling.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import os

from icpy.agent.tools.atlascloud.ttv_tool import AtlasCloudTextToVideoTool, TEXT_TO_VIDEO_MODELS
from icpy.agent.tools.base_tool import ToolResult
from icpy.agent.tools.atlascloud.models import VideoResult, VideoStatus
from icpy.agent.tools.atlascloud.exceptions import (
    AtlasCloudError,
    AtlasCloudTimeoutError,
)


@pytest.fixture
def tool():
    """Create tool instance."""
    return AtlasCloudTextToVideoTool()


@pytest.fixture
def mock_video_result():
    """Mock successful video generation result."""
    return VideoResult(
        id="test-123",
        status=VideoStatus.COMPLETED,
        model="bytedance/seedance-v1-lite-t2v-480p",
        output=["https://cdn.atlascloud.ai/generated/video-abc123.mp4"],
        has_nsfw_contents=[False],
    )


@pytest.fixture
def mock_video_bytes():
    """Mock video file bytes."""
    return b"FAKE_VIDEO_DATA_" * 1000  # Simulate video data


class TestToolInitialization:
    """Test tool initialization and properties."""
    
    def test_tool_name(self, tool):
        """Test tool name is correctly set."""
        assert tool.name == "text_to_video"
    
    def test_tool_description(self, tool):
        """Test tool has description."""
        assert "text description" in tool.description.lower()
        assert "atlas cloud" in tool.description.lower()
    
    def test_tool_parameters(self, tool):
        """Test tool parameters schema."""
        params = tool.parameters
        assert params["type"] == "object"
        assert "prompt" in params["properties"]
        assert "model" in params["properties"]
        assert "duration" in params["properties"]
        assert "aspect_ratio" in params["properties"]
        assert params["required"] == ["prompt"]
    
    def test_model_enum(self, tool):
        """Test model parameter has correct enum values."""
        model_enum = tool.parameters["properties"]["model"]["enum"]
        assert "bytedance/seedance-v1-lite-t2v-480p" in model_enum
        assert len(model_enum) > 0
        assert all(m in TEXT_TO_VIDEO_MODELS for m in model_enum)
    
    def test_aspect_ratio_enum(self, tool):
        """Test aspect ratio parameter has correct enum values."""
        aspect_enum = tool.parameters["properties"]["aspect_ratio"]["enum"]
        assert "16:9" in aspect_enum
        assert "1:1" in aspect_enum
        assert "9:16" in aspect_enum


class TestParameterValidation:
    """Test parameter validation logic."""
    
    @pytest.mark.asyncio
    async def test_missing_prompt(self, tool):
        """Test error when prompt is missing."""
        result = await tool.execute()
        
        assert result.success is False
        assert "prompt" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_prompt_too_long(self, tool):
        """Test error when prompt exceeds 2000 characters."""
        long_prompt = "A" * 2001
        
        result = await tool.execute(prompt=long_prompt)
        
        assert result.success is False
        assert "too long" in result.error.lower()
        assert "2000" in result.error
    
    @pytest.mark.asyncio
    async def test_invalid_model(self, tool):
        """Test error when invalid model is provided."""
        result = await tool.execute(
            prompt="Test video",
            model="invalid/model-name"
        )
        
        assert result.success is False
        assert "invalid model" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_invalid_aspect_ratio(self, tool):
        """Test error when invalid aspect ratio is provided."""
        with patch.object(tool, '_get_client'):
            result = await tool.execute(
                prompt="Test video",
                aspect_ratio="99:99"
            )
            
            assert result.success is False
            assert "aspect_ratio" in result.error.lower()


class TestVideoGeneration:
    """Test video generation flow."""
    
    @pytest.mark.asyncio
    async def test_successful_generation(
        self, tool, mock_video_result, mock_video_bytes, monkeypatch
    ):
        """Test successful video generation end-to-end."""
        # Mock API key
        monkeypatch.setenv("ATLASCLOUD_API_KEY", "test-key")
        
        # Mock client
        mock_client = AsyncMock()
        mock_client.generate_text_to_video.return_value = mock_video_result
        
        # Mock download
        async def mock_download(url):
            return mock_video_bytes
        
        # Mock file save
        async def mock_save_video(video_bytes, prompt, model, filename=None):
            return ("videos/test.mp4", "/workspace/videos/test.mp4")
        
        with patch.object(tool, '_get_client', return_value=mock_client), \
             patch.object(tool, '_download_video', side_effect=mock_download), \
             patch.object(tool, '_save_video_to_workspace', side_effect=mock_save_video):
            
            result = await tool.execute(
                prompt="A serene sunset over mountains",
                duration=5
            )
            
            assert result.success is True
            assert result.data is not None
            assert "file_path" in result.data
            assert "videos/test.mp4" in result.data["file_path"]
            assert result.data["model"] == "bytedance/seedance-v1-lite-t2v-480p"
            assert result.data["duration"] == 5
    
    @pytest.mark.asyncio
    async def test_generation_with_custom_params(
        self, tool, mock_video_result, mock_video_bytes, monkeypatch
    ):
        """Test generation with custom parameters."""
        monkeypatch.setenv("ATLASCLOUD_API_KEY", "test-key")
        
        mock_client = AsyncMock()
        mock_client.generate_text_to_video.return_value = mock_video_result
        
        async def mock_download(url):
            return mock_video_bytes
        
        async def mock_save_video(video_bytes, prompt, model, filename=None):
            return ("videos/custom.mp4", "/workspace/videos/custom.mp4")
        
        with patch.object(tool, '_get_client', return_value=mock_client), \
             patch.object(tool, '_download_video', side_effect=mock_download), \
             patch.object(tool, '_save_video_to_workspace', side_effect=mock_save_video):
            
            result = await tool.execute(
                prompt="Test video",
                model="alibaba/wan-2.6/text-to-video",
                duration=10,
                aspect_ratio="1:1",
                seed=42,
                filename="custom_video"
            )
            
            assert result.success is True
            assert result.data["duration"] == 10
            assert result.data["aspect_ratio"] == "1:1"
    
    @pytest.mark.asyncio
    async def test_timeout_error(self, tool, monkeypatch):
        """Test handling of timeout error."""
        monkeypatch.setenv("ATLASCLOUD_API_KEY", "test-key")
        
        mock_client = AsyncMock()
        mock_client.generate_text_to_video.side_effect = AtlasCloudTimeoutError(
            "Video generation timed out after 300 seconds"
        )
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            result = await tool.execute(
                prompt="Test video",
                timeout=300
            )
            
            assert result.success is False
            assert "timed out" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_api_error(self, tool, monkeypatch):
        """Test handling of API error."""
        monkeypatch.setenv("ATLASCLOUD_API_KEY", "test-key")
        
        mock_client = AsyncMock()
        mock_client.generate_text_to_video.side_effect = AtlasCloudError(
            "Insufficient credits"
        )
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            result = await tool.execute(prompt="Test video")
            
            assert result.success is False
            assert "api error" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_incomplete_result(self, tool, monkeypatch):
        """Test handling of incomplete generation result."""
        monkeypatch.setenv("ATLASCLOUD_API_KEY", "test-key")
        
        incomplete_result = VideoResult(
            id="test-123",
            status=VideoStatus.PROCESSING,
            model="bytedance/seedance-v1-lite-t2v-480p",
        )
        
        mock_client = AsyncMock()
        mock_client.generate_text_to_video.return_value = incomplete_result
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            result = await tool.execute(prompt="Test video")
            
            assert result.success is False
            assert "incomplete" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_no_output_url(self, tool, monkeypatch):
        """Test handling of completed result with no output URL."""
        monkeypatch.setenv("ATLASCLOUD_API_KEY", "test-key")
        
        no_output_result = VideoResult(
            id="test-123",
            status=VideoStatus.COMPLETED,
            model="bytedance/seedance-v1-lite-t2v-480p",
            output=None,
        )
        
        mock_client = AsyncMock()
        mock_client.generate_text_to_video.return_value = no_output_result
        
        with patch.object(tool, '_get_client', return_value=mock_client):
            result = await tool.execute(prompt="Test video")
            
            assert result.success is False
            assert "no output url" in result.error.lower()


class TestVideoDownload:
    """Test video download functionality."""
    
    @pytest.mark.asyncio
    async def test_download_success(self, tool, mock_video_bytes):
        """Test successful video download."""
        video_url = "https://cdn.atlascloud.ai/video.mp4"
        
        mock_response = AsyncMock()
        mock_response.content = mock_video_bytes
        mock_response.raise_for_status = MagicMock()
        
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response
        mock_http_client.__aenter__.return_value = mock_http_client
        mock_http_client.__aexit__.return_value = None
        
        with patch('httpx.AsyncClient', return_value=mock_http_client):
            result = await tool._download_video(video_url)
            
            assert result == mock_video_bytes
            mock_http_client.get.assert_called_once_with(video_url)
    
    @pytest.mark.asyncio
    async def test_download_failure(self, tool):
        """Test video download failure."""
        video_url = "https://cdn.atlascloud.ai/video.mp4"
        
        mock_http_client = AsyncMock()
        mock_http_client.get.side_effect = Exception("Network error")
        mock_http_client.__aenter__.return_value = mock_http_client
        mock_http_client.__aexit__.return_value = None
        
        with patch('httpx.AsyncClient', return_value=mock_http_client):
            with pytest.raises(AtlasCloudError, match="download failed"):
                await tool._download_video(video_url)


class TestWorkspaceSaving:
    """Test workspace file saving (local and hop)."""
    
    @pytest.mark.asyncio
    async def test_save_video_local(self, tool, mock_video_bytes):
        """Test saving video to local workspace."""
        prompt = "Test video prompt"
        model = "bytedance/seedance-v1-lite-t2v-480p"
        
        mock_context = {'contextId': 'local'}
        mock_filesystem = MagicMock()
        mock_filesystem.root_path = "/workspace"
        
        with patch('icpy.agent.tools.context_helpers.get_current_context', return_value=mock_context), \
             patch('icpy.agent.tools.context_helpers.get_contextual_filesystem', return_value=mock_filesystem), \
             patch('os.makedirs'), \
             patch('builtins.open', mock_open()) as mock_file:
            
            result = await tool._save_video_to_workspace(
                mock_video_bytes,
                prompt,
                model
            )
            
            assert result is not None
            relative_path, absolute_path = result
            assert relative_path.startswith("videos/")
            assert relative_path.endswith(".mp4")
            assert "ttv_" in relative_path
            assert "/videos/" in absolute_path
            assert absolute_path.endswith(".mp4")
    
    @pytest.mark.asyncio
    async def test_save_video_custom_filename(self, tool, mock_video_bytes):
        """Test saving video with custom filename."""
        prompt = "Test"
        model = "test-model"
        custom_filename = "my_custom_video"
        
        mock_context = {'contextId': 'local'}
        mock_filesystem = MagicMock()
        mock_filesystem.root_path = "/workspace"
        
        with patch('icpy.agent.tools.context_helpers.get_current_context', return_value=mock_context), \
             patch('icpy.agent.tools.context_helpers.get_contextual_filesystem', return_value=mock_filesystem), \
             patch('os.makedirs'), \
             patch('builtins.open', mock_open()):
            
            result = await tool._save_video_to_workspace(
                mock_video_bytes,
                prompt,
                model,
                custom_filename=custom_filename
            )
            
            assert result is not None
            relative_path, _ = result
            assert "my_custom_video.mp4" in relative_path
    
    @pytest.mark.asyncio
    async def test_save_video_remote_hop(self, tool, mock_video_bytes):
        """Test saving video to remote workspace via hop."""
        prompt = "Test video"
        model = "test-model"
        
        mock_context = {
            'contextId': 'hop1',
            'username': 'testuser',
            'workspaceRoot': '/home/testuser/icotes'
        }
        
        mock_filesystem = AsyncMock()
        mock_filesystem.write_file_binary = AsyncMock()
        mock_filesystem.create_directory = AsyncMock()
        
        with patch('icpy.agent.tools.atlascloud.ttv_tool.get_current_context', return_value=mock_context), \
             patch('icpy.agent.tools.atlascloud.ttv_tool.get_contextual_filesystem', return_value=mock_filesystem):
            
            result = await tool._save_video_to_workspace(
                mock_video_bytes,
                prompt,
                model
            )
            
            assert result is not None
            relative_path, absolute_path = result
            assert relative_path.startswith("videos/")
            assert "/videos/" in absolute_path
            assert absolute_path.endswith(".mp4")
            
            # Verify remote write was called
            mock_filesystem.create_directory.assert_called_once()
            mock_filesystem.write_file_binary.assert_called_once()


class TestClientInitialization:
    """Test client initialization."""
    
    def test_get_client_with_env_var(self, tool, monkeypatch):
        """Test client initialization from environment variable."""
        monkeypatch.setenv("ATLASCLOUD_API_KEY", "test-key-123")
        
        client = tool._get_client()
        
        assert client is not None
        assert client.api_key == "test-key-123"
    
    def test_get_client_without_api_key(self, tool, monkeypatch):
        """Test client initialization fails without API key."""
        monkeypatch.delenv("ATLASCLOUD_API_KEY", raising=False)
        
        with pytest.raises(RuntimeError, match="ATLASCLOUD_API_KEY"):
            tool._get_client()
    
    def test_get_client_caching(self, tool, monkeypatch):
        """Test client is cached after first initialization."""
        monkeypatch.setenv("ATLASCLOUD_API_KEY", "test-key")
        
        client1 = tool._get_client()
        client2 = tool._get_client()
        
        assert client1 is client2  # Same instance


# Integration tests (requires real API key)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api_generation():
    """
    Integration test with real API (requires ATLASCLOUD_API_KEY).
    Marked as integration test - skip by default.
    """
    import os
    api_key = os.getenv("ATLASCLOUD_API_KEY")
    
    if not api_key:
        pytest.skip("ATLASCLOUD_API_KEY not set")
    
    tool = AtlasCloudTextToVideoTool()
    
    result = await tool.execute(
        prompt="A cat walking on a sidewalk, realistic style",
        duration=5,  # Minimum duration to minimize cost
        model="bytedance/seedance-v1-lite-t2v-480p",  # Cheapest model
        timeout=300,
    )
    
    assert result.success is True
    assert result.data is not None
    assert "file_path" in result.data
    assert result.data["file_path"].endswith(".mp4")
