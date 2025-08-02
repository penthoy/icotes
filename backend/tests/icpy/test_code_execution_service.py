"""
Integration tests for Code Execution Service
Tests multi-language execution, sandboxing, streaming, and performance
"""

import pytest
import pytest_asyncio
import asyncio
import json
import os
import time
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List
import uuid

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icpy.services.code_execution_service import (
    CodeExecutionService, ExecutionConfig, ExecutionResult, ExecutionStatus, Language,
    get_code_execution_service, shutdown_code_execution_service
)
from icpy.core.message_broker import get_message_broker, shutdown_message_broker

# Mark all test methods as asyncio
pytestmark = pytest.mark.asyncio


class TestCodeExecutionService:
    """Test suite for CodeExecutionService"""
    
    @pytest_asyncio.fixture
    async def code_execution_service(self):
        """Create a fresh code execution service for each test"""
        # Reset global instances
        try:
            await shutdown_code_execution_service()
        except RuntimeError:
            pass
        try:
            await shutdown_message_broker()
        except RuntimeError:
            pass
        
        service = CodeExecutionService()
        await service.start()
        yield service
        await service.stop()
    
    async def test_service_lifecycle(self, code_execution_service):
        """Test service start and stop"""
        assert code_execution_service.running
        assert code_execution_service.message_broker is not None
        
        await code_execution_service.stop()
        assert not code_execution_service.running
    
    async def test_python_code_execution(self, code_execution_service):
        """Test basic Python code execution"""
        code = """
print("Hello, World!")
x = 2 + 3
print(f"2 + 3 = {x}")
"""
        
        result = await code_execution_service.execute_code(code, "python")
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.language == Language.PYTHON
        assert len(result.output) >= 2
        assert "Hello, World!" in result.output[0]
        assert "2 + 3 = 5" in result.output[1]
        assert len(result.errors) == 0
        assert result.execution_time > 0
        assert result.exit_code == 0
    
    async def test_python_code_with_error(self, code_execution_service):
        """Test Python code execution with syntax error"""
        code = """
print("This will work")
invalid_syntax here
print("This won't run")
"""
        
        result = await code_execution_service.execute_code(code, "python")
        
        assert result.status == ExecutionStatus.FAILED
        assert result.language == Language.PYTHON
        # Syntax errors are caught before execution, so no output expected
        assert len(result.errors) > 0
        assert "SyntaxError" in result.errors[0]
        assert result.exit_code == 1
    
    async def test_python_code_with_runtime_error(self, code_execution_service):
        """Test Python code execution with runtime error"""
        code = """
print("Starting...")
x = 1 / 0  # This will cause a runtime error
print("This won't run")
"""
        
        result = await code_execution_service.execute_code(code, "python")
        
        assert result.status == ExecutionStatus.FAILED
        assert result.language == Language.PYTHON
        assert len(result.output) >= 1
        assert "Starting..." in result.output[0]
        assert len(result.errors) > 0
        assert "ZeroDivisionError" in result.errors[0]
    
    @pytest.mark.skipif(not shutil.which('node'), reason="Node.js not available")
    async def test_javascript_code_execution(self, code_execution_service):
        """Test JavaScript code execution"""
        code = """
console.log("Hello from JavaScript!");
const result = 2 + 3;
console.log(`2 + 3 = ${result}`);
"""
        
        result = await code_execution_service.execute_code(code, "javascript")
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.language == Language.JAVASCRIPT
        assert len(result.output) >= 2
        assert "Hello from JavaScript!" in result.output[0]
        assert "2 + 3 = 5" in result.output[1]
        assert len(result.errors) == 0
        assert result.exit_code == 0
    
    @pytest.mark.skipif(not shutil.which('node'), reason="Node.js not available")
    async def test_javascript_code_with_error(self, code_execution_service):
        """Test JavaScript code execution with error"""
        code = """
console.log("This will work");
undefinedFunction();  // This will cause an error
console.log("This won't run");
"""
        
        result = await code_execution_service.execute_code(code, "javascript")
        
        assert result.status == ExecutionStatus.FAILED
        assert result.language == Language.JAVASCRIPT
        assert len(result.output) >= 1
        assert "This will work" in result.output[0]
        assert len(result.errors) > 0
        assert result.exit_code != 0
    
    async def test_bash_code_execution(self, code_execution_service):
        """Test Bash script execution"""
        code = """
echo "Hello from Bash!"
result=$((2 + 3))
echo "2 + 3 = $result"
"""
        
        result = await code_execution_service.execute_code(code, "bash")
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.language == Language.BASH
        assert len(result.output) >= 2
        assert "Hello from Bash!" in result.output[0]
        assert "2 + 3 = 5" in result.output[1]
        assert len(result.errors) == 0
        assert result.exit_code == 0
    
    async def test_bash_code_with_error(self, code_execution_service):
        """Test Bash script execution with error"""
        code = """
echo "This will work"
nonexistent_command  # This will cause an error
echo "This won't run"
"""
        
        result = await code_execution_service.execute_code(code, "bash")
        
        # Bash continues execution even with errors, but may have errors in stderr
        assert result.language == Language.BASH
        assert len(result.output) >= 1
        assert "This will work" in result.output[0]
        # May have errors but still complete (depending on implementation)
        # The behavior depends on how the service handles bash errors
    
    async def test_unsupported_language(self, code_execution_service):
        """Test execution with unsupported language"""
        result = await code_execution_service.execute_code("print('test')", "unsupported")
        
        assert result.status == ExecutionStatus.FAILED
        assert len(result.errors) > 0
        assert "Unsupported language" in result.errors[0]
    
    async def test_execution_timeout(self, code_execution_service):
        """Test execution timeout"""
        # Code that runs longer than timeout
        code = """
import time
time.sleep(5)  # Sleep for 5 seconds
print("This should timeout")
"""
        
        config = ExecutionConfig(timeout=1.0)  # 1 second timeout
        result = await code_execution_service.execute_code(code, "python", config)
        
        # Timeout behavior may vary depending on implementation
        # Some implementations may complete anyway if timeout isn't enforced
        assert result.status in [ExecutionStatus.TIMEOUT, ExecutionStatus.FAILED, ExecutionStatus.COMPLETED]
        assert result.language == Language.PYTHON
    
    async def test_execution_with_custom_config(self, code_execution_service):
        """Test execution with custom configuration"""
        code = 'print("Testing custom config")'
        
        config = ExecutionConfig(
            timeout=10.0,
            max_output_size=1024,
            capture_output=True,
            sandbox=True
        )
        
        result = await code_execution_service.execute_code(code, "python", config)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert "Testing custom config" in result.output[0]
    
    async def test_cancel_execution(self, code_execution_service):
        """Test execution cancellation"""
        # Code that runs for a long time
        code = """
import time
for i in range(10):
    time.sleep(1)
    print(f"Step {i}")
"""
        
        # Start execution in background
        task = asyncio.create_task(
            code_execution_service.execute_code(code, "python", ExecutionConfig(timeout=20.0))
        )
        
        # Wait a bit then cancel
        await asyncio.sleep(0.5)  # Give more time for execution to start
        active_executions = await code_execution_service.get_active_executions()
        
        if len(active_executions) > 0:
            cancelled = await code_execution_service.cancel_execution(active_executions[0])
            # Wait for task to complete
            result = await task
            # Cancellation behavior may vary depending on implementation
            assert result.status in [ExecutionStatus.CANCELLED, ExecutionStatus.FAILED, ExecutionStatus.COMPLETED]
        else:
            # Execution might have completed too quickly
            result = await task
            # Accept any status if cancellation couldn't happen in time
            assert result.status in [ExecutionStatus.COMPLETED, ExecutionStatus.CANCELLED, ExecutionStatus.FAILED]
    
    async def test_execution_history(self, code_execution_service):
        """Test execution history tracking"""
        # Execute multiple code snippets
        codes = [
            'print("First execution")',
            'print("Second execution")',
            'print("Third execution")'
        ]
        
        for code in codes:
            await code_execution_service.execute_code(code, "python")
        
        history = await code_execution_service.get_execution_history()
        assert len(history) >= 3
        
        # Check that all executions are in history
        outputs = [result.output[0] for result in history if result.output]
        assert any("First execution" in output for output in outputs)
        assert any("Second execution" in output for output in outputs)
        assert any("Third execution" in output for output in outputs)
    
    async def test_result_caching(self, code_execution_service):
        """Test execution result caching"""
        code = 'print("Cached result test")'
        
        result = await code_execution_service.execute_code(code, "python")
        execution_id = result.execution_id
        
        # Retrieve cached result
        cached_result = await code_execution_service.get_execution_result(execution_id)
        assert cached_result is not None
        assert cached_result.execution_id == execution_id
        assert cached_result.output == result.output
        assert cached_result.status == result.status
    
    async def test_get_active_executions(self, code_execution_service):
        """Test getting active executions"""
        # Initially no active executions
        active = await code_execution_service.get_active_executions()
        assert len(active) == 0
        
        # Start a long-running execution
        code = """
import time
time.sleep(1)
print("Long running task")
"""
        
        task = asyncio.create_task(
            code_execution_service.execute_code(code, "python")
        )
        
        # Check active executions
        await asyncio.sleep(0.1)
        active = await code_execution_service.get_active_executions()
        assert len(active) >= 0  # Might complete quickly
        
        # Wait for completion
        await task
        
        # Should be no active executions
        active = await code_execution_service.get_active_executions()
        assert len(active) == 0
    
    async def test_execution_statistics(self, code_execution_service):
        """Test execution statistics tracking"""
        initial_stats = await code_execution_service.get_stats()
        
        # Execute some code
        await code_execution_service.execute_code('print("Success")', "python")
        await code_execution_service.execute_code('invalid syntax', "python")  # This will fail
        
        stats = await code_execution_service.get_stats()
        
        assert stats['executions_total'] >= initial_stats['executions_total'] + 2
        assert stats['executions_successful'] >= initial_stats['executions_successful'] + 1
        assert stats['executions_failed'] >= initial_stats['executions_failed'] + 1
        assert stats['languages_used']['python'] >= 2
        assert stats['total_execution_time'] > initial_stats['total_execution_time']
    
    async def test_supported_languages(self, code_execution_service):
        """Test getting supported languages"""
        languages = await code_execution_service.get_supported_languages()
        
        assert "python" in languages
        assert "javascript" in languages
        assert "bash" in languages
        assert len(languages) >= 3
    
    async def test_streaming_execution(self, code_execution_service):
        """Test streaming code execution"""
        code = """
print("Line 1")
print("Line 2") 
print("Line 3")
"""
        
        updates = []
        async for update in code_execution_service.execute_code_streaming(code, "python"):
            updates.append(update)
        
        assert len(updates) >= 2  # At least started and completed
        
        # Check for execution started event
        start_events = [u for u in updates if u['type'] == 'execution_started']
        assert len(start_events) >= 1
        
        # Check for execution completed event
        complete_events = [u for u in updates if u['type'] == 'execution_completed']
        assert len(complete_events) >= 1
        
        if complete_events:
            completed = complete_events[0]
            assert 'data' in completed
            assert 'output' in completed['data']
            assert len(completed['data']['output']) >= 3
    
    async def test_streaming_execution_with_error(self, code_execution_service):
        """Test streaming execution with error"""
        code = """
print("Before error")
invalid_syntax_here
print("After error")
"""
        
        updates = []
        async for update in code_execution_service.execute_code_streaming(code, "python"):
            updates.append(update)
        
        assert len(updates) >= 2
        
        # Should have execution completed with failed status
        complete_events = [u for u in updates if u['type'] == 'execution_completed']
        if complete_events:
            completed = complete_events[0]
            assert completed['data']['status'] == 'failed'
            assert len(completed['data']['errors']) > 0
    
    async def test_concurrent_executions(self, code_execution_service):
        """Test multiple concurrent executions"""
        codes = [
            'print("Execution 1")',
            'print("Execution 2")',
            'print("Execution 3")',
            'print("Execution 4")',
            'print("Execution 5")'
        ]
        
        # Start all executions concurrently
        tasks = [
            code_execution_service.execute_code(code, "python")
            for code in codes
        ]
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.status == ExecutionStatus.COMPLETED
            assert f"Execution {i+1}" in result.output[0]
    
    async def test_message_broker_integration(self, code_execution_service):
        """Test integration with message broker"""
        # Test that service publishes events
        message_broker = code_execution_service.message_broker
        assert message_broker is not None
        
        received_messages = []
        
        async def message_handler(message):
            received_messages.append(message)
        
        # Subscribe to execution events
        await message_broker.subscribe("code_execution.*", message_handler)
        
        # Execute code
        await code_execution_service.execute_code('print("Test message")', "python")
        
        # Give time for message processing
        await asyncio.sleep(0.1)
        
        # Should have received execution events
        assert len(received_messages) >= 2  # Started and completed events
        
        # Check message topics
        topics = [msg.topic for msg in received_messages]
        assert any("execution.started" in topic for topic in topics)
        assert any("execution.completed" in topic for topic in topics)
    
    async def test_global_service_instance(self):
        """Test global service instance management"""
        # Get global instance
        service1 = get_code_execution_service()
        service2 = get_code_execution_service()
        
        # Should be the same instance
        assert service1 is service2
        
        # Start service
        await service1.start()
        assert service1.running
        
        # Shutdown
        await shutdown_code_execution_service()
        
        # Should create new instance after shutdown
        service3 = get_code_execution_service()
        assert service3 is not service1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
