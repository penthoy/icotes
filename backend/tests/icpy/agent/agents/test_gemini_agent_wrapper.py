"""
Tests for Gemini Agent wrapper.
Validates agent uses native SDK correctly and has correct model identifiers.
"""
from typing import Iterable

from icpy.agent.agents import gemini_agent
from icpy.agent.core.llm.gemini_native_client import GeminiNativeClientAdapter


def test_gemini_agent_delegates_to_native_client(monkeypatch):
    """Test that the Gemini agent delegates to native SDK client correctly."""
    # Patch adapter.stream_chat to avoid network calls and API keys
    def fake_stream_chat(self, *, model, messages, tools=None, max_tokens=None) -> Iterable[str]:
        yield "OK"
    monkeypatch.setattr(GeminiNativeClientAdapter, "stream_chat", fake_stream_chat, raising=True)

    out = "".join(gemini_agent.chat("hello", []))
    assert out == "OK"


def test_gemini_agent_model_identifier():
    """Verify the Gemini agent uses Gemini 3 Pro model identifier (December 2025)."""
    # gemini-3-pro-preview is the latest flagship Gemini model
    assert gemini_agent.MODEL_NAME == "gemini-3-pro-preview"
    assert gemini_agent.AGENT_METADATA["MODEL_NAME"] == "gemini-3-pro-preview"


def test_gemini_agent_metadata():
    """Verify agent metadata is correctly configured."""
    assert gemini_agent.AGENT_NAME == "GeminiAgent"
    assert "Gemini" in gemini_agent.AGENT_DESCRIPTION
    assert gemini_agent.AGENT_METADATA["AGENT_VERSION"] == "1.1.0"


def test_gemini_thought_signatures_default():
    """Verify thought signatures are enabled by default for Gemini 3."""
    # Thought signatures are critical for Gemini 3 multi-step reasoning
    assert gemini_agent.GEMINI_THOUGHT_SIGNATURES is True
