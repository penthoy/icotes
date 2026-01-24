"""
Tests for CerebrasGptOssAgent wrapper.
Validates agent delegates to GeneralAgent correctly and uses correct model identifiers.
"""
from typing import Iterable

import types

from icpy.agent.agents import cerebras_gpt_oss_agent
from icpy.agent.core.llm.cerebras_client import CerebrasClientAdapter


def test_cerebras_gpt_oss_agent_delegates_to_general_agent(monkeypatch):
    """Test that the Cerebras GPT OSS agent delegates to GeneralAgent correctly."""
    # Patch adapter.stream_chat to avoid network calls and API keys
    def fake_stream_chat(self, *, model, messages, tools=None, max_tokens=None) -> Iterable[str]:
        yield "OK"
    monkeypatch.setattr(CerebrasClientAdapter, "stream_chat", fake_stream_chat, raising=True)

    out = "".join(cerebras_gpt_oss_agent.chat("hello", []))
    assert out == "OK"


def test_cerebras_gpt_oss_agent_model_identifier():
    """Verify the Cerebras GPT OSS agent uses the correct model identifier."""
    assert cerebras_gpt_oss_agent.MODEL_NAME == "gpt-oss-120b"
    assert cerebras_gpt_oss_agent.AGENT_METADATA["MODEL_NAME"] == "gpt-oss-120b"


def test_cerebras_gpt_oss_agent_metadata():
    """Verify agent metadata is correctly configured."""
    assert cerebras_gpt_oss_agent.AGENT_NAME == "CerebrasGptOssAgent"
    assert "GPT OSS 120B" in cerebras_gpt_oss_agent.AGENT_DESCRIPTION
    assert cerebras_gpt_oss_agent.AGENT_METADATA["AGENT_VERSION"] == "1.0.0"
