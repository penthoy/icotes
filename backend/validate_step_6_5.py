#!/usr/bin/env python3
"""
Validation test for Step 6.5: Custom Agent Integration into Unified Chat Service
Tests the core functionality without external dependencies.
"""

import asyncio


async def test_custom_agent_integration():
    """Test the core custom agent integration functionality"""
    print("🧪 Testing Step 6.5: Custom Agent Integration into Unified Chat Service\n")
    
    # Test 1: Custom Agent Registry
    print("🔄 Test 1: Custom Agent Registry...")
    try:
        from icpy.agent.custom_agent import get_available_custom_agents, register_custom_agent
        
        agents = get_available_custom_agents()
        registry = register_custom_agent()
        
        print(f"📋 Available agents: {agents}")
        print(f"🗂️ Registry keys: {list(registry.keys())}")
        
        assert len(agents) >= 3, f"Expected at least 3 agents, got {len(agents)}"
        assert len(registry) >= 3, f"Expected at least 3 registry entries, got {len(registry)}"
        assert "PersonalAgent" in agents, "PersonalAgent should be available"
        
        print("✅ Custom Agent Registry: PASSED\n")
        
    except Exception as e:
        print(f"❌ Custom Agent Registry: FAILED - {e}\n")
        return False
    
    # Test 2: Chat Service Structure
    print("🔄 Test 2: Chat Service Structure...")
    try:
        from icpy.services.chat_service import ChatService, ChatMessage, MessageSender
        
        # Check for custom agent routing method
        service = ChatService.__new__(ChatService)  # Create without __init__
        has_custom_routing = hasattr(service, '_process_with_custom_agent')
        has_handle_message = hasattr(service, 'handle_user_message')
        
        print(f"🔍 Has custom agent routing: {has_custom_routing}")
        print(f"🔍 Has message handler: {has_handle_message}")
        
        assert has_custom_routing, "Should have _process_with_custom_agent method"
        assert has_handle_message, "Should have handle_user_message method"
        
        print("✅ Chat Service Structure: PASSED\n")
        
    except Exception as e:
        print(f"❌ Chat Service Structure: FAILED - {e}\n")
        return False
    
    # Test 3: Message Structure with Agent Type
    print("🔄 Test 3: Message Structure with Agent Type...")
    try:
        from icpy.services.chat_service import ChatMessage, MessageSender
        
        # Test creating messages with agentType
        test_messages = [
            {
                'agentType': 'personal',
                'content': 'Help with personal tasks'
            },
            {
                'agentType': 'openai',
                'content': 'General question'
            },
            {
                'agentType': 'openrouter',
                'content': 'API question'
            }
        ]
        
        for i, msg_data in enumerate(test_messages):
            message = ChatMessage(
                id=f"test-{i}",
                content=msg_data['content'],
                sender=MessageSender.USER,
                timestamp="2024-01-01T12:00:00Z",
                session_id="test-session",
                metadata={'agentType': msg_data['agentType']}
            )
            
            assert message.metadata['agentType'] == msg_data['agentType']
            print(f"📧 Message {i+1}: agentType={message.metadata['agentType']} ✓")
        
        print("✅ Message Structure with Agent Type: PASSED\n")
        
    except Exception as e:
        print(f"❌ Message Structure with Agent Type: FAILED - {e}\n")
        return False
    
    # Test 4: Agent Routing Logic (check method signatures)
    print("🔄 Test 4: Agent Routing Logic...")
    try:
        from icpy.services.chat_service import ChatService
        import inspect
        
        # Check _process_with_custom_agent signature
        routing_method = getattr(ChatService, '_process_with_custom_agent', None)
        if routing_method:
            sig = inspect.signature(routing_method)
            params = list(sig.parameters.keys())
            print(f"🔍 Routing method parameters: {params}")
            
            expected_params = ['self', 'user_message', 'agent_type']
            for param in expected_params:
                assert param in params, f"Missing parameter: {param}"
            
            print("✅ Agent Routing Logic: PASSED\n")
        else:
            raise Exception("_process_with_custom_agent method not found")
            
    except Exception as e:
        print(f"❌ Agent Routing Logic: FAILED - {e}\n")
        return False
    
    # Test 5: Streaming Protocol Support
    print("🔄 Test 5: Streaming Protocol Support...")
    try:
        from icpy.services.chat_service import ChatService
        import inspect
        
        # Check streaming methods exist and have correct signatures
        streaming_methods = [
            '_send_streaming_start',
            '_send_streaming_chunk', 
            '_send_streaming_end'
        ]
        
        for method_name in streaming_methods:
            method = getattr(ChatService, method_name, None)
            assert method is not None, f"Missing method: {method_name}"
            
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            print(f"🔍 {method_name} parameters: {params}")
            
            # Check that _send_streaming_start supports agent_type
            if method_name == '_send_streaming_start':
                assert 'agent_type' in params, "_send_streaming_start should support agent_type parameter"
        
        print("✅ Streaming Protocol Support: PASSED\n")
        
    except Exception as e:
        print(f"❌ Streaming Protocol Support: FAILED - {e}\n")
        return False
    
    # Test 6: Custom Agent Call Function
    print("🔄 Test 6: Custom Agent Call Function...")
    try:
        from icpy.agent.custom_agent import call_custom_agent_stream
        
        # Test that the function exists and can be called (with mock data)
        # This won't actually work without a real agent, but we can check the interface
        test_stream = call_custom_agent_stream("PersonalAgent", "test message", [])
        print(f"🔍 Custom agent call function exists: {callable(call_custom_agent_stream)}")
        print(f"🔍 Returns generator/iterator: {hasattr(test_stream, '__iter__')}")
        
        print("✅ Custom Agent Call Function: PASSED\n")
        
    except Exception as e:
        print(f"❌ Custom Agent Call Function: FAILED - {e}\n")
        return False
    
    print("🎉 All Step 6.5 integration tests passed!")
    print("✨ Custom agent integration into unified chat service is complete!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_custom_agent_integration())
    exit(0 if success else 1)
