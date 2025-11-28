"""Media Service
Phase 0/1 groundwork for handling chat media attachments.

Responsibilities (initial):
- Provide filesystem layout and helper methods for storing uploaded files.
- Enforce basic validation (size, allowed mime prefixes) using env configuration.
- Return lightweight attachment metadata dictionaries suitable to embed in ChatMessage.attachments.

Future phases will add: thumbnail generation, async processing queue, external object storage abstraction.
"""
from __future__ import annotations

import os
import uuid
import mimetypes
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Iterable
import zipfile
import io

import logging
logger = logging.getLogger(__name__)

# Environment variable helpers
"""MEDIA_BASE_DIR default adjustment

Previous default path included a leading "workspace/" prefix ("workspace/.icotes/media").
We now standardize to project-root relative ".icotes/media" so exported files
and media storage sit under the backend workspace root consistently.
For backward compatibility we detect the old path and migrate (simple reuse) if it exists.
"""
# Revert to explicit workspace prefix per updated requirement so files land under
# /workspace/.icotes/media rather than project-root/.icotes/media
_legacy_default = ".icotes/media"  # previously new default
_required_default = "workspace/.icotes/media"
env_override = os.getenv("MEDIA_BASE_DIR")
if env_override:
    MEDIA_BASE_DIR = env_override
else:
    # Use required path; if it doesn't exist create it. If data already in legacy, keep legacy but emit warning.
    if os.path.exists(_legacy_default) and not os.path.exists(_required_default):
        # Legacy (root based) exists but new required doesn't; migrate by using required and leaving old intact.
        MEDIA_BASE_DIR = _required_default
    else:
        MEDIA_BASE_DIR = _required_default
MEDIA_UPLOAD_DIR = os.getenv("MEDIA_UPLOAD_DIR", "uploads")
MEDIA_TEMP_DIR = os.getenv("MEDIA_TEMP_DIR", "tmp")
MEDIA_MAX_FILE_SIZE_MB = int(os.getenv("MEDIA_MAX_FILE_SIZE_MB", "25"))
MEDIA_ALLOWED_TYPES = [p.strip() for p in os.getenv("MEDIA_ALLOWED_TYPES", "image/,video/,audio/,application/pdf").split(',') if p.strip()]
MEDIA_SANITIZE_FILENAMES = os.getenv("MEDIA_SANITIZE_FILENAMES", "1") == "1"

# Root resolution relative to project if not absolute
_base_path = Path(MEDIA_BASE_DIR)
if not _base_path.is_absolute():
    # Fix: Use proper workspace root, not backend's cwd
    current_dir = Path.cwd().resolve()
    if current_dir.name == 'backend':
        workspace_root = current_dir.parent
    else:
        workspace_root = current_dir
    _base_path = workspace_root / _base_path

UPLOAD_PATH = _base_path / MEDIA_UPLOAD_DIR
TEMP_PATH = _base_path / MEDIA_TEMP_DIR

for p in [UPLOAD_PATH, TEMP_PATH]:
    p.mkdir(parents=True, exist_ok=True)

@dataclass
class MediaAttachment:
    id: str
    filename: str
    mime_type: str
    size_bytes: int
    relative_path: str  # path relative to MEDIA_BASE_DIR
    kind: str  # 'images' | 'audio' | 'files'
    url: Optional[str] = None  # future: signed URL or API endpoint
    thumbnail: Optional[str] = None  # relative path to thumbnail

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

class MediaValidationError(Exception):
    pass

