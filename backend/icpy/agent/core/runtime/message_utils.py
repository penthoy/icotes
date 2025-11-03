from __future__ import annotations

import logging
from typing import Any, Dict, List

from ...helpers import normalize_history, flatten_message_content

logger = logging.getLogger(__name__)


def build_safe_messages(user_message: str, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize and sanitize chat messages for agents.

    - Normalizes history via helpers.normalize_history
    - Appends the current user message if non-empty
    - Preserves multimodal user content arrays
    - Flattens non-string contents to strings for provider compatibility

    Returns a new list of message dicts ready to send to the runtime.
    """
    # Normalize history
    normalized_history = normalize_history(history)

    messages: List[Dict[str, Any]] = list(normalized_history)

    # Append current user message only if non-empty
    if isinstance(user_message, str) and user_message.strip():
        messages.append({"role": "user", "content": user_message})
    else:
        logger.info(
            'MessageBuilder: Skipping trailing user message because it is empty (provided by caller as "")'
        )

    # Final safety filter (preserve multimodal user content arrays)
    safe_messages: List[Dict[str, Any]] = []
    dropped = 0
    for i, m in enumerate(messages):
        c = m.get("content", "")
        role = m.get("role")
        if role == "user" and isinstance(c, list):
            has_content = False
            try:
                for p in c:
                    if isinstance(p, dict):
                        t = p.get("type")
                        if t == "text" and isinstance(p.get("text"), str) and p["text"].strip():
                            has_content = True
                            break
                        if t == "image_url":
                            img = p.get("image_url")
                            url = img.get("url") if isinstance(img, dict) else (img if isinstance(img, str) else None)
                            if url:
                                has_content = True
                                break
                    elif str(p).strip():
                        has_content = True
                        break
            except Exception:
                has_content = True
            if not has_content:
                dropped += 1
                logger.warning(
                    f"MessageBuilder: Removing empty user rich message at position {i}"
                )
                continue
            safe_messages.append(m)
            continue
        if role == "user" and (not isinstance(c, str) or not c.strip()):
            dropped += 1
            logger.warning(
                f"MessageBuilder: Removing empty user message at position {i}"
            )
            continue
        if not isinstance(c, str):
            m = {**m, "content": flatten_message_content(c)}
        safe_messages.append(m)
    if dropped:
        logger.info(f"MessageBuilder: Dropped {dropped} empty user message(s) before request")

    return safe_messages
