"""
Tests for path_utils utilities
"""

import pytest

from icpy.services.path_utils import format_namespaced_path, get_display_path_info
from icpy.services.context_router import get_context_router
from icpy.services.hop_service import get_hop_service


@pytest.mark.asyncio
async def test_format_namespaced_path_local():
    ns = await format_namespaced_path("local", "/workspace/file.txt")
    assert ns == "local:/workspace/file.txt"


@pytest.mark.asyncio
async def test_get_display_path_info_local_abs():
    info = await get_display_path_info("/workspace/notes.md")
    assert info["namespace"] == "local"
    assert info["context_id"] == "local"
    assert info["formatted_path"].startswith("local:/")
    assert info["absolute_path"].startswith("/")


@pytest.mark.asyncio
async def test_get_display_path_info_windows_drive_treated_as_path():
    # Simulate Windows-style path on non-Windows runner: should not be parsed as namespace
    info = await get_display_path_info("C:/temp/file.txt")
    assert info["namespace"] in ("local", "C")  # default to local context
    assert info["absolute_path"].startswith("C:/")


@pytest.mark.asyncio
async def test_format_namespaced_path_remote_friendly(monkeypatch):
    # Force stubbed connectivity so connect() doesn't attempt real SSH
    import icpy.services.hop_service as hop_mod
    monkeypatch.setattr(hop_mod, "ASYNCSSH_AVAILABLE", False, raising=False)

    hop = await get_hop_service()
    cred = hop.create_credential({
        "name": "hop1",
        "host": "example.com",
        "username": "user",
        "port": 22,
    })
    # Establish a stubbed connected session for this credential
    session = await hop.connect(cred["id"])  # type: ignore[index]
    assert session.status == "connected"

    # Should prefer friendly credential name (hop1) as namespace label
    ns_path = await format_namespaced_path(session.contextId, "/home/user/app.py")
    assert ns_path.startswith("hop1:/home/user/")

    # get_display_path_info should also reflect remote namespace when active
    info = await get_display_path_info("/home/user/app.py")
    assert info["namespace"] == "hop1"
    assert info["context_id"] == session.contextId
    assert info["is_remote"] is True
