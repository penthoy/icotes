#!/usr/bin/env python3
"""
Validation script for ICPY Step 6.2: Agentic Workflow Infrastructure

This script validates the implementation of:
- Agent directory structure and base interfaces
- Workflow execution engine with async task management  
- Agent capability registry for skill discovery
- Memory and context management infrastructure
- Workflow templating and chaining systems
"""

import asyncio
import sys
import tempfile
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def print_header(title: str):
    """Print formatted section header"""
    print(f"\n{'='*60}")
    print(f"🚀 {title}")
    print(f"{'='*60}")

def print_success(message: str):
    """Print success message"""
    print(f"✅ {message}")

def print_error(message: str):
    """Print error message"""
    print(f"❌ {message}")

def print_info(message: str):
    """Print info message"""
    print(f"📋 {message}")

async def validate_agent_infrastructure():
    """Validate agent directory structure and base interfaces"""
    print_header("Step 6.2.1: Agent Infrastructure Validation")
    
    try:
        # Test imports
        from icpy.agent.base_agent import BaseAgent, AgentConfig, DefaultAgent, AgentStatus
        from icpy.agent import BaseAgent as ImportedBaseAgent
        print_success("Agent base interfaces imported successfully")
        
        # Test agent creation
        config = AgentConfig(
            name="validation_agent",
            framework="openai",
            role="validation assistant", 
            goal="Validate agent infrastructure"
        )
        
        agent = DefaultAgent(config)
        print_success(f"Agent created: {agent.agent_id}")
        
        # Test agent lifecycle
        success = await agent.initialize()
        if success:
            print_success("Agent initialization successful")
            print_info(f"   Status: {agent.status.value}")
            print_info(f"   Framework: {agent.config.framework}")
            print_info(f"   Capabilities: {list(agent.capabilities)}")
        else:
            print_error("Agent initialization failed")
            return False
        
        # Test agent execution
        messages = []
        async for message in agent.execute("Validate agent execution"):
            messages.append(message)
            if len(messages) >= 3:  # Limit for validation
                break
        
        if messages:
            print_success(f"Agent execution successful - received {len(messages)} messages")
            print_info(f"   Sample response: {messages[0].content[:100]}...")
        else:
            print_error("Agent execution failed - no messages received")
            return False
        
        # Test agent lifecycle operations
        await agent.pause()
        print_success(f"Agent paused - status: {agent.status.value}")
        
        await agent.resume()  
        print_success(f"Agent resumed - status: {agent.status.value}")
        
        await agent.stop()
        print_success(f"Agent stopped - status: {agent.status.value}")
        
        return True
        
    except Exception as e:
        print_error(f"Agent infrastructure validation failed: {e}")
        return False

