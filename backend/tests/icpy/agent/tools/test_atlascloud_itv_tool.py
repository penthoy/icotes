"""
Tests for AtlasCloudImageToVideoTool

Comprehensive test coverage for image-to-video generation tool.
"""

import pytest
import os
import base64
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from io import BytesIO
from PIL import Image

from icpy.agent.tools.atlascloud.itv_tool import (
    AtlasCloudImageToVideoTool,
    IMAGE_TO_VIDEO_MODELS,
    ASPECT_RATIOS,
    MAX_IMAGE_SIZE_MB,
)
from icpy.agent.tools.atlascloud.models import VideoResult, VideoStatus
from icpy.agent.tools.atlascloud.exceptions import (
    AtlasCloudError,
    AtlasCloudAuthError,
    AtlasCloudTimeoutError,
)


class TestToolInitialization:
    """Test tool initialization and basic properties."""
    
    def test_tool_name(self):
        """Tool should have correct name."""
        tool = AtlasCloudImageToVideoTool()
        assert tool.name == "image_to_video"
    
    def test_tool_description(self):
        """Tool should have descriptive text."""
        tool = AtlasCloudImageToVideoTool()
        assert "image" in tool.description.lower()
        assert "video" in tool.description.lower()
    
    def test_tool_parameters(self):
        """Tool parameters should be properly defined."""
        tool = AtlasCloudImageToVideoTool()
        params = tool.parameters
        
        assert params["type"] == "object"
        assert "image" in params["properties"]
        assert "prompt" in params["properties"]
        assert "model" in params["properties"]
        assert "duration" in params["properties"]
        assert "aspect_ratio" in params["properties"]
        assert params["required"] == ["image"]
    
    def test_model_enum(self):
        """Model parameter should have enum of available models."""
        tool = AtlasCloudImageToVideoTool()
        model_enum = tool.parameters["properties"]["model"]["enum"]
        
        assert "bytedance/seedance-v1-lite-i2v-480p" in model_enum
        assert "bytedance/seedance-v1-lite-i2v-720p" in model_enum
        assert len(model_enum) == len(IMAGE_TO_VIDEO_MODELS)
    
    def test_aspect_ratio_enum(self):
        """Aspect ratio parameter should have enum of supported ratios."""
        tool = AtlasCloudImageToVideoTool()
        ratio_enum = tool.parameters["properties"]["aspect_ratio"]["enum"]
        
        assert "16:9" in ratio_enum
        assert "9:16" in ratio_enum
        assert "1:1" in ratio_enum
        assert ratio_enum == ASPECT_RATIOS


class TestParameterValidation:
    """Test parameter validation logic."""
    
    @pytest.mark.asyncio
    async def test_missing_image(self):
        """Should fail if image parameter is missing."""
        tool = AtlasCloudImageToVideoTool()
        result = await tool.execute(prompt="test prompt")
        
        assert not result.success
        assert "required" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_prompt_too_long(self):
        """Should fail if prompt exceeds 2000 characters."""
        tool = AtlasCloudImageToVideoTool()
        long_prompt = "x" * 2001
        
        result = await tool.execute(
            image="http://example.com/image.jpg",
            prompt=long_prompt
        )
        
        assert not result.success
        assert "too long" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_invalid_model(self):
        """Should fail if model is not in registry."""
        tool = AtlasCloudImageToVideoTool()
        result = await tool.execute(
            image="http://example.com/image.jpg",
            model="invalid-model"
        )
        
        assert not result.success
        assert "invalid model" in result.error.lower()


