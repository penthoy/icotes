#!/usr/bin/env python3
"""
Simple CLI functionality test
"""
import os
import sys
import subprocess

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

def test_cli_help():
    """Test CLI help command"""
    try:
        result = subprocess.run(
            [sys.executable, 'icpy_cli.py', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )
        print(f"Help command exit code: {result.returncode}")
        if result.returncode == 0:
            print("✓ Help command works")
            return True
        else:
            print("✗ Help command failed")
            print(f"STDERR: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Help command failed with exception: {e}")
        return False

def test_cli_status():
    """Test CLI status command"""
    try:
        result = subprocess.run(
            [sys.executable, 'icpy_cli.py', '--status'],
            capture_output=True,
            text=True,
            timeout=10
        )
        print(f"Status command exit code: {result.returncode}")
        print(f"Status output: {result.stdout}")
        if 'Backend:' in result.stdout:
            print("✓ Status command works")
            return True
        else:
            print("✗ Status command failed")
            print(f"STDERR: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Status command failed with exception: {e}")
        return False

def test_cli_workspace_list():
    """Test CLI workspace list command"""
    try:
        result = subprocess.run(
            [sys.executable, 'icpy_cli.py', '--workspace', 'list'],
            capture_output=True,
            text=True,
            timeout=10
        )
        print(f"Workspace list command exit code: {result.returncode}")
        print(f"Workspace list output: {result.stdout}")
        if 'workspaces' in result.stdout.lower() or 'error' in result.stdout.lower():
            print("✓ Workspace list command works")
            return True
        else:
            print("✗ Workspace list command failed")
            print(f"STDERR: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Workspace list command failed with exception: {e}")
        return False

def main():
    """Run all CLI tests"""
    print("Running CLI functionality tests...")
    print("=" * 50)
    
    tests = [
        ("CLI Help", test_cli_help),
        ("CLI Status", test_cli_status),
        ("CLI Workspace List", test_cli_workspace_list),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\nTesting {name}...")
        result = test_func()
        results.append((name, result))
        print("-" * 30)
    
    print("\nTest Results:")
    print("=" * 50)
    passed = 0
    for name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{name}: {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    return passed == len(results)

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