async def validate_workflow_engine():
    """Validate workflow execution engine"""
    print_header("Step 6.2.2: Workflow Engine Validation")
    
    try:
        from icpy.agent.workflows.workflow_engine import (
            WorkflowEngine, WorkflowConfig, WorkflowTask, TaskType, WorkflowStatus,
            create_sequential_workflow, create_parallel_workflow
        )
        
        print_success("Workflow engine imports successful")
        
        # Test sequential workflow
        sequential_workflow = create_sequential_workflow("validation_sequential", [
            {
                'name': 'task1',
                'content': 'Complete validation task 1',
                'framework': 'openai'
            },
            {
                'name': 'task2', 
                'content': 'Complete validation task 2',
                'framework': 'openai'
            }
        ])
        
        engine = WorkflowEngine(sequential_workflow)
        print_success("Sequential workflow created")
        print_info(f"   Workflow ID: {engine.workflow_id}")
        print_info(f"   Tasks: {len(engine.config.tasks)}")
        
        # Initialize workflow
        success = await engine.initialize()
        if success:
            print_success("Workflow initialization successful")
            print_info(f"   Status: {engine.state.status.value}")
        else:
            print_error("Workflow initialization failed")
            return False
        
        # Execute workflow
        success = await engine.execute()
        if success:
            print_success("Sequential workflow execution completed")
            print_info(f"   Final status: {engine.state.status.value}")
            print_info(f"   Completed tasks: {len(engine.state.completed_tasks)}")
            print_info(f"   Failed tasks: {len(engine.state.failed_tasks)}")
            print_info(f"   Active agents: {len(engine.state.agents)}")
        else:
            print_error("Sequential workflow execution failed")
            return False
        
        # Test parallel workflow
        parallel_workflow = create_parallel_workflow("validation_parallel", [
            {
                'name': 'parallel_task1',
                'content': 'Parallel validation task 1',
                'framework': 'openai'
            },
            {
                'name': 'parallel_task2',
                'content': 'Parallel validation task 2', 
                'framework': 'openai'
            }
        ])
        
        parallel_engine = WorkflowEngine(parallel_workflow)
        await parallel_engine.initialize()
        
        success = await parallel_engine.execute()
        if success:
            print_success("Parallel workflow execution completed")
            print_info(f"   Completed tasks: {len(parallel_engine.state.completed_tasks)}")
        else:
            print_error("Parallel workflow execution failed")
            return False
        
        # Test workflow control operations
        control_workflow = create_sequential_workflow("validation_control", [
            {'name': 'control_task', 'content': 'Control test task', 'framework': 'openai'}
        ])
        
        control_engine = WorkflowEngine(control_workflow)
        await control_engine.initialize()
        
        # Test pause/resume/cancel
        execution_task = asyncio.create_task(control_engine.execute())
        await asyncio.sleep(0.1)  # Let it start
        
        await control_engine.pause()
        print_success(f"Workflow paused - status: {control_engine.state.status.value}")
        
        await control_engine.resume()
        print_success(f"Workflow resumed - status: {control_engine.state.status.value}")
        
        await control_engine.cancel()
        print_success(f"Workflow cancelled - status: {control_engine.state.status.value}")
        
        await execution_task  # Wait for completion
        
        return True
        
    except Exception as e:
        print_error(f"Workflow engine validation failed: {e}")
        return False

async def validate_capability_registry():
    """Validate agent capability registry"""
    print_header("Step 6.2.3: Capability Registry Validation")
    
    try:
        from icpy.agent.registry.capability_registry import (
            CapabilityRegistry, CapabilityDefinition, Capability
        )
        
        print_success("Capability registry imports successful")
        
        # Initialize registry
        registry = CapabilityRegistry()
        success = await registry.initialize()
        
        if success:
            print_success("Capability registry initialized")
        else:
            print_error("Capability registry initialization failed")
            return False
        
        # Test built-in capabilities
        capabilities = registry.list_capabilities()
        print_success(f"Built-in capabilities loaded: {len(capabilities)}")
        
        capability_names = [cap.name for cap in capabilities]
        expected_capabilities = ["text_generation", "conversation", "code_generation"]
        
        for cap_name in expected_capabilities:
            if cap_name in capability_names:
                print_info(f"   ✓ {cap_name}")
            else:
                print_error(f"   ✗ Missing capability: {cap_name}")
                return False
        
        # Test capability attachment
        agent_id = "test_agent_123"
        success = await registry.attach_capability(agent_id, "text_generation")
        
        if success:
            print_success("Capability attachment successful")
        else:
            print_error("Capability attachment failed")
            return False
        
        # Test capability checking
        has_cap = await registry.has_capability(agent_id, "text_generation")
        if has_cap:
            print_success("Capability checking working")
        else:
            print_error("Capability checking failed")
            return False
        
        # Test capability execution
        result = await registry.execute_capability(
            agent_id,
            "text_generation",
            {"prompt": "Hello, capability test!"}
        )
        
        if result:
            print_success("Capability execution successful")
            print_info(f"   Result: {result[:100]}...")
        else:
            print_error("Capability execution failed")
            return False
        
        # Test custom capability registration
        class ValidationCapability(Capability):
            def get_definition(self):
                return CapabilityDefinition(
                    name="validation_test",
                    description="Test capability for validation",
                    category="testing",
                    parameters={"test_input": {"type": "string", "required": True}}
                )
            
            async def execute(self, agent_id: str, parameters: dict):
                return f"Validation result for: {parameters.get('test_input', 'unknown')}"
            
            async def validate_parameters(self, parameters: dict):
                return "test_input" in parameters
        
        validation_cap = ValidationCapability()
        success = await registry.register_capability(validation_cap)
        
        if success:
            print_success("Custom capability registration successful")
        else:
            print_error("Custom capability registration failed")
            return False
        
        # Test filtering
        text_caps = registry.list_capabilities(category="text")
        testing_caps = registry.list_capabilities(category="testing")
        
        print_success(f"Capability filtering working - text: {len(text_caps)}, testing: {len(testing_caps)}")
        
        return True
        
    except Exception as e:
        print_error(f"Capability registry validation failed: {e}")
        return False

