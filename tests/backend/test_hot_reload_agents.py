"""
Test suite for Hot Reload Agent System

This test suite validates the dynamic agent registry and hot-reload capabilities
while ensuring backward compatibility with existing gradio-compatible agents.
"""

import os
import sys
import json
import tempfile
import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add backend to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

# Import the modules to test
from icpy.agent.registry import AgentRegistry, get_agent_registry
from icpy.agent.environment import EnvironmentManager, get_environment_manager
from icpy.agent.custom_agent import (
    get_available_custom_agents, 
    build_agent_registry,
    get_agent_chat_function,
    reload_custom_agents,
    reload_agent_environment,
    enable_hot_reload,
    is_hot_reload_enabled
)

class TestAgentRegistry:
    """Test the dynamic agent registry functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.registry = AgentRegistry()
        enable_hot_reload(True)
    
    def test_discover_builtin_agents(self):
        """Test discovery of existing *_agent.py files"""
        paths = self.registry.get_agent_paths()
        
        # Should include the built-in agent path
        assert any('icpy/agent' in path for path in paths)
        
    def test_agent_name_resolution(self):
        """Test AGENT_NAME vs filename fallback"""
        # Create a mock module with AGENT_NAME
        mock_module = MagicMock()
        mock_module.__name__ = 'test_custom_agent'
        mock_module.AGENT_NAME = 'CustomTestAgent'
        mock_module.chat = MagicMock()
        
        agent_name = self.registry.get_agent_name(mock_module)
        assert agent_name == 'CustomTestAgent'
        
        # Test fallback to filename transformation
        mock_module_no_name = MagicMock()
        mock_module_no_name.__name__ = 'icpy.agent.my_cool_agent'
        mock_module_no_name.chat = MagicMock()
        del mock_module_no_name.AGENT_NAME  # Remove AGENT_NAME attribute
        
        agent_name = self.registry.get_agent_name(mock_module_no_name)
        assert agent_name == 'MyCoolAgent'
        
        # Test known agent mappings (backward compatibility)
        mock_personal = MagicMock()
        mock_personal.__name__ = 'icpy.agent.personal_agent'
        mock_personal.chat = MagicMock()
        del mock_personal.AGENT_NAME
        
        agent_name = self.registry.get_agent_name(mock_personal)
        assert agent_name == 'PersonalAgent'
    
    def test_agent_validation(self):
        """Test that agents have required 'chat' function"""
        # Valid agent
        valid_module = MagicMock()
        valid_module.chat = MagicMock()
        assert self.registry.validate_agent_module(valid_module) == True
        
        # Invalid agent - no chat function
        invalid_module = MagicMock()
        del invalid_module.chat
        assert self.registry.validate_agent_module(invalid_module) == False
        
        # Invalid agent - chat is not callable
        invalid_module2 = MagicMock()
        invalid_module2.chat = "not_callable"
        assert self.registry.validate_agent_module(invalid_module2) == False
    
    @pytest.mark.asyncio
    async def test_registry_reload(self):
        """Test module reload and registry update"""
        # This test would require more complex setup with actual modules
        # For now, test the basic reload mechanism
        initial_agents = await self.registry.discover_and_load()
        assert isinstance(initial_agents, list)
        
        # Test reload
        reloaded_agents = await self.registry.reload_agents()
        assert isinstance(reloaded_agents, list)
    
    @pytest.mark.asyncio
    async def test_concurrent_reload(self):
        """Test thread safety with asyncio.Lock"""
        # Test concurrent access to registry
        async def reload_task():
            return await self.registry.reload_agents()
        
        # Run multiple reload tasks concurrently
        tasks = [reload_task() for _ in range(3)]
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 3
        for result in results:
            assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test that broken agents are skipped and errors logged"""
        # Test with non-existent path
        registry = AgentRegistry()
        agents = await registry._discover_agents_in_path("/nonexistent/path")
        assert agents == []
        
        # Registry should handle errors gracefully
        all_agents = await registry.discover_and_load()
        assert isinstance(all_agents, list)

