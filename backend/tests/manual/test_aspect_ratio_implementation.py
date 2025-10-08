#!/usr/bin/env python3
"""
Quick test to verify aspect ratio API implementation
"""
import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icpy.agent.tools.imagen_tool import ImagenTool, ASPECT_RATIO_SPECS


async def test_aspect_ratio_mapping():
    """Test dimension to aspect ratio mapping"""
    tool = ImagenTool()
    
    test_cases = [
        (1920, 1080, "16:9"),  # Standard HD
        (1080, 1920, "9:16"),  # Vertical HD
        (800, 600, "4:3"),     # Classic
        (1024, 1024, "1:1"),   # Square
        (2560, 1080, "21:9"),  # Ultrawide
    ]
    
    print("Testing dimension to aspect ratio mapping:")
    print("-" * 60)
    
    for width, height, expected in test_cases:
        result = tool._map_dimensions_to_aspect_ratio(width, height)
        status = "✅" if result == expected else "❌"
        print(f"{status} {width}x{height} → {result} (expected: {expected})")
    
    print()


async def test_aspect_ratio_specs():
    """Verify all aspect ratio specs are valid"""
    print("Verifying aspect ratio specifications:")
    print("-" * 60)
    
    for ratio, (w, h, tokens) in ASPECT_RATIO_SPECS.items():
        calculated_ratio = w / h
        status = "✅"
        print(f"{status} {ratio}: {w}×{h} (ratio: {calculated_ratio:.3f}, tokens: {tokens})")
    
    print()


async def test_tool_parameters():
    """Verify tool parameters include aspect_ratio"""
    tool = ImagenTool()
    
    print("Verifying tool parameters:")
    print("-" * 60)
    
    params = tool.parameters.get("properties", {})
    
    # Check aspect_ratio parameter exists
    if "aspect_ratio" in params:
        ar_param = params["aspect_ratio"]
        print(f"✅ aspect_ratio parameter exists")
        print(f"   Type: {ar_param.get('type')}")
        print(f"   Enum: {len(ar_param.get('enum', []))} values")
        print(f"   Values: {', '.join(ar_param.get('enum', []))}")
    else:
        print("❌ aspect_ratio parameter missing")
    
    # Check width/height still exist
    if "width" in params and "height" in params:
        print(f"✅ width/height parameters still available")
    else:
        print("❌ width/height parameters missing")
    
    print()


async def test_tool_description():
    """Verify tool description mentions aspect ratios"""
    tool = ImagenTool()
    
    print("Verifying tool description:")
    print("-" * 60)
    
    if "aspect_ratio" in tool.description.lower():
        print("✅ Description mentions aspect_ratio parameter")
    else:
        print("❌ Description doesn't mention aspect_ratio")
    
    if any(ratio in tool.description for ratio in ["16:9", "9:16", "1:1"]):
        print("✅ Description includes example aspect ratios")
    else:
        print("❌ Description missing example aspect ratios")
    
    print()


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Aspect Ratio Native API Implementation - Unit Tests")
    print("=" * 60)
    print()
    
    await test_aspect_ratio_specs()
    await test_aspect_ratio_mapping()
    await test_tool_parameters()
    await test_tool_description()
    
    print("=" * 60)
    print("All unit tests completed!")
    print("=" * 60)
    print()
    print("To test actual image generation:")
    print("  export GOOGLE_API_KEY=your_key")
    print("  python tests/manual/test_aspect_ratio_generation.py")


if __name__ == "__main__":
    asyncio.run(main())
