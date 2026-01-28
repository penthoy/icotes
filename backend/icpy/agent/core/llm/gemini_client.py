"""
Legacy Gemini client adapter using OpenAI-compatible endpoint.

DEPRECATED: This adapter uses Google's OpenAI-compatible API endpoint which does NOT
properly support Gemini 3's thought signatures for tool calling. Use GeminiNativeClientAdapter
from gemini_native_client.py instead for Gemini 3 models.

This adapter is kept for potential fallback scenarios or non-tool-calling use cases.
"""
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
        
        Gemini's OpenAI-compatible endpoint has several limitations:
        1. Doesn't support 'system' role - merge into first user message
        2. May not handle 'tool' role messages properly - convert to assistant messages
        3. Requires conversations to start with 'user' role
        
        Phase 3: Preserves vendor_parts for thought signature support
        """
        if not messages:
            return messages
        
        result = []
        system_content = None
        
        # Extract system message and transform other roles
        for msg in messages:
            role = msg.get("role")
            
            if role == "system":
                # Extract system content to merge later
                system_content = msg.get("content", "")
            elif role == "tool":
                # Convert tool messages to assistant messages with formatted content
                # This ensures Gemini can understand tool results
                tool_content = msg.get("content", "")
                result.append({
                    "role": "assistant",
                    "content": f"[Tool result]: {tool_content}"
                })
            elif role == "assistant":
                # Phase 3: Preserve vendor_parts if present for thought signature replay
                assistant_msg = {**msg}  # Copy the message
                
                # Check if this is a Gemini response with vendor_parts
                if msg.get('vendor_parts') and msg.get('vendor_model') and 'gemini' in msg.get('vendor_model', '').lower():
                    # For now, keep vendor_parts as-is
                    # The OpenAI-compatible endpoint may or may not support replaying these
                    # We'll log for observability
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"[GEMINI-DEBUG] Found vendor_parts in assistant message (count={len(msg['vendor_parts'])})")
                    # Note: If OpenAI-compat doesn't support vendor_parts, we'll need SDK path (Phase 4)
                
                result.append(assistant_msg)
            else:
                # Keep user and other messages as-is
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