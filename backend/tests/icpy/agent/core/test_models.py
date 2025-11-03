from icpy.agent.core.runtime.models import Message, Role, ToolCall, ToolResult


def test_message_and_roles():
    m = Message(role=Role.user, content="hi")
    assert m.role == Role.user
    assert m.content == "hi"


def test_tool_call_and_result_dataclasses():
    tc = ToolCall(name="read_file", arguments={"file_path": "/tmp/x"})
    assert tc.name == "read_file"
    assert tc.arguments["file_path"] == "/tmp/x"

    tr = ToolResult(name="read_file", success=True, data={"filePath": "/tmp/x", "content": ""})
    assert tr.success is True
    assert tr.name == "read_file"
