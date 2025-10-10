import pytest

from icpy.agent.tools.imagen_utils import resolve_dimensions, ASPECT_RATIO_SPECS, guess_mime_from_ext


def test_resolve_dimensions_explicit_width_height():
    assert resolve_dimensions(800, 600, None, has_input_image=False) == (800, 600)


def test_resolve_dimensions_aspect_ratio_preset():
    w, h = resolve_dimensions(None, None, '1:1', has_input_image=False)
    assert (w, h) == (ASPECT_RATIO_SPECS['1:1'][0], ASPECT_RATIO_SPECS['1:1'][1])


def test_resolve_dimensions_default_square_for_generation():
    assert resolve_dimensions(None, None, None, has_input_image=False) == (1024, 1024)


def test_resolve_dimensions_preserve_edit_when_no_hints():
    assert resolve_dimensions(None, None, None, has_input_image=True) == (None, None)


def test_guess_mime_from_ext():
    assert guess_mime_from_ext('/path/to/file.png') == 'image/png'
    assert guess_mime_from_ext('image.JPG') == 'image/jpeg'
    assert guess_mime_from_ext('noext', fallback='x/y') == 'x/y'
