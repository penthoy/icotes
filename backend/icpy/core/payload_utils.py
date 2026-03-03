"""Shared helpers for unwrapping common API response envelopes."""

from __future__ import annotations

from typing import Any


def unwrap_envelope(payload: Any) -> Any:
    """Unwrap ``{..., data: {...}}`` envelopes returned by Atlas / Route APIs.

    If *payload* is a dict with a ``data`` key whose value is also a dict, the
    inner ``data`` dict is returned.  Otherwise *payload* is returned unchanged.

    This performs **no** validation (status codes, error fields, etc.) — callers
    that need error-checking should inspect the envelope *before* calling this,
    or use a domain-specific wrapper around it.
    """
    if isinstance(payload, dict) and "data" in payload and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload
