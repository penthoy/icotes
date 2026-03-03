"""Tests for RawOutputSidecar and InvocationRecorder."""

import json
import pytest
from pathlib import Path
from icpy.services.raw_output_sidecar import (
    RawOutputSidecar,
    InvocationRecorder,
    _sanitize_history_for_log,
    _sanitize_tool_result,
    set_active_recorder,
    get_active_recorder,
)


def _read_json_records(path: Path) -> list[dict]:
    """Extract JSON record lines from a .raw.jsonl file, skipping comment lines."""
    records = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            records.append(json.loads(stripped))
    return records


class TestRawOutputSidecar:
    """Test the raw output sidecar file writing."""

    def test_raw_path_matches_session(self, tmp_path):
        sidecar = RawOutputSidecar(tmp_path)
        path = sidecar._raw_path("session_123_abc")
        assert path == tmp_path / "session_123_abc.raw.jsonl"

    def test_start_invocation_returns_recorder(self, tmp_path):
        sidecar = RawOutputSidecar(tmp_path)
        recorder = sidecar.start_invocation(
            session_id="session_123",
            agent_type="MiniMaxAgent",
            user_message_id="msg-001",
            message="Hello",
            history=[{"role": "user", "content": "Hi"}],
        )
        assert isinstance(recorder, InvocationRecorder)

    def test_full_recording_writes_jsonl(self, tmp_path):
        sidecar = RawOutputSidecar(tmp_path)
        recorder = sidecar.start_invocation(
            session_id="session_abc",
            agent_type="MiniMaxAgent",
            user_message_id="msg-001",
            message="",
            history=[{"role": "user", "content": "Hey"}],
        )

        # Simulate streaming chunks (raw, with think tags)
        recorder.record_chunk("<think>reasoning</think>")
        recorder.record_chunk("Hello! ")
        recorder.record_chunk("How can I help?")
        recorder.finalize()

        # Read and verify
        raw_path = tmp_path / "session_abc.raw.jsonl"
        assert raw_path.exists()

        records = _read_json_records(raw_path)
        assert len(records) == 1

        record = records[0]
        assert record["agent_type"] == "MiniMaxAgent"
        assert record["user_message_id"] == "msg-001"
        assert record["message"] == ""
        assert record["history"] == [{"role": "user", "content": "Hey"}]
        assert record["raw_output"] == "<think>reasoning</think>Hello! How can I help?"
        assert record["chunks"] == 3
        assert record["duration_ms"] >= 0
        assert "error" not in record

    def test_error_recording(self, tmp_path):
        sidecar = RawOutputSidecar(tmp_path)
        recorder = sidecar.start_invocation(
            session_id="session_err",
            agent_type="TestAgent",
            user_message_id="msg-002",
            message="test",
            history=[],
        )
        recorder.record_chunk("partial output")
        recorder.record_error("Connection reset")
        recorder.finalize()

        raw_path = tmp_path / "session_err.raw.jsonl"
        record = _read_json_records(raw_path)[0]
        assert record["error"] == "Connection reset"
        assert record["raw_output"] == "partial output"

    def test_multiple_invocations_append(self, tmp_path):
        """Multiple invocations append to the same .raw.jsonl file."""
        sidecar = RawOutputSidecar(tmp_path)

        for i in range(3):
            recorder = sidecar.start_invocation(
                session_id="session_multi",
                agent_type="TestAgent",
                user_message_id=f"msg-{i}",
                message=f"msg {i}",
                history=[],
            )
            recorder.record_chunk(f"response {i}")
            recorder.finalize()

        raw_path = tmp_path / "session_multi.raw.jsonl"
        records = _read_json_records(raw_path)
        assert len(records) == 3
        for i, record in enumerate(records):
            assert record["user_message_id"] == f"msg-{i}"
            assert record["raw_output"] == f"response {i}"


class TestSanitizeHistory:
    """Test data URL truncation in history logs."""

    def test_plain_text_passes_through(self):
        history = [{"role": "user", "content": "Hello"}]
        result = _sanitize_history_for_log(history)
        assert result == history

    def test_data_url_truncated(self):
        fake_b64 = "x" * 10000  # ~10KB of data
        history = [{
            "role": "user",
            "content": [
                {"type": "text", "text": "describe this"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{fake_b64}"}},
            ]
        }]
        result = _sanitize_history_for_log(history)
        # Text part unchanged
        assert result[0]["content"][0] == {"type": "text", "text": "describe this"}
        # Image URL replaced with truncated placeholder
        img_url = result[0]["content"][1]["image_url"]["url"]
        assert img_url.startswith("[data_url:")
        assert "truncated" in img_url

    def test_non_data_url_preserved(self):
        history = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}},
            ]
        }]
        result = _sanitize_history_for_log(history)
        assert result[0]["content"][0]["image_url"]["url"] == "https://example.com/img.png"

    def test_assistant_messages_pass_through(self):
        history = [{"role": "assistant", "content": "I can help with that"}]
        result = _sanitize_history_for_log(history)
        assert result == history


