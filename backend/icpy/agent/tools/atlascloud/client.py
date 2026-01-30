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
        Create a configured AtlasCloudClient instance.
        
        Parameters:
            api_key (Optional[str]): API key to authenticate requests. If omitted, the `ATLASCLOUD_API_KEY` environment variable is used.
            base_url (Optional[str]): API base URL; defaults to https://api.atlascloud.ai.
            timeout (float): Default request timeout in seconds.
        
        Raises:
            ValueError: If no API key is provided and `ATLASCLOUD_API_KEY` is not set.
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
        """
        Ensure the internal HTTP client is created and return the client instance for use as an async context manager.
        
        Returns:
            AtlasCloudClient: The client instance with an initialized HTTP client.
        """
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Close the client's underlying HTTP connection when exiting an async context.
        
        This ensures the internal HTTP client is closed if it was created.
        """
        await self.close()
    
    async def _ensure_client(self):
        """
        Ensure the internal HTTP client is created and configured for use.
        
        Creates and stores an AsyncClient configured with the client's base URL, authorization header, content type, and timeout if no client currently exists.
        """
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
        """
        Close and clean up the underlying HTTP client if it exists.
        
        Closes the internal httpx.AsyncClient and clears the stored client reference so the client can be re-created later.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    def _handle_error_response(self, response: httpx.Response) -> None:
        """
        Raise a specific AtlasCloud* exception based on an HTTP error response.
        
        Inspect the HTTP status and returned error payload to choose and raise the most specific AtlasCloud exception.
        
        Parameters:
            response (httpx.Response): The HTTP response returned by the Atlas Cloud API.
        
        Raises:
            AtlasCloudAuthError: When the response status code is 401 (authentication failed).
            AtlasCloudRateLimitError: When the response status code is 429 (rate limit exceeded).
            AtlasCloudInsufficientCreditsError: When the error payload or message indicates insufficient credits.
            AtlasCloudNSFWError: When the error payload or message indicates NSFW/content rejection.
            AtlasCloudError: For all other API error responses.
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
        Start a video generation request with the specified model and inputs, and optionally wait until the request completes.
        
        Parameters:
            model (str): Model identifier to use for generation.
            prompt (Optional[str]): Text prompt for text-to-video generation.
            image (Optional[str]): Image URL or base64 input for image-to-video generation.
            video (Optional[str]): Source video URL for video-to-video generation.
            duration (int): Requested video duration in seconds.
            aspect_ratio (str): Desired output aspect ratio (e.g., "16:9", "1:1").
            seed (int): Random seed for reproducible results (-1 selects a random seed).
            last_image (Optional[str]): Optional end-frame image for interpolation workflows.
            wait_for_completion (bool): If True, poll until the generation completes and return the final result; if False, return the initial result immediately.
            poll_interval (float): Seconds between polling attempts when waiting for completion.
            timeout (Optional[float]): Maximum time in seconds to wait for completion (uses client timeout if omitted).
        
        Returns:
            VideoResult: The current or final generation result, including status and output URLs (if available).
        
        Raises:
            ValueError: If none of `prompt`, `image`, or `video` is provided.
            AtlasCloudTimeoutError: If waiting for completion exceeds the provided timeout.
            AtlasCloudError: For API errors or network failures.
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
        Get the current status and outputs (if available) for a video generation request.
        
        Parameters:
            request_id (str): Request identifier returned by the generation endpoint.
        
        Returns:
            VideoResult: Current status and any generated outputs.
        
        Raises:
            AtlasCloudError: If the API returns an error or a network/HTTP error occurs.
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
        Waits for a video generation request to finish by polling its status until completion or failure.
        
        Polls the server for the given request's status, starting with intervals of poll_interval seconds and increasing the delay by a factor of 1.2 between attempts (capped at 10 seconds), until the request completes, fails, or the total wait time exceeds timeout seconds.
        
        Parameters:
            request_id (str): The ID of the generation request to poll.
            poll_interval (float): Initial number of seconds to wait between polls.
            timeout (float): Maximum total number of seconds to wait before giving up.
        
        Returns:
            VideoResult: The final result when the generation is complete.
        
        Raises:
            AtlasCloudTimeoutError: If the wait exceeds the specified timeout.
            AtlasCloudError: If the generation finishes with a failure status.
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
        Generate a video from a text prompt using the specified model.
        
        Parameters:
            prompt (str): Text description of the video to generate.
            model (str): Model identifier to use for generation (default "bytedance/seedance-v1-lite-t2v-480p").
            **kwargs: Additional generation options (e.g., duration, aspect_ratio, seed, wait_for_completion, poll_interval, timeout).
        
        Returns:
            VideoResult: Result object representing the generated video or its current processing state.
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
        Create a new video by adding generated audio to an existing video using the specified model.
        
        Submits a video-to-video request that synthesizes audio from `prompt` and merges it into `video` according to the provided model and options.
        
        Parameters:
            video (str): URL or path of the source video to add sound to.
            prompt (str): Text describing the desired audio to generate and apply to the video.
            model (str): Model identifier to use; defaults to "atlascloud/mmaudio-v2".
            **kwargs: Additional generation options such as `wait_for_completion`, `timeout`, and `poll_interval`.
        
        Returns:
            VideoResult: Result object containing the generated video with the added audio and associated metadata.
        """
        return await self.generate_video(
            model=model,
            video=video,
            prompt=prompt,
            **kwargs
        )