"""
Image Cache
LRU cache for storing recent images in memory for fast access.
"""
import time
import logging
from collections import OrderedDict
from typing import Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CachedImage:
    """Cached image data with metadata"""
    image_id: str
    base64_data: str
    mime_type: str
    size_bytes: int
    cached_at: float
    access_count: int = 0


class ImageCache:
    """
    LRU cache for storing base64 image data in memory.
    
    Used for:
    - Fast access to recently generated images
    - Immediate display within same session
    - Image editing without disk I/O
    """
    
    def __init__(
        self,
        max_images: int = 5,
        max_size_mb: float = 10.0,
        ttl_seconds: float = 1800  # 30 minutes
    ):
        """
        Initialize cache.
        
        Args:
            max_images: Maximum number of images to cache
            max_size_mb: Maximum total cache size in MB
            ttl_seconds: Time-to-live for cached entries
        """
        self.max_images = max_images
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.ttl_seconds = ttl_seconds
        
        self._cache: OrderedDict[str, CachedImage] = OrderedDict()
        self._total_size = 0
        
        # Only log on first initialization (reduce log spam)
        global _cache_already_logged_init
        if not _cache_already_logged_init:
            logger.info(
                f"ImageCache initialized: max_images={max_images}, "
                f"max_size={max_size_mb}MB, ttl={ttl_seconds}s"
            )
        else:
            logger.debug(
                f"ImageCache created: max_images={max_images}, "
                f"max_size={max_size_mb}MB, ttl={ttl_seconds}s"
            )
    
    def put(
        self,
        image_id: str,
        base64_data: str,
        mime_type: str = "image/png"
    ) -> None:
        """
        Add image to cache.
        
        Args:
            image_id: Unique image identifier
            base64_data: Base64 encoded image data
            mime_type: MIME type of image
        """
        # Calculate size
        size_bytes = len(base64_data.encode('utf-8'))
        
        # Remove existing entry if present
        if image_id in self._cache:
            self._evict(image_id)
        
        # Check if we need to make space
        while (
            len(self._cache) >= self.max_images or
            self._total_size + size_bytes > self.max_size_bytes
        ):
            if not self._cache:
                logger.warning(
                    f"Single image ({size_bytes / 1024 / 1024:.2f}MB) "
                    f"exceeds cache limit ({self.max_size_bytes / 1024 / 1024:.2f}MB)"
                )
                break
            self._evict_oldest()
        
        # Add to cache
        cached = CachedImage(
            image_id=image_id,
            base64_data=base64_data,
            mime_type=mime_type,
            size_bytes=size_bytes,
            cached_at=time.time()
        )
        
        self._cache[image_id] = cached
        self._total_size += size_bytes
        
        logger.debug(
            f"Cached image {image_id}: {size_bytes / 1024:.2f}KB "
            f"(total: {self._total_size / 1024 / 1024:.2f}MB, count: {len(self._cache)})"
        )
    
    def get(self, image_id: str) -> Optional[str]:
        """
        Get image from cache.
        
        Args:
            image_id: Image identifier
        
        Returns:
            Base64 data if found and not expired, None otherwise
        """
        if image_id not in self._cache:
            return None
        
        cached = self._cache[image_id]
        
        # Check TTL
        age = time.time() - cached.cached_at
        if age > self.ttl_seconds:
            logger.debug(f"Cache entry expired: {image_id} (age: {age:.1f}s)")
            self._evict(image_id)
            return None
        
        # Move to end (most recently used)
        self._cache.move_to_end(image_id)
        cached.access_count += 1
        
        logger.debug(f"Cache hit: {image_id} (accesses: {cached.access_count})")
        return cached.base64_data
    
    def has(self, image_id: str) -> bool:
        """
        Check if image is in cache (without retrieving).
        
        Args:
            image_id: Image identifier
        
        Returns:
            True if in cache and not expired
        """
        if image_id not in self._cache:
            return False
        
        cached = self._cache[image_id]
        age = time.time() - cached.cached_at
        
        if age > self.ttl_seconds:
            self._evict(image_id)
            return False
        
        return True
    
    def _evict(self, image_id: str) -> None:
        """Remove specific image from cache"""
        if image_id in self._cache:
            cached = self._cache.pop(image_id)
            self._total_size -= cached.size_bytes
            logger.debug(f"Evicted: {image_id}")
    
    def _evict_oldest(self) -> None:
        """Remove oldest (least recently used) image from cache"""
        if not self._cache:
            return
        
        oldest_id = next(iter(self._cache))
        self._evict(oldest_id)
    
    def clear(self) -> None:
        """Clear all cached images"""
        count = len(self._cache)
        self._cache.clear()
        self._total_size = 0
        logger.info(f"Cache cleared: {count} images removed")
    
    def get_stats(self) -> Dict:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats
        """
        return {
            'count': len(self._cache),
            'total_size_bytes': self._total_size,
            'total_size_mb': self._total_size / 1024 / 1024,
            'max_images': self.max_images,
            'max_size_mb': self.max_size_bytes / 1024 / 1024,
            'ttl_seconds': self.ttl_seconds
        }
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries.
        
        Returns:
            Number of entries removed
        """
        now = time.time()
        expired = []
        
        for image_id, cached in self._cache.items():
            age = now - cached.cached_at
            if age > self.ttl_seconds:
                expired.append(image_id)
        
        for image_id in expired:
            self._evict(image_id)
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired cache entries")
        
        return len(expired)


# Global cache instance
_global_cache: Optional[ImageCache] = None
_cache_already_logged_init = False


def get_image_cache() -> ImageCache:
    """Get global image cache instance"""
    global _global_cache, _cache_already_logged_init
    if _global_cache is None:
        _global_cache = ImageCache()
        _cache_already_logged_init = True
    return _global_cache
