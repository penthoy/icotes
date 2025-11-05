"""
Unified path utilities for hop-aware path formatting and display metadata.

This module centralizes logic for producing namespace-aware path strings and
structured path information used by agent tools and UI components.

Contracts:
- format_namespaced_path(context_id: str, abs_path: str, router: ContextRouter | None) -> str
- get_display_path_info(path: str, router: ContextRouter | None) -> dict

Notes:
- Namespaces use friendly names when available: "local" for local context,
  and the credentialName for remote sessions (e.g., "hop1"). Falls back to
  the raw context_id if a friendly name cannot be determined.
- Handles Windows drive-letter paths (e.g., C:/foo) as plain paths, not
  namespaces.
"""

from __future__ import annotations

import os
from typing import Optional, Dict, Any

from .context_router import get_context_router, ContextRouter
from .hop_service import get_hop_service


async def _friendly_namespace_for_context(context_id: str) -> str:
    """Return a user-friendly namespace label for a given context id.

    Resolution order (no hardcoded aliases):
    1) If local -> "local"
    2) Active session's credentialName (from HopService)
    3) Host alias from hop config (.icotes/hop/config) matched by icotes-meta id
    4) Fall back to the context_id (UUID) itself
    """
    import logging
    import json
    logger = logging.getLogger(__name__)

    if not context_id or context_id == "local":
        return "local"

    # 1) Check active hop sessions for credentialName
    try:
        hop = await get_hop_service()
        sessions = hop.list_sessions()
        logger.debug(f"[PathUtils] Resolving namespace for context_id={context_id}")
        for s in sessions:
            cid = s.get("contextId") or s.get("context_id")
            if cid == context_id:
                ns = s.get("credentialName") or s.get("credential_name")
                if isinstance(ns, str) and ns.strip():
                    logger.debug(f"[PathUtils] Using session credentialName={ns}")
                    return ns
    except Exception as e:
        logger.warning(f"[PathUtils] HopService unavailable while resolving namespace: {e}")

    # 2) Parse hop config to map icotes-meta id -> Host alias
    try:
        # Locate repo/workspace to find .icotes/hop/config
        services_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up 4 levels from backend/icpy/services -> repo root
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(services_dir))))
        # Prefer WORKSPACE_ROOT if set
        workspace_root = os.environ.get('WORKSPACE_ROOT') or os.path.join(repo_root, 'workspace')
        config_path = os.path.join(workspace_root, '.icotes', 'hop', 'config')

        if os.path.exists(config_path):
            logger.debug(f"[PathUtils] Reading hop config: {config_path}")
            current_alias = None
            with open(config_path, 'r', encoding='utf-8') as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line:
                        continue
                    if line.lower().startswith('host '):
                        # e.g., "Host hop1"
                        parts = line.split(None, 1)
                        current_alias = parts[1].strip() if len(parts) > 1 else None
                        continue
                    if line.startswith('# icotes-meta:'):
                        # e.g., # icotes-meta: {"id": "...", ...}
                        try:
                            meta_str = line.split(':', 1)[1].strip()
                            meta = json.loads(meta_str)
                            meta_id = meta.get('id')
                            if meta_id and meta_id == context_id and current_alias:
                                logger.debug(f"[PathUtils] Using hop alias from config: {current_alias}")
                                return current_alias
                        except Exception:
                            # Best-effort parsing; continue scanning
                            continue
        else:
            logger.debug(f"[PathUtils] Hop config not found at {config_path}")
    except Exception as e:
        logger.warning(f"[PathUtils] Failed to parse hop config for namespace resolution: {e}")

    # 3) Last resort: return the context_id itself (no invented alias)
    logger.debug(f"[PathUtils] Falling back to contextId as namespace: {context_id}")
    return context_id


async def format_namespaced_path(
    context_id: str,
    abs_path: str,
    router: Optional[ContextRouter] = None,
) -> str:
    """Format a namespaced path string "<namespace>:<absolute_path>".

    Args:
        context_id: The internal context id ("local" or a remote session id)
        abs_path: An absolute path string. If not absolute, it will be normalized.
        router: Optional ContextRouter (unused currently but reserved for future)

    Returns:
        A string like "local:/workspace/file.txt" or "hop1:/home/user/file.txt"
    """
    # Normalize path to absolute; allow Windows drives (e.g., C:/foo)
    if not abs_path:
        abs_path = "/"
    # Preserve Windows drive absolute paths as-is; otherwise ensure leading '/'
    if not (len(abs_path) >= 3 and abs_path[1:3] == ":/" and abs_path[0].isalpha()):
        if not abs_path.startswith("/"):
            abs_path = "/" + abs_path

    namespace = await _friendly_namespace_for_context(context_id)
    return f"{namespace}:{abs_path}"


async def get_display_path_info(
    path: str,
    router: Optional[ContextRouter] = None,
) -> Dict[str, Any]:
    """Return structured metadata for displaying a path with namespace context.

    Parses the input which may be namespaced (e.g., "hop1:/path") or plain
    absolute/relative path. Uses the active context when no namespace is
    specified and normalizes the absolute path.

    Returns:
        dict with keys:
            - formatted_path: "<namespace>:<absolute_path>"
            - namespace: friendly namespace label ("local" or credentialName)
            - context_id: internal context id ("local" or remote id)
            - absolute_path: normalized absolute path on target filesystem
            - is_remote: bool
            - display_name: same as formatted_path for now
    """
    router = router or await get_context_router()

    # Empty/None path -> root
    raw = path or "/"

    # Let router handle namespaced parsing and Windows edge cases
    context_id, abs_path = await router.parse_namespaced_path(raw)

    # Normalize absolute path (preserve Windows drive absolute like C:/...)
    if not (len(abs_path) >= 3 and abs_path[1:3] == ":/" and abs_path[0].isalpha()):
        if not abs_path.startswith("/"):
            abs_path = "/" + abs_path

    namespace = await _friendly_namespace_for_context(context_id)
    formatted_path = f"{namespace}:{abs_path}"
    is_remote = context_id != "local"

    return {
        "formatted_path": formatted_path,
        "namespace": namespace,
        "context_id": context_id,
        "absolute_path": abs_path,
        "is_remote": is_remote,
        "display_name": formatted_path,
    }
