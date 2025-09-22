"""
Agent tools package
"""

from .base_tool import BaseTool, ToolResult
from .tool_registry import ToolRegistry, get_tool_registry
from .read_file_tool import ReadFileTool
from .create_file_tool import CreateFileTool
from .replace_string_tool import ReplaceStringTool
from .run_terminal_tool import RunTerminalTool
from .semantic_search_tool import SemanticSearchTool
from .websearch_tools import WebSearchTool

__all__ = [
    "BaseTool",
    "ToolResult", 
    "ToolRegistry",
    "get_tool_registry",
    "ReadFileTool",
    "CreateFileTool", 
    "ReplaceStringTool",
    "RunTerminalTool",
    "SemanticSearchTool",
    "WebSearchTool"
]

# Auto-register all tools when module is imported
def _register_default_tools():
    """Register all default tools with the registry"""
    registry = get_tool_registry()
    
    # Register each tool
    registry.register(ReadFileTool())
    registry.register(CreateFileTool())
    registry.register(ReplaceStringTool())
    registry.register(RunTerminalTool())
    registry.register(SemanticSearchTool())
    registry.register(WebSearchTool())

# Register tools on import
_register_default_tools() 