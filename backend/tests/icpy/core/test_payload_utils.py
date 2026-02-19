"""Tests for icpy.core.payload_utils."""

from icpy.core.payload_utils import unwrap_envelope


def test_unwrap_envelope_extracts_data():
    """Nested {data: {...}} envelopes are unwrapped."""
    assert unwrap_envelope({"code": 200, "message": "ok", "data": {"id": "abc"}}) == {"id": "abc"}


def test_unwrap_envelope_passthrough_no_data_key():
    """Payloads without a 'data' key are returned as-is."""
    payload = {"id": "abc", "status": "completed"}
    assert unwrap_envelope(payload) is payload


def test_unwrap_envelope_passthrough_non_dict_data():
    """If 'data' is not a dict, the outer payload is returned."""
    payload = {"data": "just-a-string"}
    assert unwrap_envelope(payload) is payload


def test_unwrap_envelope_passthrough_non_dict_input():
    """Non-dict inputs (lists, None, etc.) are returned unchanged."""
    assert unwrap_envelope([1, 2, 3]) == [1, 2, 3]
    assert unwrap_envelope(None) is None
    assert unwrap_envelope("hello") == "hello"
