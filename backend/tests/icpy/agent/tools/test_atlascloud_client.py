"""
Unit tests for Atlas Cloud client

Tests client initialization, request building, response parsing,
error handling, and polling logic with mocked HTTP responses.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import httpx

from icpy.agent.tools.atlascloud.client import AtlasCloudClient
from icpy.agent.tools.atlascloud.models import VideoResult, VideoStatus
from icpy.agent.tools.atlascloud.exceptions import (
    AtlasCloudError,
    AtlasCloudAuthError,
    AtlasCloudRateLimitError,
    AtlasCloudTimeoutError,
    AtlasCloudInsufficientCreditsError,
    AtlasCloudNSFWError,
)


@pytest.fixture
def mock_api_key():
    """Mock API key for testing."""
    return "test-api-key-12345"


@pytest.fixture
def client(mock_api_key):
    """Create client instance with mock API key."""
    return AtlasCloudClient(api_key=mock_api_key)


@pytest.fixture
def mock_video_generation_response():
    """Mock successful video generation response."""
    return {
        "id": "test-request-123",
        "status": "queued",
        "urls": {
            "result": "https://api.atlascloud.ai/api/v1/model/result/test-request-123",
            "cancel": "https://api.atlascloud.ai/api/v1/model/cancel/test-request-123"
        },
        "model": "bytedance/seedance-v1-lite-t2v-480p",
        "input": {
            "model": "bytedance/seedance-v1-lite-t2v-480p",
            "prompt": "A serene sunset over mountains",
            "duration": 5,
            "aspect_ratio": "16:9"
        },
        "created_at": "2026-01-29T10:00:00Z"
    }


@pytest.fixture
def mock_video_result_complete():
    """Mock completed video result."""
    return {
        "id": "test-request-123",
        "status": "completed",
        "urls": {
            "result": "https://api.atlascloud.ai/api/v1/model/result/test-request-123"
        },
        "model": "bytedance/seedance-v1-lite-t2v-480p",
        "output": [
            "https://cdn.atlascloud.ai/generated/video-abc123.mp4"
        ],
        "has_nsfw_contents": [False],
        "created_at": "2026-01-29T10:00:00Z"
    }


@pytest.fixture
def mock_video_result_failed():
    """Mock failed video result."""
    return {
        "id": "test-request-123",
        "status": "failed",
        "urls": {},
        "logs": "Generation failed: Invalid prompt",
        "created_at": "2026-01-29T10:00:00Z"
    }


class TestClientInitialization:
    """Test client initialization and configuration."""
    
    def test_init_with_api_key(self, mock_api_key):
        """Test client initialization with explicit API key."""
        client = AtlasCloudClient(api_key=mock_api_key)
        assert client.api_key == mock_api_key
        assert client.base_url == "https://api.atlascloud.ai"
        assert client.timeout == AtlasCloudClient.DEFAULT_TIMEOUT
    
    def test_init_from_env_var(self, mock_api_key, monkeypatch):
        """Test client initialization from environment variable."""
        monkeypatch.setenv("ATLASCLOUD_API_KEY", mock_api_key)
        client = AtlasCloudClient()
        assert client.api_key == mock_api_key
    
    def test_init_without_api_key(self, monkeypatch):
        """Test client initialization fails without API key."""
        monkeypatch.delenv("ATLASCLOUD_API_KEY", raising=False)
        with pytest.raises(ValueError, match="ATLASCLOUD_API_KEY"):
            AtlasCloudClient()
    
    def test_custom_base_url(self, mock_api_key):
        """Test client with custom base URL."""
        custom_url = "https://custom.atlascloud.ai"
        client = AtlasCloudClient(api_key=mock_api_key, base_url=custom_url)
        assert client.base_url == custom_url
    
    def test_custom_timeout(self, mock_api_key):
        """Test client with custom timeout."""
        custom_timeout = 600  # 10 minutes
        client = AtlasCloudClient(api_key=mock_api_key, timeout=custom_timeout)
        assert client.timeout == custom_timeout


class TestErrorHandling:
    """Test error response handling."""
    
    @pytest.mark.asyncio
    async def test_auth_error_401(self, client):
        """Test 401 authentication error handling."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid API key"}
        
        with pytest.raises(AtlasCloudAuthError, match="Authentication failed"):
            client._handle_error_response(mock_response)
    
    @pytest.mark.asyncio
    async def test_rate_limit_error_429(self, client):
        """Test 429 rate limit error handling."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        
        with pytest.raises(AtlasCloudRateLimitError, match="Rate limit exceeded"):
            client._handle_error_response(mock_response)
    
    @pytest.mark.asyncio
    async def test_insufficient_credits_error(self, client):
        """Test insufficient credits error handling."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 402
        mock_response.json.return_value = {"error": "Insufficient credits"}
        
        with pytest.raises(AtlasCloudInsufficientCreditsError, match="Insufficient credits"):
            client._handle_error_response(mock_response)
    
    @pytest.mark.asyncio
    async def test_nsfw_error(self, client):
        """Test NSFW content rejection error handling."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Content rejected: NSFW detected"}
        
        with pytest.raises(AtlasCloudNSFWError, match="NSFW"):
            client._handle_error_response(mock_response)
    
    @pytest.mark.asyncio
    async def test_generic_error(self, client):
        """Test generic API error handling."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}
        
        with pytest.raises(AtlasCloudError, match="API error"):
            client._handle_error_response(mock_response)


