"""
Media endpoint for serving images by ID.
Part of Phase 3: UI Integration
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pathlib import Path
import logging
from typing import Optional

from icpy.services.image_reference_service import get_image_reference_service
from icpy.services.image_cache import get_image_cache

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/media/image/{image_id}")
async def get_image(
    image_id: str,
    thumbnail: bool = Query(False, description="Return thumbnail instead of full image")
):
    """
    Serve image by ID with path resolution and caching.
    
    Strategy:
    1. Check memory cache (fast, recent images)
    2. Resolve path using image_resolver (handles renames)
    3. Load from disk and optionally cache
    4. If thumbnail=True, serve small version
    5. Return 404 if not found
    
    Args:
        image_id: UUID of the image
        thumbnail: If True, return thumbnail version
        
    Returns:
        FileResponse with image data
    """
    logger.info(f"[Media API] Fetching image: {image_id}, thumbnail={thumbnail}")
    
    try:
        # Get services
        ref_service = get_image_reference_service()
        cache = get_image_cache()
        
        # Try to resolve the image reference
        image_ref = await ref_service.get_reference(image_id)
        if not image_ref:
            logger.warning(f"[Media API] Image reference not found: {image_id}")
            raise HTTPException(status_code=404, detail=f"Image not found: {image_id}")
        
        # Determine which file to serve
        if thumbnail and image_ref.thumbnail_path:
            file_path = Path(image_ref.thumbnail_path)
            logger.info(f"[Media API] Serving thumbnail: {file_path}")
        else:
            file_path = Path(image_ref.absolute_path)
            logger.info(f"[Media API] Serving full image: {file_path}")
        
        # Check if file exists
        if not file_path.exists():
            logger.error(f"[Media API] File not found on disk: {file_path}")
            
            # Fallback to thumbnail if full image missing
            if not thumbnail and image_ref.thumbnail_path:
                fallback_path = Path(image_ref.thumbnail_path)
                if fallback_path.exists():
                    logger.warning(f"[Media API] Falling back to thumbnail: {fallback_path}")
                    file_path = fallback_path
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Image file not found: {image_ref.current_filename}"
                    )
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Image file not found: {image_ref.current_filename}"
                )
        
        # Determine media type
        mime_type = image_ref.mime_type
        if thumbnail and file_path.suffix == '.webp':
            mime_type = 'image/webp'
        
        logger.info(f"[Media API] Returning file: {file_path} (mime: {mime_type})")
        
        return FileResponse(
            path=str(file_path),
            media_type=mime_type,
            filename=file_path.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Media API] Error serving image {image_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error serving image: {str(e)}")


@router.get("/api/media/thumbnail/{image_id}")
async def get_thumbnail_base64(image_id: str):
    """
    Get thumbnail as base64 (for immediate display without separate request).
    
    Args:
        image_id: UUID of the image
        
    Returns:
        JSON with thumbnail_base64 field
    """
    logger.info(f"[Media API] Fetching thumbnail base64: {image_id}")
    
    try:
        ref_service = get_image_reference_service()
        image_ref = await ref_service.get_reference(image_id)
        
        if not image_ref or not image_ref.thumbnail_base64:
            raise HTTPException(status_code=404, detail=f"Thumbnail not found: {image_id}")
        
        return {
            "image_id": image_id,
            "thumbnail_base64": image_ref.thumbnail_base64,
            "mime_type": "image/webp"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Media API] Error fetching thumbnail {image_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching thumbnail: {str(e)}")
