"""
Test YouTube Download Tool

Basic tests for the YouTube downloader tool.
"""

import pytest
from icpy.agent.tools.youtube_download_tool import YouTubeDownloadTool, YT_DLP_AVAILABLE

# Skip all tests if yt-dlp is not available
pytestmark = pytest.mark.skipif(not YT_DLP_AVAILABLE, reason="yt-dlp not installed")


class TestYouTubeDownloadTool:
    """Test suite for YouTube download tool"""
    
    @pytest.fixture
    def tool(self):
        """Create tool instance"""
        return YouTubeDownloadTool()
    
    def test_tool_initialization(self, tool):
        """Test that tool initializes correctly"""
        assert tool.name == "youtube_download"
        assert "YouTube" in tool.description
        assert "url" in tool.parameters["properties"]
        assert "quality" in tool.parameters["properties"]
    
    def test_extract_video_id_standard_url(self, tool):
        """Test video ID extraction from standard YouTube URL"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = tool._extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_short_url(self, tool):
        """Test video ID extraction from short YouTube URL"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        video_id = tool._extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_with_timestamp(self, tool):
        """Test video ID extraction from URL with timestamp"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=123"
        video_id = tool._extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_invalid_url(self, tool):
        """Test video ID extraction from invalid URL"""
        url = "https://example.com/not-a-youtube-video"
        video_id = tool._extract_video_id(url)
        assert video_id is None
    
    def test_sanitize_filename(self, tool):
        """Test filename sanitization"""
        # Test with invalid characters
        result = tool._sanitize_filename("Test: Video | Name?")
        assert ":" not in result
        assert "|" not in result
        assert "?" not in result
        
        # Test with spaces
        result = tool._sanitize_filename("Test   Multiple   Spaces")
        assert "___" not in result  # Multiple spaces should become single underscore
        
        # Test with valid filename
        result = tool._sanitize_filename("Valid_Filename_123")
        assert result == "Valid_Filename_123"
    
    def test_quality_presets_exist(self, tool):
        """Test that quality presets are properly defined"""
        from icpy.agent.tools.youtube_download_tool import QUALITY_PRESETS
        
        assert 'low' in QUALITY_PRESETS
        assert 'medium' in QUALITY_PRESETS
        assert 'high' in QUALITY_PRESETS
        assert 'audio_only' in QUALITY_PRESETS
        
        # Check each preset has required fields
        for quality, preset in QUALITY_PRESETS.items():
            assert 'format' in preset
            assert 'description' in preset
            assert 'max_filesize' in preset
    
    def test_rate_limiting(self, tool):
        """Test rate limiting mechanism"""
        from icpy.agent.tools.youtube_download_tool import _rate_limit_tracker
        
        # Clear tracker
        _rate_limit_tracker.clear()

        try:
            # First 3 requests should succeed
            for _ in range(3):
                allowed, error = tool._check_rate_limit()
                assert allowed is True
                assert error is None

            # 4th request should fail
            allowed, error = tool._check_rate_limit()
            assert allowed is False
            assert error is not None
            assert "Rate limit exceeded" in error
        finally:
            _rate_limit_tracker.clear()
    
    @pytest.mark.asyncio
    async def test_execute_missing_url(self, tool):
        """Test execution with missing URL"""
        result = await tool.execute()
        assert result.success is False
        assert "Missing required parameter" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_invalid_url(self, tool):
        """Test execution with invalid URL"""
        # Clear rate limiter to avoid interference
        from icpy.agent.tools.youtube_download_tool import _rate_limit_tracker
        _rate_limit_tracker.clear()
        
        result = await tool.execute(url="https://example.com/not-youtube")
        assert result.success is False
        assert "Invalid YouTube URL" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_invalid_quality(self, tool):
        """Test execution with invalid quality option"""
        result = await tool.execute(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            quality="ultra_high"
        )
        assert result.success is False
        assert "Invalid quality" in result.error
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.integration
    async def test_get_video_info(self, tool):
        """
        Integration test: Get metadata for a real video.
        Uses a stable, well-known video for testing.
        """
        # Using a short, stable public domain video
        url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        video_id = "jNQXAC9IVRw"
        
        success, metadata, error = await tool._get_video_info(url, video_id)
        
        assert success is True
        assert metadata is not None
        assert error is None
        
        # Check metadata structure
        assert 'video_id' in metadata
        assert 'title' in metadata
        assert 'uploader' in metadata
        assert 'duration' in metadata
        
        assert metadata['video_id'] == video_id
    
    def test_to_openai_function(self, tool):
        """Test OpenAI function format conversion"""
        function_def = tool.to_openai_function()
        
        assert function_def['name'] == 'youtube_download'
        assert 'description' in function_def
        assert 'parameters' in function_def
        assert function_def['parameters']['type'] == 'object'
        assert 'url' in function_def['parameters']['properties']
        assert 'url' in function_def['parameters']['required']


class TestYouTubeDownloadToolRegistry:
    """Test tool registry integration"""
    
    def test_tool_registered(self):
        """Test that YouTube download tool is registered"""
        from icpy.agent.tools import get_tool_registry
        
        registry = get_tool_registry()
        tool = registry.get('youtube_download')
        
        assert tool is not None
        assert isinstance(tool, YouTubeDownloadTool)
    
    def test_tool_in_openai_tools(self):
        """Test that tool appears in OpenAI tools list"""
        from icpy.agent.tools import get_tool_registry
        
        registry = get_tool_registry()
        all_tools = registry.all()
        
        # Find youtube_download in tools list
        youtube_tool = next(
            (t for t in all_tools if t.name == 'youtube_download'),
            None
        )
        
        assert youtube_tool is not None
        assert isinstance(youtube_tool, YouTubeDownloadTool)
        
        # Test OpenAI function format
        openai_func = youtube_tool.to_openai_function()
        assert openai_func['name'] == 'youtube_download'
        assert 'description' in openai_func
        assert 'parameters' in openai_func


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])