class TestVideoGeneration:
    """Test video generation methods."""
    
    @pytest.mark.asyncio
    async def test_generate_video_text_to_video(
        self, client, mock_video_generation_response, mock_video_result_complete
    ):
        """Test text-to-video generation flow."""
        mock_http_client = AsyncMock()
        
        # Mock initial POST response
        post_response = AsyncMock(spec=httpx.Response)
        post_response.status_code = 200
        post_response.json.return_value = mock_video_generation_response
        
        # Mock GET result response (completed)
        get_response = AsyncMock(spec=httpx.Response)
        get_response.status_code = 200
        get_response.json.return_value = mock_video_result_complete
        
        mock_http_client.post.return_value = post_response
        mock_http_client.get.return_value = get_response
        
        client._client = mock_http_client
        
        result = await client.generate_video(
            model="bytedance/seedance-v1-lite-t2v-480p",
            prompt="A serene sunset over mountains",
            duration=5,
            wait_for_completion=True,
            poll_interval=0.1,  # Fast polling for tests
        )
        
        assert result.is_complete
        assert result.video_url == "https://cdn.atlascloud.ai/generated/video-abc123.mp4"
        assert result.id == "test-request-123"
    
    @pytest.mark.asyncio
    async def test_generate_video_image_to_video(self, client):
        """Test image-to-video generation."""
        mock_http_client = AsyncMock()
        
        response_data = {
            "id": "img-request-456",
            "status": "queued",
            "model": "bytedance/seedance-v1-lite-i2v-480p",
        }
        
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        
        mock_http_client.post.return_value = mock_response
        client._client = mock_http_client
        
        result = await client.generate_video(
            model="bytedance/seedance-v1-lite-i2v-480p",
            image="https://example.com/image.jpg",
            wait_for_completion=False,
        )
        
        assert result.id == "img-request-456"
        assert result.status == VideoStatus.QUEUED
    
    @pytest.mark.asyncio
    async def test_generate_video_validation_error(self, client):
        """Test validation error when neither prompt nor image provided."""
        with pytest.raises(ValueError, match="Either 'prompt' or 'image' must be provided"):
            await client.generate_video(model="test-model")
    
    @pytest.mark.asyncio
    async def test_generate_text_to_video_convenience(self, client):
        """Test text-to-video convenience method."""
        mock_http_client = AsyncMock()
        
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "conv-123",
            "status": "queued",
        }
        
        mock_http_client.post.return_value = mock_response
        client._client = mock_http_client
        
        result = await client.generate_text_to_video(
            prompt="Test prompt",
            wait_for_completion=False,
        )
        
        assert result.id == "conv-123"
    
    @pytest.mark.asyncio
    async def test_generate_image_to_video_convenience(self, client):
        """Test image-to-video convenience method."""
        mock_http_client = AsyncMock()
        
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "conv-456",
            "status": "queued",
        }
        
        mock_http_client.post.return_value = mock_response
        client._client = mock_http_client
        
        result = await client.generate_image_to_video(
            image="https://example.com/image.jpg",
            wait_for_completion=False,
        )
        
        assert result.id == "conv-456"
    
    @pytest.mark.asyncio
    async def test_generate_video_wrapped_response(self, client):
        """Test handling Atlas Cloud's wrapped API response format."""
        mock_http_client = AsyncMock()
        
        # Wrapped response format: {code, message, data}
        wrapped_post_response = {
            "code": 200,
            "message": "Success",
            "data": {
                "id": "wrapped-request-789",
                "status": "queued",
                "model": "bytedance/seedance-v1-lite-t2v-480p",
                "urls": {}
            },
            "timings": {"inference": 0}
        }
        
        wrapped_get_response = {
            "code": 200,
            "message": "Success",
            "data": {
                "id": "wrapped-request-789",
                "status": "completed",
                "output": ["https://cdn.atlascloud.ai/wrapped/video.mp4"],
                "urls": {}
            }
        }
        
        post_response = AsyncMock(spec=httpx.Response)
        post_response.status_code = 200
        post_response.json.return_value = wrapped_post_response
        
        get_response = AsyncMock(spec=httpx.Response)
        get_response.status_code = 200
        get_response.json.return_value = wrapped_get_response
        
        mock_http_client.post.return_value = post_response
        mock_http_client.get.return_value = get_response
        client._client = mock_http_client
        
        result = await client.generate_video(
            model="bytedance/seedance-v1-lite-t2v-480p",
            prompt="Test wrapped response",
            wait_for_completion=True,
            poll_interval=0.1,
        )
        
        assert result.id == "wrapped-request-789"
        assert result.is_complete
        assert result.video_url == "https://cdn.atlascloud.ai/wrapped/video.mp4"


