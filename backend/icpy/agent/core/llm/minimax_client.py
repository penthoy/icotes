"""MiniMax LLM client adapter.

Uses resolve_client to pick direct MiniMax API or icotesroute fallback,
following the same pattern as all other provider adapters.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .base import BaseLLMClient, ProviderNotConfigured
from ...helpers import OpenAIStreamingHandler
from ...client_resolver import resolve_client


class MiniMaxClientAdapter(BaseLLMClient):
    """Adapter for MiniMax models (e.g. MiniMax-M2.5).

    Priority: direct MINIMAX_API_KEY → icotesroute fallback.
    """

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
            client, resolved_model = resolve_client("minimax", model)
        except ValueError as e:
            raise ProviderNotConfigured(str(e)) from e

        handler = OpenAIStreamingHandler(client, resolved_model)
        return handler.stream_chat_with_tools(messages, max_tokens=max_tokens, extra_params=extra_params)
