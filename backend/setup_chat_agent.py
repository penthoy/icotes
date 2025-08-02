#!/usr/bin/env python3
"""
Chat Agent Setup Script
Configures a default OpenAI GPT-4o-mini agent for the chat service
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path="../.env")
except ImportError:
    print("Warning: python-dotenv not available, ensure environment variables are set")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import icpy modules
from icpy.agent.base_agent import AgentConfig
from icpy.services.agent_service import get_agent_service
from icpy.services.chat_service import get_chat_service


async def setup_chat_agent():
    """Setup and configure a default chat agent for OpenAI GPT-4o-mini"""
    try:
        print("🤖 Setting up Chat Agent (GPT-4o-mini)...")
        
        # Check API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not api_key.startswith("sk-"):
            print("❌ No valid OpenAI API key found in environment variables")
            print("   Please set OPENAI_API_KEY in your .env file")
            return False
        
        print(f"✅ OpenAI API key found: {api_key[:10]}...")
        
        # Get services
        agent_service = await get_agent_service()
        chat_service = get_chat_service()
        
        # Create agent configuration for GPT-4o-mini
        config = AgentConfig(
            framework="openai",
            name="chat_assistant",
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=1000,
            role="Helpful AI Assistant",
            goal="Provide informative, engaging, and concise responses to user queries",
            backstory="You are a knowledgeable AI assistant designed to help users with a wide variety of tasks and questions."
        )
        
        print("📝 Creating OpenAI agent with configuration:")
        print(f"   - Framework: {config.framework}")
        print(f"   - Model: {config.model}")
        print(f"   - Name: {config.name}")
        print(f"   - Temperature: {config.temperature}")
        print(f"   - Max Tokens: {config.max_tokens}")
        
        # Create the agent
        session_id = await agent_service.create_agent(config)
        if not session_id:
            print("❌ Failed to create agent")
            return False
        
        print(f"✅ Agent created with session ID: {session_id}")
        
        # Start the agent
        started = await agent_service.start_agent(session_id)
        if not started:
            print("❌ Failed to start agent")
            return False
        
        print("✅ Agent started successfully")
        
        # Configure chat service to use this agent
        await chat_service.update_config({
            'agent_id': config.name,
            'agent_name': 'GPT-4o-mini Assistant'
        })
        
        print("✅ Chat service configured to use the new agent")
        
        # Test the agent with a simple message
        print("\n🧪 Testing agent with a simple message...")
        try:
            task_config = {
                'type': 'chat_response',
                'user_message': 'Hello! Please respond with a brief greeting.',
                'session_id': 'test_session',
                'system_prompt': f"{config.role}. {config.goal}. {config.backstory}"
            }
            
            result = await agent_service.execute_agent_task(session_id, task_config)
            
            if result.get('success') and result.get('result'):
                print(f"✅ Test successful! Agent response: {result['result'][:100]}...")
            else:
                print(f"⚠️  Test completed but response may be empty: {result}")
        
        except Exception as e:
            print(f"⚠️  Test failed but agent should still work: {e}")
        
        print("\n🎉 Chat agent setup completed successfully!")
        print("   You can now use the chat interface with real GPT-4o-mini responses.")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to setup chat agent: {e}")
        logger.exception("Detailed error:")
        return False


async def main():
    """Main function"""
    print("=" * 60)
    print("🚀 Chat Agent Configuration Tool")
    print("=" * 60)
    
    success = await setup_chat_agent()
    
    if success:
        print("\n✅ Setup completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Setup failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
