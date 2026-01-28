"""
Tests for Anthropic Agent wrapper.
Validates agent delegates to GeneralAgent correctly and uses correct model identifiers.
"""
from typing import Iterable

from icpy.agent.agents import anthropic_agent
from icpy.agent.core.llm.anthropic_client import AnthropicClientAdapter


def test_anthropic_agent_delegates_to_general_agent(monkeypatch):
    """Test that the Anthropic agent delegates to GeneralAgent correctly."""
    # Patch adapter.stream_chat to avoid network calls and API keys
    def fake_stream_chat(self, *, model, messages, tools=None, max_tokens=None) -> Iterable[str]:
        yield "OK"
    monkeypatch.setattr(AnthropicClientAdapter, "stream_chat", fake_stream_chat, raising=True)

    out = "".join(anthropic_agent.chat("hello", []))
    assert out == "OK"


def test_anthropic_agent_model_identifier():
    """Verify the Anthropic agent uses Claude Opus 4.5 model identifier (December 2025)."""
    # claude-opus-4-5-20251101 is the latest premium Claude model
    assert anthropic_agent.MODEL_NAME == "claude-opus-4-5-20251101"
    assert anthropic_agent.AGENT_METADATA["MODEL_NAME"] == "claude-opus-4-5-20251101"


def test_anthropic_agent_metadata():
    """Verify agent metadata is correctly configured."""
    assert anthropic_agent.AGENT_NAME == "AnthropicAgent"
    assert "Claude" in anthropic_agent.AGENT_DESCRIPTION or "Opus" in anthropic_agent.AGENT_DESCRIPTION
    assert anthropic_agent.AGENT_METADATA["AGENT_VERSION"] == "1.1.0"
