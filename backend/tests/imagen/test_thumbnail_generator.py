import os
from pathlib import Path
from icpy.utils.thumbnail_generator import generate_thumbnail, calculate_checksum
from PIL import Image


def _make_png(tmpdir: Path, name: str = 'img.png', size=(256, 128)) -> str:
    path = tmpdir / name
    img = Image.new('RGB', size, (255, 0, 0))
    img.save(path, 'PNG')
    return str(path)


def test_generate_thumbnail(tmp_path):
    img_path = _make_png(tmp_path)
    thumbs = tmp_path / 'thumbs'
    result = generate_thumbnail(img_path, str(thumbs), max_size=(64, 64), scale_factor=0.5, quality=60, image_id='test')
    assert Path(result['path']).exists()
    assert result['width'] <= 64 and result['height'] <= 64
    assert result['size_bytes'] > 0
    assert isinstance(result['base64'], str) and len(result['base64']) > 0


def test_calculate_checksum(tmp_path):
    img_path = _make_png(tmp_path)
    checksum = calculate_checksum(img_path)
    assert isinstance(checksum, str) and len(checksum) == 64
