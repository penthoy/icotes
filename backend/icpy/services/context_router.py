"""
Context Router Service

Phase 3: Introduce a centralized router which resolves service implementations
for the current execution context (local vs remote hop). For now, this returns
the existing local services so API behavior remains unchanged. In later phases
it will return remote-capable facades (SFTP FS, remote PTY) when hop is active.

Contracts:
- get_filesystem(): returns a FileSystemService-like object for current context
- get_terminal_service(): returns a TerminalService-like object for current context
- get_context(): returns the current hop session summary

This module depends on HopService for status and will evolve to manage remote
adapters. It keeps a minimal footprint for safe integration.
"""

from __future__ import annotations

import logging
from typing import Optional

from .hop_service import get_hop_service, HopService, HopSession, ASYNCSSH_AVAILABLE
from .filesystem_service import get_filesystem_service, FileSystemService
from .terminal_service import get_terminal_service, TerminalService
from .remote_fs_adapter import get_remote_filesystem_adapter, RemoteFileSystemAdapter  # Phase 5

logger = logging.getLogger(__name__)

# Phase 6 import - conditional to avoid circular dependency
try:
    from .remote_terminal_manager import get_remote_terminal_manager, RemoteTerminalManager
    REMOTE_TERMINAL_AVAILABLE = True
except ImportError:
    RemoteTerminalManager = None  # type: ignore
    REMOTE_TERMINAL_AVAILABLE = False
    logger.debug("[ContextRouter] RemoteTerminalManager not available")


