from icpy.agent.helpers import OpenAIStreamingHandler
from unittest.mock import MagicMock

class DummyClient:
    class Chat:
        class Completions:
            def create(self, **kwargs):
                # Simulate minimal stream with one content chunk, no tool calls
                class Chunk:
                    class Choices:
                        class Delta:
                            content = "ok"
                            tool_calls = None
                        delta = Delta()
                        finish_reason = "stop"
                    choices = [Choices()]
                yield Chunk()
        completions = Completions()
    chat = Chat()


def test_handler_accepts_rich_user_messages():
    handler = OpenAIStreamingHandler(DummyClient(), "gpt-5-mini")
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": [
            {"type": "text", "text": "caption"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAA"}},
        ]},
    ]
    chunks = list(handler.stream_chat_with_tools(messages))
    assert "ok" in "".join(chunks)


class DummyClientWithSimulatedToolBlock:
    class Chat:
        class Completions:
            def __init__(self):
                self.call_count = 0
            
            def create(self, **kwargs):
                self.call_count += 1
                
                # First call: return simulated tool block (what some Chinese models do)
                if self.call_count == 1:
                    simulated = (
                        "\n\n🔧 **Executing tools...**\n\n"
                        "📋 **generate_image**: {\"prompt\":\"a calm android portrait\",\"filename\":\"simulated.png\"}\n"
                        "✅ **Success**: {\"savedToWorkspace\":true}\n\n"
                        "🔧 **Tool execution complete. Continuing...**\n\n"
                    )
                    class Chunk1:
                        class Choices:
                            class Delta:
                                content = simulated
                                tool_calls = None
                            delta = Delta()
                            finish_reason = "stop"
                        choices = [Choices()]
                    yield Chunk1()
                # Second call (after tool execution): return final response
                else:
                    final_response = "Here's the image showing a calm android portrait."
                    class Chunk2:
                        class Choices:
                            class Delta:
                                content = final_response
                                tool_calls = None
                            delta = Delta()
                            finish_reason = "stop"
                        choices = [Choices()]
                    yield Chunk2()
        
        completions = Completions()
    chat = Chat()


def test_handler_executes_fallback_for_simulated_media_tool_block():
    handler = OpenAIStreamingHandler(DummyClientWithSimulatedToolBlock(), "kimi-k2.5")
    handler.tool_executor.execute_tool_call_sync = MagicMock(return_value={
        "success": True,
        "data": {
            "message": "Image generated successfully",
            "savedToWorkspace": True,
            "filePath": "simulated.png",
        },
    })

    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "Generate an image"},
    ]

    chunks = list(handler.stream_chat_with_tools(messages))
    combined = "".join(chunks)

    handler.tool_executor.execute_tool_call_sync.assert_called_once()
    call_args = handler.tool_executor.execute_tool_call_sync.call_args[0]
    assert call_args[0] == "generate_image"
    assert call_args[1]["prompt"] == "a calm android portrait"
    assert "Detected simulated tool output" in combined


def test_simulated_tool_parser_extracts_json_arguments():
    text = (
        "🔧 **Executing tools...**\n"
        "📋 **generate_image**: {\"prompt\":\"hello\",\"aspect_ratio\":\"1:1\"}\n"
        "🔧 **Tool execution complete. Continuing...**"
    )

    parsed = OpenAIStreamingHandler._extract_tool_args_from_simulated_blocks(text)
    assert parsed == [("generate_image", {"prompt": "hello", "aspect_ratio": "1:1"})]
