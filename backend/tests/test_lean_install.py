"""
Lean-install smoke test.

The default Docker image (and `uv sync --no-dev` without extras) ships only the
core dependencies. Optional packages live in extras (documents, media, discord,
google, agents-frameworks, providers-sdk). This test simulates their absence in a
subprocess -- even when they are installed in the current environment -- and
verifies that the app still boots and degrades gracefully.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Top-level modules that belong to optional extras.
BLOCKED_TOP_LEVEL = [
    "crewai", "langchain", "langchain_community", "langchain_openai",
    "langgraph", "langsmith", "agents",
    "pandas", "pdfplumber", "docx", "pptx", "openpyxl", "reportlab", "xlrd", "pyxlsb",
    "yt_dlp", "elevenlabs", "discord",
]
# Fully-qualified names only (google.genai / google.auth are core).
BLOCKED_QUALIFIED = ["google.generativeai"]

SCRIPT = textwrap.dedent(
    """
    import asyncio, importlib.abc, os, sys, tempfile

    BLOCKED_TOP = set({top!r})
    BLOCKED_FULL = set({full!r})

    class Blocker(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in BLOCKED_TOP or name in BLOCKED_FULL:
                raise ImportError("blocked optional dependency: " + name)
            return None

    sys.meta_path.insert(0, Blocker())

    # Sanity: the blocker works
    for mod in ("crewai", "docx", "discord", "google.generativeai"):
        try:
            __import__(mod)
        except ImportError:
            pass
        else:
            raise SystemExit("blocker failed for " + mod)

    # Core google packages must remain importable
    import google.genai  # noqa: F401

    os.environ["WORKSPACE_ROOT"] = tempfile.mkdtemp()
    os.environ["DISCORD_BOT_TOKEN"] = "x"

    # 1. App imports with ICPY_AVAILABLE True
    import main
    assert main.ICPY_AVAILABLE is True, "ICPY_AVAILABLE flipped by a missing optional dependency"

    # 2. Tool registry builds
    from icpy.agent.tools import get_tool_registry
    registry = get_tool_registry()
    assert registry.get("read_doc") is not None

    # 3. Discord bot start does not raise without discord.py
    from icpy.services import discord_bot_service
    assert discord_bot_service.DISCORD_AVAILABLE is False
    asyncio.run(main.start_discord_bot())
    asyncio.run(main.stop_discord_bot())

    # 4. Framework compatibility layer degrades to None instead of raising
    from icpy.core.framework_compatibility import (
        AgentConfig, FrameworkCompatibilityLayer, FrameworkType,
    )
    layer = FrameworkCompatibilityLayer()
    agent = asyncio.run(layer.create_agent(AgentConfig(
        framework=FrameworkType.CREWAI, name="x", role="r", goal="g", backstory="b",
    )))
    assert agent is None

    # 5. Document tool reports a helpful install hint
    from icpy.agent.tools.read_doc_tool import ReadDocTool
    path = os.path.join(os.environ["WORKSPACE_ROOT"], "sample.docx")
    with open(path, "wb") as fh:
        fh.write(b"PK\\x03\\x04 not a real docx")
    result = asyncio.run(ReadDocTool().execute(filePath=path))
    assert result.success is False, result
    assert "documents" in (result.error or ""), result.error

    # 6. Health endpoint responds
    from fastapi.testclient import TestClient
    with TestClient(main.app) as client:
        assert client.get("/healthz").status_code == 200

    print("LEAN_OK")
    """
).format(top=BLOCKED_TOP_LEVEL, full=BLOCKED_QUALIFIED)


def test_app_boots_without_optional_extras(tmp_path):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(BACKEND_DIR), env.get("PYTHONPATH")]))
    proc = subprocess.run(
        [sys.executable, "-c", SCRIPT],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0 and "LEAN_OK" in proc.stdout, (
        f"stdout:\n{proc.stdout[-3000:]}\nstderr:\n{proc.stderr[-3000:]}"
    )
