"""
Route Service Client — routes non-LLM service requests through the Route Proxy.

When the Route Proxy is configured (ICOTES_ROUTE_URL + ICOTESROUTE_API_KEY),
this client sends ElevenLabs, Tavily, Serper, and AtlasCloud requests
through the proxy instead of calling provider APIs directly.

This eliminates the need for individual service API keys in SaaS deployments.
"""

import os
import logging
from typing import Any, Optional

import httpx

from icpy.core.http_retry import retry_async_operation

logger = logging.getLogger(__name__)


class RouteServiceClient:
    """Routes non-LLM service requests through the icotes Route Proxy.

    Supports:
        - ElevenLabs: TTS, STT, SFX, Music
        - Tavily / Serper: Web search
        - AtlasCloud: Image generation, Video generation

    All requests use the same auth (Bearer ICOTESROUTE_API_KEY) and base URL.
    """

    def __init__(
        self,
        route_url: Optional[str] = None,
        route_key: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """Initialize with proxy URL and key from env or explicit args."""
        self.route_url = (route_url or os.getenv("ICOTES_ROUTE_URL", "")).rstrip("/")
        self.route_key = route_key or os.getenv("ICOTESROUTE_API_KEY", "")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def is_available(self) -> bool:
        """Return True if route proxy is configured for service routing."""
        return bool(self.route_url and self.route_key)

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Lazy-init the httpx async client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.route_url,
                headers={"Authorization": f"Bearer {self.route_key}"},
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _enrich_connection_error(self, exc: Exception, path: str) -> Exception:
        """Re-raise ConnectError / ConnectTimeout with route URL context."""
        if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)):
            msg = (
                f"Route proxy unreachable at {self.route_url}{path} — "
                f"check that icotesroute is running and ICOTES_ROUTE_URL is correct. "
                f"(original: {exc})"
            )
            logger.error("[RouteService] %s", msg)
            return ConnectionError(msg)
        return exc

    async def _post_with_retry(self, path: str, payload: dict[str, Any]) -> httpx.Response:
        """POST with small retry budget for transient transport failures."""
        async def _operation() -> httpx.Response:
            client = await self._ensure_client()
            return await client.post(path, json=payload)

        try:
            return await retry_async_operation(
                _operation,
                on_retry_reset=self.close,
                logger=logger,
                operation_name=f"RouteService POST {path}",
            )
        except Exception as exc:
            raise self._enrich_connection_error(exc, path) from exc

    async def _get_with_retry(self, path: str) -> httpx.Response:
        """GET with small retry budget for transient transport failures."""
        async def _operation() -> httpx.Response:
            client = await self._ensure_client()
            return await client.get(path)

        try:
            return await retry_async_operation(
                _operation,
                on_retry_reset=self.close,
                logger=logger,
                operation_name=f"RouteService GET {path}",
            )
        except Exception as exc:
            raise self._enrich_connection_error(exc, path) from exc

    # ── ElevenLabs TTS ──────────────────────────────────────────────────────

    async def tts(
        self,
        text: str,
        voice: str = "alloy",
        model_id: str = "eleven_multilingual_v2",
        output_format: str = "mp3_44100_128",
        **kwargs: Any,
    ) -> bytes:
        """Text-to-speech via Route Proxy → ElevenLabs.

        Returns raw audio bytes.
        """
        payload = {
            "model": "elevenlabs/tts-v2",
            "input": text,
            "voice": voice,
            "model_id": model_id,
            "output_format": output_format,
            **kwargs,
        }
        logger.info("[RouteService] TTS request: %d chars, voice=%s", len(text), voice)
        resp = await self._post_with_retry("/v1/audio/speech", payload)
        resp.raise_for_status()
        return resp.content

    # ── ElevenLabs STT ──────────────────────────────────────────────────────

    async def stt(
        self,
        audio_data: bytes,
        model_id: str = "scribe_v2",
        language_code: Optional[str] = None,
        **kwargs: Any,
    ) -> dict:
        """Speech-to-text via Route Proxy → ElevenLabs.

        Returns transcription dict.
        """
        # Send audio as base64 in JSON body
        import base64
        payload: dict[str, Any] = {
            "model": "elevenlabs/stt-v2",
            "file": base64.b64encode(audio_data).decode("utf-8"),
            "model_id": model_id,
            **kwargs,
        }
        if language_code:
            payload["language_code"] = language_code

        logger.info("[RouteService] STT request: %d bytes", len(audio_data))
        resp = await self._post_with_retry("/v1/audio/transcriptions", payload)
        resp.raise_for_status()
        return resp.json()

    # ── ElevenLabs SFX ──────────────────────────────────────────────────────

    async def sfx(
        self,
        text: str,
        duration_seconds: float = 1.0,
        prompt_influence: float = 0.3,
        **kwargs: Any,
    ) -> bytes:
        """Sound effects generation via Route Proxy → ElevenLabs.

        Returns raw audio bytes.
        """
        payload = {
            "model": "elevenlabs/sfx-v1",
            "text": text,
            "duration_seconds": duration_seconds,
            "prompt_influence": prompt_influence,
            **kwargs,
        }
        logger.info("[RouteService] SFX request: '%s', %.1fs", text[:50], duration_seconds)
        resp = await self._post_with_retry("/v1/audio/sfx", payload)
        resp.raise_for_status()
        return resp.content

    # ── ElevenLabs Music ────────────────────────────────────────────────────

    async def music(
        self,
        prompt: str,
        duration_seconds: float = 5.0,
        **kwargs: Any,
    ) -> bytes:
        """Music generation via Route Proxy → ElevenLabs.

        Returns raw audio bytes.
        """
        payload = {
            "model": "elevenlabs/music-v1",
            "prompt": prompt,
            "duration_seconds": duration_seconds,
            **kwargs,
        }
        logger.info("[RouteService] Music request: '%s', %.1fs", prompt[:50], duration_seconds)
        resp = await self._post_with_retry("/v1/audio/music", payload)
        resp.raise_for_status()
        return resp.content

    # ── Web Search (Tavily / Serper) ────────────────────────────────────────

    async def search(
        self,
        query: str,
        provider: str = "tavily",
        max_results: int = 5,
        search_depth: str = "basic",
        include_answer: bool = True,
        **kwargs: Any,
    ) -> dict:
        """Web search via Route Proxy → Tavily or Serper.

        Returns search results dict.
        """
        payload: dict[str, Any] = {
            "model": f"{provider}/search",
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": include_answer,
            **kwargs,
        }
        logger.info("[RouteService] Search request: '%s' via %s", query[:50], provider)
        resp = await self._post_with_retry("/v1/search", payload)
        resp.raise_for_status()
        return resp.json()

    # ── AtlasCloud Image Generation ─────────────────────────────────────────

    async def generate_image(
        self,
        prompt: str,
        model: str = "atlascloud/image-v1",
        **kwargs: Any,
    ) -> dict:
        """Image generation via Route Proxy → AtlasCloud.

        Returns generation result dict.
        """
        payload = {
            "model": model,
            "prompt": prompt,
            **kwargs,
        }
        logger.info("[RouteService] Image generation: '%s'", prompt[:50])
        resp = await self._post_with_retry("/v1/images/generations", payload)
        resp.raise_for_status()
        return resp.json()

    # ── AtlasCloud Video Generation ─────────────────────────────────────────

    async def generate_video(
        self,
        prompt: str,
        model: str = "atlascloud/seedance-v1-lite",
        **kwargs: Any,
    ) -> dict:
        """Video generation via Route Proxy → AtlasCloud.

        Returns generation result dict (may include polling ID for async jobs).
        """
        payload = {
            "model": model,
            "prompt": prompt,
            **kwargs,
        }
        logger.info("[RouteService] Video generation: '%s'", prompt[:50])
        resp = await self._post_with_retry("/v1/videos/generations", payload)
        resp.raise_for_status()
        return resp.json()

    async def get_prediction(self, prediction_id: str) -> dict:
        """Get Atlas prediction status via Route proxy.

        This endpoint is used to complete async Atlas image/video jobs in proxy-only mode.
        """
        resp = await self._get_with_retry(f"/v1/predictions/{prediction_id}")
        resp.raise_for_status()
        return resp.json()


# ── Singleton accessor ──────────────────────────────────────────────────────

_route_service_client: Optional[RouteServiceClient] = None


def get_route_service_client() -> RouteServiceClient:
    """Get or create the singleton RouteServiceClient."""
    global _route_service_client
    if _route_service_client is None:
        _route_service_client = RouteServiceClient()
    return _route_service_client


def is_route_service_available() -> bool:
    """Check if non-LLM service routing through proxy is available."""
    return get_route_service_client().is_available
