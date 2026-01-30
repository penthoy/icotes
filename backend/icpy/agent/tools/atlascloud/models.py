"""
Pydantic models for Atlas Cloud API request/response structures
"""

from typing import Optional, List, Dict, Any, Literal, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class VideoStatus(str, Enum):
    """Video generation job status."""
    CREATED = "created"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class AtlasAPIResponse(BaseModel):
    """Wrapper for Atlas Cloud API responses."""
    code: int = Field(description="HTTP status code")
    message: str = Field(description="Response message")
    data: Optional[Union[Dict[str, Any], List[Any]]] = Field(
        None,
        description="Response data payload"
    )
    
    class Config:
        extra = 'allow'  # Allow additional fields like 'timings'


class VideoGenerationRequest(BaseModel):
    """Request model for video generation API."""
    
    model: str = Field(
        description="Model identifier (e.g., 'bytedance/seedance-v1-lite-t2v-480p')"
    )
    prompt: Optional[str] = Field(
        None,
        max_length=2000,
        description="Text prompt for video generation (max 2000 chars)"
    )
    image: Optional[str] = Field(
        None,
        description="Input image URL or base64 string (for image-to-video models)"
    )
    video: Optional[str] = Field(
        None,
        description="Input video URL (for video-to-video models like mmaudio-v2)"
    )
    duration: Optional[int] = Field(
        5,
        ge=5,
        le=10,
        description="Video duration in seconds (5-10)"
    )
    aspect_ratio: Optional[Literal["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"]] = Field(
        "16:9",
        description="Video aspect ratio"
    )
    seed: Optional[int] = Field(
        -1,
        description="Random seed for reproducibility (-1 for random)"
    )
    last_image: Optional[str] = Field(
        None,
        description="Optional end frame image (for interpolation)"
    )
    
    class Config:
        use_enum_values = True


class VideoGenerationResponse(BaseModel):
    """Initial response from video generation API."""
    
    id: str = Field(description="Unique request ID for polling results")
    status: VideoStatus = Field(description="Current job status")
    urls: Dict[str, str] = Field(
        default_factory=dict,
        description="URLs for result polling and cancellation"
    )
    input: Optional[Dict[str, Any]] = Field(
        None,
        description="Echo of input parameters"
    )
    model: Optional[str] = Field(None, description="Model name")
    logs: Optional[str] = Field(None, description="Generation logs")
    created_at: Optional[datetime] = Field(None, description="Request creation timestamp")
    
    class Config:
        use_enum_values = True


class VideoResult(BaseModel):
    """Final result from video generation with outputs."""
    
    id: str = Field(description="Request ID")
    status: VideoStatus = Field(description="Final job status")
    urls: Dict[str, str] = Field(
        default_factory=dict,
        description="URLs for polling and cancellation"
    )
    input: Optional[Dict[str, Any]] = Field(
        None,
        description="Input parameters used"
    )
    model: Optional[str] = Field(None, description="Model name")
    output: Optional[List[str]] = Field(
        None,
        description="List of generated video URLs"
    )
    outputs: Optional[List[str]] = Field(
        None,
        description="List of generated video URLs (alternative field name)"
    )
    video: Optional[str] = Field(
        None,
        description="Single video URL (alternative field name)"
    )
    prediction: Optional[Dict[str, Any]] = Field(
        None,
        description="Prediction details with download URLs"
    )
    has_nsfw_contents: Optional[List[bool]] = Field(
        None,
        description="NSFW flags for each output"
    )
    logs: Optional[str] = Field(None, description="Generation logs")
    error: Optional[str] = Field(None, description="Error message if generation failed")
    created_at: Optional[datetime] = Field(None, description="Request timestamp")
    
    class Config:
        use_enum_values = True
        extra = 'allow'  # Allow additional fields we don't know about
    
    @property
    def is_complete(self) -> bool:
        """Check if generation is complete.
        
        Note: Handles both VideoStatus enum and string values due to Pydantic's
        use_enum_values=True which may deserialize status as string "completed"
        instead of VideoStatus.COMPLETED enum.
        """
        status_val = self.status.value if isinstance(self.status, VideoStatus) else self.status
        return status_val == VideoStatus.COMPLETED.value
    
    @property
    def is_failed(self) -> bool:
        """Check if generation failed.
        
        Note: Handles both VideoStatus enum and string values. See is_complete docstring.
        """
        status_val = self.status.value if isinstance(self.status, VideoStatus) else self.status
        return status_val == VideoStatus.FAILED.value
    
    @property
    def is_processing(self) -> bool:
        """Check if generation is still in progress."""
        return self.status in (VideoStatus.CREATED, VideoStatus.QUEUED, VideoStatus.PROCESSING)
    
    @property
    def video_url(self) -> Optional[str]:
        """Get the first direct video file URL, skipping API endpoints."""
        # Check common field names for video URLs (both singular and plural forms)
        url_fields = [
            self.outputs,  # Atlas Cloud uses 'outputs' (plural)
            self.output,   # Some APIs use 'output' (singular)
        ]
        
        for field in url_fields:
            if field and isinstance(field, list):
                for url in field:
                    if url and self._is_direct_file_url(url):
                        return url
        
        # Check single URL field
        if self.video and self._is_direct_file_url(self.video):
            return self.video
        
        # Check nested structures
        if self.prediction:
            url = self._extract_url_from_dict(self.prediction)
            if url:
                return url
        
        if self.urls:
            url = self._extract_url_from_dict(self.urls)
            if url:
                return url
        
        return None
    
    def _is_direct_file_url(self, url: str) -> bool:
        """Check if URL is a direct file URL (not an API endpoint)."""
        if not url or not isinstance(url, str):
            return False
        if not (url.startswith('http://') or url.startswith('https://')):
            return False
        # CDN URLs (CloudFront, etc.) are always valid direct file URLs
        cdn_domains = ['cloudfront.net', 'cdn.', 'akamai', 's3.amazonaws.com']
        if any(cdn in url.lower() for cdn in cdn_domains):
            return True
        # Skip API endpoints - they require authentication and return metadata, not files
        api_indicators = ['/api/', '/v1/', '/v2/', '/v3/', '/model/', '/prediction/']
        return not any(indicator in url for indicator in api_indicators)
    
    def _extract_url_from_dict(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract first valid video URL from a dictionary."""
        priority_keys = ['download', 'video_url', 'file', 'url', 'output', 'video']
        for key in priority_keys:
            if key in data:
                value = data[key]
                if isinstance(value, str) and self._is_direct_file_url(value):
                    return value
                elif isinstance(value, list) and value:
                    for item in value:
                        if isinstance(item, str) and self._is_direct_file_url(item):
                            return item
        return None
        return any(indicator in url for indicator in api_indicators)
