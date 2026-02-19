from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .base import BaseLLMClient, ProviderNotConfigured
from ...helpers import OpenAIStreamingHandler
from ...client_resolver import resolve_client


class MoonshotClientAdapter(BaseLLMClient):
    """Adapter for Moonshot (Kimi) OpenAI-compatible API."""

    def stream_chat(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterable[str]:
        try:
            client, resolved_model = resolve_client("moonshot", model)
        except ValueError as e:
            raise ProviderNotConfigured(str(e)) from e
        
        # For kimi-k2.5, disable thinking mode when using tools
        # Ref: https://platform.moonshot.ai/docs/guide/kimi-k2-5-quickstart#tool-use-compatibility
        extra_params = {}
        if "k2.5" in resolved_model.lower() and tools:
            extra_params["thinking"] = {"type": "disabled"}
        
        handler = OpenAIStreamingHandler(client, resolved_model)
        return handler.stream_chat_with_tools(messages, max_tokens=max_tokens, extra_params=extra_params)
