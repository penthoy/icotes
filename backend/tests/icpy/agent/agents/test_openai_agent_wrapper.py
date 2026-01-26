"""
Tests for OpenAI Agent wrapper.
Validates agent delegates to GeneralAgent correctly and uses correct model identifiers.
"""
from typing import Iterable

import types

from icpy.agent.agents import openai_agent
from icpy.agent.core.llm.openai_client import OpenAIClientAdapter


def test_openai_agent_delegates_to_general_agent(monkeypatch):
    """Test that the OpenAI agent delegates to GeneralAgent correctly."""
    # Patch adapter.stream_chat to avoid network calls and API keys
    def fake_stream_chat(self, *, model, messages, tools=None, max_tokens=None) -> Iterable[str]:
        yield "OK"
    monkeypatch.setattr(OpenAIClientAdapter, "stream_chat", fake_stream_chat, raising=True)

    out = "".join(openai_agent.chat("hello", []))
    assert out == "OK"


def test_openai_agent_model_identifier():
    """Verify the OpenAI agent uses the latest model identifier (December 2025)."""
    # gpt-5.2 is the latest flagship model as of December 2025
    assert openai_agent.MODEL_NAME == "gpt-5.2"
    assert openai_agent.AGENT_METADATA["MODEL_NAME"] == "gpt-5.2"


def test_openai_agent_metadata():
    """Verify agent metadata is correctly configured."""
    assert openai_agent.AGENT_NAME == "OpenAIAgent"
    assert "OpenAI" in openai_agent.AGENT_DESCRIPTION
    assert openai_agent.AGENT_METADATA["AGENT_VERSION"] == "1.3.0"
