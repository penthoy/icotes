"""
API tests for Hop endpoints (Phase 1 behavior, no real SSH required)
"""

import asyncio
from fastapi.testclient import TestClient
from fastapi import FastAPI
from icpy.api.endpoints.hop import router as hop_router


def create_test_app():
    app = FastAPI()
    app.include_router(hop_router)
    return app


def test_hop_credentials_api(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    app = create_test_app()
    client = TestClient(app)

    # Create credential
    resp = client.post("/api/hop/credentials", json={
        "name": "cred1",
        "host": "example.com",
        "username": "user",
        "auth": "password"
    })
    assert resp.status_code == 200
    cred = resp.json()

    # List
    resp = client.get("/api/hop/credentials")
    assert resp.status_code == 200
    creds = resp.json()
    assert len(creds) == 1

    # Get
    cid = creds[0]["id"]
    resp = client.get(f"/api/hop/credentials/{cid}")
    assert resp.status_code == 200
    assert resp.json()["host"] == "example.com"

    # Update
    resp = client.put(f"/api/hop/credentials/{cid}", json={"port": 2200})
    assert resp.status_code == 200
    assert resp.json()["port"] == 2200

    # Delete
    resp = client.delete(f"/api/hop/credentials/{cid}")
    assert resp.status_code == 200


def test_hop_key_upload(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    app = create_test_app()
    client = TestClient(app)

    files = {"file": ("id_rsa", b"TEST", "application/octet-stream")}
    resp = client.post("/api/hop/keys", files=files)
    assert resp.status_code == 200
    assert "keyId" in resp.json()


def test_hop_status_connect_disconnect(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    app = create_test_app()
    client = TestClient(app)

    # Initially local/disconnected
    resp = client.get("/api/hop/status")
    assert resp.status_code == 200
    assert resp.json()["contextId"] == "local"

    # Create a credential and try connect (no asyncssh available pathway is tolerated)
    cred = client.post("/api/hop/credentials", json={
        "name": "c1",
        "host": "127.0.0.1",
        "username": "u",
        "auth": "password"
    }).json()

    resp = client.post("/api/hop/connect", json={"credentialId": cred["id"]})
    assert resp.status_code == 200
    # Status may be connected (stub) or error if asyncssh present and connection fails; both acceptable for API shape
    assert "status" in resp.json()

    # Disconnect should return to local
    resp = client.post("/api/hop/disconnect")
    assert resp.status_code == 200
    assert resp.json()["contextId"] == "local"
