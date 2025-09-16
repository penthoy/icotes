import os, sys, io, json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend root (parent dir of 'icpy') on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from icpy.gateway.api_gateway import create_fastapi_app
from importlib import reload
import icpy.services.media_service as media_service_module

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    # Override media base dir via env
    tmpdir = tmp_path_factory.mktemp("media")
    os.environ["MEDIA_BASE_DIR"] = str(tmpdir)
    # Allow text/ mime types for this suite (Phase 1 tests exercise generic files)
    os.environ.setdefault("MEDIA_ALLOWED_TYPES", "image/,video/,audio/,application/pdf,text/")
    # Reload media service module so it picks up new env vars before instantiation
    reload(media_service_module)
    app = create_fastapi_app()
    with TestClient(app) as c:
        yield c

class TestMediaAPI:
    def test_upload_image(self, client):
        content = b"fake image data"
        files = {"file": ("test.png", content, "image/png")}
        r = client.post("/api/media/upload", files=files)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "attachment" in data
        att = data["attachment"]
        assert att["filename"] == "test.png"
        assert att["mime_type"] == "image/png"
        assert att["kind"] == "images"

    def test_list_images(self, client):
        r = client.get("/api/media/list/images")
        assert r.status_code == 200
        data = r.json()
        assert "files" in data
        assert any(f["name"].endswith("test.png") for f in data["files"])  # uploaded earlier

    def test_download_via_id(self, client):
        # Upload new file and then fetch via id path search
        files = {"file": ("note.txt", b"hello", "text/plain")}
        r = client.post("/api/media/upload", files=files)
        assert r.status_code == 200
        att_id = r.json()["attachment"]["id"]
        r2 = client.get(f"/api/media/file/{att_id}")
        assert r2.status_code == 200
        assert r2.content == b"hello"

    def test_delete_file(self, client):
        files = {"file": ("deleteme.txt", b"bye", "text/plain")}
        r = client.post("/api/media/upload", files=files)
        att = r.json()["attachment"]
        name = att["filename"]
        # list to find actual stored name pattern
        list_r = client.get("/api/media/list/files")
        stored = next(f for f in list_r.json()["files"] if name in f["name"])  # hashed id prefix
        del_r = client.delete(f"/api/media/files/{stored['name']}")
        assert del_r.status_code == 200
        assert del_r.json()["success"] is True

    def test_zip_endpoint(self, client):
        # Upload two files
        for idx in range(2):
            files = {"file": (f"z{idx}.txt", f"data{idx}".encode(), "text/plain")}
            client.post("/api/media/upload", files=files)
        list_r = client.get("/api/media/list/files")
        rel_paths = [f["rel_path"] for f in list_r.json()["files"][:2]]
        r = client.post("/api/media/zip", json={"paths": rel_paths})
        assert r.status_code == 200
        assert r.headers.get("content-type") == "application/zip"
        assert len(r.content) > 0
