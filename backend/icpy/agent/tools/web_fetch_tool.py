"""
Web fetch tool for agents

Phases 1-6: Complete implementation with YouTube, caching, optimization, and hop support

This tool enables AI agents to fetch and read web pages with intelligent
parsing and structuring. Includes YouTube transcript extraction, caching,
rate limiting, and remote fetching via SSH hops.
"""

import logging
import re
import time
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import asyncio
import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Try to import YouTube transcript API (Phase 3)
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False
    logger.warning("youtube-transcript-api not available, YouTube support disabled")


# Security: Blocked URL patterns to prevent SSRF attacks
BLOCKED_HOSTS = {
    'localhost', '127.0.0.1', '0.0.0.0',
    '169.254.169.254',  # AWS metadata
    '::1',  # IPv6 localhost
}

# Block private IP ranges (regex patterns)
PRIVATE_IP_PATTERNS = [
    r'^10\.',  # 10.0.0.0/8
    r'^172\.(1[6-9]|2[0-9]|3[0-1])\.',  # 172.16.0.0/12
    r'^192\.168\.',  # 192.168.0.0/16
]

# Maximum response size (10MB)
MAX_RESPONSE_SIZE = 10 * 1024 * 1024

# Default timeout
DEFAULT_TIMEOUT = 30

# Phase 4: Cache settings
CACHE_TTL = 300  # 5 minutes
_content_cache: Dict[str, Tuple[Any, datetime]] = {}

# Phase 4: Rate limiting
RATE_LIMIT_REQUESTS = 10  # requests per minute per domain
RATE_LIMIT_WINDOW = 60  # seconds
_rate_limit_tracker: Dict[str, List[float]] = {}

# Phase 4: Retry settings
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # exponential backoff: 2^retry_count seconds