class ContextRouter:
    """Resolve backend services for the active context (local or remote).

    Phase 3 implementation: always return local services, but expose the
    indirection points so callers don't need to change when remote support
    arrives in later phases.
    """

    def __init__(self) -> None:
        self._hop_service: Optional[HopService] = None
        self._local_fs: Optional[FileSystemService] = None
        self._local_term: Optional[TerminalService] = None

    async def _ensure_dependencies(self):
        if self._hop_service is None:
            self._hop_service = await get_hop_service()
        if self._local_fs is None:
            self._local_fs = await get_filesystem_service()
        if self._local_term is None:
            self._local_term = await get_terminal_service()

    async def get_filesystem(self) -> FileSystemService:
        """Return a filesystem interface for the active context.

        For now, returns the local FileSystemService. In Phase 5, this will
        return an SFTP-backed adapter when hop is connected.
        """
        await self._ensure_dependencies()
        try:
            session = self._hop_service.status() if self._hop_service else None
            # Use method calls instead of getattr to ensure properties work correctly in Docker
            active_conn = self._hop_service.get_active_connection() if self._hop_service else None
            active_sftp = self._hop_service.get_active_sftp() if self._hop_service else None
            has_conn = active_conn is not None
            has_sftp = active_sftp is not None
            # Only use remote when SSH connection object is present, session is connected, and SFTP is available
            if (
                session
                and session.status == "connected"
                and session.contextId
                and session.contextId != "local"
                and has_conn
                and has_sftp
            ):
                # Return a transient remote adapter bound to current hop connection
                remote = await get_remote_filesystem_adapter()
                return remote  # type: ignore[return-value]
            else:
                # Log only critical failures for debugging
                if session and session.status == 'connected' and session.contextId != 'local' and (not has_conn or not has_sftp):
                    logger.warning(
                        f"[ContextRouter] Remote FS unavailable despite connected status: "
                        f"context={session.contextId}, conn={has_conn}, sftp={has_sftp}"
                    )
        except Exception as e:
            logger.warning(f"[ContextRouter] Remote FS unavailable, falling back to local: {e}")
        return self._local_fs  # type: ignore[return-value]

    # -------- Namespace-aware helpers --------
    async def resolve_namespace_id(self, ns: str) -> str:
        """Resolve a human-friendly namespace (e.g., credential name like 'hop1')
        to an actual context id. If ns directly matches a context id, it's returned.
        Falls back to 'local' when not found.

        Preference order when multiple matches exist:
        - Exact context id match
        - Active session with matching credentialName
        - Any connected session with matching credentialName
        - Any session with matching credentialName
        """
        await self._ensure_dependencies()
        if not ns:
            return 'local'
        if ns == 'local':
            return 'local'
        try:
            # Fast path: exact context id match
            sessions = self._hop_service.list_sessions() if self._hop_service else []
            for s in sessions:
                cid = s.get('contextId') or s.get('context_id')
                if cid == ns:
                    return cid
            # Match by credentialName
            active_cid = None
            connected_cid = None
            any_cid = None
            for s in sessions:
                cred_name = s.get('credentialName') or s.get('credential_name')
                cid = s.get('contextId') or s.get('context_id')
                if not cred_name or not cid:
                    continue
                if cred_name == ns:
                    any_cid = any_cid or cid
                    if s.get('status') == 'connected':
                        connected_cid = connected_cid or cid
                    if s.get('active'):
                        active_cid = cid
                        break
            return active_cid or connected_cid or any_cid or 'local'
        except Exception as e:
            logger.debug(f"[ContextRouter] resolve_namespace_id fallback to local for ns={ns}: {e}")
            return 'local'

    async def parse_namespaced_path(self, raw: str) -> tuple[str, str]:
        """Parse a namespaced path of the form '<namespace>:/abs/path'.

        Returns a tuple (context_id, abs_path). If no namespace is present,
        returns (active_context_id, raw_or_resolved_path).
        """
        await self._ensure_dependencies()
        if not raw:
            return (self._hop_service.status().contextId if self._hop_service else 'local', '/')
        # Detect pattern like 'ns:/path' but exclude Windows drive letters
        idx = raw.find(':/')
        if idx > 0:
            ns = raw[:idx]
            # Skip if this looks like a Windows drive letter (single char)
            if idx == 1 and ns.isalpha():
                # This is a Windows path like C:/, not a namespace
                ctx = self._hop_service.status().contextId if self._hop_service else 'local'
                return (ctx, raw)
            
            path = raw[idx+2:] or '/'
            # Normalize multiple slashes
            if not path.startswith('/'):
                path = '/' + path
            resolved = await self.resolve_namespace_id(ns)
            return (resolved, path)
        # No namespace; use active context
        ctx = self._hop_service.status().contextId if self._hop_service else 'local'
        # Ensure absolute path default
        path = raw if raw.startswith('/') else ('/' + raw)
        return (ctx, path)

    async def get_filesystem_for_namespace(self, context_id: str) -> FileSystemService:
        """Return filesystem bound to a specific context id.

        - 'local' returns the local FileSystemService
        - any other returns a RemoteFileSystemAdapter bound to that context if available
        Fallback to local if remote not connected.
        """
        await self._ensure_dependencies()
        if not context_id or context_id == 'local':
            return self._local_fs  # type: ignore[return-value]
        try:
            # Ensure that the requested context exists and is connected
            session = self._hop_service._sessions.get(context_id) if self._hop_service else None  # type: ignore[attr-defined]
            sftp = self._hop_service.get_sftp_for_context(context_id) if self._hop_service else None
            if session and session.status == 'connected' and sftp is not None:
                return await get_remote_filesystem_adapter(context_id)
        except Exception as e:
            logger.debug(f"[ContextRouter] get_filesystem_for_namespace fallback to local for {context_id}: {e}")
        return self._local_fs  # type: ignore[return-value]

    async def get_terminal_service(self):
        """Return a terminal service for the active context.

        Phase 6 complete: Returns RemoteTerminalManager when hop is connected,
        otherwise returns local TerminalService.
        
        Returns:
            TerminalService or RemoteTerminalManager - both have compatible
            connect_terminal() interface for WebSocket connections.
        """
        await self._ensure_dependencies()
        
        # Check if we should use remote terminal
        if REMOTE_TERMINAL_AVAILABLE and ASYNCSSH_AVAILABLE:
            try:
                session = self._hop_service.status() if self._hop_service else None
                # Use method call instead of getattr to ensure properties work correctly in Docker
                active_conn = self._hop_service.get_active_connection() if self._hop_service else None
                has_conn = active_conn is not None
                
                # Only use remote when SSH connection is active
                if (
                    session
                    and session.status == "connected"
                    and session.contextId
                    and session.contextId != "local"
                    and has_conn
                ):
                    # Return remote terminal manager
                    remote_term = await get_remote_terminal_manager()
                    return remote_term
                else:
                    # Log only critical failures for debugging
                    if session and session.status == 'connected' and session.contextId != 'local' and not has_conn:
                        logger.warning(
                            f"[ContextRouter] Remote terminal unavailable despite connected status: "
                            f"context={session.contextId}, conn={has_conn}"
                        )
            except Exception as e:
                logger.warning(f"[ContextRouter] Remote terminal check failed, using local: {e}")
        
        # Return local terminal service
        logger.debug("[ContextRouter] Using local TerminalService")
        return self._local_term  # type: ignore[return-value]

    async def get_context(self) -> HopSession:
        await self._ensure_dependencies()
        return self._hop_service.status()  # type: ignore[return-value]


_context_router_singleton: Optional[ContextRouter] = None


async def get_context_router() -> ContextRouter:
    global _context_router_singleton
    if _context_router_singleton is None:
        _context_router_singleton = ContextRouter()
    return _context_router_singleton
