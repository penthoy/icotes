#!/usr/bin/env python3
"""
Test script for real API integration with various AI frameworks
Tests actual API calls using keys from .env file
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

from icpy.core.framework_compatibility import (
    FrameworkCompatibilityLayer, 
    FrameworkType, 
    AgentConfig,
    OpenAIAgentWrapper,
    CrewAIAgentWrapper
)


class APIIntegrationTester:
    """Test actual API integration with various frameworks"""
    
    def __init__(self):
        self.framework_layer = FrameworkCompatibilityLayer()
        self.test_results: Dict[str, Dict[str, Any]] = {}
        
    def print_header(self, title: str):
        """Print a formatted header"""
        print(f"\n{'='*60}")
        print(f"🚀 {title}")
        print(f"{'='*60}")
        
    def print_subheader(self, title: str):
        """Print a formatted subheader"""
        print(f"\n{'🔍 ' + title}")
        print(f"{'-'*50}")
        
    def log_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} {test_name}")
        if details:
            print(f"📋    {details}")
            
        # Store result
        framework = test_name.split()[0].lower()
        if framework not in self.test_results:
            self.test_results[framework] = {}
        self.test_results[framework][test_name] = {
            'success': success,
            'details': details
        }
        
    async def test_openai_integration(self):
        """Test OpenAI API integration"""
        self.print_subheader("OpenAI API Integration Test")
        
        try:
            # Check API key
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key or not api_key.startswith("sk-"):
                self.log_result("OpenAI API Key Check", False, "No valid OpenAI API key found")
                return
            
            self.log_result("OpenAI API Key Check", True, f"API key found: {api_key[:10]}...")
            
            # Test basic agent creation
            config = AgentConfig(
                framework=FrameworkType.OPENAI,
                name="test_openai_agent",
                model="gpt-3.5-turbo",
                temperature=0.7,
                max_tokens=100,
                system_prompt="You are a helpful AI assistant. Keep responses concise.",
                api_key=api_key
            )
            
            agent = await self.framework_layer.create_agent(config)
            if not agent:
                self.log_result("OpenAI Agent Creation", False, "Failed to create agent")
                return
                
            self.log_result("OpenAI Agent Creation", True, "Agent created successfully")
            
            # Test basic execution
            start_time = time.time()
            response = await agent.execute("What is 2+2? Give a very brief answer.")
            execution_time = time.time() - start_time
            
            if response.content and len(response.content) > 0:
                self.log_result("OpenAI Basic Execution", True, 
                              f"Response: '{response.content[:50]}...' (took {execution_time:.2f}s)")
            else:
                self.log_result("OpenAI Basic Execution", False, "No response content")
                
            # Test streaming execution
            self.print_subheader("OpenAI Streaming Test")
            stream_content = ""
            chunk_count = 0
            
            start_time = time.time()
            async for chunk in agent.execute_streaming("Write a haiku about coding. Be creative."):
                stream_content += chunk
                chunk_count += 1
            stream_time = time.time() - start_time
            
            if stream_content and chunk_count > 1:
                self.log_result("OpenAI Streaming Execution", True, 
                              f"Streamed {chunk_count} chunks, content: '{stream_content[:50]}...' (took {stream_time:.2f}s)")
            else:
                self.log_result("OpenAI Streaming Execution", False, "Streaming failed")
                
            # Test with context
            context = {"task_type": "math", "difficulty": "easy"}
            response = await agent.execute("Solve this: 15 * 7", context)
            
            if response.content:
                self.log_result("OpenAI Context Execution", True, 
                              f"Response with context: '{response.content[:50]}...'")
            else:
                self.log_result("OpenAI Context Execution", False, "No response with context")
                
            # Test error handling
            try:
                bad_config = AgentConfig(
                    framework=FrameworkType.OPENAI,
                    name="bad_agent",
                    model="nonexistent-model",
                    api_key=api_key
                )
                bad_agent = await self.framework_layer.create_agent(bad_config)
                response = await bad_agent.execute("Test")
                
                if response.status.value == "failed":
                    self.log_result("OpenAI Error Handling", True, "Properly handled invalid model")
                else:
                    self.log_result("OpenAI Error Handling", False, "Should have failed with invalid model")
            except Exception as e:
                self.log_result("OpenAI Error Handling", True, f"Properly caught exception: {str(e)[:50]}...")
                
        except Exception as e:
            self.log_result("OpenAI Integration", False, f"Unexpected error: {str(e)}")
            
    async def test_crewai_integration(self):
        """Test CrewAI integration"""
        self.print_subheader("CrewAI Integration Test")
        
        try:
            # Check API key (CrewAI uses OpenAI by default)
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key or not api_key.startswith("sk-"):
                self.log_result("CrewAI API Key Check", False, "No valid OpenAI API key for CrewAI")
                return
                
            self.log_result("CrewAI API Key Check", True, f"API key available for CrewAI")
            
            # Test agent creation
            config = AgentConfig(
                framework=FrameworkType.CREWAI,
                name="test_crewai_agent",
                role="Data Analyst",
                goal="Analyze and interpret data to provide insights",
                backstory="You are an experienced data analyst with expertise in statistical analysis",
                model="gpt-3.5-turbo"
            )
            
            agent = await self.framework_layer.create_agent(config)
            if not agent:
                self.log_result("CrewAI Agent Creation", False, "Failed to create CrewAI agent")
                return
                
            self.log_result("CrewAI Agent Creation", True, "CrewAI agent created successfully")
            
            # Test execution
            start_time = time.time()
            response = await agent.execute("Analyze the trend: Sales increased 20% in Q1, 15% in Q2, 5% in Q3. What do you conclude?")
            execution_time = time.time() - start_time
            
            if response.content and len(response.content) > 0:
                self.log_result("CrewAI Execution", True, 
                              f"Response: '{response.content[:100]}...' (took {execution_time:.2f}s)")
            else:
                self.log_result("CrewAI Execution", False, "No response content from CrewAI")
                
            # Test streaming
            stream_content = ""
            async for chunk in agent.execute_streaming("Give me 3 quick tips for data visualization"):
                stream_content += chunk
                
            if stream_content:
                self.log_result("CrewAI Streaming", True, f"Streaming worked: '{stream_content[:50]}...'")
            else:
                self.log_result("CrewAI Streaming", False, "No streaming content")
                
        except Exception as e:
            self.log_result("CrewAI Integration", False, f"Error: {str(e)}")
            
    async def test_framework_compatibility_layer(self):
        """Test the framework compatibility layer"""
        self.print_subheader("Framework Compatibility Layer Test")
        
        try:
            # Test framework detection
            frameworks = [FrameworkType.OPENAI, FrameworkType.CREWAI]
            
            for framework in frameworks:
                config = AgentConfig(
                    framework=framework,
                    name=f"test_{framework.value}_agent",
                    model="gpt-3.5-turbo"
                )
                
                agent = await self.framework_layer.create_agent(config)
                if agent:
                    self.log_result(f"Framework Layer {framework.value}", True, "Framework properly detected and agent created")
                else:
                    self.log_result(f"Framework Layer {framework.value}", False, "Failed to create agent through compatibility layer")
                    
        except Exception as e:
            self.log_result("Framework Compatibility Layer", False, f"Error: {str(e)}")
            
    async def test_performance_benchmarks(self):
        """Test performance with real API calls"""
        self.print_subheader("Performance Benchmarks")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not api_key.startswith("sk-"):
            self.log_result("Performance Benchmark", False, "No API key for performance testing")
            return
            
        try:
            config = AgentConfig(
                framework=FrameworkType.OPENAI,
                name="benchmark_agent",
                model="gpt-3.5-turbo",
                max_tokens=50,
                api_key=api_key
            )
            
            agent = await self.framework_layer.create_agent(config)
            
            # Test multiple concurrent requests
            tasks = []
            start_time = time.time()
            
            for i in range(3):  # Keep it small to avoid rate limits
                task = agent.execute(f"Count from 1 to 5. Request #{i+1}")
                tasks.append(task)
                
            responses = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            successful_responses = [r for r in responses if r.content and r.status.value == "completed"]
            
            self.log_result("Performance Concurrent Requests", 
                          len(successful_responses) == 3,
                          f"{len(successful_responses)}/3 requests succeeded in {total_time:.2f}s")
                          
        except Exception as e:
            self.log_result("Performance Benchmark", False, f"Error: {str(e)}")
            
    async def test_context_management(self):
        """Test context and memory management with real APIs"""
        self.print_subheader("Context Management Test")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not api_key.startswith("sk-"):
            self.log_result("Context Management", False, "No API key for context testing")
            return
            
        try:
            config = AgentConfig(
                framework=FrameworkType.OPENAI,
                name="context_agent",
                model="gpt-3.5-turbo",
                max_tokens=100,
                system_prompt="You are a helpful assistant. Remember previous context.",
                api_key=api_key
            )
            
            agent = await self.framework_layer.create_agent(config)
            
            # First interaction
            response1 = await agent.execute("My name is Alice and I love pizza.")
            
            # Second interaction with context reference
            context = {"previous_info": "User introduced themselves as Alice who loves pizza"}
            response2 = await agent.execute("What do I like to eat?", context)
            
            if response2.content and "pizza" in response2.content.lower():
                self.log_result("Context Memory", True, "Agent remembered context about pizza")
            else:
                self.log_result("Context Memory", False, f"Agent didn't use context properly: '{response2.content}'")
                
        except Exception as e:
            self.log_result("Context Management", False, f"Error: {str(e)}")
            
    async def run_all_tests(self):
        """Run all API integration tests"""
        self.print_header("ICPY Real API Integration Test Suite")
        
        print("📋 Testing actual API integrations with environment keys...")
        print(f"📋 OpenAI Key: {'✅ Available' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
        print(f"📋 Groq Key: {'✅ Available' if os.getenv('GROQ_API_KEY') else '❌ Missing'}")
        print(f"📋 Anthropic Key: {'✅ Available' if os.getenv('ANTHROPIC_API_KEY') else '❌ Missing'}")
        
        # Run tests
        await self.test_openai_integration()
        await self.test_crewai_integration()
        await self.test_framework_compatibility_layer()
        await self.test_performance_benchmarks()
        await self.test_context_management()
        
        # Print summary
        self.print_header("Test Results Summary")
        
        total_tests = 0
        passed_tests = 0
        
        for framework, tests in self.test_results.items():
            print(f"\n🔍 {framework.upper()} Framework:")
            for test_name, result in tests.items():
                status = "✅" if result['success'] else "❌"
                print(f"  {status} {test_name}")
                total_tests += 1
                if result['success']:
                    passed_tests += 1
                    
        print(f"\n📊 Overall Results: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All API integration tests passed!")
        else:
            print(f"⚠️  {total_tests - passed_tests} tests failed - check logs above")
            
        return passed_tests == total_tests


async def main():
    """Main test execution"""
    tester = APIIntegrationTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        sys.exit(1)
