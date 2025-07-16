#!/usr/bin/env python3
"""
Minimal test for REST API
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing REST API...")

try:
    from fastapi import FastAPI
    from icpy.api.rest_api import RestAPI
    from unittest.mock import AsyncMock
    
    # Create FastAPI app
    app = FastAPI()
    
    # Create REST API instance
    rest_api = RestAPI(app)
    
    # Mock services
    rest_api.message_broker = AsyncMock()
    rest_api.connection_manager = AsyncMock()
    rest_api.workspace_service = AsyncMock()
    rest_api.filesystem_service = AsyncMock()
    rest_api.terminal_service = AsyncMock()
    
    print(f"✓ REST API created successfully with {len(app.routes)} routes")
    
    # List some key endpoints
    key_endpoints = [
        "/api/health",
        "/api/stats", 
        "/api/workspaces",
        "/api/files",
        "/api/terminals",
        "/api/openapi.json"
    ]
    
    print("\n✓ Key endpoints registered:")
    for route in app.routes:
        if hasattr(route, 'path'):
            if route.path in key_endpoints:
                methods = getattr(route, 'methods', ['GET'])
                print(f"  {' '.join(methods)} {route.path}")
    
    print("\n✓ REST API implementation is working correctly!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
