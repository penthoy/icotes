from typing import Iterable

import types

from icpy.agent.agents import openai_agent
from icpy.agent.core.llm.openai_client import OpenAIClientAdapter


def test_openai_agent_delegates_to_general_agent(monkeypatch):
    # Patch adapter.stream_chat to avoid network calls and API keys
    def fake_stream_chat(self, *, model, messages, tools=None, max_tokens=None) -> Iterable[str]:
        yield "OK"
    monkeypatch.setattr(OpenAIClientAdapter, "stream_chat", fake_stream_chat, raising=True)

    out = "".join(openai_agent.chat("hello", []))
    assert out == "OK"
