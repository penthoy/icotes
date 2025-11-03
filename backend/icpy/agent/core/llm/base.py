from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, Iterable, List, Optional


class ProviderNotConfigured(Exception):
    """Raised when a provider is not properly configured (e.g., missing API key)."""


class ProviderError(Exception):
    """Raised for provider-specific errors that should surface to callers."""


class BaseLLMClient(ABC):
    """Minimal provider-agnostic interface for chat completions.

    Implementations must not perform network calls during tests unless explicitly mocked.
    """

    @abstractmethod
    def stream_chat(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterable[str]:
        """Return an iterator/generator of response text chunks.

        Tool call handling is orchestrated at a higher level (runtime), not here.
        """
        raise NotImplementedError
