"""
Tests for GroqGptOssAgent wrapper.
Validates agent delegates to GeneralAgent correctly and uses correct model identifiers.
"""
from typing import Iterable

import types

from icpy.agent.agents import groq_gpt_oss_agent
from icpy.agent.core.llm.groq_client import GroqClientAdapter


def test_groq_gpt_oss_agent_delegates_to_general_agent(monkeypatch):
    """Test that the Groq GPT OSS agent delegates to GeneralAgent correctly."""
    # Patch adapter.stream_chat to avoid network calls and API keys
    def fake_stream_chat(self, *, model, messages, tools=None, max_tokens=None) -> Iterable[str]:
        yield "OK"
    monkeypatch.setattr(GroqClientAdapter, "stream_chat", fake_stream_chat, raising=True)

    out = "".join(groq_gpt_oss_agent.chat("hello", []))
    assert out == "OK"


def test_groq_gpt_oss_agent_model_identifier():
    """Verify the Groq GPT OSS agent uses the correct model identifier."""
    assert groq_gpt_oss_agent.MODEL_NAME == "gpt-oss-120b"
    assert groq_gpt_oss_agent.AGENT_METADATA["MODEL_NAME"] == "gpt-oss-120b"


def test_groq_gpt_oss_agent_metadata():
    """Verify agent metadata is correctly configured."""
    assert groq_gpt_oss_agent.AGENT_NAME == "GroqGptOssAgent"
    assert "GPT OSS 120B" in groq_gpt_oss_agent.AGENT_DESCRIPTION
    assert groq_gpt_oss_agent.AGENT_METADATA["AGENT_VERSION"] == "1.0.0"
