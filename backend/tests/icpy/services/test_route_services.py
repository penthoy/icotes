"""Tests for RouteServiceClient — non-LLM service routing through the proxy."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from icpy.services.route_services import (
    RouteServiceClient,
    get_route_service_client,
    is_route_service_available,
)


@pytest.fixture
def route_client():
    """Create a RouteServiceClient with test credentials."""
    return RouteServiceClient(
        route_url="http://127.0.0.1:9100",
        route_key="test-route-key",
    )


@pytest.fixture
def no_route_client():
    """Create a RouteServiceClient without credentials."""
    return RouteServiceClient(route_url="", route_key="")


def test_is_available_with_credentials(route_client):
    assert route_client.is_available is True


def test_is_not_available_without_credentials(no_route_client):
    assert no_route_client.is_available is False


def test_is_route_service_available_from_env(monkeypatch):
    monkeypatch.setenv("ICOTES_ROUTE_URL", "http://127.0.0.1:9100")
    monkeypatch.setenv("ICOTESROUTE_API_KEY", "test-key")
    # Reset singleton
    import icpy.services.route_services as mod
    mod._route_service_client = None

    assert is_route_service_available() is True

    # Clean up singleton
    mod._route_service_client = None


def test_is_route_service_not_available_without_env(monkeypatch):
    monkeypatch.delenv("ICOTES_ROUTE_URL", raising=False)
    monkeypatch.delenv("ICOTESROUTE_API_KEY", raising=False)
    import icpy.services.route_services as mod
    mod._route_service_client = None

    assert is_route_service_available() is False

    mod._route_service_client = None


@pytest.mark.asyncio
async def test_tts_sends_correct_payload(route_client):
    """TTS should POST to /v1/audio/speech with elevenlabs/tts-v2 model."""
    mock_response = MagicMock()
    mock_response.content = b"fake-audio-bytes"
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False
    route_client._client = mock_client

    result = await route_client.tts(text="Hello world", voice="alloy")

    assert result == b"fake-audio-bytes"
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args[0][0] == "/v1/audio/speech"
    payload = call_args[1]["json"]
    assert payload["model"] == "elevenlabs/tts-v2"
    assert payload["input"] == "Hello world"
    assert payload["voice"] == "alloy"


@pytest.mark.asyncio
async def test_search_sends_correct_payload(route_client):
    """Search should POST to /v1/search with tavily/search model."""
    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value={"answer": "test", "results": []})
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False
    route_client._client = mock_client

    result = await route_client.search(query="latest AI news")

    assert result["answer"] == "test"
    call_args = mock_client.post.call_args
    assert call_args[0][0] == "/v1/search"
    payload = call_args[1]["json"]
    assert payload["model"] == "tavily/search"
    assert payload["query"] == "latest AI news"


@pytest.mark.asyncio
async def test_generate_video_sends_correct_payload(route_client):
    """Video gen should POST to /v1/videos/generations."""
    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value={"id": "123", "status": "processing"})
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False
    route_client._client = mock_client

    result = await route_client.generate_video(prompt="a cat walking")

    call_args = mock_client.post.call_args
    assert call_args[0][0] == "/v1/videos/generations"
    payload = call_args[1]["json"]
    assert payload["model"] == "atlascloud/seedance-v1-lite"
    assert payload["prompt"] == "a cat walking"


@pytest.mark.asyncio
async def test_sfx_sends_correct_payload(route_client):
    """SFX should POST to /v1/audio/sfx with elevenlabs/sfx-v1 model."""
    mock_response = MagicMock()
    mock_response.content = b"fake-sfx-bytes"
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False
    route_client._client = mock_client

    result = await route_client.sfx(text="explosion sound", duration_seconds=2.0)

    assert result == b"fake-sfx-bytes"
    call_args = mock_client.post.call_args
    assert call_args[0][0] == "/v1/audio/sfx"
    payload = call_args[1]["json"]
    assert payload["model"] == "elevenlabs/sfx-v1"


@pytest.mark.asyncio
async def test_music_sends_correct_payload(route_client):
    """Music should POST to /v1/audio/music with elevenlabs/music-v1 model."""
    mock_response = MagicMock()
    mock_response.content = b"fake-music-bytes"
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False
    route_client._client = mock_client

    result = await route_client.music(prompt="upbeat electronic", duration_seconds=5.0)

    assert result == b"fake-music-bytes"
    call_args = mock_client.post.call_args
    assert call_args[0][0] == "/v1/audio/music"
    payload = call_args[1]["json"]
    assert payload["model"] == "elevenlabs/music-v1"


@pytest.mark.asyncio
async def test_generate_image_sends_correct_payload(route_client):
    """Image gen should POST to /v1/images/generations."""
    mock_response = MagicMock()
    mock_response.json = MagicMock(return_value={"url": "https://example.com/img.png"})
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False
    route_client._client = mock_client

    result = await route_client.generate_image(prompt="a sunset over mountains")

    call_args = mock_client.post.call_args
    assert call_args[0][0] == "/v1/images/generations"
    payload = call_args[1]["json"]
    assert payload["model"] == "atlascloud/image-v1"


@pytest.mark.asyncio
async def test_tts_404_has_route_context(route_client):
    """Route 404 should be surfaced as clear route-side endpoint issue."""
    req = httpx.Request("POST", "http://127.0.0.1:9100/v1/audio/speech")
    resp_404 = httpx.Response(404, request=req)

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("404", request=req, response=resp_404))

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False
    route_client._client = mock_client

    with pytest.raises(RuntimeError) as exc:
        await route_client.tts(text="hello", voice="george")

    assert "Route endpoint not found (404)" in str(exc.value)
    assert "/v1/audio/speech" in str(exc.value)
    assert "elevenlabs/tts-v2" in str(exc.value)


@pytest.mark.asyncio
async def test_video_404_has_route_context(route_client):
    """Atlas route 404 should include endpoint and model for ticketing."""
    req = httpx.Request("POST", "http://127.0.0.1:9100/v1/videos/generations")
    resp_404 = httpx.Response(404, request=req)

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("404", request=req, response=resp_404))

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False
    route_client._client = mock_client

    with pytest.raises(RuntimeError) as exc:
        await route_client.generate_video(prompt="ambient", model="atlascloud/mmaudio-v2")

    assert "Route endpoint not found (404)" in str(exc.value)
    assert "/v1/videos/generations" in str(exc.value)
    assert "atlascloud/mmaudio-v2" in str(exc.value)
