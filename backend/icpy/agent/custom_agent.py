"""
Custom Agent Registry for ICUI Framework

Enhanced entry point for custom agents with hot-reload capabilities.
Maintains backward compatibility while adding dynamic agent discovery.
This module acts as a bridge between the main.py API and individual agent implementations.
"""

import logging
import asyncio
from typing import List, Dict, Callable, Any, AsyncGenerator

# Configure logging
logger = logging.getLogger(__name__)

# Hot-reload system imports
try:
    from .hot_reload_registry import get_agent_registry, initialize_registry
    from .environment import get_environment_manager
    HOT_RELOAD_AVAILABLE = True
    logger.info("Hot-reload system available")
except ImportError as e:
    logger.warning(f"Hot-reload system not available: {e}")
    HOT_RELOAD_AVAILABLE = False

# Global flag to enable/disable hot reload
_hot_reload_enabled = HOT_RELOAD_AVAILABLE
_registry_initialized = False

def enable_hot_reload(enabled: bool = True):
    """Enable or disable hot reload functionality"""
    global _hot_reload_enabled
    _hot_reload_enabled = enabled and HOT_RELOAD_AVAILABLE
    logger.info(f"Hot reload {'enabled' if _hot_reload_enabled else 'disabled'}")

def is_hot_reload_enabled() -> bool:
    """Check if hot reload is currently enabled"""
    return _hot_reload_enabled

async def _ensure_registry_initialized():
    """Ensure the registry is initialized (lazy initialization)"""
    global _registry_initialized, _hot_reload_enabled
    if not _registry_initialized and _hot_reload_enabled:
        try:
            await initialize_registry()
            _registry_initialized = True
            logger.info("Agent registry initialized")
        except Exception as e:
            logger.error(f"Failed to initialize registry: {e}")
            # Fall back to static registry
            _hot_reload_enabled = False

def build_agent_registry():
    """
    Build the agent registry using the hot-reload system
    
    Returns the dynamic registry or an empty dict if hot-reload is unavailable
    """
    if _hot_reload_enabled:
        # Get from dynamic registry
        try:
            registry = get_agent_registry()
            dynamic_registry = registry.get_registry()
            if dynamic_registry:
                logger.debug("Using dynamic agent registry")
                return dynamic_registry
        except Exception as e:
            logger.warning(f"Dynamic registry failed: {e}")
    
    # Return empty registry if hot-reload is not available
    logger.warning("Hot-reload system not available, returning empty registry")
    return {}

def get_available_custom_agents() -> List[str]:
    """Get list of available custom agent names for frontend dropdown menu"""
    if not _hot_reload_enabled:
        logger.warning("Hot-reload system not available, returning empty agent list")
        return []
    
    # Get from dynamic registry
    try:
        registry = get_agent_registry()
        
        # Check if registry is empty and try to initialize it
        current_agents = registry.get_available_agents()
        if not current_agents:
            # Try to initialize synchronously using asyncio
            import asyncio
            try:
                # Try to use existing event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create a new thread for the async operation
                    import concurrent.futures
                    
                    def init_registry():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(registry.discover_and_load())
                        finally:
                            new_loop.close()
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(init_registry)
                        agents = future.result(timeout=5)  # 5 second timeout
                        if agents:
                            current_agents = agents
                else:
                    # No running loop, safe to use asyncio.run
                    agents = asyncio.run(registry.discover_and_load())
                    if agents:
                        current_agents = agents
            except Exception as init_error:
                logger.warning(f"Failed to initialize registry: {init_error}")
        
        if current_agents:
            logger.debug(f"Dynamic registry returned {len(current_agents)} agents")
            return current_agents
            
    except Exception as e:
        logger.warning(f"Dynamic registry failed: {e}")
    
    # Return empty list if registry failed
    logger.warning("Failed to get agents from registry, returning empty list")
    return []

def get_configured_custom_agents() -> List[Dict[str, Any]]:
    """Get list of custom agents with their display configuration from workspace config"""
    try:
        from icpy.services.agent_config_service import get_agent_config_service
        
        # Get available agents
        available_agents = get_available_custom_agents()
        
        # Get configuration service
        config_service = get_agent_config_service()
        
        # Auto-add any newly discovered agents to config
        for agent_name in available_agents:
            config_service.add_discovered_agent(agent_name, auto_enable=True)
        
        # Get configured agents with display metadata
        configured_agents = config_service.get_configured_agents(available_agents)
        
        logger.info(f"Returning {len(configured_agents)} configured agents")
        return configured_agents
        
    except Exception as e:
        logger.error(f"Failed to get configured agents: {e}")
        # Fallback to simple list
        agents = get_available_custom_agents()
        return [{"name": agent, "displayName": agent, "description": "", "category": "General", "order": 999, "icon": "🤖"} 
                for agent in agents]


