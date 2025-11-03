from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .base import BaseLLMClient, ProviderNotConfigured
from ...helpers import OpenAIStreamingHandler
from ...clients import get_anthropic_client


class AnthropicClientAdapter(BaseLLMClient):
    def stream_chat(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterable[str]:
        try:
            client = get_anthropic_client()
        except ValueError as e:
            raise ProviderNotConfigured(str(e)) from e
        handler = OpenAIStreamingHandler(client, model)
        return handler.stream_chat_with_tools(messages, max_tokens=max_tokens)