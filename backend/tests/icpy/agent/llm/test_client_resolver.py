import pytest

from icpy.agent.client_resolver import resolve_client


def _clear_provider_env(monkeypatch):
    """Clear all provider-specific env vars so route fallback can be tested."""
    for key in [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
        "DEEPSEEK_API_KEY",
        "CEREBRAS_API_KEY",
        "OPENROUTER_API_KEY",
        "DASHSCOPE_API_KEY",
        "MOONSHOT_API_KEY",
        "OLLAMA_URL",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_resolver_prefers_direct_key_over_route(monkeypatch):
    """When direct API key is set, use it even if route proxy is available."""
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-direct")
    monkeypatch.setenv("ICOTES_ROUTE_URL", "http://127.0.0.1:9100")
    monkeypatch.setenv("ICOTESROUTE_API_KEY", "route-key")

    client, resolved_model = resolve_client("openai", "gpt-5.2")

    assert resolved_model == "gpt-5.2"
    assert "api.openai.com" in str(client.base_url)


def test_resolver_routes_openai_through_proxy(monkeypatch):
    """OpenAI without direct key should route through proxy with provider/model."""
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("ICOTES_ROUTE_URL", "http://127.0.0.1:9100")
    monkeypatch.setenv("ICOTESROUTE_API_KEY", "route-key")

    client, resolved_model = resolve_client("openai", "gpt-5.2")

    assert resolved_model == "openai/gpt-5.2"
    assert str(client.base_url).startswith("http://127.0.0.1:9100/v1")


def test_resolver_routes_anthropic_through_proxy(monkeypatch):
    """Any non-OpenAI provider without direct key should also route through proxy."""
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("ICOTES_ROUTE_URL", "http://127.0.0.1:9100")
    monkeypatch.setenv("ICOTESROUTE_API_KEY", "route-key")

    client, resolved_model = resolve_client("anthropic", "claude-opus-4-5-20251101")

    assert resolved_model == "anthropic/claude-opus-4-5-20251101"
    assert str(client.base_url).startswith("http://127.0.0.1:9100/v1")


def test_resolver_preserves_already_prefixed_model(monkeypatch):
    """Model already correctly prefixed with route provider should pass through unchanged."""
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("ICOTES_ROUTE_URL", "http://127.0.0.1:9100")
    monkeypatch.setenv("ICOTESROUTE_API_KEY", "route-key")

    _client, resolved_model = resolve_client("openai", "openai/gpt-5.2")

    assert resolved_model == "openai/gpt-5.2"


def test_resolver_prepends_provider_for_vendor_prefixed_model(monkeypatch):
    """Model with a vendor prefix (e.g. Groq's 'openai/gpt-oss-120b') must get
    the route provider prepended so the proxy routes to the right upstream.

    Without this fix the proxy would see 'openai/gpt-oss-120b' and route to
    OpenAI instead of Groq.
    """
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("ICOTES_ROUTE_URL", "http://127.0.0.1:9100")
    monkeypatch.setenv("ICOTESROUTE_API_KEY", "route-key")

    _client, resolved_model = resolve_client("groq", "openai/gpt-oss-120b")

    assert resolved_model == "groq/openai/gpt-oss-120b"


def test_resolver_vendor_prefix_idempotent(monkeypatch):
    """If the model is already correctly tagged with route provider, don't double-prefix."""
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("ICOTES_ROUTE_URL", "http://127.0.0.1:9100")
    monkeypatch.setenv("ICOTESROUTE_API_KEY", "route-key")

    _client, resolved_model = resolve_client("groq", "groq/openai/gpt-oss-120b")

    assert resolved_model == "groq/openai/gpt-oss-120b"


def test_resolver_ollama_always_direct_error_without_url(monkeypatch):
    """Ollama is always direct — should error if OLLAMA_URL not set, even with route proxy."""
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("ICOTES_ROUTE_URL", "http://127.0.0.1:9100")
    monkeypatch.setenv("ICOTESROUTE_API_KEY", "route-key")

    with pytest.raises(ValueError, match="OLLAMA_URL is not set"):
        resolve_client("ollama", "llama3.2")


def test_resolver_ollama_direct_when_url_set(monkeypatch):
    """Ollama with OLLAMA_URL set should use direct client."""
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("OLLAMA_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("ICOTES_ROUTE_URL", "http://127.0.0.1:9100")
    monkeypatch.setenv("ICOTESROUTE_API_KEY", "route-key")

    client, resolved_model = resolve_client("ollama", "llama3.2")

    assert resolved_model == "llama3.2"
    assert "localhost" in str(client.base_url)


def test_resolver_error_when_no_key_and_no_route(monkeypatch):
    """No direct key and no route proxy — should give clear config error."""
    _clear_provider_env(monkeypatch)
    monkeypatch.delenv("ICOTES_ROUTE_URL", raising=False)
    monkeypatch.delenv("ICOTES_ROUTE_ENABLED", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY is not set"):
        resolve_client("openai", "gpt-5.2")


def test_resolver_routes_all_providers_through_proxy(monkeypatch):
    """All non-Ollama providers should route through proxy when no direct keys."""
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("ICOTES_ROUTE_URL", "http://127.0.0.1:9100")
    monkeypatch.setenv("ICOTESROUTE_API_KEY", "route-key")

    providers_and_models = [
        ("openai", "gpt-5.2"),
        ("anthropic", "claude-opus-4-5-20251101"),
        ("google", "gemini-3-pro"),
        ("groq", "llama-3.1-8b"),
        ("cerebras", "gpt-oss-120b"),
        ("deepseek", "deepseek-chat"),
        ("moonshot", "kimi-k2.5"),
        ("alibaba", "qwen3-coder"),
    ]

    for provider, model in providers_and_models:
        client, resolved_model = resolve_client(provider, model)
        assert resolved_model == f"{provider}/{model}", f"Failed for {provider}"
        assert str(client.base_url).startswith("http://127.0.0.1:9100/v1"), f"Failed for {provider}"
