#!/usr/bin/env python3
"""
Simple script to test REST API endpoints are working.
REMEMBER: Always run in venv with: source venv/bin/activate && python test_endpoints.py
"""
import sys
import os
sys.path.insert(0, os.getcwd())

def test_rest_api_endpoints():
    print("Testing REST API endpoints...")
    
    try:
        from icpy.api.rest_api import RestAPI
        print("✓ RestAPI class imported successfully")
        
        from main import app
        print("✓ Main app imported successfully")
        
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # Test status endpoint
        print("\nTesting /api/status...")
        try:
            response = client.get("/api/status")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {response.json()}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Status endpoint error: {e}")
        
        # Test files endpoint
        print("\nTesting /api/files/...")
        try:
            response = client.get("/api/files/")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Found {len(data.get('files', []))} files and {len(data.get('directories', []))} directories")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Files endpoint error: {e}")
        
        # List all API routes
        print("\nAll API routes:")
        for route in app.routes:
            if hasattr(route, 'path') and '/api' in route.path:
                methods = list(getattr(route, 'methods', set()))
                print(f"  {route.path} [{', '.join(methods)}]")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_rest_api_endpoints()
    if success:
        print("\n✓ All tests passed! REST API endpoints are working.")
    else:
        print("\n✗ Tests failed!")
        sys.exit(1)
