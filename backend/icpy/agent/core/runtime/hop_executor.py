from __future__ import annotations

from typing import Any, Dict

from ..tools.registry import ToolRegistryView


class HopAwareToolExecutor:
    """Execute registered tools; routing is delegated inside each tool via ContextRouter.

    This executor simply finds the tool and runs it with provided kwargs.
    """

    def __init__(self, registry: ToolRegistryView | None = None) -> None:
        self.registry = registry or ToolRegistryView()

    async def execute(self, name: str, **kwargs: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.registry.get(name)
        if not tool:
            return {"success": False, "error": f"Tool {name} not found"}
        try:
            result = await tool.execute(**kwargs)
            return {"success": result.success, "data": result.data, "error": result.error}
        except Exception as e:
            return {"success": False, "error": str(e)}
