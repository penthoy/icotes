#!/usr/bin/env python3
"""
Test script to reproduce the 500 error on PUT /api/files endpoint
and validate the fix.
"""

import requests
import json
import sys

def test_put_files_endpoint():
    """Test the PUT /api/files endpoint"""
    
    # Test data
    test_data = {
        "path": "/tmp/test_file_api.txt", 
        "content": "Hello, this is test content from API fix!",
        "create_dirs": True
    }
    
    url = "http://localhost:8001/api/files"
    
    print(f"Testing PUT request to: {url}")
    print(f"Payload: {json.dumps(test_data, indent=2)}")
    
    try:
        response = requests.put(url, json=test_data, timeout=10)
        
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
            
        # Check if file was created
        import os
        if os.path.exists(test_data["path"]):
            with open(test_data["path"], 'r') as f:
                file_content = f.read()
            print(f"\nFile created successfully!")
            print(f"File content: {file_content}")
            return True
        else:
            print("\nFile was not created")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False

if __name__ == "__main__":
    success = test_put_files_endpoint()
    sys.exit(0 if success else 1)