class WebFetchTool(BaseTool):
    """Tool for fetching and analyzing web page content"""
    
    def __init__(self):
        super().__init__()
        self.name = "web_fetch"
        self.description = (
            "Fetch and read content from any webpage with intelligent parsing and structuring. "
            "Supports regular web pages, YouTube video transcripts, documentation sites, and articles. "
            "Returns clean markdown content with optional page structure (table of contents, sections). "
            "Features: caching, rate limiting, retry logic, and remote fetching via SSH hops. "
            "Use this to read documentation, articles, tutorials, extract YouTube transcripts, or any web content. "
            "Examples: 'Fetch https://example.com', 'Get transcript from https://youtube.com/watch?v=...', "
            "'Read the Python requests documentation', 'Extract content from this article'."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch (must be http or https)"
                },
                "format": {
                    "type": "string",
                    "enum": ["markdown", "text", "structured"],
                    "description": "Output format. 'markdown' (default) for clean markdown, 'text' for plain text, 'structured' for detailed JSON with sections"
                },
                "section": {
                    "type": "string",
                    "description": "Optional section ID to fetch specific part of the page (e.g., 'installation', 'getting-started')"
                },
                "extract_links": {
                    "type": "boolean",
                    "description": "Include extracted links in response (default: true)"
                },
                "extract_images": {
                    "type": "boolean",
                    "description": "Include image metadata in response (default: true)"
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum content length in characters (default: 50000, max: 200000)"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds (default: 30, max: 60)"
                }
            },
            "required": ["url"]
        }
    
    def _validate_url(self, url: str) -> tuple[bool, Optional[str]]:
        """
        Validate URL for security (prevent SSRF attacks).
        
        Returns:
            (is_valid, error_message)
        """
        try:
            parsed = urlparse(url)
            
            # Check protocol
            if parsed.scheme not in ['http', 'https']:
                return False, f"Invalid protocol '{parsed.scheme}'. Only http and https are allowed."
            
            # Check for blocked hosts
            hostname = parsed.hostname
            if not hostname:
                return False, "Invalid URL: no hostname found"
            
            hostname_lower = hostname.lower()
            
            # Check against blocked hosts
            if hostname_lower in BLOCKED_HOSTS:
                return False, f"Access to {hostname} is not allowed (security restriction)"
            
            # Check private IP ranges
            for pattern in PRIVATE_IP_PATTERNS:
                if re.match(pattern, hostname_lower):
                    return False, f"Access to private IP range is not allowed (security restriction)"
            
            return True, None
            
        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"
    
    async def _fetch_url(self, url: str, timeout: int) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Fetch URL content with proper headers and error handling.
        
        Returns:
            (success, content_or_error, metadata)
        """
        try:
            headers = {
                'User-Agent': 'icotes-web-fetch/1.0 (+https://icotes.com)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
                response = await client.get(url, headers=headers)
                
                # Check response size
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > MAX_RESPONSE_SIZE:
                    return False, f"Response too large: {content_length} bytes (max: {MAX_RESPONSE_SIZE})", None
                
                # Check status
                if response.status_code >= 400:
                    return False, f"HTTP {response.status_code}: {response.reason_phrase}", None
                
                content = response.text
                
                # Check actual content size
                if len(content) > MAX_RESPONSE_SIZE:
                    return False, f"Content too large: {len(content)} bytes (max: {MAX_RESPONSE_SIZE})", None
                
                # Collect metadata
                metadata = {
                    'url': str(response.url),  # Final URL after redirects
                    'status_code': response.status_code,
                    'content_type': response.headers.get('content-type', ''),
                    'content_length': len(content),
                }
                
                return True, content, metadata
                
        except httpx.TimeoutException:
            return False, f"Request timed out after {timeout} seconds", None
        except httpx.NetworkError as e:
            return False, f"Network error: {str(e)}", None
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}", exc_info=True)
            return False, f"Failed to fetch URL: {str(e)}", None
    
    def _clean_html(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        Remove unwanted elements from HTML (scripts, styles, ads, nav).
        """
        # Remove script, style, nav, footer elements
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        
        # Remove common ad and tracking elements by class/id
        ad_selectors = [
            '[class*="advertisement"]',
            '[class*="ad-"]',
            '[id*="advertisement"]',
            '[id*="ad-"]',
            '[class*="social-share"]',
            '[class*="cookie-banner"]',
            '[class*="newsletter"]',
            '[class*="popup"]',
        ]
        
        for selector in ad_selectors:
            for element in soup.select(selector):
                element.decompose()
        
        return soup
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Extract page metadata (title, description, author, etc.).
        """
        metadata = {
            'url': url,
            'title': '',
            'description': '',
            'author': '',
            'keywords': [],
        }
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text().strip()
        
        # Try h1 if no title tag
        if not metadata['title']:
            h1 = soup.find('h1')
            if h1:
                metadata['title'] = h1.get_text().strip()
        
        # Extract meta tags
        meta_description = soup.find('meta', attrs={'name': 'description'}) or \
                          soup.find('meta', attrs={'property': 'og:description'})
        if meta_description:
            metadata['description'] = meta_description.get('content', '').strip()
        
        meta_author = soup.find('meta', attrs={'name': 'author'})
        if meta_author:
            metadata['author'] = meta_author.get('content', '').strip()
        
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            keywords = meta_keywords.get('content', '').strip()
            metadata['keywords'] = [k.strip() for k in keywords.split(',') if k.strip()]
        
        return metadata
    
    def _extract_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract page structure (headings hierarchy, table of contents).
        
        Phase 2 implementation.
        """
        structure = {
            'sections': [],
            'toc': [],
        }
        
        # Find all heading elements
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        for heading in headings:
            level = int(heading.name[1])  # Extract number from h1, h2, etc.
            text = heading.get_text().strip()
            
            # Try to get or generate an ID for the section
            section_id = heading.get('id', '')
            if not section_id:
                # Generate ID from text (simplified slug)
                section_id = re.sub(r'[^\w\s-]', '', text.lower())
                section_id = re.sub(r'[-\s]+', '-', section_id).strip('-')
            
            # Get a preview of content after this heading
            preview = ''
            next_elem = heading.find_next_sibling()
            if next_elem:
                preview_text = next_elem.get_text().strip()
                preview = preview_text[:200] + '...' if len(preview_text) > 200 else preview_text
            
            section_data = {
                'heading': text,
                'level': level,
                'id': section_id,
                'summary': preview,
            }
            
            structure['sections'].append(section_data)
            structure['toc'].append(text)
        
        return structure
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """
        Extract all links with context.
        """
        links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            text = a_tag.get_text().strip()
            
            # Skip empty links
            if not href or href.startswith('#'):
                continue
            
            # Make relative URLs absolute
            if href.startswith('/'):
                parsed_base = urlparse(base_url)
                href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
            elif not href.startswith('http'):
                # Skip non-http links (mailto, javascript, etc.)
                continue
            
            links.append({
                'url': href,
                'text': text or href,
            })
        
        return links
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """
        Extract image metadata.
        """
        images = []
        
        for img_tag in soup.find_all('img', src=True):
            src = img_tag['src']
            alt = img_tag.get('alt', '').strip()
            
            # Make relative URLs absolute
            if src.startswith('/'):
                parsed_base = urlparse(base_url)
                src = f"{parsed_base.scheme}://{parsed_base.netloc}{src}"
            elif not src.startswith('http'):
                # Skip data URLs and other non-http sources
                if not src.startswith('data:'):
                    continue
            
            images.append({
                'src': src,
                'alt': alt or '(no alt text)',
            })
        
        return images
    
    def _find_section(self, soup: BeautifulSoup, section_id: str) -> Optional[BeautifulSoup]:
        """
        Find a specific section by ID and return its content.
        
        Phase 2 implementation.
        """
        # Try to find element with matching ID
        section_elem = soup.find(id=section_id)
        
        if not section_elem:
            # Try to find heading with matching text (case-insensitive)
            section_id_normalized = section_id.lower().replace('-', ' ').replace('_', ' ')
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                heading_text = heading.get_text().strip().lower()
                if section_id_normalized in heading_text or heading_text in section_id_normalized:
                    section_elem = heading
                    break
        
        if not section_elem:
            return None
        
        # Create new soup with section content
        section_soup = BeautifulSoup('<div></div>', 'html.parser')
        section_div = section_soup.div
        
        # Add the heading itself
        section_div.append(section_elem.__copy__())
        
        # Add all siblings until next heading of same or higher level
        if section_elem.name and section_elem.name.startswith('h'):
            current_level = int(section_elem.name[1])
            for sibling in section_elem.find_next_siblings():
                if sibling.name and sibling.name.startswith('h'):
                    sibling_level = int(sibling.name[1])
                    if sibling_level <= current_level:
                        break
                section_div.append(sibling.__copy__())
        
        return section_soup
    
    def _convert_to_markdown(self, soup: BeautifulSoup) -> str:
        """
        Convert cleaned HTML to markdown.
        """
        # Convert to markdown using markdownify
        markdown = md(
            str(soup),
            heading_style="ATX",  # Use # for headings
            bullets="-",  # Use - for lists
            strip=['script', 'style'],  # Ensure these are stripped
        )
        
        # Clean up excessive newlines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        return markdown.strip()
    
    def _convert_to_text(self, soup: BeautifulSoup) -> str:
        """
        Convert HTML to plain text.
        """
        # Get text with some structure preserved
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _truncate_content(self, content: str, max_length: int, structure: Optional[Dict] = None) -> tuple[str, bool, Optional[str]]:
        """
        Truncate content if it exceeds max_length.
        
        Returns:
            (truncated_content, was_truncated, truncation_reason)
        """
        if len(content) <= max_length:
            return content, False, None
        
        # Truncate at word boundary
        truncated = content[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.9:  # Only use word boundary if it's close
            truncated = truncated[:last_space]
        
        # Build helpful truncation message
        original_length = len(content)
        truncated_pct = int((max_length / original_length) * 100)
        
        reason = f"Content truncated (showing {truncated_pct}% of {original_length:,} chars)"
        
        # Add suggestions based on available structure
        suggestions = []
        if structure and structure.get('sections'):
            section_count = len(structure['sections'])
            if section_count > 1:
                suggestions.append(f"fetch specific section from {section_count} available")
        
        if original_length > max_length * 2:
            suggestions.append(f"increase max_length (current: {max_length:,}, recommend: {min(original_length, 200000):,})")
        
        if suggestions:
            reason += f". Options: {' OR '.join(suggestions)}"
        
        truncated += f'\n\n... [{reason}]'
        return truncated, True, reason
    
    # ============================================================================
    # Phase 3: YouTube and Special Content Handlers
    # ============================================================================
    
    def _is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube video"""
        parsed = urlparse(url)
        return parsed.hostname in ['www.youtube.com', 'youtube.com', 'youtu.be', 'm.youtube.com']
    
    def _extract_youtube_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        parsed = urlparse(url)
        
        if parsed.hostname in ['youtu.be']:
            # Format: https://youtu.be/VIDEO_ID
            return parsed.path.lstrip('/')
        elif parsed.hostname in ['www.youtube.com', 'youtube.com', 'm.youtube.com']:
            # Format: https://www.youtube.com/watch?v=VIDEO_ID
            query_params = parse_qs(parsed.query)
            if 'v' in query_params:
                return query_params['v'][0]
        
        return None
    
    async def _fetch_youtube_transcript(self, url: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Fetch YouTube video transcript (Phase 3).
        
        Returns:
            (success, transcript_data, error)
        """
        if not YOUTUBE_AVAILABLE:
            return False, None, "YouTube transcript API not available"
        
        video_id = self._extract_youtube_video_id(url)
        if not video_id:
            return False, None, "Could not extract YouTube video ID from URL"
        
        try:
            # Fetch transcript using the YouTube Transcript API
            api = YouTubeTranscriptApi()
            
            # Try English first, then fall back to any available language
            try:
                fetched_transcript = api.fetch(video_id, languages=['en'])
            except Exception as e:
                # Try to get any available language
                logger.debug(f"English transcript not available, trying other languages: {e}")
                fetched_transcript = api.fetch(video_id)
            
            # Build full transcript text with timestamps
            transcript_entries = list(fetched_transcript)
            full_text = '\n'.join([
                f"[{entry.start:.2f}s] {entry.text}" 
                for entry in transcript_entries
            ])
            
            # Also provide clean text without timestamps
            clean_text = '\n'.join([entry.text for entry in transcript_entries])
            
            # Build result
            result = {
                'video_id': video_id,
                'title': f"YouTube Video: {video_id}",
                'transcript': clean_text,
                'transcript_with_timestamps': full_text,
                'timestamps': [
                    {
                        'time': entry.start,
                        'duration': entry.duration,
                        'text': entry.text
                    }
                    for entry in transcript_entries
                ],
                'language': fetched_transcript.language,
                'is_generated': fetched_transcript.is_generated,
                'url': url
            }
            
            logger.info(f"Successfully fetched YouTube transcript for {video_id}: {len(transcript_entries)} entries, language: {fetched_transcript.language}")
            return True, result, None
            
        except TranscriptsDisabled:
            return False, None, "Transcripts are disabled for this video"
        except NoTranscriptFound:
            return False, None, "No transcript found for this video"
        except Exception as e:
            logger.error(f"Error fetching YouTube transcript: {e}")
            return False, None, f"Failed to fetch transcript: {str(e)}"
    
    # ============================================================================
    # Phase 4: Caching and Optimization
    # ============================================================================
    
    def _get_cache_key(self, url: str, format: str = 'markdown', section: Optional[str] = None) -> str:
        """Generate cache key from URL and parameters"""
        # Include relevant parameters in cache key
        cache_params = {
            'url': url,
            'format': format,
            'section': section,
        }
        cache_str = str(sorted(cache_params.items()))
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get content from cache if not expired"""
        if cache_key in _content_cache:
            content, cached_at = _content_cache[cache_key]
            if datetime.now() - cached_at < timedelta(seconds=CACHE_TTL):
                logger.info(f"Cache hit for key {cache_key[:8]}...")
                return content
            else:
                # Remove expired entry
                del _content_cache[cache_key]
                logger.debug(f"Cache expired for key {cache_key[:8]}...")
        return None
    
    def _store_in_cache(self, cache_key: str, content: Any) -> None:
        """Store content in cache"""
        _content_cache[cache_key] = (content, datetime.now())
        logger.debug(f"Cached content for key {cache_key[:8]}...")
    
    def _check_rate_limit(self, domain: str) -> Tuple[bool, Optional[str]]:
        """
        Check if request is within rate limit for domain.
        
        Returns:
            (is_allowed, error_message)
        """
        now = time.time()
        
        # Get or create request history for domain
        if domain not in _rate_limit_tracker:
            _rate_limit_tracker[domain] = []
        
        # Remove old requests outside the window
        _rate_limit_tracker[domain] = [
            req_time for req_time in _rate_limit_tracker[domain]
            if now - req_time < RATE_LIMIT_WINDOW
        ]
        
        # Check if limit exceeded
        if len(_rate_limit_tracker[domain]) >= RATE_LIMIT_REQUESTS:
            wait_time = RATE_LIMIT_WINDOW - (now - _rate_limit_tracker[domain][0])
            return False, f"Rate limit exceeded for {domain}. Try again in {wait_time:.0f} seconds."
        
        # Record this request
        _rate_limit_tracker[domain].append(now)
        return True, None
    
    async def _fetch_with_retry(self, url: str, timeout: int) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Fetch URL with exponential backoff retry (Phase 4).
        
        Returns:
            (success, content_or_error, metadata)
        """
        last_error = None
        
        for attempt in range(MAX_RETRIES):
            try:
                success, content_or_error, metadata = await self._fetch_url(url, timeout)
                
                if success:
                    return True, content_or_error, metadata
                
                # If it's a permanent error (4xx), don't retry
                if metadata is None or '4' in str(content_or_error):
                    return False, content_or_error, metadata
                
                last_error = content_or_error
                
                # Wait before retry with exponential backoff
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BACKOFF_BASE ** attempt
                    logger.info(f"Retry {attempt + 1}/{MAX_RETRIES} for {url} after {wait_time}s")
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                last_error = str(e)
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BACKOFF_BASE ** attempt
                    await asyncio.sleep(wait_time)
        
        return False, f"Failed after {MAX_RETRIES} attempts: {last_error}", None
    
    # ============================================================================
    # Phase 6: Hop Support
    # ============================================================================
    
    async def _fetch_via_hop(self, url: str, timeout: int) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Fetch URL through SSH hop connection using curl (Phase 6).
        
        Returns:
            (success, content_or_error, metadata)
        """
        try:
            # Get context router to check if we're hopped
            from icpy.services.context_router import get_context_router
            router = await get_context_router()
            active_context = router.get_active_context_id()
            
            if active_context == 'local':
                # Not hopped, use regular fetch
                return await self._fetch_with_retry(url, timeout)
            
            logger.info(f"Fetching {url} via hop context: {active_context}")
            
            # Use RemoteTerminalManager to execute curl on remote
            from icpy.services.remote_terminal_manager import RemoteTerminalManager
            terminal_manager = RemoteTerminalManager()
            
            # Build curl command
            curl_cmd = f"curl -s -L --max-time {timeout} -A 'icotes-web-fetch/1.0' '{url}'"
            
            # Execute on remote
            result = await terminal_manager.execute_command(active_context, curl_cmd)
            
            if result.get('exit_code') == 0:
                content = result.get('output', '')
                metadata = {
                    'url': url,
                    'status_code': 200,  # curl doesn't give us status code easily
                    'content_type': 'text/html',
                    'content_length': len(content),
                    'via_hop': active_context
                }
                return True, content, metadata
            else:
                error = result.get('error', 'Unknown error')
                return False, f"Remote fetch failed: {error}", None
                
        except Exception as e:
            logger.warning(f"Hop fetch failed, falling back to local: {e}")
            # Fall back to local fetch
            return await self._fetch_with_retry(url, timeout)
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute web fetch with given parameters.
        
        Phases 1-6: Complete implementation with all features.
        """
        # Extract parameters
        url = kwargs.get('url', '')
        format_type = kwargs.get('format', 'markdown')
        section = kwargs.get('section')
        extract_links = kwargs.get('extract_links', True)
        extract_images = kwargs.get('extract_images', True)
        max_length = min(kwargs.get('max_length', 50000), 200000)
        timeout = min(kwargs.get('timeout', DEFAULT_TIMEOUT), 60)
        
        # Validate URL
        is_valid, error = self._validate_url(url)
        if not is_valid:
            logger.warning(f"Invalid URL rejected: {url} - {error}")
            return ToolResult(
                success=False,
                error=error
            )
        
        # Phase 3: Check if this is a YouTube URL
        if self._is_youtube_url(url):
            logger.info(f"Detected YouTube URL: {url}")
            
            # Check cache first for YouTube too
            cache_key = self._get_cache_key(url, format=format_type, section=None)
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                logger.info(f"Returning cached YouTube transcript for {url}")
                if 'metadata' not in cached_result:
                    cached_result['metadata'] = {}
                cached_result['metadata']['cache_hit'] = True
                return ToolResult(success=True, data=cached_result)
            
            # Fetch transcript
            success, transcript_data, error = await self._fetch_youtube_transcript(url)
            
            if success:
                # Format transcript as response
                result_data = {
                    'url': transcript_data['url'],
                    'title': transcript_data.get('title', 'YouTube Video'),
                    'content': transcript_data['transcript'],
                    'metadata': {
                        'video_id': transcript_data['video_id'],
                        'language': transcript_data['language'],
                        'is_generated': transcript_data['is_generated'],
                        'type': 'youtube_transcript',
                        'cache_hit': False
                    },
                    'timestamps': transcript_data['timestamps'],
                    'was_truncated': False
                }
                
                # Cache the YouTube transcript
                self._store_in_cache(cache_key, result_data)
                
                return ToolResult(success=True, data=result_data)
            else:
                # Fall through to regular fetch if transcript fails
                logger.warning(f"YouTube transcript fetch failed: {error}, falling back to regular fetch")
        
        # Phase 4: Check cache
        cache_key = self._get_cache_key(url, format=format_type, section=section)
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            logger.info(f"Returning cached result for {url}")
            # Add cache indicator to metadata
            if 'metadata' not in cached_result:
                cached_result['metadata'] = {}
            cached_result['metadata']['cache_hit'] = True
            return ToolResult(success=True, data=cached_result)
        
        # Phase 4: Check rate limit
        parsed = urlparse(url)
        domain = parsed.hostname or 'unknown'
        is_allowed, rate_error = self._check_rate_limit(domain)
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for {domain}")
            return ToolResult(success=False, error=rate_error)
        
        logger.info(f"Fetching URL: {url} (format={format_type}, timeout={timeout}s)")
        
        # Phase 6: Fetch content (with hop support and retry)
        success, content_or_error, fetch_metadata = await self._fetch_via_hop(url, timeout)
        
        if not success:
            logger.warning(f"Failed to fetch {url}: {content_or_error}")
            return ToolResult(
                success=False,
                error=content_or_error
            )
        
        html_content = content_or_error
        
        # Parse HTML
        try:
            soup = BeautifulSoup(html_content, 'lxml')
        except Exception as e:
            logger.error(f"Failed to parse HTML from {url}: {e}")
            return ToolResult(
                success=False,
                error=f"Failed to parse HTML: {str(e)}"
            )
        
        # Clean HTML
        soup = self._clean_html(soup)
        
        # Extract metadata
        metadata = self._extract_metadata(soup, url)
        metadata.update(fetch_metadata or {})
        
        # Extract structure (Phase 2)
        structure = self._extract_structure(soup)
        
        # Handle section-specific request (Phase 2)
        if section:
            logger.info(f"Extracting section: {section}")
            section_soup = self._find_section(soup, section)
            if section_soup:
                soup = section_soup
            else:
                logger.warning(f"Section '{section}' not found in {url}")
                return ToolResult(
                    success=False,
                    error=f"Section '{section}' not found. Available sections: {', '.join(structure['toc'][:10])}"
                )
        
        # Convert content based on format
        if format_type == 'text':
            content = self._convert_to_text(soup)
        else:  # markdown or structured
            content = self._convert_to_markdown(soup)
        
        # Truncate if needed
        content, was_truncated, truncation_reason = self._truncate_content(content, max_length, structure)
        
        # Build result
        result_data = {
            'url': metadata['url'],
            'title': metadata['title'],
            'content': content,
            'metadata': metadata,
            'was_truncated': was_truncated,
        }
        
        # Add truncation reason if applicable
        if was_truncated and truncation_reason:
            result_data['truncation_reason'] = truncation_reason
        
        # Add structure for structured format or if explicitly requested
        if format_type == 'structured':
            result_data['structure'] = structure
        
        # Add links if requested
        if extract_links:
            result_data['links'] = self._extract_links(soup, url)
        
        # Add images if requested
        if extract_images:
            result_data['images'] = self._extract_images(soup, url)
        
        # Add cache miss indicator
        result_data['metadata']['cache_hit'] = False
        
        logger.info(f"Successfully fetched {url}: {len(content)} chars, {len(structure['sections'])} sections")
        
        # Phase 4: Store in cache
        self._store_in_cache(cache_key, result_data)
        
        return ToolResult(
            success=True,
            data=result_data
        )

