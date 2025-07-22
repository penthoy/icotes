#!/usr/bin/env python3
"""
Test script to verify directory creation via REST API endpoint works correctly.
"""
import asyncio
import os
import requests
import tempfile
import shutil
from pathlib import Path

async def test_directory_endpoint():
    """Test directory creation via REST API using the actual server."""
    base_url = "http://localhost:8000"
    
    # Create a temporary test directory
    test_root = Path(tempfile.mkdtemp(prefix="icpy_directory_test_"))
    print(f"Test directory: {test_root}")
    
    try:
        # Test 1: Create a simple directory
        print("\n1. Testing simple directory creation...")
        test_path = test_root / "new_directory"
        response = requests.post(f"{base_url}/api/files", json={
            "path": str(test_path),
            "type": "directory"
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Response: {data}")
            if test_path.exists() and test_path.is_dir():
                print("✓ Directory created successfully")
            else:
                print("✗ Directory not found on filesystem")
        else:
            print(f"✗ HTTP {response.status_code}: {response.text}")
        
        # Test 2: Create nested directories
        print("\n2. Testing nested directory creation...")
        nested_path = test_root / "level1" / "level2" / "level3"
        response = requests.post(f"{base_url}/api/files", json={
            "path": str(nested_path),
            "type": "directory"
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Response: {data}")
            if nested_path.exists() and nested_path.is_dir():
                print("✓ Nested directory created successfully")
            else:
                print("✗ Nested directory not found on filesystem")
        else:
            print(f"✗ HTTP {response.status_code}: {response.text}")
        
        # Test 3: Verify file creation still works (type defaults to file)
        print("\n3. Testing file creation (default behavior)...")
        file_path = test_root / "test_file.txt"
        response = requests.post(f"{base_url}/api/files", json={
            "path": str(file_path),
            "content": "This is a test file"
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Response: {data}")
            if file_path.exists() and file_path.is_file():
                print("✓ File created successfully")
                print(f"✓ File content: {file_path.read_text()}")
            else:
                print("✗ File not found on filesystem")
        else:
            print(f"✗ HTTP {response.status_code}: {response.text}")
            
        print("\n✓ All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to server. Make sure the backend is running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"✗ Error during testing: {e}")
        return False
    finally:
        # Clean up
        shutil.rmtree(test_root)
        print(f"Cleaned up test directory: {test_root}")
        
    return True

if __name__ == "__main__":
    print("Directory Creation Endpoint Test")
    print("=" * 40)
    print("This test requires the backend server to be running.")
    print("Start the server with: python main.py")
    print("=" * 40)
    
    asyncio.run(test_directory_endpoint())
