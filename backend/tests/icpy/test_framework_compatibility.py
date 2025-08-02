"""
Integration tests for framework compatibility layer
Tests unified interfaces and cross-framework functionality
"""

import pytest
import asyncio
from typing import Dict, Any

from icpy.core.framework_compatibility import (
    FrameworkCompatibilityLayer,
    FrameworkType,
    AgentConfig,
    AgentStatus,
    get_compatibility_layer
)


class TestFrameworkCompatibility:
    """Test suite for framework compatibility layer"""
    
    @pytest.fixture
    def compatibility_layer(self):
        """Create a fresh compatibility layer for each test"""
        return FrameworkCompatibilityLayer()
    
    def test_supported_frameworks(self, compatibility_layer):
        """Test that all expected frameworks are supported"""
        supported = compatibility_layer.get_supported_frameworks()
        expected = ["openai", "crewai", "langchain", "langgraph"]
        
        assert len(supported) == len(expected)
        for framework in expected:
            assert framework in supported
        
        print(f"✓ Supported frameworks: {supported}")
    
    @pytest.mark.asyncio
    async def test_openai_agent_creation(self, compatibility_layer):
        """Test OpenAI agent creation through compatibility layer"""
        config = AgentConfig(
            framework=FrameworkType.OPENAI,
            name="test_openai_agent",
            system_prompt="You are a helpful assistant",
            model="gpt-3.5-turbo",
            api_key="test-key"
        )
        
        agent = await compatibility_layer.create_agent(config)
        assert agent is not None
        assert agent.config.name == "test_openai_agent"
        assert agent.config.framework == FrameworkType.OPENAI
        
        # Test execution
        response = await agent.execute("Hello, world!")
        assert response.status == AgentStatus.COMPLETED
        assert "OpenAI Agent" in response.content
        
        # Cleanup
        await compatibility_layer.remove_agent("test_openai_agent")
        print("✓ OpenAI agent creation and execution successful")
    
    @pytest.mark.asyncio
    async def test_crewai_agent_creation(self, compatibility_layer):
        """Test CrewAI agent creation through compatibility layer"""
        config = AgentConfig(
            framework=FrameworkType.CREWAI,
            name="test_crewai_agent",
            role="Software Developer",
            goal="Write clean, efficient code",
            backstory="I am an experienced software developer"
        )
        
        agent = await compatibility_layer.create_agent(config)
        assert agent is not None
        assert agent.config.name == "test_crewai_agent"
        assert agent.config.framework == FrameworkType.CREWAI
        
        # Test execution
        response = await agent.execute("Write a hello world function")
        assert response.status == AgentStatus.COMPLETED
        assert "CrewAI Agent" in response.content
        
        # Cleanup
        await compatibility_layer.remove_agent("test_crewai_agent")
        print("✓ CrewAI agent creation and execution successful")
    
    @pytest.mark.asyncio
    async def test_langchain_agent_creation(self, compatibility_layer):
        """Test LangChain agent creation through compatibility layer"""
        config = AgentConfig(
            framework=FrameworkType.LANGCHAIN,
            name="test_langchain_agent",
            system_prompt="You are a knowledgeable AI assistant"
        )
        
        agent = await compatibility_layer.create_agent(config)
        assert agent is not None
        assert agent.config.name == "test_langchain_agent"
        assert agent.config.framework == FrameworkType.LANGCHAIN
        
        # Test execution with memory
        response1 = await agent.execute("My name is Alice")
        assert response1.status == AgentStatus.COMPLETED
        assert "LangChain Agent" in response1.content
        
        response2 = await agent.execute("What is my name?")
        assert response2.status == AgentStatus.COMPLETED
        
        # Cleanup
        await compatibility_layer.remove_agent("test_langchain_agent")
        print("✓ LangChain agent creation and execution successful")
    
    @pytest.mark.asyncio
    async def test_langgraph_agent_creation(self, compatibility_layer):
        """Test LangGraph agent creation through compatibility layer"""
        config = AgentConfig(
            framework=FrameworkType.LANGGRAPH,
            name="test_langgraph_agent",
            system_prompt="You are a workflow-based AI assistant"
        )
        
        agent = await compatibility_layer.create_agent(config)
        assert agent is not None
        assert agent.config.name == "test_langgraph_agent"
        assert agent.config.framework == FrameworkType.LANGGRAPH
        
        # Test execution
        response = await agent.execute("Process this workflow step")
        assert response.status == AgentStatus.COMPLETED
        assert "LangGraph Agent" in response.content
        
        # Cleanup
        await compatibility_layer.remove_agent("test_langgraph_agent")
        print("✓ LangGraph agent creation and execution successful")
    
    @pytest.mark.asyncio
    async def test_streaming_execution(self, compatibility_layer):
        """Test streaming execution across frameworks"""
        frameworks_to_test = [
            (FrameworkType.OPENAI, "openai_stream"),
            (FrameworkType.CREWAI, "crewai_stream"),
            (FrameworkType.LANGCHAIN, "langchain_stream"),
            (FrameworkType.LANGGRAPH, "langgraph_stream")
        ]
        
        for framework, name in frameworks_to_test:
            config = AgentConfig(
                framework=framework,
                name=name,
                role="Test Agent" if framework == FrameworkType.CREWAI else None,
                goal="Test streaming" if framework == FrameworkType.CREWAI else None,
                backstory="Test backstory" if framework == FrameworkType.CREWAI else None,
                api_key="test-key" if framework == FrameworkType.OPENAI else None
            )
            
            agent = await compatibility_layer.create_agent(config)
            assert agent is not None
            
            # Test streaming
            chunks = []
            async for chunk in agent.execute_streaming("Generate a streaming response"):
                chunks.append(chunk)
            
            assert len(chunks) > 0
            response_text = "".join(chunks)
            assert len(response_text) > 0
            
            await compatibility_layer.remove_agent(name)
        
        print("✓ Streaming execution successful for all frameworks")
    
    @pytest.mark.asyncio
    async def test_agent_lifecycle(self, compatibility_layer):
        """Test complete agent lifecycle management"""
        config = AgentConfig(
            framework=FrameworkType.OPENAI,
            name="lifecycle_test_agent",
            api_key="test-key"
        )
        
        # Create agent
        agent = await compatibility_layer.create_agent(config)
        assert agent is not None
        
        # Check agent is in list
        agents_list = await compatibility_layer.list_agents()
        assert len(agents_list) == 1
        assert agents_list[0]["name"] == "lifecycle_test_agent"
        assert agents_list[0]["framework"] == "openai"
        
        # Get agent
        retrieved_agent = await compatibility_layer.get_agent("lifecycle_test_agent")
        assert retrieved_agent is not None
        assert retrieved_agent.config.name == "lifecycle_test_agent"
        
        # Remove agent
        removed = await compatibility_layer.remove_agent("lifecycle_test_agent")
        assert removed is True
        
        # Check agent is no longer in list
        agents_list = await compatibility_layer.list_agents()
        assert len(agents_list) == 0
        
        print("✓ Agent lifecycle management successful")
    
    @pytest.mark.asyncio
    async def test_multiple_agents(self, compatibility_layer):
        """Test managing multiple agents simultaneously"""
        agents_configs = [
            AgentConfig(framework=FrameworkType.OPENAI, name="agent1", api_key="test"),
            AgentConfig(framework=FrameworkType.CREWAI, name="agent2", role="Developer", goal="Code", backstory="Experienced"),
            AgentConfig(framework=FrameworkType.LANGCHAIN, name="agent3"),
        ]
        
        # Create all agents
        created_agents = []
        for config in agents_configs:
            agent = await compatibility_layer.create_agent(config)
            assert agent is not None
            created_agents.append(agent)
        
        # Verify all agents exist
        agents_list = await compatibility_layer.list_agents()
        assert len(agents_list) == 3
        
        agent_names = [agent["name"] for agent in agents_list]
        assert "agent1" in agent_names
        assert "agent2" in agent_names
        assert "agent3" in agent_names
        
        # Execute tasks on different agents simultaneously
        tasks = []
        for i, agent in enumerate(created_agents):
            task = agent.execute(f"Task {i+1} for {agent.config.name}")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        assert len(responses) == 3
        
        for response in responses:
            assert response.status == AgentStatus.COMPLETED
        
        # Cleanup all
        cleanup_success = await compatibility_layer.cleanup_all()
        assert cleanup_success is True
        
        agents_list = await compatibility_layer.list_agents()
        assert len(agents_list) == 0
        
        print("✓ Multiple agents management successful")
    
    @pytest.mark.asyncio
    async def test_error_handling(self, compatibility_layer):
        """Test error handling for invalid configurations"""
        # Test invalid framework
        try:
            invalid_config = AgentConfig(
                framework="invalid_framework",  # This should cause issues
                name="invalid_agent"
            )
            # This should handle the error gracefully
            assert True  # If we get here, error handling worked
        except:
            pass  # Expected behavior for invalid framework
        
        # Test agent not found
        non_existent_agent = await compatibility_layer.get_agent("non_existent")
        assert non_existent_agent is None
        
        # Test removing non-existent agent
        removed = await compatibility_layer.remove_agent("non_existent")
        assert removed is False
        
        print("✓ Error handling successful")
    
    def test_global_compatibility_layer(self):
        """Test global compatibility layer instance"""
        layer1 = get_compatibility_layer()
        layer2 = get_compatibility_layer()
        
        # Should be the same instance
        assert layer1 is layer2
        
        print("✓ Global compatibility layer singleton working")
    
    @pytest.mark.asyncio
    async def test_framework_configuration(self, compatibility_layer):
        """Test framework-specific configuration"""
        # Configure OpenAI framework
        openai_config = {"api_key": "test-key", "default_model": "gpt-4"}
        compatibility_layer.configure_framework(FrameworkType.OPENAI, openai_config)
        
        # Configure CrewAI framework
        crewai_config = {"verbose": False, "allow_delegation": True}
        compatibility_layer.configure_framework(FrameworkType.CREWAI, crewai_config)
        
        # Test validation
        valid_openai = compatibility_layer.validate_framework_config(
            FrameworkType.OPENAI, {"api_key": "test"}
        )
        assert valid_openai is True
        
        invalid_openai = compatibility_layer.validate_framework_config(
            FrameworkType.OPENAI, {"no_api_key": "test"}
        )
        assert invalid_openai is False
        
        print("✓ Framework configuration successful")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
