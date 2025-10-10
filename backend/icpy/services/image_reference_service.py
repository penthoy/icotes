"""
Image Reference Service
Manages image references to avoid storing large base64 data in chat history.
"""
import asyncio
import json
import os
import uuid
import time
import logging
from contextlib import suppress
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional, Any

from ..utils.thumbnail_generator import generate_thumbnail, calculate_checksum

logger = logging.getLogger(__name__)


@dataclass
class ImageReference:
    """
    Reference to an image file with metadata.
    Used instead of storing full base64 data in JSONL.
    """
    image_id: str  # Stable UUID identifier
    original_filename: str  # Original filename when created
    current_filename: str  # Current filename (updates if renamed)
    relative_path: str  # Path relative to workspace
    absolute_path: str  # Full system path
    mime_type: str  # MIME type (e.g., "image/png")
    size_bytes: int  # Original file size
    thumbnail_base64: str  # Small base64 thumbnail for immediate display
    thumbnail_path: str  # Path to thumbnail file on disk
    prompt: str  # Original generation prompt
    model: str  # Model used to generate
    timestamp: float  # Creation timestamp
    checksum: str  # SHA256 checksum for integrity/search
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImageReference':
        """Create from dictionary"""
        return cls(**data)


class ImageReferenceService:
    """Service for creating and managing image references"""
    
    def __init__(self, workspace_path: str):
        """
        Initialize service.
        
        Args:
            workspace_path: Path to workspace directory
        """
        self.workspace_path = str(workspace_path)  # Keep as string for consistency
        self._workspace_path_obj = Path(workspace_path)
        self._workspace_path_obj.mkdir(parents=True, exist_ok=True)

        # Internal directories
        self.thumbnails_dir = self._workspace_path_obj / ".icotes" / "thumbnails"
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.thumbnails_dir.parent / "image_references.json"
        self._index_path.parent.mkdir(parents=True, exist_ok=True)

        # Concurrency control for async contexts
        self._lock = asyncio.Lock()
        self._references: Dict[str, Dict[str, Any]] = {}
        self._load_index()
        
        logger.info(f"ImageReferenceService initialized: workspace={workspace_path}")
    
    async def create_reference(
        self,
        image_data: str,
        filename: str,
        prompt: str,
        model: str,
        mime_type: str = "image/png"
    ) -> ImageReference:
        """
        Create an ImageReference from image data.
        
        Args:
            image_data: Base64 encoded image data
            filename: Filename of the image
            prompt: Generation prompt
            model: Model used
            mime_type: MIME type of image
        
        Returns:
            ImageReference object
        """
        try:
            # Generate unique image ID
            image_id = str(uuid.uuid4())
            
            # Determine paths
            relative_path = filename
            absolute_path = self._workspace_path_obj / filename
            
            # Ensure file exists locally; if missing but image_data provided, write it now.
            if not absolute_path.exists():
                try:
                    import base64 as _b64
                    absolute_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(absolute_path, "wb") as fh:
                        fh.write(_b64.b64decode(image_data))
                    logger.info(f"Wrote local image copy for reference: {absolute_path}")
                except Exception as write_e:
                    # If we fail to materialize, keep going; downstream will raise a clearer error.
                    logger.warning(f"Unable to materialize local image copy at {absolute_path}: {write_e}")
            
            # Calculate file size
            size_bytes = absolute_path.stat().st_size if absolute_path.exists() else 0
            
            # Generate checksum (fallback to bytes-based if file still missing)
            if absolute_path.exists():
                checksum = calculate_checksum(str(absolute_path))
            else:
                try:
                    import hashlib, base64 as _b64
                    checksum = hashlib.sha256(_b64.b64decode(image_data)).hexdigest()
                except Exception:
                    checksum = ""
            
            # Generate thumbnail
            thumbnail_result = generate_thumbnail(
                str(absolute_path),
                str(self.thumbnails_dir),
                image_id=image_id
            )
            
            # Create reference
            ref = ImageReference(
                image_id=image_id,
                original_filename=filename,
                current_filename=filename,
                relative_path=relative_path,
                absolute_path=str(absolute_path),
                mime_type=mime_type,
                size_bytes=size_bytes,
                thumbnail_base64=thumbnail_result['base64'],
                thumbnail_path=thumbnail_result['path'],
                prompt=prompt,
                model=model,
                timestamp=time.time(),
                checksum=checksum
            )
            
            logger.info(f"Created ImageReference: {image_id} for {filename}")

            # Persist reference for future lookup (media endpoints, etc.)
            await self._store_reference(ref)
            return ref
            
        except Exception as e:
            logger.error(f"Failed to create image reference: {e}")
            raise

    async def get_reference(self, image_id: str) -> Optional[ImageReference]:
        """Retrieve a stored image reference by ID."""
        async with self._lock:
            ref_dict = self._references.get(image_id)
            if ref_dict is None:
                # Reload index in case another process updated it
                self._load_index()
                ref_dict = self._references.get(image_id)
        if ref_dict:
            try:
                return ImageReference.from_dict(ref_dict)
            except Exception as exc:
                logger.warning(f"Failed to deserialize image reference {image_id}: {exc}")
        return None

    async def list_references(self) -> Dict[str, ImageReference]:
        """Return all known references keyed by image_id."""
        async with self._lock:
            # Provide shallow copy to avoid external mutation
            current = {key: ImageReference.from_dict(value) for key, value in self._references.items()}
        return current

    def _load_index(self) -> None:
        """Load reference index from disk into memory."""
        if not self._index_path.exists():
            self._references = {}
            return
        try:
            with self._index_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                self._references = {key: value for key, value in data.items() if isinstance(value, dict)}
            else:
                logger.warning("Image reference index is not a dict; resetting")
                self._references = {}
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse image reference index; resetting ({exc})")
            self._references = {}
        except Exception as exc:
            logger.warning(f"Could not load image reference index: {exc}")
            self._references = {}

    async def _store_reference(self, reference: ImageReference) -> None:
        """Store or update a reference in the on-disk index."""
        async with self._lock:
            self._references[reference.image_id] = reference.to_dict()
            self._write_index()

    def _write_index(self) -> None:
        """Persist the current reference map to disk atomically."""
        tmp_path = self._index_path.with_suffix(".tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as fh:
                json.dump(self._references, fh, indent=2)
            tmp_path.replace(self._index_path)
        except Exception as exc:
            logger.error(f"Failed to write image reference index: {exc}")
            with suppress(FileNotFoundError):
                tmp_path.unlink()


async def create_image_reference(
    image_data: str,
    filename: str,
    workspace_path: str,
    prompt: str,
    model: str,
    mime_type: str = "image/png"
) -> ImageReference:
    """
    Convenience function to create an image reference.
    
    Args:
        image_data: Base64 encoded image data
        filename: Filename of the image
        workspace_path: Path to workspace
        prompt: Generation prompt
        model: Model used
        mime_type: MIME type
    
    Returns:
        ImageReference object
    """
    service = ImageReferenceService(workspace_path)
    return await service.create_reference(
        image_data=image_data,
        filename=filename,
        prompt=prompt,
        model=model,
        mime_type=mime_type
    )


_global_image_reference_service: Optional[ImageReferenceService] = None


def _detect_workspace_root() -> str:
    """Determine the default workspace root for image references."""
    env_root = os.environ.get("WORKSPACE_ROOT")
    if env_root:
        return env_root
    backend_root = Path(__file__).resolve().parents[2]
    return str(backend_root.parent / "workspace")


def get_image_reference_service(workspace_path: Optional[str] = None) -> ImageReferenceService:
    """Return a global ImageReferenceService instance.
    
    Ensures that FastAPI endpoints and background services share a single cache of
    references while still allowing tests to request isolated instances.
    """
    global _global_image_reference_service

    if workspace_path:
        resolved = str(Path(workspace_path).resolve())
    else:
        resolved = str(Path(_detect_workspace_root()).resolve())

    if _global_image_reference_service is None:
        _global_image_reference_service = ImageReferenceService(workspace_path=resolved)
    else:
        current = Path(_global_image_reference_service.workspace_path).resolve()
        if current != Path(resolved):
            # Recreate service if workspace changed (e.g., during tests)
            _global_image_reference_service = ImageReferenceService(workspace_path=resolved)

    return _global_image_reference_service
