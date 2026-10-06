"""
Tests for Nano Banana Agent wrapper.
Validates agent model identifier and metadata configuration.
"""
import pytest

from icpy.agent.agents import nano_banana_agent


def test_nano_banana_agent_model_identifier():
    """Verify the Nano Banana agent uses Gemini 3 Pro Image model (Nano Banana Pro)."""
    # gemini-3-pro-image-preview is Nano Banana Pro (ACTIVE, no deprecation announced)
    # gemini-3-pro-preview (without -image) is the TEXT model deprecated March 9 2026
    # gemini-3.1-pro-preview is text/reasoning only — NOT for image generation
    assert nano_banana_agent.AGENT_MODEL_ID == "gemini-3-pro-image-preview"
    assert nano_banana_agent.MODEL_NAME == "gemini-3-pro-image-preview"


def test_nano_banana_agent_metadata():
    """Verify agent metadata is correctly configured."""
    assert nano_banana_agent.AGENT_NAME == "NanoBananaAgent"
    assert "Gemini" in nano_banana_agent.AGENT_DESCRIPTION
    assert nano_banana_agent.AGENT_METADATA["AGENT_VERSION"] == "1.2.0"


def test_nano_banana_dependencies_available():
    """Verify dependencies are available for NanoBananaAgent."""
    # Dependencies should be available if Google SDK is installed
    assert hasattr(nano_banana_agent, 'DEPENDENCIES_AVAILABLE')


def test_nano_banana_get_tools():
    """Verify get_tools returns empty list (Gemini generates images natively)."""
    if nano_banana_agent.DEPENDENCIES_AVAILABLE:
        tools = nano_banana_agent.get_tools()
        assert tools == []


# --- genai is None (lean image) behavior -------------------------------------

@pytest.fixture
def no_genai(monkeypatch):
    if not nano_banana_agent.DEPENDENCIES_AVAILABLE:
        pytest.skip("NanoBananaAgent dependencies not available")
    monkeypatch.setattr(nano_banana_agent, "genai", None)
    monkeypatch.setattr(nano_banana_agent, "add_context_to_agent_prompt", lambda p: p)


def test_nano_banana_route_proxy_used_when_genai_missing_even_with_key(no_genai, monkeypatch):
    """With GOOGLE_API_KEY set but no legacy SDK, the route proxy path must be used."""
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy-key")
    monkeypatch.setattr(nano_banana_agent, "is_icotes_route_enabled", lambda: True)
    monkeypatch.setattr(
        nano_banana_agent, "resolve_client", lambda provider, model: (object(), "resolved-model")
    )
    seen = {}

    class FakeHandler:
        def __init__(self, client, model):
            seen["model"] = model

        def stream_chat_with_tools(self, messages):
            seen["messages"] = messages
            yield "proxied"

    monkeypatch.setattr(nano_banana_agent, "OpenAIStreamingHandler", FakeHandler)

    out = list(nano_banana_agent.chat("draw a cat", []))
    assert out == ["proxied"]
    assert seen["model"] == "resolved-model"
    assert seen["messages"][-1] == {"role": "user", "content": "draw a cat"}


def test_nano_banana_clear_message_when_genai_missing_and_no_proxy(no_genai, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy-key")
    monkeypatch.setattr(nano_banana_agent, "is_icotes_route_enabled", lambda: False)

    out = "".join(nano_banana_agent.chat("draw a cat", []))
    assert "'google' extra" in out
    assert "INSTALL_EXTRAS=google" in out
    assert "uv sync --extra google" in out


def test_nano_banana_missing_key_message_unchanged_when_genai_present(monkeypatch):
    if not nano_banana_agent.DEPENDENCIES_AVAILABLE:
        pytest.skip("NanoBananaAgent dependencies not available")
    monkeypatch.setattr(nano_banana_agent, "genai", object())
    monkeypatch.setattr(nano_banana_agent, "add_context_to_agent_prompt", lambda p: p)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr(nano_banana_agent, "is_icotes_route_enabled", lambda: False)

    out = "".join(nano_banana_agent.chat("draw a cat", []))
    assert "GOOGLE_API_KEY not set" in out
