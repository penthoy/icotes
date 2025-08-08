#!/usr/bin/env python3
"""
Simple JWT token test for SaaS mode authentication.
"""

import os
import jwt
from datetime import datetime, timezone, timedelta

# Test JWT creation and validation
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
    return token

def test_saas_endpoints():
    """Test SaaS mode endpoints with JWT token."""
    import requests
    
    # Create test token
    test_token = create_test_jwt()
    print(f"Created test JWT: {test_token[:50]}...")
    
    # Test without token (should fail in SaaS mode)
    print("\n1. Testing without auth token:")
    response = requests.get("http://localhost:8007/auth/profile")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Test with token in cookie
    print("\n2. Testing with auth token in cookie:")
    cookies = {"auth_token": test_token}
    response = requests.get("http://localhost:8007/auth/profile", cookies=cookies)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Test auth info endpoint
    print("\n3. Testing auth info endpoint:")
    response = requests.get("http://localhost:8007/auth/info", cookies=cookies)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    print("JWT SaaS Mode Test")
    print("==================")
    test_saas_endpoints()
