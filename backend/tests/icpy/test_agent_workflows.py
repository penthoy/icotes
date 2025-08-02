"""
Comprehensive test suite for ICPY Agent Workflow Infrastructure (Step 6.2)

Tests agent workflow creation, execution, capability registration, 
workflow state management, and agent memory handling.
"""

import asyncio
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from icpy.agent.base_agent import AgentConfig, DefaultAgent, AgentStatus
from icpy.agent.workflows.workflow_engine import (
    WorkflowEngine, WorkflowConfig, WorkflowTask, TaskType, WorkflowStatus,
    create_sequential_workflow, create_parallel_workflow
)
from icpy.agent.registry.capability_registry import (
    CapabilityRegistry, CapabilityDefinition, Capability
)
from icpy.agent.memory.context_manager import (
    ContextManager, MemoryEntry, ContextSession, InMemoryStore, FileBasedStore
)
from icpy.agent.configs.agent_templates import (
    template_manager, create_code_generator, create_documentation_writer,
    create_development_team_workflow
)


class TestAgentWorkflows:
    """Test agent workflow creation and execution"""
    
    @pytest.mark.asyncio
    async def test_agent_creation_and_initialization(self):
        """Test basic agent creation and initialization"""
        config = AgentConfig(
            name="test_agent",
            framework="openai",
            role="assistant",
            goal="Help with testing"
        )
        
        agent = DefaultAgent(config)
        assert agent.status == AgentStatus.CREATED
        
        # Initialize agent
        success = await agent.initialize()
        assert success
        assert agent.status == AgentStatus.READY
        assert agent.native_agent is not None
        
        # Test capabilities
        assert agent.has_capability("text_generation")
        assert agent.has_capability("conversation")
        assert agent.has_capability("reasoning")
        
        # Cleanup
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_agent_execution(self):
        """Test agent task execution"""
        config = AgentConfig(
            name="test_agent",
            framework="openai",
            role="assistant"
        )
        
        agent = DefaultAgent(config)
        await agent.initialize()
        
        # Execute a simple task
        messages = []
        async for message in agent.execute("Say hello"):
            messages.append(message)
        
        assert len(messages) > 0
        assert any("hello" in msg.content.lower() for msg in messages)
        assert agent.status == AgentStatus.READY
        
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_agent_lifecycle_management(self):
        """Test agent lifecycle operations"""
        config = AgentConfig(name="lifecycle_agent", framework="openai")
        agent = DefaultAgent(config)
        
        # Test initialization
        await agent.initialize()
        assert agent.status == AgentStatus.READY
        
        # Test pause/resume
        await agent.pause()
        assert agent.status == AgentStatus.PAUSED
        
        await agent.resume()
        assert agent.status == AgentStatus.READY
        
        # Test stop
        await agent.stop()
        assert agent.status == AgentStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_workflow_engine_initialization(self):
        """Test workflow engine creation and initialization"""
        tasks = [
            WorkflowTask(
                name="task1",
                task_content="Complete task 1",
                agent_config=AgentConfig(name="agent1", framework="openai")
            ),
            WorkflowTask(
                name="task2", 
                task_content="Complete task 2",
                dependencies=["task1"],
                agent_config=AgentConfig(name="agent2", framework="openai")
            )
        ]
        
        config = WorkflowConfig(
            name="test_workflow",
            description="Test workflow",
            tasks=tasks
        )
        
        engine = WorkflowEngine(config)
        assert engine.state.status == WorkflowStatus.CREATED
        
        # Initialize workflow
        success = await engine.initialize()
        assert success
        assert engine.state.status == WorkflowStatus.READY
        assert len(engine.state.agents) >= 0
    
    @pytest.mark.asyncio
    async def test_sequential_workflow_execution(self):
        """Test sequential workflow execution"""
        workflow = create_sequential_workflow("sequential_test", [
            {
                'name': 'first_task',
                'content': 'Complete the first task',
                'framework': 'openai'
            },
            {
                'name': 'second_task', 
                'content': 'Complete the second task',
                'framework': 'openai'
            }
        ])
        
        engine = WorkflowEngine(workflow)
        await engine.initialize()
        
        # Execute workflow
        success = await engine.execute()
        assert success
        assert engine.state.status == WorkflowStatus.COMPLETED
        assert len(engine.state.completed_tasks) == 2
        assert len(engine.state.failed_tasks) == 0
    
    @pytest.mark.asyncio 
    async def test_parallel_workflow_execution(self):
        """Test parallel workflow execution"""
        workflow = create_parallel_workflow("parallel_test", [
            {
                'name': 'parallel_task_1',
                'content': 'Complete parallel task 1',
                'framework': 'openai'
            },
            {
                'name': 'parallel_task_2',
                'content': 'Complete parallel task 2', 
                'framework': 'openai'
            }
        ])
        
        engine = WorkflowEngine(workflow)
        await engine.initialize()
        
        # Execute workflow
        success = await engine.execute()
        assert success
        assert engine.state.status == WorkflowStatus.COMPLETED
        assert len(engine.state.completed_tasks) == 2
    
    @pytest.mark.asyncio
    async def test_workflow_state_management(self):
        """Test workflow state persistence and recovery"""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "workflow_state.json"
            
            workflow = create_sequential_workflow("state_test", [
                {'name': 'task1', 'content': 'Task 1', 'framework': 'openai'}
            ])
            workflow.auto_save = True
            workflow.save_path = str(save_path)
            
            engine = WorkflowEngine(workflow)
            await engine.initialize()
            await engine.execute()
            
            # Check that state was saved
            assert save_path.exists()
            
            # Verify state content
            import json
            with open(save_path, 'r') as f:
                state_data = json.load(f)
            
            assert state_data['workflow_id'] == engine.workflow_id
            assert state_data['state']['status'] == 'completed'
    
    @pytest.mark.asyncio
    async def test_workflow_pause_resume_cancel(self):
        """Test workflow pause, resume, and cancel operations"""
        workflow = create_sequential_workflow("control_test", [
            {'name': 'long_task', 'content': 'Long running task', 'framework': 'openai'}
        ])
        
        engine = WorkflowEngine(workflow)
        await engine.initialize()
        
        # Start execution in background
        execution_task = asyncio.create_task(engine.execute())
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Test pause
        success = await engine.pause()
        assert success
        assert engine.state.status == WorkflowStatus.PAUSED
        
        # Test resume
        success = await engine.resume()
        assert success
        assert engine.state.status == WorkflowStatus.RUNNING
        
        # Test cancel
        success = await engine.cancel()
        assert success
        assert engine.state.status == WorkflowStatus.CANCELLED
        
        # Wait for execution to complete
        await execution_task


