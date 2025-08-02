#!/usr/bin/env python3
"""
Test script to verify personal agent tool call fix
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from icpy.agent.personal_agent import chat

def test_personal_agent_tool_call():
    """Test the personal agent with a question that should trigger the record_unknown_question tool"""
    print("Testing personal agent with question: 'are you a fighter pilot?'")
    print("This should trigger the record_unknown_question tool...")
    print("-" * 50)
    
    try:
        # Test the agent with the trigger question
        response_generator = chat("are you a fighter pilot?", "[]")
        
        full_response = ""
        for chunk in response_generator:
            print(chunk, end="", flush=True)
            full_response += chunk
        
        print("\n" + "-" * 50)
        print("✅ Test completed successfully!")
        print(f"Full response length: {len(full_response)} characters")
        
        # Check if tool processing messages are present
        if "[Processing tools...]" in full_response and "[Tools processed, generating response...]" in full_response:
            print("✅ Tool processing detected in response")
        else:
            print("⚠️  No tool processing detected in response")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_personal_agent_tool_call()