async def validate_context_manager():
    """Validate memory and context management"""
    print_header("Step 6.2.4: Context Manager Validation")
    
    try:
        from icpy.agent.memory.context_manager import (
            ContextManager, MemoryEntry, ContextSession, InMemoryStore, FileBasedStore
        )
        
        print_success("Context manager imports successful")
        
        # Test in-memory store
        memory_store = InMemoryStore()
        
        test_memory = MemoryEntry(
            content="Test memory for validation",
            memory_type="episodic",
            agent_id="validation_agent",
            session_id="validation_session",
            importance=0.8
        )
        
        success = await memory_store.store_memory(test_memory)
        if success:
            print_success("Memory storage successful")
        else:
            print_error("Memory storage failed")
            return False
        
        # Test memory retrieval
        memories = await memory_store.retrieve_memories("validation_agent")
        if len(memories) == 1 and memories[0].content == "Test memory for validation":
            print_success("Memory retrieval successful")
            print_info(f"   Retrieved: {memories[0].content}")
        else:
            print_error("Memory retrieval failed")
            return False
        
        # Test memory search
        search_results = await memory_store.search_memories("validation", "validation_agent")
        if len(search_results) == 1:
            print_success("Memory search successful")
        else:
            print_error("Memory search failed")
            return False
        
        # Test file-based store
        with tempfile.TemporaryDirectory() as temp_dir:
            file_store = FileBasedStore(temp_dir)
            
            file_memory = MemoryEntry(
                content="File-based test memory",
                memory_type="semantic",
                agent_id="file_agent",
                session_id="file_session"
            )
            
            success = await file_store.store_memory(file_memory)
            if success:
                print_success("File-based memory storage successful")
                
                # Verify file creation
                agent_dir = Path(temp_dir) / "file_agent"
                if agent_dir.exists():
                    print_info(f"   Memory files created in: {agent_dir}")
                else:
                    print_error("Memory files not created")
                    return False
            else:
                print_error("File-based memory storage failed")
                return False
        
        # Test context manager
        context_manager = ContextManager()
        
        # Create session
        session_id = await context_manager.create_session(
            agent_id="context_agent",
            session_type="validation",
            max_context_length=100
        )
        
        if session_id:
            print_success("Context session creation successful")
            print_info(f"   Session ID: {session_id}")
        else:
            print_error("Context session creation failed")
            return False
        
        # Store memories in session
        memory_id1 = await context_manager.store_memory(
            agent_id="context_agent",
            content="First context memory",
            session_id=session_id
        )
        
        memory_id2 = await context_manager.store_memory(
            agent_id="context_agent",
            content="Second context memory", 
            session_id=session_id
        )
        
        if memory_id1 and memory_id2:
            print_success("Session memory storage successful")
        else:
            print_error("Session memory storage failed")
            return False
        
        # Test shared context
        shared_context_id = await context_manager.create_shared_context(
            name="Validation Shared Context",
            description="Shared context for validation testing",
            participant_agents=["agent1", "agent2", "agent3"]
        )
        
        if shared_context_id:
            print_success("Shared context creation successful")
            print_info(f"   Shared context ID: {shared_context_id}")
        else:
            print_error("Shared context creation failed")
            return False
        
        # Test context retrieval
        context = await context_manager.get_session_context(session_id)
        if len(context) == 2:
            print_success("Context retrieval successful")
            print_info(f"   Retrieved {len(context)} memories")
        else:
            print_error("Context retrieval failed")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Context manager validation failed: {e}")
        return False

