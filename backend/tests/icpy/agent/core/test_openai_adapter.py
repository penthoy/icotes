import os
import pytest

from icpy.agent.core.llm.openai_client import OpenAIClientAdapter
from icpy.agent.core.llm.base import ProviderNotConfigured


def test_openai_adapter_raises_when_no_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    adapter = OpenAIClientAdapter()
    with pytest.raises(ProviderNotConfigured):
        list(adapter.stream_chat(model="gpt-4o", messages=[{"role": "user", "content": "hi"}]))