class TestResultPolling:
    """Test result polling and waiting logic."""
    
    @pytest.mark.asyncio
    async def test_get_result(self, client, mock_video_result_complete):
        """Test getting result by request ID."""
        mock_http_client = AsyncMock()
        
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_video_result_complete
        
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client
        
        result = await client.get_result("test-request-123")
        
        assert result.id == "test-request-123"
        assert result.is_complete
        assert result.video_url == "https://cdn.atlascloud.ai/generated/video-abc123.mp4"
    
    @pytest.mark.asyncio
    async def test_get_result_wrapped_response(self, client):
        """Test getting result with wrapped API response."""
        mock_http_client = AsyncMock()
        
        wrapped_response = {
            "code": 200,
            "message": "Success",
            "data": {
                "id": "wrapped-result-999",
                "status": "completed",
                "output": ["https://cdn.atlascloud.ai/wrapped.mp4"],
                "urls": {}
            }
        }
        
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = wrapped_response
        
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client
        
        result = await client.get_result("wrapped-result-999")
        
        assert result.id == "wrapped-result-999"
        assert result.is_complete
        assert result.video_url == "https://cdn.atlascloud.ai/wrapped.mp4"
    
    @pytest.mark.asyncio
    async def test_wait_for_result_success(self, client, mock_video_result_complete):
        """Test waiting for result to complete."""
        mock_http_client = AsyncMock()
        
        # First call: processing
        processing_response = AsyncMock(spec=httpx.Response)
        processing_response.status_code = 200
        processing_response.json.return_value = {
            "id": "test-request-123",
            "status": "processing",
        }
        
        # Second call: completed
        complete_response = AsyncMock(spec=httpx.Response)
        complete_response.status_code = 200
        complete_response.json.return_value = mock_video_result_complete
        
        mock_http_client.get.side_effect = [processing_response, complete_response]
        client._client = mock_http_client
        
        result = await client.wait_for_result(
            "test-request-123",
            poll_interval=0.1,
            timeout=10,
        )
        
        assert result.is_complete
        assert mock_http_client.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_wait_for_result_with_created_status(self, client, mock_video_result_complete):
        """Test waiting for result when initially in 'created' status."""
        mock_http_client = AsyncMock()
        
        # First call: created status
        created_response = AsyncMock(spec=httpx.Response)
        created_response.status_code = 200
        created_response.json.return_value = {
            "id": "test-request-123",
            "status": "created",
        }
        
        # Second call: completed
        complete_response = AsyncMock(spec=httpx.Response)
        complete_response.status_code = 200
        complete_response.json.return_value = mock_video_result_complete
        
        mock_http_client.get.side_effect = [created_response, complete_response]
        client._client = mock_http_client
        
        result = await client.wait_for_result(
            "test-request-123",
            poll_interval=0.1,
            timeout=10,
        )
        
        assert result.is_complete
        assert mock_http_client.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_wait_for_result_timeout(self, client):
        """Test timeout when waiting for result."""
        mock_http_client = AsyncMock()
        
        # Always return processing status
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test-request-123",
            "status": "processing",
        }
        
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client
        
        with pytest.raises(AtlasCloudTimeoutError, match="timed out"):
            await client.wait_for_result(
                "test-request-123",
                poll_interval=0.1,
                timeout=0.5,  # Short timeout for test
            )
    
    @pytest.mark.asyncio
    async def test_wait_for_result_failure(self, client, mock_video_result_failed):
        """Test handling of failed generation."""
        mock_http_client = AsyncMock()
        
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_video_result_failed
        
        mock_http_client.get.return_value = mock_response
        client._client = mock_http_client
        
        with pytest.raises(AtlasCloudError, match="generation failed"):
            await client.wait_for_result("test-request-123")


