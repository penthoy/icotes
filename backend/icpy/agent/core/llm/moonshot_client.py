from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .base import BaseLLMClient, ProviderNotConfigured
from ...helpers import OpenAIStreamingHandler
from ...clients import get_moonshot_client


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
        """
        Stream chat responses from the Moonshot (Kimi) API, optionally using tools and a token limit.
        
        If the provided `model` contains "k2.5" (case-insensitive) and `tools` is not empty, the adapter disables Kimi's thinking mode for compatibility when invoking the model.
        
        Parameters:
            model (str): Model identifier to use for the chat.
            messages (List[Dict[str, Any]]): Conversation messages formatted for the API.
            tools (Optional[List[Dict[str, Any]]]): Optional tool specifications to enable tool-augmented responses.
            max_tokens (Optional[int]): Optional maximum number of tokens to generate.
        
        Returns:
            Iterable[str]: An iterable that yields streamed text chunks from the model response.
        
        Raises:
            ProviderNotConfigured: If the Moonshot client cannot be obtained due to missing configuration.
        """
        try:
            client = get_moonshot_client()
        except ValueError as e:
            raise ProviderNotConfigured(str(e)) from e
        
        # For kimi-k2.5, disable thinking mode when using tools
        # Ref: https://platform.moonshot.ai/docs/guide/kimi-k2-5-quickstart#tool-use-compatibility
        extra_params = {}
        if "k2.5" in model.lower() and tools:
            extra_params["thinking"] = {"type": "disabled"}
        
        handler = OpenAIStreamingHandler(client, model)
        return handler.stream_chat_with_tools(messages, max_tokens=max_tokens, extra_params=extra_params)