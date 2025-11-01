"""
Tests for WebFetchTool (Phases 1-2)

Tests cover:
- Phase 1: Basic fetching, markdown conversion, error handling, metadata extraction
- Phase 2: Structure extraction, TOC generation, section-specific fetching
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import httpx
from bs4 import BeautifulSoup

from icpy.agent.tools.web_fetch_tool import WebFetchTool
from icpy.agent.tools.base_tool import ToolResult


# Sample HTML for testing
SIMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <meta name="description" content="This is a test page">
    <meta name="author" content="Test Author">
</head>
<body>
    <h1>Main Title</h1>
    <p>This is a simple paragraph with some content.</p>
    <p>Another paragraph here.</p>
</body>
</html>
"""

COMPLEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Complex Page</title>
</head>
<body>
    <nav>
        <a href="/home">Home</a>
        <a href="/about">About</a>
    </nav>
    <header>Header content</header>
    <main>
        <h1>Main Content</h1>
        <p>Actual content here.</p>
        <aside>Sidebar content</aside>
        <div class="advertisement">Ad content</div>
    </main>
    <footer>Footer content</footer>
    <script>console.log('test');</script>
    <style>.test { color: red; }</style>
</body>
</html>
"""

STRUCTURED_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Documentation</title>
</head>
<body>
    <h1>Main Title</h1>
    <p>Introduction paragraph.</p>
    
    <h2 id="installation">Installation</h2>
    <p>Install with pip install example.</p>
    <pre><code>pip install example</code></pre>
    
    <h2 id="usage">Usage</h2>
    <p>Here's how to use it.</p>
    
    <h3>Basic Usage</h3>
    <p>Basic usage example.</p>
    
    <h3>Advanced Usage</h3>
    <p>Advanced usage example.</p>
    
    <h2 id="api">API Reference</h2>
    <p>API documentation.</p>
</body>
</html>
"""

HTML_WITH_LINKS_IMAGES = """
<!DOCTYPE html>
<html>
<head><title>Media Page</title></head>
<body>
    <h1>Test Page</h1>
    <p>Check out <a href="https://example.com/page1">this link</a>.</p>
    <p>Also see <a href="/relative/path">this page</a>.</p>
    <img src="https://example.com/image1.png" alt="Image 1">
    <img src="/relative/image.jpg" alt="Relative Image">
    <a href="#anchor">Anchor link</a>
    <a href="mailto:test@example.com">Email</a>
</body>
</html>
"""


class TestWebFetchToolValidation:
    """Test URL validation and security"""
    
    @pytest.fixture
    def tool(self):
        return WebFetchTool()
    
    def test_valid_http_url(self, tool):
        """Test valid HTTP URL passes validation"""
        is_valid, error = tool._validate_url("http://example.com")
        assert is_valid is True
        assert error is None
    
    def test_valid_https_url(self, tool):
        """Test valid HTTPS URL passes validation"""
        is_valid, error = tool._validate_url("https://example.com/path?query=1")
        assert is_valid is True
        assert error is None
    
    def test_invalid_protocol(self, tool):
        """Test invalid protocol is rejected"""
        is_valid, error = tool._validate_url("ftp://example.com")
        assert is_valid is False
        assert "protocol" in error.lower()
    
    def test_localhost_blocked(self, tool):
        """Test localhost is blocked for security"""
        is_valid, error = tool._validate_url("http://localhost/api")
        assert is_valid is False
        assert "not allowed" in error.lower()
    
    def test_127_0_0_1_blocked(self, tool):
        """Test 127.0.0.1 is blocked"""
        is_valid, error = tool._validate_url("http://127.0.0.1:8000")
        assert is_valid is False
        assert "not allowed" in error.lower()
    
    def test_private_ip_10_blocked(self, tool):
        """Test 10.x.x.x private IPs are blocked"""
        is_valid, error = tool._validate_url("http://10.0.0.1/")
        assert is_valid is False
        assert "private ip" in error.lower()
    
    def test_private_ip_192_168_blocked(self, tool):
        """Test 192.168.x.x private IPs are blocked"""
        is_valid, error = tool._validate_url("http://192.168.1.1/")
        assert is_valid is False
        assert "private ip" in error.lower()
    
    def test_private_ip_172_16_blocked(self, tool):
        """Test 172.16-31.x.x private IPs are blocked"""
        is_valid, error = tool._validate_url("http://172.16.0.1/")
        assert is_valid is False
        assert "private ip" in error.lower()


