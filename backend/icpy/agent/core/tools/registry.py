from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from ...tools import get_tool_registry


class ToolRegistryView:
    """Lightweight wrapper over the global tool registry.

    Provides a stable interface for the generalized agent runtime without
    coupling tests to the full registry implementation.
    """

    def __init__(self) -> None:
        self._registry = get_tool_registry()

    def get(self, name: str) -> Optional[Any]:
        return self._registry.get(name)

    def all(self) -> Iterable[Any]:
        return self._registry.all()