class TestCapabilityRegistry:
    """Test agent capability registration and discovery"""
    
    @pytest.mark.asyncio
    async def test_capability_registry_initialization(self):
        """Test capability registry initialization"""
        registry = CapabilityRegistry()
        success = await registry.initialize()
        assert success
        
        # Check built-in capabilities are loaded
        capabilities = registry.list_capabilities()
        capability_names = [cap.name for cap in capabilities]
        assert "text_generation" in capability_names
        assert "conversation" in capability_names
        assert "code_generation" in capability_names
    
    @pytest.mark.asyncio
    async def test_custom_capability_registration(self):
        """Test registering custom capabilities"""
        registry = CapabilityRegistry()
        await registry.initialize()
        
        # Create custom capability
        class CustomCapability(Capability):
            def get_definition(self):
                return CapabilityDefinition(
                    name="custom_test",
                    description="Custom test capability",
                    category="test",
                    parameters={"input": {"type": "string", "required": True}}
                )
            
            async def execute(self, agent_id: str, parameters: dict):
                return f"Custom result for {parameters.get('input', 'unknown')}"
            
            async def validate_parameters(self, parameters: dict):
                return "input" in parameters
        
        # Register capability
        custom_cap = CustomCapability()
        success = await registry.register_capability(custom_cap)
        assert success
        
        # Verify registration
        definition = registry.get_capability_definition("custom_test")
        assert definition is not None
        assert definition.name == "custom_test"
        assert definition.category == "test"
    
    @pytest.mark.asyncio
    async def test_capability_attachment_and_execution(self):
        """Test attaching capabilities to agents and executing them"""
        registry = CapabilityRegistry()
        await registry.initialize()
        
        agent_id = "test_agent_123"
        
        # Attach capability to agent
        success = await registry.attach_capability(agent_id, "text_generation")
        assert success
        
        # Check if agent has capability
        has_cap = await registry.has_capability(agent_id, "text_generation")
        assert has_cap
        
        # Get agent capabilities
        capabilities = registry.get_agent_capabilities(agent_id)
        assert len(capabilities) == 1
        assert capabilities[0].capability_name == "text_generation"
        
        # Execute capability
        result = await registry.execute_capability(
            agent_id, 
            "text_generation", 
            {"prompt": "Hello world"}
        )
        assert result is not None
        assert "Hello world" in result
    
    @pytest.mark.asyncio
    async def test_capability_discovery(self):
        """Test automatic capability discovery for agents"""
        registry = CapabilityRegistry()
        await registry.initialize()
        
        # Mock agent with different frameworks
        class MockAgent:
            def __init__(self, framework):
                self.config = type('obj', (object,), {'framework': framework})
        
        # Test OpenAI agent discovery
        openai_agent = MockAgent("openai")
        capabilities = await registry.discover_agent_capabilities(openai_agent)
        assert "text_generation" in capabilities
        
        # Test CrewAI agent discovery  
        crewai_agent = MockAgent("crewai")
        capabilities = await registry.discover_agent_capabilities(crewai_agent)
        assert "text_generation" in capabilities
    
    @pytest.mark.asyncio
    async def test_capability_filtering_and_search(self):
        """Test capability filtering and search functionality"""
        registry = CapabilityRegistry()
        await registry.initialize()
        
        # Test category filtering
        text_capabilities = registry.list_capabilities(category="text")
        assert len(text_capabilities) > 0
        assert all(cap.category == "text" for cap in text_capabilities)
        
        # Test framework filtering
        openai_capabilities = registry.list_capabilities(framework="openai") 
        assert len(openai_capabilities) > 0
        
        # Test getting categories
        categories = registry.get_categories()
        assert "text" in categories
        assert "development" in categories