async def validate_agent_templates():
    """Validate agent templates and rapid development"""
    print_header("Step 6.2.5: Agent Templates Validation")
    
    try:
        from icpy.agent.configs.agent_templates import (
            template_manager, create_code_generator, create_documentation_writer,
            create_development_team_workflow, AgentTemplate
        )
        
        print_success("Agent templates imports successful")
        
        # Test built-in templates
        templates = template_manager.list_templates()
        template_names = [t.name for t in templates]
        
        expected_templates = [
            "code_generator", "documentation_writer", "test_engineer", 
            "development_team", "researcher"
        ]
        
        print_success(f"Built-in templates loaded: {len(templates)}")
        
        for template_name in expected_templates:
            if template_name in template_names:
                print_info(f"   ✓ {template_name}")
            else:
                print_error(f"   ✗ Missing template: {template_name}")
                return False
        
        # Test agent creation from templates
        coder_config = create_code_generator("validation_coder", language="python")
        if coder_config:
            print_success("Code generator creation successful")
            print_info(f"   Name: {coder_config.name}")
            print_info(f"   Role: {coder_config.role}")
            print_info(f"   Language: {coder_config.custom_config.get('preferred_language')}")
        else:
            print_error("Code generator creation failed")
            return False
        
        doc_config = create_documentation_writer("validation_writer", doc_type="api")
        if doc_config:
            print_success("Documentation writer creation successful")
            print_info(f"   Name: {doc_config.name}")
            print_info(f"   Goal: {doc_config.goal}")
        else:
            print_error("Documentation writer creation failed")
            return False
        
        # Test workflow creation from templates
        team_workflow = create_development_team_workflow("validation_team")
        if team_workflow:
            print_success("Development team workflow creation successful")
            print_info(f"   Name: {team_workflow.name}")
            print_info(f"   Tasks: {len(team_workflow.tasks)}")
            
            task_names = [task.name for task in team_workflow.tasks]
            expected_tasks = ["requirements_analysis", "architecture_design", "backend_development"]
            
            for task_name in expected_tasks:
                if task_name in task_names:
                    print_info(f"   ✓ Task: {task_name}")
                else:
                    print_error(f"   ✗ Missing task: {task_name}")
                    return False
        else:
            print_error("Development team workflow creation failed")
            return False
        
        # Test template categories
        dev_templates = template_manager.list_templates(category="development")
        doc_templates = template_manager.list_templates(category="documentation")
        
        print_success(f"Template filtering working - dev: {len(dev_templates)}, doc: {len(doc_templates)}")
        
        # Test custom template registration
        from icpy.agent.base_agent import AgentConfig
        
        custom_config = AgentConfig(
            name="validation_custom",
            framework="openai",
            role="Validation Specialist",
            goal="Perform comprehensive validation testing"
        )
        
        custom_template = AgentTemplate(
            name="validation_specialist",
            description="Custom template for validation testing",
            category="validation",
            config=custom_config,
            capabilities=["validation", "testing", "analysis"]
        )
        
        template_manager.register_template(custom_template)
        
        retrieved = template_manager.get_template("validation_specialist")
        if retrieved and retrieved.name == "validation_specialist":
            print_success("Custom template registration successful")
        else:
            print_error("Custom template registration failed")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Agent templates validation failed: {e}")
        return False

