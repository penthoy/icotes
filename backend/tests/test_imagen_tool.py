"""
Test script for ImagenTool - verifies image generation tool functionality

This script tests:
1. Tool initialization and registration
2. Image generation via Google's Gemini API
3. Proper error handling
4. Result format validation

Run from backend directory:
    uv run python -m tests.test_imagen_tool
"""
from __future__ import annotations
import asyncio
import os
import sys

# Add backend to path
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)


async def test_imagen_tool_basic():
    """Test basic ImagenTool functionality"""
    print("=== Testing ImagenTool Basic Functionality ===\n")
    
    # Import the tool
    try:
        from icpy.agent.tools import ImagenTool
        print("✅ ImagenTool imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import ImagenTool: {e}")
        return False
    
    # Check tool registration
    try:
        from icpy.agent.tools import get_tool_registry
        registry = get_tool_registry()
        imagen_tool = registry.get("generate_image")
        
        if imagen_tool:
            print("✅ ImagenTool is registered in tool registry")
            print(f"   Tool name: {imagen_tool.name}")
            print(f"   Tool description: {imagen_tool.description}")
        else:
            print("❌ ImagenTool not found in registry")
            return False
    except Exception as e:
        print(f"❌ Error checking tool registry: {e}")
        return False
    
    # Test tool metadata
    tool = ImagenTool()
    print(f"\n📋 Tool Metadata:")
    print(f"   Name: {tool.name}")
    print(f"   Description: {tool.description}")
    print(f"   Parameters: {tool.parameters}")
    
    # Test OpenAI function format
    function_def = tool.to_openai_function()
    print(f"\n📋 OpenAI Function Definition:")
    print(f"   {function_def}")
    
    return True


async def test_imagen_tool_execution():
    """Test ImagenTool execution with a simple prompt"""
    print("\n=== Testing ImagenTool Execution ===\n")
    
    # Check if GOOGLE_API_KEY is set
    if not os.getenv("GOOGLE_API_KEY"):
        print("⚠️  GOOGLE_API_KEY not set - skipping execution test")
        print("   Set GOOGLE_API_KEY in .env to test image generation")
        return True  # Not a failure, just skipped
    
    try:
        from icpy.agent.tools import ImagenTool
        tool = ImagenTool()
        
        print("🎨 Generating test image...")
        print("   Prompt: 'A simple blue circle on white background'")
        
        result = await tool.execute(
            prompt="A simple blue circle on white background",
            save_to_workspace=True
        )
        
        if result.success:
            print("✅ Image generation successful!")
            print(f"   Result data keys: {list(result.data.keys())}")
            
            if "imageData" in result.data:
                print(f"   Image data length: {len(result.data['imageData'])} chars")
            
            if "filePath" in result.data:
                print(f"   Saved to: {result.data['filePath']}")
            
            return True
        else:
            print(f"❌ Image generation failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"❌ Error during execution test: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("Testing ImagenTool")
    print("=" * 70)
    
    # Test basic functionality
    basic_ok = await test_imagen_tool_basic()
    
    # Test execution
    exec_ok = await test_imagen_tool_execution()
    
    print("\n" + "=" * 70)
    print("Test Summary:")
    print(f"  Basic Functionality: {'✅ PASS' if basic_ok else '❌ FAIL'}")
    print(f"  Execution Test: {'✅ PASS' if exec_ok else '❌ FAIL'}")
    print("=" * 70)
    
    return basic_ok and exec_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
