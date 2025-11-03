from typing import Iterable

from icpy.agent.agents import gemini_agent
from icpy.agent.core.llm.gemini_client import GeminiClientAdapter


def test_gemini_agent_delegates_to_general_agent(monkeypatch):
    # Patch adapter.stream_chat to avoid network calls and API keys
    def fake_stream_chat(self, *, model, messages, tools=None, max_tokens=None) -> Iterable[str]:
        yield "OK"
    monkeypatch.setattr(GeminiClientAdapter, "stream_chat", fake_stream_chat, raising=True)

    out = "".join(gemini_agent.chat("hello", []))
    assert out == "OK"
