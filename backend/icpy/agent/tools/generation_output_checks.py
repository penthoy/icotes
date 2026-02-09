"""Utilities to validate generator tool outputs.

Some provider APIs and remote filesystem paths can report "saved" successfully
while the expected file is not actually present (or is empty). These helpers
perform a post-write verification and collect lightweight diagnostics to aid
debugging.

Intended for use by generation tools (TTS, music, image/video generation).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


async def verify_output_file(
    filesystem_service: Any,
    file_path: str,
    *,
    expected_size: Optional[int] = None,
    min_size: int = 1,
    include_directory_listing: bool = True,
    directory_listing_limit: int = 50,
) -> Tuple[bool, Dict[str, Any]]:
    """Verify that an output file exists and looks valid.

    Args:
        filesystem_service: Contextual filesystem (local or remote) supporting
            `get_file_info` and optionally `list_directory`.
        file_path: Absolute path in the active context.
        expected_size: If provided, require exact byte size match.
        min_size: Minimum acceptable size when expected_size is not provided.
        include_directory_listing: Include parent dir listing in debug info.
        directory_listing_limit: Max entries to include from parent directory.

    Returns:
        (ok, debug_info)
    """

    debug: Dict[str, Any] = {
        "file_path": file_path,
        "expected_size": expected_size,
        "min_size": min_size,
    }

    # Primary check: filesystem_service.get_file_info (works for both local and remote)
    info = None
    try:
        if filesystem_service is not None and hasattr(filesystem_service, "get_file_info"):
            info = await filesystem_service.get_file_info(file_path)
    except Exception as e:
        debug["get_file_info_error"] = f"{type(e).__name__}: {e}"

    if info is not None:
        try:
            debug["file_info"] = info.to_dict() if hasattr(info, "to_dict") else dict(info)  # type: ignore[arg-type]
        except Exception:
            debug["file_info"] = {
                "path": getattr(info, "path", None),
                "name": getattr(info, "name", None),
                "size": getattr(info, "size", None),
                "modified_at": getattr(info, "modified_at", None),
                "type": str(getattr(info, "type", None)),
            }

        size = getattr(info, "size", None)
        # Guard: only trust size if it's actually numeric
        if not isinstance(size, (int, float)):
            size = None
        debug["observed_size"] = size

        if size is not None:
            if expected_size is not None:
                ok = size == expected_size
            else:
                ok = size >= min_size
        else:
            # FS service returned non-numeric / unusable size; defer to local fallback
            ok = False
    else:
        debug["file_info"] = None
        debug["observed_size"] = None
        ok = False

    # Secondary local check (best effort) – also serves as authoritative fallback
    # when the contextual FS returned a non-numeric size or raised an error.
    try:
        if isinstance(file_path, str) and file_path.startswith("/"):
            local_exists = os.path.exists(file_path)
            debug["local_exists"] = local_exists
            if local_exists and os.path.isfile(file_path):
                local_size = os.path.getsize(file_path)
                debug["local_size"] = local_size

                # If primary FS check was inconclusive, use local result
                if not ok:
                    if expected_size is not None:
                        ok = local_size == expected_size
                    else:
                        ok = local_size >= min_size
    except Exception as e:
        debug["local_check_error"] = f"{type(e).__name__}: {e}"

    # Parent directory listing for debugging
    parent_dir = None
    try:
        parent_dir = os.path.dirname(file_path) if file_path else None
    except Exception:
        parent_dir = None

    debug["parent_dir"] = parent_dir

    if include_directory_listing and parent_dir:
        try:
            if filesystem_service is not None and hasattr(filesystem_service, "list_directory"):
                items = await filesystem_service.list_directory(parent_dir, include_hidden=False, recursive=False)
                debug["parent_listing_count"] = len(items)
                listing = []
                for fi in items[: max(0, directory_listing_limit)]:
                    listing.append(
                        {
                            "name": getattr(fi, "name", None),
                            "size": getattr(fi, "size", None),
                            "path": getattr(fi, "path", None),
                            "type": str(getattr(fi, "type", None)),
                        }
                    )
                debug["parent_listing"] = listing
        except Exception as e:
            debug["parent_listing_error"] = f"{type(e).__name__}: {e}"

    if not ok:
        logger.warning("[OutputCheck] Output file verification failed: %s", debug)

    return ok, debug