class TestWebFetchToolFetching:
    """Test HTTP fetching functionality"""
    
    @pytest.fixture
    def tool(self):
        return WebFetchTool()
    
    @pytest.mark.asyncio
    async def test_successful_fetch(self, tool):
        """Test successful page fetch"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.reason_phrase = "OK"
        mock_response.text = SIMPLE_HTML
        mock_response.url = "https://example.com"
        mock_response.headers = {
            'content-type': 'text/html',
            'content-length': str(len(SIMPLE_HTML))
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            success, content, metadata = await tool._fetch_url("https://example.com", 30)
            
            assert success is True
            assert content == SIMPLE_HTML
            assert metadata['status_code'] == 200
            assert metadata['url'] == "https://example.com"
    
    @pytest.mark.asyncio
    async def test_404_error(self, tool):
        """Test 404 error handling"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.reason_phrase = "Not Found"
        mock_response.headers = {}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            success, error, metadata = await tool._fetch_url("https://example.com/notfound", 30)
            
            assert success is False
            assert "404" in error
    
    @pytest.mark.asyncio
    async def test_timeout_error(self, tool):
        """Test timeout handling"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Request timed out")
            )
            
            success, error, metadata = await tool._fetch_url("https://example.com", 5)
            
            assert success is False
            assert "timed out" in error.lower()
    
    @pytest.mark.asyncio
    async def test_network_error(self, tool):
        """Test network error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.NetworkError("Connection refused")
            )
            
            success, error, metadata = await tool._fetch_url("https://example.com", 30)
            
            assert success is False
            assert "network error" in error.lower()
    
    @pytest.mark.asyncio
    async def test_content_too_large(self, tool):
        """Test rejection of oversized content"""
        mock_response = Mock()
        mock_response.headers = {'content-length': str(20 * 1024 * 1024)}  # 20MB
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            success, error, metadata = await tool._fetch_url("https://example.com", 30)
            
            assert success is False
            assert "too large" in error.lower()


