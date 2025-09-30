"""
Preview service endpoints.

These endpoints handle live preview functionality for web development.
"""

import logging
from typing import Optional, Dict
import aiohttp

from fastapi import HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

logger = logging.getLogger(__name__)

try:
    from icpy.services import get_preview_service
    ICPY_AVAILABLE = True
except ImportError:
    logger.warning("icpy preview service not available")
    ICPY_AVAILABLE = False
    get_preview_service = lambda: None


class PreviewCreateRequest(BaseModel):
    """Request model for creating a preview."""
    files: Dict[str, str]
    projectType: Optional[str] = None


class PreviewCreateResponse(BaseModel):
    """Response model for preview creation."""
    preview_id: str
    preview_url: str
    project_type: str


class PreviewUpdateRequest(BaseModel):
    """Request model for updating a preview."""
    files: Dict[str, str]


class PreviewStatusResponse(BaseModel):
    """Response model for preview status."""
    id: str
    project_type: str
    status: str
    url: Optional[str] = None
    ready: bool
    error: Optional[str] = None
    created_at: float
    updated_at: float


async def create_preview(request: PreviewCreateRequest):
    """Create a new preview project."""
    preview_id = None
    try:
        if not ICPY_AVAILABLE:
            raise HTTPException(status_code=500, detail="Preview service not available")
        
        preview_service = get_preview_service()
        preview_id = await preview_service.create_preview(
            files=request.files,
            project_type=request.projectType
        )
        
        # Get preview details
        preview_status = await preview_service.get_preview_status(preview_id)
        if not preview_status:
            raise HTTPException(status_code=500, detail="Failed to get preview status")
        
        # Use the URL from the preview status if available, otherwise construct it
        preview_url = preview_status.get("url") or f"/preview/{preview_id}/"
        
        logger.info(f"Preview API returning: ID={preview_id}, URL={preview_url}")
        
        return PreviewCreateResponse(
            preview_id=preview_id,
            preview_url=preview_url,
            project_type=preview_status["project_type"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating preview with id={preview_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create preview: {str(e)}") from e


async def update_preview(preview_id: str, request: PreviewUpdateRequest):
    """Update an existing preview."""
    try:
        if not ICPY_AVAILABLE:
            raise HTTPException(status_code=500, detail="Preview service not available")
        
        preview_service = get_preview_service()
        success = await preview_service.update_preview(preview_id, request.files)
        
        if not success:
            raise HTTPException(status_code=404, detail="Preview not found")
        
        return {"success": True, "message": "Preview updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating preview {preview_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update preview: {str(e)}")


async def get_preview_status(preview_id: str):
    """Get preview status and information."""
    try:
        if not ICPY_AVAILABLE:
            raise HTTPException(status_code=500, detail="Preview service not available")
        
        preview_service = get_preview_service()
        status = await preview_service.get_preview_status(preview_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Preview not found")
        
        return PreviewStatusResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting preview status {preview_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get preview status: {str(e)}")


async def delete_preview(preview_id: str):
    """Delete a preview and cleanup resources."""
    try:
        if not ICPY_AVAILABLE:
            raise HTTPException(status_code=500, detail="Preview service not available")
        
        preview_service = get_preview_service()
        success = await preview_service.delete_preview(preview_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Preview not found")
        
        return {"success": True, "message": "Preview deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting preview {preview_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete preview: {str(e)}")


async def serve_preview_file(preview_id: str, file_path: str, request: Request):
    """Serve static files for previews."""
    try:
        if not ICPY_AVAILABLE:
            raise HTTPException(status_code=500, detail="Preview service not available")
        
        # Note: Authentication could be added here for SaaS mode if needed
        # if ICPY_AVAILABLE and auth_manager.is_saas_mode():
        #     user = get_optional_user(request)
        #     if not user:
        #         raise HTTPException(status_code=401, detail="Authentication required")
        
        preview_service = get_preview_service()
        preview_status = await preview_service.get_preview_status(preview_id)
        
        if not preview_status:
            raise HTTPException(status_code=404, detail="Preview not found")
        
        # For now, proxy to the local dev server
        # In Phase 1, we'll use a simple HTTP proxy to the preview port
        preview = preview_service.active_previews.get(preview_id)
        if not preview or not preview.port:
            raise HTTPException(status_code=503, detail="Preview not ready")
        
        # Proxy request to the preview server
        target_url = f"http://localhost:{preview.port}/{file_path}"
        
        timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(target_url) as response:
                content = await response.read()
                headers = dict(response.headers)

                # Remove hop-by-hop and sensitive headers
                headers.pop('connection', None)
                headers.pop('transfer-encoding', None)
                headers.pop('content-encoding', None)  # Remove encoding since we're returning raw content
                headers.pop('content-length', None)  # Will be recalculated

                # Normalize some common content types so the browser renders correctly in iframe
                # Some simple servers may return text/plain for .js/.css; correct them here
                import mimetypes
                guessed, _ = mimetypes.guess_type(file_path)
                if guessed:
                    headers['content-type'] = guessed
                else:
                    # Ensure at least a generic text/html for root path
                    headers.setdefault('content-type', 'text/html; charset=utf-8')

                return Response(
                    content=content,
                    status_code=response.status,
                    headers=headers
                )
        
    except HTTPException:
        raise
    except aiohttp.ClientError as e:
        logger.error(f"Preview proxy error for {preview_id}/{file_path}: {e}")
        raise HTTPException(status_code=502, detail="Preview server connection failed") from e
    except Exception as e:
        logger.exception("Error serving preview file %s/%s", preview_id, file_path)
        raise HTTPException(status_code=500, detail="Failed to serve preview file") from e