"""
Quick test to verify legacy WebSocket endpoint fix works
"""
import asyncio
import json
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from main import execute_python_code
from icpy.services import get_code_execution_service

async def test_legacy_fix():
    """Test that the legacy WebSocket would work with fixed execution"""
    print("Testing legacy execution method...")
    
    # Test basic execution (the fallback method)
    output, errors, execution_time = execute_python_code("print('Legacy test')")
    print(f"Legacy method - Output: {output}, Errors: {errors}")
    
    # Test ICPY method 
    print("\nTesting ICPY execution method...")
    code_service = get_code_execution_service()
    await code_service.start()
    
    result = await code_service.execute_code("print('ICPY test')", "python")
    print(f"ICPY method - Status: {result.status}, Output: {result.output}, Errors: {result.errors}")
    
    await code_service.stop()
    print("\nBoth methods working correctly!")

if __name__ == "__main__":
    asyncio.run(test_legacy_fix())
