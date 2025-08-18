"""
Tests for base tool interface
"""

import pytest
from icpy.agent.tools.base_tool import BaseTool, ToolResult


class MockTool(BaseTool):
    """Mock tool for testing base functionality"""
    
    def __init__(self):
        self.name = "mock_tool"
        self.description = "A mock tool for testing"
        self.parameters = {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Test input"
                }
            },
            "required": ["input"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        if kwargs.get("input") == "error":
            return ToolResult(success=False, error="Mock error")
        return ToolResult(success=True, data=f"Mock result: {kwargs.get('input', 'default')}")


class TestToolResult:
    """Test ToolResult dataclass"""
    
    def test_tool_result_success(self):
        """Test successful tool result"""
        result = ToolResult(success=True, data="test data")
        assert result.success is True
        assert result.data == "test data"
        assert result.error is None
    
    def test_tool_result_error(self):
        """Test error tool result"""
        result = ToolResult(success=False, error="test error")
        assert result.success is False
        assert result.data is None
        assert result.error == "test error"
    
    def test_tool_result_defaults(self):
        """Test tool result with defaults"""
        result = ToolResult(success=True)
        assert result.success is True
        assert result.data is None
        assert result.error is None


class TestBaseTool:
    """Test BaseTool interface"""
    
    def test_tool_properties(self):
        """Test tool has required properties"""
        tool = MockTool()
        assert tool.name == "mock_tool"
        assert tool.description == "A mock tool for testing"
        assert isinstance(tool.parameters, dict)
        assert "type" in tool.parameters
        assert "properties" in tool.parameters
    
    @pytest.mark.asyncio
    async def test_tool_execute_success(self):
        """Test successful tool execution"""
        tool = MockTool()
        result = await tool.execute(input="test")
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.data == "Mock result: test"
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_tool_execute_error(self):
        """Test tool execution with error"""
        tool = MockTool()
        result = await tool.execute(input="error")
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert result.error == "Mock error"
        assert result.data is None
    
    def test_to_openai_function(self):
        """Test OpenAI function schema generation"""
        tool = MockTool()
        schema = tool.to_openai_function()
        
        assert isinstance(schema, dict)
        assert schema["name"] == "mock_tool"
        assert schema["description"] == "A mock tool for testing"
        assert "parameters" in schema
        assert schema["parameters"]["type"] == "object"
        assert "properties" in schema["parameters"]
        assert "input" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["input"] 