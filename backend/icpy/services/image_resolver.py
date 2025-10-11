"""
Image Resolver
Resolves image paths even after files are renamed or moved.
"""
import logging
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass

from .image_reference_service import ImageReference
from ..utils.thumbnail_generator import calculate_checksum

logger = logging.getLogger(__name__)


class ImageResolver:
    """
    Resolves image file paths using multiple strategies.
    
    Resolution strategy order:
    1. Try current_filename at relative_path (fastest)
    2. Search workspace for files containing image_id
    3. Search workspace for files matching checksum
    4. Fallback to thumbnail_path
    5. Return None if not found
    """
    
    def __init__(self, workspace_path: str):
        """
        Initialize resolver.
        
        Args:
            workspace_path: Path to workspace directory
        """
        self.workspace_path = Path(workspace_path)
        self._resolution_cache: Dict[str, str] = {}
        
        logger.info(f"ImageResolver initialized: workspace={workspace_path}")
    
    def resolve_image_path(
        self,
        reference: ImageReference,
        update_reference: bool = False
    ) -> Optional[str]:
        """
        Resolve the actual path to an image file.
        
        Args:
            reference: ImageReference to resolve
            update_reference: If True, update reference.current_filename
        
        Returns:
            Resolved path or None if not found
        """
        # Check cache first
        if reference.image_id in self._resolution_cache:
            cached_path = self._resolution_cache[reference.image_id]
            if Path(cached_path).exists():
                logger.debug(f"Cache hit for {reference.image_id}")
                return cached_path
        
        # Strategy 1: Try current filename at relative path
        current_path = self.workspace_path / reference.relative_path
        if current_path.exists():
            logger.debug(f"Resolved via current path: {current_path}")
            self._cache_resolution(reference.image_id, str(current_path))
            return str(current_path)
        
        # Strategy 2: Try absolute path (in case workspace moved)
        if Path(reference.absolute_path).exists():
            logger.debug(f"Resolved via absolute path: {reference.absolute_path}")
            self._cache_resolution(reference.image_id, reference.absolute_path)
            return reference.absolute_path
        
        # Strategy 3: Search for files containing image_id in filename
        found_by_id = self._search_by_image_id(reference.image_id)
        if found_by_id:
            logger.info(f"Resolved by image_id search: {found_by_id}")
            self._cache_resolution(reference.image_id, str(found_by_id))
            if update_reference:
                reference.current_filename = found_by_id.name
            return str(found_by_id)
        
        # Strategy 4: Search by checksum (if available)
        if reference.checksum:
            found_by_checksum = self._search_by_checksum(reference.checksum)
            if found_by_checksum:
                logger.info(f"Resolved by checksum: {found_by_checksum}")
                self._cache_resolution(reference.image_id, str(found_by_checksum))
                if update_reference:
                    reference.current_filename = found_by_checksum.name
                return str(found_by_checksum)
        
        # Strategy 5: Fallback to thumbnail
        thumbnail_path = Path(reference.thumbnail_path)
        if thumbnail_path.exists():
            logger.warning(f"Original image not found, using thumbnail: {thumbnail_path}")
            return str(thumbnail_path)
        
        # Not found
        logger.error(f"Failed to resolve image: {reference.image_id}")
        return None
    
    def _search_by_image_id(self, image_id: str) -> Optional[Path]:
        """
        Search workspace for files containing image_id in filename.
        
        Args:
            image_id: Image ID to search for
        
        Returns:
            Path if found, None otherwise
        """
        try:
            # Common image extensions
            extensions = ['*.png', '*.jpg', '*.jpeg', '*.webp', '*.gif']
            
            for ext in extensions:
                for file_path in self.workspace_path.rglob(ext):
                    # Skip thumbnails directory
                    if '.icotes/thumbnails' in str(file_path):
                        continue
                    
                    if image_id in file_path.name:
                        return file_path
            
            return None
        except Exception as e:
            logger.warning(f"Error searching by image_id: {e}")
            return None
    
    def _search_by_checksum(self, target_checksum: str) -> Optional[Path]:
        """
        Search workspace for files matching checksum.
        This is slow but reliable for completely renamed files.
        
        Args:
            target_checksum: SHA256 checksum to match
        
        Returns:
            Path if found, None otherwise
        """
        try:
            # Common image extensions
            extensions = ['*.png', '*.jpg', '*.jpeg', '*.webp', '*.gif']
            
            # Limit search to reasonable number of files
            max_files_to_check = 100
            files_checked = 0
            
            for ext in extensions:
                for file_path in self.workspace_path.rglob(ext):
                    # Skip thumbnails directory
                    if '.icotes/thumbnails' in str(file_path):
                        continue
                    
                    files_checked += 1
                    if files_checked > max_files_to_check:
                        logger.warning(f"Checksum search limit reached ({max_files_to_check} files)")
                        return None
                    
                    try:
                        file_checksum = calculate_checksum(str(file_path))
                        if file_checksum == target_checksum:
                            logger.info(f"Found match by checksum after checking {files_checked} files")
                            return file_path
                    except Exception as e:
                        logger.debug(f"Error calculating checksum for {file_path}: {e}")
                        continue
            
            return None
        except Exception as e:
            logger.warning(f"Error searching by checksum: {e}")
            return None
    
    def _cache_resolution(self, image_id: str, path: str):
        """Cache a successful resolution"""
        self._resolution_cache[image_id] = path
        
        # Limit cache size (FIFO eviction - Python 3.7+ dicts maintain insertion order)
        if len(self._resolution_cache) > 100:
            # Remove oldest entry by insertion order
            self._resolution_cache.pop(next(iter(self._resolution_cache)))
    
    def clear_cache(self):
        """Clear the resolution cache"""
        self._resolution_cache.clear()


def resolve_image_path(
    reference: ImageReference,
    workspace_path: str,
    update_reference: bool = False
) -> Optional[str]:
    """
    Convenience function to resolve an image path.
    
    Args:
        reference: ImageReference to resolve
        workspace_path: Path to workspace
        update_reference: If True, update reference.current_filename
    
    Returns:
        Resolved path or None
    """
    resolver = ImageResolver(workspace_path)
    return resolver.resolve_image_path(reference, update_reference)
