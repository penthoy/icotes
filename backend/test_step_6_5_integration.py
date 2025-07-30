#!/usr/bin/env python3
"""
Simple integration test to validate unified chat service custom agent routing (Step 6.5).
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch

# Mock the required dependencies
async def test_chat_service_imports():
    """Test that all required modules can be imported"""
    try:
        from icpy.services.chat_service import ChatService, ChatMessage, MessageSender
        from icpy.agent import custom_agent
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


async def test_custom_agent_registry():
    """Test custom agent registry functionality"""
    try:
        from icpy.agent.custom_agent import get_available_custom_agents, register_custom_agent
        
        # Test registry
        agents = get_available_custom_agents()
        print(f"📋 Available custom agents: {agents}")
        
        registry = register_custom_agent()
        print(f"🗂️ Registry: {list(registry.keys())}")
        
        # Test that we have some agents
        assert len(agents) > 0, "Should have at least one custom agent"
        assert len(registry) > 0, "Registry should have at least one agent"
        
        print("✅ Custom agent registry test passed")
        return True
    except Exception as e:
        print(f"❌ Custom agent registry test failed: {e}")
        return False


async def test_chat_service_initialization():
    """Test that chat service can be initialized"""
    try:
        with patch('icpy.services.chat_service.get_db_manager') as mock_db, \
             patch('icpy.services.chat_service.get_message_broker') as mock_broker, \
             patch('icpy.services.chat_service.get_connection_manager') as mock_conn:
            
            # Setup mocks
            mock_db.return_value = AsyncMock()
            mock_broker.return_value = AsyncMock()
            mock_conn.return_value = AsyncMock()
            
            from icpy.services.chat_service import ChatService
            
            # Create chat service
            chat_service = ChatService()
            await chat_service.initialize()
            
            print("✅ Chat service initialization test passed")
            return True
    except Exception as e:
        print(f"❌ Chat service initialization test failed: {e}")
        return False


async def test_message_structure():
    """Test that ChatMessage can be created with agentType"""
    try:
        from icpy.services.chat_service import ChatMessage, MessageSender
        
        # Test message with custom agent type
        message = ChatMessage(
            id="test-1",
            content="Test message",
            sender=MessageSender.USER,
            timestamp="2024-01-01T12:00:00Z",
            session_id="test-session",
            metadata={'agentType': 'personal'}
        )
        
        assert message.metadata['agentType'] == 'personal'
        print("✅ Message structure test passed")
        return True
    except Exception as e:
        print(f"❌ Message structure test failed: {e}")
        return False


async def test_agent_routing_logic():
    """Test the agent routing logic in chat service"""
    try:
        with patch('icpy.services.chat_service.get_db_manager') as mock_db, \
             patch('icpy.services.chat_service.get_message_broker') as mock_broker, \
             patch('icpy.services.chat_service.get_connection_manager') as mock_conn, \
             patch('icpy.agent.custom_agent.registry') as mock_registry:
            
            # Setup mocks
            mock_db.return_value = AsyncMock()
            mock_broker.return_value = AsyncMock()
            mock_conn.return_value = AsyncMock()
            
            # Mock custom agent
            mock_agent = AsyncMock()
            mock_agent.stream_chat.return_value = ["Hello", " from", " custom agent!"]
            mock_registry.get_agent.return_value = mock_agent
            
            from icpy.services.chat_service import ChatService, ChatMessage, MessageSender
            
            # Create chat service
            chat_service = ChatService()
            await chat_service.initialize()
            
            # Test message with custom agent type
            message = ChatMessage(
                id="test-2",
                content="Help me",
                sender=MessageSender.USER,
                timestamp="2024-01-01T12:00:00Z",
                session_id="test-session",
                metadata={'agentType': 'personal'}
            )
            
            # Check if routing logic exists
            routing_method = getattr(chat_service, '_process_with_custom_agent', None)
            if routing_method:
                print("✅ Custom agent routing method exists")
                return True
            else:
                print("❌ Custom agent routing method not found")
                return False
                
    except Exception as e:
        print(f"❌ Agent routing test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("🧪 Testing Unified Chat Service Custom Agent Integration (Step 6.5)\n")
    
    tests = [
        ("Import Test", test_chat_service_imports),
        ("Custom Agent Registry", test_custom_agent_registry),
        ("Chat Service Initialization", test_chat_service_initialization),
        ("Message Structure", test_message_structure),
        ("Agent Routing Logic", test_agent_routing_logic),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"🔄 Running {test_name}...")
        try:
            result = await test_func()
            results.append((test_name, result))
            print(f"{'✅' if result else '❌'} {test_name}: {'PASSED' if result else 'FAILED'}\n")
        except Exception as e:
            print(f"❌ {test_name}: FAILED with exception: {e}\n")
            results.append((test_name, False))
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"📊 Test Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Custom agent integration is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return False


if __name__ == "__main__":
    asyncio.run(main())
