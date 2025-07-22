#!/usr/bin/env python3
"""
Comprehensive test for directory and file creation via REST API.
REMEMBER: Always run in venv with: source venv/bin/activate && python test_comprehensive.py
"""
import requests
import json
import sys
import os
import shutil

def cleanup_test_files():
    """Clean up any test files/directories from previous runs."""
    test_paths = [
        "/home/penthoy/ilaborcode/workspace/test_file.txt",
        "/home/penthoy/ilaborcode/workspace/test_directory",
        "/home/penthoy/ilaborcode/workspace/nested/deep/test_directory",
        "/home/penthoy/ilaborcode/workspace/nested"
    ]
    
    for path in test_paths:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

def test_file_creation():
    """Test file creation (should work as before)."""
    print("🔍 Test 1: File creation")
    
    test_data = {
        "path": "/home/penthoy/ilaborcode/workspace/test_file.txt",
        "content": "Hello World!",
        "type": "file"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/files", json=test_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Response: {data['message']}")
            
            # Verify file exists and has correct content
            if os.path.exists(test_data["path"]) and os.path.isfile(test_data["path"]):
                with open(test_data["path"], 'r') as f:
                    content = f.read()
                if content == test_data["content"]:
                    print(f"  ✅ File created with correct content")
                    return True
                else:
                    print(f"  ❌ File content mismatch: '{content}' != '{test_data['content']}'")
            else:
                print(f"  ❌ File was not created")
        else:
            print(f"  ❌ Request failed: {response.status_code}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    return False

def test_file_creation_default_type():
    """Test file creation with default type (no type specified)."""
    print("\n🔍 Test 2: File creation (default type)")
    
    test_data = {
        "path": "/home/penthoy/ilaborcode/workspace/test_file_default.txt",
        "content": "Default type test!"
        # Note: no "type" field - should default to file
    }
    
    try:
        response = requests.post("http://localhost:8000/api/files", json=test_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Response: {data['message']}")
            
            # Verify file exists
            if os.path.exists(test_data["path"]) and os.path.isfile(test_data["path"]):
                print(f"  ✅ File created successfully (default behavior)")
                return True
            else:
                print(f"  ❌ File was not created")
        else:
            print(f"  ❌ Request failed: {response.status_code}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    return False

def test_directory_creation():
    """Test directory creation."""
    print("\n🔍 Test 3: Directory creation")
    
    test_data = {
        "path": "/home/penthoy/ilaborcode/workspace/test_directory",
        "type": "directory"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/files", json=test_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Response: {data['message']}")
            
            # Verify directory exists
            if os.path.exists(test_data["path"]) and os.path.isdir(test_data["path"]):
                print(f"  ✅ Directory created successfully")
                return True
            else:
                print(f"  ❌ Directory was not created or is not a directory")
        else:
            print(f"  ❌ Request failed: {response.status_code}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    return False

def test_nested_directory_creation():
    """Test nested directory creation."""
    print("\n🔍 Test 4: Nested directory creation")
    
    test_data = {
        "path": "/home/penthoy/ilaborcode/workspace/nested/deep/test_directory",
        "type": "directory",
        "create_dirs": True
    }
    
    try:
        response = requests.post("http://localhost:8000/api/files", json=test_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Response: {data['message']}")
            
            # Verify directory exists
            if os.path.exists(test_data["path"]) and os.path.isdir(test_data["path"]):
                print(f"  ✅ Nested directory created successfully")
                return True
            else:
                print(f"  ❌ Nested directory was not created")
        else:
            print(f"  ❌ Request failed: {response.status_code}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    return False

def test_existing_directory():
    """Test creating directory that already exists."""
    print("\n🔍 Test 5: Creating existing directory")
    
    test_data = {
        "path": "/home/penthoy/ilaborcode/workspace/test_directory",  # Already exists from test 3
        "type": "directory"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/files", json=test_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Response: {data['message']}")
            print(f"  ✅ Handled existing directory correctly")
            return True
        else:
            print(f"  ❌ Request failed: {response.status_code}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    return False

def main():
    """Run all tests."""
    print("🧪 Running comprehensive REST API tests for file/directory creation")
    print("=" * 60)
    
    cleanup_test_files()
    
    tests = [
        test_file_creation,
        test_file_creation_default_type,
        test_directory_creation,
        test_nested_directory_creation,
        test_existing_directory
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results), 1):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  Test {i} ({test.__name__}): {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ ALL TESTS PASSED! Directory creation fix is working correctly.")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    cleanup_test_files()
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
