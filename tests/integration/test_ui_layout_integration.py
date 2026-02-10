#!/usr/bin/env python3
"""
Integration Test: UI Layout System
Tests Phase 1-4 implementation end-to-end
"""

import asyncio
import json
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from icpy.agent.tools import UILayoutTool, get_tool_registry


async def test_tool_registration():
    """Test that UILayoutTool is properly registered"""
    print("✓ Testing tool registration...")
    
    registry = get_tool_registry()
    tools = registry.all()
    
    ui_layout_tool = None
    for tool in tools:
        if tool.name == 'ui_layout':
            ui_layout_tool = tool
            break
    
    assert ui_layout_tool is not None, "UILayoutTool not found in registry"
    assert isinstance(ui_layout_tool, UILayoutTool), "Tool is not UILayoutTool instance"
    print(f"  ✓ UILayoutTool registered: {ui_layout_tool.name}")
    print(f"  ✓ Description: {ui_layout_tool.description[:80]}...")
    return ui_layout_tool


async def test_get_layout_action(tool):
    """Test get_layout action (doesn't need WebSocket)"""
    print("\n✓ Testing get_layout action...")
    
    result = await tool.execute(action='get_layout')
    
    assert result.success, f"get_layout failed: {result.error}"
    print(f"  ✓ Success: {result.data.get('message', 'OK')}")
    print(f"  ✓ Available layouts: {result.data.get('available_layouts', [])}")
    return result


async def test_validation(tool):
    """Test input validation"""
    print("\n✓ Testing input validation...")
    
    # Test missing required parameter
    result = await tool.execute(action='switch_layout')
    assert not result.success, "Should fail without layout_name"
    print(f"  ✓ Validation works: {result.error}")
    
    # Test invalid percentage
    result = await tool.execute(action='set_split', split_key='mainHorizontalSplit', percentage=150)
    assert not result.success, "Should fail with invalid percentage"
    print(f"  ✓ Range validation works: {result.error}")
    
    return True


async def test_yaml_files_exist():
    """Test that YAML preset files exist"""
    print("\n✓ Testing YAML preset files...")
    
    # Get absolute path to workspace root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    workspace_root = os.path.join(project_root, 'workspace')
    layout_dir = os.path.join(workspace_root, '.icotes', 'layout')
    
    print(f"  Looking in: {layout_dir}")
    
    expected_files = ['H.yaml', 'IDE.yaml', 'mobile.yaml']
    
    for filename in expected_files:
        filepath = os.path.join(layout_dir, filename)
        assert os.path.exists(filepath), f"Missing {filename} at {filepath}"
        
        # Check file is valid YAML
        with open(filepath, 'r') as f:
            import yaml
            try:
                data = yaml.safe_load(f)
                assert 'name' in data, f"{filename} missing 'name' field"
                assert 'areas' in data, f"{filename} missing 'areas' field"
                print(f"  ✓ {filename}: name={data['name']}, deviceTarget={data.get('deviceTarget', 'desktop')}")
            except yaml.YAMLError as e:
                assert False, f"Invalid YAML in {filename}: {e}"
    
    return True


async def main():
    """Run all integration tests"""
    print("=" * 60)
    print("UI Layout System - Integration Test Suite")
    print("=" * 60)
    
    try:
        # Test 1: Tool registration
        tool = await test_tool_registration()
        
        # Test 2: YAML files exist and are valid
        await test_yaml_files_exist()
        
        # Test 3: Get layout action
        await test_get_layout_action(tool)
        
        # Test 4: Input validation
        await test_validation(tool)
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nPhases 1-4 implementation verified:")
        print("  ✓ Phase 1: YAML schema & foundation")
        print("  ✓ Phase 2: Save/Load UI (requires frontend)")
        print("  ✓ Phase 3: Agent control via UILayoutTool")
        print("  ✓ Phase 4: Mobile layout presets")
        print("\nNote: Full WebSocket integration requires running frontend")
        return 0
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TEST FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
