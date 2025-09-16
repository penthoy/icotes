import os
import pytest
from pathlib import Path
from icpy.services.media_service import get_media_service, MediaValidationError


def test_save_bytes_basic(tmp_path, monkeypatch):
    # Redirect media base dir to temp
    monkeypatch.setenv("MEDIA_BASE_DIR", str(tmp_path / "media"))
    # Allow text files for testing
    monkeypatch.setenv("MEDIA_ALLOWED_TYPES", "text/,image/,video/,audio/,application/pdf")
    # Force reinitialize singleton for test isolation
    from importlib import reload
    import icpy.services.media_service as ms
    reload(ms)
    service = ms.get_media_service()

    data = b"hello world" * 10
    attachment = service.save_bytes(data, "example.txt", "text/plain")

    assert attachment.id
    assert attachment.filename == "example.txt"
    assert attachment.size_bytes == len(data)
    stored_path = Path(service.base_dir) / attachment.relative_path
    assert stored_path.exists()
    assert stored_path.read_bytes() == data


def test_disallowed_mime(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_BASE_DIR", str(tmp_path / "media"))
    monkeypatch.setenv("MEDIA_ALLOWED_TYPES", "image/")  # Only images
    from importlib import reload
    import icpy.services.media_service as ms
    reload(ms)
    service = ms.get_media_service()

    # This should raise MediaValidationError from the reloaded module
    with pytest.raises(ms.MediaValidationError):
        service.save_bytes(b"data", "file.bin", "application/octet-stream")
