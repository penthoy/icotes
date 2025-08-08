#!/usr/bin/env python3
"""
Create a test JWT token for testing SaaS mode authentication.
"""

import os
import json
from datetime import datetime, timezone, timedelta
from jose import jwt

# Test configuration
JWT_SECRET = "test-secret-key-for-development"
JWT_ALGORITHM = "HS256"

def create_test_jwt():
    """Create a test JWT token with user information."""
    # JWT payload
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)  # Token expires in 1 hour
    
    payload = {
        'sub': 'test-user-123',  # User ID
        'email': 'test@example.com',
        'role': 'user',
        'iat': int(now.timestamp()),
        'exp': int(exp.timestamp()),
        'iss': 'icotes-test',
        'aud': 'icotes-app'
    }
    
    # Encode JWT
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return token, payload

def decode_test_jwt(token):
    """Decode and validate a test JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception as e:
        print(f"Error decoding JWT: {e}")
        return None

if __name__ == "__main__":
    # Create test token
    token, payload = create_test_jwt()
    
    print("=== Test JWT Token ===")
    print(f"Token: {token}")
    print("\n=== Payload ===")
    print(json.dumps(payload, indent=2))
    
    # Verify token can be decoded
    print("\n=== Verification ===")
    decoded = decode_test_jwt(token)
    if decoded:
        print("✅ Token is valid")
        print(json.dumps(decoded, indent=2))
    else:
        print("❌ Token validation failed")
    
    # Show curl command for testing
    print(f"\n=== Test Commands ===")
    print(f"export TEST_JWT='{token}'")
    print(f"export JWT_SECRET='{JWT_SECRET}'")
    print("\n# Test SaaS mode with JWT cookie:")
    print(f"curl -s -H 'Cookie: auth_token={token}' http://localhost:8007/auth/profile | jq .")
    print("\n# Start SaaS container with test JWT secret:")
    print(f"sudo docker run -d --name icotes-saas-jwt-test -p 8008:8000 \\")
    print(f"  -e AUTH_MODE=saas -e SUPABASE_JWT_SECRET='{JWT_SECRET}' \\")
    print(f"  icotes:saas-test")
