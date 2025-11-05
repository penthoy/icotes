from typing import Iterable

from icpy.agent.agents import anthropic_agent
from icpy.agent.core.llm.anthropic_client import AnthropicClientAdapter


def test_anthropic_agent_delegates_to_general_agent(monkeypatch):
    # Patch adapter.stream_chat to avoid network calls and API keys
    def fake_stream_chat(self, *, model, messages, tools=None, max_tokens=None) -> Iterable[str]:
        yield "OK"
    monkeypatch.setattr(AnthropicClientAdapter, "stream_chat", fake_stream_chat, raising=True)

    out = "".join(anthropic_agent.chat("hello", []))
    assert out == "OK"
