"""
Tool registry for managing agent tools
"""

from typing import Dict, List, Optional
from .base_tool import BaseTool


class ToolRegistry:
    """Registry for managing agent tools"""
    
    def __init__(self):
        """Initialize empty registry"""
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool in the registry"""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def all(self) -> List[BaseTool]:
        """Get all registered tools"""
        return list(self._tools.values())


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry 