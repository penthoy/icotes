"""Media API Router
Phase 1 minimal endpoints:
- POST /api/media/upload : accept raw bytes (simplified) for now via form field 'file'
- Future: chunked uploads, thumbnails, multi-attachment association
"""
from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import FileResponse, StreamingResponse
from typing import Dict, List
import logging
from pathlib import Path
import os
import shutil

from ..services.media_service import get_media_service, MediaValidationError
import io

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["media"])

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> Dict:
    service = get_media_service()
    try:
        data = await file.read()
        attachment = service.save_bytes(data, file.filename, file.content_type)
        return {"attachment": attachment.to_dict()}
    except MediaValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Upload failed")
        raise HTTPException(status_code=500, detail="Upload failed")

@router.get("/file/{attachment_id}")
async def get_file(attachment_id: str):
    """Lookup a file by attachment id by scanning structured kind dirs.
    Phase 1 storage uses kind subdirectories with sharded two-char prefix.
    """
    service = get_media_service()
    search_dirs = [service.images_dir, service.audio_dir, service.files_dir]
    for base in search_dirs:
        pattern = f"{attachment_id}_*"
        matches = list(base.rglob(pattern))
        if matches:
            return FileResponse(path=matches[0])
    raise HTTPException(status_code=404, detail="Not found")

@router.get("/list/{kind}")
async def list_kind(kind: str) -> Dict:
    if kind not in {"images", "audio", "files"}:
        raise HTTPException(status_code=400, detail="Invalid kind")
    service = get_media_service()
    return {"files": service.list_kind(kind)}

@router.post("/export")
async def export_media(body: Dict = Body(...)):
    """Copy a stored media attachment to a destination path in the workspace.

    Body params:
      attachment_id: str (id returned from /media/upload)
      dest_path: str (absolute or relative path within workspace root)

    This avoids the client re-uploading bytes after initial media storage.
    """
    attachment_id = body.get('attachment_id')
    dest_path = body.get('dest_path')
    
    print(f"🔧 [BACKEND EXPORT DEBUG] Received request:")
    print(f"   attachment_id: {attachment_id}")
    print(f"   dest_path: '{dest_path}'")
    print(f"   body: {body}")
    
    if not attachment_id or dest_path is None:
        raise HTTPException(status_code=400, detail="attachment_id and dest_path required")

    service = get_media_service()

    # Resolve attachment file path (reuse logic similar to get_file)
    search_dirs = [service.images_dir, service.audio_dir, service.files_dir]
    source_path: Path | None = None
    for base in search_dirs:
        pattern = f"{attachment_id}_*"
        matches = list(base.rglob(pattern))
        if matches:
            source_path = matches[0]
            break
    if not source_path or not source_path.exists():
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Workspace root should be the parent of the backend directory, not the backend directory itself
    # Backend runs from /home/penthoy/icotes/backend/, but workspace is /home/penthoy/icotes/
    current_dir = Path(os.getcwd()).resolve()
    if current_dir.name == 'backend':
        workspace_root = current_dir.parent
    else:
        workspace_root = current_dir
    logger.info(f"[DEBUG] Export request: attachment_id={attachment_id}, dest_path='{dest_path}', workspace_root={workspace_root}, current_dir={current_dir}")
    
    # Treat incoming dest_path as workspace-relative unless it's explicitly absolute
    if os.path.isabs(dest_path):
        dest_path_full = Path(dest_path).resolve()
    else:
        dest_path_full = (workspace_root / dest_path).resolve()
    
    logger.info(f"[DEBUG] Resolved dest_path_full={dest_path_full}")

    # Ensure destination within workspace
    try:
        dest_path_full.relative_to(workspace_root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Destination path outside workspace root")

    # If dest_path ends with '/', treat as directory -> append original filename (without uuid prefix)
    if dest_path.endswith('/') or dest_path_full.is_dir():
        # Extract original filename part after first underscore
        original_name = source_path.name.split('_', 1)[-1]
        dest_path_full = dest_path_full / original_name

    # Create parent directories
    dest_path_full.parent.mkdir(parents=True, exist_ok=True)

    try:
        shutil.copy2(source_path, dest_path_full)
        logger.info(f"[DEBUG] Successfully copied {source_path} to {dest_path_full}")
    except Exception as e:
        logger.exception("Failed exporting media attachment")
        raise HTTPException(status_code=500, detail="Export failed")

    rel = dest_path_full.relative_to(workspace_root).as_posix()
    return {"success": True, "path": rel}

@router.delete("/{kind}/{filename}")
async def delete_kind_file(kind: str, filename: str):
    if kind not in {"images", "audio", "files"}:
        raise HTTPException(status_code=400, detail="Invalid kind")
    service = get_media_service()
    result = service.delete_kind_file(kind, filename)
    if not result.get('success') and result.get('reason') == 'not_found':
        raise HTTPException(status_code=404, detail="Not found")
    return result

@router.post("/zip")
async def create_zip(body: Dict = Body(...)):
    paths: List[str] = body.get('paths') or []
    if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
        raise HTTPException(status_code=400, detail="paths must be list[str]")
    service = get_media_service()
    data = service.build_zip(paths)
    return StreamingResponse(io.BytesIO(data), media_type='application/zip', headers={
        'Content-Disposition': 'attachment; filename="media_bundle.zip"'
    })
