"""
Context-aware helper functions for agent tools

Phase 7: These helpers ensure tools work with the active hop context,
routing to local or remote filesystem/terminal as appropriate.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def get_contextual_filesystem():
    """
    Get filesystem service appropriate for the current hop context.
    
    When hopped to a remote server, returns RemoteFileSystemAdapter.
    Otherwise returns local FileSystemService.
    
    This enables tools to transparently work on remote files when hopped.
    """
    try:
        from icpy.services.context_router import get_context_router
        router = await get_context_router()
        fs = await router.get_filesystem()
        logger.debug(f"[ContextHelpers] Using filesystem: {type(fs).__name__}")
        return fs
    except Exception as e:
        logger.warning(f"[ContextHelpers] ContextRouter unavailable, falling back to local FS: {e}")
        # Fallback to local filesystem
        from icpy.services.filesystem_service import get_filesystem_service
        return await get_filesystem_service()


async def get_contextual_terminal():
    """
    Get terminal service appropriate for the current hop context.
    
    Phase 6 Complete: When hopped to a remote server, returns RemoteTerminalManager.
    Otherwise returns local TerminalService.
    """
    try:
        from icpy.services.context_router import get_context_router
        router = await get_context_router()
        terminal = await router.get_terminal_service()
        logger.debug(f"[ContextHelpers] Using terminal: {type(terminal).__name__}")
        return terminal
    except Exception as e:
        logger.warning(f"[ContextHelpers] ContextRouter unavailable, falling back to local terminal: {e}")
        # Fallback to local terminal
        from icpy.services.terminal_service import get_terminal_service
        return await get_terminal_service()


async def get_current_context() -> dict:
    """
    Get information about the current execution context (local vs remote hop).
    
    Returns:
        dict with keys: contextId, status, host, cwd, etc.
        If no hop active, returns {"contextId": "local", "status": "disconnected"}
    """
    try:
        from icpy.services.context_router import get_context_router
        from icpy.services.path_utils import _friendly_namespace_for_context

        router = await get_context_router()
        session = await router.get_context()
        cwd = getattr(session, 'cwd', '/')

        # Resolve a friendly namespace label derived from active sessions and hop config.
        # No hardcoded fallbacks: prefer credential/config alias; finally fall back to contextId.
        try:
            namespace = await _friendly_namespace_for_context(session.contextId)
        except Exception:
            namespace = 'local' if session.contextId == 'local' else session.contextId

        return {
            "contextId": session.contextId,
            "status": session.status,
            "host": getattr(session, 'host', None),
            "port": getattr(session, 'port', None),
            "username": getattr(session, 'username', None),
            "credentialName": getattr(session, 'credentialName', None),
            "namespace": namespace,
            "cwd": cwd,
            # Provide a canonical workspaceRoot alias to reduce ambiguity in tools/prompts
            "workspaceRoot": cwd,
        }
    except Exception as e:
        logger.warning(f"[ContextHelpers] Failed to get context: {e}")
        return {"contextId": "local", "status": "disconnected"}
