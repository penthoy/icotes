"""
Authentication endpoints for SaaS mode functionality.

These endpoints handle user authentication, profile management, and token validation.
"""

import os
import logging
from typing import Dict, Any

from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

try:
    from icpy.auth import auth_manager, get_current_user, get_optional_user
    ICPY_AVAILABLE = True
except ImportError:
    logger.warning("icpy auth modules not available")
    ICPY_AVAILABLE = False
    auth_manager = None
    get_current_user = lambda request: None
    get_optional_user = lambda request: None


async def auth_info(request: Request):
    """Get authentication information."""
    user = None
    try:
        user = get_optional_user(request) if ICPY_AVAILABLE else None
    except Exception:
        user = None
        
    return {
        "auth_mode": "saas" if (ICPY_AVAILABLE and auth_manager.is_saas_mode()) else "standalone",
        "authenticated": user is not None if (ICPY_AVAILABLE and auth_manager.is_saas_mode()) else None,
        "user": {
            "id": user.get("user_id") if user else None,
            "email": user.get("email") if user else None,
            "role": user.get("role") if user else None
        } if user else None,
        "requires_auth": ICPY_AVAILABLE and auth_manager.is_saas_mode()
    }


async def user_profile(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user profile. Only available in SaaS mode."""
    if auth_manager.is_standalone_mode():
        raise HTTPException(status_code=404, detail="User profiles not available in standalone mode")
    
    return {
        "user": {
            "id": user.get("user_id"),
            "email": user.get("email"),
            "role": user.get("role"),
            "token_issued_at": user.get("iat"),
            "token_expires_at": user.get("exp")
        }
    }


async def debug_test_token(request: Request):
    """Debug endpoint to test authentication token validation. For development/testing only."""
    if not ICPY_AVAILABLE or auth_manager.is_standalone_mode():
        raise HTTPException(status_code=404, detail="Debug endpoints not available in standalone mode")
    
    token = request.query_params.get('token')
    source = request.query_params.get('src', 'test')
    
    if not token:
        return {
            "error": "missing_token", 
            "message": "Please provide token as query parameter",
            "example": "/auth/debug/test-token?token=your_jwt_here&src=test"
        }
    
    try:
        # Test token validation
        payload = auth_manager.validate_jwt_token(token)
        return {
            "success": True,
            "source": source,
            "token_valid": True,
            "user": {
                "id": payload.get('sub'),
                "email": payload.get('email'),
                "role": payload.get('role', 'user'),
                "issued_at": payload.get('iat'),
                "expires_at": payload.get('exp')
            },
            "payload": payload if os.getenv('CONTAINER_DEBUG_AUTH') else None
        }
    except HTTPException as e:
        return {
            "success": False,
            "source": source,
            "token_valid": False,
            "error": e.detail,
            "status_code": e.status_code
        }