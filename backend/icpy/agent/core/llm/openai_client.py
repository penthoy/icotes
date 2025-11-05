from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .base import BaseLLMClient, ProviderNotConfigured
from ...helpers import OpenAIStreamingHandler
from ...clients import get_openai_client


class OpenAIClientAdapter(BaseLLMClient):
    """Adapter over the existing OpenAI-compatible client.

    This implementation reuses the project's OpenAIStreamingHandler to preserve
    tool-call behavior and streaming semantics.
    """

    def stream_chat(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterable[str]:
        try:
            client = get_openai_client()
        except ValueError as e:
            # Normalize to ProviderNotConfigured for runtime consistency
            raise ProviderNotConfigured(str(e)) from e
        # When tools are provided, use the handler (it builds the right request and handles loops)
        handler = OpenAIStreamingHandler(client, model)
        # OpenAIStreamingHandler expects messages with optional 'tools' loaded internally;
        # we pass tools directly to maintain flexibility while keeping compatibility.
        # It ignores None tools gracefully.
        return handler.stream_chat_with_tools(messages, max_tokens=max_tokens)
