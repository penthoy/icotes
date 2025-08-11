#!/usr/bin/env python3
"""
Simple SaaS mode test using requests instead of TestClient.
Run with: uv run python simple-saas-test.py
"""

import os
import sys
import subprocess
import time
import requests
from jose import jwt
from datetime import datetime, timezone, timedelta

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

def start_saas_server():
    """Start the backend server in SaaS mode."""
    test_token, jwt_secret = create_test_jwt()
    
    # Set environment variables for SaaS mode
    env = os.environ.copy()
    env.update({
        'AUTH_MODE': 'saas',
        'SUPABASE_JWT_SECRET': jwt_secret,
        'UNAUTH_REDIRECT_URL': 'https://icotes.com',
        'COOKIE_NAME': 'auth_token'
    })
    
    print("🚀 Starting backend server in SaaS mode...")
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    
    # Start server in background
    proc = subprocess.Popen([
        'uv', 'run', 'python', 'main.py', '--host', '0.0.0.0', '--port', '8007'
    ], cwd=backend_dir, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    for i in range(10):
        try:
            response = requests.get('http://localhost:8007/healthz', timeout=1)
            if response.status_code == 200:
                print("✅ Server started successfully!")
                return proc, test_token
        except requests.exceptions.RequestException:
            time.sleep(1)
    
    # If we get here, server didn't start
    stdout, stderr = proc.communicate(timeout=5)
    print("❌ Server failed to start:")
    print("STDOUT:", stdout.decode())
    print("STDERR:", stderr.decode())
    proc.terminate()
    return None, None

def test_saas_endpoints(test_token):
    """Test the SaaS mode endpoints."""
    print("\n🧪 Testing SaaS Mode Endpoints")
    print("=" * 50)
    
    base_url = "http://localhost:8007"
    
    # Test 1: healthz should work without auth
    print("\n1. Testing /healthz (should work without auth):")
    try:
        response = requests.get(f"{base_url}/healthz", timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        print("   ✅ PASS")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
    
    # Test 2: Root route without auth should redirect
    print("\n2. Testing / without auth (should redirect):")
    try:
        response = requests.get(f"{base_url}/", allow_redirects=False, timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Location: {response.headers.get('location', 'None')}")
        if response.status_code == 302:
            assert response.headers.get('location') == 'https://icotes.com'
            print("   ✅ PASS - Redirected to expected URL")
        else:
            print(f"   ❌ FAIL - Expected 302 redirect, got {response.status_code}")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
    
    # Test 3: Root route with auth should serve content
    print("\n3. Testing / with valid JWT (should serve content):")
    try:
        cookies = {'auth_token': test_token}
        response = requests.get(f"{base_url}/", cookies=cookies, allow_redirects=False, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Content-Type: {response.headers.get('content-type', 'Unknown')}")
            print("   ✅ PASS - Served content with valid JWT")
        else:
            print(f"   ❌ FAIL - Expected 200, got {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
    
    # Test 4: Protected API endpoint with JWT
    print("\n4. Testing /auth/profile with valid JWT:")
    try:
        cookies = {'auth_token': test_token}
        response = requests.get(f"{base_url}/auth/profile", cookies=cookies, timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   User ID: {data['user']['id']}")
            print("   ✅ PASS")
        else:
            print(f"   ❌ FAIL - Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
    
    # Test 5: Protected API endpoint without JWT
    print("\n5. Testing /auth/profile without JWT:")
    try:
        response = requests.get(f"{base_url}/auth/profile", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ PASS - Correctly rejected unauthorized request")
        else:
            print(f"   ❌ FAIL - Expected 401, got {response.status_code}")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")

def main():
    """Main test function."""
    try:
        # Start server
        proc, test_token = start_saas_server()
        if not proc or not test_token:
            print("❌ Failed to start server")
            return 1
        
        try:
            # Run tests
            test_saas_endpoints(test_token)
            print("\n🎉 All tests completed!")
            return 0
        
        finally:
            # Clean up
            print("\n🧹 Shutting down server...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            print("✅ Server shut down")
    
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