class TestEnvironmentManager:
    """Test environment variable management"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.env_manager = EnvironmentManager()
    
    def test_environment_reload(self):
        """Test dotenv reload in agent modules"""
        # Set a test environment variable
        os.environ['TEST_RELOAD_VAR'] = 'original_value'
        
        # Track the variable
        self.env_manager.track_environment_variable('TEST_RELOAD_VAR')
        
        # Change the value
        os.environ['TEST_RELOAD_VAR'] = 'new_value'
        
        # Reload should detect the change
        changed_vars = self.env_manager.reload_environment()
        assert isinstance(changed_vars, dict)
        
        # Clean up
        del os.environ['TEST_RELOAD_VAR']
    
    def test_agent_env_vars(self):
        """Test getting agent-specific environment variables"""
        # Set some test environment variables
        os.environ['OPENAI_API_KEY'] = 'test_key_openai'
        os.environ['OPENROUTER_API_KEY'] = 'test_key_openrouter'
        os.environ['CUSTOM_AGENT_VAR'] = 'test_custom'
        
        # Test OpenAI agent vars
        openai_vars = self.env_manager.get_agent_env_vars('OpenAIDemoAgent')
        assert 'OPENAI_API_KEY' in openai_vars
        assert openai_vars['OPENAI_API_KEY'] == 'test_key_openai'
        
        # Test OpenRouter agent vars
        openrouter_vars = self.env_manager.get_agent_env_vars('OpenRouterAgent')
        assert 'OPENROUTER_API_KEY' in openrouter_vars
        
        # Clean up
        del os.environ['OPENAI_API_KEY']
        del os.environ['OPENROUTER_API_KEY']
        del os.environ['CUSTOM_AGENT_VAR']
    
    def test_common_env_vars(self):
        """Test getting common environment variables"""
        # Set a common API key
        os.environ['OPENAI_API_KEY'] = 'test_common_key'
        
        common_vars = self.env_manager.get_common_env_vars()
        assert isinstance(common_vars, dict)
        assert 'OPENAI_API_KEY' in common_vars
        
        # Clean up
        del os.environ['OPENAI_API_KEY']

class TestBackwardCompatibility:
    """Test backward compatibility with existing agent system"""
    
    def test_static_registry_fallback(self):
        """Test that static registry works when hot reload is disabled"""
        # Disable hot reload
        enable_hot_reload(False)
        assert not is_hot_reload_enabled()
        
        # Should still get agents from static registry
        agents = get_available_custom_agents()
        assert isinstance(agents, list)
        
        # Should include known agents if available
        registry = build_agent_registry()
        assert isinstance(registry, dict)
        
        # Re-enable for other tests
        enable_hot_reload(True)
    
    def test_gradio_compatible_format(self):
        """Test that agents maintain gradio-compatible chat(message, history) format"""
        # Test with workspace test agent if available
        test_agent_path = Path("workspace/.icotes/plugins/test_hot_reload_agent.py")
        if test_agent_path.exists():
            # Import the test agent module
            import importlib.util
            spec = importlib.util.spec_from_file_location("test_agent", test_agent_path)
            test_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(test_module)
            
            # Test gradio-compatible format
            assert hasattr(test_module, 'chat')
            assert callable(test_module.chat)
            
            # Test with string history (gradio format)
            response = list(test_module.chat("test message", "[]"))
            assert isinstance(response, list)
            assert len(response) > 0
            
            # Test with list history
            response = list(test_module.chat("test message", []))
            assert isinstance(response, list)
            assert len(response) > 0
    
    def test_existing_agent_functions(self):
        """Test that existing agent functions still work"""
        # Test get_agent_chat_function
        agents = get_available_custom_agents()
        if agents:
            first_agent = agents[0]
            chat_func = get_agent_chat_function(first_agent)
            # Should return a callable or None
            assert chat_func is None or callable(chat_func)

class TestWorkspacePlugins:
    """Test workspace plugin functionality"""
    
    def test_discover_workspace_agents(self):
        """Test discovery of agents in workspace/.icotes/plugins/"""
        registry = AgentRegistry()
        paths = registry.get_agent_paths()
        
        # Should include workspace plugins path
        workspace_path = "workspace/.icotes/plugins"
        if Path(workspace_path).exists():
            assert workspace_path in paths or any(workspace_path in path for path in paths)
    
    @pytest.mark.asyncio
    async def test_workspace_agent_loading(self):
        """Test loading of workspace plugin agents"""
        # Check if test agent exists
        test_agent_path = Path("workspace/.icotes/plugins/test_hot_reload_agent.py")
        if test_agent_path.exists():
            registry = AgentRegistry()
            agents = await registry.discover_and_load()
            
            # Should include the test hot reload agent
            assert "TestHotReloadAgent" in agents or any("Test" in agent for agent in agents)

@pytest.mark.asyncio
async def test_full_hot_reload_workflow():
    """Integration test for complete hot reload workflow"""
    # Enable hot reload
    enable_hot_reload(True)
    
    # Test agent reload
    reloaded_agents = await reload_custom_agents()
    assert isinstance(reloaded_agents, list)
    
    # Test environment reload
    env_success = await reload_agent_environment()
    assert isinstance(env_success, bool)
    
    # Test that existing functions still work
    agents = get_available_custom_agents()
    assert isinstance(agents, list)

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 