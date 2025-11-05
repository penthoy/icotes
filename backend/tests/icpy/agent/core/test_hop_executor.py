import asyncio
from typing import Any, Dict

import pytest

from icpy.agent.core.runtime.hop_executor import HopAwareToolExecutor


class DummyTool:
    name = "dummy_tool"

    async def execute(self, **kwargs: Dict[str, Any]):
        class Result:
            def __init__(self):
                self.success = True
                self.data = {"echo": kwargs}
                self.error = None
        return Result()


class DummyRegistry:
    def __init__(self):
        self._tools = {"dummy_tool": DummyTool()}

    def get(self, name):
        return self._tools.get(name)

    def all(self):
        return list(self._tools.values())


class DummyView:
    def __init__(self):
        self._registry = DummyRegistry()

    def get(self, name):
        return self._registry.get(name)

    def all(self):
        return self._registry.all()


@pytest.mark.asyncio
async def test_hop_executor_executes_tool():
    exec = HopAwareToolExecutor(registry=DummyView())
    res = await exec.execute("dummy_tool", path="/tmp/a")
    assert res["success"] is True
    assert res["data"]["echo"]["path"] == "/tmp/a"
