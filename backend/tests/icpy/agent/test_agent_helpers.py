"""
Tests for agent helper functions including get_model_name_for_agent.
"""
from unittest.mock import patch, MagicMock

from icpy.agent.helpers import get_model_name_for_agent


def test_get_model_name_for_agent_uses_fallback_when_no_config():
    """Test that fallback model is used when no config is available."""
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
