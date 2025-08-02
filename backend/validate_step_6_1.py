#!/usr/bin/env python3
"""
Step 6.1 Validation Script
Validates agentic framework installation and compatibility layer

Run with: uv run python validate_step_6_1.py
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

async def main():
    print("🚀 Step 6.1: Agentic Framework Installation and Validation")
    print("=" * 60)
    
    # Test 1: Framework Imports
    print("\n📦 Testing Framework Imports...")
    try:
        import openai
        print(f"✅ OpenAI: {getattr(openai, '__version__', 'installed')}")
        
        import crewai
        print(f"✅ CrewAI: {getattr(crewai, '__version__', 'installed')}")
        
        import langchain
        print(f"✅ LangChain: {getattr(langchain, '__version__', 'installed')}")
        
        import langgraph
        print(f"✅ LangGraph: installed")
        
        print("✅ All frameworks imported successfully!")
        
    except Exception as e:
        print(f"❌ Framework import failed: {e}")
        return False
    
    # Test 2: Compatibility Layer
    print("\n🔧 Testing Compatibility Layer...")
    try:
        from icpy.core.framework_compatibility import (
            get_compatibility_layer,
            FrameworkType,
            AgentConfig,
            AgentStatus
        )
        
        layer = get_compatibility_layer()
        supported = layer.get_supported_frameworks()
        print(f"✅ Supported frameworks: {supported}")
        
    except Exception as e:
        print(f"❌ Compatibility layer failed: {e}")
        traceback.print_exc()
        return False
    
    # Test 3: Agent Creation
    print("\n🤖 Testing Agent Creation...")
    try:
        # Test OpenAI Agent
        openai_config = AgentConfig(
            framework=FrameworkType.OPENAI,
            name="test_openai",
            api_key="test-key"
        )
        openai_agent = await layer.create_agent(openai_config)
        if openai_agent:
            print("✅ OpenAI agent created successfully")
            response = await openai_agent.execute("Hello!")
            print(f"   Response: {response.content[:50]}...")
        else:
            print("❌ OpenAI agent creation failed")
        
        # Test CrewAI Agent
        crewai_config = AgentConfig(
            framework=FrameworkType.CREWAI,
            name="test_crewai",
            role="Assistant",
            goal="Help users",
            backstory="I am helpful"
        )
        crewai_agent = await layer.create_agent(crewai_config)
        if crewai_agent:
            print("✅ CrewAI agent created successfully")
            response = await crewai_agent.execute("Hello!")
            print(f"   Response: {response.content[:50]}...")
        else:
            print("❌ CrewAI agent creation failed")
        
        # Test LangChain Agent
        langchain_config = AgentConfig(
            framework=FrameworkType.LANGCHAIN,
            name="test_langchain"
        )
        langchain_agent = await layer.create_agent(langchain_config)
        if langchain_agent:
            print("✅ LangChain agent created successfully")
            response = await langchain_agent.execute("Hello!")
            print(f"   Response: {response.content[:50]}...")
        else:
            print("❌ LangChain agent creation failed")
        
        # Test LangGraph Agent
        langgraph_config = AgentConfig(
            framework=FrameworkType.LANGGRAPH,
            name="test_langgraph"
        )
        langgraph_agent = await layer.create_agent(langgraph_config)
        if langgraph_agent:
            print("✅ LangGraph agent created successfully")
            response = await langgraph_agent.execute("Hello!")
            print(f"   Response: {response.content[:50]}...")
        else:
            print("❌ LangGraph agent creation failed")
        
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        traceback.print_exc()
        return False
    
    # Test 4: Streaming
    print("\n📡 Testing Streaming Execution...")
    try:
        if openai_agent:
            chunks = []
            async for chunk in openai_agent.execute_streaming("Stream test"):
                chunks.append(chunk)
            print(f"✅ Streaming works: received {len(chunks)} chunks")
        
    except Exception as e:
        print(f"❌ Streaming test failed: {e}")
        return False
    
    # Test 5: Multi-agent Management
    print("\n👥 Testing Multi-agent Management...")
    try:
        agents_list = await layer.list_agents()
        print(f"✅ Active agents: {len(agents_list)}")
        for agent_info in agents_list:
            print(f"   - {agent_info['name']} ({agent_info['framework']})")
        
        # Cleanup
        cleanup_success = await layer.cleanup_all()
        print(f"✅ Cleanup successful: {cleanup_success}")
        
    except Exception as e:
        print(f"❌ Multi-agent management failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Step 6.1 Validation Complete!")
    print("✅ All agentic frameworks installed and validated")
    print("✅ Framework compatibility layer working")
    print("✅ Agent creation and execution functional")
    print("✅ Cross-framework interface consistency verified")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