class TestEnhancedRecording:
    """Test system_prompt, tool_schemas, tool_executions, and llm_requests recording."""

    def _make_recorder(self, tmp_path, session_id="session_enhanced"):
        sidecar = RawOutputSidecar(tmp_path)
        return sidecar.start_invocation(
            session_id=session_id,
            agent_type="TestAgent",
            user_message_id="msg-e1",
            message="test",
            history=[{"role": "user", "content": "hello"}],
        )

    def test_system_prompt_recorded(self, tmp_path):
        recorder = self._make_recorder(tmp_path)
        recorder.record_system_prompt("You are a helpful assistant.")
        recorder.record_chunk("Hi!")
        recorder.finalize()

        record = _read_json_records(tmp_path / "session_enhanced.raw.jsonl")[0]
        assert record["system_prompt"] == "You are a helpful assistant."

    def test_tool_schemas_recorded_compact(self, tmp_path):
        recorder = self._make_recorder(tmp_path)
        schemas = [
            {"type": "function", "function": {
                "name": "text_to_speech",
                "description": "Convert text to speech using ElevenLabs",
                "parameters": {"type": "object", "properties": {"text": {"type": "string"}, "voice": {"type": "string"}}},
            }},
            {"type": "function", "function": {
                "name": "generate_image",
                "description": "Generate an image from a text prompt",
                "parameters": {"type": "object", "properties": {"prompt": {"type": "string"}}},
            }},
        ]
        recorder.record_tool_schemas(schemas)
        recorder.record_chunk("done")
        recorder.finalize()

        record = _read_json_records(tmp_path / "session_enhanced.raw.jsonl")[0]
        assert len(record["tool_schemas"]) == 2
        assert record["tool_schemas"][0]["name"] == "text_to_speech"
        assert "text" in record["tool_schemas"][0]["parameters_keys"]
        assert record["tool_schemas"][1]["name"] == "generate_image"

    def test_tool_execution_recorded_full(self, tmp_path):
        recorder = self._make_recorder(tmp_path)
        result = {
            "success": True,
            "data": {
                "file_path": "sounds/tts_hello.mp3",
                "absolute_path": "/workspace/sounds/tts_hello.mp3",
                "text": "Hello",
                "audio_size_bytes": 12345,
                "saved": True,
            }
        }
        recorder.record_tool_execution("text_to_speech", {"text": "Hello", "voice": "tao2"}, result, 1500)
        recorder.record_chunk("done")
        recorder.finalize()

        record = _read_json_records(tmp_path / "session_enhanced.raw.jsonl")[0]
        assert len(record["tool_executions"]) == 1
        te = record["tool_executions"][0]
        assert te["tool"] == "text_to_speech"
        assert te["arguments"]["text"] == "Hello"
        assert te["result"]["data"]["absolute_path"] == "/workspace/sounds/tts_hello.mp3"
        assert te["duration_ms"] == 1500

    def test_llm_request_recorded(self, tmp_path):
        recorder = self._make_recorder(tmp_path)
        recorder.record_llm_request(
            model="kimi-k2.5",
            message_count=5,
            tool_count=12,
            iteration=1,
            extra_params={"thinking": {"type": "disabled"}},
        )
        recorder.record_chunk("response")
        recorder.finalize()

        record = _read_json_records(tmp_path / "session_enhanced.raw.jsonl")[0]
        assert len(record["llm_requests"]) == 1
        lr = record["llm_requests"][0]
        assert lr["model"] == "kimi-k2.5"
        assert lr["message_count"] == 5
        assert lr["tool_count"] == 12
        assert lr["iteration"] == 1

    def test_full_enhanced_recording(self, tmp_path):
        """Simulate a complete agent invocation with all enhanced fields."""
        recorder = self._make_recorder(tmp_path, "session_full")

        recorder.record_system_prompt("You are KimiAgent, a helpful AI.")
        recorder.record_tool_schemas([
            {"type": "function", "function": {"name": "text_to_speech", "description": "TTS", "parameters": {"type": "object", "properties": {"text": {}, "voice": {}}}}},
        ])
        recorder.record_llm_request("kimi-k2.5", 3, 1, 1)
        recorder.record_chunk("📋 **text_to_speech**: {'text': 'Hello'}\n")
        recorder.record_tool_execution(
            "text_to_speech",
            {"text": "Hello", "voice": "tao2"},
            {"success": True, "data": {"file_path": "sounds/tts_hello.mp3", "absolute_path": "/workspace/sounds/tts_hello.mp3"}},
            800,
        )
        recorder.record_chunk("✅ **Success**: ...\n")
        recorder.record_llm_request("kimi-k2.5", 6, 1, 2)
        recorder.record_chunk("Here's your audio!")
        recorder.finalize()

        record = _read_json_records(tmp_path / "session_full.raw.jsonl")[0]
        assert record["system_prompt"] is not None
        assert len(record["tool_schemas"]) == 1
        assert len(record["tool_executions"]) == 1
        assert len(record["llm_requests"]) == 2
        assert record["chunks"] == 3
        # Verify the full absolute_path is preserved (not truncated)
        assert record["tool_executions"][0]["result"]["data"]["absolute_path"] == "/workspace/sounds/tts_hello.mp3"

    def test_human_readable_comments_written(self, tmp_path):
        """Verify the pprint comment block is written after the JSON line."""
        recorder = self._make_recorder(tmp_path, "session_hr")
        recorder.record_system_prompt("You are helpful.")
        recorder.record_tool_schemas([
            {"type": "function", "function": {"name": "my_tool", "description": "desc", "parameters": {"type": "object", "properties": {"x": {}}}}},
        ])
        recorder.record_tool_execution("my_tool", {"x": 1}, {"ok": True}, 50)
        recorder.record_llm_request("gpt-4", 2, 1, 1)
        recorder.record_chunk("output")
        recorder.finalize()

        raw = (tmp_path / "session_hr.raw.jsonl").read_text()
        # Must have comment lines
        comment_lines = [l for l in raw.splitlines() if l.startswith("#")]
        assert len(comment_lines) > 5

        # Check for section headers
        assert any("SYSTEM PROMPT" in l for l in comment_lines)
        assert any("TOOL SCHEMAS" in l for l in comment_lines)
        assert any("TOOL EXECUTIONS" in l for l in comment_lines)
        assert any("LLM REQUESTS" in l for l in comment_lines)
        assert any("RAW OUTPUT" in l for l in comment_lines)

        # JSON line is still parseable
        records = _read_json_records(tmp_path / "session_hr.raw.jsonl")
        assert len(records) == 1
        assert records[0]["agent_type"] == "TestAgent"

    def test_omitted_when_not_set(self, tmp_path):
        """Enhanced fields should not appear when not explicitly set."""
        recorder = self._make_recorder(tmp_path, "session_minimal")
        recorder.record_chunk("just text")
        recorder.finalize()

        record = _read_json_records(tmp_path / "session_minimal.raw.jsonl")[0]
        assert "system_prompt" not in record
        assert "tool_schemas" not in record
        assert "tool_executions" not in record
        assert "llm_requests" not in record


class TestSanitizeToolResult:
    """Test that large blobs in tool results are truncated but paths preserved."""

    def test_small_result_unchanged(self):
        result = {"success": True, "data": {"file_path": "sounds/hello.mp3"}}
        assert _sanitize_tool_result(result) == result

    def test_large_string_truncated(self):
        big = "x" * 5000
        result = {"success": True, "data": {"imageData": big, "filePath": "/workspace/img.png"}}
        sanitized = _sanitize_tool_result(result)
        assert sanitized["data"]["filePath"] == "/workspace/img.png"
        assert len(sanitized["data"]["imageData"]) < 300
        assert "5000 chars total" in sanitized["data"]["imageData"]


class TestContextVar:
    """Test the active recorder context variable."""

    def test_default_is_none(self):
        assert get_active_recorder() is None

    def test_set_and_get(self, tmp_path):
        sidecar = RawOutputSidecar(tmp_path)
        recorder = sidecar.start_invocation(
            session_id="ctx_test",
            agent_type="T",
            user_message_id="m1",
            message="",
            history=[],
        )
        set_active_recorder(recorder)
        assert get_active_recorder() is recorder
        # finalize clears the context var
        recorder.record_chunk("x")
        recorder.finalize()
        assert get_active_recorder() is None
