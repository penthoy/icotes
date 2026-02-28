"""Client resolver for LLM provider routing.

Decides whether to use a direct provider client or the Route proxy.

Priority:
1. Direct provider API key set → use direct provider client
2. Ollama → always direct (local service, never routed)
3. ICOTES_ROUTE_URL set → route through proxy with provider/model format
4. Otherwise → raise clear config error

The proxy accepts all providers and always expects `provider/model` format.
No per-provider feature flags needed — the proxy handles errors.
"""

import os
from typing import Callable

from openai import OpenAI

from .clients import (
    get_ali_client,
    get_anthropic_client,
    get_cerebras_client,
    get_deepseek_client,
    get_google_client,
    get_groq_client,
    get_icotes_route_client,
    get_minimax_client,
    get_moonshot_client,
    get_ollama_client,
    get_openai_client,
    get_openrouter_client,
    is_icotes_route_enabled,
)


ProviderClientGetter = Callable[[], OpenAI]


# Maps provider names to their direct client factory functions
_DIRECT_CLIENT_GETTERS: dict[str, ProviderClientGetter] = {
    "openai": get_openai_client,
    "anthropic": get_anthropic_client,
    "google": get_google_client,
    "groq": get_groq_client,
    "deepseek": get_deepseek_client,
    "cerebras": get_cerebras_client,
    "openrouter": get_openrouter_client,
    "alibaba": get_ali_client,
    "minimax": get_minimax_client,
    "moonshot": get_moonshot_client,
    "ollama": get_ollama_client,
}


# Maps provider names to the env var that holds their direct API key
_DIRECT_PROVIDER_ENV_KEYS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "alibaba": "DASHSCOPE_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "ollama": "OLLAMA_URL",
}


def _normalize_provider(provider: str) -> str:
    """Normalize provider name to lowercase, raise on empty."""
    normalized = provider.strip().lower()
    if not normalized:
        raise ValueError("Provider cannot be empty")
    return normalized


def _has_direct_provider_config(provider: str) -> bool:
    """Return True if the provider's direct API key/URL is set in env."""
    env_key = _DIRECT_PROVIDER_ENV_KEYS.get(provider)
    if not env_key:
        return False
    return bool(os.getenv(env_key))


def _resolve_route_model(provider: str, model: str) -> str:
    """Ensure model is in ``{provider}/{model}`` format for the route proxy.

    The route proxy always interprets the first path segment as the provider.
    If the model already carries a *different* vendor prefix (e.g. Groq exposes
    ``openai/gpt-oss-120b``) we must still prepend the route provider so the
    proxy routes to the correct upstream (``groq/openai/gpt-oss-120b``).

    The only exception is when the model string already starts with the correct
    route provider prefix (idempotent call), in which case it is passed through.
    """
    model_name = model.strip()
    if not model_name:
        raise ValueError("Model cannot be empty")

    # Already correctly prefixed — pass through (idempotent)
    if model_name.startswith(f"{provider}/"):
        return model_name

    # Always prefix with the route provider (even if model already has a vendor /)
    return f"{provider}/{model_name}"


def resolve_client(provider: str, model: str) -> tuple[OpenAI, str]:
    """
    Resolve the best client and model for a provider.

    Priority:
    1. Direct provider credential exists → direct provider client
    2. Ollama → always direct (never routed through proxy)
    3. Route proxy enabled (ICOTES_ROUTE_URL set) → route with provider/model
    4. Otherwise → raise clear configuration error
    """
    normalized_provider = _normalize_provider(provider)

    # Validate provider is known
    direct_client_getter = _DIRECT_CLIENT_GETTERS.get(normalized_provider)
    if not direct_client_getter:
        raise ValueError(f"Unsupported provider '{provider}'")

    # Priority 1: Direct API key exists
    if _has_direct_provider_config(normalized_provider):
        return direct_client_getter(), model

    # Priority 2: Ollama always goes direct (local service)
    if normalized_provider == "ollama":
        raise ValueError(
            "OLLAMA_URL is not set. Ollama is a local service and cannot be "
            "routed through the proxy. Set OLLAMA_URL (e.g. http://localhost:11434/v1)."
        )

    # Priority 3: Route proxy fallback
    if is_icotes_route_enabled():
        route_client = get_icotes_route_client()
        route_model = _resolve_route_model(normalized_provider, model)
        return route_client, route_model

    # No direct key and no route — clear error
    expected_key = _DIRECT_PROVIDER_ENV_KEYS.get(normalized_provider, "<provider_key>")
    raise ValueError(
        f"{expected_key} is not set and ICOTES_ROUTE_URL is not configured. "
        "Set a direct provider key or configure route proxy "
        "(ICOTES_ROUTE_URL + ICOTESROUTE_API_KEY)."
    )
