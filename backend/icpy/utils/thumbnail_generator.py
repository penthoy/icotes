"""
Thumbnail Generator Utility
Generates optimized thumbnails from images using Pillow.
"""
import base64
import hashlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from PIL import Image
import logging

logger = logging.getLogger(__name__)


@dataclass
class ThumbnailConfig:
    """Configuration for thumbnail generation"""
    max_width: int = 128
    max_height: int = 128
    scale_factor: float = 0.1  # 1/10 of original size
    quality: int = 80
    format: str = 'WEBP'


def generate_thumbnail(
    image_path: str,
    thumbnails_dir: str,
    max_size: Tuple[int, int] = (128, 128),
    scale_factor: float = 0.1,
    quality: int = 80,
    image_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate an optimized thumbnail from an image.
    
    Uses LANCZOS resampling for high quality thumbnails.
    Saves as WebP for better compression than PNG/JPEG.
    
    Strategy:
    - If 1/10 of original size < max_size: use 1/10 size
    - Otherwise: fit within max_size maintaining aspect ratio
    
    Args:
        image_path: Path to original image
        thumbnails_dir: Directory to save thumbnails
        max_size: Maximum dimensions (width, height)
        scale_factor: Scale factor (e.g., 0.1 for 1/10 size)
        quality: WebP quality (1-100, 80 recommended)
        image_id: Optional image ID for filename (generates UUID if None)
    
    Returns:
        Dict containing:
        - 'path': Path to saved thumbnail file
        - 'base64': Base64 encoded thumbnail data
        - 'size_bytes': File size in bytes
        - 'width': Thumbnail width
        - 'height': Thumbnail height
    """
    try:
        # Load original image
        img = Image.open(image_path)
        original_width, original_height = img.size
        
        # Convert to RGB if necessary (e.g., PNG with transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Calculate thumbnail size
        # Strategy: Use smaller of (1/10 original) or (max_size)
        scaled_width = int(original_width * scale_factor)
        scaled_height = int(original_height * scale_factor)
        
        # Ensure minimum size of 1x1
        scaled_width = max(1, scaled_width)
        scaled_height = max(1, scaled_height)
        
        if scaled_width <= max_size[0] and scaled_height <= max_size[1]:
            # Use 1/10 size
            thumb_width, thumb_height = scaled_width, scaled_height
        else:
            # Fit within max_size maintaining aspect ratio
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            thumb_width, thumb_height = img.size
        
        # Ensure minimum thumbnail size
        thumb_width = max(1, thumb_width)
        thumb_height = max(1, thumb_height)
        
        # Resize if not using thumbnail() method
        if (thumb_width, thumb_height) != img.size:
            img = img.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        
        # Generate filename
        if image_id is None:
            import uuid
            image_id = str(uuid.uuid4())
        
        thumbnail_filename = f"{image_id}.webp"
        thumbnail_path = Path(thumbnails_dir) / thumbnail_filename
        
        # Ensure thumbnails directory exists
        Path(thumbnails_dir).mkdir(parents=True, exist_ok=True)
        
        # Save as WebP with method=6 (best compression, slower but acceptable for thumbnails)
        img.save(thumbnail_path, format='WEBP', quality=quality, method=6)
        
        # Get file size
        file_size = thumbnail_path.stat().st_size
        
        # Generate base64
        buffer = io.BytesIO()
        img.save(buffer, format='WEBP', quality=quality, method=6)
        thumbnail_bytes = buffer.getvalue()
        thumbnail_base64 = base64.b64encode(thumbnail_bytes).decode('utf-8')
        
        logger.info(f"Generated thumbnail: {thumb_width}x{thumb_height}, {file_size} bytes")
        
        return {
            'path': str(thumbnail_path),
            'base64': thumbnail_base64,
            'size_bytes': file_size,
            'width': thumb_width,
            'height': thumb_height
        }
        
    except Exception as e:
        logger.error(f"Failed to generate thumbnail for {image_path}: {e}")
        raise


def calculate_checksum(file_path: str) -> str:
    """
    Calculate SHA256 checksum of a file.
    
    Args:
        file_path: Path to file
    
    Returns:
        Hex string of SHA256 hash
    """
    sha256 = hashlib.sha256()
    
    with open(file_path, 'rb') as f:
        # Read in chunks to handle large files
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    
    return sha256.hexdigest()
