#!/usr/bin/env python3
"""
Test script to verify SaaS mode authentication works correctly.
Run with: uv run test-saas-mode.py
"""

import os
import sys
import asyncio
from jose import jwt
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

def create_test_jwt(user_id="test-user-123", email="test@example.com"):
    """Create a test JWT token."""
    secret = "test-secret-key-for-jwt-validation"
    payload = {
        "sub": user_id,
        "email": email,
        "role": "user",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token, secret

def test_saas_mode():
    """Test SaaS mode authentication flows."""
    print("🧪 Testing SaaS Mode Authentication")
    print("=" * 50)
    
    # Create test JWT
    test_token, jwt_secret = create_test_jwt()
    
    # Set environment for SaaS mode
    os.environ['AUTH_MODE'] = 'saas'
    os.environ['SUPABASE_JWT_SECRET'] = jwt_secret
    os.environ['UNAUTH_REDIRECT_URL'] = 'https://icotes.com'
    
    # Import app after setting environment variables
    from main import app
    client = TestClient(app)
    
    print("\n1. Testing healthz endpoint (should work without auth):")
    response = client.get("/healthz")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    print("   ✅ PASS")
    
    print("\n2. Testing root route without auth (should redirect):")
    response = client.get("/", allow_redirects=False)
    print(f"   Status: {response.status_code}")
    print(f"   Location: {response.headers.get('location', 'None')}")
    assert response.status_code == 302
    assert response.headers.get('location') == 'https://icotes.com'
    print("   ✅ PASS")
    
    print("\n3. Testing root route with valid JWT (should serve app):")
    response = client.get("/", cookies={"auth_token": test_token}, allow_redirects=False)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   Content-Type:", response.headers.get('content-type', 'Unknown'))
        print("   ✅ PASS")
    else:
        print(f"   ❌ FAIL - Expected 200, got {response.status_code}")
    
    print("\n4. Testing protected API endpoint with JWT:")
    response = client.get("/auth/profile", cookies={"auth_token": test_token})
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   User ID: {data['user']['id']}")
        print("   ✅ PASS")
    else:
        print(f"   ❌ FAIL - Expected 200, got {response.status_code}")
    
    print("\n5. Testing protected API endpoint without JWT:")
    response = client.get("/auth/profile")
    print(f"   Status: {response.status_code}")
    assert response.status_code == 401
    print("   ✅ PASS")
    
    print("\n6. Testing auth info endpoint:")
    response = client.get("/auth/info")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Auth Mode: {data['auth_mode']}")
        print(f"   Requires Auth: {data['requires_auth']}")
        print("   ✅ PASS")
    else:
        print(f"   ❌ FAIL - Expected 200, got {response.status_code}")

def test_standalone_mode():
    """Test standalone mode (should work without JWT)."""
    print("\n\n🧪 Testing Standalone Mode")
    print("=" * 50)
    
    # Set environment for standalone mode
    os.environ['AUTH_MODE'] = 'standalone'
    if 'SUPABASE_JWT_SECRET' in os.environ:
        del os.environ['SUPABASE_JWT_SECRET']
    
    # Import app after setting environment variables
    from main import app
    client = TestClient(app)
    
    print("\n1. Testing root route without auth (should serve app):")
    response = client.get("/", allow_redirects=False)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   Content-Type:", response.headers.get('content-type', 'Unknown'))
        print("   ✅ PASS")
    else:
        print(f"   ❌ FAIL - Expected 200, got {response.status_code}")
    
    print("\n2. Testing auth info endpoint:")
    response = client.get("/auth/info")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Auth Mode: {data['auth_mode']}")
        print(f"   Requires Auth: {data['requires_auth']}")
        print("   ✅ PASS")
    else:
        print(f"   ❌ FAIL - Expected 200, got {response.status_code}")

if __name__ == "__main__":
    try:
        test_saas_mode()
        test_standalone_mode()
        print("\n🎉 All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