class TestWebFetchToolContentProcessing:
    """Test HTML processing and conversion"""
    
    @pytest.fixture
    def tool(self):
        return WebFetchTool()
    
    def test_clean_html_removes_scripts(self, tool):
        """Test script tags are removed"""
        soup = BeautifulSoup(COMPLEX_HTML, 'lxml')
        cleaned = tool._clean_html(soup)
        
        assert cleaned.find('script') is None
        assert cleaned.find('style') is None
    
    def test_clean_html_removes_nav(self, tool):
        """Test navigation elements are removed"""
        soup = BeautifulSoup(COMPLEX_HTML, 'lxml')
        cleaned = tool._clean_html(soup)
        
        assert cleaned.find('nav') is None
        assert cleaned.find('header') is None
        assert cleaned.find('footer') is None
        assert cleaned.find('aside') is None
    
    def test_clean_html_removes_ads(self, tool):
        """Test ad elements are removed"""
        soup = BeautifulSoup(COMPLEX_HTML, 'lxml')
        cleaned = tool._clean_html(soup)
        
        assert cleaned.find('div', class_='advertisement') is None
    
    def test_extract_metadata_title(self, tool):
        """Test title extraction"""
        soup = BeautifulSoup(SIMPLE_HTML, 'lxml')
        metadata = tool._extract_metadata(soup, "https://example.com")
        
        assert metadata['title'] == "Test Page"
        assert metadata['description'] == "This is a test page"
        assert metadata['author'] == "Test Author"
    
    def test_extract_metadata_fallback_h1(self, tool):
        """Test title falls back to h1 if no title tag"""
        html = "<html><body><h1>Heading Title</h1></body></html>"
        soup = BeautifulSoup(html, 'lxml')
        metadata = tool._extract_metadata(soup, "https://example.com")
        
        assert metadata['title'] == "Heading Title"
    
    def test_convert_to_markdown(self, tool):
        """Test HTML to markdown conversion"""
        soup = BeautifulSoup(SIMPLE_HTML, 'lxml')
        cleaned = tool._clean_html(soup)
        markdown = tool._convert_to_markdown(cleaned)
        
        assert "# Main Title" in markdown
        assert "This is a simple paragraph" in markdown
        assert "Another paragraph" in markdown
    
    def test_convert_to_text(self, tool):
        """Test HTML to plain text conversion"""
        soup = BeautifulSoup(SIMPLE_HTML, 'lxml')
        cleaned = tool._clean_html(soup)
        text = tool._convert_to_text(cleaned)
        
        assert "Main Title" in text
        assert "This is a simple paragraph" in text
        # Should not have markdown syntax
        assert "#" not in text
    
    def test_truncate_content_under_limit(self, tool):
        """Test content under limit is not truncated"""
        content = "Short content"
        truncated, was_truncated, reason = tool._truncate_content(content, 1000)
        
        assert truncated == content
        assert was_truncated is False
        assert reason is None
    
    def test_truncate_content_over_limit(self, tool):
        """Test content over limit is truncated"""
        content = "word " * 1000
        truncated, was_truncated, reason = tool._truncate_content(content, 100)
        
        assert len(truncated) <= 250  # Increased margin for detailed truncation message
        assert was_truncated is True
        assert "truncated" in truncated.lower()
        assert reason is not None
        assert "%" in reason  # Should show percentage


class TestWebFetchToolStructureExtraction:
    """Test Phase 2: Structure extraction features"""
    
    @pytest.fixture
    def tool(self):
        return WebFetchTool()
    
    def test_extract_structure_headings(self, tool):
        """Test heading hierarchy extraction"""
        soup = BeautifulSoup(STRUCTURED_HTML, 'lxml')
        structure = tool._extract_structure(soup)
        
        assert len(structure['sections']) == 6  # 1 h1, 3 h2, 2 h3
        assert structure['sections'][0]['heading'] == "Main Title"
        assert structure['sections'][0]['level'] == 1
        assert structure['sections'][1]['heading'] == "Installation"
        assert structure['sections'][1]['level'] == 2
    
    def test_extract_structure_ids(self, tool):
        """Test section ID extraction"""
        soup = BeautifulSoup(STRUCTURED_HTML, 'lxml')
        structure = tool._extract_structure(soup)
        
        # Find the Installation section
        installation = [s for s in structure['sections'] if s['heading'] == 'Installation'][0]
        assert installation['id'] == 'installation'
        
        # Find the Usage section
        usage = [s for s in structure['sections'] if s['heading'] == 'Usage'][0]
        assert usage['id'] == 'usage'
    
    def test_extract_structure_toc(self, tool):
        """Test table of contents generation"""
        soup = BeautifulSoup(STRUCTURED_HTML, 'lxml')
        structure = tool._extract_structure(soup)
        
        assert "Main Title" in structure['toc']
        assert "Installation" in structure['toc']
        assert "Usage" in structure['toc']
        assert "API Reference" in structure['toc']
    
    def test_extract_structure_summary(self, tool):
        """Test section summary extraction"""
        soup = BeautifulSoup(STRUCTURED_HTML, 'lxml')
        structure = tool._extract_structure(soup)
        
        installation = [s for s in structure['sections'] if s['heading'] == 'Installation'][0]
        assert 'Install with pip' in installation['summary']
    
    def test_find_section_by_id(self, tool):
        """Test finding section by ID"""
        soup = BeautifulSoup(STRUCTURED_HTML, 'lxml')
        section_soup = tool._find_section(soup, 'installation')
        
        assert section_soup is not None
        text = section_soup.get_text()
        assert "Installation" in text
        assert "pip install" in text
    
    def test_find_section_by_text(self, tool):
        """Test finding section by heading text"""
        soup = BeautifulSoup(STRUCTURED_HTML, 'lxml')
        section_soup = tool._find_section(soup, 'usage')
        
        assert section_soup is not None
        text = section_soup.get_text()
        assert "Usage" in text
        assert "how to use" in text.lower()
    
    def test_find_section_stops_at_next_heading(self, tool):
        """Test section extraction stops at next same-level heading"""
        soup = BeautifulSoup(STRUCTURED_HTML, 'lxml')
        section_soup = tool._find_section(soup, 'usage')
        
        text = section_soup.get_text()
        # Should include Usage and its subsections
        assert "Basic Usage" in text
        assert "Advanced Usage" in text
        # Should NOT include API Reference (next h2)
        assert "API Reference" not in text
    
    def test_find_nonexistent_section(self, tool):
        """Test finding non-existent section returns None"""
        soup = BeautifulSoup(STRUCTURED_HTML, 'lxml')
        section_soup = tool._find_section(soup, 'nonexistent-section')
        
        assert section_soup is None


