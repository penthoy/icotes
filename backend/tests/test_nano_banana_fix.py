#!/usr/bin/env python3
"""
Test to verify Nano Banana agent can handle empty message with history.
"""
import sys
import os

# Add backend to path
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

# Add workspace plugins to path
workspace_plugins = os.path.join(os.path.dirname(backend_path), "workspace", ".icotes", "plugins")
sys.path.insert(0, workspace_plugins)

def test_empty_message_with_history():
    """Test that agent can extract message from history when message param is empty"""
    try:
        import nano_banana_agent
        
        # Simulate the scenario from chat_service where message is "" and history contains the actual message
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": [
                {"type": "text", "text": "can you create image of a dog?"}
            ]}
        ]
        
        print("Testing nano_banana_agent with empty message and history...")
        print(f"History has {len(history)} items")
        print(f"Last message: {history[-1]}")
        
        # This is what chat_service does - passes empty message
        message = ""
        
        # Try to get a response
        generator = nano_banana_agent.chat(message, history)
        
        first_chunk = None
        chunk_count = 0
        for chunk in generator:
            chunk_count += 1
            if first_chunk is None:
                first_chunk = chunk
            print(f"Chunk {chunk_count}: {chunk[:100] if len(chunk) > 100 else chunk}")
            
            # Don't run the full generation, just verify it starts without error
            if chunk_count >= 3 or "Error" in chunk or "🚫" in chunk:
                break
        
        if first_chunk and ("Error" in first_chunk or "🚫" in first_chunk or "empty" in first_chunk.lower()):
            print(f"\n❌ FAILED: Got error: {first_chunk}")
            return False
        
        print(f"\n✅ SUCCESS: Agent started processing without 'contents must not be empty' error")
        print(f"   Received {chunk_count} chunks")
        return True
        
    except Exception as e:
        print(f"\n❌ FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Check for Google API key
    if not os.environ.get("GOOGLE_API_KEY"):
        print("⚠️  WARNING: GOOGLE_API_KEY not set. Test may fail.")
        print("   Set it with: export GOOGLE_API_KEY='your-key-here'")
    
    success = test_empty_message_with_history()
    sys.exit(0 if success else 1)
