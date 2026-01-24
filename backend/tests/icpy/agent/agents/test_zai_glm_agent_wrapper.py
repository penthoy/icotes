"""
Tests for Z.AI GLM Agent wrapper.
Validates agent delegates to GeneralAgent correctly and uses correct model identifiers.
"""
from typing import Iterable

import types

from icpy.agent.agents import zai_glm_agent
from icpy.agent.core.llm.cerebras_client import CerebrasClientAdapter


def test_zai_glm_agent_delegates_to_general_agent(monkeypatch):
    """Test that the Z.AI GLM agent delegates to GeneralAgent correctly."""
    # Patch adapter.stream_chat to avoid network calls and API keys
    def fake_stream_chat(self, *, model, messages, tools=None, max_tokens=None) -> Iterable[str]:
        yield "OK"
    monkeypatch.setattr(CerebrasClientAdapter, "stream_chat", fake_stream_chat, raising=True)

    out = "".join(zai_glm_agent.chat("hello", []))
    assert out == "OK"


def test_zai_glm_agent_model_identifier():
    """Verify the Z.AI GLM agent uses the correct model identifier."""
    # zai-glm-4.7 is the latest GLM model on Cerebras as of January 2026
    assert zai_glm_agent.MODEL_NAME == "zai-glm-4.7"
    assert zai_glm_agent.AGENT_METADATA["MODEL_NAME"] == "zai-glm-4.7"


def test_zai_glm_agent_metadata():
    """Verify agent metadata is correctly configured."""
    assert zai_glm_agent.AGENT_NAME == "ZaiGlmAgent"
    assert "GLM 4.7" in zai_glm_agent.AGENT_DESCRIPTION
    assert zai_glm_agent.AGENT_METADATA["AGENT_VERSION"] == "1.0.0"
