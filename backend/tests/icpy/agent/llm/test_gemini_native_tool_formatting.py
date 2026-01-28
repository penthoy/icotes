import json

from icpy.agent.core.llm.gemini_native_client import GeminiNativeClientAdapter


def _extract_json_from_success_line(line: str) -> str:
    assert line.startswith("✅ **Success**: ")
    payload = line[len("✅ **Success**: ") :].strip()
    return payload


def test_generate_image_success_is_valid_json_and_contains_urls():
    adapter = GeminiNativeClientAdapter()

    # Simulate a realistic (potentially large) generate_image payload
    tool_result = {
        "success": True,
        "data": {
            "imageReference": {
                "image_id": "abc",
                "thumbnail_base64": "A" * 20000,  # huge thumbnail; should not be embedded
                "relative_path": "img.png",
                "absolute_path": "/tmp/img.png",
                "mime_type": "image/png",
            },
            "imageUrl": "file:///home/penthoy/icotes/workspace/img.png",
            "fullImageUrl": "/api/media/image/abc",
            "prompt": "a cat wearing a hat",
            "model": "gemini-2.5-flash-image",
        },
    }

    payload = adapter._serialize_tool_success_data("generate_image", tool_result)
    parsed = json.loads(payload)

    assert parsed.get("imageUrl")
    assert parsed.get("fullImageUrl")

    # Ensure we didn't stream the massive thumbnail
    image_ref = parsed.get("imageReference")
    assert isinstance(image_ref, dict)
    assert "thumbnail_base64" not in image_ref


def test_large_dict_result_emits_valid_json_summary():
    adapter = GeminiNativeClientAdapter()

    tool_result = {
        "success": True,
        "data": {
            "message": "x" * 20000,
            "other": "y" * 20000,
            "ok": True,
        },
    }

    payload = adapter._serialize_tool_success_data("some_tool", tool_result)
    parsed = json.loads(payload)

    assert parsed.get("truncated") is True
    assert "keys" in parsed
