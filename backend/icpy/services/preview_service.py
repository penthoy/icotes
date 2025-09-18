"""
Preview Service for icpy Backend

Handles live preview functionality for web applications including project type detection,
static file serving, and build processes. Implements Phase 1 of the Live Preview Plans
with iframe-based preview support.

Key Features:
- Project type auto-detection (HTML, React, Vue, Next.js, etc.)
- Static file serving with proper MIME types
- Build process orchestration for different project types
- Preview lifecycle management (create, update, delete)
- Security sandboxing for preview content
- Real-time preview updates via WebSocket events

This service follows Google-style docstrings and integrates with the message broker
for event-driven architecture.
"""

import asyncio
import aiofiles
import hashlib
import json
import logging
import mimetypes
import os
import pathlib
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable

from ..core.message_broker import get_message_broker
from ..core.connection_manager import get_connection_manager

logger = logging.getLogger(__name__)


class ProjectType(Enum):
    """Project type enumeration for preview generation."""
    HTML = "html"
    REACT = "react"
    VUE = "vue"
    NEXT = "next"
    VITE = "vite"
    NODE = "node"
    PYTHON_FLASK = "python-flask"
    STATIC = "static"


class PreviewStatus(Enum):
    """Preview status enumeration."""
    BUILDING = "building"
    READY = "ready"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class PreviewProject:
    """Preview project data structure."""
    id: str
    project_type: ProjectType
    status: PreviewStatus
    files: Dict[str, str] = field(default_factory=dict)
    build_dir: Optional[str] = None
    serve_dir: Optional[str] = None
    url: Optional[str] = None
    port: Optional[int] = None
    process: Optional[subprocess.Popen] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class PreviewService:
    """
    Service for managing live preview functionality.
    
    Provides iframe-based live preview for web applications with support for
    multiple project types, build processes, and real-time updates.
    """

    def __init__(self, base_preview_dir: str = "/tmp/icotes_previews"):
        """
        Initialize the preview service.
        
        Args:
            base_preview_dir: Base directory for storing preview projects
        """
        self.base_preview_dir = pathlib.Path(base_preview_dir)
        self.base_preview_dir.mkdir(exist_ok=True)
        
        self.active_previews: Dict[str, PreviewProject] = {}
        self.port_range = range(3001, 4000)
        self.used_ports: Set[int] = set()
        
        self.message_broker = get_message_broker()
        self.connection_manager = get_connection_manager()
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the preview service."""
        logger.info("Starting Preview Service")
        
        # Start periodic cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        # Publish service started event
        await self.message_broker.publish("preview.service.started", {
            "service": "preview",
            "timestamp": time.time()
        })
        
    async def stop(self):
        """Stop the preview service and cleanup resources."""
        logger.info("Stopping Preview Service")
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            
        # Cleanup all active previews
        for preview_id in list(self.active_previews.keys()):
            await self.delete_preview(preview_id)
            
        # Publish service stopped event
        await self.message_broker.publish("preview.service.stopped", {
            "service": "preview",
            "timestamp": time.time()
        })

    def detect_project_type(self, files: Dict[str, str]) -> ProjectType:
        """
        Detect project type based on file patterns and content.
        
        Args:
            files: Dictionary of file paths to content
            
        Returns:
            Detected project type
        """
        file_names = set(files.keys())
        
        # Check for package.json to identify Node.js projects
        if "package.json" in file_names:
            try:
                package_json = json.loads(files["package.json"])
                dependencies = {**package_json.get("dependencies", {}), 
                              **package_json.get("devDependencies", {})}
                
                if any(dep in dependencies for dep in ["react", "@types/react"]):
                    return ProjectType.REACT
                if any(dep in dependencies for dep in ["vue", "@vue/cli"]):
                    return ProjectType.VUE
                if any(dep in dependencies for dep in ["next", "next"]):
                    return ProjectType.NEXT
                if any(dep in dependencies for dep in ["vite", "@vitejs/plugin-react"]):
                    return ProjectType.VITE
                    
                return ProjectType.NODE
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse package.json: {e}")
        
        # Check for static HTML files
        if any(name == "index.html" or name.endswith(".html") for name in file_names):
            return ProjectType.HTML
            
        # Check for Python Flask/Django
        if any(name in ["app.py", "main.py", "manage.py"] for name in file_names):
            return ProjectType.PYTHON_FLASK
            
        # Default to static
        return ProjectType.STATIC

    def _get_available_port(self) -> int:
        """Get an available port from the port range."""
        for port in self.port_range:
            if port not in self.used_ports:
                self.used_ports.add(port)
                return port
        raise Exception("No available ports in range")

    def _release_port(self, port: int):
        """Release a port back to the available pool."""
        self.used_ports.discard(port)

    async def create_preview(self, files: Dict[str, str], project_type: Optional[str] = None) -> str:
        """
        Create a new preview project.
        
        Args:
            files: Dictionary of file paths to content
            project_type: Optional project type override
            
        Returns:
            Preview ID
        """
        preview_id = str(uuid.uuid4())
        
        try:
            # Detect project type if not provided
            detected_type = ProjectType(project_type) if project_type else self.detect_project_type(files)
            
            logger.info(f"Creating preview {preview_id} with type {detected_type.value}")
            
            # Create preview project
            preview = PreviewProject(
                id=preview_id,
                project_type=detected_type,
                status=PreviewStatus.BUILDING,
                files=files.copy()
            )
            
            # Create project directory
            project_dir = self.base_preview_dir / preview_id
            project_dir.mkdir(exist_ok=True)
            preview.build_dir = str(project_dir)
            
            # Write files to disk
            await self._write_files_to_disk(project_dir, files)
            
            # Store preview
            self.active_previews[preview_id] = preview
            
            # Start build process
            asyncio.create_task(self._build_and_serve_preview(preview))
            
            # Publish preview created event
            await self.message_broker.publish("preview.created", {
                "preview_id": preview_id,
                "project_type": detected_type.value,
                "files_count": len(files),
                "timestamp": time.time()
            })
            
            return preview_id
            
        except Exception as e:
            logger.error(f"Failed to create preview {preview_id}: {e}")
            # Cleanup on failure
            if preview_id in self.active_previews:
                await self.delete_preview(preview_id)
            raise

    async def update_preview(self, preview_id: str, files: Dict[str, str]) -> bool:
        """
        Update an existing preview with new files.
        
        Args:
            preview_id: Preview ID
            files: Updated files dictionary
            
        Returns:
            Success status
        """
        if preview_id not in self.active_previews:
            logger.warning(f"Preview {preview_id} not found for update")
            return False
            
        try:
            preview = self.active_previews[preview_id]
            preview.files.update(files)
            preview.status = PreviewStatus.BUILDING
            preview.updated_at = time.time()
            
            # Write updated files to disk
            project_dir = pathlib.Path(preview.build_dir)
            await self._write_files_to_disk(project_dir, files)
            
            logger.info(f"Updating preview {preview_id}")
            
            # Restart build process
            asyncio.create_task(self._build_and_serve_preview(preview))
            
            # Publish preview updated event
            await self.message_broker.publish("preview.updated", {
                "preview_id": preview_id,
                "files_count": len(files),
                "timestamp": time.time()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update preview {preview_id}: {e}")
            return False

    async def get_preview_status(self, preview_id: str) -> Optional[Dict[str, Any]]:
        """
        Get preview status and information.
        
        Args:
            preview_id: Preview ID
            
        Returns:
            Preview status information or None if not found
        """
        if preview_id not in self.active_previews:
            return None
            
        preview = self.active_previews[preview_id]
        return {
            "id": preview.id,
            "project_type": preview.project_type.value,
            "status": preview.status.value,
            "url": preview.url,
            "ready": preview.status == PreviewStatus.READY,
            "error": preview.error,
            "created_at": preview.created_at,
            "updated_at": preview.updated_at
        }

    async def delete_preview(self, preview_id: str) -> bool:
        """
        Delete a preview and cleanup resources.
        
        Args:
            preview_id: Preview ID
            
        Returns:
            Success status
        """
        if preview_id not in self.active_previews:
            logger.warning(f"Preview {preview_id} not found for deletion")
            return False
            
        try:
            preview = self.active_previews[preview_id]
            
            logger.info(f"Deleting preview {preview_id}")
            
            # Stop process if running
            if preview.process:
                try:
                    preview.process.terminate()
                    await asyncio.sleep(1)
                    if preview.process.poll() is None:
                        preview.process.kill()
                except Exception as e:
                    logger.warning(f"Failed to stop preview process: {e}")
            
            # Release port
            if preview.port:
                self._release_port(preview.port)
            
            # Remove files
            if preview.build_dir:
                try:
                    shutil.rmtree(preview.build_dir)
                except Exception as e:
                    logger.warning(f"Failed to remove preview directory: {e}")
            
            # Remove from active previews
            del self.active_previews[preview_id]
            
            # Publish preview deleted event
            await self.message_broker.publish("preview.deleted", {
                "preview_id": preview_id,
                "timestamp": time.time()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete preview {preview_id}: {e}")
            return False

    async def _write_files_to_disk(self, project_dir: pathlib.Path, files: Dict[str, str]):
        """Write files to the project directory."""
        for file_path, content in files.items():
            # Ensure file path is safe (no directory traversal)
            safe_path = pathlib.Path(file_path)
            if safe_path.is_absolute() or ".." in safe_path.parts:
                logger.warning(f"Skipping unsafe file path: {file_path}")
                continue
                
            full_path = project_dir / safe_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(full_path, 'w', encoding='utf-8') as f:
                await f.write(content)

    async def _build_and_serve_preview(self, preview: PreviewProject):
        """Build and serve a preview project."""
        try:
            project_dir = pathlib.Path(preview.build_dir)
            
            # Build based on project type
            if preview.project_type == ProjectType.HTML:
                await self._serve_static_html(preview, project_dir)
            elif preview.project_type == ProjectType.REACT:
                await self._build_and_serve_react(preview, project_dir)
            elif preview.project_type == ProjectType.VUE:
                await self._build_and_serve_vue(preview, project_dir)
            elif preview.project_type == ProjectType.STATIC:
                await self._serve_static_files(preview, project_dir)
            else:
                # Default to static serving
                await self._serve_static_files(preview, project_dir)
                
        except Exception as e:
            logger.error(f"Failed to build preview {preview.id}: {e}")
            preview.status = PreviewStatus.ERROR
            preview.error = str(e)

    async def _serve_static_html(self, preview: PreviewProject, project_dir: pathlib.Path):
        """Serve static HTML files."""
        port = self._get_available_port()
        preview.port = port
        preview.serve_dir = str(project_dir)
        
        # Start simple HTTP server
        cmd = ["python", "-m", "http.server", str(port)]
        preview.process = subprocess.Popen(
            cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        await asyncio.sleep(2)
        
        preview.url = f"/preview/{preview.id}/"
        preview.status = PreviewStatus.READY
        
        logger.info(f"Static HTML preview {preview.id} ready on port {port}")

    async def _serve_static_files(self, preview: PreviewProject, project_dir: pathlib.Path):
        """Serve static files."""
        await self._serve_static_html(preview, project_dir)

    async def _build_and_serve_react(self, preview: PreviewProject, project_dir: pathlib.Path):
        """Build and serve React application."""
        try:
            # Generate package.json if it doesn't exist
            package_json_path = project_dir / "package.json"
            if not package_json_path.exists():
                package_json = {
                    "name": f"preview-{preview.id}",
                    "version": "1.0.0",
                    "private": True,
                    "dependencies": {
                        "react": "^18.2.0",
                        "react-dom": "^18.2.0",
                        "react-scripts": "5.0.1"
                    },
                    "scripts": {
                        "start": "react-scripts start",
                        "build": "react-scripts build"
                    },
                    "browserslist": {
                        "production": [
                            ">0.2%",
                            "not dead",
                            "not op_mini all"
                        ],
                        "development": [
                            "last 1 chrome version",
                            "last 1 firefox version",
                            "last 1 safari version"
                        ]
                    }
                }
                
                async with aiofiles.open(package_json_path, 'w') as f:
                    await f.write(json.dumps(package_json, indent=2))
            
            # Install dependencies
            install_proc = subprocess.Popen(
                ["npm", "install"],
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            install_proc.wait()
            
            if install_proc.returncode != 0:
                raise Exception("npm install failed")
            
            # Start dev server
            port = self._get_available_port()
            preview.port = port
            
            env = os.environ.copy()
            env["PORT"] = str(port)
            
            preview.process = subprocess.Popen(
                ["npm", "start"],
                cwd=project_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for dev server to start
            await asyncio.sleep(10)
            
            preview.url = f"/preview/{preview.id}/"
            preview.status = PreviewStatus.READY
            
            logger.info(f"React preview {preview.id} ready on port {port}")
            
        except Exception as e:
            logger.error(f"Failed to build React preview: {e}")
            raise

    async def _build_and_serve_vue(self, preview: PreviewProject, project_dir: pathlib.Path):
        """Build and serve Vue application."""
        # Similar to React but with Vue-specific configuration
        await self._serve_static_html(preview, project_dir)

    async def _periodic_cleanup(self):
        """Periodic cleanup of old previews."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                current_time = time.time()
                expired_previews = []
                
                for preview_id, preview in self.active_previews.items():
                    # Clean up previews older than 1 hour
                    if current_time - preview.updated_at > 3600:
                        expired_previews.append(preview_id)
                
                for preview_id in expired_previews:
                    logger.info(f"Cleaning up expired preview {preview_id}")
                    await self.delete_preview(preview_id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in preview cleanup: {e}")


# Global service instance
_preview_service: Optional[PreviewService] = None


def get_preview_service() -> PreviewService:
    """Get the global preview service instance."""
    global _preview_service
    if _preview_service is None:
        _preview_service = PreviewService()
    return _preview_service


async def initialize_preview_service():
    """Initialize the preview service."""
    service = get_preview_service()
    await service.start()


async def shutdown_preview_service():
    """Shutdown the preview service."""
    global _preview_service
    if _preview_service:
        await _preview_service.stop()
        _preview_service = None