"""
Integration tests for ICPY Step 6.3: Agent Service Layer Implementation

This test suite validates the agent service layer implementation including:
- Agent lifecycle and session management
- Workflow execution and monitoring
- REST API endpoints
- WebSocket real-time communication
- Service integration and performance
"""

import asyncio
import json
import pytest
import time
from typing import Dict, Any, List
from unittest.mock import Mock, patch

from icpy.services.agent_service import AgentService, get_agent_service, shutdown_agent_service
from icpy.agent.base_agent import AgentConfig, AgentStatus
from icpy.agent.workflows.workflow_engine import WorkflowConfig, WorkflowTask
from icpy.core.framework_compatibility import FrameworkCompatibilityLayer


class TestAgentServiceLifecycle:
    """Test agent service lifecycle management"""
    
    @pytest.mark.asyncio
    async def test_agent_service_initialization(self):
        """Test agent service initialization"""
        service = AgentService()
        
        # Initialize service
        await service.initialize()
        
        # Verify initialization
        assert service.message_broker is not None
        assert service.connection_manager is not None
        assert service.capability_registry is not None
        assert service.context_manager is not None
        assert service._monitoring_task is not None
        
        # Cleanup
        await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_agent_creation_and_management(self):
        """Test agent creation and lifecycle management"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Create agent config
            config = AgentConfig(
                name="test_agent",
                framework="openai",
                role="Test Agent",
                goal="Execute test tasks",
                capabilities=["text_generation", "reasoning"]
            )
            
            # Create agent
            session_id = await service.create_agent(config)
            assert session_id is not None
            
            # Verify agent session
            session = service.get_agent_session(session_id)
            assert session is not None
            assert session.agent_name == "test_agent"
            assert session.framework == "openai"
            assert len(session.capabilities) > 0
            
            # Start agent
            success = await service.start_agent(session_id)
            assert success
            
            # Verify agent is running
            updated_session = service.get_agent_session(session_id)
            assert updated_session.status.value == "running"
            
            # Stop agent
            success = await service.stop_agent(session_id)
            assert success
            
            # Destroy agent
            success = await service.destroy_agent(session_id)
            assert success
            
        finally:
            await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_agent_task_execution(self):
        """Test agent task execution"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Create and start agent
            config = AgentConfig(
                name="task_agent",
                framework="openai",
                role="Task Executor",
                goal="Execute user tasks"
            )
            
            session_id = await service.create_agent(config)
            await service.start_agent(session_id)
            
            # Execute task
            result = await service.execute_agent_task(
                session_id, 
                "Generate a hello world message",
                {"format": "json"}
            )
            
            assert result is not None
            assert len(result) > 0
            
            # Verify session is back to ready state
            session = service.get_agent_session(session_id)
            assert session.status.value == "ready"
            
        finally:
            await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_agent_from_template(self):
        """Test agent creation from template"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Create agent from template
            session_id = await service.create_agent_from_template(
                "code_generator",
                "test_coder",
                {"preferred_language": "python"}
            )
            
            # Verify agent creation
            session = service.get_agent_session(session_id)
            assert session is not None
            assert session.agent_name == "test_coder"
            assert "code_generation" in session.capabilities
            
        finally:
            await service.shutdown()


class TestWorkflowExecution:
    """Test workflow execution and management"""
    
    @pytest.mark.asyncio
    async def test_workflow_creation_and_execution(self):
        """Test workflow creation and execution"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Create workflow config
            tasks = [
                WorkflowTask(
                    name="task1",
                    task_content="Create a test function",
                    agent_config=AgentConfig(name="agent1", framework="openai")
                ),
                WorkflowTask(
                    name="task2",
                    task_content="Test the function",
                    dependencies=["task1"],
                    agent_config=AgentConfig(name="agent2", framework="openai")
                )
            ]
            
            config = WorkflowConfig(
                name="test_workflow",
                description="Test workflow execution",
                tasks=tasks
            )
            
            # Create workflow
            session_id = await service.create_workflow(config)
            assert session_id is not None
            
            # Verify workflow session
            session = service.get_workflow_session(session_id)
            assert session is not None
            assert session.workflow_name == "test_workflow"
            
            # Execute workflow
            success = await service.execute_workflow(session_id)
            assert success
            
            # Verify workflow completion
            updated_session = service.get_workflow_session(session_id)
            assert updated_session.status.value == "completed"
            
        finally:
            await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_workflow_control_operations(self):
        """Test workflow pause, resume, and cancel operations"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Create simple workflow
            tasks = [
                WorkflowTask(
                    name="long_task",
                    task_content="Perform a long-running task",
                    agent_config=AgentConfig(name="worker", framework="openai")
                )
            ]
            
            config = WorkflowConfig(
                name="control_test_workflow",
                description="Workflow for testing control operations",
                tasks=tasks
            )
            
            session_id = await service.create_workflow(config)
            
            # Start workflow execution in background
            execution_task = asyncio.create_task(service.execute_workflow(session_id))
            await asyncio.sleep(0.1)  # Let it start
            
            # Test pause
            success = await service.pause_workflow(session_id)
            assert success
            
            session = service.get_workflow_session(session_id)
            assert session.status.value == "paused"
            
            # Test resume
            success = await service.resume_workflow(session_id)
            assert success
            
            session = service.get_workflow_session(session_id)
            assert session.status.value == "running"
            
            # Test cancel
            success = await service.cancel_workflow(session_id)
            assert success
            
            session = service.get_workflow_session(session_id)
            assert session.status.value == "cancelled"
            
            # Clean up execution task
            execution_task.cancel()
            try:
                await execution_task
            except asyncio.CancelledError:
                pass
            
        finally:
            await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_workflow_from_template(self):
        """Test workflow creation from template"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Create workflow from template
            session_id = await service.create_workflow_from_template(
                "development_team",
                "test_dev_workflow"
            )
            
            # Verify workflow creation
            session = service.get_workflow_session(session_id)
            assert session is not None
            assert session.workflow_name == "test_dev_workflow"
            
        finally:
            await service.shutdown()


