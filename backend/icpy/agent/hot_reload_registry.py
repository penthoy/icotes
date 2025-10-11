"""
Dynamic Agent Registry for Hot Reload System

This module provides dynamic agent discovery, loading, and reloading capabilities
while maintaining backward compatibility with the existing gradio-compatible agent format.
"""

import os
import sys
import json
import asyncio
import logging
import pkgutil
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Callable, Any, Optional
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

class AgentRegistry:
    """
    Dynamic agent registry with hot-reload capabilities
    
    Features:
    - Dynamic discovery of agent modules
    - Hot-reload of agent code and environment variables
    - Workspace plugin support
    - Thread-safe operations
    - Backward compatibility with existing agents
    """
    
    def __init__(self):
        self._registry: Dict[str, Dict[str, Callable]] = {}
        self._lock = asyncio.Lock()
        self._module_cache: Dict[str, Any] = {}
        self._last_reload_time = 0
        
    def get_agent_paths(self) -> List[str]:
        """Get all paths to scan for agents"""
        paths = []
        
        # Built-in agents path
        builtin_path = Path(__file__).parent
        paths.append(str(builtin_path))
        
        # Built-in agents subfolder path (backend/icpy/agent/agents/)
        agents_subfolder = builtin_path / "agents"
        if agents_subfolder.exists():
            paths.append(str(agents_subfolder))
        
        # Workspace plugins path (relative to project root, not backend dir)
        project_root = Path(__file__).parent.parent.parent.parent  # Go up from backend/icpy/agent/
        workspace_plugins = project_root / "workspace" / ".icotes" / "plugins"
        if workspace_plugins.exists():
            paths.append(str(workspace_plugins))
            
        # Custom path from environment
        custom_path = os.getenv("CUSTOM_AGENT_PATH")
        if custom_path and Path(custom_path).exists():
            paths.append(custom_path)
            
        return paths
    
    def validate_agent_module(self, module) -> bool:
        """Validate agent has required chat function with correct signature"""
        if not hasattr(module, 'chat'):
            logger.debug(f"Module {module.__name__} missing 'chat' function")
            return False
        
        # Check if chat function is callable
        chat_func = getattr(module, 'chat')
        if not callable(chat_func):
            logger.debug(f"Module {module.__name__} 'chat' is not callable")
            return False
            
        # Gradio-compatible: chat(message, history) - no strict type checking
        # This preserves existing agent compatibility
        return True
    
    def get_agent_name(self, module) -> str:
        """Get agent name from module, prefer AGENT_NAME constant or derive from filename"""
        # Check for explicit AGENT_NAME constant
        if hasattr(module, 'AGENT_NAME'):
            return getattr(module, 'AGENT_NAME')
        
        # Fallback to module name transformation
        module_name = module.__name__.split('.')[-1]  # Get last part of module path
        
        # Handle existing agents with known names (backward compatibility)
        name_mappings = {
            'personal_agent': 'PersonalAgent',
            'openai_agent': 'OpenAIDemoAgent', 
            'openrouter_agent': 'OpenRouterAgent',
            'qwen3coder_agent': 'Qwen3CoderAgent',
            'mailsent_agent': 'MailsentAgent',
            'test_agent': 'TestAgent',
            'ali_agent': 'AliAgent'
        }
        
        if module_name in name_mappings:
            return name_mappings[module_name]
        
        # Default: convert snake_case to TitleCase
        if module_name.endswith('_agent'):
            module_name = module_name[:-6]  # Remove '_agent' suffix
            
        return ''.join(word.title() for word in module_name.split('_')) + 'Agent'
    
    async def discover_and_load(self) -> List[str]:
        """Discover and load all agents from builtin and workspace locations"""
        async with self._lock:
            self._registry.clear()
            loaded_agents = []
            
            for agent_path in self.get_agent_paths():
                try:
                    agents_in_path = await self._discover_agents_in_path(agent_path)
                    loaded_agents.extend(agents_in_path)
                except Exception as e:
                    logger.error(f"Error discovering agents in {agent_path}: {e}")
            
            logger.info(f"Loaded {len(loaded_agents)} agents: {loaded_agents}")
            return loaded_agents
    
    async def _discover_agents_in_path(self, agent_path: str) -> List[str]:
        """Discover and load agents in a specific path"""
        loaded_agents = []
        agent_path_obj = Path(agent_path)
        
        if not agent_path_obj.exists():
            logger.debug(f"Agent path does not exist: {agent_path}")
            return loaded_agents
        
        # Find all *_agent.py files
        for py_file in agent_path_obj.glob("*_agent.py"):
            if py_file.name.startswith('__'):
                continue  # Skip __init__.py and similar
                
            module_name = py_file.stem
            
            # Skip base/registry modules
            if module_name in ['base_agent', 'custom_agent']:
                continue
                
            try:
                agent_name = await self._load_agent_module(agent_path, module_name)
                if agent_name:
                    loaded_agents.append(agent_name)
            except Exception as e:
                logger.error(f"Error loading agent {module_name}: {e}")
                
        return loaded_agents
    
    async def _load_agent_module(self, agent_path: str, module_name: str) -> Optional[str]:
        """Load a single agent module"""
        try:
            # Build module path using Path for cross-platform compatibility
            agent_path_obj = Path(agent_path).resolve()
            builtin_base = Path(__file__).parent.resolve()
            agents_subfolder = builtin_base / "agents"
            
            # Build module path
            if agent_path_obj == builtin_base:
                # Built-in agents in main folder
                full_module_name = f"icpy.agent.{module_name}"
            elif agent_path_obj == agents_subfolder:
                # Built-in agents in agents subfolder
                full_module_name = f"icpy.agent.agents.{module_name}"
            else:
                # Workspace/custom agents - use spec loading
                module_file = Path(agent_path) / f"{module_name}.py"
                spec = importlib.util.spec_from_file_location(module_name, module_file)
                if not spec or not spec.loader:
                    logger.error(f"Could not load spec for {module_name}")
                    return None
                    
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Cache the module
                self._module_cache[module_name] = module
                
                # Validate and register
                if self.validate_agent_module(module):
                    agent_name = self.get_agent_name(module)
                    self._registry[agent_name] = {"chat": module.chat}
                    logger.info(f"Loaded workspace agent: {agent_name}")
                    return agent_name
                else:
                    logger.warning(f"Agent {module_name} validation failed")
                    return None
            
            # Handle built-in agents
            if full_module_name in sys.modules:
                # Reload existing module
                module = importlib.reload(sys.modules[full_module_name])
            else:
                # Import new module
                module = importlib.import_module(full_module_name)
            
            # Cache the module
            self._module_cache[full_module_name] = module
            
            # Validate and register
            if self.validate_agent_module(module):
                agent_name = self.get_agent_name(module)
                self._registry[agent_name] = {"chat": module.chat}
                logger.info(f"Loaded built-in agent: {agent_name}")
                return agent_name
            else:
                logger.warning(f"Agent {module_name} validation failed")
                return None
                
        except Exception as e:
            logger.error(f"Error loading agent module {module_name}: {e}")
            return None
    
    async def reload_agents(self) -> List[str]:
        """Reload all agent modules and rebuild registry"""
        logger.info("Starting agent reload...")
        
        # Reload environment variables first
        await self.reload_environment()
        
        # Discover and load agents
        loaded_agents = await self.discover_and_load()
        
        self._last_reload_time = asyncio.get_event_loop().time()
        logger.info(f"Agent reload complete. Loaded: {loaded_agents}")
        
        return loaded_agents
    
    async def reload_environment(self) -> bool:
        """Reload environment variables for all agent modules"""
        try:
            logger.info("Reloading environment variables...")
            
            # Reload .env file
            load_dotenv(override=True)
            
            # Reload environment in cached modules that support it
            for module_name, module in self._module_cache.items():
                if hasattr(module, 'reload_env'):
                    try:
                        module.reload_env()
                        logger.debug(f"Reloaded environment for {module_name}")
                    except Exception as e:
                        logger.warning(f"Error reloading environment for {module_name}: {e}")
            
            logger.info("Environment reload complete")
            return True
            
        except Exception as e:
            logger.error(f"Error reloading environment: {e}")
            return False
    
    def get_available_agents(self) -> List[str]:
        """Get list of available agent names"""
        return list(self._registry.keys())
    
    def get_agent_chat_function(self, agent_name: str) -> Optional[Callable]:
        """Get chat function for specified agent name"""
        agent = self._registry.get(agent_name)
        if not agent:
            return None
        return agent.get("chat")
    
    def get_registry(self) -> Dict[str, Dict[str, Callable]]:
        """Get the full registry (for backward compatibility)"""
        return self._registry.copy()

# Global registry instance
_global_registry: Optional[AgentRegistry] = None

def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry instance"""
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry

# Backward compatibility functions
async def initialize_registry():
    """Initialize the global registry"""
    registry = get_agent_registry()
    await registry.discover_and_load()

async def reload_all_agents() -> List[str]:
    """Reload all agents"""
    registry = get_agent_registry()
    return await registry.reload_agents()

def get_available_custom_agents() -> List[str]:
    """Get list of available custom agent names (backward compatibility)"""
    registry = get_agent_registry()
    return registry.get_available_agents()

def build_agent_registry() -> Dict[str, Dict[str, Callable]]:
    """Build agent registry (backward compatibility)"""
    registry = get_agent_registry()
    return registry.get_registry() 