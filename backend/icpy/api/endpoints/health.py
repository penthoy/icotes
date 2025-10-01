"""
Health check and configuration endpoints.

These endpoints provide basic system status and configuration information.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

try:
    from icpy.services.clipboard_service import clipboard_service
    from icpy.auth import auth_manager, get_optional_user
    ICPY_AVAILABLE = True
except ImportError:
    logger.warning("icpy modules not available for health endpoints")
    ICPY_AVAILABLE = False
    clipboard_service = None
    auth_manager = None
    get_optional_user = lambda request: None

try:
    from terminal import terminal_manager
    TERMINAL_AVAILABLE = True
except ImportError:
    logger.warning("Terminal module not available")
    TERMINAL_AVAILABLE = False


async def health_check(request: Request):
    """Health check endpoint."""
    clipboard_status = await clipboard_service.get_status() if ICPY_AVAILABLE else {"capabilities": {"read": False, "write": False}}
    
    # Get user info without failing if not authenticated
    user = None
    try:
        user = get_optional_user(request) if ICPY_AVAILABLE else None
    except Exception:
        user = None
    
    health_data = {
        "status": "healthy",
        "services": {
            "icpy": ICPY_AVAILABLE,
            "terminal": TERMINAL_AVAILABLE,
            "clipboard": clipboard_status["capabilities"]
        },
        "timestamp": asyncio.get_event_loop().time(),
        "auth": {
            "mode": "saas" if (ICPY_AVAILABLE and auth_manager.is_saas_mode()) else "standalone",
            "authenticated": user is not None if (ICPY_AVAILABLE and auth_manager.is_saas_mode()) else None,
            "user_id": user.get("user_id") if user else None
        }
    }
    
    return health_data


async def healthz():
    """Simple health check endpoint for orchestrator probes."""
    return {"status": "ok"}


async def get_frontend_config(request: Request):
    """
    Provide dynamic configuration for the frontend based on the request host.
    Prioritizes dynamic host detection for Cloudflare tunnel compatibility.
    Falls back to environment variables only when hosts match.
    """
    # Get the host from the request
    host = request.headers.get("host", "localhost:8000")
    
    # Check for development environment variables
    env_backend_url = os.getenv('VITE_BACKEND_URL')
    env_api_url = os.getenv('VITE_API_URL') 
    env_ws_url = os.getenv('VITE_WS_URL')
    
    # Check if the request host matches the environment configuration
    use_env_config = False
    if env_backend_url and env_api_url and env_ws_url:
        try:
            env_host = env_backend_url.replace('http://', '').replace('https://', '').split('/')[0]
            if host == env_host:
                use_env_config = True
                logger.info(f"Request host {host} matches environment host {env_host}, using environment config")
            else:
                logger.info(f"Request host {host} differs from environment host {env_host}, using dynamic detection for Cloudflare tunnel compatibility")
        except Exception as e:
            logger.warning(f"Error parsing environment URL {env_backend_url}: {e}")
    
    if use_env_config:
        # Development mode with matching host: use environment variables
        config = {
            "base_url": env_backend_url,
            "api_url": env_api_url,
            "ws_url": env_ws_url,
            "version": "1.0.0",
            "auth_mode": auth_manager.auth_mode if ICPY_AVAILABLE else "standalone",
            "features": {
                "terminal": TERMINAL_AVAILABLE,
                "icpy": ICPY_AVAILABLE,
                "clipboard": True
            }
        }
        logger.info(f"Using environment-based config: {config}")
        return config
    
    # Dynamic host detection mode (used for Cloudflare tunnels, Docker, and mismatched hosts)
    
    # Determine protocol (HTTP vs HTTPS)
    # Check for forwarded proto first (reverse proxy), then connection
    protocol = "http"
    if (request.headers.get("x-forwarded-proto") == "https" or 
        request.headers.get("x-forwarded-ssl") == "on" or
        str(request.url.scheme) == "https"):
        protocol = "https"
    
    # Build URLs
    base_url = f"{protocol}://{host}"
    ws_protocol = "wss" if protocol == "https" else "ws"
    ws_url = f"{ws_protocol}://{host}/ws"
    
    config = {
        "base_url": base_url,
        "api_url": f"{base_url}/api",
        "ws_url": ws_url,
        "version": "1.0.0",
        "auth_mode": auth_manager.auth_mode if ICPY_AVAILABLE else "standalone",
        "features": {
            "terminal": TERMINAL_AVAILABLE,
            "icpy": ICPY_AVAILABLE,
            "clipboard": True
        }
    }
    
    logger.info(f"Using dynamic host-based config: {config}")
    return config