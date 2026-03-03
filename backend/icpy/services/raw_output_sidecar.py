"""
Raw Output Sidecar Logger

Dumps the exact inputs and raw output sent to/from agent chat() functions
into a .raw.jsonl file alongside the main session .jsonl file.

Purpose: debugging what the LLM actually sees (system prompt, messages array,
tool definitions) and what it returns (including <think> tags, raw tool calls).

File format: one JSON line per agent invocation containing:
  - timestamp: ISO 8601
  - agent_type: agent name (e.g., "MiniMaxAgent")
  - user_message_id: the triggering user message ID
  - message: the `message` param passed to chat()
  - history: the full `history` list passed to chat() (what the LLM sees as context)
  - system_prompt: the complete system prompt sent to the LLM (if captured)
  - tool_schemas: the tool definitions/schemas sent to the LLM (if captured)
  - tool_executions: list of tool calls with name, args, full untruncated result, and duration
  - llm_requests: list of LLM API request summaries (model, message count, tool count)
  - raw_output: the complete concatenated raw response before any filtering
  - chunks: total number of streaming chunks received
  - duration_ms: wall-clock time for the full streaming response
"""

import json
import logging
import pprint
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ContextVar so the agent layer can write debug data into the active recorder
# without needing a direct reference. Set by chat_service before each invocation.
_active_recorder: ContextVar[Optional["InvocationRecorder"]] = ContextVar(
    "active_sidecar_recorder", default=None
)


def set_active_recorder(recorder: Optional["InvocationRecorder"]) -> None:
    """Set the active sidecar recorder for the current async context."""
    _active_recorder.set(recorder)


def get_active_recorder() -> Optional["InvocationRecorder"]:
    """Get the active sidecar recorder (if any) for the current async context."""
    return _active_recorder.get()


class RawOutputSidecar:
    """Records raw agent inputs/outputs to a .raw.jsonl sidecar file."""

    def __init__(self, history_root: Path):
        self.history_root = history_root

    def _raw_path(self, session_id: str) -> Path:
        """Get the .raw.jsonl path for a session."""
        return self.history_root / f"{session_id}.raw.jsonl"

    def start_invocation(
        self,
        session_id: str,
        agent_type: str,
        user_message_id: str,
        message: str,
        history: List[Dict[str, Any]],
    ) -> "InvocationRecorder":
        """Start recording a new agent invocation.
        
        Returns an InvocationRecorder that collects streaming chunks
        and writes the complete record on finalize().
        """
        return InvocationRecorder(
            raw_path=self._raw_path(session_id),
            agent_type=agent_type,
            user_message_id=user_message_id,
            message=message,
            history=history,
        )


