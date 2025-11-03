from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .base import BaseLLMClient, ProviderNotConfigured
from ...helpers import OpenAIStreamingHandler
from ...clients import get_google_client


class GeminiClientAdapter(BaseLLMClient):
    def stream_chat(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterable[str]:
        try:
            client = get_google_client()
        except ValueError as e:
            raise ProviderNotConfigured(str(e)) from e
        
        # Gemini API doesn't support 'system' role - merge it into first user message
        transformed_messages = self._transform_messages_for_gemini(messages)
        
        handler = OpenAIStreamingHandler(client, model)
        return handler.stream_chat_with_tools(transformed_messages, max_tokens=max_tokens)
    
    def _transform_messages_for_gemini(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform messages for Gemini API compatibility.
        
        Gemini requires conversations to start with 'user' role and doesn't support 'system' role.
        This merges any system message into the first user message.
        """
        if not messages:
            return messages
        
        result = []
        system_content = None
        
        # Extract system message if present
        for msg in messages:
            if msg.get("role") == "system":
                system_content = msg.get("content", "")
            else:
                result.append(msg)
        
        # Merge system content into first user message
        if system_content and result:
            first_user_idx = None
            for i, msg in enumerate(result):
                if msg.get("role") == "user":
                    first_user_idx = i
                    break
            
            if first_user_idx is not None:
                # Prepend system content to first user message
                original_content = result[first_user_idx].get("content", "")
                result[first_user_idx] = {
                    **result[first_user_idx],
                    "content": f"{system_content}\n\n{original_content}"
                }
        
        return result