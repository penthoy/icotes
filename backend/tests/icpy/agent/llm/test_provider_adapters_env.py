import pytest

from icpy.agent.core.llm.base import ProviderNotConfigured
from icpy.agent.core.llm.openrouter_client import OpenRouterClientAdapter
from icpy.agent.core.llm.groq_client import GroqClientAdapter
from icpy.agent.core.llm.anthropic_client import AnthropicClientAdapter
from icpy.agent.core.llm.gemini_client import GeminiClientAdapter


def _expect_missing_key(monkeypatch, key: str, adapter_cls):
    monkeypatch.delenv(key, raising=False)
    adapter = adapter_cls()
    with pytest.raises(ProviderNotConfigured):
        list(adapter.stream_chat(model="m", messages=[{"role": "user", "content": "hi"}]))


def test_openrouter_requires_key(monkeypatch):
    _expect_missing_key(monkeypatch, "OPENROUTER_API_KEY", OpenRouterClientAdapter)


def test_groq_requires_key(monkeypatch):
    _expect_missing_key(monkeypatch, "GROQ_API_KEY", GroqClientAdapter)


def test_anthropic_requires_key(monkeypatch):
    _expect_missing_key(monkeypatch, "ANTHROPIC_API_KEY", AnthropicClientAdapter)


def test_gemini_requires_key(monkeypatch):
    _expect_missing_key(monkeypatch, "GOOGLE_API_KEY", GeminiClientAdapter)
