"""
Async HTTP client for Atlas Cloud API

Handles video generation requests, result polling, and error handling.
Supports text-to-video and image-to-video models.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import httpx

from .models import VideoGenerationRequest, VideoGenerationResponse, VideoResult, VideoStatus
from .exceptions import (
    AtlasCloudError,
    AtlasCloudAuthError,
    AtlasCloudRateLimitError,
    AtlasCloudTimeoutError,
    AtlasCloudInsufficientCreditsError,
    AtlasCloudNSFWError,
)

logger = logging.getLogger(__name__)


class AtlasCloudClient:
    """
    Async HTTP client for Atlas Cloud video generation API.
    
    Supports:
    - Text-to-video generation
    - Image-to-video generation
    - Async job polling with configurable timeouts
    - Automatic error handling and retries
    
    Example:
        >>> client = AtlasCloudClient(api_key="your-key")
        >>> result = await client.generate_video(
        ...     model="bytedance/seedance-v1-lite-t2v-480p",
        ...     prompt="A serene sunset over mountains"
        ... )
        >>> video_url = result.video_url
    """
    
    BASE_URL = "https://api.atlascloud.ai"
    DEFAULT_TIMEOUT = 300  # 5 minutes
    DEFAULT_POLL_INTERVAL = 2  # seconds
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize Atlas Cloud client.
        
        Args:
            api_key: API key (defaults to ATLASCLOUD_API_KEY env var)
            base_url: API base URL (defaults to https://api.atlascloud.ai)
            timeout: Default request timeout in seconds
        """
        self.api_key = api_key or os.getenv("ATLASCLOUD_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ATLASCLOUD_API_KEY must be provided or set as environment variable. "
                "Get your API key from https://console.atlascloud.ai/settings"
            )
        
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        
        # Create async HTTP client with auth headers
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
    
    async def close(self):
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    def _handle_error_response(self, response: httpx.Response) -> None:
        """
        Handle error responses and raise appropriate exceptions.
        
        Args:
            response: HTTP response object
            
        Raises:
            AtlasCloudAuthError: Authentication failed (401)
            AtlasCloudRateLimitError: Rate limit exceeded (429)
            AtlasCloudInsufficientCreditsError: Insufficient credits
            AtlasCloudNSFWError: NSFW content rejected
            AtlasCloudError: Other API errors
        """
        status_code = response.status_code
        
        try:
            error_data = response.json()
        except Exception:
            error_data = {"error": response.text}
        
        error_message = error_data.get("error", str(error_data))
        
        # Map status codes to specific exceptions
        if status_code == 401:
            raise AtlasCloudAuthError(
                f"Authentication failed: {error_message}",
                status_code=status_code,
                response=error_data,
            )
        elif status_code == 429:
            raise AtlasCloudRateLimitError(
                f"Rate limit exceeded: {error_message}",
                status_code=status_code,
                response=error_data,
            )
        elif "insufficient" in str(error_message).lower() or "credit" in str(error_message).lower():
            raise AtlasCloudInsufficientCreditsError(
                f"Insufficient credits: {error_message}",
                status_code=status_code,
                response=error_data,
            )
        elif "nsfw" in str(error_message).lower():
            raise AtlasCloudNSFWError(
                f"Content rejected (NSFW): {error_message}",
                status_code=status_code,
                response=error_data,
            )
        else:
            raise AtlasCloudError(
                f"API error ({status_code}): {error_message}",
                status_code=status_code,
                response=error_data,
            )
    
    async def generate_video(
        self,
        model: str,
        prompt: Optional[str] = None,
        image: Optional[str] = None,        video: Optional[str] = None,        duration: int = 5,
        aspect_ratio: str = "16:9",
        seed: int = -1,
        last_image: Optional[str] = None,
        wait_for_completion: bool = True,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: Optional[float] = None,
    ) -> VideoResult:
        """
        Generate a video using Atlas Cloud API.
        
        Args:
            model: Model identifier (e.g., 'bytedance/seedance-v1-lite-t2v-480p')
            prompt: Text prompt for generation (required for text-to-video)
            image: Image URL or base64 (required for image-to-video)
            video: Video URL (required for video-to-video models like mmaudio-v2)
            duration: Video duration in seconds (5-10)
            aspect_ratio: Video aspect ratio (16:9, 1:1, etc.)
            seed: Random seed for reproducibility (-1 for random)
            last_image: Optional end frame for interpolation
            wait_for_completion: If True, poll until complete; if False, return immediately
            poll_interval: Seconds between polling requests
            timeout: Maximum wait time in seconds (defaults to client timeout)
            
        Returns:
            VideoResult with status and output URLs (if complete)
            
        Raises:
            ValueError: Invalid parameters
            AtlasCloudTimeoutError: Generation timed out
            AtlasCloudError: API error occurred
        """
        # Validate inputs
        if not prompt and not image and not video:
            raise ValueError("Either 'prompt', 'image', or 'video' must be provided")
        
        # Build request
        request_data = VideoGenerationRequest(
            model=model,
            prompt=prompt,
            image=image,
            video=video,
            duration=duration,
            aspect_ratio=aspect_ratio,
            seed=seed,
            last_image=last_image,
        )
        
        await self._ensure_client()
        
        # Submit generation request
        logger.info(f"Submitting video generation request: model={model}, prompt={prompt[:50] if prompt else 'N/A'}...")
        
        try:
            response = await self._client.post(
                "/api/v1/model/generateVideo",
                json=request_data.model_dump(exclude_none=True),
            )
            
            if response.status_code != 200:
                self._handle_error_response(response)
            
            # Parse initial response (API returns wrapped response)
            response_data = response.json()
            
            # Handle wrapped API response
            if 'code' in response_data and 'data' in response_data:
                from .models import AtlasAPIResponse
                wrapped = AtlasAPIResponse(**response_data)
                if wrapped.code != 200:
                    raise AtlasCloudError(f"API error: {wrapped.message}", status_code=wrapped.code)
                actual_data = wrapped.data or {}
            else:
                actual_data = response_data
            
            initial_response = VideoGenerationResponse(**actual_data)
            
            logger.info(f"Video generation started: request_id={initial_response.id}, status={initial_response.status}")
            
            # If not waiting, return immediately
            if not wait_for_completion:
                return VideoResult(**actual_data)
            
            # Poll for completion
            return await self.wait_for_result(
                request_id=initial_response.id,
                poll_interval=poll_interval,
                timeout=timeout or self.timeout,
            )
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during video generation: {e}")
            raise AtlasCloudError(f"Network error: {e}") from e
    
    async def get_result(self, request_id: str) -> VideoResult:
        """
        Get the current status/result of a video generation request.
        
        Args:
            request_id: Unique request ID from initial generation response
            
        Returns:
            VideoResult with current status and outputs (if complete)
            
        Raises:
            AtlasCloudError: API error occurred
        """
        await self._ensure_client()
        
        try:
            response = await self._client.get(f"/api/v1/model/result/{request_id}")
            
            if response.status_code != 200:
                self._handle_error_response(response)
            
            # Handle wrapped API response
            response_data = response.json()
            # AtlasCloud wraps responses in {code, message, data} structure
            if 'code' in response_data and 'data' in response_data:
                from .models import AtlasAPIResponse
                wrapped = AtlasAPIResponse(**response_data)
                if wrapped.code != 200:
                    raise AtlasCloudError(f"API error: {wrapped.message}", status_code=wrapped.code)
                actual_data = wrapped.data or {}
            else:
                actual_data = response_data
            
            result = VideoResult(**actual_data)
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting result for {request_id}: {e}")
            raise AtlasCloudError(f"Network error: {e}") from e
    
    async def wait_for_result(
        self,
        request_id: str,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> VideoResult:
        """
        Poll for video generation completion with exponential backoff.
        
        Args:
            request_id: Request ID to poll
            poll_interval: Initial seconds between polls
            timeout: Maximum wait time in seconds
            
        Returns:
            VideoResult when complete
            
        Raises:
            AtlasCloudTimeoutError: Exceeded timeout
            AtlasCloudError: Generation failed
        """
        start_time = datetime.now()
        max_wait = timedelta(seconds=timeout)
        current_interval = poll_interval
        
        logger.info(f"Waiting for video generation {request_id} to complete (timeout: {timeout}s)...")
        
        while True:
            elapsed = datetime.now() - start_time
            
            if elapsed > max_wait:
                raise AtlasCloudTimeoutError(
                    f"Video generation timed out after {timeout} seconds. Request ID: {request_id}"
                )
            
            # Get current status
            result = await self.get_result(request_id)
            
            if result.is_complete:
                logger.info(f"Video generation complete: {request_id}")
                return result
            
            if result.is_failed:
                # Note: result.logs may be None/empty for some failures
                # Common failure: "Unable to download or load video" when SITE_URL is not publicly accessible
                error_msg = result.logs or result.error or "Unknown error"
                logger.error(f"Video generation failed for {request_id}: {error_msg}")
                raise AtlasCloudError(
                    f"Video generation failed: {error_msg}",
                    response={"request_id": request_id, "status": result.status}
                )
            
            # Still processing - wait and retry
            logger.debug(f"Video generation {request_id} status: {result.status}, waiting {current_interval}s...")
            await asyncio.sleep(current_interval)
            
            # Exponential backoff (max 10 seconds)
            current_interval = min(current_interval * 1.2, 10)
    
    async def generate_text_to_video(
        self,
        prompt: str,
        model: str = "bytedance/seedance-v1-lite-t2v-480p",
        **kwargs
    ) -> VideoResult:
        """
        Convenience method for text-to-video generation.
        
        Args:
            prompt: Text description of video to generate
            model: Video model to use (defaults to cheapest)
            **kwargs: Additional parameters (duration, aspect_ratio, etc.)
            
        Returns:
            VideoResult with generated video
        """
        return await self.generate_video(model=model, prompt=prompt, **kwargs)
    
    async def generate_image_to_video(
        self,
        image: str,
        model: str = "bytedance/seedance-v1-lite-i2v-480p",
        prompt: Optional[str] = None,
        **kwargs
    ) -> VideoResult:
        """
        Convenience method for image-to-video generation.
        
        Args:
            image: Image URL or base64 string
            model: Video model to use (defaults to cheapest)
            prompt: Optional text prompt to guide generation
            **kwargs: Additional parameters (duration, aspect_ratio, etc.)
            
        Returns:
            VideoResult with generated video
        """
        return await self.generate_video(
            model=model,
            image=image,
            prompt=prompt,
            **kwargs
        )
    
    async def generate_video_to_video_with_sound(
        self,
        video: str,
        prompt: str,
        model: str = "atlascloud/mmaudio-v2",
        **kwargs
    ) -> VideoResult:
        """
        Convenience method for video-to-video-with-sound generation.
        
        Args:
            video: Video URL to add sound to
            prompt: Text description of audio to generate
            model: Video-to-video model to use (defaults to mmaudio-v2)
            **kwargs: Additional parameters (wait_for_completion, timeout, etc.)
            
        Returns:
            VideoResult with generated video with sound
        """
        return await self.generate_video(
            model=model,
            video=video,
            prompt=prompt,
            **kwargs
        )