class TestContextManager:
    """Test async context manager support."""
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_api_key):
        """Test using client as async context manager."""
        async with AtlasCloudClient(api_key=mock_api_key) as client:
            assert client._client is not None
            assert isinstance(client._client, httpx.AsyncClient)
        
        # Client should be closed after context exit
        assert client._client is None or client._client.is_closed
    
    @pytest.mark.asyncio
    async def test_manual_close(self, client):
        """Test manual client closing."""
        await client._ensure_client()
        assert client._client is not None
        
        await client.close()
        assert client._client is None


class TestVideoResultModel:
    """Test VideoResult model properties."""
    
    def test_is_complete(self):
        """Test is_complete property."""
        result = VideoResult(id="123", status=VideoStatus.COMPLETED)
        assert result.is_complete is True
        
        result = VideoResult(id="123", status=VideoStatus.PROCESSING)
        assert result.is_complete is False
    
    def test_is_failed(self):
        """Test is_failed property."""
        result = VideoResult(id="123", status=VideoStatus.FAILED)
        assert result.is_failed is True
        
        result = VideoResult(id="123", status=VideoStatus.COMPLETED)
        assert result.is_failed is False
    
    def test_is_processing(self):
        """Test is_processing property."""
        result = VideoResult(id="123", status=VideoStatus.CREATED)
        assert result.is_processing is True
        
        result = VideoResult(id="123", status=VideoStatus.QUEUED)
        assert result.is_processing is True
        
        result = VideoResult(id="123", status=VideoStatus.PROCESSING)
        assert result.is_processing is True
        
        result = VideoResult(id="123", status=VideoStatus.COMPLETED)
        assert result.is_processing is False
    
    def test_video_url(self):
        """Test video_url property."""
        # Test with output list
        result = VideoResult(
            id="123",
            status=VideoStatus.COMPLETED,
            output=["https://example.com/video.mp4"]
        )
        assert result.video_url == "https://example.com/video.mp4"
        
        # Test with video field (alternative)
        result = VideoResult(
            id="123",
            status=VideoStatus.COMPLETED,
            video="https://example.com/single-video.mp4"
        )
        assert result.video_url == "https://example.com/single-video.mp4"
        
        # Test with urls dict
        result = VideoResult(
            id="123",
            status=VideoStatus.COMPLETED,
            urls={"video": "https://example.com/url-video.mp4"}
        )
        assert result.video_url == "https://example.com/url-video.mp4"
        
        # Test with no video URL
        result = VideoResult(id="123", status=VideoStatus.QUEUED)
        assert result.video_url is None


# Integration tests (requires real API key)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api_text_to_video():
    """
    Integration test with real API (requires ATLASCLOUD_API_KEY).
    Marked as integration test - skip by default.
    """
    import os
    api_key = os.getenv("ATLASCLOUD_API_KEY")
    
    if not api_key:
        pytest.skip("ATLASCLOUD_API_KEY not set")
    
    async with AtlasCloudClient(api_key=api_key) as client:
        result = await client.generate_text_to_video(
            prompt="A cat walking on a sidewalk",
            duration=5,  # Minimum duration to minimize cost
            timeout=300,
        )
        
        assert result.is_complete
        assert result.video_url is not None
        assert result.video_url.startswith("http")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api_get_result():
    """
    Integration test for get_result (requires valid request_id).
    Marked as integration test - skip by default.
    """
    import os
    api_key = os.getenv("ATLASCLOUD_API_KEY")
    request_id = os.getenv("TEST_REQUEST_ID")  # Must be set to test
    
    if not api_key or not request_id:
        pytest.skip("ATLASCLOUD_API_KEY or TEST_REQUEST_ID not set")
    
    async with AtlasCloudClient(api_key=api_key) as client:
        result = await client.get_result(request_id)
        
        assert result.id == request_id
        assert result.status in VideoStatus
