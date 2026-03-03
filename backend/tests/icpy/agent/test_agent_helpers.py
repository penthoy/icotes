"""
Tests for agent helper functions including get_model_name_for_agent
and get_thinking_extra_params.
"""
from unittest.mock import patch, MagicMock

from icpy.agent.helpers import get_model_name_for_agent, get_thinking_extra_params


def test_get_model_name_for_agent_uses_fallback_when_no_config():
    """Test that fallback model is used when no config is available."""
    # Since the import is inside the function, we patch at the source module level
    with patch('icpy.services.agent_config_service.get_agent_config_service') as mock_get_service:
        # Simulate config service not available
        mock_get_service.side_effect = Exception("Service not available")
        
        result = get_model_name_for_agent("TestAgent", "fallback-model")
        assert result == "fallback-model"


def test_get_model_name_for_agent_uses_fallback_when_no_model_name():
    """Test that fallback model is used when modelName is not set in config."""
    with patch('icpy.services.agent_config_service.get_agent_config_service') as mock_get_service:
        mock_service = MagicMock()
        mock_config = MagicMock()
        mock_config.model_name = None  # No modelName in config
        mock_service.get_agent_display_config.return_value = mock_config
        mock_get_service.return_value = mock_service
        
        result = get_model_name_for_agent("TestAgent", "fallback-model")
        assert result == "fallback-model"


def test_get_model_name_for_agent_uses_config_model_name():
    """Test that modelName from config takes precedence over fallback."""
    with patch('icpy.services.agent_config_service.get_agent_config_service') as mock_get_service:
        mock_service = MagicMock()
        mock_config = MagicMock()
        mock_config.model_name = "config-model"  # Model from agents.json
        mock_service.get_agent_display_config.return_value = mock_config
        mock_get_service.return_value = mock_service
        
        result = get_model_name_for_agent("TestAgent", "fallback-model")
        assert result == "config-model"


def test_get_model_name_for_agent_handles_empty_string():
    """Test that empty string modelName falls back to default."""
    with patch('icpy.services.agent_config_service.get_agent_config_service') as mock_get_service:
        mock_service = MagicMock()
        mock_config = MagicMock()
        mock_config.model_name = ""  # Empty string should be falsy
        mock_service.get_agent_display_config.return_value = mock_config
        mock_get_service.return_value = mock_service
        
        result = get_model_name_for_agent("TestAgent", "fallback-model")
        assert result == "fallback-model"


# --- get_thinking_extra_params tests ---

def test_get_thinking_extra_params_disabled():
    """Test that thinkingMode 'disabled' produces correct extra_params."""
    with patch('icpy.services.agent_config_service.get_agent_config_service') as mock_get_service:
        mock_service = MagicMock()
        mock_config = MagicMock()
        mock_config.thinking_mode = "disabled"
        mock_service.get_agent_display_config.return_value = mock_config
        mock_get_service.return_value = mock_service

        result = get_thinking_extra_params("MiniMaxAgent")
        assert result == {"thinking": {"type": "disabled"}}


def test_get_thinking_extra_params_enabled():
    """Test that thinkingMode 'enabled' produces correct extra_params."""
    with patch('icpy.services.agent_config_service.get_agent_config_service') as mock_get_service:
        mock_service = MagicMock()
        mock_config = MagicMock()
        mock_config.thinking_mode = "enabled"
        mock_service.get_agent_display_config.return_value = mock_config
        mock_get_service.return_value = mock_service

        result = get_thinking_extra_params("KimiAgent")
        assert result == {"thinking": {"type": "enabled"}}


def test_get_thinking_extra_params_none_when_not_set():
    """Test that None thinkingMode returns None (use model default)."""
    with patch('icpy.services.agent_config_service.get_agent_config_service') as mock_get_service:
        mock_service = MagicMock()
        mock_config = MagicMock()
        mock_config.thinking_mode = None
        mock_service.get_agent_display_config.return_value = mock_config
        mock_get_service.return_value = mock_service

        result = get_thinking_extra_params("OpenAIAgent")
        assert result is None


def test_get_thinking_extra_params_handles_config_error():
    """Test graceful fallback when config service is unavailable."""
    with patch('icpy.services.agent_config_service.get_agent_config_service') as mock_get_service:
        mock_get_service.side_effect = Exception("Service not available")

        result = get_thinking_extra_params("TestAgent")
        assert result is None
