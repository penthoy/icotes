#!/usr/bin/env python3
"""
Test script for Context Manager with real API integration
Demonstrates memory management, session handling, and context sharing with live AI responses
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

from icpy.agent.memory.context_manager import (
    ContextManager, 
    MemoryEntry, 
    ContextSession,
    InMemoryStore
)
from icpy.core.framework_compatibility import (
    FrameworkCompatibilityLayer, 
    FrameworkType, 
    AgentConfig
)


class ContextManagerTester:
    """Test context manager with real API calls"""
    
    def __init__(self):
        self.context_manager = ContextManager()
        self.framework_layer = FrameworkCompatibilityLayer()
        self.test_results: Dict[str, bool] = {}
        
    def print_header(self, title: str):
        """Print a formatted header"""
        print(f"\n{'='*60}")
        print(f"🧠 {title}")
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
        self.test_results[test_name] = success
        
    async def test_memory_storage_and_retrieval(self):
        """Test basic memory storage and retrieval"""
        self.print_subheader("Memory Storage and Retrieval")
        
        try:
            # Initialize context manager
            await self.context_manager.initialize()
            
            # Create a session
            session_id = await self.context_manager.create_session(
                agent_id="test_agent",
                session_type="conversation",
                max_context_length=10
            )
            
            self.log_result("Session Creation", session_id is not None, f"Session ID: {session_id}")
            
            # Store some memories
            memory_ids = []
            for i in range(5):
                memory_id = await self.context_manager.store_memory(
                    agent_id="test_agent",
                    content=f"Test memory {i+1}: This is a test conversation about AI agents",
                    memory_type="episodic",
                    session_id=session_id,
                    importance=float(i+1),
                    metadata={"step": i+1, "topic": "testing"}
                )
                memory_ids.append(memory_id)
            
            self.log_result("Memory Storage", len(memory_ids) == 5, f"Stored {len(memory_ids)} memories")
            
            # Retrieve memories
            retrieved = await self.context_manager.retrieve_memories(
                agent_id="test_agent",
                session_id=session_id
            )
            
            self.log_result("Memory Retrieval", len(retrieved) == 5, 
                          f"Retrieved {len(retrieved)} memories")
            
            # Test search
            search_results = await self.context_manager.search_memories(
                agent_id="test_agent",
                query="AI agents"
            )
            
            self.log_result("Memory Search", len(search_results) > 0, 
                          f"Found {len(search_results)} matching memories")
            
        except Exception as e:
            self.log_result("Memory Operations", False, f"Error: {str(e)}")
            
    async def test_context_with_real_ai(self):
        """Test context management with real AI interactions"""
        self.print_subheader("Context Management with Real AI")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not api_key.startswith("sk-"):
            self.log_result("Real AI Context Test", False, "No OpenAI API key available")
            return
            
        try:
            # Create an AI agent
            config = AgentConfig(
                framework=FrameworkType.OPENAI,
                name="context_test_agent",
                model="gpt-3.5-turbo",
                temperature=0.7,
                max_tokens=150,
                system_prompt="You are a helpful assistant. Remember previous context in conversations.",
                api_key=api_key
            )
            
            agent = await self.framework_layer.create_agent(config)
            self.log_result("AI Agent Creation", agent is not None, "Created OpenAI agent for context testing")
            
            # Create conversation session
            session_id = await self.context_manager.create_session(
                agent_id="context_ai_agent",
                session_type="conversation",
                max_context_length=20
            )
            
            # First interaction - establish context
            first_prompt = "My name is Alex and I'm working on a Python project about machine learning."
            response1 = await agent.execute(first_prompt)
            
            # Store the interaction in memory
            await self.context_manager.store_memory(
                agent_id="context_ai_agent",
                content=f"User: {first_prompt}\nAssistant: {response1.content}",
                memory_type="episodic",
                session_id=session_id,
                importance=2.0,
                metadata={"interaction": 1, "topic": "introduction"}
            )
            
            self.log_result("First AI Interaction", response1.content is not None, 
                          f"Response: '{response1.content[:50]}...'")
            
            # Second interaction - reference previous context
            # Retrieve context for the agent
            context_memories = await self.context_manager.get_session_context(session_id)
            context_info = {
                "previous_conversation": [mem.content for mem in context_memories[-3:]]
            }
            
            second_prompt = "What programming language am I working with?"
            response2 = await agent.execute(second_prompt, context_info)
            
            # Store second interaction
            await self.context_manager.store_memory(
                agent_id="context_ai_agent",
                content=f"User: {second_prompt}\nAssistant: {response2.content}",
                memory_type="episodic",
                session_id=session_id,
                importance=2.0,
                metadata={"interaction": 2, "topic": "context_reference"}
            )
            
            # Check if AI remembered Python from context
            python_mentioned = "python" in response2.content.lower()
            self.log_result("Context Memory Retention", python_mentioned, 
                          f"AI response: '{response2.content[:100]}...'")
            
            # Third interaction - complex context reference
            context_memories = await self.context_manager.get_session_context(session_id)
            context_info = {
                "conversation_history": [mem.content for mem in context_memories],
                "user_profile": {"name": "Alex", "project": "machine learning in Python"}
            }
            
            third_prompt = "Can you suggest a good ML library for my project?"
            response3 = await agent.execute(third_prompt, context_info)
            
            await self.context_manager.store_memory(
                agent_id="context_ai_agent",
                content=f"User: {third_prompt}\nAssistant: {response3.content}",
                memory_type="episodic",
                session_id=session_id,
                importance=3.0,
                metadata={"interaction": 3, "topic": "recommendations"}
            )
            
            # Check if response is relevant to ML and Python
            relevant_response = any(lib in response3.content.lower() for lib in ['sklearn', 'scikit-learn', 'pytorch', 'tensorflow', 'pandas', 'numpy', 'machine learning', 'ml'])
            self.log_result("Contextual Recommendations", relevant_response, 
                          f"AI suggested: '{response3.content[:100]}...'")
            
        except Exception as e:
            self.log_result("Real AI Context Test", False, f"Error: {str(e)}")
            
    async def test_shared_context(self):
        """Test shared context between multiple agents"""
        self.print_subheader("Shared Context Between Agents")
        
        try:
            # Create shared context
            context_id = await self.context_manager.create_shared_context(
                name="Team Project Discussion",
                description="Shared context for team members working on ML project",
                participant_agents=["agent_alice", "agent_bob"]
            )
            
            self.log_result("Shared Context Creation", context_id is not None, 
                          f"Created shared context: {context_id}")
            
            # Add memories to shared context
            shared_memory_id = await self.context_manager.store_memory(
                agent_id="agent_alice",
                content="We decided to use scikit-learn for the initial prototype",
                memory_type="semantic",
                importance=3.0,
                metadata={"shared": True, "decision": "library_choice"}
            )
            
            # Share the memory
            shared = await self.context_manager.share_memory(context_id, shared_memory_id)
            self.log_result("Memory Sharing", shared, "Memory shared in team context")
            
            # Add another agent to shared context
            added = await self.context_manager.add_agent_to_shared_context(context_id, "agent_charlie")
            self.log_result("Agent Addition to Shared Context", added, "Added new agent to shared context")
            
        except Exception as e:
            self.log_result("Shared Context Test", False, f"Error: {str(e)}")
            
    async def test_retention_policies(self):
        """Test different memory retention policies"""
        self.print_subheader("Memory Retention Policies")
        
        try:
            # Test FIFO retention
            fifo_session = await self.context_manager.create_session(
                agent_id="fifo_agent",
                session_type="conversation",
                max_context_length=3,
                retention_policy="fifo"
            )
            
            # Add more memories than the limit
            for i in range(5):
                await self.context_manager.store_memory(
                    agent_id="fifo_agent",
                    content=f"FIFO memory {i+1}",
                    session_id=fifo_session,
                    importance=1.0
                )
            
            fifo_memories = await self.context_manager.retrieve_memories(
                agent_id="fifo_agent",
                session_id=fifo_session
            )
            
            self.log_result("FIFO Retention Policy", len(fifo_memories) <= 3, 
                          f"FIFO kept {len(fifo_memories)} memories (limit: 3)")
            
            # Test importance-based retention
            importance_session = await self.context_manager.create_session(
                agent_id="importance_agent",
                session_type="conversation",
                max_context_length=3,
                retention_policy="importance"
            )
            
            # Add memories with different importance levels
            importances = [1.0, 3.0, 2.0, 5.0, 1.5]
            for i, imp in enumerate(importances):
                await self.context_manager.store_memory(
                    agent_id="importance_agent",
                    content=f"Importance memory {i+1} (importance: {imp})",
                    session_id=importance_session,
                    importance=imp
                )
            
            importance_memories = await self.context_manager.retrieve_memories(
                agent_id="importance_agent",
                session_id=importance_session
            )
            
            # Check if highest importance memories are kept
            kept_importances = [mem.importance for mem in importance_memories]
            high_importance_kept = all(imp >= 2.0 for imp in kept_importances)
            
            self.log_result("Importance Retention Policy", 
                          len(importance_memories) <= 3 and high_importance_kept, 
                          f"Kept {len(importance_memories)} memories with importances: {kept_importances}")
            
        except Exception as e:
            self.log_result("Retention Policies", False, f"Error: {str(e)}")
            
    async def test_context_summary(self):
        """Test context summary generation"""
        self.print_subheader("Context Summary Generation")
        
        try:
            # Create agent and add various memories
            agent_id = "summary_agent"
            
            # Add different types of memories
            memory_types = ["episodic", "semantic", "procedural"]
            for i, mem_type in enumerate(memory_types):
                for j in range(3):
                    await self.context_manager.store_memory(
                        agent_id=agent_id,
                        content=f"{mem_type.capitalize()} memory {j+1}: Details about {mem_type} information",
                        memory_type=mem_type,
                        importance=float(i+j+1),
                        metadata={"category": mem_type, "index": j}
                    )
            
            # Generate summary
            summary = await self.context_manager.get_agent_context_summary(agent_id)
            
            expected_keys = ['agent_id', 'total_memories', 'memory_types', 'average_importance', 'active_sessions', 'shared_contexts']
            has_all_keys = all(key in summary for key in expected_keys)
            
            self.log_result("Context Summary Generation", has_all_keys, 
                          f"Summary keys: {list(summary.keys())}")
            
            self.log_result("Memory Type Distribution", 
                          len(summary['memory_types']) == 3,
                          f"Memory types: {summary['memory_types']}")
            
        except Exception as e:
            self.log_result("Context Summary", False, f"Error: {str(e)}")
            
    async def test_cleanup_operations(self):
        """Test memory cleanup operations"""
        self.print_subheader("Memory Cleanup Operations")
        
        try:
            # Add some test memories
            cleanup_agent = "cleanup_agent"
            
            for i in range(5):
                await self.context_manager.store_memory(
                    agent_id=cleanup_agent,
                    content=f"Cleanup test memory {i+1}",
                    importance=1.0,
                    metadata={"test": "cleanup"}
                )
            
            # Get initial count
            initial_memories = await self.context_manager.retrieve_memories(cleanup_agent)
            initial_count = len(initial_memories)
            
            # Perform cleanup (using 0 retention days to clean everything)
            cleanup_results = await self.context_manager.cleanup_expired_data(retention_days=0)
            
            # Get final count
            final_memories = await self.context_manager.retrieve_memories(cleanup_agent)
            final_count = len(final_memories)
            
            self.log_result("Memory Cleanup", 
                          cleanup_results['expired_memories'] > 0,
                          f"Cleaned {cleanup_results['expired_memories']} memories, {final_count} remaining")
            
        except Exception as e:
            self.log_result("Cleanup Operations", False, f"Error: {str(e)}")
            
    async def run_all_tests(self):
        """Run all context manager tests"""
        self.print_header("Context Manager Real API Integration Tests")
        
        print("📋 Testing context management with real AI interactions...")
        print(f"📋 Using OpenAI API: {'✅ Available' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
        
        # Run all tests
        await self.test_memory_storage_and_retrieval()
        await self.test_context_with_real_ai()
        await self.test_shared_context()
        await self.test_retention_policies()
        await self.test_context_summary()
        await self.test_cleanup_operations()
        
        # Print summary
        self.print_header("Context Manager Test Results")
        
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅" if result else "❌"
            print(f"  {status} {test_name}")
            
        print(f"\n📊 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All context manager tests passed!")
        else:
            print(f"⚠️  {total - passed} tests failed")
            
        # Cleanup
        await self.context_manager.shutdown()
        
        return passed == total


async def main():
    """Main test execution"""
    tester = ContextManagerTester()
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
        print(f"\n❌ Context manager tests failed: {e}")
        sys.exit(1)