class TestWebFetchToolLinksAndImages:
    """Test link and image extraction"""
    
    @pytest.fixture
    def tool(self):
        return WebFetchTool()
    
    def test_extract_links_absolute(self, tool):
        """Test absolute link extraction"""
        soup = BeautifulSoup(HTML_WITH_LINKS_IMAGES, 'lxml')
        links = tool._extract_links(soup, "https://example.com")
        
        absolute_links = [l for l in links if l['url'] == 'https://example.com/page1']
        assert len(absolute_links) == 1
        assert absolute_links[0]['text'] == 'this link'
    
    def test_extract_links_relative(self, tool):
        """Test relative links are made absolute"""
        soup = BeautifulSoup(HTML_WITH_LINKS_IMAGES, 'lxml')
        links = tool._extract_links(soup, "https://example.com")
        
        relative_links = [l for l in links if 'relative/path' in l['url']]
        assert len(relative_links) == 1
        assert relative_links[0]['url'] == 'https://example.com/relative/path'
    
    def test_extract_links_skips_anchors(self, tool):
        """Test anchor links are skipped"""
        soup = BeautifulSoup(HTML_WITH_LINKS_IMAGES, 'lxml')
        links = tool._extract_links(soup, "https://example.com")
        
        anchor_links = [l for l in links if l['url'].startswith('#')]
        assert len(anchor_links) == 0
    
    def test_extract_images_absolute(self, tool):
        """Test absolute image extraction"""
        soup = BeautifulSoup(HTML_WITH_LINKS_IMAGES, 'lxml')
        images = tool._extract_images(soup, "https://example.com")
        
        absolute_images = [i for i in images if i['src'] == 'https://example.com/image1.png']
        assert len(absolute_images) == 1
        assert absolute_images[0]['alt'] == 'Image 1'
    
    def test_extract_images_relative(self, tool):
        """Test relative images are made absolute"""
        soup = BeautifulSoup(HTML_WITH_LINKS_IMAGES, 'lxml')
        images = tool._extract_images(soup, "https://example.com")
        
        relative_images = [i for i in images if 'relative/image' in i['src']]
        assert len(relative_images) == 1
        assert relative_images[0]['src'] == 'https://example.com/relative/image.jpg'


