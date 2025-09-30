"""
CORS configuration utilities.

Helper functions for configuring Cross-Origin Resource Sharing (CORS) policies.
"""

import os
import logging
from typing import List

logger = logging.getLogger(__name__)


def configure_cors_origins() -> List[str]:
    """Configure and return CORS allowed origins based on environment variables."""
    allowed_origins = []
    
    # Add production domains if available
    frontend_url = os.environ.get("FRONTEND_URL")
    if frontend_url:
        allowed_origins.append(frontend_url)
    
    # Add SITE_URL-based origins for both single-port and dual-port setups
    site_url = os.environ.get("SITE_URL")
    if site_url:
        # Single-port setup (backend serves frontend)
        backend_port = os.environ.get("BACKEND_PORT") or os.environ.get("PORT") or "8000"
        allowed_origins.append(f"http://{site_url}:{backend_port}")
        allowed_origins.append(f"https://{site_url}:{backend_port}")
        
        # Dual-port setup (separate frontend)
        frontend_port = os.environ.get("FRONTEND_PORT") or "5173"
        allowed_origins.append(f"http://{site_url}:{frontend_port}")
        allowed_origins.append(f"https://{site_url}:{frontend_port}")
    
    # For development, allow localhost and common development ports
    if os.environ.get("NODE_ENV") == "development":
        allowed_origins.extend([
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ])
        
        # Add SITE_URL with common development ports
        if site_url:
            for port in ["8000", "3000", "5173"]:
                allowed_origins.append(f"http://{site_url}:{port}")
                allowed_origins.append(f"https://{site_url}:{port}")
    
    # For production, allow all origins if not specified (Coolify handles this)
    if os.environ.get("NODE_ENV") == "production" and not allowed_origins:
        allowed_origins = ["*"]
    
    # Remove duplicates and log
    allowed_origins = list(set(allowed_origins))
    logger.info(f"CORS allowed origins: {allowed_origins}")
    
    return allowed_origins