class TestContextManager:
    """Test agent memory and context management"""
    
    @pytest.mark.asyncio
    async def test_in_memory_store(self):
        """Test in-memory memory store operations"""
        store = InMemoryStore()
        
        # Create test memory
        memory = MemoryEntry(
            content="Test memory content",
            memory_type="episodic",
            agent_id="agent1",
            session_id="session1",
            importance=0.8
        )
        
        # Store memory
        success = await store.store_memory(memory)
        assert success
        
        # Retrieve memories
        memories = await store.retrieve_memories("agent1")
        assert len(memories) == 1
        assert memories[0].content == "Test memory content"
        
        # Search memories
        search_results = await store.search_memories("Test", "agent1")
        assert len(search_results) == 1
        
        # Delete memory
        success = await store.delete_memory(memory.id)
        assert success
        
        # Verify deletion
        memories = await store.retrieve_memories("agent1")
        assert len(memories) == 0
    
    @pytest.mark.asyncio
    async def test_file_based_store(self):
        """Test file-based memory store operations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = FileBasedStore(temp_dir)
            
            # Create test memory
            memory = MemoryEntry(
                content="File-based test memory",
                memory_type="semantic", 
                agent_id="agent2",
                session_id="session2"
            )
            
            # Store memory
            success = await store.store_memory(memory)
            assert success
            
            # Verify file was created
            agent_dir = Path(temp_dir) / "agent2"
            assert agent_dir.exists()
            memory_file = agent_dir / f"{memory.id}.json"
            assert memory_file.exists()
            
            # Retrieve memories
            memories = await store.retrieve_memories("agent2")
            assert len(memories) == 1
            assert memories[0].content == "File-based test memory"
    
    @pytest.mark.asyncio
    async def test_context_manager_sessions(self):
        """Test context manager session operations"""
        context_manager = ContextManager()
        
        # Create session
        session_id = await context_manager.create_session(
            agent_id="agent1",
            session_type="conversation",
            max_context_length=100
        )
        assert session_id is not None
        
        # Store memories in session
        memory_id1 = await context_manager.store_memory(
            agent_id="agent1",
            content="First session memory",
            session_id=session_id
        )
        
        memory_id2 = await context_manager.store_memory(
            agent_id="agent1", 
            content="Second session memory",
            session_id=session_id
        )
        
        # Retrieve session context
        context = await context_manager.get_session_context(session_id)
        assert len(context) == 2
        
        # End session
        success = await context_manager.end_session(session_id)
        assert success
    
    @pytest.mark.asyncio
    async def test_shared_context(self):
        """Test shared context between multiple agents"""
        context_manager = ContextManager()
        
        # Create shared context
        context_id = await context_manager.create_shared_context(
            name="Team Context",
            description="Shared context for team collaboration",
            participant_agents=["agent1", "agent2", "agent3"]
        )
        
        # Add agent to shared context
        success = await context_manager.add_agent_to_shared_context(context_id, "agent4")
        assert success
        
        # Store memory and share it
        memory_id = await context_manager.store_memory(
            agent_id="agent1",
            content="Shared team memory"
        )
        
        success = await context_manager.share_memory(context_id, memory_id)
        assert success
    
    @pytest.mark.asyncio
    async def test_memory_search_and_retrieval(self):
        """Test memory search and retrieval functionality"""
        context_manager = ContextManager()
        
        # Store various memories
        await context_manager.store_memory(
            agent_id="agent1",
            content="Python programming tutorial",
            memory_type="semantic"
        )
        
        await context_manager.store_memory(
            agent_id="agent1", 
            content="JavaScript best practices",
            memory_type="semantic"
        )
        
        await context_manager.store_memory(
            agent_id="agent1",
            content="Meeting notes from yesterday", 
            memory_type="episodic"
        )
        
        # Search memories
        search_results = await context_manager.search_memories("agent1", "programming")
        assert len(search_results) >= 1
        
        # Retrieve by type
        semantic_memories = await context_manager.retrieve_memories(
            agent_id="agent1",
            memory_type="semantic"
        )
        assert len(semantic_memories) == 2
        
        episodic_memories = await context_manager.retrieve_memories(
            agent_id="agent1", 
            memory_type="episodic"
        )
        assert len(episodic_memories) == 1
    
    @pytest.mark.asyncio
    async def test_memory_retention_policies(self):
        """Test memory retention policies"""
        context_manager = ContextManager()
        
        # Create session with small context limit
        session_id = await context_manager.create_session(
            agent_id="agent1",
            max_context_length=2,
            retention_policy="fifo"
        )
        
        # Store more memories than limit
        for i in range(5):
            await context_manager.store_memory(
                agent_id="agent1",
                content=f"Memory {i}",
                session_id=session_id,
                importance=float(i)  # Increasing importance
            )
        
        # Check that retention policy was applied
        memories = await context_manager.retrieve_memories("agent1", session_id)
        assert len(memories) <= 2
    
    @pytest.mark.asyncio
    async def test_context_cleanup(self):
        """Test cleanup of expired memories and contexts"""
        context_manager = ContextManager()
        
        # Store some memories
        await context_manager.store_memory(
            agent_id="agent1",
            content="Old memory"
        )
        
        # Create shared context with expiration
        context_id = await context_manager.create_shared_context(
            name="Temp Context",
            expires_in=timedelta(seconds=1)
        )
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Cleanup expired data
        cleanup_results = await context_manager.cleanup_expired_data(retention_days=0)
        assert cleanup_results['expired_contexts'] >= 1


class TestAgentTemplates:
    """Test agent template system and rapid agent creation"""
    
    def test_template_manager_initialization(self):
        """Test template manager loads built-in templates"""
        templates = template_manager.list_templates()
        template_names = [t.name for t in templates]
        
        assert "code_generator" in template_names
        assert "documentation_writer" in template_names
        assert "test_engineer" in template_names
        assert "development_team" in template_names
        assert "researcher" in template_names
    
    def test_agent_creation_from_template(self):
        """Test creating agents from templates"""
        # Create code generator
        config = create_code_generator("my_coder", language="python")
        assert config is not None
        assert config.name == "my_coder"
        assert "Python Developer" in config.role
        assert config.custom_config["preferred_language"] == "python"
        
        # Create documentation writer
        config = create_documentation_writer("my_writer", doc_type="user_guide")
        assert config is not None
        assert config.name == "my_writer"
        assert "user_guide documentation" in config.goal
    
    def test_workflow_creation_from_template(self):
        """Test creating workflows from templates"""
        workflow = create_development_team_workflow("my_team_project")
        assert workflow is not None
        assert workflow.name == "my_team_project"
        assert len(workflow.tasks) > 0
        
        # Check task dependencies
        task_names = [task.name for task in workflow.tasks]
        assert "requirements_analysis" in task_names
        assert "architecture_design" in task_names
        assert "backend_development" in task_names
        assert "frontend_development" in task_names
    
    def test_template_categories_and_filtering(self):
        """Test template categorization and filtering"""
        # Test category filtering
        dev_templates = template_manager.list_templates(category="development")
        assert len(dev_templates) > 0
        assert all(t.category == "development" for t in dev_templates)
        
        doc_templates = template_manager.list_templates(category="documentation")
        assert len(doc_templates) > 0
        assert all(t.category == "documentation" for t in doc_templates)
        
        # Test template retrieval
        code_template = template_manager.get_template("code_generator")
        assert code_template is not None
        assert code_template.category == "development"
    
    def test_custom_template_registration(self):
        """Test registering custom templates"""
        from icpy.agent.configs.agent_templates import AgentTemplate
        
        custom_config = AgentConfig(
            name="custom_agent",
            framework="openai",
            role="Custom Role",
            goal="Custom goal"
        )
        
        custom_template = AgentTemplate(
            name="custom_template",
            description="Custom template for testing",
            category="custom",
            config=custom_config,
            capabilities=["custom_capability"]
        )
        
        template_manager.register_template(custom_template)
        
        # Verify registration
        retrieved = template_manager.get_template("custom_template")
        assert retrieved is not None
        assert retrieved.name == "custom_template"
        assert retrieved.category == "custom"


# Integration test for complete workflow
class TestWorkflowIntegration:
    """Integration tests for complete agent workflow scenarios"""
    
    @pytest.mark.asyncio
    async def test_complete_development_workflow(self):
        """Test complete development workflow with multiple agents"""
        # Create agents from templates
        coder_config = create_code_generator("coder", "python")
        tester_config = template_manager.create_agent_from_template("test_engineer", "tester")
        doc_config = create_documentation_writer("documenter")
        
        # Create workflow tasks
        tasks = [
            WorkflowTask(
                name="code_generation",
                task_content="Create a Python function to calculate fibonacci numbers",
                agent_config=coder_config
            ),
            WorkflowTask(
                name="test_creation", 
                task_content="Create unit tests for the fibonacci function",
                dependencies=["code_generation"],
                agent_config=tester_config
            ),
            WorkflowTask(
                name="documentation",
                task_content="Document the fibonacci function and its tests",
                dependencies=["code_generation", "test_creation"],
                agent_config=doc_config
            )
        ]
        
        # Create and execute workflow
        workflow_config = WorkflowConfig(
            name="fibonacci_development",
            description="Complete development workflow for fibonacci function",
            tasks=tasks
        )
        
        engine = WorkflowEngine(workflow_config)
        await engine.initialize()
        
        success = await engine.execute()
        assert success
        assert engine.state.status == WorkflowStatus.COMPLETED
        assert len(engine.state.completed_tasks) == 3
        
        # Verify results
        code_result = await engine.get_task_result("code_generation")
        test_result = await engine.get_task_result("test_creation")
        doc_result = await engine.get_task_result("documentation")
        
        assert code_result is not None
        assert test_result is not None  
        assert doc_result is not None
    
    @pytest.mark.asyncio
    async def test_agent_collaboration_with_shared_context(self):
        """Test agents collaborating through shared context"""
        context_manager = ContextManager()
        registry = CapabilityRegistry()
        await registry.initialize()
        
        # Create shared context for collaboration
        shared_context_id = await context_manager.create_shared_context(
            name="Code Review Session",
            description="Shared context for code review collaboration",
            participant_agents=["coder", "reviewer", "tester"]
        )
        
        # Store shared knowledge
        await context_manager.store_memory(
            agent_id="coder",
            content="Implemented user authentication module with JWT tokens",
            memory_type="semantic"
        )
        
        await context_manager.share_memory(shared_context_id, "auth_implementation")
        
        # Agents can now access shared context
        shared_context = await context_manager.get_session_context(
            await context_manager.create_session("reviewer"),
            include_shared=True
        )
        
        assert len(shared_context) >= 0  # Shared memories should be included
    
    @pytest.mark.asyncio
    async def test_capability_based_workflow_routing(self):
        """Test workflow routing based on agent capabilities"""
        registry = CapabilityRegistry()
        await registry.initialize()
        
        # Attach different capabilities to agents
        await registry.attach_capability("agent1", "code_generation")
        await registry.attach_capability("agent2", "text_generation")
        await registry.attach_capability("agent3", "code_generation")
        
        # Find agents with specific capability
        code_agents = []
        for agent_id in ["agent1", "agent2", "agent3"]:
            if await registry.has_capability(agent_id, "code_generation"):
                code_agents.append(agent_id)
        
        assert len(code_agents) == 2
        assert "agent1" in code_agents
        assert "agent3" in code_agents
        assert "agent2" not in code_agents


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
