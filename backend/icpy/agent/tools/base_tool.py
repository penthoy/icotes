"""
Base tool interface for agent tools
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    """Result of tool execution"""
    success: bool
    data: Any = None
    error: Optional[str] = None


class BaseTool(ABC):
    """Base class for all agent tools"""
    
    def __init__(self):
        """Initialize tool with required properties"""
        self.name: str = ""
        self.description: str = ""
        self.parameters: Dict[str, Any] = {}
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters"""
        pass
    
    def to_openai_function(self) -> Dict[str, Any]:
        """Convert tool to OpenAI function calling format"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        } 