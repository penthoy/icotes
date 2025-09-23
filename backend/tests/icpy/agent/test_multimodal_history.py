import json
from icpy.agent.helpers import normalize_history


def test_normalize_preserves_rich_user_content():
    rich = [
        {"type": "text", "text": "what do you see?"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAA"}},
    ]
    history = [
        {"role": "user", "content": rich},
        {"role": "assistant", "content": "A response"},
    ]

    out = normalize_history(history)
    assert isinstance(out, list)
    assert out[0]["role"] == "user"
    # Content should remain a list preserving parts
    assert isinstance(out[0]["content"], list)
    assert out[0]["content"][1]["type"] == "image_url"


def test_normalize_drops_empty_rich_user():
    empty_rich = [
        {"type": "text", "text": "   "},
        {"type": "image_url", "image_url": {"url": ""}},
    ]
    history = [
        {"role": "user", "content": empty_rich},
        {"role": "assistant", "content": "foo"},
    ]
    out = normalize_history(history)
    # Only assistant message should remain
    assert len(out) == 1
    assert out[0]["role"] == "assistant"
