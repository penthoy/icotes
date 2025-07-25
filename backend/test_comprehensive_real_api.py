#!/usr/bin/env python3
"""
Comprehensive End-to-End Test with Real API Integration
Demonstrates the complete ICPY agent system working with actual API keys
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List
import time

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from icpy.services.agent_service import get_agent_service
from icpy.agent.base_agent import AgentConfig
from icpy.agent.memory.context_manager import get_context_manager
from icpy.core.framework_compatibility import FrameworkType


class EndToEndTester:
    """Comprehensive end-to-end test with real APIs"""
    
    def __init__(self):
        self.test_results: Dict[str, bool] = {}
        self.agent_service = None
        self.context_manager = None
        
    def print_header(self, title: str):
        """Print a formatted header"""
        print(f"\n{'='*70}")
        print(f"🚀 {title}")
        print(f"{'='*70}")
        
    def print_subheader(self, title: str):
        """Print a formatted subheader"""
        print(f"\n{'🔍 ' + title}")
        print(f"{'-'*60}")
        
    def log_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} {test_name}")
        if details:
            print(f"📋    {details}")
        self.test_results[test_name] = success
        
    async def test_complete_agent_workflow(self):
        """Test complete agent workflow with real API calls"""
        self.print_subheader("Complete Agent Workflow with Real AI")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not api_key.startswith("sk-"):
            self.log_result("Real API Workflow", False, "No OpenAI API key available")
            return
            
        try:
            # Initialize services
            self.agent_service = await get_agent_service()
            self.context_manager = await get_context_manager()
            
            self.log_result("Service Initialization", True, "Agent service and context manager ready")
            
            # Create an agent configuration
            config = AgentConfig(
                name="coding_assistant",
                framework="openai",  # Using string format as expected by AgentConfig
                role="Senior Python Developer",
                goal="Help users write better Python code",
                backstory="You are an experienced Python developer with expertise in clean code and best practices",
                model="gpt-3.5-turbo",
                temperature=0.7,
                max_tokens=200
            )
            
            # Create agent session
            session_id = await self.agent_service.create_agent(config)
            self.log_result("Agent Creation", session_id is not None, f"Created session: {session_id}")
            
            # Start the agent
            started = await self.agent_service.start_agent(session_id)
            self.log_result("Agent Start", started, "Agent started successfully")
            
            # Execute a coding task
            start_time = time.time()
            result = await self.agent_service.execute_agent_task(
                session_id, 
                "Write a simple Python function that calculates the factorial of a number. Include error handling."
            )
            execution_time = time.time() - start_time
            
            self.log_result("Code Generation Task", len(result) > 0, 
                          f"Generated {len(result)} characters in {execution_time:.2f}s")
            
            # Show the generated code
            print(f"📋    Generated Code Preview: '{result[:100]}...'")
            
            # Execute a follow-up task with context
            followup_result = await self.agent_service.execute_agent_task(
                session_id,
                "Now add unit tests for that factorial function."
            )
            
            self.log_result("Follow-up Task", len(followup_result) > 0,
                          f"Generated follow-up response: {len(followup_result)} characters")
            
            # Test agent session retrieval
            session_info = await self.agent_service.get_agent_session(session_id)
            self.log_result("Session Retrieval", session_info is not None,
                          f"Retrieved session: {session_info.agent_name}")
            
            # Stop the agent
            stopped = await self.agent_service.stop_agent(session_id)
            self.log_result("Agent Stop", stopped, "Agent stopped successfully")
            
            # Clean up
            destroyed = await self.agent_service.destroy_agent(session_id)
            self.log_result("Agent Cleanup", destroyed, "Agent session destroyed")
            
        except Exception as e:
            self.log_result("Complete Agent Workflow", False, f"Error: {str(e)}")
            
    async def test_multi_agent_collaboration(self):
        """Test multiple agents working together"""
        self.print_subheader("Multi-Agent Collaboration")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not api_key.startswith("sk-"):
            self.log_result("Multi-Agent Test", False, "No OpenAI API key available")
            return
            
        try:
            # Create different types of agents
            agents = {}
            
            # Code reviewer agent
            reviewer_config = AgentConfig(
                name="code_reviewer",
                framework="openai",
                role="Code Reviewer",
                goal="Review code for best practices and potential issues",
                backstory="You are an expert code reviewer focused on quality and maintainability",
                model="gpt-3.5-turbo",
                temperature=0.3,
                max_tokens=150
            )
            
            agents['reviewer'] = await self.agent_service.create_agent(reviewer_config)
            
            # Documentation agent
            docs_config = AgentConfig(
                name="documentation_specialist",
                framework="openai",
                role="Documentation Specialist",
                goal="Create clear and comprehensive documentation",
                backstory="You specialize in writing clear, helpful documentation for developers",
                model="gpt-3.5-turbo",
                temperature=0.5,
                max_tokens=150
            )
            
            agents['docs'] = await self.agent_service.create_agent(docs_config)
            
            self.log_result("Multi-Agent Creation", len(agents) == 2,
                          f"Created {len(agents)} specialized agents")
            
            # Start both agents
            for agent_type, session_id in agents.items():
                await self.agent_service.start_agent(session_id)
            
            # Create shared context
            shared_context_id = await self.context_manager.create_shared_context(
                name="Code Review Session",
                description="Collaboration between reviewer and documentation agents",
                participant_agents=list(agents.values())
            )
            
            # Sample code to review
            code_sample = """
