"""
Atlascloud video generation client and tools

Provides async HTTP client for Atlas Cloud's unified AI model API,
including video generation (Seedance, Kling, Veo, Wan, etc.) and
OpenAI-compatible LLM inference.
"""

from .client import AtlasCloudClient
from .models import (
    AtlasAPIResponse,
    VideoGenerationRequest,
    VideoGenerationResponse,
    VideoResult,
    VideoStatus,
)
from .exceptions import (
    AtlasCloudError,
    AtlasCloudAuthError,
    AtlasCloudRateLimitError,
    AtlasCloudTimeoutError,
    AtlasCloudInsufficientCreditsError,
    AtlasCloudNSFWError,
)

__all__ = [
    "AtlasCloudClient",
    "AtlasAPIResponse",
    "VideoGenerationRequest",
    "VideoGenerationResponse",
    "VideoResult",
    "VideoStatus",
    "AtlasCloudError",
    "AtlasCloudAuthError",
    "AtlasCloudRateLimitError",
    "AtlasCloudTimeoutError",
    "AtlasCloudInsufficientCreditsError",
    "AtlasCloudNSFWError",
]
