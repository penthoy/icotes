import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Ensure backend root (parent dir of 'icpy') on path
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from icpy.api.rest_api import RestAPI


@pytest.fixture()
def client():
    app = FastAPI(title="Test RestAPI Raw")
    # Register routes (no need to fully initialize services for /api/files/raw local path serving)
    RestAPI(app)
    with TestClient(app) as c:
        yield c


class TestFilesRawRange:
    def test_files_raw_serves_full_file_with_accept_ranges(self, client, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        test_file = tmp_path / 'range_test.bin'
        payload = b'0123456789ABCDEFGHIJ'  # 20 bytes
        test_file.write_bytes(payload)

        r = client.get('/api/files/raw', params={'path': str(test_file)})
        assert r.status_code == 200, r.text
        assert r.headers.get('accept-ranges') == 'bytes'
        assert r.content == payload

    def test_files_raw_range_header_returns_206(self, client, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        test_file = tmp_path / 'range_test_206.bin'
        payload = b'0123456789ABCDEFGHIJ'  # 20 bytes
        test_file.write_bytes(payload)

        r = client.get(
            '/api/files/raw',
            params={'path': str(test_file)},
            headers={'Range': 'bytes=0-9'},
        )

        assert r.status_code == 206, r.text
        assert r.headers.get('accept-ranges') == 'bytes'
        assert r.headers.get('content-range') == 'bytes 0-9/20'
        assert r.headers.get('content-length') == '10'
        assert r.content == payload[:10]

    def test_files_raw_suffix_range_header(self, client, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        test_file = tmp_path / 'range_test_suffix.bin'
        payload = b'0123456789ABCDEFGHIJ'  # 20 bytes
        test_file.write_bytes(payload)

        r = client.get(
            '/api/files/raw',
            params={'path': str(test_file)},
            headers={'Range': 'bytes=-4'},
        )

        assert r.status_code == 206, r.text
        assert r.headers.get('content-range') == 'bytes 16-19/20'
        assert r.content == payload[-4:]
