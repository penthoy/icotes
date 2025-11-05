"""
Tests for WebFetchTool Phase 3-6 features:
- Phase 3: YouTube transcript extraction
- Phase 4: Caching and rate limiting
- Phase 6: Hop support
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import asyncio
from icpy.agent.tools.web_fetch_tool import WebFetchTool
from icpy.agent.tools import web_fetch_tool


class TestWebFetchToolYouTube:
    """Test Phase 3: YouTube transcript extraction"""
    
    @pytest.fixture
    def tool(self):
        # Clear cache and rate limits before each test
        web_fetch_tool._content_cache.clear()
        web_fetch_tool._rate_limit_tracker.clear()
        return WebFetchTool()
    
    def test_is_youtube_url_youtube_com(self, tool):
        """Test YouTube URL detection for youtube.com"""
        assert tool._is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
        assert tool._is_youtube_url("https://youtube.com/watch?v=dQw4w9WgXcQ") is True
        assert tool._is_youtube_url("http://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    
    def test_is_youtube_url_youtu_be(self, tool):
        """Test YouTube URL detection for youtu.be"""
        assert tool._is_youtube_url("https://youtu.be/dQw4w9WgXcQ") is True
        assert tool._is_youtube_url("http://youtu.be/dQw4w9WgXcQ") is True
    
    def test_is_youtube_url_mobile(self, tool):
        """Test YouTube URL detection for mobile"""
        assert tool._is_youtube_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ") is True
    
    def test_is_youtube_url_negative(self, tool):
        """Test non-YouTube URLs return False"""
        assert tool._is_youtube_url("https://example.com") is False
        assert tool._is_youtube_url("https://vimeo.com/123456") is False
        assert tool._is_youtube_url("https://youtube.com.fake.com/watch") is False
    
    def test_extract_youtube_video_id_watch(self, tool):
        """Test video ID extraction from watch URLs"""
        video_id = tool._extract_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"
        
        video_id = tool._extract_youtube_video_id("https://youtube.com/watch?v=abc123&t=10s")
        assert video_id == "abc123"
    
    def test_extract_youtube_video_id_short(self, tool):
        """Test video ID extraction from short URLs"""
        video_id = tool._extract_youtube_video_id("https://youtu.be/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"
        
        video_id = tool._extract_youtube_video_id("https://youtu.be/abc123?t=10s")
        assert video_id == "abc123"
    
    def test_extract_youtube_video_id_invalid(self, tool):
        """Test video ID extraction returns None for invalid URLs"""
        assert tool._extract_youtube_video_id("https://youtube.com/watch") is None
        assert tool._extract_youtube_video_id("https://example.com") is None
    
    @pytest.mark.asyncio
    async def test_fetch_youtube_transcript_success(self, tool):
        """Test successful YouTube transcript fetching"""
        mock_transcript = [
            {'text': 'Hello world', 'start': 0.0, 'duration': 2.5},
            {'text': 'This is a test', 'start': 2.5, 'duration': 3.0},
        ]
        
        mock_transcript_obj = Mock()
        mock_transcript_obj.language = 'en'
        mock_transcript_obj.is_generated = False
        
        with patch('icpy.agent.tools.web_fetch_tool.YouTubeTranscriptApi') as mock_api:
            mock_api.get_transcript.return_value = mock_transcript
            mock_api.list_transcripts.return_value.find_transcript.return_value = mock_transcript_obj
            
            success, data, error = await tool._fetch_youtube_transcript("https://youtube.com/watch?v=test123")
            
            assert success is True
            assert error is None
            assert data['video_id'] == 'test123'
            assert data['language'] == 'en'
            assert data['is_generated'] is False
            assert 'Hello world' in data['transcript']
            assert 'This is a test' in data['transcript']
            assert len(data['timestamps']) == 2
            assert data['timestamps'][0]['time'] == 0.0
            assert data['timestamps'][0]['text'] == 'Hello world'
    
    @pytest.mark.asyncio
    async def test_fetch_youtube_transcript_disabled(self, tool):
        """Test handling of disabled transcripts"""
        from youtube_transcript_api import TranscriptsDisabled
        
        with patch('icpy.agent.tools.web_fetch_tool.YouTubeTranscriptApi') as mock_api:
            mock_api.get_transcript.side_effect = TranscriptsDisabled('test123')
            
            success, data, error = await tool._fetch_youtube_transcript("https://youtube.com/watch?v=test123")
            
            assert success is False
            assert data is None
            assert "disabled" in error.lower()
    
    @pytest.mark.asyncio
    async def test_fetch_youtube_transcript_not_found(self, tool):
        """Test handling of missing transcripts"""
        from youtube_transcript_api import NoTranscriptFound
        
        with patch('icpy.agent.tools.web_fetch_tool.YouTubeTranscriptApi') as mock_api:
            mock_api.get_transcript.side_effect = NoTranscriptFound('test123', ['en'], [])
            
            success, data, error = await tool._fetch_youtube_transcript("https://youtube.com/watch?v=test123")
            
            assert success is False
            assert data is None
            assert "not found" in error.lower() or "no transcript" in error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_youtube_url(self, tool):
        """Test end-to-end execution with YouTube URL"""
        mock_transcript = [
            {'text': 'Test video', 'start': 0.0, 'duration': 2.0},
        ]
        
        mock_transcript_obj = Mock()
        mock_transcript_obj.language = 'en'
        mock_transcript_obj.is_generated = False
        
        with patch('icpy.agent.tools.web_fetch_tool.YouTubeTranscriptApi') as mock_api:
            mock_api.get_transcript.return_value = mock_transcript
            mock_api.list_transcripts.return_value.find_transcript.return_value = mock_transcript_obj
            
            result = await tool.execute(url="https://youtube.com/watch?v=test123")
            
            assert result.success is True
            assert result.data['metadata']['type'] == 'youtube_transcript'
            assert result.data['metadata']['video_id'] == 'test123'
            assert 'Test video' in result.data['content']


class TestWebFetchToolCaching:
    """Test Phase 4: Caching functionality"""
    
    @pytest.fixture
    def tool(self):
        # Clear cache and rate limits before each test
        web_fetch_tool._content_cache.clear()
        web_fetch_tool._rate_limit_tracker.clear()
        return WebFetchTool()
    
    def test_get_cache_key_same_params(self, tool):
        """Test cache key generation is consistent"""
        key1 = tool._get_cache_key("https://example.com", format="markdown", section=None)
        key2 = tool._get_cache_key("https://example.com", format="markdown", section=None)
        assert key1 == key2
    
    def test_get_cache_key_different_url(self, tool):
        """Test different URLs produce different cache keys"""
        key1 = tool._get_cache_key("https://example.com", format="markdown", section=None)
        key2 = tool._get_cache_key("https://other.com", format="markdown", section=None)
        assert key1 != key2
    
    def test_get_cache_key_different_format(self, tool):
        """Test different formats produce different cache keys"""
        key1 = tool._get_cache_key("https://example.com", format="markdown", section=None)
        key2 = tool._get_cache_key("https://example.com", format="text", section=None)
        assert key1 != key2
    
    def test_get_cache_key_different_section(self, tool):
        """Test different sections produce different cache keys"""
        key1 = tool._get_cache_key("https://example.com", format="markdown", section="intro")
        key2 = tool._get_cache_key("https://example.com", format="markdown", section="body")
        assert key1 != key2
    
    def test_cache_store_and_retrieve(self, tool):
        """Test storing and retrieving from cache"""
        cache_key = tool._get_cache_key("https://example.com", format="markdown", section=None)
        test_data = {'content': 'test content', 'url': 'https://example.com'}
        
        tool._store_in_cache(cache_key, test_data)
        retrieved = tool._get_from_cache(cache_key)
        
        assert retrieved == test_data
    
    def test_cache_expiration(self, tool):
        """Test cache entries expire after TTL"""
        cache_key = tool._get_cache_key("https://example.com", format="markdown", section=None)
        test_data = {'content': 'test content'}
        
        # Store with artificial old timestamp
        old_time = datetime.now() - timedelta(minutes=10)
        web_fetch_tool._content_cache[cache_key] = (test_data, old_time)
        
        # Should return None for expired cache
        retrieved = tool._get_from_cache(cache_key)
        assert retrieved is None
    
    def test_cache_miss(self, tool):
        """Test cache miss returns None"""
        cache_key = tool._get_cache_key("https://nonexistent.com", format="markdown", section=None)
        retrieved = tool._get_from_cache(cache_key)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_execute_uses_cache(self, tool):
        """Test that execute uses cache on second call"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><h1>Test</h1></body></html>"
        mock_response.url = "https://example.com"
        mock_response.headers = {'content-type': 'text/html'}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            # First call - should hit the network
            result1 = await tool.execute(url="https://example.com")
            assert result1.success is True
            
            # Second call - should use cache (mock should not be called again)
            mock_client.reset_mock()
            result2 = await tool.execute(url="https://example.com")
            assert result2.success is True
            assert result2.data == result1.data
            
            # Mock should not have been called for cached request
            mock_client.return_value.__aenter__.return_value.get.assert_not_called()


