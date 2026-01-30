"""
Custom exceptions for Atlas Cloud API interactions
"""


class AtlasCloudError(Exception):
    """Base exception for all Atlas Cloud API errors."""
    
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        """
        Initialize the exception with a message and optional HTTP metadata.
        
        Parameters:
            message (str): Human-readable error message describing the failure.
            status_code (int, optional): HTTP status code associated with the error, if available.
            response (dict, optional): Parsed response body or additional metadata returned by the API.
        """
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class AtlasCloudAuthError(AtlasCloudError):
    """Authentication failed (401) - invalid or missing API key."""
    pass


class AtlasCloudRateLimitError(AtlasCloudError):
    """Rate limit exceeded (429) - too many requests."""
    pass


class AtlasCloudTimeoutError(AtlasCloudError):
    """Request timed out waiting for video generation to complete."""
    pass


class AtlasCloudInsufficientCreditsError(AtlasCloudError):
    """Insufficient credits to process the request."""
    pass


class AtlasCloudNSFWError(AtlasCloudError):
    """Content rejected due to NSFW filter."""
    pass