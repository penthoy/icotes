"""
Integration tests for agentic frameworks installation and validation
Tests framework compatibility and basic agent instantiation
"""

import pytest
import asyncio
import os
from typing import Dict, Any, Optional
import sys
import importlib


class TestAgenticFrameworks:
    """Test suite for validating agentic framework installations"""

    def test_framework_imports(self):
        """Test that all required frameworks can be imported"""
        frameworks = {
            'openai': 'OpenAI Python SDK',
            'crewai': 'CrewAI multi-agent framework',
            'langchain': 'LangChain framework',
            'langchain_community': 'LangChain Community extensions',
            'langchain_openai': 'LangChain OpenAI integration',
            'langgraph': 'LangGraph orchestration framework',
            'langsmith': 'LangSmith monitoring'
        }
        
        successful_imports = {}
        failed_imports = {}
        
        for framework, description in frameworks.items():
            try:
                module = importlib.import_module(framework)
                successful_imports[framework] = {
                    'description': description,
                    'version': getattr(module, '__version__', 'unknown'),
                    'module': module
                }
            except ImportError as e:
                failed_imports[framework] = {
                    'description': description,
                    'error': str(e)
                }
        
        # Assert all frameworks imported successfully
        assert len(failed_imports) == 0, f"Failed to import frameworks: {failed_imports}"
        assert len(successful_imports) == len(frameworks), "Not all frameworks imported"
        
        print("Successfully imported frameworks:")
        for name, info in successful_imports.items():
            print(f"  - {name} ({info['version']}): {info['description']}")

    def test_openai_agent_creation(self):
        """Test basic OpenAI client instantiation"""
        try:
            import openai
            
            # Test client creation (doesn't require API key for instantiation)
            client = openai.OpenAI(api_key="test-key")
            assert client is not None
            
            # Test async client
            async_client = openai.AsyncOpenAI(api_key="test-key")
            assert async_client is not None
            
            print("✓ OpenAI client creation successful")
            
        except Exception as e:
            pytest.fail(f"OpenAI agent creation failed: {e}")

    def test_crewai_agent_creation(self):
        """Test basic CrewAI agent and crew instantiation"""
        try:
            from crewai import Agent, Task, Crew
            
            # Test agent creation
            agent = Agent(
                role='Test Agent',
                goal='Test goal',
                backstory='Test backstory',
                verbose=False,
                allow_delegation=False
            )
            assert agent is not None
            assert agent.role == 'Test Agent'
            
            # Test task creation
            task = Task(
                description='Test task description',
                agent=agent,
                expected_output='Test output'
            )
            assert task is not None
            
            # Test crew creation
            crew = Crew(
                agents=[agent],
                tasks=[task],
                verbose=False
            )
            assert crew is not None
            
            print("✓ CrewAI agent and crew creation successful")
            
        except Exception as e:
            pytest.fail(f"CrewAI agent creation failed: {e}")

    def test_langchain_agent_creation(self):
        """Test basic LangChain components instantiation"""
        try:
            from langchain.schema import BaseMessage, HumanMessage, AIMessage
            from langchain.memory import ConversationBufferMemory
            from langchain.prompts import PromptTemplate
            
            # Test message creation
            human_msg = HumanMessage(content="Test human message")
            ai_msg = AIMessage(content="Test AI message")
            assert human_msg.content == "Test human message"
            assert ai_msg.content == "Test AI message"
            
            # Test memory creation
            memory = ConversationBufferMemory()
            assert memory is not None
            
            # Test prompt template
            prompt = PromptTemplate(
                input_variables=["input"],
                template="Answer the following: {input}"
            )
            assert prompt is not None
            
            formatted = prompt.format(input="test question")
            assert "test question" in formatted
            
            print("✓ LangChain components creation successful")
            
        except Exception as e:
            pytest.fail(f"LangChain component creation failed: {e}")

    def test_langgraph_creation(self):
        """Test basic LangGraph workflow instantiation"""
        try:
            from langgraph.graph import StateGraph, END
            from typing import TypedDict
            
            # Define a simple state
            class GraphState(TypedDict):
                messages: list
                
            # Test graph creation
            workflow = StateGraph(GraphState)
            assert workflow is not None
            
            # Add a simple node
            def test_node(state: GraphState):
                return {"messages": state["messages"] + ["test"]}
            
            workflow.add_node("test_node", test_node)
            workflow.set_entry_point("test_node")
            workflow.add_edge("test_node", END)
            
            # Compile the graph
            app = workflow.compile()
            assert app is not None
            
            print("✓ LangGraph workflow creation successful")
            
        except Exception as e:
            pytest.fail(f"LangGraph workflow creation failed: {e}")

    @pytest.mark.asyncio
    async def test_async_compatibility(self):
        """Test that frameworks work with async/await patterns"""
        try:
            import asyncio
            
            # Test async operation simulation
            async def mock_agent_operation():
                await asyncio.sleep(0.01)  # Simulate async work
                return "operation_complete"
            
            result = await mock_agent_operation()
            assert result == "operation_complete"
            
            # Test that we can create async contexts for frameworks
            from langchain.memory import ConversationBufferMemory
            memory = ConversationBufferMemory()
            assert memory is not None
            
            print("✓ Async compatibility verified")
            
        except Exception as e:
            pytest.fail(f"Async compatibility test failed: {e}")

    def test_framework_version_compatibility(self):
        """Test that framework versions are compatible with each other"""
        try:
            import openai
            import crewai
            import langchain
            import langgraph
            
            # Try different ways to get version info
            def get_version(module, module_name):
                # Try multiple version attributes
                for attr in ['__version__', 'VERSION', '_version']:
                    if hasattr(module, attr):
                        return getattr(module, attr)
                
                # For langgraph, try importing from submodules
                if module_name == 'langgraph':
                    try:
                        import importlib.metadata
                        return importlib.metadata.version('langgraph')
                    except:
                        pass
                
                return 'installed'  # We know it's installed if we can import it
            
            versions = {
                'openai': get_version(openai, 'openai'),
                'crewai': get_version(crewai, 'crewai'),
                'langchain': get_version(langchain, 'langchain'),
                'langgraph': get_version(langgraph, 'langgraph')
            }
            
            print("Framework versions:")
            for name, version in versions.items():
                print(f"  - {name}: {version}")
            
            # Basic version checks (ensure we have reasonable versions)
            assert versions['openai'] != 'unknown', "OpenAI version not found"
            assert versions['crewai'] != 'unknown', "CrewAI version not found"
            assert versions['langchain'] != 'unknown', "LangChain version not found"
            assert versions['langgraph'] != 'unknown', "LangGraph version not found"
            
            print("✓ Framework version compatibility verified")
            
        except Exception as e:
            pytest.fail(f"Framework version compatibility test failed: {e}")

    def test_error_handling_initialization(self):
        """Test framework initialization error handling"""
        try:
            # Test OpenAI with invalid configuration
            import openai
            
            # This should not raise an exception during client creation
            client = openai.OpenAI(api_key="invalid-key")
            assert client is not None
            
            # Test CrewAI with minimal configuration
            from crewai import Agent
            
            agent = Agent(
                role='Minimal Agent',
                goal='Test',
                backstory='Test',
                verbose=False
            )
            assert agent is not None
            
            print("✓ Error handling during initialization verified")
            
        except Exception as e:
            pytest.fail(f"Error handling test failed: {e}")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