class InvocationRecorder:
    """Collects streaming chunks and writes a single raw record on finalize."""

    def __init__(
        self,
        raw_path: Path,
        agent_type: str,
        user_message_id: str,
        message: str,
        history: List[Dict[str, Any]],
    ):
        self._raw_path = raw_path
        self._agent_type = agent_type
        self._user_message_id = user_message_id
        self._message = message
        self._history = history
        self._raw_chunks: List[str] = []
        self._start_time = time.monotonic()
        self._error: Optional[str] = None
        # Enhanced debug data
        self._system_prompt: Optional[str] = None
        self._tool_schemas: Optional[List[Dict[str, Any]]] = None
        self._tool_executions: List[Dict[str, Any]] = []
        self._llm_requests: List[Dict[str, Any]] = []

    def record_chunk(self, chunk: str) -> None:
        """Record a raw streaming chunk (before any filtering)."""
        self._raw_chunks.append(chunk)

    def record_error(self, error: str) -> None:
        """Record an error that occurred during streaming."""
        self._error = error

    def record_system_prompt(self, prompt: str) -> None:
        """Record the full system prompt sent to the LLM."""
        self._system_prompt = prompt

    def record_tool_schemas(self, schemas: List[Dict[str, Any]]) -> None:
        """Record the tool definition schemas sent to the LLM.

        Stores a compact summary (name + description) to keep logs manageable.
        """
        compact = []
        for s in (schemas or []):
            fn = s.get("function", s)
            compact.append({
                "name": fn.get("name", "?"),
                "description": (fn.get("description") or "")[:120],
                "parameters_keys": list((fn.get("parameters", {}).get("properties", {})).keys()),
            })
        self._tool_schemas = compact

    def record_tool_execution(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any],
        duration_ms: int = 0,
    ) -> None:
        """Record a single tool call with its full untruncated result."""
        # Sanitize large binary blobs (e.g., imageData base64) but keep file paths intact
        sanitized_result = _sanitize_tool_result(result)
        self._tool_executions.append({
            "tool": tool_name,
            "arguments": arguments,
            "result": sanitized_result,
            "duration_ms": duration_ms,
        })

    def record_llm_request(
        self,
        model: str,
        message_count: int,
        tool_count: int,
        iteration: int,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a summary of an LLM API request (one per streaming iteration)."""
        self._llm_requests.append({
            "model": model,
            "message_count": message_count,
            "tool_count": tool_count,
            "iteration": iteration,
            "extra_params": extra_params,
        })

    def finalize(self) -> None:
        """Write the complete invocation record to the .raw.jsonl file.

        Format: a single compact JSON line (for programmatic parsing) followed by
        a human-readable pprint block prefixed with ``#`` comment markers, matching
        the style used by ``debug_interceptor.py``.  Large fields (system_prompt,
        raw_output, history) are written as separate clearly-labelled sections so
        that developers can skim the file quickly.
        """
        duration_ms = round((time.monotonic() - self._start_time) * 1000)
        raw_output = "".join(self._raw_chunks)

        # Truncate image data URLs in history to keep the sidecar readable
        sanitized_history = _sanitize_history_for_log(self._history)

        record: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_type": self._agent_type,
            "user_message_id": self._user_message_id,
            "message": self._message,
            "history": sanitized_history,
            "raw_output": raw_output,
            "chunks": len(self._raw_chunks),
            "duration_ms": duration_ms,
        }
        if self._system_prompt is not None:
            record["system_prompt"] = self._system_prompt
        if self._tool_schemas is not None:
            record["tool_schemas"] = self._tool_schemas
        if self._tool_executions:
            record["tool_executions"] = self._tool_executions
        if self._llm_requests:
            record["llm_requests"] = self._llm_requests
        if self._error:
            record["error"] = self._error

        # Clear the ContextVar so stale references don't leak
        try:
            _active_recorder.set(None)
        except Exception:
            pass

        try:
            self._raw_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._raw_path, "a", encoding="utf-8") as f:
                # ── Compact JSON line (for programmatic parsing) ──
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

                # ── Human-readable sections ──
                sep = "# " + "─" * 78 + "\n"
                f.write(sep)
                f.write(f"# 🕐 {record['timestamp']}  |  agent={self._agent_type}  |  "
                        f"chunks={len(self._raw_chunks)}  |  duration={duration_ms}ms\n")
                f.write(f"# user_message_id: {self._user_message_id}\n")
                if self._error:
                    f.write(f"# ⚠ ERROR: {self._error}\n")
                f.write(sep)

                # System prompt
                if self._system_prompt is not None:
                    f.write("#\n# ── SYSTEM PROMPT ──\n")
                    for line in self._system_prompt.split("\n"):
                        f.write(f"#   {line}\n")
                    f.write("#\n")

                # Tool schemas
                if self._tool_schemas:
                    f.write("# ── TOOL SCHEMAS ──\n")
                    for ts in self._tool_schemas:
                        params = ", ".join(ts.get("parameters_keys", []))
                        f.write(f"#   • {ts['name']}({params})\n")
                        if ts.get("description"):
                            f.write(f"#     {ts['description']}\n")
                    f.write("#\n")

                # LLM requests
                if self._llm_requests:
                    f.write("# ── LLM REQUESTS ──\n")
                    for lr in self._llm_requests:
                        f.write(f"#   [{lr['iteration']}] model={lr['model']}  "
                                f"messages={lr['message_count']}  tools={lr['tool_count']}")
                        if lr.get("extra_params"):
                            f.write(f"  extra={lr['extra_params']}")
                        f.write("\n")
                    f.write("#\n")

                # Tool executions
                if self._tool_executions:
                    f.write("# ── TOOL EXECUTIONS ──\n")
                    for te in self._tool_executions:
                        f.write(f"#   🔧 {te['tool']}  ({te['duration_ms']}ms)\n")
                        f.write(f"#     args: {pprint.pformat(te['arguments'], width=100)}\n"
                                .replace("\n", "\n#     "))
                        f.write("\n")
                        result_str = pprint.pformat(te["result"], width=100, depth=4)
                        for rline in result_str.split("\n"):
                            f.write(f"#     result: {rline}\n")
                        f.write("#\n")

                # Conversation history (compact: role + length)
                if sanitized_history:
                    f.write("# ── HISTORY ──\n")
                    for i, msg in enumerate(sanitized_history):
                        role = msg.get("role", "?")
                        content = msg.get("content", "")
                        clen = len(content) if isinstance(content, str) else len(json.dumps(content))
                        preview = ""
                        if isinstance(content, str):
                            preview = content[:120].replace("\n", "↵")
                            if len(content) > 120:
                                preview += "…"
                        f.write(f"#   [{i}] {role} ({clen} chars): {preview}\n")
                    f.write("#\n")

                # Raw output
                f.write("# ── RAW OUTPUT ──\n")
                for line in raw_output.split("\n"):
                    f.write(f"#   {line}\n")

                f.write(sep)
                f.write("#\n\n")
        except Exception as e:
            logger.error(f"Failed to write raw sidecar: {e}")


def _sanitize_tool_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize a tool result for logging: truncate large binary blobs but keep paths."""
    if not isinstance(result, dict):
        return result
    sanitized = {}
    for key, val in result.items():
        if key == "data" and isinstance(val, dict):
            sanitized[key] = _sanitize_tool_result(val)
        elif isinstance(val, str) and len(val) > 2000:
            # Likely a base64 blob or huge output
            sanitized[key] = val[:200] + f"... [{len(val)} chars total]"
        else:
            sanitized[key] = val
    return sanitized


def _sanitize_history_for_log(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Truncate large data URLs in history entries to keep logs readable."""
    sanitized = []
    for msg in history:
        content = msg.get("content")
        if isinstance(content, list):
            # Multimodal content — truncate image_url data URIs
            new_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    img = part.get("image_url", {})
                    url = img.get("url", "") if isinstance(img, dict) else ""
                    if isinstance(url, str) and url.startswith("data:"):
                        # Replace data URL with a placeholder showing type and size
                        size_kb = round(len(url) / 1024)
                        new_parts.append({
                            "type": "image_url",
                            "image_url": {"url": f"[data_url:{size_kb}KB_truncated]"}
                        })
                    else:
                        new_parts.append(part)
                else:
                    new_parts.append(part)
            sanitized.append({**msg, "content": new_parts})
        else:
            sanitized.append(msg)
    return sanitized
