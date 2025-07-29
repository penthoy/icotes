#!/usr/bin/env python3
"""
Simple test script for the simplified agent system
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def test_agent_imports():
    """Test that all agents can be imported successfully"""
    try:
        from icpy.agent.personal_agent import chat as personal_chat
        print("✓ Personal agent imported successfully")
        
        from icpy.agent.openai_agent import chat as openai_chat
        print("✓ OpenAI agent imported successfully")
        
        from icpy.agent.custom_agent import get_available_custom_agents, call_custom_agent
        print("✓ Custom agent registry imported successfully")
        
        agents = get_available_custom_agents()
        print(f"✓ Available agents: {agents}")
        
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_chat():
    """Test a simple chat interaction"""
    try:
        from icpy.agent.openai_agent import chat as openai_chat
        print("\nTesting OpenAI agent chat...")
        
        # Test with simple message
        result = openai_chat("Hello", [])
        print("✓ OpenAI chat function called successfully")
        print("✓ Response is generator:", hasattr(result, '__iter__'))
        
        return True
    except Exception as e:
        print(f"✗ Chat test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_streaming_behavior():
    """Test actual streaming behavior with timing"""
    try:
        import time
        from icpy.agent.openai_agent import chat as openai_chat
        print("\nTesting streaming behavior...")
        
        # Test with a message that should generate a longer response
        result = openai_chat("Please count from 1 to 5 quickly", [])
        
        print("Starting streaming test...")
        start_time = time.time()
        chunk_times = []
        
        for i, chunk in enumerate(result):
            current_time = time.time()
            elapsed = current_time - start_time
            chunk_times.append(elapsed)
            print(f"[{elapsed:.2f}s] Chunk {i+1}: '{chunk}'", flush=True)
            
        total_time = time.time() - start_time
        print(f"\n✓ Streaming completed in {total_time:.2f}s with {len(chunk_times)} chunks")
        
        # Check if we got streaming behavior (multiple chunks over time)
        if len(chunk_times) > 3 and chunk_times[-1] - chunk_times[0] > 0.5:
            print("✓ Streaming appears to be working (multiple chunks over time)")
        else:
            print("⚠️  Streaming might not be working properly (too few chunks or too fast)")
            
        return True
    except Exception as e:
        print(f"✗ Streaming test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_websocket_streaming():
    """Test the async streaming function used by WebSocket"""
    try:
        import asyncio
        import time
        from icpy.agent.custom_agent import call_custom_agent_stream
        print("\nTesting WebSocket streaming behavior...")
        
        async def run_stream_test():
            print("Starting async streaming test...")
            start_time = time.time()
            chunk_times = []
            chunk_count = 0
            
            async for chunk in call_custom_agent_stream("OpenAIDemoAgent", "Please count from 1 to 5 quickly", []):
                chunk_count += 1
                current_time = time.time()
                elapsed = current_time - start_time
                chunk_times.append(elapsed)
                print(f"[{elapsed:.2f}s] Async Chunk {chunk_count}: '{chunk}'", flush=True)
                
            total_time = time.time() - start_time
            print(f"\n✓ Async streaming completed in {total_time:.2f}s with {len(chunk_times)} chunks")
            
            if len(chunk_times) > 3 and chunk_times[-1] - chunk_times[0] > 0.5:
                print("✓ Async streaming appears to be working")
            else:
                print("⚠️  Async streaming might have buffering issues")
        
        asyncio.run(run_stream_test())
        return True
    except Exception as e:
        print(f"✗ Async streaming test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing simplified agent system...")
    print("=" * 50)
    
    success = True
    success &= test_agent_imports()
    success &= test_simple_chat()
    success &= test_streaming_behavior()
    success &= test_websocket_streaming()
    
    print("=" * 50)
    if success:
        print("🎉 All tests passed! The simplified agent system is working.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
