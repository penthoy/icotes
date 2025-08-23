#!/usr/bin/env python3
"""
Test script to verify GPT-5 compatibility in OpenAI API helpers.

This script demonstrates the backward-compatible parameter selection
that allows the same code to work with both GPT-4 and GPT-5 models.
"""

import sys
import os
sys.path.append('.')

from icpy.agent.helpers import get_openai_token_param

def test_parameter_selection():
    """Test that the correct parameters are selected for different model families."""
    
    test_cases = [
        # GPT-4 family models - should use max_tokens
        ("gpt-4", "max_tokens"),
        ("gpt-4o", "max_tokens"),
        ("gpt-4o-mini", "max_tokens"),
        ("gpt-4-turbo", "max_tokens"),
        ("GPT-4", "max_tokens"),  # Test case insensitive
        
        # GPT-5 family models - should use max_completion_tokens
        ("gpt-5", "max_completion_tokens"),
        ("gpt-5-turbo", "max_completion_tokens"), 
        ("GPT-5-TURBO", "max_completion_tokens"),  # Test case insensitive
        
        # o1 family models - should use max_completion_tokens
        ("o1-mini", "max_completion_tokens"),
        ("o1-preview", "max_completion_tokens"),
        
        # Other models - should use max_tokens (fallback)
        ("claude-3-haiku", "max_tokens"),
        ("llama-3.1-70b", "max_tokens"),
    ]
    
    print("🧪 Testing OpenAI API parameter selection...")
    print()
    
    all_passed = True
    for model_name, expected_param in test_cases:
        result = get_openai_token_param(model_name, 1000)
        actual_param = list(result.keys())[0]
        token_value = result[actual_param]
        
        status = "✅" if actual_param == expected_param else "❌"
        print(f"{status} {model_name:<20} -> {actual_param} = {token_value}")
        
        if actual_param != expected_param:
            print(f"   Expected: {expected_param}, Got: {actual_param}")
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All tests passed! GPT-5 compatibility is working correctly.")
    else:
        print("💥 Some tests failed. Please check the parameter selection logic.")
    
    return all_passed

def demonstrate_api_call_preparation():
    """Demonstrate how the helper would be used in actual API calls."""
    
    print("\n📡 Demonstrating API call parameter preparation...")
    print()
    
    models_to_test = ["gpt-4o-mini", "gpt-5-turbo", "o1-mini"]
    
    for model in models_to_test:
        print(f"Model: {model}")
        
        # Simulate preparing API parameters
        base_params = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello!"}],
            "temperature": 0.7,
            "stream": True
        }
        
        # Add the appropriate token parameter
        token_params = get_openai_token_param(model, 2000)
        api_params = {**base_params, **token_params}
        
        print(f"  API Parameters: {list(api_params.keys())}")
        print(f"  Token Parameter: {list(token_params.keys())[0]} = {list(token_params.values())[0]}")
        print()

if __name__ == "__main__":
    print("🔧 OpenAI GPT-5 Compatibility Test")
    print("=" * 50)
    
    # Run parameter selection tests
    success = test_parameter_selection()
    
    # Demonstrate usage
    demonstrate_api_call_preparation()
    
    if success:
        print("\n✨ GPT-5 compatibility implementation is ready!")
        print("   • GPT-4 models use 'max_tokens' parameter")
        print("   • GPT-5 and o1 models use 'max_completion_tokens' parameter") 
        print("   • All other models default to 'max_tokens' parameter")
        print("   • The implementation is backward compatible")
    else:
        print("\n⚠️  Issues detected. Please review the implementation.")
        sys.exit(1)
