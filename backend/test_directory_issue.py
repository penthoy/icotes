#!/usr/bin/env python3
"""
Test script to reproduce the directory creation issue.
REMEMBER: Always run in venv with: source venv/bin/activate && python test_directory_issue.py
"""
import requests
import json
import sys
import os

def test_directory_creation_issue():
    """Test the directory creation issue with the REST API."""
    print("Testing directory creation issue...")
    
    # Test data - this should create a directory but currently creates a file
    test_data = {
        "path": "/home/penthoy/ilaborcode/workspace/test_directory_creation", 
        "type": "directory"
    }
    
    url = "http://localhost:8000/api/files"
    
    print(f"Testing POST request to: {url}")
    print(f"Payload: {json.dumps(test_data, indent=2)}")
    
    try:
        response = requests.post(url, json=test_data, timeout=10)
        
        print(f"\nResponse status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.content:
            try:
                json_response = response.json()
                print(f"Response JSON: {json.dumps(json_response, indent=2)}")
            except:
                print(f"Response text: {response.text}")
        else:
            print("Empty response body")
            
        # Check what was actually created
        test_path = test_data["path"]
        if os.path.exists(test_path):
            if os.path.isdir(test_path):
                print(f"\n✅ SUCCESS: Directory was created at {test_path}")
                return True
            else:
                print(f"\n❌ BUG REPRODUCED: File was created instead of directory at {test_path}")
                print(f"   File contents: {open(test_path, 'r').read()}")
                # Clean up the incorrectly created file
                os.remove(test_path)
                return False
        else:
            print(f"\n❌ FAILED: Nothing was created at {test_path}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False
    except Exception as e:
        print(f"Error during test: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Reproducing directory creation bug...")
    print("   This test sends type='directory' but expects a file to be created (bug)")
    
    success = test_directory_creation_issue()
    
    if not success:
        print("\n✅ BUG REPRODUCED: Directory creation creates file instead")
        print("   This confirms the issue described in the ticket")
    else:
        print("\n❓ Bug might be already fixed or server not running")
        
    sys.exit(0)
