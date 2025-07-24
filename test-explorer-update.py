#!/usr/bin/env python3
"""
Test script to verify Explorer realtime update functionality
Creates and deletes files to trigger filesystem events
"""

import os
import time
import sys

# Get workspace root from environment or use default
workspace_root = os.environ.get('VITE_WORKSPACE_ROOT', '/home/penthoy/ilaborcode/workspace')

def test_file_operations():
    """Test file operations that should trigger Explorer updates"""
    
    print(f"Testing Explorer realtime updates in: {workspace_root}")
    print("Make sure the Explorer is open in your browser and watching this directory.")
    print()
    
    # Test 1: Create a new file
    test_file = os.path.join(workspace_root, 'test-realtime-update.txt')
    print("1. Creating test file...")
    with open(test_file, 'w') as f:
        f.write("This is a test file for Explorer realtime updates.\n")
    print(f"   Created: {test_file}")
    time.sleep(2)
    
    # Test 2: Modify the file
    print("2. Modifying test file...")
    with open(test_file, 'a') as f:
        f.write(f"Modified at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    print(f"   Modified: {test_file}")
    time.sleep(2)
    
    # Test 3: Create a directory
    test_dir = os.path.join(workspace_root, 'test-realtime-dir')
    print("3. Creating test directory...")
    os.makedirs(test_dir, exist_ok=True)
    print(f"   Created directory: {test_dir}")
    time.sleep(2)
    
    # Test 4: Create a file in the directory
    test_file_in_dir = os.path.join(test_dir, 'nested-file.txt')
    print("4. Creating file in directory...")
    with open(test_file_in_dir, 'w') as f:
        f.write("This is a nested file.\n")
    print(f"   Created: {test_file_in_dir}")
    time.sleep(2)
    
    # Test 5: Delete the file
    print("5. Deleting test file...")
    if os.path.exists(test_file):
        os.remove(test_file)
        print(f"   Deleted: {test_file}")
    time.sleep(2)
    
    # Test 6: Delete the directory
    print("6. Deleting test directory...")
    if os.path.exists(test_dir):
        os.remove(test_file_in_dir)
        os.rmdir(test_dir)
        print(f"   Deleted directory: {test_dir}")
    time.sleep(2)
    
    print()
    print("Test completed! Check your Explorer to see if it updated in real-time.")
    print("You should have seen:")
    print("- test-realtime-update.txt appear and disappear")
    print("- test-realtime-dir directory appear and disappear")

if __name__ == "__main__":
    if not os.path.exists(workspace_root):
        print(f"Error: Workspace directory does not exist: {workspace_root}")
        print("Please check your VITE_WORKSPACE_ROOT environment variable.")
        sys.exit(1)
    
    try:
        test_file_operations()
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as e:
        print(f"Error during test: {e}")
        sys.exit(1) 