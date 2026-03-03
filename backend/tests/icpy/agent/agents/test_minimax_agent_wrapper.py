"""
Tests for MiniMaxAgent wrapper.
Validates agent delegates to GeneralAgent correctly and uses correct model identifiers.
"""
from typing import Iterable

from icpy.agent.agents import minimax_agent
from icpy.agent.core.llm.minimax_client import MiniMaxClientAdapter


def test_minimax_agent_delegates_to_general_agent(monkeypatch):
    """Test that the MiniMax agent delegates to GeneralAgent correctly."""
    # Patch adapter.stream_chat to avoid network calls and API keys
    def fake_stream_chat(self, *, model, messages, tools=None, max_tokens=None, extra_params=None) -> Iterable[str]:
        yield "OK"
    monkeypatch.setattr(MiniMaxClientAdapter, "stream_chat", fake_stream_chat, raising=True)

    out = "".join(minimax_agent.chat("hello", []))
    assert out == "OK"


def test_minimax_agent_model_identifier():
    """Verify the MiniMax agent uses the correct model identifier."""
    assert minimax_agent.MODEL_NAME == "MiniMax-M2.5"
    assert minimax_agent.AGENT_METADATA["MODEL_NAME"] == "MiniMax-M2.5"


def test_minimax_agent_metadata():
    """Verify agent metadata is correctly configured."""
    assert minimax_agent.AGENT_NAME == "MiniMaxAgent"
    assert "MiniMax" in minimax_agent.AGENT_DESCRIPTION
    assert minimax_agent.AGENT_METADATA["AGENT_VERSION"] == "1.0.0"