async def validate_integration():
    """Validate complete integration of all components"""
    print_header("Step 6.2.6: Integration Validation")
    
    try:
        # Import all components
        from icpy.agent.base_agent import DefaultAgent, AgentConfig
        from icpy.agent.workflows.workflow_engine import WorkflowEngine, WorkflowConfig, WorkflowTask
        from icpy.agent.registry.capability_registry import CapabilityRegistry
        from icpy.agent.memory.context_manager import ContextManager
        from icpy.agent.configs.agent_templates import create_code_generator
        
        print_success("All component imports successful")
        
        # Create integrated system
        registry = CapabilityRegistry()
        context_manager = ContextManager()
        await registry.initialize()
        
        # Create agents using templates
        coder_config = create_code_generator("integration_coder", "python")
        coder_agent = DefaultAgent(coder_config)
        await coder_agent.initialize()
        
        print_success("Template-based agent creation successful")
        
        # Attach capabilities
        await registry.attach_capability(coder_agent.agent_id, "code_generation")
        await registry.attach_capability(coder_agent.agent_id, "text_generation")
        
        capabilities = registry.get_agent_capabilities(coder_agent.agent_id)
        print_success(f"Capability attachment successful - {len(capabilities)} capabilities")
        
        # Create session for memory management
        session_id = await context_manager.create_session(
            agent_id=coder_agent.agent_id,
            session_type="development"
        )
        
        # Store some memories
        await context_manager.store_memory(
            agent_id=coder_agent.agent_id,
            content="Working on Python code generation project",
            session_id=session_id
        )
        
        print_success("Memory management integration successful")
        
        # Create workflow with the agent
        workflow_task = WorkflowTask(
            name="integrated_coding_task",
            task_content="Generate a Python function for fibonacci sequence",
            agent_config=coder_config
        )
        
        workflow_config = WorkflowConfig(
            name="integration_workflow",
            description="Integrated workflow test",
            tasks=[workflow_task]
        )
        
        engine = WorkflowEngine(workflow_config)
        await engine.initialize()
        success = await engine.execute()
        
        if success:
            print_success("Integrated workflow execution successful")
            print_info(f"   Workflow status: {engine.state.status.value}")
            print_info(f"   Completed tasks: {len(engine.state.completed_tasks)}")
        else:
            print_error("Integrated workflow execution failed")
            return False
        
        # Test capability execution through registry
        result = await registry.execute_capability(
            coder_agent.agent_id,
            "text_generation",
            {"prompt": "Summarize the integration test results"}
        )
        
        if result:
            print_success("Capability execution through registry successful")
            print_info(f"   Result length: {len(result)} characters")
        else:
            print_error("Capability execution through registry failed")
            return False
        
        # Cleanup
        await coder_agent.stop()
        await context_manager.end_session(session_id)
        
        print_success("Integration validation completed successfully")
        return True
        
    except Exception as e:
        print_error(f"Integration validation failed: {e}")
        return False

async def main():
    """Main validation function"""
    print_header("ICPY Step 6.2: Agentic Workflow Infrastructure Validation")
    print_info("Validating agent workflow infrastructure implementation...")
    
    validation_results = []
    
    # Run all validation tests
    validation_tests = [
        ("Agent Infrastructure", validate_agent_infrastructure),
        ("Workflow Engine", validate_workflow_engine),
        ("Capability Registry", validate_capability_registry),
        ("Context Manager", validate_context_manager),
        ("Agent Templates", validate_agent_templates),
        ("Integration", validate_integration)
    ]
    
    for test_name, test_func in validation_tests:
        print_info(f"\nRunning {test_name} validation...")
        try:
            result = await test_func()
            validation_results.append((test_name, result))
            if result:
                print_success(f"{test_name} validation PASSED")
            else:
                print_error(f"{test_name} validation FAILED")
        except Exception as e:
            print_error(f"{test_name} validation ERROR: {e}")
            validation_results.append((test_name, False))
    
    # Final summary
    print_header("Validation Summary")
    
    passed_tests = sum(1 for _, result in validation_results if result)
    total_tests = len(validation_results)
    
    for test_name, result in validation_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\n📊 Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print_success("🎉 Step 6.2 Validation Complete!")
        print_success("✅ All agentic workflow infrastructure components validated")
        print_success("✅ Agent base interfaces and lifecycle management working")
        print_success("✅ Workflow execution engine with async task management operational")
        print_success("✅ Capability registry and skill discovery functional")
        print_success("✅ Memory and context management infrastructure validated")
        print_success("✅ Agent templates and rapid development system working")
        print_success("✅ Complete integration between all components successful")
        return True
    else:
        print_error(f"❌ Step 6.2 Validation Failed: {total_tests - passed_tests} tests failed")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Validation script error: {e}")
        sys.exit(1)