class MediaService:
    def __init__(self):
        self.base_dir = _base_path
        self.upload_dir = UPLOAD_PATH  # legacy location (phase 0/1 alpha)
        self.temp_dir = TEMP_PATH
        self.max_size_bytes = MEDIA_MAX_FILE_SIZE_MB * 1024 * 1024
        self.allowed_prefixes = MEDIA_ALLOWED_TYPES
        # New structured kind dirs (Phase 1 spec alignment)
        self.images_dir = self.base_dir / 'images'
        self.audio_dir = self.base_dir / 'audio'
        self.files_dir = self.base_dir / 'files'
        for d in (self.images_dir, self.audio_dir, self.files_dir):
            d.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, name: str) -> str:
        if not MEDIA_SANITIZE_FILENAMES:
            return name
        # Basic sanitation: remove path separators and spaces -> underscore
        name = name.replace('..', '')
        name = name.replace('/', '_').replace('\\', '_').strip()
        name = '_'.join(name.split())
        return name

    def _validate(self, filename: str, size_bytes: int, mime_type: Optional[str]):
        if size_bytes > self.max_size_bytes:
            raise MediaValidationError(f"File exceeds max size {MEDIA_MAX_FILE_SIZE_MB}MB")
        if mime_type:
            if not any(mime_type.startswith(prefix) for prefix in self.allowed_prefixes):
                raise MediaValidationError(f"Disallowed mime type: {mime_type}")

    def _classify_kind(self, mime_type: str) -> str:
        if mime_type.startswith('image/'):
            return 'images'
        if mime_type.startswith('audio/'):
            return 'audio'
        return 'files'

    def save_bytes(self, data: bytes, original_filename: str, mime_type: Optional[str] = None) -> MediaAttachment:
        mime_type = mime_type or mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
        size_bytes = len(data)
        self._validate(original_filename, size_bytes, mime_type)

        safe_name = self._sanitize_filename(original_filename)
        attachment_id = uuid.uuid4().hex
        kind = self._classify_kind(mime_type)
        # Store directly under kind directory (no shard subdir)
        base_kind_dir = {
            'images': self.images_dir,
            'audio': self.audio_dir,
            'files': self.files_dir,
        }[kind]
        base_kind_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{attachment_id}_{safe_name}"
        file_path = base_kind_dir / stored_name
        with open(file_path, 'wb') as f:
            f.write(data)

        rel_path = file_path.relative_to(self.base_dir).as_posix()
        attachment = MediaAttachment(
            id=attachment_id,
            filename=safe_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            relative_path=rel_path,
            kind=kind,
            url=None  # Future: build API URL /media/{id}
        )
        logger.info(f"Saved media attachment {attachment_id} -> {rel_path}")
        return attachment

    def get_file_path(self, attachment: MediaAttachment | str) -> Path:
        if isinstance(attachment, str):
            # interpret as relative path
            return self.base_dir / attachment
        return self.base_dir / attachment.relative_path

    # ------------------ Listing / Delete / Zip helpers ------------------
    def list_kind(self, kind: str) -> List[Dict[str, Any]]:
        """List files for a given kind (images|audio|files) newest first."""
        kind_dir = {
            'images': self.images_dir,
            'audio': self.audio_dir,
            'files': self.files_dir,
        }.get(kind)
        if not kind_dir or not kind_dir.exists():
            return []
        items: List[Dict[str, Any]] = []
        for p in kind_dir.rglob('*'):
            if p.is_file():
                rel = p.relative_to(self.base_dir).as_posix()
                stat = p.stat()
                mime = mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
                items.append({
                    'name': p.name,
                    'rel_path': rel,
                    'size': stat.st_size,
                    'created_at': stat.st_mtime,
                    'mime': mime,
                })
        # Sort newest first
        items.sort(key=lambda x: x['created_at'], reverse=True)
        return items

    def delete_kind_file(self, kind: str, filename: str) -> Dict[str, Any]:
        """Delete file by searching within kind dir for name match. Returns success & referenced flag."""
        files = self.list_kind(kind)
        match = next((f for f in files if f['name'] == filename), None)
        if not match:
            return {'success': False, 'referenced': False, 'reason': 'not_found'}
        path = self.base_dir / match['rel_path']
        try:
            path.unlink(missing_ok=True)
            # TODO: detect references in chat messages; for now referenced always False
            return {'success': True, 'referenced': False}
        except Exception as e:
            logger.exception('Failed deleting media file %s', path)
            return {'success': False, 'referenced': False, 'reason': 'error'}

    def build_zip(self, rel_paths: Iterable[str]) -> bytes:
        """Create an in-memory zip from provided relative paths."""
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for rel in rel_paths:
                try:
                    # Defense-in-depth: validate path doesn't escape media root
                    p = (self.base_dir / rel).resolve()
                    p.relative_to(self.base_dir)
                    if p.exists() and p.is_file():
                        # Use just filename inside zip to avoid leaking server paths
                        zf.write(p, arcname=p.name)
                except (ValueError, OSError):
                    # Skip invalid paths that escape media root
                    logger.warning(f"Skipping invalid path in build_zip: {rel}")
                    continue
        mem.seek(0)
        return mem.read()

# Singleton accessor
_media_service: Optional[MediaService] = None

def get_media_service() -> MediaService:
    global _media_service
    if _media_service is None:
        _media_service = MediaService()
    return _media_service
