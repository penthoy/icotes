import pytest
from icpy.agent.tools.base_tool import BaseTool

class DummyTool(BaseTool):
    def __init__(self):
        super().__init__()
        self.name = "dummy"
        self.description = ""
        self.parameters = {"type": "object", "properties": {}}
    async def execute(self, **kwargs):
        return None

@pytest.mark.asyncio
async def test_parse_path_parameter_local_absolute():
    tool = DummyTool()
    ctx, path = await tool._parse_path_parameter("/tmp/file.txt")
    assert ctx == "local"
    assert path.startswith("/") and path.endswith("file.txt")

@pytest.mark.asyncio
async def test_parse_path_parameter_windows_drive():
    tool = DummyTool()
    ctx, path = await tool._parse_path_parameter("C:/Users/test/file.txt")
    # Windows-style paths should not be treated as namespaces
    assert ctx == "local"
    assert ":/" in path or path.startswith("/")

@pytest.mark.asyncio
async def test_format_path_info_minimal():
    tool = DummyTool()
    info = await tool._format_path_info("/tmp/demo.txt")
    assert isinstance(info, dict)
    assert "formatted_path" in info
    assert "namespace" in info
    assert "absolute_path" in info
