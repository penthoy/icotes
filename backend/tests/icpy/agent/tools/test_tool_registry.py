"""
Tests for tool registry
"""

import pytest
from icpy.agent.tools.tool_registry import ToolRegistry, get_tool_registry
from icpy.agent.tools.base_tool import BaseTool, ToolResult


class MockTool1(BaseTool):
    """First mock tool for testing"""
    
    def __init__(self):
        self.name = "tool1"
        self.description = "First test tool"
        self.parameters = {"type": "object", "properties": {}}
    
    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data="tool1 result")


class MockTool2(BaseTool):
    """Second mock tool for testing"""
    
    def __init__(self):
        self.name = "tool2"
        self.description = "Second test tool"
        self.parameters = {"type": "object", "properties": {}}
    
    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data="tool2 result")


class TestToolRegistry:
    """Test ToolRegistry class"""
    
    def test_registry_init(self):
        """Test registry initialization"""
        registry = ToolRegistry()
        assert registry._tools == {}
        assert registry.all() == []
    
    def test_register_tool(self):
        """Test registering a tool"""
        registry = ToolRegistry()
        tool = MockTool1()
        
        registry.register(tool)
        assert "tool1" in registry._tools
        assert registry.get("tool1") is tool
    
    def test_register_multiple_tools(self):
        """Test registering multiple tools"""
        registry = ToolRegistry()
        tool1 = MockTool1()
        tool2 = MockTool2()
        
        registry.register(tool1)
        registry.register(tool2)
        
        assert len(registry._tools) == 2
        assert registry.get("tool1") is tool1
        assert registry.get("tool2") is tool2
    
    def test_register_idempotent(self):
        """Test that registering the same tool twice is idempotent"""
        registry = ToolRegistry()
        tool1 = MockTool1()
        tool2 = MockTool1()  # Different instance, same name
        
        registry.register(tool1)
        registry.register(tool2)
        
        # Should have the second instance (last one wins)
        assert len(registry._tools) == 1
        assert registry.get("tool1") is tool2
    
    def test_get_nonexistent_tool(self):
        """Test getting a tool that doesn't exist"""
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None
    
    def test_get_all_tools(self):
        """Test getting all registered tools"""
        registry = ToolRegistry()
        tool1 = MockTool1()
        tool2 = MockTool2()
        
        registry.register(tool1)
        registry.register(tool2)
        
        all_tools = registry.all()
        assert len(all_tools) == 2
        assert tool1 in all_tools
        assert tool2 in all_tools
    
    def test_get_all_tools_empty(self):
        """Test getting all tools when registry is empty"""
        registry = ToolRegistry()
        assert registry.all() == []


class TestGlobalRegistry:
    """Test global registry functions"""
    
    def test_get_tool_registry_singleton(self):
        """Test that get_tool_registry returns the same instance"""
        # Reset global registry for clean test
        import icpy.agent.tools.tool_registry as registry_module
        registry_module._registry = None
        
        registry1 = get_tool_registry()
        registry2 = get_tool_registry()
        
        assert registry1 is registry2
        assert isinstance(registry1, ToolRegistry)
    
    def test_get_tool_registry_persistence(self):
        """Test that tools persist across get_tool_registry calls"""
        # Reset global registry for clean test
        import icpy.agent.tools.tool_registry as registry_module
        registry_module._registry = None
        
        registry1 = get_tool_registry()
        tool = MockTool1()
        registry1.register(tool)
        
        registry2 = get_tool_registry()
        assert registry2.get("tool1") is tool 