"""
Capability Registry for ICPY Agentic Workflows

This module provides dynamic capability discovery, registration, and composition
for agents in the ICPY system.
"""

import inspect
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Callable, Union
from pathlib import Path


@dataclass
class CapabilityDefinition:
    """Definition of an agent capability"""
    name: str
    description: str
    category: str = "general"
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_frameworks: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class CapabilityInstance:
    """Instance of a capability attached to an agent"""
    capability_name: str
    agent_id: str
    instance_id: str
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    usage_count: int = 0


class Capability(ABC):
    """Base class for agent capabilities"""
    
    @abstractmethod
    def get_definition(self) -> CapabilityDefinition:
        """Return capability definition"""
        pass
    
    @abstractmethod
    async def execute(self, agent_id: str, parameters: Dict[str, Any]) -> Any:
        """Execute the capability"""
        pass
    
    @abstractmethod
    async def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate capability parameters"""
        pass


class CapabilityRegistry:
    """
    Registry for managing agent capabilities
    
    Provides capability discovery, registration, composition, and runtime
    injection for agents across different frameworks.
    """
    
    def __init__(self, registry_path: Optional[str] = None):
        self.capabilities: Dict[str, Capability] = {}
        self.definitions: Dict[str, CapabilityDefinition] = {}
        self.instances: Dict[str, List[CapabilityInstance]] = {}  # agent_id -> capabilities
        self.categories: Dict[str, Set[str]] = {}
        self.registry_path = Path(registry_path) if registry_path else None
        self.auto_discovery_paths: List[Path] = []
        
    async def initialize(self) -> bool:
        """Initialize the capability registry"""
        try:
            # Load built-in capabilities
            await self._load_builtin_capabilities()
            
            # Auto-discover capabilities in specified paths
            for path in self.auto_discovery_paths:
                await self._discover_capabilities(path)
            
            # Load registry from file if specified
            if self.registry_path and self.registry_path.exists():
                await self._load_registry()
            
            return True
            
        except Exception as e:
            print(f"Failed to initialize capability registry: {e}")
            return False
    
    async def register_capability(self, capability: Capability) -> bool:
        """Register a new capability"""
        try:
            definition = capability.get_definition()
            
            # Validate capability
            if not await self._validate_capability(capability, definition):
                return False
            
            # Register capability
            self.capabilities[definition.name] = capability
            self.definitions[definition.name] = definition
            
            # Update category index
            if definition.category not in self.categories:
                self.categories[definition.category] = set()
            self.categories[definition.category].add(definition.name)
            
            # Save registry if path is specified
            if self.registry_path:
                await self._save_registry()
            
            return True
            
        except Exception as e:
            print(f"Failed to register capability {capability.__class__.__name__}: {e}")
            return False
    
    async def unregister_capability(self, capability_name: str) -> bool:
        """Unregister a capability"""
        if capability_name not in self.capabilities:
            return False
        
        # Remove from all indexes
        definition = self.definitions[capability_name]
        self.categories[definition.category].discard(capability_name)
        
        del self.capabilities[capability_name]
        del self.definitions[capability_name]
        
        # Remove from agent instances
        for agent_id in self.instances:
            self.instances[agent_id] = [
                inst for inst in self.instances[agent_id] 
                if inst.capability_name != capability_name
            ]
        
        return True
    
    async def attach_capability(self, agent_id: str, capability_name: str, 
                              config: Optional[Dict[str, Any]] = None) -> bool:
        """Attach a capability to an agent"""
        if capability_name not in self.capabilities:
            return False
        
        # Check if agent already has this capability
        if agent_id in self.instances:
            for instance in self.instances[agent_id]:
                if instance.capability_name == capability_name:
                    return False  # Already attached
        
        # Create capability instance
        instance = CapabilityInstance(
            capability_name=capability_name,
            agent_id=agent_id,
            instance_id=f"{agent_id}_{capability_name}_{datetime.utcnow().timestamp()}",
            config=config or {}
        )
        
        # Add to agent instances
        if agent_id not in self.instances:
            self.instances[agent_id] = []
        self.instances[agent_id].append(instance)
        
        return True
    
    async def detach_capability(self, agent_id: str, capability_name: str) -> bool:
        """Detach a capability from an agent"""
        if agent_id not in self.instances:
            return False
        
        initial_count = len(self.instances[agent_id])
        self.instances[agent_id] = [
            inst for inst in self.instances[agent_id]
            if inst.capability_name != capability_name
        ]
        
        return len(self.instances[agent_id]) < initial_count
    
    async def execute_capability(self, agent_id: str, capability_name: str, 
                               parameters: Dict[str, Any]) -> Any:
        """Execute a capability for an agent"""
        # Check if agent has capability
        if not await self.has_capability(agent_id, capability_name):
            raise ValueError(f"Agent {agent_id} does not have capability {capability_name}")
        
        # Get capability instance
        instance = None
        for inst in self.instances.get(agent_id, []):
            if inst.capability_name == capability_name and inst.enabled:
                instance = inst
                break
        
        if not instance:
            raise ValueError(f"Capability {capability_name} not enabled for agent {agent_id}")
        
        # Get capability implementation
        capability = self.capabilities[capability_name]
        
        # Validate parameters
        if not await capability.validate_parameters(parameters):
            raise ValueError(f"Invalid parameters for capability {capability_name}")
        
        # Execute capability
        result = await capability.execute(agent_id, parameters)
        
        # Update usage statistics
        instance.last_used = datetime.utcnow()
        instance.usage_count += 1
        
        return result
    
    async def has_capability(self, agent_id: str, capability_name: str) -> bool:
        """Check if an agent has a specific capability"""
        if agent_id not in self.instances:
            return False
        
        return any(
            inst.capability_name == capability_name and inst.enabled
            for inst in self.instances[agent_id]
        )
    
    def get_agent_capabilities(self, agent_id: str) -> List[CapabilityInstance]:
        """Get all capabilities for an agent"""
        return self.instances.get(agent_id, [])
    
    def get_capability_definition(self, capability_name: str) -> Optional[CapabilityDefinition]:
        """Get definition for a capability"""
        return self.definitions.get(capability_name)
    
    def list_capabilities(self, category: Optional[str] = None, 
                         framework: Optional[str] = None) -> List[CapabilityDefinition]:
        """List available capabilities with optional filtering"""
        results = []
        
        for definition in self.definitions.values():
            # Filter by category
            if category and definition.category != category:
                continue
            
            # Filter by framework
            if framework and framework not in definition.required_frameworks:
                continue
            
            results.append(definition)
        
        return results
    
    def get_categories(self) -> List[str]:
        """Get all capability categories"""
        return list(self.categories.keys())
    
    async def discover_agent_capabilities(self, agent) -> List[str]:
        """Auto-discover capabilities for an agent based on its framework and configuration"""
        discovered = []
        
        # Framework-specific capabilities
        framework_capabilities = {
            'openai': ['text_generation', 'function_calling', 'code_generation'],
            'crewai': ['team_collaboration', 'role_playing', 'task_delegation'],
            'langchain': ['chain_composition', 'tool_usage', 'memory_management'],
            'langgraph': ['graph_workflows', 'state_management', 'conditional_routing']
        }
        
        if hasattr(agent, 'config') and hasattr(agent.config, 'framework'):
            framework_caps = framework_capabilities.get(agent.config.framework, [])
            for cap in framework_caps:
                if cap in self.capabilities:
                    discovered.append(cap)
        
        # Auto-attach basic capabilities
        basic_capabilities = ['text_generation', 'conversation', 'reasoning']
        for cap in basic_capabilities:
            if cap in self.capabilities and cap not in discovered:
                discovered.append(cap)
        
        return discovered
    
    async def compose_capabilities(self, capability_names: List[str]) -> Optional[Capability]:
        """Compose multiple capabilities into a single composite capability"""
        # This is a placeholder for capability composition
        # In a full implementation, this would create a composite capability
        # that can execute multiple capabilities in sequence or based on logic
        pass
    
    async def shutdown(self):
        """Shutdown the capability registry"""
        try:
            # Save current state if registry path is specified
            if self.registry_path:
                await self._save_registry()
            
            # Clear all data
            self.capabilities.clear()
            self.definitions.clear()
            self.instances.clear()
            self.categories.clear()
            
        except Exception as e:
            print(f"Error during capability registry shutdown: {e}")
    
    def add_discovery_path(self, path: Union[str, Path]):
        """Add a path for auto-discovery of capabilities"""
        self.auto_discovery_paths.append(Path(path))
    
    # Private methods
    async def _load_builtin_capabilities(self):
        """Load built-in capabilities"""
        # Text Generation Capability
        class TextGenerationCapability(Capability):
            def get_definition(self) -> CapabilityDefinition:
                return CapabilityDefinition(
                    name="text_generation",
                    description="Generate text based on prompts",
                    category="text",
                    parameters={
                        "prompt": {"type": "string", "required": True},
                        "max_tokens": {"type": "integer", "default": 1000},
                        "temperature": {"type": "float", "default": 0.7}
                    },
                    required_frameworks=["openai", "crewai", "langchain", "langgraph"],
                    tags=["text", "generation", "llm"]
                )
            
            async def execute(self, agent_id: str, parameters: Dict[str, Any]) -> Any:
                # This would integrate with the agent's framework
                return f"Generated text for: {parameters.get('prompt', '')}"
            
            async def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
                return "prompt" in parameters and isinstance(parameters["prompt"], str)
        
        # Conversation Capability
        class ConversationCapability(Capability):
            def get_definition(self) -> CapabilityDefinition:
                return CapabilityDefinition(
                    name="conversation",
                    description="Engage in conversational interactions",
                    category="interaction",
                    parameters={
                        "message": {"type": "string", "required": True},
                        "context": {"type": "array", "default": []}
                    },
                    required_frameworks=["openai", "crewai", "langchain", "langgraph"],
                    tags=["conversation", "chat", "interaction"]
                )
            
            async def execute(self, agent_id: str, parameters: Dict[str, Any]) -> Any:
                return f"Conversation response to: {parameters.get('message', '')}"
            
            async def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
                return "message" in parameters and isinstance(parameters["message"], str)
        
        # Code Generation Capability
        class CodeGenerationCapability(Capability):
            def get_definition(self) -> CapabilityDefinition:
                return CapabilityDefinition(
                    name="code_generation",
                    description="Generate code in various programming languages",
                    category="development",
                    parameters={
                        "language": {"type": "string", "required": True},
                        "description": {"type": "string", "required": True},
                        "style": {"type": "string", "default": "clean"}
                    },
                    required_frameworks=["openai", "langchain"],
                    tags=["code", "programming", "development"]
                )
            
            async def execute(self, agent_id: str, parameters: Dict[str, Any]) -> Any:
                lang = parameters.get("language", "python")
                desc = parameters.get("description", "")
                return f"# Generated {lang} code for: {desc}\n# TODO: Implementation"
            
            async def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
                return ("language" in parameters and "description" in parameters and
                        isinstance(parameters["language"], str) and 
                        isinstance(parameters["description"], str))
        
        # Register built-in capabilities
        await self.register_capability(TextGenerationCapability())
        await self.register_capability(ConversationCapability())
        await self.register_capability(CodeGenerationCapability())
    
    async def _discover_capabilities(self, path: Path):
        """Auto-discover capabilities in a directory"""
        if not path.exists() or not path.is_dir():
            return
        
        # Look for Python files that might contain capabilities
        for py_file in path.rglob("*.py"):
            try:
                # This is a simplified discovery - in a full implementation,
                # we would dynamically import and inspect modules
                pass
            except Exception as e:
                print(f"Failed to discover capabilities in {py_file}: {e}")
    
    async def _validate_capability(self, capability: Capability, definition: CapabilityDefinition) -> bool:
        """Validate a capability before registration"""
        # Check required methods
        required_methods = ['get_definition', 'execute', 'validate_parameters']
        for method in required_methods:
            if not hasattr(capability, method):
                return False
        
        # Validate definition
        if not definition.name or not definition.description:
            return False
        
        return True
    
    async def _save_registry(self):
        """Save registry to file"""
        if not self.registry_path:
            return
        
        registry_data = {
            'definitions': {
                name: {
                    'name': defn.name,
                    'description': defn.description,
                    'category': defn.category,
                    'parameters': defn.parameters,
                    'required_frameworks': defn.required_frameworks,
                    'dependencies': defn.dependencies,
                    'version': defn.version,
                    'author': defn.author,
                    'tags': defn.tags,
                    'metadata': defn.metadata
                }
                for name, defn in self.definitions.items()
            },
            'instances': {
                agent_id: [
                    {
                        'capability_name': inst.capability_name,
                        'instance_id': inst.instance_id,
                        'config': inst.config,
                        'enabled': inst.enabled,
                        'created_at': inst.created_at.isoformat(),
                        'usage_count': inst.usage_count
                    }
                    for inst in instances
                ]
                for agent_id, instances in self.instances.items()
            }
        }
        
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, 'w') as f:
            json.dump(registry_data, f, indent=2)
    
    async def _load_registry(self):
        """Load registry from file"""
        try:
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
            
            # Load instances
            for agent_id, instance_data in data.get('instances', {}).items():
                self.instances[agent_id] = []
                for inst_data in instance_data:
                    instance = CapabilityInstance(
                        capability_name=inst_data['capability_name'],
                        agent_id=agent_id,
                        instance_id=inst_data['instance_id'],
                        config=inst_data.get('config', {}),
                        enabled=inst_data.get('enabled', True),
                        usage_count=inst_data.get('usage_count', 0)
                    )
                    if 'created_at' in inst_data:
                        instance.created_at = datetime.fromisoformat(inst_data['created_at'])
                    self.instances[agent_id].append(instance)
        
        except Exception as e:
            print(f"Failed to load registry from {self.registry_path}: {e}")


# Global capability registry instance
_capability_registry: Optional[CapabilityRegistry] = None


async def get_capability_registry() -> CapabilityRegistry:
    """Get the global capability registry instance"""
    global _capability_registry
    if _capability_registry is None:
        _capability_registry = CapabilityRegistry()
        await _capability_registry.initialize()
    return _capability_registry


async def shutdown_capability_registry():
    """Shutdown the global capability registry"""
    global _capability_registry
    if _capability_registry:
        await _capability_registry.shutdown()
        _capability_registry = None
