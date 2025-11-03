from icpy.agent.core.tools.registry import ToolRegistryView


def test_tool_registry_view_can_list_tools():
    view = ToolRegistryView()
    tools = list(view.all())
    # Should be iterable; we don't assert count because it varies
    assert isinstance(tools, list)


def test_tool_registry_view_get_unknown_returns_none():
    view = ToolRegistryView()
    assert view.get("__unknown_tool__") is None
