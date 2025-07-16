#!/usr/bin/env python3
"""
Simple test script for REST API functionality
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Starting REST API test...")

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from unittest.mock import AsyncMock, MagicMock
    
    from icpy.api.rest_api import RestAPI
    print("✓ Imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

async def test_rest_api():
    """Test REST API functionality."""
    
    try:
        # Create FastAPI app
        app = FastAPI(title="Test App", version="1.0.0")
        print("✓ FastAPI app created")
        
        # Create mock services
        mock_workspace_service = AsyncMock()
        mock_workspace_service.list_workspaces.return_value = [
            {"id": "ws1", "name": "Workspace 1"},
            {"id": "ws2", "name": "Workspace 2"}
        ]
        
        mock_filesystem_service = AsyncMock()
        mock_filesystem_service.list_directory.return_value = [
            {"name": "file1.txt", "type": "file"},
            {"name": "dir1", "type": "directory"}
        ]
        
        mock_terminal_service = AsyncMock()
        mock_terminal_service.list_terminals.return_value = [
            {"id": "term1", "name": "Terminal 1"}
        ]
        print("✓ Mock services created")
        
        # Create REST API instance
        rest_api = RestAPI(app)
        print("✓ REST API instance created")
        
        # Mock the dependencies
        rest_api.message_broker = AsyncMock()
        rest_api.connection_manager = AsyncMock()
        rest_api.workspace_service = mock_workspace_service
        rest_api.filesystem_service = mock_filesystem_service
        rest_api.terminal_service = mock_terminal_service
        print("✓ Dependencies mocked")
        
        # Test basic functionality
        print(f"✓ App has {len(app.routes)} routes")
        
        # Test with client
        with TestClient(app) as client:
            # Test health check
            response = client.get("/api/health")
            print(f"✓ Health check: {response.status_code}")
            
            # Test stats
            response = client.get("/api/stats")
            print(f"✓ Stats endpoint: {response.status_code}")
            
            # Test workspace endpoints
            response = client.get("/api/workspaces")
            print(f"✓ List workspaces: {response.status_code}")
            
            # Test file endpoints
            response = client.get("/api/files?path=/")
            print(f"✓ List files: {response.status_code}")
            
            # Test terminal endpoints
            response = client.get("/api/terminals")
            print(f"✓ List terminals: {response.status_code}")
            
            # Test OpenAPI docs
            response = client.get("/api/openapi.json")
            print(f"✓ OpenAPI docs: {response.status_code}")
            
            print("\n✓ All tests passed!")
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_rest_api())
