import os
import base64
import io
import asyncio
import pytest
from fastapi.testclient import TestClient

from icpy.gateway.api_gateway import create_fastapi_app
from icpy.services.image_reference_service import get_image_reference_service
from PIL import Image


def make_png_file(tmpdir, size=(100, 60), color=(0, 200, 50)):
    from pathlib import Path
    p = Path(tmpdir) / 'sample.png'
    img = Image.new('RGB', size, color)
    img.save(p, 'PNG')
    return str(p)


@pytest.fixture
def app(tmp_path, monkeypatch):
    # Force workspace root to tmp_path
    os.environ['WORKSPACE_ROOT'] = str(tmp_path)
    app = create_fastapi_app()
    return app


def test_media_endpoint_serves_full_and_thumbnail(app, tmp_path):
    client = TestClient(app)

    # Create an image file in workspace and register a reference
    img_path = make_png_file(tmp_path, size=(200, 120))

    # Build a minimal reference by invoking the real service via create_reference
    svc = get_image_reference_service(workspace_path=str(tmp_path))

    # The create_reference expects the file to be present on disk with same filename
    filename = os.path.basename(img_path)
    with open(img_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')

    ref = asyncio.get_event_loop().run_until_complete(
        svc.create_reference(image_data=b64, filename=filename, prompt='t', model='m', mime_type='image/png')
    )

    # Full image should 200
    r1 = client.get(f"/api/media/image/{ref.image_id}")
    assert r1.status_code == 200
    assert r1.headers['content-type'].startswith('image/')

    # Thumbnail should 200
    r2 = client.get(f"/api/media/image/{ref.image_id}?thumbnail=true")
    assert r2.status_code == 200
    assert r2.headers['content-type'].startswith('image/')
