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
    JAVASCRIPT = "javascript"
    CSS = "css"
    MARKDOWN = "markdown"
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
    content_hash: Optional[str] = None


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
        self.content_hash_to_preview: Dict[str, str] = {}  # Maps content hash to preview ID
        self.port_range = range(3001, 4000)
        self.used_ports: Set[int] = set()
        
        self.message_broker = None  # Will be initialized in start()
        self.connection_manager = get_connection_manager()
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the preview service."""
        logger.info("Starting Preview Service")
        
        # Initialize the message broker
        self.message_broker = await get_message_broker()
        
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
            
        # Check for JavaScript/TypeScript files
        if any(name.endswith((".js", ".mjs", ".ts")) for name in file_names):
            return ProjectType.JAVASCRIPT
            
        # Check for React/JSX files
        if any(name.endswith((".jsx", ".tsx")) for name in file_names):
            return ProjectType.REACT
            
        # Check for Vue files
        if any(name.endswith(".vue") for name in file_names):
            return ProjectType.VUE
            
        # Check for CSS files
        if any(name.endswith((".css", ".scss", ".sass")) for name in file_names):
            return ProjectType.CSS
            
        # Check for Markdown files
        if any(name.endswith((".md", ".markdown")) for name in file_names):
            return ProjectType.MARKDOWN
            
        # Check for Python Flask/Django
        if any(name in ["app.py", "main.py", "manage.py"] for name in file_names):
            return ProjectType.PYTHON_FLASK
            
        # Default to static
        return ProjectType.STATIC

    def _get_available_port(self) -> int:
        """Get an available port from the port range."""
        import socket
        
        for port in self.port_range:
            if port not in self.used_ports:
                # Double-check that the port is actually available
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.bind(('127.0.0.1', port))
                        self.used_ports.add(port)
                        logger.info(f"Allocated port {port}, used ports: {self.used_ports}")
                        return port
                except OSError:
                    logger.warning(f"Port {port} appears to be in use, skipping")
                    continue
        raise Exception("No available ports in range")

    def _release_port(self, port: int):
        """Release a port back to the available pool."""
        self.used_ports.discard(port)

    def _generate_content_hash(self, files: Dict[str, str], project_type: str) -> str:
        """Generate a hash for the files content to identify identical previews."""
        # Sort files by name for consistent hashing
        sorted_files = sorted(files.items())
        content_str = f"{project_type}:" + ":".join(f"{name}:{content}" for name, content in sorted_files)
        hash_value = hashlib.md5(content_str.encode()).hexdigest()
        
        # Debug logging to see what's being hashed
        logger.info(f"Generating hash for project_type={project_type}")
        for name, content in sorted_files:
            logger.info(f"  File: {name}, Content length: {len(content)}, First 100 chars: {repr(content[:100])}")
        logger.info(f"  Final content_str length: {len(content_str)}")
        logger.info(f"  Generated hash: {hash_value}")
        
        return hash_value

    def _is_preview_active(self, preview: PreviewProject) -> bool:
        """Check if a preview is still active and its process is running."""
        logger.info(f"Checking if preview {preview.id} is active: status={preview.status.value}, has_process={preview.process is not None}")
        
        if preview.status not in [PreviewStatus.READY, PreviewStatus.BUILDING]:
            logger.info(f"Preview {preview.id} is not active: status is {preview.status.value}")
            return False
        
        # Check if process is still running
        if preview.process:
            poll_result = preview.process.poll()
            logger.info(f"Preview {preview.id} process poll result: {poll_result}")
            if poll_result is not None:
                # Process has terminated
                logger.info(f"Preview {preview.id} process has terminated with code {poll_result}")
                preview.status = PreviewStatus.STOPPED
                return False
        else:
            logger.info(f"Preview {preview.id} has no process")
        
        logger.info(f"Preview {preview.id} is active")
        return True

    async def _find_existing_preview(self, content_hash: str) -> Optional[str]:
        """Find an existing active preview with the same content hash."""
        logger.info(f"Looking for existing preview with content hash: {content_hash}")
        logger.info(f"Current content_hash_to_preview mapping: {self.content_hash_to_preview}")
        
        preview_id = self.content_hash_to_preview.get(content_hash)
        if not preview_id:
            logger.info(f"No existing preview found for content hash {content_hash}")
            return None
        
        preview = self.active_previews.get(preview_id)
        if not preview:
            # Clean up stale mapping
            logger.info(f"Found stale mapping for content hash {content_hash}, cleaning up")
            del self.content_hash_to_preview[content_hash]
            return None
        
        if not self._is_preview_active(preview):
            # Preview is no longer active, clean up
            logger.info(f"Preview {preview_id} is no longer active, cleaning up")
            await self._cleanup_preview(preview_id)
            return None
        
        logger.info(f"Reusing existing preview {preview_id} for content hash {content_hash}")
        return preview_id

    async def _cleanup_preview(self, preview_id: str):
        """Clean up a preview without going through the full delete process."""
        if preview_id in self.active_previews:
            preview = self.active_previews[preview_id]
            
            # Stop process if running
            if preview.process:
                try:
                    preview.process.terminate()
                    preview.process.wait(timeout=1)
                except:
                    try:
                        preview.process.kill()
                    except:
                        pass
            
            # Release port
            if preview.port:
                self._release_port(preview.port)
            
            # Remove from mappings
            del self.active_previews[preview_id]
            if preview.content_hash and preview.content_hash in self.content_hash_to_preview:
                if self.content_hash_to_preview[preview.content_hash] == preview_id:
                    del self.content_hash_to_preview[preview.content_hash]

    async def create_preview(self, files: Dict[str, str], project_type: Optional[str] = None) -> str:
        """
        Create a new preview project or return existing one if identical content exists.
        
        Args:
            files: Dictionary of file paths to content
            project_type: Optional project type override
            
        Returns:
            Preview ID (either new or existing)
        """
        
        try:
            # Detect project type if not provided
            detected_type = ProjectType(project_type) if project_type else self.detect_project_type(files)
            
            # Generate content hash to check for existing previews
            content_hash = self._generate_content_hash(files, detected_type.value)
            
            # Check if we already have an active preview with the same content
            existing_preview_id = await self._find_existing_preview(content_hash)
            if existing_preview_id:
                # Update the timestamp of the existing preview
                existing_preview = self.active_previews[existing_preview_id]
                existing_preview.updated_at = time.time()
                logger.info(f"Reusing preview {existing_preview_id} with URL: {existing_preview.url}")
                return existing_preview_id
            
            # Create new preview
            preview_id = str(uuid.uuid4())
            logger.info(f"Creating new preview {preview_id} with type {detected_type.value}")
            
            # Create preview project
            preview = PreviewProject(
                id=preview_id,
                project_type=detected_type,
                status=PreviewStatus.BUILDING,
                files=files.copy(),
                content_hash=content_hash
            )
            
            # Create project directory
            project_dir = self.base_preview_dir / preview_id
            project_dir.mkdir(exist_ok=True)
            preview.build_dir = str(project_dir)
            
            # Write files to disk
            await self._write_files_to_disk(project_dir, files)
            
            # Store preview and content hash mapping
            self.active_previews[preview_id] = preview
            self.content_hash_to_preview[content_hash] = preview_id
            
            # Start build process
            asyncio.create_task(self._build_and_serve_preview(preview))
            
            # Publish preview created event
            await self.message_broker.publish("preview.created", {
                "preview_id": preview_id,
                "project_type": detected_type.value,
                "files_count": len(files),
                "content_hash": content_hash,
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
            
            # Remove from content hash mapping
            if preview.content_hash and preview.content_hash in self.content_hash_to_preview:
                if self.content_hash_to_preview[preview.content_hash] == preview_id:
                    del self.content_hash_to_preview[preview.content_hash]
            
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
        
        # For HTML projects with a single HTML file, also create index.html
        # This ensures the content is served at the root path
        html_files = [f for f in files.keys() if f.endswith('.html')]
        if len(html_files) == 1 and 'index.html' not in files:
            html_file = html_files[0]
            index_path = project_dir / 'index.html'
            async with aiofiles.open(index_path, 'w', encoding='utf-8') as f:
                await f.write(files[html_file])
            logger.info(f"Created index.html from {html_file} for direct preview access")

    async def _build_and_serve_preview(self, preview: PreviewProject):
        """Build and serve a preview project."""
        try:
            project_dir = pathlib.Path(preview.build_dir)
            
            # Build based on project type
            if preview.project_type == ProjectType.HTML:
                await self._serve_static_html(preview, project_dir)
            elif preview.project_type == ProjectType.JAVASCRIPT:
                await self._serve_javascript(preview, project_dir)
            elif preview.project_type == ProjectType.CSS:
                await self._serve_css(preview, project_dir)
            elif preview.project_type == ProjectType.MARKDOWN:
                await self._serve_markdown(preview, project_dir)
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
        # Use existing port if already assigned, otherwise get a new one
        if not preview.port:
            port = self._get_available_port()
            preview.port = port
        else:
            port = preview.port
        preview.serve_dir = str(project_dir)
        
        # Start simple HTTP server
        cmd = ["python", "-m", "http.server", str(port)]
        logger.info(f"Starting preview server with command: {' '.join(cmd)} in directory {project_dir}")
        preview.process = subprocess.Popen(
            cmd,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        await asyncio.sleep(2)
        
        # Check if the process started successfully
        if preview.process.poll() is not None:
            logger.error(f"Preview server failed to start on port {port}, return code: {preview.process.returncode}")
            # Read stderr for error details
            stderr = preview.process.stderr.read()
            logger.error(f"Preview server stderr: {stderr.decode()}")
            self._release_port(port)
            return None
        
        logger.info(f"Preview server started successfully on port {port}, PID: {preview.process.pid}")
        
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

    async def _serve_javascript(self, preview: PreviewProject, project_dir: pathlib.Path):
        """Serve JavaScript files by wrapping them in HTML."""
        try:
            port = self._get_available_port()
            preview.port = port
            preview.serve_dir = str(project_dir)
            
            # Find the main JS file
            js_files = [f for f in preview.files.keys() if f.endswith(('.js', '.mjs', '.ts'))]
            main_js = js_files[0] if js_files else 'script.js'
            
            # Create an HTML wrapper for the JS file
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JavaScript Preview - {main_js}</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; }}
        .js-container {{ max-width: 800px; margin: 0 auto; }}
        .header {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="js-container">
        <div class="header">
            <h1>JavaScript Preview</h1>
            <p>File: <code>{main_js}</code></p>
        </div>
        <div id="output"></div>
    </div>
    <script src="{main_js}"></script>
</body>
</html>"""
            
            # Write the HTML wrapper as index.html
            html_path = project_dir / "index.html"
            html_path.write_text(html_content, encoding='utf-8')
            
            await self._serve_static_html(preview, project_dir)
        except Exception as e:
            logger.error(f"Failed to serve JavaScript preview: {e}")
            raise

    async def _serve_css(self, preview: PreviewProject, project_dir: pathlib.Path):
        """Serve CSS files by creating a demo HTML page."""
        port = self._get_available_port()
        preview.port = port
        preview.serve_dir = str(project_dir)
        
        # Find the main CSS file
        css_files = [f for f in preview.files.keys() if f.endswith(('.css', '.scss', '.sass'))]
        main_css = css_files[0] if css_files else 'style.css'
        
        # Create an HTML demo page for the CSS
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CSS Preview - {main_css}</title>
    <link rel="stylesheet" href="{main_css}">
