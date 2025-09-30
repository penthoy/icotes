"""
Static file serving utilities.

Helper functions for mounting and serving static files.
"""

import os
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)


def mount_static_files(app: FastAPI) -> None:
    """Mount static files for production React app build."""
    # Check if dist directory exists (production)
    # From backend/icpy/core/static_files.py, go up to icotes root then to dist
    # backend/icpy/core -> backend/icpy -> backend -> icotes -> icotes/dist
    dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "dist")
    if os.path.exists(dist_path):
        # Mount static files for production
        app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")
        # Mount additional static files that might be needed
        if os.path.exists(os.path.join(dist_path, "static")):
            app.mount("/static", StaticFiles(directory=os.path.join(dist_path, "static")), name="static")
        logger.info(f"Serving static files from {dist_path}")
    else:
        logger.info("No dist directory found - running in development mode")