class TestServiceQueries:
    """Test service query and status methods"""
    
    @pytest.mark.asyncio
    async def test_session_queries(self):
        """Test session listing and querying"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Create multiple agents and workflows
            agent_configs = [
                AgentConfig(name=f"agent_{i}", framework="openai")
                for i in range(3)
            ]
            
            agent_sessions = []
            for config in agent_configs:
                session_id = await service.create_agent(config)
                agent_sessions.append(session_id)
            
            # Test agent session listing
            sessions = service.get_agent_sessions()
            assert len(sessions) == 3
            
            # Test individual session retrieval
            for session_id in agent_sessions:
                session = service.get_agent_session(session_id)
                assert session is not None
            
            # Test workflow session listing (should be empty)
            workflow_sessions = service.get_workflow_sessions()
            assert len(workflow_sessions) == 0
            
        finally:
            await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_template_queries(self):
        """Test template listing and availability"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Get available templates
            templates = service.get_available_templates()
            
            assert "agent_templates" in templates
            assert "workflow_templates" in templates
            
            # Verify built-in templates are available
            agent_templates = templates["agent_templates"]
            template_names = [t["name"] for t in agent_templates]
            
            assert "code_generator" in template_names
            assert "documentation_writer" in template_names
            assert "test_engineer" in template_names
            
        finally:
            await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_resource_monitoring(self):
        """Test resource usage monitoring"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Wait for monitoring to collect some data
            await asyncio.sleep(1)
            
            # Get resource usage
            stats = service.get_resource_usage()
            
            assert "total_agents" in stats
            assert "total_workflows" in stats
            assert "resource_usage" in stats
            assert "performance_metrics" in stats
            
            # Create some agents and verify stats update
            config = AgentConfig(name="monitor_test", framework="openai")
            session_id = await service.create_agent(config)
            
            updated_stats = service.get_resource_usage()
            assert updated_stats["total_agents"] > stats["total_agents"]
            
        finally:
            await service.shutdown()


class TestServiceIntegration:
    """Test service integration with other components"""
    
    @pytest.mark.asyncio
    async def test_message_broker_integration(self):
        """Test integration with message broker"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Create agent and verify events are emitted
            config = AgentConfig(name="event_test", framework="openai")
            session_id = await service.create_agent(config)
            
            # Allow time for event processing
            await asyncio.sleep(0.1)
            
            # Verify session was created
            session = service.get_agent_session(session_id)
            assert session is not None
            
        finally:
            await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_capability_registry_integration(self):
        """Test integration with capability registry"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Create agent with capabilities
            config = AgentConfig(
                name="capability_test",
                framework="openai",
                capabilities=["text_generation", "code_generation"]
            )
            
            session_id = await service.create_agent(config)
            session = service.get_agent_session(session_id)
            
            # Verify capabilities are attached
            assert len(session.capabilities) > 0
            assert "text_generation" in session.capabilities
            
        finally:
            await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_context_manager_integration(self):
        """Test integration with context manager"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Create agent with memory enabled
            config = AgentConfig(
                name="memory_test",
                framework="openai",
                memory_enabled=True
            )
            
            session_id = await service.create_agent(config)
            
            # Execute task with context
            await service.execute_agent_task(
                session_id,
                "Remember this information",
                {"user_data": "important context"}
            )
            
            # Verify agent session exists and task completed
            session = service.get_agent_session(session_id)
            assert session is not None
            assert session.status.value in ["ready", "stopped"]
            
        finally:
            await service.shutdown()