</head>
<body>
    <div class="css-preview-container">
        <header>
            <h1>CSS Preview</h1>
            <p>Stylesheet: <code>{main_css}</code></p>
        </header>
        <main>
            <section>
                <h2>Sample Content</h2>
                <p>This page demonstrates your CSS styles with sample content.</p>
                <div class="demo-buttons">
                    <button class="primary">Primary Button</button>
                    <button class="secondary">Secondary Button</button>
                </div>
                <div class="demo-form">
                    <form>
                        <label>Sample Input:</label>
                        <input type="text" placeholder="Enter text here">
                        <label>Sample Textarea:</label>
                        <textarea placeholder="Enter more text here"></textarea>
                    </form>
                </div>
            </section>
        </main>
    </div>
</body>
</html>"""
        
        # Write the HTML demo as index.html
        html_path = project_dir / "index.html"
        html_path.write_text(html_content, encoding='utf-8')
        
        await self._serve_static_html(preview, project_dir)

    async def _serve_markdown(self, preview: PreviewProject, project_dir: pathlib.Path):
        """Serve Markdown files by converting them to HTML."""
        port = self._get_available_port()
        preview.port = port
        preview.serve_dir = str(project_dir)
        
        # Find the main Markdown file
        md_files = [f for f in preview.files.keys() if f.endswith(('.md', '.markdown'))]
        main_md = md_files[0] if md_files else 'README.md'
        md_content = preview.files.get(main_md, '# No content')
        
        # Simple Markdown to HTML conversion (basic)
        html_content = md_content.replace('\\n', '<br>')
        html_content = html_content.replace('# ', '<h1>').replace('## ', '<h2>').replace('### ', '<h3>')
        
        # Create an HTML page for the Markdown
        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Markdown Preview - {main_md}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .md-header {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .md-content {{ background: white; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
        code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="md-header">
        <h1>Markdown Preview</h1>
        <p>File: <code>{main_md}</code></p>
    </div>
    <div class="md-content">
        {html_content}
    </div>
</body>
</html>"""
        
        # Write the HTML as index.html
        html_path = project_dir / "index.html"
        html_path.write_text(full_html, encoding='utf-8')
        
        await self._serve_static_html(preview, project_dir)

    async def _periodic_cleanup(self):
        """Periodic cleanup of old previews."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                current_time = time.time()
                expired_previews = []
                
                for preview_id, preview in self.active_previews.items():
                    # Clean up previews older than 6 hours (extended for development use)
                    if current_time - preview.updated_at > 21600:
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