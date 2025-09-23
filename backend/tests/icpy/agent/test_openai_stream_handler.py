from icpy.agent.helpers import OpenAIStreamingHandler

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
