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

from .hop_service import get_hop_service, HopService, HopSession
from .filesystem_service import get_filesystem_service, FileSystemService
from .terminal_service import get_terminal_service, TerminalService

logger = logging.getLogger(__name__)


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
        # TODO(Phase 5): if hop connected -> return remote FS adapter
        return self._local_fs  # type: ignore[return-value]

    async def get_terminal_service(self) -> TerminalService:
        """Return a terminal service for the active context.

        For now, returns the local TerminalService. In Phase 6, this will
        provide a remote PTY-backed terminal when hop is connected.
        """
        await self._ensure_dependencies()
        # TODO(Phase 6): if hop connected -> return remote terminal adapter
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
