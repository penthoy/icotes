"""
Clipboard service endpoints.

These endpoints provide clipboard functionality with multi-layer support.
"""

import logging
from typing import Optional

from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

try:
    from icpy.services.clipboard_service import clipboard_service
    ICPY_AVAILABLE = True
except ImportError:
    logger.warning("icpy clipboard service not available")
    ICPY_AVAILABLE = False
    clipboard_service = None


class ClipboardRequest(BaseModel):
    """Request model for clipboard operations."""
    text: str


class ClipboardResponse(BaseModel):
    """Response model for clipboard operations."""
    success: bool
    message: str
    text: Optional[str] = None
    metadata: Optional[dict] = None


async def set_clipboard(request: ClipboardRequest):
    """Set clipboard content using enhanced multi-layer strategy."""
    try:
        if ICPY_AVAILABLE and clipboard_service:
            result = await clipboard_service.write_clipboard(request.text)
            return ClipboardResponse(
                success=result["success"],
                message=f"Clipboard updated via {result['method']}" if result["success"] else result.get("error", "Failed to update clipboard"),
                metadata=result
            )
        else:
            return ClipboardResponse(
                success=False,
                message="Clipboard service not available"
            )
    except Exception as e:
        logger.error(f"Error setting clipboard: {e}")
        return ClipboardResponse(
            success=False,
            message=f"Error: {str(e)}"
        )


async def get_clipboard():
    """Get clipboard content using enhanced multi-layer strategy."""
    try:
        if ICPY_AVAILABLE and clipboard_service:
            result = await clipboard_service.read_clipboard()
            return ClipboardResponse(
                success=result["success"],
                message=f"Clipboard retrieved via {result['method']}" if result["success"] else result.get("error", "Failed to retrieve clipboard"),
                text=result.get("content", ""),
                metadata=result
            )
        else:
            return ClipboardResponse(
                success=False,
                message="Clipboard service not available"
            )
    except Exception as e:
        logger.error(f"Error getting clipboard: {e}")
        return ClipboardResponse(
            success=False,
            message=f"Error: {str(e)}"
        )


async def get_clipboard_history():
    """Get clipboard history."""
    try:
        if ICPY_AVAILABLE and clipboard_service:
            history = await clipboard_service.get_history()
            return {
                "success": True,
                "history": history,
                "count": len(history)
            }
        else:
            return {
                "success": False,
                "message": "Clipboard service not available"
            }
    except Exception as e:
        logger.error(f"Error getting clipboard history: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }


async def get_clipboard_status():
    """Get clipboard service status and capabilities."""
    try:
        if ICPY_AVAILABLE and clipboard_service:
            status = await clipboard_service.get_status()
            return {
                "success": True,
                "status": status
            }
        else:
            return {
                "success": False,
                "message": "Clipboard service not available"
            }
    except Exception as e:
        logger.error(f"Error getting clipboard status: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }


async def clear_clipboard():
    """Clear clipboard content."""
    try:
        if ICPY_AVAILABLE and clipboard_service:
            result = await clipboard_service.clear_clipboard()
            return {
                "success": result["success"],
                "message": f"Clipboard cleared via {result['method']}" if result["success"] else result.get("error", "Failed to clear clipboard")
            }
        else:
            return {
                "success": False,
                "message": "Clipboard service not available"
            }
    except Exception as e:
        logger.error(f"Error clearing clipboard: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }