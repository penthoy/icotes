from typing import Any, Dict, Iterable, List, Optional

from icpy.agent.core.runtime.general_agent import GeneralAgent
from icpy.agent.core.llm.base import BaseLLMClient


class FakeLLM(BaseLLMClient):
    def __init__(self, output: str):
        self.output = output

    def stream_chat(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterable[str]:
        # Return chunks of the output for streaming behavior
        for ch in [self.output[:2], self.output[2:]]:
            if ch:
                yield ch


def test_general_agent_streams_content():
    llm = FakeLLM("hello")
    agent = GeneralAgent(llm, model="test-model")
    chunks = list(
        agent.run(
            system_prompt="sys",
            messages=[{"role": "user", "content": "hi"}],
            tools=None,
        )
    )
    assert "".join(chunks) == "hello"
