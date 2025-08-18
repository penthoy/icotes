"""
Environment Manager for Agent Hot Reload System

This module manages environment variable reloading for agents to support
dynamic configuration updates without process restart.
"""

import os
import sys
import logging
from typing import Dict, Set, List, Optional
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

class EnvironmentManager:
    """
    Manages environment variable reloading for agents
    
    Features:
    - Reload .env file and update os.environ
    - Track agent-specific environment variables
    - Notify cached modules of environment changes
    - Support for export command integration
    """
    
    def __init__(self):
        self._tracked_vars: Set[str] = set()
        self._agent_env_prefixes: Set[str] = set()
        
    def track_environment_variable(self, var_name: str):
        """Track a specific environment variable for changes"""
        self._tracked_vars.add(var_name)
        logger.debug(f"Now tracking environment variable: {var_name}")
    
    def track_agent_prefix(self, prefix: str):
        """Track all environment variables with a specific prefix (e.g., 'OPENAI_')"""
        self._agent_env_prefixes.add(prefix.upper())
        logger.debug(f"Now tracking environment prefix: {prefix}")
    
    def reload_environment(self) -> Dict[str, str]:
        """
        Reload .env file and update os.environ
        
        Returns:
            Dict of changed environment variables
        """
        try:
            logger.info("Reloading environment variables from .env file...")
            
            # Store current environment state
            old_env = dict(os.environ)
            
            # Reload .env file with override
            load_dotenv(override=True)
            
            # Find changed variables
            changed_vars = {}
            for key, value in os.environ.items():
                if key not in old_env or old_env[key] != value:
                    changed_vars[key] = value
            
            # Log changes for tracked variables
            for var_name in self._tracked_vars:
                if var_name in changed_vars:
                    logger.info(f"Environment variable {var_name} updated")
            
            # Log changes for tracked prefixes
            for prefix in self._agent_env_prefixes:
                prefix_changes = {k: v for k, v in changed_vars.items() if k.startswith(prefix)}
                if prefix_changes:
                    logger.info(f"Environment variables with prefix {prefix}: {list(prefix_changes.keys())}")
            
            logger.info(f"Environment reload complete. {len(changed_vars)} variables changed.")
            return changed_vars
            
        except Exception as e:
            logger.error(f"Error reloading environment: {e}")
            return {}
    
    def reload_agent_modules_environment(self):
        """Reload environment in all cached agent modules that support it"""
        try:
            reloaded_modules = []
            
            for module_name, module in sys.modules.items():
                # Check if it's an agent module and has reload_env method
                if (module_name.startswith('icpy.agent') or 
                    module_name.endswith('_agent')) and hasattr(module, 'reload_env'):
                    try:
                        module.reload_env()
                        reloaded_modules.append(module_name)
                        logger.debug(f"Reloaded environment for module: {module_name}")
                    except Exception as e:
                        logger.warning(f"Error reloading environment for {module_name}: {e}")
            
            if reloaded_modules:
                logger.info(f"Reloaded environment for {len(reloaded_modules)} modules")
            else:
                logger.debug("No modules with reload_env method found")
                
        except Exception as e:
            logger.error(f"Error reloading agent modules environment: {e}")
    
    def get_agent_env_vars(self, agent_name: str) -> Dict[str, str]:
        """
        Get environment variables specific to an agent
        
        Args:
            agent_name: Name of the agent (e.g., 'OpenAIDemoAgent')
            
        Returns:
            Dict of environment variables with agent-specific prefix
        """
        # Convert agent name to uppercase prefix
        prefix = f"{agent_name.upper()}_"
        
        # Also try common prefixes based on agent name
        common_prefixes = [prefix]
        
        # Add common API prefixes based on agent name
        if 'openai' in agent_name.lower():
            common_prefixes.extend(['OPENAI_', 'OPENAI_API_'])
        elif 'openrouter' in agent_name.lower():
            common_prefixes.extend(['OPENROUTER_', 'OPENROUTER_API_'])
        elif 'anthropic' in agent_name.lower():
            common_prefixes.extend(['ANTHROPIC_', 'ANTHROPIC_API_'])
        
        # Collect all matching environment variables
        agent_vars = {}
        for prefix in common_prefixes:
            for key, value in os.environ.items():
                if key.startswith(prefix):
                    agent_vars[key] = value
        
        return agent_vars
    
    def get_common_env_vars(self) -> Dict[str, str]:
        """Get commonly used environment variables across agents"""
        common_vars = [
            'OPENAI_API_KEY',
            'ANTHROPIC_API_KEY', 
            'OPENROUTER_API_KEY',
            'GROQ_API_KEY',
            'DEEPSEEK_API_KEY',
            'GOOGLE_API_KEY',
            'DASHSCOPE_API_KEY',
            'MAILERSEND_API_KEY',
            'PUSHOVER_TOKEN',
            'PUSHOVER_USER'
        ]
        
        return {var: os.getenv(var, '') for var in common_vars if os.getenv(var)}
    
    def validate_required_env_vars(self, required_vars: List[str]) -> Dict[str, bool]:
        """
        Validate that required environment variables are set
        
        Args:
            required_vars: List of required environment variable names
            
        Returns:
            Dict mapping variable names to whether they are set
        """
        validation_results = {}
        
        for var_name in required_vars:
            value = os.getenv(var_name)
            validation_results[var_name] = bool(value and value.strip())
            
            if not validation_results[var_name]:
                logger.warning(f"Required environment variable {var_name} is not set")
        
        return validation_results

# Global environment manager instance
_global_env_manager: Optional[EnvironmentManager] = None

def get_environment_manager() -> EnvironmentManager:
    """Get the global environment manager instance"""
    global _global_env_manager
    if _global_env_manager is None:
        _global_env_manager = EnvironmentManager()
        
        # Track common API keys
        common_keys = [
            'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'OPENROUTER_API_KEY',
            'GROQ_API_KEY', 'DEEPSEEK_API_KEY', 'GOOGLE_API_KEY'
        ]
        for key in common_keys:
            _global_env_manager.track_environment_variable(key)
            
    return _global_env_manager

# Convenience functions
def reload_environment() -> Dict[str, str]:
    """Reload environment variables"""
    env_manager = get_environment_manager()
    return env_manager.reload_environment()

def get_agent_environment(agent_name: str) -> Dict[str, str]:
    """Get environment variables for a specific agent"""
    env_manager = get_environment_manager()
    return env_manager.get_agent_env_vars(agent_name) 