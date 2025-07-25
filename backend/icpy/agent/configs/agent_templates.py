"""
Agent Templates for ICPY Agentic Workflows

This module provides pre-built agent configuration templates for rapid
development of common agent types and workflow patterns.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base_agent import AgentConfig
from ..workflows.workflow_engine import WorkflowConfig, WorkflowTask, TaskType


@dataclass
class AgentTemplate:
    """Template for creating agents with pre-configured settings"""
    name: str
    description: str
    category: str = "general"
    framework: str = "openai"
    config: AgentConfig = field(default_factory=lambda: AgentConfig(name="", framework="openai"))
    capabilities: List[str] = field(default_factory=list)
    workflow_tasks: List[Dict[str, Any]] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class AgentTemplateManager:
    """Manager for agent templates and rapid agent creation"""
    
    def __init__(self, templates_path: Optional[str] = None):
        self.templates: Dict[str, AgentTemplate] = {}
        self.templates_path = Path(templates_path) if templates_path else None
        self._load_builtin_templates()
    
    def register_template(self, template: AgentTemplate):
        """Register a new agent template"""
        self.templates[template.name] = template
    
    def get_template(self, name: str) -> Optional[AgentTemplate]:
        """Get a template by name"""
        return self.templates.get(name)
    
    def list_templates(self, category: Optional[str] = None) -> List[AgentTemplate]:
        """List available templates, optionally filtered by category"""
        templates = list(self.templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return templates
    
    def create_agent_from_template(self, template_name: str, name: str, 
                                 custom_config: Optional[Dict[str, Any]] = None) -> Optional[AgentConfig]:
        """Create an agent configuration from a template"""
        template = self.get_template(template_name)
        if not template:
            return None
        
        # Start with template config
        config = AgentConfig(
            name=name,
            framework=template.config.framework,
            role=template.config.role,
            goal=template.config.goal,
            backstory=template.config.backstory,
            capabilities=template.capabilities.copy(),
            memory_enabled=template.config.memory_enabled,
            context_window=template.config.context_window,
            temperature=template.config.temperature,
            model=template.config.model,
            max_tokens=template.config.max_tokens,
            custom_config=template.config.custom_config.copy()
        )
        
        # Apply custom configuration overrides
        if custom_config:
            for key, value in custom_config.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                else:
                    config.custom_config[key] = value
        
        return config
    
    def create_workflow_from_template(self, template_name: str, workflow_name: str) -> Optional[WorkflowConfig]:
        """Create a workflow from an agent template"""
        template = self.get_template(template_name)
        if not template or not template.workflow_tasks:
            return None
        
        tasks = []
        for task_def in template.workflow_tasks:
            task = WorkflowTask(
                name=task_def.get('name', ''),
                task_type=TaskType(task_def.get('task_type', 'sequential')),
                task_content=task_def.get('content', ''),
                agent_config=self.create_agent_from_template(
                    template_name, 
                    task_def.get('agent_name', f"{workflow_name}_agent")
                ),
                dependencies=task_def.get('dependencies', []),
                conditions=task_def.get('conditions', {}),
                timeout=task_def.get('timeout'),
                max_retries=task_def.get('max_retries', 3),
                metadata=task_def.get('metadata', {})
            )
            tasks.append(task)
        
        return WorkflowConfig(
            name=workflow_name,
            description=f"Workflow created from {template_name} template",
            tasks=tasks
        )
    
    def save_templates(self):
        """Save templates to file"""
        if not self.templates_path:
            return
        
        templates_data = {}
        for name, template in self.templates.items():
            templates_data[name] = {
                'name': template.name,
                'description': template.description,
                'category': template.category,
                'framework': template.framework,
                'config': {
                    'role': template.config.role,
                    'goal': template.config.goal,
                    'backstory': template.config.backstory,
                    'memory_enabled': template.config.memory_enabled,
                    'context_window': template.config.context_window,
                    'temperature': template.config.temperature,
                    'model': template.config.model,
                    'max_tokens': template.config.max_tokens,
                    'custom_config': template.config.custom_config
                },
                'capabilities': template.capabilities,
                'workflow_tasks': template.workflow_tasks,
                'examples': template.examples,
                'tags': template.tags
            }
        
        self.templates_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.templates_path, 'w') as f:
            json.dump(templates_data, f, indent=2)
    
    def load_templates(self):
        """Load templates from file"""
        if not self.templates_path or not self.templates_path.exists():
            return
        
        try:
            with open(self.templates_path, 'r') as f:
                templates_data = json.load(f)
            
            for name, data in templates_data.items():
                config = AgentConfig(
                    name="",  # Will be set when creating from template
                    framework=data['framework'],
                    role=data['config']['role'],
                    goal=data['config']['goal'],
                    backstory=data['config']['backstory'],
                    memory_enabled=data['config']['memory_enabled'],
                    context_window=data['config']['context_window'],
                    temperature=data['config']['temperature'],
                    model=data['config']['model'],
                    max_tokens=data['config'].get('max_tokens'),
                    custom_config=data['config']['custom_config']
                )
                
                template = AgentTemplate(
                    name=data['name'],
                    description=data['description'],
                    category=data['category'],
                    framework=data['framework'],
                    config=config,
                    capabilities=data['capabilities'],
                    workflow_tasks=data['workflow_tasks'],
                    examples=data['examples'],
                    tags=data['tags']
                )
                
                self.templates[name] = template
                
        except Exception as e:
            print(f"Failed to load templates: {e}")
    
    def _load_builtin_templates(self):
        """Load built-in agent templates"""
        
        # Code Generation Agent
        code_agent_config = AgentConfig(
            name="code_generator",
            framework="openai",
            role="Senior Software Developer",
            goal="Generate high-quality, well-documented code based on user requirements",
            backstory="I am an experienced software developer with expertise across multiple programming languages and frameworks. I write clean, efficient, and maintainable code with proper documentation and testing.",
            capabilities=["code_generation", "code_review", "debugging", "documentation"],
            memory_enabled=True,
            context_window=6000,
            temperature=0.3,
            model="gpt-4"
        )
        
        code_agent_template = AgentTemplate(
            name="code_generator",
            description="Agent specialized in generating high-quality code",
            category="development",
            framework="openai",
            config=code_agent_config,
            capabilities=["code_generation", "code_review", "debugging", "documentation"],
            workflow_tasks=[
                {
                    "name": "analyze_requirements",
                    "content": "Analyze the user requirements and break them down into implementable components",
                    "task_type": "sequential"
                },
                {
                    "name": "generate_code",
                    "content": "Generate the code implementation based on analyzed requirements",
                    "task_type": "sequential",
                    "dependencies": ["analyze_requirements"]
                },
                {
                    "name": "add_documentation",
                    "content": "Add comprehensive documentation and comments to the generated code",
                    "task_type": "sequential",
                    "dependencies": ["generate_code"]
                },
                {
                    "name": "create_tests",
                    "content": "Create unit tests for the generated code",
                    "task_type": "parallel",
                    "dependencies": ["generate_code"]
                }
            ],
            examples=[
                {
                    "input": "Create a Python function to calculate fibonacci numbers",
                    "output": "# Generates optimized fibonacci function with memoization and tests"
                }
            ],
            tags=["coding", "development", "programming"]
        )
        
        # Documentation Agent
        doc_agent_config = AgentConfig(
            name="documentation_writer",
            framework="openai",
            role="Technical Writer",
            goal="Create comprehensive, clear, and user-friendly documentation",
            backstory="I am a technical writer with extensive experience in creating documentation for software projects. I excel at explaining complex technical concepts in simple, accessible language.",
            capabilities=["documentation", "text_generation", "markdown", "technical_writing"],
            memory_enabled=True,
            context_window=8000,
            temperature=0.4,
            model="gpt-4"
        )
        
        doc_agent_template = AgentTemplate(
            name="documentation_writer",
            description="Agent specialized in creating technical documentation",
            category="documentation",
            framework="openai",
            config=doc_agent_config,
            capabilities=["documentation", "text_generation", "markdown", "technical_writing"],
            workflow_tasks=[
                {
                    "name": "analyze_codebase",
                    "content": "Analyze the codebase to understand its structure and functionality",
                    "task_type": "sequential"
                },
                {
                    "name": "create_api_docs",
                    "content": "Generate API documentation with examples",
                    "task_type": "parallel",
                    "dependencies": ["analyze_codebase"]
                },
                {
                    "name": "write_user_guide",
                    "content": "Write user guide and tutorials",
                    "task_type": "parallel",
                    "dependencies": ["analyze_codebase"]
                },
                {
                    "name": "create_readme",
                    "content": "Create comprehensive README with setup and usage instructions",
                    "task_type": "sequential",
                    "dependencies": ["create_api_docs", "write_user_guide"]
                }
            ],
            examples=[
                {
                    "input": "Document this FastAPI application",
                    "output": "# Creates API docs, user guide, and comprehensive README"
                }
            ],
            tags=["documentation", "writing", "markdown"]
        )
        
        # Testing Agent
        test_agent_config = AgentConfig(
            name="test_engineer",
            framework="openai",
            role="QA Engineer",
            goal="Create comprehensive test suites and ensure code quality",
            backstory="I am a QA engineer with expertise in test automation, unit testing, integration testing, and quality assurance. I ensure code reliability and catch bugs before they reach production.",
            capabilities=["test_generation", "code_analysis", "debugging", "quality_assurance"],
            memory_enabled=True,
            context_window=5000,
            temperature=0.2,
            model="gpt-4"
        )
        
        test_agent_template = AgentTemplate(
            name="test_engineer",
            description="Agent specialized in creating tests and ensuring code quality",
            category="testing",
            framework="openai",
            config=test_agent_config,
            capabilities=["test_generation", "code_analysis", "debugging", "quality_assurance"],
            workflow_tasks=[
                {
                    "name": "analyze_code",
                    "content": "Analyze code to identify testable components and edge cases",
                    "task_type": "sequential"
                },
                {
                    "name": "create_unit_tests",
                    "content": "Generate comprehensive unit tests",
                    "task_type": "parallel",
                    "dependencies": ["analyze_code"]
                },
                {
                    "name": "create_integration_tests",
                    "content": "Generate integration tests",
                    "task_type": "parallel",
                    "dependencies": ["analyze_code"]
                },
                {
                    "name": "setup_test_environment",
                    "content": "Set up test configuration and CI/CD integration",
                    "task_type": "sequential",
                    "dependencies": ["create_unit_tests", "create_integration_tests"]
                }
            ],
            examples=[
                {
                    "input": "Create tests for this user authentication module",
                    "output": "# Generates unit tests, integration tests, and test setup"
                }
            ],
            tags=["testing", "qa", "automation"]
        )
        
        # Multi-Agent Development Team
        team_workflow_template = AgentTemplate(
            name="development_team",
            description="Multi-agent team for full software development lifecycle",
            category="team",
            framework="crewai",
            config=AgentConfig(
                name="dev_team_lead",
                framework="crewai",
                role="Development Team Lead",
                goal="Coordinate a team of agents to deliver complete software solutions",
                backstory="I lead development teams and coordinate between different specialists to deliver high-quality software products."
            ),
            capabilities=["team_coordination", "project_management", "code_generation", "testing", "documentation"],
            workflow_tasks=[
                {
                    "name": "requirements_analysis",
                    "content": "Analyze project requirements and create development plan",
                    "task_type": "sequential",
                    "agent_name": "business_analyst"
                },
                {
                    "name": "architecture_design",
                    "content": "Design system architecture and component structure",
                    "task_type": "sequential",
                    "dependencies": ["requirements_analysis"],
                    "agent_name": "architect"
                },
                {
                    "name": "backend_development",
                    "content": "Implement backend services and APIs",
                    "task_type": "parallel",
                    "dependencies": ["architecture_design"],
                    "agent_name": "backend_developer"
                },
                {
                    "name": "frontend_development",
                    "content": "Implement frontend interface and user experience",
                    "task_type": "parallel",
                    "dependencies": ["architecture_design"],
                    "agent_name": "frontend_developer"
                },
                {
                    "name": "testing",
                    "content": "Create and run comprehensive test suite",
                    "task_type": "sequential",
                    "dependencies": ["backend_development", "frontend_development"],
                    "agent_name": "test_engineer"
                },
                {
                    "name": "documentation",
                    "content": "Create project documentation and user guides",
                    "task_type": "parallel",
                    "dependencies": ["backend_development", "frontend_development"],
                    "agent_name": "technical_writer"
                },
                {
                    "name": "deployment",
                    "content": "Deploy application and set up monitoring",
                    "task_type": "sequential",
                    "dependencies": ["testing", "documentation"],
                    "agent_name": "devops_engineer"
                }
            ],
            examples=[
                {
                    "input": "Build a complete web application for task management",
                    "output": "# Coordinates multiple agents to deliver full application"
                }
            ],
            tags=["team", "collaboration", "full-stack"]
        )
        
        # Research Agent
        research_agent_config = AgentConfig(
            name="researcher",
            framework="langchain",
            role="Research Analyst",
            goal="Conduct thorough research and provide comprehensive analysis",
            backstory="I am a research analyst who excels at gathering information from multiple sources, analyzing data, and presenting findings in a clear, actionable format.",
            capabilities=["research", "analysis", "data_gathering", "report_generation"],
            memory_enabled=True,
            context_window=10000,
            temperature=0.6,
            model="gpt-4"
        )
        
        research_agent_template = AgentTemplate(
            name="researcher",
            description="Agent specialized in research and analysis",
            category="research",
            framework="langchain",
            config=research_agent_config,
            capabilities=["research", "analysis", "data_gathering", "report_generation"],
            workflow_tasks=[
                {
                    "name": "define_research_scope",
                    "content": "Define research questions and scope",
                    "task_type": "sequential"
                },
                {
                    "name": "gather_information",
                    "content": "Collect information from multiple sources",
                    "task_type": "parallel",
                    "dependencies": ["define_research_scope"]
                },
                {
                    "name": "analyze_findings",
                    "content": "Analyze gathered information and identify patterns",
                    "task_type": "sequential",
                    "dependencies": ["gather_information"]
                },
                {
                    "name": "generate_report",
                    "content": "Create comprehensive research report with recommendations",
                    "task_type": "sequential",
                    "dependencies": ["analyze_findings"]
                }
            ],
            examples=[
                {
                    "input": "Research best practices for microservices architecture",
                    "output": "# Comprehensive report on microservices patterns and recommendations"
                }
            ],
            tags=["research", "analysis", "reports"]
        )
        
        # Register all templates
        self.register_template(code_agent_template)
        self.register_template(doc_agent_template)
        self.register_template(test_agent_template)
        self.register_template(team_workflow_template)
        self.register_template(research_agent_template)


# Global template manager instance
template_manager = AgentTemplateManager()


# Utility functions for easy template usage
def create_code_generator(name: str, language: str = "python", 
                         custom_config: Optional[Dict[str, Any]] = None) -> Optional[AgentConfig]:
    """Create a code generation agent"""
    config = custom_config or {}
    config.update({
        'role': f"{language.title()} Developer",
        'goal': f"Generate high-quality {language} code",
        'custom_config': {'preferred_language': language}
    })
    return template_manager.create_agent_from_template("code_generator", name, config)


def create_documentation_writer(name: str, doc_type: str = "api", 
                              custom_config: Optional[Dict[str, Any]] = None) -> Optional[AgentConfig]:
    """Create a documentation writing agent"""
    config = custom_config or {}
    config.update({
        'goal': f"Create comprehensive {doc_type} documentation",
        'custom_config': {'doc_type': doc_type}
    })
    return template_manager.create_agent_from_template("documentation_writer", name, config)


def create_test_engineer(name: str, test_framework: str = "pytest", 
                        custom_config: Optional[Dict[str, Any]] = None) -> Optional[AgentConfig]:
    """Create a testing agent"""
    config = custom_config or {}
    config.update({
        'goal': f"Create comprehensive tests using {test_framework}",
        'custom_config': {'test_framework': test_framework}
    })
    return template_manager.create_agent_from_template("test_engineer", name, config)


def create_development_team_workflow(name: str) -> Optional[WorkflowConfig]:
    """Create a multi-agent development team workflow"""
    return template_manager.create_workflow_from_template("development_team", name)


def create_researcher(name: str, domain: str = "technology", 
                     custom_config: Optional[Dict[str, Any]] = None) -> Optional[AgentConfig]:
    """Create a research agent"""
    config = custom_config or {}
    config.update({
        'role': f"{domain.title()} Research Analyst",
        'goal': f"Conduct thorough research in {domain}",
        'custom_config': {'domain': domain}
    })
    return template_manager.create_agent_from_template("researcher", name, config)
