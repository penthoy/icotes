"""Tests for AtlasCloudVideoToVideoSoundTool error classification."""

import pytest
from unittest.mock import AsyncMock, patch

from icpy.agent.tools.atlascloud.v2v_sound_tool import AtlasCloudVideoToVideoSoundTool


@pytest.mark.asyncio
async def test_route_404_runtime_error_is_not_wrapped_as_unexpected():
    """Route-side 404s should be surfaced directly for easier ticketing/debugging."""
    tool = AtlasCloudVideoToVideoSoundTool()

    mock_client = AsyncMock()
    mock_client.generate_video_to_video_with_sound.side_effect = RuntimeError(
        "Route endpoint not found (404): http://192.168.2.202:9100/v1/videos/generations. "
        "model=atlascloud/mmaudio-v2 This likely indicates an icotesroute endpoint/model mapping issue."
    )

    with patch.object(tool, "_process_video", new=AsyncMock(return_value="https://example.com/input.mp4")), \
         patch.object(tool, "_get_client", return_value=mock_client):
        result = await tool.execute(
            video="/home/penthoy/icotes/workspace/videos/test_video.mp4",
            prompt="Soft ambient electronic music with gentle synth pads",
            filename="test_video_with_sound",
        )

    assert result.success is False
    assert result.error is not None
    assert "Route endpoint not found (404)" in result.error
    assert "/v1/videos/generations" in result.error
    assert "Unexpected error" not in result.error
