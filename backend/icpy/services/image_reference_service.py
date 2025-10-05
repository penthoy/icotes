"""
Image Reference Service
Manages image references to avoid storing large base64 data in chat history.
"""
import uuid
import time
import base64
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional, Any

from ..utils.thumbnail_generator import generate_thumbnail, calculate_checksum

logger = logging.getLogger(__name__)


@dataclass
class ImageReference:
    """
    Reference to an image file with metadata.
    Used instead of storing full base64 data in JSONL.
    """
    image_id: str  # Stable UUID identifier
    original_filename: str  # Original filename when created
    current_filename: str  # Current filename (updates if renamed)
    relative_path: str  # Path relative to workspace
    absolute_path: str  # Full system path
    mime_type: str  # MIME type (e.g., "image/png")
    size_bytes: int  # Original file size
    thumbnail_base64: str  # Small base64 thumbnail for immediate display
    thumbnail_path: str  # Path to thumbnail file on disk
    prompt: str  # Original generation prompt
    model: str  # Model used to generate
    timestamp: float  # Creation timestamp
    checksum: str  # SHA256 checksum for integrity/search
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImageReference':
        """Create from dictionary"""
        return cls(**data)


class ImageReferenceService:
    """Service for creating and managing image references"""
    
    def __init__(self, workspace_path: str):
        """
        Initialize service.
        
        Args:
            workspace_path: Path to workspace directory
        """
        self.workspace_path = str(workspace_path)  # Keep as string for consistency
        self._workspace_path_obj = Path(workspace_path)
        self.thumbnails_dir = self._workspace_path_obj / ".icotes" / "thumbnails"
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ImageReferenceService initialized: workspace={workspace_path}")
    
    async def create_reference(
        self,
        image_data: str,
        filename: str,
        prompt: str,
        model: str,
        mime_type: str = "image/png"
    ) -> ImageReference:
        """
        Create an ImageReference from image data.
        
        Args:
            image_data: Base64 encoded image data
            filename: Filename of the image
            prompt: Generation prompt
            model: Model used
            mime_type: MIME type of image
        
        Returns:
            ImageReference object
        """
        try:
            # Generate unique image ID
            image_id = str(uuid.uuid4())
            
            # Determine paths
            relative_path = filename
            absolute_path = self._workspace_path_obj / filename
            
            # Check if file exists
            if not absolute_path.exists():
                # File might have been saved with different name
                # Try to find it or use provided path
                logger.warning(f"Image file not found at {absolute_path}")
            
            # Calculate file size
            size_bytes = absolute_path.stat().st_size if absolute_path.exists() else 0
            
            # Generate checksum
            checksum = calculate_checksum(str(absolute_path)) if absolute_path.exists() else ""
            
            # Generate thumbnail
            thumbnail_result = generate_thumbnail(
                str(absolute_path),
                str(self.thumbnails_dir),
                image_id=image_id
            )
            
            # Create reference
            ref = ImageReference(
                image_id=image_id,
                original_filename=filename,
                current_filename=filename,
                relative_path=relative_path,
                absolute_path=str(absolute_path),
                mime_type=mime_type,
                size_bytes=size_bytes,
                thumbnail_base64=thumbnail_result['base64'],
                thumbnail_path=thumbnail_result['path'],
                prompt=prompt,
                model=model,
                timestamp=time.time(),
                checksum=checksum
            )
            
            logger.info(f"Created ImageReference: {image_id} for {filename}")
            return ref
            
        except Exception as e:
            logger.error(f"Failed to create image reference: {e}")
            raise


async def create_image_reference(
    image_data: str,
    filename: str,
    workspace_path: str,
    prompt: str,
    model: str,
    mime_type: str = "image/png"
) -> ImageReference:
    """
    Convenience function to create an image reference.
    
    Args:
        image_data: Base64 encoded image data
        filename: Filename of the image
        workspace_path: Path to workspace
        prompt: Generation prompt
        model: Model used
        mime_type: MIME type
    
    Returns:
        ImageReference object
    """
    service = ImageReferenceService(workspace_path)
    return await service.create_reference(
        image_data=image_data,
        filename=filename,
        prompt=prompt,
        model=model,
        mime_type=mime_type
    )
