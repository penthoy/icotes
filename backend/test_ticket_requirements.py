#!/usr/bin/env python3
"""
Test script to verify directory creation functionality meets ticket requirements.
REMEMBER: Always run in venv with: source venv/bin/activate && python test_ticket_requirements.py
"""
import requests
import json
import sys
import os
import shutil

def test_ticket_requirements():
    """Test all requirements from the ticket."""
    print("🎯 Testing Ticket Requirements - Directory Creation via REST API")
    print("=" * 70)
    
    # Clean up any existing test files
    test_paths = [
        "/home/penthoy/ilaborcode/workspace/frontend_test_directory",
        "/home/penthoy/ilaborcode/workspace/frontend_test_file.txt"
    ]
    
    for path in test_paths:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Directory creation with type: "directory"
    print("\n📁 Test 1: POST /api/files with type: 'directory' should create directory")
    total_tests += 1
    
    try:
        response = requests.post("http://localhost:8000/api/files", json={
            "path": "/home/penthoy/ilaborcode/workspace/frontend_test_directory",
            "type": "directory"
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "Directory created successfully" in data.get("message", ""):
                if os.path.isdir("/home/penthoy/ilaborcode/workspace/frontend_test_directory"):
                    print("   ✅ PASS - Directory created successfully")
                    tests_passed += 1
                else:
                    print("   ❌ FAIL - Response OK but directory not found")
            else:
                print(f"   ❌ FAIL - Wrong message: {data.get('message')}")
        else:
            print(f"   ❌ FAIL - HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ FAIL - Error: {e}")
    
    # Test 2: File creation with type: "file" 
    print("\n📄 Test 2: POST /api/files with type: 'file' should create file")
    total_tests += 1
    
    try:
        response = requests.post("http://localhost:8000/api/files", json={
            "path": "/home/penthoy/ilaborcode/workspace/frontend_test_file.txt",
            "type": "file",
            "content": "Test content"
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "File created successfully" in data.get("message", ""):
                if os.path.isfile("/home/penthoy/ilaborcode/workspace/frontend_test_file.txt"):
                    with open("/home/penthoy/ilaborcode/workspace/frontend_test_file.txt", 'r') as f:
                        content = f.read()
                    if content == "Test content":
                        print("   ✅ PASS - File created with correct content")
                        tests_passed += 1
                    else:
                        print("   ❌ FAIL - File content incorrect")
                else:
                    print("   ❌ FAIL - Response OK but file not found")
            else:
                print(f"   ❌ FAIL - Wrong message: {data.get('message')}")
        else:
            print(f"   ❌ FAIL - HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ FAIL - Error: {e}")
    
    # Test 3: Default behavior (no type specified)
    print("\n📄 Test 3: POST /api/files with no type should create file (backward compatibility)")
    total_tests += 1
    
    try:
        response = requests.post("http://localhost:8000/api/files", json={
            "path": "/home/penthoy/ilaborcode/workspace/frontend_test_default.txt",
            "content": "Default behavior test"
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "File created successfully" in data.get("message", ""):
                if os.path.isfile("/home/penthoy/ilaborcode/workspace/frontend_test_default.txt"):
                    print("   ✅ PASS - Default behavior creates file")
                    tests_passed += 1
                    os.remove("/home/penthoy/ilaborcode/workspace/frontend_test_default.txt")  # cleanup
                else:
                    print("   ❌ FAIL - Response OK but file not found")
            else:
                print(f"   ❌ FAIL - Wrong message: {data.get('message')}")
        else:
            print(f"   ❌ FAIL - HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ FAIL - Error: {e}")
    
    # Test 4: Nested directory creation
    print("\n📁 Test 4: Nested directory creation with parents that don't exist")
    total_tests += 1
    
    try:
        response = requests.post("http://localhost:8000/api/files", json={
            "path": "/home/penthoy/ilaborcode/workspace/parent/child/grandchild",
            "type": "directory",
            "create_dirs": True
        }, timeout=10)
        
        if response.status_code == 200:
            if os.path.isdir("/home/penthoy/ilaborcode/workspace/parent/child/grandchild"):
                print("   ✅ PASS - Nested directory created with parents")
                tests_passed += 1
                shutil.rmtree("/home/penthoy/ilaborcode/workspace/parent")  # cleanup
            else:
                print("   ❌ FAIL - Nested directory not created")
        else:
            print(f"   ❌ FAIL - HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ FAIL - Error: {e}")
    
    # Test 5: Error handling - directory where file exists
    print("\n⚠️  Test 5: Error handling - creating directory where file exists")
    total_tests += 1
    
    try:
        # First create a file
        test_path = "/home/penthoy/ilaborcode/workspace/conflict_test"
        with open(test_path, 'w') as f:
            f.write("existing file")
        
        # Try to create directory with same name
        response = requests.post("http://localhost:8000/api/files", json={
            "path": test_path,
            "type": "directory"
        }, timeout=10)
        
        # Should fail or handle gracefully
        if response.status_code == 500:
            print("   ✅ PASS - Correctly returned error for conflicting path")
            tests_passed += 1
        elif response.status_code == 200:
            # If it succeeds, the file should still be a file, not converted to directory
            if os.path.isfile(test_path):
                print("   ✅ PASS - Handled conflict gracefully, file unchanged")
                tests_passed += 1
            else:
                print("   ❌ FAIL - File was overwritten or changed")
        else:
            print(f"   ❌ FAIL - Unexpected status: {response.status_code}")
        
        # Clean up
        if os.path.exists(test_path):
            if os.path.isdir(test_path):
                shutil.rmtree(test_path)
            else:
                os.remove(test_path)
                
    except Exception as e:
        print(f"   ❌ FAIL - Error: {e}")
    
    # Final cleanup
    for path in test_paths:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
    
    # Results
    print("\n" + "=" * 70)
    print("📊 TICKET ACCEPTANCE CRITERIA RESULTS:")
    print(f"   Tests Passed: {tests_passed}/{total_tests}")
    
    criteria = [
        "✅ Directory creation works via REST API when type: 'directory' is specified",
        "✅ File creation continues to work as before", 
        "✅ Appropriate success/error messages returned",
        "✅ No regression in existing file operations",
        "✅ Manual testing scenarios covered"
    ]
    
    if tests_passed == total_tests:
        print("\n🎉 ALL ACCEPTANCE CRITERIA MET!")
        for criterion in criteria:
            print(f"   {criterion}")
        print("\n✅ TICKET CAN BE CLOSED - Directory creation via REST API is working correctly!")
        return True
    else:
        print(f"\n❌ {total_tests - tests_passed} tests failed. Ticket requirements not fully met.")
        return False

if __name__ == "__main__":
    success = test_ticket_requirements()
    sys.exit(0 if success else 1)
