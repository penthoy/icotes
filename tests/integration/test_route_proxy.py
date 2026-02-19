#!/usr/bin/env python3
"""
Quick connectivity test for the icotes route proxy server.

Tests the proxy at a given URL (defaults to the LAN IP for local testing).
Reads ICOTES_ROUTE_KEY from env or accepts it as a CLI argument.

Usage:
    uv run python tests/integration/test_route_proxy.py --key <your-key>
    uv run python tests/integration/test_route_proxy.py --url http://192.168.2.202:9100 --key <key>
"""

import argparse
import json
import os
import sys
import httpx


# ── default values ─────────────────────────────────────────────────────────────
DEFAULT_URL = os.getenv("ICOTES_ROUTE_URL", "http://192.168.2.202:9100")
# No default key — must be explicitly provided via --key or env var
DEFAULT_KEY = os.getenv("ICOTES_ROUTE_KEY", "")

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"{GREEN}  ✓ {msg}{RESET}")


def fail(msg: str) -> None:
    print(f"{RED}  ✗ {msg}{RESET}")


def info(msg: str) -> None:
    print(f"{YELLOW}  → {msg}{RESET}")


# ── individual tests ────────────────────────────────────────────────────────────

def test_health(base_url: str) -> bool:
    """GET /healthz should return 200."""
    print("\n[1] Health check")
    try:
        r = httpx.get(f"{base_url}/healthz", timeout=5)
        if r.status_code == 200:
            ok(f"GET /healthz → {r.status_code}")
            return True
        else:
            fail(f"Unexpected status {r.status_code}: {r.text}")
            return False
    except httpx.ConnectError as e:
        fail(f"Connection failed: {e}")
        return False


def test_auth_reject(base_url: str) -> bool:
    """POST /v1/chat/completions with a wrong key should return 401."""
    print("\n[2] Auth rejection (wrong key)")
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "ping"}],
    }
    try:
        r = httpx.post(
            f"{base_url}/v1/chat/completions",
            json=payload,
            headers={"Authorization": "Bearer irt-this-is-a-wrong-key"},
            timeout=5,
        )
        if r.status_code == 401:
            ok(f"POST /v1/chat/completions with bad key → 401 (correctly rejected)")
            return True
        else:
            fail(f"Expected 401 but got {r.status_code}: {r.text[:200]}")
            return False
    except httpx.ConnectError as e:
        fail(f"Connection failed: {e}")
        return False


def test_chat_completion(base_url: str, key: str) -> bool:
    """POST /v1/chat/completions (non-streaming) with a real key."""
    print("\n[3] Non-streaming chat completion")
    if not key:
        info("ICOTES_ROUTE_KEY not set — skipping (pass --key or set env var)")
        return True

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Reply with exactly: pong"}],
        "max_tokens": 10,
        "stream": False,
    }
    try:
        r = httpx.post(
            f"{base_url}/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {key}"},
            timeout=30,
        )
        if r.status_code == 200:
            body = r.json()
            content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
            ok(f"POST /v1/chat/completions → 200  |  reply: {content!r}")
            return True
        else:
            fail(f"Unexpected status {r.status_code}: {r.text[:300]}")
            return False
    except httpx.ConnectError as e:
        fail(f"Connection failed: {e}")
        return False


def test_streaming_chat(base_url: str, key: str) -> bool:
    """POST /v1/chat/completions with stream=true and collect SSE chunks."""
    print("\n[4] Streaming chat completion (SSE)")
    if not key:
        info("ICOTES_ROUTE_KEY not set — skipping")
        return True

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Count 1 2 3"}],
        "max_tokens": 20,
        "stream": True,
    }
    try:
        chunks_received = 0
        content_parts: list[str] = []

        with httpx.stream(
            "POST",
            f"{base_url}/v1/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "Accept": "text/event-stream",
            },
            timeout=30,
        ) as r:
            if r.status_code != 200:
                fail(f"Unexpected status {r.status_code}")
                return False

            for line in r.iter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if token := delta.get("content"):
                            content_parts.append(token)
                        chunks_received += 1
                    except json.JSONDecodeError:
                        pass

        assembled = "".join(content_parts)
        ok(f"Streaming → {chunks_received} chunks  |  assembled: {assembled!r}")
        return True

    except httpx.ConnectError as e:
        fail(f"Connection failed: {e}")
        return False


# ── main ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Test icotes route proxy connectivity")
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Route proxy base URL (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--key",
        default=DEFAULT_KEY,
        help="Route proxy API key (default: $ICOTES_ROUTE_KEY env var)",
    )
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    key = args.key

    # Mask key in output — show only last 4 chars
    masked_key = f"***{key[-4:]}" if len(key) > 4 else "<not set>" if not key else "***"

    print(f"\nicotes Route Proxy Test")
    print(f"  URL : {base_url}")
    print(f"  Key : {masked_key}")

    results = [
        test_health(base_url),
        test_auth_reject(base_url),
        test_chat_completion(base_url, key),
        test_streaming_chat(base_url, key),
    ]

    passed = sum(results)
    total = len(results)

    print(f"\n{'='*50}")
    if passed == total:
        print(f"{GREEN}All {total} tests passed.{RESET}")
    else:
        print(f"{RED}{total - passed}/{total} test(s) failed.{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