class TestImageProcessing:
    """Test image processing and validation."""
    
    def test_validate_base64_image_valid(self):
        """Should validate correct base64 image."""
        tool = AtlasCloudImageToVideoTool()
        
        # Create valid 500x500 test image
        img = Image.new('RGB', (500, 500), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        img_bytes = buffer.getvalue()
        
        base64_str = base64.b64encode(img_bytes).decode('utf-8')
        data_url = f"data:image/jpeg;base64,{base64_str}"
        
        # Should not raise
        tool._validate_base64_image(data_url)
    
    def test_validate_base64_image_too_small(self):
        """Should fail if image resolution is too small."""
        tool = AtlasCloudImageToVideoTool()
        
        # Create 100x100 image (below MIN_IMAGE_RESOLUTION)
        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        img_bytes = buffer.getvalue()
        
        base64_str = base64.b64encode(img_bytes).decode('utf-8')
        data_url = f"data:image/jpeg;base64,{base64_str}"
        
        with pytest.raises(ValueError, match="too small"):
            tool._validate_base64_image(data_url)
    
    def test_validate_base64_image_invalid_format(self):
        """Should fail if data URL format is invalid."""
        tool = AtlasCloudImageToVideoTool()
        
        with pytest.raises(ValueError, match="Invalid"):
            tool._validate_base64_image("not-a-data-url")
    
    @pytest.mark.asyncio
    async def test_process_image_url(self):
        """Should pass through HTTP URLs unchanged."""
        tool = AtlasCloudImageToVideoTool()
        url = "https://example.com/image.jpg"
        
        result = await tool._process_image(url)
        
        assert result == url
    
    @pytest.mark.asyncio
    async def test_process_image_base64(self):
        """Should validate and pass through base64 images."""
        tool = AtlasCloudImageToVideoTool()
        
        # Create valid test image
        img = Image.new('RGB', (500, 500), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()
        
        base64_str = base64.b64encode(img_bytes).decode('utf-8')
        data_url = f"data:image/png;base64,{base64_str}"
        
        result = await tool._process_image(data_url)
        
        assert result == data_url
    
    @pytest.mark.asyncio
    async def test_process_image_workspace_file(self):
        """Should read and convert workspace files to base64."""
        tool = AtlasCloudImageToVideoTool()
        
        # Create test image bytes
        img = Image.new('RGB', (600, 400), color='green')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        img_bytes = buffer.getvalue()
        
        # Mock contextual filesystem
        mock_fs = AsyncMock()
        mock_fs.resolve_path.return_value = "/tmp/workspace/images/test.jpg"
        
        with patch('icpy.agent.tools.context_helpers.get_contextual_filesystem', return_value=mock_fs):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.stat') as mock_stat:
                    mock_stat.return_value.st_size = len(img_bytes)
                    with patch('builtins.open', mock_open(read_data=img_bytes)):
                        result = await tool._process_image("images/test.jpg")
        
        # Should return base64 data URL
        assert result.startswith("data:image/jpeg;base64,")
    
    @pytest.mark.asyncio
    async def test_process_image_file_not_found(self):
        """Should fail if workspace file doesn't exist."""
        tool = AtlasCloudImageToVideoTool()
        
        mock_ws_service = AsyncMock()
        mock_ws_service.get_workspace_path.return_value = "/tmp/workspace"
        
        with patch('icpy.agent.tools.context_helpers.get_workspace_service', return_value=mock_ws_service):
            with patch('pathlib.Path.exists', return_value=False):
                with pytest.raises(ValueError, match="not found"):
                    await tool._process_image("images/missing.jpg")
    
    @pytest.mark.asyncio
    async def test_process_image_file_too_large(self):
        """Should fail if file exceeds MAX_IMAGE_SIZE_MB."""
        tool = AtlasCloudImageToVideoTool()
        
        mock_ws_service = AsyncMock()
        mock_ws_service.get_workspace_path.return_value = "/tmp/workspace"
        
        # Mock file size > MAX_IMAGE_SIZE_MB
        large_size = (MAX_IMAGE_SIZE_MB + 1) * 1024 * 1024
        
        with patch('icpy.agent.tools.context_helpers.get_workspace_service', return_value=mock_ws_service):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.stat') as mock_stat:
                    mock_stat.return_value.st_size = large_size
                    with pytest.raises(ValueError, match="too large"):
                        await tool._process_image("images/huge.jpg")


class TestVideoGeneration:
    """Test video generation workflow."""
    
    @pytest.mark.asyncio
    async def test_successful_generation(self):
        """Should generate video successfully."""
        tool = AtlasCloudImageToVideoTool()
        
        # Mock client
        mock_client = AsyncMock()
        mock_result = VideoResult(
            id="test-123",
            status=VideoStatus.COMPLETED,
            outputs=["https://cdn.example.com/video.mp4"]
        )
        mock_client.generate_image_to_video.return_value = mock_result
        
        # Mock video download
        video_bytes = b"fake-video-data"
        
        with patch.dict(os.environ, {"ATLASCLOUD_API_KEY": "test-key"}):
            with patch.object(tool, '_get_client', return_value=mock_client):
                with patch.object(tool, '_download_video', return_value=video_bytes):
                    with patch.object(tool, '_save_video_to_workspace', return_value=("videos/test.mp4", "/tmp/test.mp4")):
                        result = await tool.execute(
                            image="https://example.com/image.jpg",
                            prompt="dancing cat"
                        )
        
        assert result.success
        assert "video_path" in result.data
        assert result.data["model"] == "bytedance/seedance-v1-lite-i2v-480p"
    
    @pytest.mark.asyncio
    async def test_generation_with_custom_params(self):
        """Should pass custom parameters to client."""
        tool = AtlasCloudImageToVideoTool()
        
        mock_client = AsyncMock()
        mock_result = VideoResult(
            id="test-456",
            status=VideoStatus.COMPLETED,
            outputs=["https://cdn.example.com/video2.mp4"]
        )
        mock_client.generate_image_to_video.return_value = mock_result
        
        with patch.dict(os.environ, {"ATLASCLOUD_API_KEY": "test-key"}):
            with patch.object(tool, '_get_client', return_value=mock_client):
                with patch.object(tool, '_download_video', return_value=b"data"):
                    with patch.object(tool, '_save_video_to_workspace', return_value=("videos/custom.mp4", "/tmp/custom.mp4")):
                        result = await tool.execute(
                            image="https://example.com/photo.png",
                            prompt="sunset",
                            model="bytedance/seedance-v1-pro-i2v-720p",
                            duration=8,
                            aspect_ratio="9:16",
                            seed=42
                        )
        
        # Verify client was called with correct parameters
        assert mock_client.generate_image_to_video.called
        call_kwargs = mock_client.generate_image_to_video.call_args.kwargs
        assert call_kwargs["model"] == "bytedance/seedance-v1-pro-i2v-720p"
        assert call_kwargs["duration"] == 8
        assert call_kwargs["aspect_ratio"] == "9:16"
        assert call_kwargs["seed"] == 42
        assert result.success
    
    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """Should handle timeout errors gracefully."""
        tool = AtlasCloudImageToVideoTool()
        
        mock_client = AsyncMock()
        mock_client.generate_image_to_video.side_effect = AtlasCloudTimeoutError("Timeout after 300s")
        
        with patch.dict(os.environ, {"ATLASCLOUD_API_KEY": "test-key"}):
            with patch.object(tool, '_get_client', return_value=mock_client):
                result = await tool.execute(image="https://example.com/image.jpg")
        
        assert not result.success
        assert "timed out" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_api_error(self):
        """Should handle API errors gracefully."""
        tool = AtlasCloudImageToVideoTool()
        
        mock_client = AsyncMock()
        mock_client.generate_image_to_video.side_effect = AtlasCloudError("API error: Rate limit exceeded")
        
        with patch.dict(os.environ, {"ATLASCLOUD_API_KEY": "test-key"}):
            with patch.object(tool, '_get_client', return_value=mock_client):
                result = await tool.execute(image="https://example.com/image.jpg")
        
        assert not result.success
        assert "api error" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_incomplete_result(self):
        """Should fail if video generation doesn't complete."""
        tool = AtlasCloudImageToVideoTool()
        
        mock_client = AsyncMock()
        mock_result = VideoResult(
            id="test-789",
            status=VideoStatus.PROCESSING  # Not completed
        )
        mock_client.generate_image_to_video.return_value = mock_result
        
        with patch.dict(os.environ, {"ATLASCLOUD_API_KEY": "test-key"}):
            with patch.object(tool, '_get_client', return_value=mock_client):
                result = await tool.execute(image="https://example.com/image.jpg")
        
        assert not result.success
        assert "incomplete" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_no_output_url(self):
        """Should fail if completed result has no video URL."""
        tool = AtlasCloudImageToVideoTool()
        
        mock_client = AsyncMock()
        mock_result = VideoResult(
            id="test-999",
            status=VideoStatus.COMPLETED,
            # No outputs/video URL
        )
        mock_client.generate_image_to_video.return_value = mock_result
        
        with patch.dict(os.environ, {"ATLASCLOUD_API_KEY": "test-key"}):
            with patch.object(tool, '_get_client', return_value=mock_client):
                result = await tool.execute(image="https://example.com/image.jpg")
        
        assert not result.success
        assert "no output url" in result.error.lower()


class TestVideoDownload:
    """Test video download functionality."""
    
    @pytest.mark.asyncio
    async def test_download_success(self):
        """Should download video from URL."""
        tool = AtlasCloudImageToVideoTool()
        video_url = "https://cdn.example.com/video.mp4"
        video_bytes = b"fake-video-content"
        
        mock_response = MagicMock()
        mock_response.content = video_bytes
        mock_response.raise_for_status = MagicMock()
        
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response
        mock_http_client.__aenter__.return_value = mock_http_client
        mock_http_client.__aexit__.return_value = None
        
        with patch('httpx.AsyncClient', return_value=mock_http_client):
            result = await tool._download_video(video_url)
        
        assert result == video_bytes
    
    @pytest.mark.asyncio
    async def test_download_failure(self):
        """Should raise error if download fails."""
        tool = AtlasCloudImageToVideoTool()
        video_url = "https://cdn.example.com/missing.mp4"
        
        import httpx
        
        mock_http_client = AsyncMock()
        mock_http_client.get.side_effect = httpx.HTTPError("404 Not Found")
        mock_http_client.__aenter__.return_value = mock_http_client
        mock_http_client.__aexit__.return_value = None
        
        with patch('httpx.AsyncClient', return_value=mock_http_client):
            with pytest.raises(AtlasCloudError, match="download failed"):
                await tool._download_video(video_url)


class TestWorkspaceSaving:
    """Test workspace file saving functionality."""
    
    @pytest.mark.asyncio
    async def test_save_video_local(self):
        """Should save video to local workspace."""
        tool = AtlasCloudImageToVideoTool()
        video_bytes = b"test-video-data"
        
        mock_ws_service = AsyncMock()
        mock_ws_service.get_workspace_path.return_value = "/tmp/workspace"
        
        with patch('icpy.agent.tools.context_helpers.get_workspace_service', return_value=mock_ws_service):
            with patch('pathlib.Path.mkdir'):
                with patch('builtins.open', mock_open()) as mock_file:
                    result = await tool._save_video_to_workspace(
                        video_bytes,
                        "photo.jpg",
                        "bytedance/seedance-v1-lite-i2v-480p"
                    )
        
        assert result is not None
        relative_path, _ = result
        assert relative_path.startswith("videos/")
        assert relative_path.endswith(".mp4")
        assert "photo" in relative_path
        assert "i2v" in relative_path
    
    @pytest.mark.asyncio
    async def test_save_video_custom_filename(self):
        """Should use custom filename when provided."""
        tool = AtlasCloudImageToVideoTool()
        video_bytes = b"test-video-data"
        
        mock_ws_service = AsyncMock()
        mock_ws_service.get_workspace_path.return_value = "/tmp/workspace"
        
        with patch('icpy.agent.tools.context_helpers.get_workspace_service', return_value=mock_ws_service):
            with patch('pathlib.Path.mkdir'):
                with patch('builtins.open', mock_open()):
                    result = await tool._save_video_to_workspace(
                        video_bytes,
                        "image.jpg",
                        "bytedance/seedance-v1-lite-i2v-480p",
                        filename="my_custom_video"
                    )
        
        relative_path, _ = result
        assert "my_custom_video.mp4" in relative_path
    
    @pytest.mark.asyncio
    async def test_save_video_remote_hop(self):
        """Should save video via hop for remote sessions."""
        tool = AtlasCloudImageToVideoTool()
        video_bytes = b"test-video-data"
        
        mock_ws_service = AsyncMock()
        mock_ws_service.get_workspace_path.return_value = "/remote/workspace"
        
        mock_hop_service = AsyncMock()
        mock_hop_service.get_hop.return_value = {"activeNamespace": "remote-ns"}
        
        mock_fs_service = AsyncMock()
        
        with patch('icpy.agent.tools.context_helpers.get_workspace_service', return_value=mock_ws_service):
            with patch('icpy.agent.tools.context_helpers.get_hop_service', return_value=mock_hop_service):
                with patch('pathlib.Path.mkdir'):
                    with patch('builtins.open', mock_open()) as mock_file:
                        # Simulate local write failure, then remote success
                        mock_file.side_effect = [OSError("Permission denied")]
                        
                        with patch('icpy.agent.tools.context_helpers.get_filesystem_service', return_value=mock_fs_service):
                            await tool._save_video_to_workspace(
                                video_bytes,
                                "image.png",
                                "bytedance/seedance-v1-lite-i2v-480p",
                                hop_session="hop-123"
                            )
        
        # Should have attempted remote write
        assert mock_fs_service.write_file.called


class TestClientInitialization:
    """Test client initialization and API key handling."""
    
    def test_get_client_with_env_var(self):
        """Should create client from environment variable."""
        tool = AtlasCloudImageToVideoTool()
        
        with patch.dict(os.environ, {"ATLASCLOUD_API_KEY": "test-api-key"}):
            client = tool._get_client()
        
        assert client is not None
        assert client.api_key == "test-api-key"
    
    def test_get_client_without_api_key(self):
        """Should raise error if no API key available."""
        tool = AtlasCloudImageToVideoTool()
        
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(AtlasCloudAuthError, match="API_KEY"):
                tool._get_client()
    
    def test_get_client_caching(self):
        """Should cache client instance."""
        tool = AtlasCloudImageToVideoTool()
        
        with patch.dict(os.environ, {"ATLASCLOUD_API_KEY": "test-key"}):
            client1 = tool._get_client()
            client2 = tool._get_client()
        
        assert client1 is client2


# Integration test (requires actual API key)
@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ATLASCLOUD_API_KEY"),
    reason="ATLASCLOUD_API_KEY not set"
)
@pytest.mark.asyncio
async def test_real_api_generation():
    """
    Real API integration test.
    
    Skipped unless ATLASCLOUD_API_KEY is set.
    Uses cheapest model to minimize cost.
    """
    tool = AtlasCloudImageToVideoTool()
    
    # Use a public test image URL
    test_image = "https://picsum.photos/500/500"
    
    result = await tool.execute(
        image=test_image,
        prompt="gentle camera zoom",
        model="bytedance/seedance-v1-lite-i2v-480p",
        duration=5,
        timeout=300
    )
    
    assert result.success, f"Generation failed: {result.error}"
    assert "video_path" in result.data
    assert Path(result.data["absolute_path"]).exists()
    
    # Cleanup
    Path(result.data["absolute_path"]).unlink(missing_ok=True)
