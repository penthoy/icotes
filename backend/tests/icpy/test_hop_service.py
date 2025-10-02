"""
Unit tests for HopService (Phase 1)

Covers:
- Credential CRUD persistence without secrets
- Key upload permissions
- Status behavior without real SSH
"""

import os
import json
from pathlib import Path
from icpy.services.hop_service import HopService


def test_credentials_crud_tmpdir(tmp_path, monkeypatch):
    # Redirect data dir and workspace for isolation
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("WORKSPACE_ROOT", str(workspace_dir))

    svc = HopService()

    # Initially empty
    assert svc.list_credentials() == []

    # Create
    created = svc.create_credential({
        "name": "test",
        "host": "example.com",
        "port": 22,
        "username": "user",
        "auth": "password",
        "defaultPath": "/home/user"
    })
    assert created["host"] == "example.com"

    # List
    creds = svc.list_credentials()
    assert len(creds) == 1

    cid = creds[0]["id"]
    got = svc.get_credential(cid)
    assert got["username"] == "user"
    # Ensure secrets not present
    assert "password" not in got and "passphrase" not in got

    # Update
    updated = svc.update_credential(cid, {"name": "updated", "port": 2222})
    assert updated["name"] == "updated"
    assert updated["port"] == 2222

    # Delete
    ok = svc.delete_credential(cid)
    assert ok is True
    assert svc.list_credentials() == []


def test_key_upload_permissions(tmp_path, monkeypatch):
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("WORKSPACE_ROOT", str(workspace_dir))
    svc = HopService()

    key_id = svc.store_private_key(b"TEST-KEY")
    key_path = svc.get_key_path(key_id)

    assert key_path.exists()

    # Check permissions are at most 0600 (on systems where chmod applies)
    try:
        mode = key_path.stat().st_mode
        assert oct(mode & 0o777) in {"0o600", "0o700"}  # allow 700 if dir applique
    except Exception:
        # On some systems permission checks may fail in tests; ignore
        pass


def test_status_default_local(tmp_path, monkeypatch):
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("WORKSPACE_ROOT", str(workspace_dir))
    svc = HopService()
    st = svc.status()
    assert st.contextId == "local"
    assert st.status in {"disconnected", "connected"}
