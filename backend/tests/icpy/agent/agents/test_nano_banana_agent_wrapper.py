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