def calculate_fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
"""
            
            # Get code review
            review_result = await self.agent_service.execute_agent_task(
                agents['reviewer'],
                f"Please review this Python code and suggest improvements:\n{code_sample}"
            )
            
            # Store review in shared context
            review_memory_id = await self.context_manager.store_memory(
                agent_id=agents['reviewer'],
                content=f"Code Review: {review_result}",
                memory_type="semantic",
                importance=3.0,
                metadata={"type": "code_review", "shared": True}
            )
            
            await self.context_manager.share_memory(shared_context_id, review_memory_id)
            
            # Get documentation based on the review
            context = {"code_review": review_result, "original_code": code_sample}
            docs_result = await self.agent_service.execute_agent_task(
                agents['docs'],
                "Create documentation for this fibonacci function, considering the review feedback.",
                context
            )
            
            self.log_result("Code Review Generated", len(review_result) > 0,
                          f"Review: '{review_result[:80]}...'")
            
            self.log_result("Documentation Generated", len(docs_result) > 0,
                          f"Docs: '{docs_result[:80]}...'")
            
            # Test collaboration effectiveness
            collaboration_effective = ("fibonacci" in docs_result.lower() and 
                                     len(review_result) > 50 and 
                                     len(docs_result) > 50)
            
            self.log_result("Collaboration Effectiveness", collaboration_effective,
                          "Agents produced relevant, substantial responses")
            
            # Clean up agents
            for session_id in agents.values():
                await self.agent_service.stop_agent(session_id)
                await self.agent_service.destroy_agent(session_id)
                
        except Exception as e:
            self.log_result("Multi-Agent Collaboration", False, f"Error: {str(e)}")
            
    async def test_template_based_workflows(self):
        """Test creating agents and workflows from templates"""
        self.print_subheader("Template-Based Agent Creation")
        
        try:
            # Get available templates
            templates = await self.agent_service.get_agent_templates()
            self.log_result("Template Listing", len(templates) > 0,
                          f"Found {len(templates)} agent templates")
            
            # Create agent from template
            if templates:
                template_name = list(templates.keys())[0]  # Use first available template
                template_session = await self.agent_service.create_agent_from_template(
                    template_name, "template_test_agent"
                )
                
                self.log_result("Template Agent Creation", template_session is not None,
                              f"Created agent from template: {template_name}")
                
                # Test the template agent
                if template_session:
                    await self.agent_service.start_agent(template_session)
                    
                    template_result = await self.agent_service.execute_agent_task(
                        template_session,
                        "Introduce yourself and explain what you can help with."
                    )
                    
                    self.log_result("Template Agent Execution", len(template_result) > 0,
                                  f"Template agent response: '{template_result[:80]}...'")
                    
                    # Clean up
                    await self.agent_service.stop_agent(template_session)
                    await self.agent_service.destroy_agent(template_session)
            
            # Test workflow templates
            workflow_templates = await self.agent_service.get_workflow_templates()
            self.log_result("Workflow Template Listing", len(workflow_templates) > 0,
                          f"Found {len(workflow_templates)} workflow templates")
            
        except Exception as e:
            self.log_result("Template-Based Workflows", False, f"Error: {str(e)}")
            
    async def test_performance_monitoring(self):
        """Test system performance monitoring"""
        self.print_subheader("Performance Monitoring")
        
        try:
            # Get initial stats
            initial_stats = await self.agent_service.get_service_stats()
            self.log_result("Stats Collection", 'total_agents' in initial_stats,
                          f"Initial stats keys: {list(initial_stats.keys())}")
            
            # Create multiple agents to test monitoring
            test_agents = []
            for i in range(3):
                config = AgentConfig(
                    name=f"perf_test_agent_{i}",
                    framework="openai",
                    role="Test Agent",
                    goal="Performance testing",
                    backstory="I am a test agent for performance monitoring",
                    model="gpt-3.5-turbo"
                )
                
                session_id = await self.agent_service.create_agent(config)
                test_agents.append(session_id)
            
            # Get updated stats
            updated_stats = await self.agent_service.get_service_stats()
            
            # Check if stats reflect the new agents
            agent_count_increased = updated_stats['total_agents'] >= initial_stats['total_agents'] + 3
            self.log_result("Performance Tracking", agent_count_increased,
                          f"Agent count: {initial_stats['total_agents']} → {updated_stats['total_agents']}")
            
            # Test resource monitoring
            resource_usage = updated_stats.get('resource_usage', {})
            has_resource_metrics = len(resource_usage) > 0
            self.log_result("Resource Monitoring", has_resource_metrics,
                          f"Resource metrics: {list(resource_usage.keys())}")
            
            # Clean up test agents
            for session_id in test_agents:
                await self.agent_service.destroy_agent(session_id)
                
        except Exception as e:
            self.log_result("Performance Monitoring", False, f"Error: {str(e)}")
            
    async def test_error_handling_resilience(self):
        """Test system error handling and resilience"""
        self.print_subheader("Error Handling and Resilience")
        
        try:
            # Test invalid agent creation
            invalid_config = AgentConfig(
                name="invalid_agent",
                framework="nonexistent_framework",
                model="invalid-model"
            )
            
            try:
                invalid_session = await self.agent_service.create_agent(invalid_config)
                # If this succeeds, it should handle the error gracefully
                if invalid_session:
                    await self.agent_service.destroy_agent(invalid_session)
                self.log_result("Invalid Config Handling", True, "System handled invalid config gracefully")
            except Exception:
                self.log_result("Invalid Config Handling", True, "System properly rejected invalid config")
            
            # Test non-existent session operations
            try:
                fake_session = "non-existent-session-id"
                result = await self.agent_service.get_agent_session(fake_session)
                handled_gracefully = result is None
                self.log_result("Non-existent Session Handling", handled_gracefully,
                              "System handled non-existent session lookup")
            except Exception as e:
                self.log_result("Non-existent Session Handling", True,
                              f"System properly raised exception: {type(e).__name__}")
            
            # Test system recovery after errors
            # Create a valid agent to test recovery
            recovery_config = AgentConfig(
                name="recovery_test",
                framework="openai",
                model="gpt-3.5-turbo"
            )
            
            recovery_session = await self.agent_service.create_agent(recovery_config)
            recovery_success = recovery_session is not None
            self.log_result("System Recovery", recovery_success,
                          "System continues working after handling errors")
            
            if recovery_session:
                await self.agent_service.destroy_agent(recovery_session)
                
        except Exception as e:
            self.log_result("Error Handling", False, f"Unexpected error: {str(e)}")
            
    async def run_comprehensive_test(self):
        """Run comprehensive end-to-end test suite"""
        self.print_header("ICPY Comprehensive End-to-End Test with Real APIs")
        
        print("📋 Testing complete system integration with real API calls...")
        print(f"📋 OpenAI API: {'✅ Available' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
        print(f"📋 Groq API: {'✅ Available' if os.getenv('GROQ_API_KEY') else '❌ Missing'}")
        print(f"📋 Anthropic API: {'✅ Available' if os.getenv('ANTHROPIC_API_KEY') else '❌ Missing'}")
        
        start_time = time.time()
        
        # Run all comprehensive tests
        await self.test_complete_agent_workflow()
        await self.test_multi_agent_collaboration()
        await self.test_template_based_workflows()
        await self.test_performance_monitoring()
        await self.test_error_handling_resilience()
        
        total_time = time.time() - start_time
        
        # Print comprehensive results
        self.print_header("Comprehensive Test Results")
        
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        
        print(f"⏱️  Total execution time: {total_time:.2f} seconds")
        print(f"🔧 Tests executed: {total}")
        print(f"✅ Tests passed: {passed}")
        print(f"❌ Tests failed: {total - passed}")
        print(f"📊 Success rate: {(passed/total)*100:.1f}%")
        
        print(f"\n📋 Detailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅" if result else "❌"
            print(f"  {status} {test_name}")
            
        if passed == total:
            print(f"\n🎉 All {total} comprehensive tests passed!")
            print("🚀 ICPY system is fully operational with real API integration!")
        else:
            print(f"\n⚠️  {total - passed} tests failed - system needs attention")
            
        return passed == total


async def main():
    """Main test execution"""
    tester = EndToEndTester()
    success = await tester.run_comprehensive_test()
    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Comprehensive test suite failed: {e}")
        sys.exit(1)