class TestWebFetchToolIntegration:
    """Test end-to-end tool execution"""
    
    @pytest.fixture
    def tool(self):
        # Import the cache and rate limit dicts from the module
        from icpy.agent.tools import web_fetch_tool
        # Clear cache and rate limits before each test
        web_fetch_tool._content_cache.clear()
        web_fetch_tool._rate_limit_tracker.clear()
        return WebFetchTool()
    
    @pytest.mark.asyncio
    async def test_execute_simple_page(self, tool):
        """Test fetching a simple page end-to-end"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.reason_phrase = "OK"
        mock_response.text = SIMPLE_HTML
        mock_response.url = "https://example.com"
        mock_response.headers = {'content-type': 'text/html'}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await tool.execute(url="https://example.com")
            
            assert result.success is True
            assert result.data['title'] == "Test Page"
            assert "Main Title" in result.data['content']
            assert result.data['metadata']['url'] == "https://example.com"
    
    @pytest.mark.asyncio
    async def test_execute_invalid_url(self, tool):
        """Test execution with invalid URL"""
        result = await tool.execute(url="http://localhost/test")
        
        assert result.success is False
        assert "not allowed" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_markdown_format(self, tool):
        """Test markdown format output"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = SIMPLE_HTML
        mock_response.url = "https://example.com"
        mock_response.headers = {'content-type': 'text/html'}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await tool.execute(url="https://example.com", format="markdown")
            
            assert result.success is True
            assert "#" in result.data['content']  # Markdown heading syntax
    
    @pytest.mark.asyncio
    async def test_execute_text_format(self, tool):
        """Test plain text format output"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = SIMPLE_HTML
        mock_response.url = "https://example.com"
        mock_response.headers = {'content-type': 'text/html'}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await tool.execute(url="https://example.com", format="text")
            
            assert result.success is True
            assert "#" not in result.data['content']  # No markdown syntax
    
    @pytest.mark.asyncio
    async def test_execute_structured_format(self, tool):
        """Test structured format includes structure data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = STRUCTURED_HTML
        mock_response.url = "https://example.com/docs"
        mock_response.headers = {'content-type': 'text/html'}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await tool.execute(url="https://example.com/docs", format="structured")
            
            assert result.success is True
            assert 'structure' in result.data
            assert len(result.data['structure']['sections']) > 0
            assert len(result.data['structure']['toc']) > 0
    
    @pytest.mark.asyncio
    async def test_execute_specific_section(self, tool):
        """Test fetching specific section"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = STRUCTURED_HTML
        mock_response.url = "https://example.com/docs"
        mock_response.headers = {'content-type': 'text/html'}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await tool.execute(url="https://example.com/docs", section="installation")
            
            assert result.success is True
            assert "Installation" in result.data['content']
            assert "pip install" in result.data['content']
            # Should not include other sections
            assert "API Reference" not in result.data['content']
    
    @pytest.mark.asyncio
    async def test_execute_nonexistent_section(self, tool):
        """Test error when section not found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = STRUCTURED_HTML
        mock_response.url = "https://example.com/docs"
        mock_response.headers = {'content-type': 'text/html'}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await tool.execute(url="https://example.com/docs", section="nonexistent")
            
            assert result.success is False
            assert "not found" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_with_links_and_images(self, tool):
        """Test extraction of links and images"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = HTML_WITH_LINKS_IMAGES
        mock_response.url = "https://example.com"
        mock_response.headers = {'content-type': 'text/html'}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await tool.execute(
                url="https://example.com",
                extract_links=True,
                extract_images=True
            )
            
            assert result.success is True
            assert 'links' in result.data
            assert len(result.data['links']) > 0
            assert 'images' in result.data
            assert len(result.data['images']) > 0
    
    @pytest.mark.asyncio
    async def test_execute_max_length(self, tool):
        """Test content truncation with max_length"""
        long_html = f"""
        <html><body>
        <h1>Title</h1>
        <p>{'Long content ' * 1000}</p>
        </body></html>
        """
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = long_html
        mock_response.url = "https://example.com"
        mock_response.headers = {'content-type': 'text/html'}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await tool.execute(url="https://example.com", max_length=500)
            
            assert result.success is True
            assert len(result.data['content']) <= 650  # Increased margin for detailed message
            assert result.data['was_truncated'] is True
            assert 'truncation_reason' in result.data