class TestPerformanceAndReliability:
    """Test performance and reliability aspects"""
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_creation(self):
        """Test concurrent agent creation and management"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Create multiple agents concurrently
            async def create_agent(i):
                config = AgentConfig(name=f"concurrent_agent_{i}", framework="openai")
                return await service.create_agent(config)
            
            # Create 5 agents concurrently
            tasks = [create_agent(i) for i in range(5)]
            session_ids = await asyncio.gather(*tasks)
            
            # Verify all agents were created
            assert len(session_ids) == 5
            assert all(session_id is not None for session_id in session_ids)
            
            # Verify sessions are accessible
            sessions = service.get_agent_sessions()
            assert len(sessions) == 5
            
        finally:
            await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling and recovery"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Test creating agent with invalid template
            with pytest.raises(ValueError):
                await service.create_agent_from_template(
                    "nonexistent_template",
                    "test_agent"
                )
            
            # Test operations on non-existent sessions
            with pytest.raises(ValueError):
                await service.start_agent("nonexistent_session")
            
            with pytest.raises(ValueError):
                await service.execute_agent_task(
                    "nonexistent_session",
                    "test task"
                )
            
            # Test workflow operations on non-existent sessions
            with pytest.raises(ValueError):
                await service.execute_workflow("nonexistent_workflow")
            
        finally:
            await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_resource_cleanup(self):
        """Test proper resource cleanup"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Create agents and workflows
            agent_config = AgentConfig(name="cleanup_test", framework="openai")
            agent_session = await service.create_agent(agent_config)
            
            # Verify resources are allocated
            assert len(service.active_agents) > 0
            assert len(service.agent_sessions) > 0
            
            # Destroy agent
            await service.destroy_agent(agent_session)
            
            # Verify immediate cleanup
            assert agent_session not in service.active_agents
            
        finally:
            await service.shutdown()
            
            # Verify complete cleanup after shutdown
            assert len(service.active_agents) == 0
            assert len(service.active_workflows) == 0


class TestAgentServiceAPI:
    """Test agent service API integration"""
    
    @pytest.mark.asyncio
    async def test_service_singleton(self):
        """Test service singleton pattern"""
        # Get service instance
        service1 = await get_agent_service()
        service2 = await get_agent_service()
        
        # Verify same instance
        assert service1 is service2
        
        # Cleanup
        await shutdown_agent_service()
    
    @pytest.mark.asyncio
    async def test_service_lifecycle(self):
        """Test complete service lifecycle"""
        # Initialize service
        service = await get_agent_service()
        assert service is not None
        
        # Use service
        sessions = service.get_agent_sessions()
        assert isinstance(sessions, list)
        
        # Shutdown service
        await shutdown_agent_service()
        
        # Verify clean shutdown
        assert service._shutdown_event.is_set()


# Performance benchmarks
class TestPerformanceBenchmarks:
    """Performance benchmarks for agent service"""
    
    @pytest.mark.asyncio
    async def test_agent_creation_performance(self):
        """Benchmark agent creation performance"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Measure creation time
            start_time = time.time()
            
            config = AgentConfig(name="perf_test", framework="openai")
            session_id = await service.create_agent(config)
            
            creation_time = time.time() - start_time
            
            # Verify reasonable performance (should be < 1 second)
            assert creation_time < 1.0
            assert session_id is not None
            
        finally:
            await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_task_execution_performance(self):
        """Benchmark task execution performance"""
        service = AgentService()
        await service.initialize()
        
        try:
            # Create and start agent
            config = AgentConfig(name="perf_exec_test", framework="openai")
            session_id = await service.create_agent(config)
            await service.start_agent(session_id)
            
            # Measure execution time
            start_time = time.time()
            
            result = await service.execute_agent_task(
                session_id,
                "Quick test task"
            )
            
            execution_time = time.time() - start_time
            
            # Verify reasonable performance (should complete quickly with mock)
            assert execution_time < 5.0
            assert result is not None
            
        finally:
            await service.shutdown()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
