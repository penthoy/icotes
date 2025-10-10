"""
Utilities for ImagenTool sizing and simple helpers.

Keep these helpers small and pure so they are easy to unit test and reason about.
"""
from __future__ import annotations

from typing import Optional, Tuple, Dict

# Common aspect ratio presets used by UI/tests
# Map: label -> (recommended_width, recommended_height, token_weight)
# Token weight is an arbitrary relative cost indicator for prompt sizing heuristics
ASPECT_RATIO_SPECS: Dict[str, Tuple[int, int, float]] = {
    "1:1": (1024, 1024, 1.0),
    "16:9": (1920, 1080, 1.2),
    "9:16": (1080, 1920, 1.2),
    "4:3": (1600, 1200, 1.1),
    "21:9": (2560, 1080, 1.3),
}


def resolve_dimensions(
    width: Optional[int],
    height: Optional[int],
    aspect_ratio_label: Optional[str],
    has_input_image: bool,
    default_square: Tuple[int, int] = (1024, 1024),
) -> Tuple[Optional[int], Optional[int]]:
    """
    Decide target width/height based on user parameters.

    Rules:
    - If width/height are provided explicitly, prefer them as-is (maintain AR later)
    - Else if aspect_ratio_label is provided, use the preset recommended size
    - Else if text-to-image (no input image): default to 1024x1024 (configurable)
    - Else (edit mode without explicit size): return None to keep original

    Returns the (width, height) which may include None when not constrained.
    """
    # Explicit dimensions win
    if width or height:
        return width, height

    # Preset from aspect ratio label
    if aspect_ratio_label:
        preset = ASPECT_RATIO_SPECS.get(aspect_ratio_label)
        if preset:
            w, h, _ = preset
            return w, h

    # Default only for text-to-image (no input image)
    if not has_input_image:
        return default_square

    # Editing without size hints: preserve original
    return None, None


def guess_mime_from_ext(path: str, fallback: str = "image/png") -> str:
    """Lightweight mime guess from file extension."""
    ext = path.lower().rsplit('.', 1)[-1] if '.' in path else ''
    return {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'webp': 'image/webp',
        'gif': 'image/gif',
    }.get(ext, fallback)
