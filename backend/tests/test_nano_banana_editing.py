#!/usr/bin/env python3
"""
Test script for Nano Banana Agent image editing capabilities.

This script demonstrates:
1. Text-only image generation (existing)
2. Image editing with multimodal input (NEW)
3. Image analysis (NEW)
"""

import sys
import os
import base64

# Add workspace plugins to path
sys.path.insert(0, '/home/penthoy/icotes/workspace/.icotes/plugins')

from nano_banana_agent import chat

def create_test_image():
    """Create a minimal 1x1 red pixel PNG for testing."""
    # 1x1 red pixel PNG
    red_pixel = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x00\xff\xffB\x80\x05\x1d\x02\t~\xe7\x00\x00\x00\x00IEND\xaeB`\x82'
    return base64.b64encode(red_pixel).decode('utf-8')

def test_text_only_generation():
    """Test 1: Text-only image generation (existing capability)."""
    print("\n" + "="*60)
    print("TEST 1: Text-only Image Generation")
    print("="*60)
    
    message = "Create a simple blue circle"
    print(f"Input: {message}")
    print("\nResponse:")
    
    try:
        response = ""
        for chunk in chat(message, []):
            print(chunk, end="", flush=True)
            response += chunk
        print("\n✅ Test 1 passed")
        return True
    except Exception as e:
        print(f"\n❌ Test 1 failed: {e}")
        return False

def test_multimodal_image_editing():
    """Test 2: Image editing with multimodal input (NEW capability)."""
    print("\n" + "="*60)
    print("TEST 2: Multimodal Image Editing")
    print("="*60)
    
    # Create multimodal message with text + image
    test_image_b64 = create_test_image()
    message = [
        {"type": "text", "text": "Add a yellow border to this image"},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{test_image_b64}"}}
    ]
    
    print(f"Input: Text + Image (1x1 PNG)")
    print("Instruction: 'Add a yellow border to this image'")
    print("\nResponse:")
    
    try:
        response = ""
        for chunk in chat(message, []):
            print(chunk, end="", flush=True)
            response += chunk
        print("\n✅ Test 2 passed")
        return True
    except Exception as e:
        print(f"\n❌ Test 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_image_analysis():
    """Test 3: Image analysis without generation (NEW capability)."""
    print("\n" + "="*60)
    print("TEST 3: Image Analysis")
    print("="*60)
    
    # Create multimodal message for analysis
    test_image_b64 = create_test_image()
    message = [
        {"type": "text", "text": "What color is this image? Just describe it, don't generate anything new."},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{test_image_b64}"}}
    ]
    
    print(f"Input: Text + Image (1x1 red pixel PNG)")
    print("Instruction: 'What color is this image?'")
    print("\nResponse:")
    
    try:
        response = ""
        for chunk in chat(message, []):
            print(chunk, end="", flush=True)
            response += chunk
        print("\n✅ Test 3 passed")
        return True
    except Exception as e:
        print(f"\n❌ Test 3 failed: {e}")
        return False

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("NANO BANANA AGENT - IMAGE EDITING CAPABILITY TESTS")
    print("="*60)
    
    # Check API key
    if not os.environ.get("GOOGLE_API_KEY"):
        print("\n⚠️  WARNING: GOOGLE_API_KEY not set")
        print("Tests will fail without API key. Set it with:")
        print("export GOOGLE_API_KEY='your-key-here'")
        return
    
    results = []
    
    # Run tests
    results.append(("Text Generation", test_text_only_generation()))
    results.append(("Image Editing", test_multimodal_image_editing()))
    results.append(("Image Analysis", test_image_analysis()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:20} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Image editing capability is working.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check configuration and API key.")

if __name__ == "__main__":
    main()
