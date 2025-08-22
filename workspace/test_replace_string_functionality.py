#!/usr/bin/env python3
"""
Test script to validate the replace_string_in_file tool functionality
and demonstrate the enhanced widget support.
"""

import sys
import os
import asyncio

# Add the backend path to Python path
backend_path = '/home/penthoy/icotes/backend'
sys.path.insert(0, backend_path)

from icpy.agent.tools.replace_string_tool import ReplaceStringTool

async def test_replace_string_tool():
    """Test the replace_string_in_file tool"""
    print("🧪 Testing replace_string_in_file Tool")
    print("=" * 40)
    
    tool = ReplaceStringTool()
    
    # Test 1: Basic replacement
    print("\n1. Testing basic string replacement...")
    result = await tool.execute(
        filePath="/home/penthoy/icotes/workspace/test_replace_widget.txt",
        oldString="original text that should be replaced",
        newString="NEW REPLACED TEXT"
    )
    
    print(f"Success: {result.success}")
    if result.success:
        data = result.data
        print(f"Replaced count: {data.get('replacedCount', 0)}")
        print(f"File path: {data.get('filePath', 'N/A')}")
        print(f"Original content length: {len(data.get('originalContent', ''))}")
        print(f"Modified content length: {len(data.get('modifiedContent', ''))}")
        print(f"Content changed: {data.get('originalContent') != data.get('modifiedContent')}")
        
        # Show diff
        orig = data.get('originalContent', '')
        mod = data.get('modifiedContent', '')
        if orig != mod:
            print("\n📄 Changes made:")
            orig_lines = orig.split('\n')
            mod_lines = mod.split('\n')
            for i, (old_line, new_line) in enumerate(zip(orig_lines, mod_lines)):
                if old_line != new_line:
                    print(f"Line {i+1}:")
                    print(f"  - {old_line}")
                    print(f"  + {new_line}")
    else:
        print(f"Error: {result.error}")

    # Test 2: No match replacement
    print("\n2. Testing no-match scenario...")
    result = await tool.execute(
        filePath="/home/penthoy/icotes/workspace/test_replace_widget.txt",
        oldString="non-existent text",
        newString="this won't be replaced"
    )
    
    print(f"Success: {result.success}")
    if result.success:
        data = result.data
        print(f"Replaced count: {data.get('replacedCount', 0)}")
        print(f"Content unchanged: {data.get('originalContent') == data.get('modifiedContent')}")
    else:
        print(f"Error: {result.error}")

if __name__ == "__main__":
    asyncio.run(test_replace_string_tool())
