"""
Hop API endpoints

Exposes REST endpoints for:
- Credentials CRUD
- Key upload
- Connect / Disconnect / Status

Implements Phase 1 and Phase 2 functionality from ssh_hop_plan.md
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ...services.hop_service import get_hop_service, ASYNCSSH_AVAILABLE
from ...core.message_broker import get_message_broker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hop", tags=["hop"])


class SSHCredentialCreate(BaseModel):
    name: str
    host: str
    port: int = 22
    username: str = ""
    auth: str = Field(default="password", pattern="^(password|privateKey|agent)$")
    privateKeyId: Optional[str] = None
    defaultPath: Optional[str] = None


class SSHCredentialUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    auth: Optional[str] = Field(default=None, pattern="^(password|privateKey|agent)$")
    privateKeyId: Optional[str] = None
    defaultPath: Optional[str] = None


class HopConnectRequest(BaseModel):
    credentialId: str
    password: Optional[str] = None
    passphrase: Optional[str] = None


@router.post("/credentials")
async def create_credential(payload: SSHCredentialCreate):
    service = await get_hop_service()
    try:
        created = service.create_credential(payload.model_dump())
        # Broadcast event for UI refresh
        try:
            broker = await get_message_broker()
            await broker.publish('hop.credentials.created', {"credential": created})
        except Exception:
            pass
        return created
    except KeyError:
        raise HTTPException(status_code=400, detail="Missing required fields")
    except Exception as e:
        logger.error(f"Failed to create credential: {e}")
        raise HTTPException(status_code=500, detail="Create credential failed")


@router.get("/credentials")
async def list_credentials():
    service = await get_hop_service()
    return service.list_credentials()


@router.get("/credentials/{cred_id}")
async def get_credential(cred_id: str):
    service = await get_hop_service()
    c = service.get_credential(cred_id)
    if not c:
        raise HTTPException(status_code=404, detail="Credential not found")
    return c


@router.put("/credentials/{cred_id}")
async def update_credential(cred_id: str, payload: SSHCredentialUpdate):
    service = await get_hop_service()
    updates = payload.model_dump(exclude_unset=True)
    # Track whether defaultPath is being changed so we can reflect it in any active session
    default_path_changed = 'defaultPath' in updates
    c = service.update_credential(cred_id, updates)
    if not c:
        raise HTTPException(status_code=404, detail="Credential not found")
    try:
        broker = await get_message_broker()
        await broker.publish('hop.credentials.updated', {"credential": c})
        # If this credential is currently connected (there may be an active session for it),
        # and defaultPath changed, update the session cwd live so the UI (Explorer) can hop correctly next time.
        if default_path_changed:
            # Find session with matching credentialId/contextId
            try:
                sessions = service.list_sessions()
                updated_any = False
                for s in sessions:
                    if s.get('contextId') == cred_id or s.get('credentialId') == cred_id:
                        # Only update if still connected
                        if s.get('status') == 'connected':
                            # Mutate the underlying service session object
                            # service._sessions is internal; safe targeted update for live refresh benefit
                            svc_session = service._sessions.get(s.get('contextId'))  # type: ignore[attr-defined]
                            if svc_session:
                                svc_session.cwd = c.get('defaultPath') or svc_session.cwd or '/'
                                updated_any = True
                if updated_any:
                    # Broadcast updated status for active context if affected
                    active = service.status()
                    await broker.publish('hop.status', active.__dict__)
                    # Also broadcast full session list (reflects cwd change)
                    sessions = service.list_sessions()
                    await broker.publish('hop.sessions', {"sessions": sessions})
            except Exception:
                pass
    except Exception:
        pass
    return c


@router.delete("/credentials/{cred_id}")
async def delete_credential(cred_id: str):
    service = await get_hop_service()
    if not service.delete_credential(cred_id):
        raise HTTPException(status_code=404, detail="Credential not found")
    try:
        broker = await get_message_broker()
        await broker.publish('hop.credentials.deleted', {"id": cred_id})
    except Exception:
        pass
    return {"success": True}


@router.post("/keys")
async def upload_key(file: UploadFile = File(...)):
    service = await get_hop_service()
    try:
        content = await file.read()
        key_id = service.store_private_key(content)
        return {"keyId": key_id}
    except Exception as e:
        logger.error(f"Key upload failed: {e}")
        raise HTTPException(status_code=500, detail="Key upload failed")


@router.post("/connect")
async def connect(payload: HopConnectRequest):
    service = await get_hop_service()
    try:
        logger.info(f"[HopAPI] Connect requested for credential={payload.credentialId} (asyncssh_available={ASYNCSSH_AVAILABLE})")
        session = await service.connect(payload.credentialId, password=payload.password, passphrase=payload.passphrase)
        logger.info(f"[HopAPI] Connect result: status={session.status} host={session.host} user={session.username} error={session.lastError}")
        # Enrich payload with credentialName for friendly display on initial connect
        payload_with_name = session.__dict__.copy()
        try:
            if getattr(session, 'credentialId', None):
                cred = service.get_credential(session.credentialId)  # type: ignore[attr-defined]
                if cred:
                    payload_with_name['credentialName'] = cred.get('name')
        except Exception:
            pass

        # Broadcast status change and session list update
        try:
            broker = await get_message_broker()
            await broker.publish('hop.status', payload_with_name)
            # Publish updated session list
            sessions = service.list_sessions()
            await broker.publish('hop.sessions', {"sessions": sessions})
        except Exception:
            pass
        return payload_with_name
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Connect failed: {e}")
        # service will have set status/error accordingly; return status
        return service.status().__dict__


@router.post("/disconnect")
async def disconnect(context_id: Optional[str] = Body(None, embed=True)):
    """Disconnect a specific context or the active context if none specified.
    
    Args:
        context_id: Optional context ID to disconnect. If not provided, disconnects active context.
    """
    service = await get_hop_service()
    logger.info(f"[HopAPI] Disconnect requested for context={context_id or 'active'}")
    session = await service.disconnect(context_id)
    try:
        broker = await get_message_broker()
        await broker.publish('hop.status', session.__dict__)
        # Also publish session list update
        sessions = service.list_sessions()
        await broker.publish('hop.sessions', {"sessions": sessions})
    except Exception:
        pass
    return session.__dict__


@router.get("/status")
async def status():
    service = await get_hop_service()
    session = service.status()
    logger.info(f"[HopAPI] Status requested: status={session.status} contextId={session.contextId} host={session.host}")
    # Enrich with credentialName for friendly display in UI
    payload = session.__dict__.copy()
    try:
        if getattr(session, 'credentialId', None):
            cred = service.get_credential(session.credentialId)  # type: ignore[attr-defined]
            if cred:
                payload['credentialName'] = cred.get('name')
    except Exception:
        pass
    try:
        broker = await get_message_broker()
        await broker.publish('hop.status', payload)
    except Exception:
        pass
    return payload


@router.get("/health")
async def check_health():
    """Phase 8: Check connection health without affecting status."""
    service = await get_hop_service()
    quality = await service.check_connection_health()
    return {"quality": quality}


@router.get("/sessions")
async def list_sessions():
    """List all active sessions including local."""
    service = await get_hop_service()
    sessions = service.list_sessions()
    return {"sessions": sessions}


class HopToRequest(BaseModel):
    contextId: str

class SendFilesRequest(BaseModel):
    target_context_id: str
    paths: List[str]
    source_context_id: Optional[str] = None
    common_prefix: Optional[str] = None

@router.post("/send-files")
async def send_files(payload: SendFilesRequest):
    """Send (copy) files/folders from a source context to a target context.

    Behaviors:
    - Supports local⇄remote (when SFTP available) and local→local (noop safeguard)
    - Preserves relative layout using provided common_prefix when possible
    - Creates intermediate directories
    - Returns lists of created paths and per-path errors (does not abort on first error)
    """
    import os, posixpath, stat as statmod

    service = await get_hop_service()
    hop = service

    src_ctx = payload.source_context_id or hop.status().contextId
    dst_ctx = payload.target_context_id

    if not payload.paths:
        logger.info(f"[/api/hop/send-files] No paths provided (src={src_ctx} dst={dst_ctx})")
        return {"success": True, "message": "No paths provided", "created": [], "errors": []}
    if dst_ctx == src_ctx:
        logger.info(f"[/api/hop/send-files] Source and target identical (ctx={src_ctx})")
        return {"success": True, "message": "Source and target context identical; nothing to do", "created": [], "errors": []}

    # Workspace root resolver
    def _workspace_root() -> str:
        return os.environ.get('WORKSPACE_ROOT') or os.environ.get('VITE_WORKSPACE_ROOT') or '/'

    # Resolve default destination base path for context
    def _cred_default_path(ctx_id: str) -> str:
        if ctx_id == 'local':
            return _workspace_root()
        cred = hop.get_credential(ctx_id)
        if cred and cred.get('defaultPath'):
            return cred['defaultPath']
        ses = hop._sessions.get(ctx_id)  # type: ignore[attr-defined]
        if ses and getattr(ses, 'cwd', None):
            return getattr(ses, 'cwd')
        return '/'

    dest_base = _cred_default_path(dst_ctx).rstrip('/') or '/'
    common_prefix = (payload.common_prefix or '').rstrip('/')
    if common_prefix and any('..' in p for p in common_prefix.split('/')):
        logger.warning(f"[/api/hop/send-files] Ignoring suspicious common_prefix={common_prefix!r}")
        common_prefix = ''

    # SFTP handles (None if local or not connected / feature unavailable)
    sftp_src = hop._sftp_clients.get(src_ctx) if src_ctx != 'local' else None  # type: ignore[attr-defined]
    sftp_dst = hop._sftp_clients.get(dst_ctx) if dst_ctx != 'local' else None  # type: ignore[attr-defined]

    # Guard: remote operations require SFTP client
    errors: List[str] = []
    created: List[str] = []
    if src_ctx != 'local' and not sftp_src:
        msg = f"Source context {src_ctx} not available (no SFTP)"
        logger.warning(f"[/api/hop/send-files] {msg}")
        return {"success": False, "created": [], "errors": [msg]}
    if dst_ctx != 'local' and not sftp_dst:
        msg = f"Target context {dst_ctx} not available (no SFTP)"
        logger.warning(f"[/api/hop/send-files] {msg}")
        return {"success": False, "created": [], "errors": [msg]}

    def _rel_for(path: str) -> str:
        """Compute relative path while filtering out . and .. for security"""
        if common_prefix and path.startswith(common_prefix + '/'):
            rel = path[len(common_prefix)+1:]
        else:
            rel = posixpath.basename(path)
        # Security: remove any . or .. components to prevent path traversal
        parts = [p for p in rel.split('/') if p and p not in ('.', '..')]
        return '/'.join(parts)

    async def copy_file(src_path: str, rel_path: str):
        try:
            # Security: validate rel_path doesn't contain path traversal
            if '..' in rel_path or rel_path.startswith('/'):
                logger.warning(f"[/api/hop/send-files] Rejecting suspicious rel_path: {rel_path}")
                errors.append(f"{src_path}: Invalid relative path")
                return
            
            dest_path = posixpath.normpath(f"{dest_base}/{rel_path}")
            
            # Skip if destination already exists with non-zero size
            # This prevents overwriting good local files when remote is unavailable
            if dst_ctx == 'local' and os.path.exists(dest_path):
                try:
                    size = os.path.getsize(dest_path)
                    if size > 0:
                        logger.debug(f"[/api/hop/send-files] Skipping {dest_path} - already exists with size {size}")
                        created.append(dest_path)  # Count as successful (no-op)
                        return
                except Exception:
                    pass  # If we can't check size, proceed with transfer
            
            # Read bytes
            if sftp_src:
                async with sftp_src.open(src_path, 'rb') as f:  # type: ignore
                    data = await f.read()
            else:
                with open(src_path, 'rb') as f:  # type: ignore
                    data = f.read()
            # Ensure directory exists
            dest_dir = posixpath.dirname(dest_path)
            if sftp_dst:
                segments = [seg for seg in dest_dir.strip('/').split('/') if seg]
                cur = ''
                for seg in segments:
                    cur = f"{cur}/{seg}" if cur else f"/{seg}"
                    try:
                        await sftp_dst.stat(cur)  # type: ignore
                    except Exception:
                        try:
                            await sftp_dst.mkdir(cur)  # type: ignore
                        except Exception:
                            pass
            else:
                os.makedirs(dest_dir, exist_ok=True)
            # Write bytes
            if sftp_dst:
                async with sftp_dst.open(dest_path, 'wb') as f:  # type: ignore
                    await f.write(data)
            else:
                with open(dest_path, 'wb') as f:  # type: ignore
                    f.write(data)
            created.append(dest_path)
        except Exception as e:
            logger.warning(f"[/api/hop/send-files] copy_file failed src={src_path} rel={rel_path}: {e}")
            errors.append(f"{src_path}: {e}")

    async def recurse_path(src_path: str, rel_prefix: str = ''):
        try:
            if sftp_src:
                st = await sftp_src.stat(src_path)  # type: ignore
                # AsyncSSH SFTPAttrs uses 'permissions' instead of 'st_mode'
                mode = getattr(st, 'st_mode', None) or getattr(st, 'permissions', 0)
                is_dir = statmod.S_ISDIR(mode)
            else:
                is_dir = os.path.isdir(src_path)  # type: ignore
        except Exception as e:
            logger.warning(f"[/api/hop/send-files] stat failed path={src_path}: {e}")
            errors.append(f"stat failed: {src_path}: {e}")
            return
        if not is_dir:
            await copy_file(src_path, rel_prefix)
            return
        # Directory branch
        try:
            if sftp_src:
                names = await sftp_src.listdir(src_path)  # type: ignore
            else:
                names = os.listdir(src_path)  # type: ignore
            # Ensure directory exists at destination
            if rel_prefix:
                dir_path = posixpath.normpath(f"{dest_base}/{rel_prefix}")
                if sftp_dst:
                    try:
                        await sftp_dst.mkdir(dir_path)  # type: ignore
                    except Exception:
                        pass
                else:
                    os.makedirs(dir_path, exist_ok=True)
            for name in names:
                child_src = src_path.rstrip('/') + '/' + name
                child_rel = (rel_prefix.rstrip('/') + '/' + name).lstrip('/') if rel_prefix else name
                await recurse_path(child_src, child_rel)
        except Exception as e:
            logger.warning(f"[/api/hop/send-files] recurse list failed path={src_path}: {e}")
            errors.append(f"list failed: {src_path}: {e}")

    logger.info(f"[/api/hop/send-files] Begin transfer src={src_ctx} dst={dst_ctx} count={len(payload.paths)} dest_base={dest_base} common_prefix={common_prefix!r}")
    for p in payload.paths:
        rel = _rel_for(p)
        logger.debug(f"[/api/hop/send-files] processing path={p} rel={rel}")
        await recurse_path(p, rel)

    try:
        broker = await get_message_broker()
        if created:
            await broker.publish('hop.send_files.completed', {"count": len(created), "target": dst_ctx})
    except Exception:
        pass

    logger.info(f"[/api/hop/send-files] Completed src={src_ctx} dst={dst_ctx} created={len(created)} errors={len(errors)} dest_base={dest_base}")
    if errors:
        logger.warning(f"[/api/hop/send-files] Errors encountered: {errors}")
    return {"success": True, "created": created, "errors": errors}


@router.post("/hop")
async def hop_to(payload: HopToRequest):
    """Switch the active context to a different session.
    
    Args:
        payload: Contains the contextId to hop to
    
    Returns:
        The newly active session
    """
    service = await get_hop_service()
    try:
        logger.info(f"[HopAPI] Hop requested to context={payload.contextId}")
        session = await service.hop_to(payload.contextId)
        logger.info(f"[HopAPI] Hopped to {payload.contextId}, status={session.status}")
        # Enrich with credentialName for friendly display in UI
        session_payload = session.__dict__.copy()
        try:
            if getattr(session, 'credentialId', None):
                cred = service.get_credential(session.credentialId)  # type: ignore[attr-defined]
                if cred:
                    session_payload['credentialName'] = cred.get('name')
        except Exception:
            pass
        # Broadcast status change
        try:
            broker = await get_message_broker()
            await broker.publish('hop.status', session_payload)
            # Also publish updated session list
            sessions = service.list_sessions()
            await broker.publish('hop.sessions', {"sessions": sessions})
        except Exception:
            pass
        return session_payload
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Hop failed: {e}")
        raise HTTPException(status_code=500, detail=f"Hop failed: {str(e)}")
