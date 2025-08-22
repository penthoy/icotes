#!/usr/bin/env python3
"""
Test script to validate Anthropic client connectivity using get_anthropic_client.
This helps diagnose model connectivity issues and tests the latest Claude 4 models.
Updated to use claude-sonnet-4-20250514 (Claude Sonnet 4, released May 2025).
"""

import os
import sys
import traceback
from pathlib import Path

# Add the backend to the Python path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

def test_anthropic_client():
    """Test the get_anthropic_client function and validate connectivity."""
    print("🧪 Testing Anthropic Client Connectivity...")
    print("=" * 60)
    
    try:
        # Test import of the client function
        print("📋 Importing get_anthropic_client...")
        from icpy.agent.clients import get_anthropic_client
        print("✅ Successfully imported get_anthropic_client")
        
        # Check if API key is set
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_api_key:
            print(f"✅ ANTHROPIC_API_KEY is set (begins with: {anthropic_api_key[:8]}...)")
        else:
            print("❌ ANTHROPIC_API_KEY environment variable is not set")
            print("   Please set your Anthropic API key in your environment")
            return False
        
        # Test client initialization
        print("📋 Initializing Anthropic client...")
        client = get_anthropic_client()
        print("✅ Successfully initialized client")
        print(f"   Client type: {type(client)}")
        print(f"   Base URL: {getattr(client, 'base_url', 'N/A')}")
        
        # Test a simple API call
        print("📋 Testing API connectivity with a simple completion...")
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",  # Latest Claude Sonnet 4 model
                messages=[{"role": "user", "content": "Hello, respond with just 'API test successful'"}],
                max_tokens=10,
                temperature=0
            )
            
            if response and response.content:
                content = response.content[0].text
                print(f"✅ API call successful! Response: {content}")
                return True
            else:
                print("❌ API call returned empty response")
                return False
                
        except Exception as api_error:
            print(f"❌ API call failed: {api_error}")
            print("   This might indicate:")
            print("   - Invalid API key")
            print("   - Network connectivity issues") 
            print("   - Model name issues")
            print("   - Rate limiting")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   The icpy.agent.clients module may not be available")
        print("   Make sure you're running this from the workspace directory")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("   Full traceback:")
        traceback.print_exc()
        return False

def diagnose_claude_error():
    """Provide specific guidance for the claude-sonnet-4 error."""
    print("\n🔍 Diagnosing 'claude-sonnet-4' model error...")
    print("=" * 60)
    
    print("The error 'claude-sonnet-4' suggests:")
    print("1. ❌ 'claude-sonnet-4' is not a valid Anthropic model ID")
    print("2. ✅ Valid Claude model IDs include:")
    print("   - claude-opus-4-1-20250805 (Claude Opus 4.1 - most capable)")
    print("   - claude-opus-4-20250514 (Claude Opus 4 - very high capability)")
    print("   - claude-sonnet-4-20250514 (Claude Sonnet 4 - high performance)")
    print("   - claude-3-7-sonnet-20250219 (Claude Sonnet 3.7)")
    print("   - claude-3-5-haiku-20241022 (Claude Haiku 3.5 - fastest)")
    
    print("\n💡 Recommendation:")
    print("   Update the AGENT_MODEL_ID in your Claude agent to use:")
    print("   'claude-sonnet-4-20250514' (recommended for balanced performance)")
    print("   or 'claude-opus-4-1-20250805' for maximum capability")

def test_multiple_models():
    """Test multiple Claude models to ensure they're all accessible."""
    print("\n🧪 Testing Multiple Claude Models...")
    print("=" * 60)
    
    models_to_test = [
        "claude-opus-4-1-20250805",   # Claude Opus 4.1 (most capable)
        "claude-opus-4-20250514",     # Claude Opus 4
        "claude-sonnet-4-20250514",   # Claude Sonnet 4 (latest Sonnet)
        "claude-3-7-sonnet-20250219", # Claude Sonnet 3.7
        "claude-3-5-haiku-20241022"   # Claude Haiku 3.5 (fastest)
    ]
    
    try:
        from icpy.agent.clients import get_anthropic_client
        client = get_anthropic_client()
        
        results = {}
        
        for model in models_to_test:
            print(f"📋 Testing {model}...")
            try:
                response = client.messages.create(
                    model=model,
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=5,
                    temperature=0
                )
                
                if response and response.content:
                    results[model] = "✅ Success"
                    print(f"   ✅ {model} - Working")
                else:
                    results[model] = "❌ Empty response"
                    print(f"   ❌ {model} - Empty response")
                    
            except Exception as e:
                results[model] = f"❌ Error: {str(e)[:50]}..."
                print(f"   ❌ {model} - Error: {str(e)[:50]}...")
        
        print("\n📊 Model Test Summary:")
        for model, result in results.items():
            print(f"   {model}: {result}")
            
        return results
        
    except Exception as e:
        print(f"❌ Could not test models: {e}")
        return {}

if __name__ == "__main__":
    print("🚀 Claude Client Connectivity Test")
    print(f"Working directory: {os.getcwd()}")
    print(f"Backend path: {backend_path}")
    print()
    
    success = test_anthropic_client()
    
    if success:
        # If basic test passes, test multiple models
        model_results = test_multiple_models()
    else:
        diagnose_claude_error()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed! Anthropic client is working correctly.")
        print("💡 Recommendation: Use 'claude-sonnet-4-20250514' for the best balanced performance.")
        print("💡 Or use 'claude-opus-4-1-20250805' for maximum capability.")
    else:
        print("⚠️  Issues found. Please review the output above.")
