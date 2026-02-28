from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .base import BaseLLMClient, ProviderNotConfigured
from ...helpers import OpenAIStreamingHandler
from ...client_resolver import resolve_client


class GroqClientAdapter(BaseLLMClient):
    def stream_chat(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Iterable[str]:
        try:
            client, resolved_model = resolve_client("groq", model)
        except ValueError as e:
            raise ProviderNotConfigured(str(e)) from e
        handler = OpenAIStreamingHandler(client, resolved_model)
        return handler.stream_chat_with_tools(messages, max_tokens=max_tokens, extra_params=extra_params)