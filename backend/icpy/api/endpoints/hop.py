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
    c = service.update_credential(cred_id, payload.model_dump(exclude_unset=True))
    if not c:
        raise HTTPException(status_code=404, detail="Credential not found")
    try:
        broker = await get_message_broker()
        await broker.publish('hop.credentials.updated', {"credential": c})
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
        # Broadcast status change and session list update
        try:
            broker = await get_message_broker()
            await broker.publish('hop.status', session.__dict__)
            # Publish updated session list
            sessions = service.list_sessions()
            await broker.publish('hop.sessions', {"sessions": sessions})
        except Exception:
            pass
        return session.__dict__
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
    try:
        broker = await get_message_broker()
        await broker.publish('hop.status', session.__dict__)
    except Exception:
        pass
    return session.__dict__


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
        # Broadcast status change
        try:
            broker = await get_message_broker()
            await broker.publish('hop.status', session.__dict__)
            # Also publish updated session list
            sessions = service.list_sessions()
            await broker.publish('hop.sessions', {"sessions": sessions})
        except Exception:
            pass
        return session.__dict__
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Hop failed: {e}")
        raise HTTPException(status_code=500, detail=f"Hop failed: {str(e)}")
