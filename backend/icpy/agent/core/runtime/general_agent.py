from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from ..llm.base import BaseLLMClient
from .models import Message, Role


class GeneralAgent:
    """Provider-agnostic agent that streams responses via a BaseLLMClient.

    Tool-call handling is intentionally left to provider-specific streaming handlers
    in Part 1. This keeps behavior stable while we introduce the contract.
    """

    def __init__(self, llm: BaseLLMClient, model: str) -> None:
        self.llm = llm
        self.model = model

    def run(
        self,
        *,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterable[str]:
        """Stream assistant text given system+history messages.

        Messages must already be normalized for the provider (preserve multimodal arrays
        for user messages when applicable).
        """
        # Ensure system is first
        msgs: List[Dict[str, Any]] = []
        has_system = any(m.get("role") == "system" for m in messages)
        if not has_system:
            msgs.append({"role": "system", "content": system_prompt})
        else:
            # Caller provided system; ignore system_prompt param
            pass
        msgs.extend(messages)

        # Delegate streaming to the provider client
        return self.llm.stream_chat(model=self.model, messages=msgs, tools=tools, max_tokens=max_tokens)
