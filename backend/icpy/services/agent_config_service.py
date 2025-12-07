"""
Agent Configuration Service

Manages agent display configuration from workspace/.icotes/agents.json
Provides industry-standard configuration management for hot reload system.
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

@dataclass
class AgentDisplayConfig:
    """Configuration for how an agent appears in the UI"""
    enabled: bool = True
    display_name: str = ""
    description: str = ""
    category: str = "General"
    order: int = 999
    icon: str = "🤖"
    model_name: Optional[str] = None  # Override model name from agents.json

@dataclass
class CategoryConfig:
    """Configuration for agent categories"""
    icon: str = "📁"
    order: int = 999

@dataclass
class AgentMenuSettings:
    """Global settings for the agent menu"""
    show_categories: bool = True
    show_descriptions: bool = True
    default_agent: str = ""
    auto_reload_on_change: bool = True

class AgentConfigService:
    """
    Service for managing agent configuration from workspace
    
    Features:
    - Load configuration from .icotes/agents.json
    - Auto-reload on file changes
    - Merge with discovered agents
    - Provide display metadata for frontend
    """
    
    def __init__(self, workspace_root: str = None):
        self.workspace_root = workspace_root or os.getcwd()
        self.config_file = Path(self.workspace_root) / ".icotes" / "agents.json"
        self.config_dir = self.config_file.parent
        
        self._config_cache: Optional[Dict[str, Any]] = None
        self._observer: Optional[Observer] = None
        self._file_handler: Optional[FileSystemEventHandler] = None
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize with default config if file doesn't exist
        if not self.config_file.exists():
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default agent configuration file"""
        default_config = {
            "$schema": "https://icotes.dev/schemas/agents.json",
            "version": "1.0",
            "agents": {},
            "categories": {
                "General": {"icon": "💬", "order": 1},
                "Development": {"icon": "🛠️", "order": 2},
                "AI Models": {"icon": "🧠", "order": 3}
            },
            "settings": {
                "showCategories": True,
                "showDescriptions": True,
                "defaultAgent": "",
                "autoReloadOnChange": True
            }
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"Created default agent config at {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to create default config: {e}")
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self._config_cache = config
                    logger.debug(f"Loaded agent config from {self.config_file}")
                    return config
            else:
                logger.warning(f"Config file not found: {self.config_file}")
                return self._get_fallback_config()
        except Exception as e:
            logger.error(f"Error loading agent config: {e}")
            return self._get_fallback_config()
    
    def _get_fallback_config(self) -> Dict[str, Any]:
        """Fallback configuration when file loading fails"""
        return {
            "version": "1.0",
            "agents": {},
            "categories": {"General": {"icon": "💬", "order": 1}},
            "settings": {
                "showCategories": False,
                "showDescriptions": True,
                "defaultAgent": "",
                "autoReloadOnChange": False
            }
        }
    
    def get_agent_display_config(self, agent_name: str) -> AgentDisplayConfig:
        """Get display configuration for a specific agent"""
        config = self._config_cache or self.load_config()
        agent_config = config.get("agents", {}).get(agent_name, {})
        
        return AgentDisplayConfig(
            enabled=agent_config.get("enabled", True),
            display_name=agent_config.get("displayName", agent_name),
            description=agent_config.get("description", ""),
            category=agent_config.get("category", "General"),
            order=agent_config.get("order", 999),
            icon=agent_config.get("icon", "🤖"),
            model_name=agent_config.get("modelName", None)  # Optional model override
        )
    
    def get_category_config(self, category_name: str) -> CategoryConfig:
        """Get configuration for a category"""
        config = self._config_cache or self.load_config()
        category_config = config.get("categories", {}).get(category_name, {})
        
        return CategoryConfig(
            icon=category_config.get("icon", "📁"),
            order=category_config.get("order", 999)
        )
    
    def get_menu_settings(self) -> AgentMenuSettings:
        """Get global menu settings"""
        config = self._config_cache or self.load_config()
        settings = config.get("settings", {})
        
        return AgentMenuSettings(
            show_categories=settings.get("showCategories", True),
            show_descriptions=settings.get("showDescriptions", True),
            default_agent=settings.get("defaultAgent", ""),
            auto_reload_on_change=settings.get("autoReloadOnChange", True)
        )
    
    def get_configured_agents(self, available_agents: List[str]) -> List[Dict[str, Any]]:
        """
        Get list of agents with their display configuration
        Merges available agents with configuration, filters enabled ones
        """
        configured_agents = []
        
        for agent_name in available_agents:
            display_config = self.get_agent_display_config(agent_name)
            
            if display_config.enabled:
                configured_agents.append({
                    "name": agent_name,
                    "displayName": display_config.display_name,
                    "description": display_config.description,
                    "category": display_config.category,
                    "order": display_config.order,
                    "icon": display_config.icon
                })
        
        # Sort by order, then by display name
        configured_agents.sort(key=lambda x: (x["order"], x["displayName"]))
        
        return configured_agents
    
    def update_agent_config(self, agent_name: str, config_update: Dict[str, Any]) -> bool:
        """Update configuration for a specific agent"""
        try:
            config = self.load_config()
            
            if "agents" not in config:
                config["agents"] = {}
            
            if agent_name not in config["agents"]:
                config["agents"][agent_name] = {}
            
            # Update the agent configuration
            config["agents"][agent_name].update(config_update)
            
            # Save back to file
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Update cache
            self._config_cache = config
            
            logger.info(f"Updated config for agent {agent_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update agent config: {e}")
            return False
    
    def add_discovered_agent(self, agent_name: str, auto_enable: bool = True) -> bool:
        """Add a newly discovered agent to the configuration"""
        config = self.load_config()
        
        # Check if agent is already configured
        if agent_name in config.get("agents", {}):
            return True
        
        # Add with default configuration
        agent_config = {
            "enabled": auto_enable,
            "displayName": agent_name,
            "description": f"Auto-discovered agent: {agent_name}",
            "category": "General",
            "order": 999
        }
        
        return self.update_agent_config(agent_name, agent_config)
    
    def start_file_watcher(self):
        """Start watching the config file for changes"""
        if self._observer is not None:
            return  # Already watching
        
        class ConfigFileHandler(FileSystemEventHandler):
            def __init__(self, service):
                self.service = service
            
            def on_modified(self, event):
                if not event.is_directory and event.src_path == str(self.service.config_file):
                    logger.info("Agent config file changed, reloading...")
                    self.service._config_cache = None  # Clear cache
                    self.service.load_config()
        
        self._file_handler = ConfigFileHandler(self)
        self._observer = Observer()
        self._observer.schedule(self._file_handler, str(self.config_dir), recursive=False)
        self._observer.start()
        
        logger.info(f"Started watching agent config file: {self.config_file}")
    
    def stop_file_watcher(self):
        """Stop watching the config file"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            self._file_handler = None
            logger.info("Stopped watching agent config file")

# Global instance
_agent_config_service: Optional[AgentConfigService] = None

def get_agent_config_service() -> AgentConfigService:
    """Get the global agent config service instance"""
    global _agent_config_service
    if _agent_config_service is None:
        workspace_root = os.getenv('WORKSPACE_ROOT', os.getcwd())
        _agent_config_service = AgentConfigService(workspace_root)
        
        # Start file watcher if auto-reload is enabled
        settings = _agent_config_service.get_menu_settings()
        if settings.auto_reload_on_change:
            _agent_config_service.start_file_watcher()
    
    return _agent_config_service 