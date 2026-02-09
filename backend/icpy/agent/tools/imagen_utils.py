"""
Utilities for ImagenTool sizing and simple helpers.

Keep these helpers small and pure so they are easy to unit test and reason about.
"""
from __future__ import annotations

from typing import Optional, Tuple, Dict

# Gemini API natively supported aspect ratios with their default resolutions
# Map: label -> (width, height, token_weight)
# These are passed directly to the API via image_config.aspect_ratio
# Reference: https://ai.google.dev/gemini-api/docs/image-generation
ASPECT_RATIO_SPECS: Dict[str, Tuple[int, int, float]] = {
    "1:1": (1024, 1024, 1.0),    # Square (default)
    "2:3": (832, 1248, 1.1),     # Portrait
    "3:2": (1248, 832, 1.1),     # Landscape  
    "3:4": (864, 1184, 1.1),     # Portrait
    "4:3": (1184, 864, 1.1),     # Landscape
    "4:5": (896, 1152, 1.1),     # Portrait (social media)
    "5:4": (1152, 896, 1.1),     # Landscape
    "9:16": (768, 1344, 1.2),    # Vertical video/phone
    "16:9": (1344, 768, 1.2),    # Widescreen
    "21:9": (1536, 672, 1.3),    # Ultrawide/cinematic
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