def get_agent_chat_function(agent_name: str) -> Callable:
    """Get chat function for specified agent name (all functions support streaming)"""
    if not _hot_reload_enabled:
        logger.error("Hot-reload system not available, cannot get agent chat function")
        return None
    
    # Get from dynamic registry
    try:
        registry = get_agent_registry()
        
        # Check if registry is empty and try to initialize it
        current_agents = registry.get_available_agents()
        if not current_agents:
            # Try to initialize synchronously using asyncio
            import asyncio
            try:
                # Try to use existing event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create a new thread for the async operation
                    import concurrent.futures
                    
                    def init_registry():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(registry.discover_and_load())
                        finally:
                            new_loop.close()
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(init_registry)
                        _ = future.result(timeout=5)  # 5 second timeout
                else:
                    # No running loop, safe to use run_until_complete
                    _ = loop.run_until_complete(registry.discover_and_load())
            except Exception as init_error:
                logger.warning(f"Failed to initialize registry: {init_error}")
        
        chat_function = registry.get_agent_chat_function(agent_name)
        if chat_function:
            logger.debug(f"Got chat function for {agent_name} from dynamic registry")
            return chat_function
    except Exception as e:
        logger.error(f"Dynamic registry failed for {agent_name}: {e}")
    
    # Return None if agent not found
    logger.error(f"Agent {agent_name} not found in registry")
    return None


def call_custom_agent(agent_name: str, message: str, history: List[Dict[str, Any]]) -> str:
    """Call custom agent with message and history, returns response (streaming generator)"""
    chat_function = get_agent_chat_function(agent_name)
    if not chat_function:
        raise ValueError(f"Unknown custom agent: {agent_name}")
    
    return chat_function(message, history)


async def call_custom_agent_stream(agent_name: str, message: str, history: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
    """Call custom agent with streaming support"""
    # Ensure registry is initialized for hot reload
    if _hot_reload_enabled:
        await _ensure_registry_initialized()
    
    chat_function = get_agent_chat_function(agent_name)
    if not chat_function:
        raise ValueError(f"Unknown custom agent: {agent_name}")
    
    # Handle both sync and async generators (gradio-compatible)
    if hasattr(chat_function, '__call__'):
        # Run sync generator in thread pool to avoid blocking event loop
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Create sync generator
        gen = chat_function(message, history)
        
        # Helper function to get next chunk - must be a proper function, not lambda
        def get_next_chunk():
            try:
                return next(gen), False
            except StopIteration:
                return None, True
        
        # Yield chunks from sync generator without blocking
        while True:
            try:
                # Run next() in executor to avoid blocking
                chunk, is_done = await loop.run_in_executor(None, get_next_chunk)
                if is_done:
                    break
                if chunk is not None:
                    yield chunk
            except Exception as e:
                # Log error but let it propagate so chat_service can handle it
                logger.error(f"Error in agent streaming for {agent_name}: {e}")
                raise

# Hot reload specific functions
async def reload_custom_agents() -> List[str]:
    """Reload all custom agents and return list of available agents"""
    if not _hot_reload_enabled:
        logger.warning("Hot reload not enabled, returning static agent list")
        return get_available_custom_agents()
    
    try:
        registry = get_agent_registry()
        reloaded_agents = await registry.reload_agents()
        logger.info(f"Successfully reloaded {len(reloaded_agents)} agents")
        return reloaded_agents
    except Exception as e:
        logger.error(f"Failed to reload agents: {e}")
        # Return current static list as fallback
        return get_available_custom_agents()

async def reload_agent_environment() -> bool:
    """Reload environment variables for all agents"""
    if not _hot_reload_enabled:
        logger.warning("Hot reload not enabled")
        return False
    
    try:
        env_manager = get_environment_manager()
        changed_vars = env_manager.reload_environment()
        
        # Also reload in agent modules
        env_manager.reload_agent_modules_environment()
        
        logger.info(f"Environment reloaded, {len(changed_vars)} variables changed")
        return True
    except Exception as e:
        logger.error(f"Failed to reload environment: {e}")
        return False

def get_agent_info(agent_name: str) -> Dict[str, Any]:
    """Get information about a specific agent"""
    info = {
        "name": agent_name,
        "available": agent_name in get_available_custom_agents(),
        "hot_reload_enabled": _hot_reload_enabled
    }
    
    if _hot_reload_enabled:
        try:
            env_manager = get_environment_manager()
            info["environment_vars"] = env_manager.get_agent_env_vars(agent_name)
        except Exception as e:
            logger.warning(f"Could not get environment info for {agent_name}: {e}")
            info["environment_vars"] = {}
    
    return info