class TestWebFetchToolRateLimiting:
    """Test Phase 4: Rate limiting functionality"""
    
    @pytest.fixture
    def tool(self):
        # Clear cache and rate limits before each test
        web_fetch_tool._content_cache.clear()
        web_fetch_tool._rate_limit_tracker.clear()
        return WebFetchTool()
    
    def test_rate_limit_allows_initial_requests(self, tool):
        """Test rate limiting allows initial requests"""
        is_allowed, error = tool._check_rate_limit("example.com")
        assert is_allowed is True
        assert error is None
    
    def test_rate_limit_tracks_requests(self, tool):
        """Test rate limiting tracks requests per domain"""
        domain = "example.com"
        
        # Make several requests
        for _ in range(5):
            is_allowed, _ = tool._check_rate_limit(domain)
            assert is_allowed is True
        
        # Check tracker has entries
        assert domain in web_fetch_tool._rate_limit_tracker
        assert len(web_fetch_tool._rate_limit_tracker[domain]) == 5
    
    def test_rate_limit_enforces_limit(self, tool):
        """Test rate limiting enforces the limit"""
        domain = "example.com"
        
        # Make maximum allowed requests (10 per minute by default)
        for _ in range(10):
            is_allowed, _ = tool._check_rate_limit(domain)
            assert is_allowed is True
        
        # Next request should be blocked
        is_allowed, error = tool._check_rate_limit(domain)
        assert is_allowed is False
        assert error is not None
        assert "rate limit" in error.lower()
    
    def test_rate_limit_window_expiration(self, tool):
        """Test old requests are removed from window"""
        domain = "example.com"
        
        # Add old timestamps outside the window
        old_time = datetime.now().timestamp() - 120  # 2 minutes ago
        web_fetch_tool._rate_limit_tracker[domain] = [old_time] * 5
        
        # New request should be allowed as old ones expired
        is_allowed, error = tool._check_rate_limit(domain)
        assert is_allowed is True
        
        # Old timestamps should be removed
        assert len(web_fetch_tool._rate_limit_tracker[domain]) == 1
    
    def test_rate_limit_per_domain_isolation(self, tool):
        """Test rate limits are tracked per domain"""
        domain1 = "example.com"
        domain2 = "other.com"
        
        # Fill up domain1
        for _ in range(10):
            tool._check_rate_limit(domain1)
        
        # domain2 should still be allowed
        is_allowed, _ = tool._check_rate_limit(domain2)
        assert is_allowed is True
    
    @pytest.mark.asyncio
    async def test_execute_respects_rate_limit(self, tool):
        """Test execute respects rate limiting"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><h1>Test</h1></body></html>"
        mock_response.url = "https://example.com"
        mock_response.headers = {'content-type': 'text/html'}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            # Make 10 requests (should all succeed with caching disabled)
            for i in range(10):
                # Use different sections to bypass cache
                result = await tool.execute(url="https://example.com", section=f"section{i}")
                assert result.success is True
            
            # 11th request should be rate limited
            result = await tool.execute(url="https://example.com", section="section11")
            assert result.success is False
            assert "rate limit" in result.error.lower()


class TestWebFetchToolRetry:
    """Test Phase 4: Retry logic"""
    
    @pytest.fixture
    def tool(self):
        # Clear cache and rate limits before each test
        web_fetch_tool._content_cache.clear()
        web_fetch_tool._rate_limit_tracker.clear()
        return WebFetchTool()
    
    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, tool):
        """Test retry logic on timeout"""
        import httpx
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Success after retry</body></html>"
        mock_response.url = "https://example.com"
        mock_response.headers = {'content-type': 'text/html'}
        
        with patch('httpx.AsyncClient') as mock_client:
            # First call times out, second succeeds
            mock_get = AsyncMock(side_effect=[
                httpx.TimeoutException("Timeout"),
                mock_response
            ])
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            success, content, metadata = await tool._fetch_with_retry("https://example.com", timeout=10)
            
            assert success is True
            assert "Success after retry" in content
            assert mock_get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, tool):
        """Test failure after max retries"""
        import httpx
        
        with patch('httpx.AsyncClient') as mock_client:
            # All retries fail
            mock_get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.return_value.__aenter__.return_value.get = mock_get
            
            success, error, metadata = await tool._fetch_with_retry("https://example.com", timeout=10)
            
            assert success is False
            assert "timeout" in error.lower()
            # Should retry 3 times (initial + 2 retries)
            assert mock_get.call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exponential_backoff(self, tool):
        """Test exponential backoff timing"""
        import httpx
        
        with patch('httpx.AsyncClient') as mock_client, \
             patch('asyncio.sleep') as mock_sleep:
            # All retries fail
            mock_get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.return_value.__aenter__.return_value.get = mock_get
            mock_sleep.return_value = None
            
            await tool._fetch_with_retry("https://example.com", timeout=10)
            
            # Check exponential backoff: 2^0=1, 2^1=2
            assert mock_sleep.call_count == 2
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            assert sleep_calls[0] == 1  # First retry: 2^0
            assert sleep_calls[1] == 2  # Second retry: 2^1


class TestWebFetchToolHopSupport:
    """Test Phase 6: Hop support"""
    
    @pytest.fixture
    def tool(self):
        # Clear cache and rate limits before each test
        web_fetch_tool._content_cache.clear()
        web_fetch_tool._rate_limit_tracker.clear()
        return WebFetchTool()
    
    @pytest.mark.asyncio
    async def test_fetch_via_hop_local_context(self, tool):
        """Test local context uses direct fetch"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Local fetch</body></html>"
        mock_response.url = "https://example.com"
        mock_response.headers = {'content-type': 'text/html'}
        
        with patch('icpy.agent.tools.web_fetch_tool.context_router') as mock_router, \
             patch('httpx.AsyncClient') as mock_client:
            mock_router.get_active_context_id.return_value = 'local'
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            success, content, metadata = await tool._fetch_via_hop("https://example.com", timeout=10)
            
            assert success is True
            assert "Local fetch" in content
    
    @pytest.mark.asyncio
    async def test_fetch_via_hop_remote_context(self, tool):
        """Test remote context uses curl"""
        mock_terminal = AsyncMock()
        mock_terminal.execute_command.return_value = """
        <html><body>Remote fetch via curl</body></html>
        """
        
        with patch('icpy.agent.tools.web_fetch_tool.context_router') as mock_router, \
             patch('icpy.agent.tools.web_fetch_tool.RemoteTerminalManager') as mock_rtm:
            mock_router.get_active_context_id.return_value = 'remote-server'
            mock_rtm.return_value.__aenter__.return_value = mock_terminal
            
            success, content, metadata = await tool._fetch_via_hop("https://example.com", timeout=10)
            
            assert success is True
            assert "Remote fetch" in content
            mock_terminal.execute_command.assert_called_once()
            # Check curl command was used
            call_args = mock_terminal.execute_command.call_args[0][0]
            assert 'curl' in call_args
            assert 'example.com' in call_args
    
    @pytest.mark.asyncio
    async def test_fetch_via_hop_fallback_on_error(self, tool):
        """Test fallback to local fetch on hop error"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Fallback to local</body></html>"
        mock_response.url = "https://example.com"
        mock_response.headers = {'content-type': 'text/html'}
        
        mock_terminal = AsyncMock()
        mock_terminal.execute_command.side_effect = Exception("Remote error")
        
        with patch('icpy.agent.tools.web_fetch_tool.context_router') as mock_router, \
             patch('icpy.agent.tools.web_fetch_tool.RemoteTerminalManager') as mock_rtm, \
             patch('httpx.AsyncClient') as mock_client:
            mock_router.get_active_context_id.return_value = 'remote-server'
            mock_rtm.return_value.__aenter__.return_value = mock_terminal
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            success, content, metadata = await tool._fetch_via_hop("https://example.com", timeout=10)
            
            assert success is True
            assert "Fallback to local" in content
