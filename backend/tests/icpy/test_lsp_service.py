"""Integration tests for LSP Service.

This suite is intentionally skipped.

The LSP service is deprecated (not wired into the app lifecycle, no active API
endpoints, and no frontend integration), but keeping this file (skipped) helps
document prior coverage intent without breaking pytest collection.
"""

import pytest

pytestmark = [pytest.mark.skip(reason="LSP service is deprecated")]


def test_lsp_service_deprecated_placeholder():
    assert True
