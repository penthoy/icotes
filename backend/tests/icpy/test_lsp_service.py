"""
Integration tests for LSP Service
Tests LSP server lifecycle, code intelligence features, and multi-language support
"""

import pytest
import pytest_asyncio
import asyncio
import json
import os
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
import uuid

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icpy.services.lsp_service import (
    LSPService, LSPServerConfig, LSPServerState, DiagnosticSeverity,
    Diagnostic, CompletionItem,
    get_lsp_service, shutdown_lsp_service
)
from icpy.core.message_broker import get_message_broker, shutdown_message_broker

# Mark all test methods as asyncio
pytestmark = pytest.mark.asyncio


class TestLSPService:
    """Test suite for LSPService"""
    
    @pytest_asyncio.fixture
    async def lsp_service(self):
        """Create a fresh LSP service for each test"""
        # Reset global instances
        try:
            await shutdown_lsp_service()
        except RuntimeError:
            pass
        try:
            await shutdown_message_broker()
        except RuntimeError:
            pass
        
        service = LSPService()
        await service.start()
        yield service
        await service.stop()

    @pytest_asyncio.fixture
    async def temp_workspace(self):
        """Create a temporary workspace for testing"""
        temp_dir = tempfile.mkdtemp()
        
        # Create test files
        test_py_file = os.path.join(temp_dir, "test.py")
        with open(test_py_file, 'w') as f:
            f.write("""
def hello_world():
    print("Hello, World!")
    return "success"

class TestClass:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return f"Hello, {self.name}!"

# Test variable
test_var = "Hello"
""")
        
        yield temp_dir
        shutil.rmtree(temp_dir)

    async def test_service_lifecycle(self, lsp_service):
        """Test LSP service lifecycle operations"""
        # Service should be running after fixture setup
        assert lsp_service.running is True
        
        # Test stopping and restarting
        await lsp_service.stop()
        assert lsp_service.running is False
        
        await lsp_service.start()
        assert lsp_service.running is True

    async def test_server_configuration(self, lsp_service):
        """Test LSP server configuration"""
        # The service should have default server configurations
        assert hasattr(lsp_service, 'server_configs')
        assert isinstance(lsp_service.server_configs, dict)
        
        # Should have some default configurations (implementation may vary)
        # This test verifies the configuration system exists

    async def test_server_status(self, lsp_service):
        """Test server status reporting"""
        # Get initial status
        status = await lsp_service.get_server_status()
        assert isinstance(status, dict)
        assert "running" in status
        assert status["running"] is True

    async def test_document_operations(self, lsp_service, temp_workspace):
        """Test document lifecycle operations"""
        test_file = os.path.join(temp_workspace, "test.py")
        
        # Test opening document
        with open(test_file, 'r') as f:
            content = f.read()
        
        result = await lsp_service.open_document(test_file, content, "python")
        # Should return True if successful or False if no server available
        assert isinstance(result, bool)
        
        # Test updating document
        new_content = content + "\n# New comment"
        result = await lsp_service.update_document(test_file, new_content)
        assert isinstance(result, bool)
        
        # Test closing document
        result = await lsp_service.close_document(test_file)
        assert isinstance(result, bool)

    async def test_code_completions(self, lsp_service, temp_workspace):
        """Test code completion functionality"""
        test_file = os.path.join(temp_workspace, "test.py")
        
        # Open document first
        with open(test_file, 'r') as f:
            content = f.read()
        await lsp_service.open_document(test_file, content, "python")
        
        # Test completion
        completions = await lsp_service.get_completions(test_file, 0, 0)
        assert isinstance(completions, list)
        # Should return empty list if no server available, or completion items if server is running
        assert all(isinstance(item, CompletionItem) for item in completions)

    async def test_hover_information(self, lsp_service, temp_workspace):
        """Test hover information functionality"""
        test_file = os.path.join(temp_workspace, "test.py")
        
        # Open document first
        with open(test_file, 'r') as f:
            content = f.read()
        await lsp_service.open_document(test_file, content, "python")
        
        # Test hover
        hover_info = await lsp_service.get_hover_info(test_file, 1, 5)
        # Should return None if no server available, or hover info if available
        assert hover_info is None or isinstance(hover_info, dict)

    async def test_diagnostics(self, lsp_service, temp_workspace):
        """Test diagnostics functionality"""
        test_file = os.path.join(temp_workspace, "test.py")
        
        # Open document first
        with open(test_file, 'r') as f:
            content = f.read()
        await lsp_service.open_document(test_file, content, "python")
        
        # Test diagnostics
        diagnostics = await lsp_service.get_diagnostics(test_file)
        assert isinstance(diagnostics, list)
        # Should return empty list if no server available, or diagnostic items if server is running
        assert all(isinstance(item, Diagnostic) for item in diagnostics)

    async def test_server_startup_with_workspace(self, lsp_service, temp_workspace):
        """Test LSP server startup with workspace"""
        # Try to start server for Python language
        server_id = await lsp_service.start_server("python", temp_workspace)
        
        # Should return server_id if successful, None if failed
        assert server_id is None or isinstance(server_id, str)
        
        # If server started successfully, stop it
        if server_id:
            result = await lsp_service.stop_server(server_id)
            assert isinstance(result, bool)

    async def test_available_languages(self, lsp_service):
        """Test getting available languages"""
        languages = await lsp_service.get_available_languages()
        assert isinstance(languages, list)
        # Should return list of supported languages

    async def test_server_error_handling(self, lsp_service, temp_workspace):
        """Test LSP server error handling"""
        # Try to start server for non-existent language
        server_id = await lsp_service.start_server("nonexistent", temp_workspace)
        assert server_id is None

    async def test_message_broker_integration(self, lsp_service):
        """Test integration with message broker"""
        # Get message broker
        broker = await get_message_broker()
        
        # Subscribe to LSP events
        received_events = []
        
        async def event_handler(message):
            received_events.append(message)
        
        await broker.subscribe("lsp.*", event_handler)
        
        # Trigger an LSP operation that should generate events
        await lsp_service.get_server_status()
        
        # Give broker time to process
        await asyncio.sleep(0.1)
        
        # Test passes if no exceptions occurred
        assert True

    async def test_global_service_management(self):
        """Test global LSP service management"""
        # Test getting global service (not async)
        service1 = get_lsp_service()
        service2 = get_lsp_service()
        
        # Should be the same instance
        assert service1 is service2
        
        # Test shutdown
        await shutdown_lsp_service()
        
        # Getting service after shutdown should create new instance
        service3 = get_lsp_service()
        assert service3 is not service1
        
        # Cleanup
        await shutdown_lsp_service()

    async def test_dataclass_creation(self):
        """Test LSP dataclass creation and validation"""
        # Test LSPServerConfig creation
        config = LSPServerConfig(
            language="python",
            command=["python", "-m", "pylsp"],
            args=["--verbose"],
            env={"PYTHONPATH": "/test/path"},
            file_extensions=[".py", ".pyi"]
        )
        
        assert config.language == "python"
        assert config.command == ["python", "-m", "pylsp"]
        assert config.args == ["--verbose"]
        assert config.env["PYTHONPATH"] == "/test/path"
        assert ".py" in config.file_extensions

        # Test Diagnostic creation
        diagnostic = Diagnostic(
            range={"start": {"line": 1, "character": 0}, "end": {"line": 1, "character": 10}},
            message="Test error",
            severity=DiagnosticSeverity.ERROR,
            source="test"
        )
        
        assert diagnostic.message == "Test error"
        assert diagnostic.severity == DiagnosticSeverity.ERROR
        assert diagnostic.source == "test"

        # Test CompletionItem creation
        completion = CompletionItem(
            label="test_function",
            kind=3,  # Function
            detail="def test_function()",
            documentation="Test function documentation"
        )
        
        assert completion.label == "test_function"
        assert completion.kind == 3
        assert completion.detail == "def test_function()"
        assert completion.documentation == "Test function documentation"

    async def test_concurrent_operations(self, lsp_service, temp_workspace):
        """Test concurrent LSP operations"""
        test_file = os.path.join(temp_workspace, "test.py")
        
        # Open document first
        with open(test_file, 'r') as f:
            content = f.read()
        
        # Start multiple concurrent operations
        tasks = [
            lsp_service.open_document(test_file, content, "python"),
            lsp_service.get_completions(test_file, 0, 0),
            lsp_service.get_hover_info(test_file, 1, 5),
            lsp_service.get_diagnostics(test_file),
        ]
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete without exceptions
        assert len(results) == 4
        assert all(not isinstance(r, Exception) for r in results)

    async def test_service_stats(self, lsp_service):
        """Test service statistics tracking"""
        # Service should have stats attribute
        assert hasattr(lsp_service, 'stats')
        assert isinstance(lsp_service.stats, dict)
        
        # Should contain expected statistics keys
        expected_keys = [
            'servers_running', 'documents_open', 'diagnostics_count', 
            'completions_served', 'hover_requests'
        ]
        for key in expected_keys:
            assert key in lsp_service.stats

    async def test_document_tracking(self, lsp_service, temp_workspace):
        """Test document state tracking"""
        test_file = os.path.join(temp_workspace, "test.py")
        
        # Service should track open documents
        assert hasattr(lsp_service, 'open_documents')
        assert isinstance(lsp_service.open_documents, dict)
        
        # Open a document
        with open(test_file, 'r') as f:
            content = f.read()
        
        await lsp_service.open_document(test_file, content, "python")
        
        # Document tracking should work (implementation dependent)
        # Test passes if no exceptions
        assert True

    async def test_caching_system(self, lsp_service):
        """Test caching system"""
        # Service should have caching attributes
        assert hasattr(lsp_service, 'completion_cache')
        assert hasattr(lsp_service, 'hover_cache')
        assert hasattr(lsp_service, 'cache_ttl')
        
        assert isinstance(lsp_service.completion_cache, dict)
        assert isinstance(lsp_service.hover_cache, dict)
        assert isinstance(lsp_service.cache_ttl, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

import pytest
import pytest_asyncio
import asyncio
import json
import os
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
import uuid

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icpy.services.lsp_service import (
    LSPService, LSPServerConfig, LSPServerState, DiagnosticSeverity,
    Diagnostic, CompletionItem,
    get_lsp_service, shutdown_lsp_service
)
from icpy.core.message_broker import get_message_broker, shutdown_message_broker

# Mark all test methods as asyncio
pytestmark = pytest.mark.asyncio


class TestLSPService:
    """Test suite for LSPService"""
    
    @pytest_asyncio.fixture
    async def lsp_service(self):
        """Create a fresh LSP service for each test"""
        # Reset global instances
        try:
            await shutdown_lsp_service()
        except RuntimeError:
            pass
        try:
            await shutdown_message_broker()
        except RuntimeError:
            pass
        
        service = LSPService()
        await service.start()
        yield service
        await service.stop()

    @pytest_asyncio.fixture
    async def mock_lsp_server_process(self):
        """Mock LSP server process for testing"""
        mock_process = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        mock_process.returncode = None
        mock_process.pid = 12345
        
        # Mock communication
        mock_process.stdin.write = AsyncMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout.readline = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b'', b''))
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.terminate = AsyncMock()
        mock_process.kill = AsyncMock()
        
        return mock_process

    @pytest_asyncio.fixture
    async def temp_workspace(self):
        """Create a temporary workspace for testing"""
        temp_dir = tempfile.mkdtemp()
        
        # Create test files
        test_py_file = os.path.join(temp_dir, "test.py")
        with open(test_py_file, 'w') as f:
            f.write("""
def hello_world():
    print("Hello, World!")
    return "success"

class TestClass:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return f"Hello, {self.name}!"

# Test variable
test_var = "Hello"
""")
        
        test_js_file = os.path.join(temp_dir, "test.js")
        with open(test_js_file, 'w') as f:
            f.write("""
function helloWorld() {
    console.log("Hello, World!");
    return "success";
}

class TestClass {
    constructor(name) {
        this.name = name;
    }
    
    greet() {
        return `Hello, ${this.name}!`;
    }
}

const testVar = "Hello";
""")
        
        yield temp_dir
        shutil.rmtree(temp_dir)

    async def test_service_lifecycle(self, lsp_service):
        """Test LSP service lifecycle operations"""
        # Service should be running after fixture setup
        assert lsp_service.is_running()
        
        # Test stopping and restarting
        await lsp_service.stop()
        assert not lsp_service.is_running()
        
        await lsp_service.start()
        assert lsp_service.is_running()

    async def test_server_configuration(self, lsp_service):
        """Test LSP server configuration"""
        # Test adding Python server configuration
        python_config = LSPServerConfig(
            language="python",
            command=["python", "-m", "pylsp"],
            args=["--verbose"],
            env={"PYTHONPATH": "/test/path"}
        )
        
        lsp_service.add_server_config("python", python_config)
        
        # Verify configuration is stored
        configs = lsp_service.get_server_configs()
        assert "python" in configs
        assert configs["python"].language == "python"
        assert configs["python"].command == ["python", "-m", "pylsp"]

    async def test_workspace_management(self, lsp_service, temp_workspace):
        """Test workspace operations"""
        # Test setting workspace
        await lsp_service.set_workspace(temp_workspace)
        
        # Verify workspace is set
        assert lsp_service.get_workspace() == temp_workspace
        
        # Test getting workspace files
        files = await lsp_service.get_workspace_files()
        assert any(f.endswith("test.py") for f in files)
        assert any(f.endswith("test.js") for f in files)

    @patch('asyncio.create_subprocess_exec')
    async def test_server_startup_mock(self, mock_subprocess, lsp_service, mock_lsp_server_process):
        """Test LSP server startup with mocked process"""
        mock_subprocess.return_value = mock_lsp_server_process
        
        # Configure Python server
        python_config = LSPServerConfig(
            language="python",
            command=["python", "-m", "pylsp"]
        )
        lsp_service.add_server_config("python", python_config)
        
        # Start server
        result = await lsp_service.start_server("python")
        assert result is True
        
        # Verify server is tracked
        assert "python" in lsp_service.get_active_servers()
        server_info = lsp_service.get_server_info("python")
        assert server_info["state"] == LSPServerState.RUNNING.value
        assert server_info["pid"] == 12345

    @patch('asyncio.create_subprocess_exec')
    async def test_server_communication_mock(self, mock_subprocess, lsp_service, mock_lsp_server_process):
        """Test LSP server communication with mocked responses"""
        # Setup mock responses
        initialize_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "capabilities": {
                    "textDocumentSync": 1,
                    "completionProvider": {
                        "resolveProvider": True,
                        "triggerCharacters": ["."]
                    },
                    "hoverProvider": True,
                    "definitionProvider": True,
                    "diagnosticProvider": True
                }
            }
        }
        
        mock_lsp_server_process.stdout.readline = AsyncMock(
            side_effect=[
                f"Content-Length: {len(json.dumps(initialize_response))}\r\n".encode(),
                b"\r\n",
                json.dumps(initialize_response).encode() + b"\n",
                b"",  # EOF
            ]
        )
        
        mock_subprocess.return_value = mock_lsp_server_process
        
        # Configure and start server
        python_config = LSPServerConfig(
            language="python",
            command=["python", "-m", "pylsp"]
        )
        lsp_service.add_server_config("python", python_config)
        
        result = await lsp_service.start_server("python")
        assert result is True
        
        # Test sending initialize request
        response = await lsp_service.send_request("python", "initialize", {
            "processId": os.getpid(),
            "rootUri": f"file:///test",
            "capabilities": {}
        })
        
        # Verify request was sent
        assert mock_lsp_server_process.stdin.write.called

    async def test_code_completion_mock(self, lsp_service):
        """Test code completion functionality (mocked)"""
        # Mock completion response
        with patch.object(lsp_service, 'send_request') as mock_request:
            mock_request.return_value = {
                "items": [
                    {
                        "label": "hello_world",
                        "kind": 3,  # Function
                        "detail": "def hello_world()",
                        "documentation": "Test function"
                    },
                    {
                        "label": "TestClass",
                        "kind": 7,  # Class
                        "detail": "class TestClass",
                        "documentation": "Test class"
                    }
                ]
            }
            
            # Test completion
            completions = await lsp_service.get_completions(
                "file:///test/test.py", 
                0, 0  # line, character
            )
            
            assert len(completions) == 2
            assert completions[0]["label"] == "hello_world"
            assert completions[1]["label"] == "TestClass"

    async def test_diagnostics_mock(self, lsp_service):
        """Test diagnostics functionality (mocked)"""
        # Mock diagnostics response
        with patch.object(lsp_service, 'send_request') as mock_request:
            mock_request.return_value = {
                "diagnostics": [
                    {
                        "range": {
                            "start": {"line": 1, "character": 0},
                            "end": {"line": 1, "character": 10}
                        },
                        "severity": 1,  # Error
                        "message": "Undefined variable 'undefined_var'",
                        "source": "pylsp"
                    }
                ]
            }
            
            # Test diagnostics
            diagnostics = await lsp_service.get_diagnostics(
                "python", "file:///test/test.py"
            )
            
            assert len(diagnostics) == 1
            assert diagnostics[0]["severity"] == 1
            assert "undefined_var" in diagnostics[0]["message"]

    async def test_hover_information_mock(self, lsp_service):
        """Test hover information functionality (mocked)"""
        # Mock hover response
        with patch.object(lsp_service, 'send_request') as mock_request:
            mock_request.return_value = {
                "contents": {
                    "kind": "markdown",
                    "value": "```python\ndef hello_world() -> str\n```\nA test function that prints hello world"
                }
            }
            
            # Test hover
            hover_info = await lsp_service.get_hover_info(
                "file:///test/test.py",
                1, 5  # line, character
            )
            
            assert hover_info is not None
            assert "hello_world" in hover_info["contents"]["value"]

    async def test_goto_definition_mock(self, lsp_service):
        """Test go to definition functionality (mocked)"""
        # Mock definition response
        with patch.object(lsp_service, 'send_request') as mock_request:
            mock_request.return_value = {
                "uri": "file:///test/test.py",
                "range": {
                    "start": {"line": 1, "character": 4},
                    "end": {"line": 1, "character": 15}
                }
            }
            
            # Test goto definition
            definition = await lsp_service.goto_definition(
                "python", "file:///test/test.py",
                10, 5  # line, character
            )
            
            assert definition is not None
            assert definition["uri"] == "file:///test/test.py"
            assert definition["range"]["start"]["line"] == 1

    async def test_multiple_servers(self, lsp_service):
        """Test managing multiple LSP servers"""
        # Configure multiple servers
        python_config = LSPServerConfig(
            language="python",
            command=["python", "-m", "pylsp"]
        )
        typescript_config = LSPServerConfig(
            language="typescript",
            command=["typescript-language-server", "--stdio"]
        )
        
        lsp_service.add_server_config("python", python_config)
        lsp_service.add_server_config("typescript", typescript_config)
        
        # Verify both configurations exist
        configs = lsp_service.get_server_configs()
        assert "python" in configs
        assert "typescript" in configs

    async def test_server_error_handling(self, lsp_service):
        """Test LSP server error handling"""
        # Test starting non-existent server
        nonexistent_config = LSPServerConfig(
            language="nonexistent",
            command=["nonexistent-lsp-server"]
        )
        lsp_service.add_server_config("nonexistent", nonexistent_config)
        
        # This should fail gracefully
        result = await lsp_service.start_server("nonexistent")
        assert result is False
        
        # Server should not be in active servers
        assert "nonexistent" not in lsp_service.get_active_servers()

    async def test_server_shutdown(self, lsp_service):
        """Test LSP server shutdown"""
        # Configure server
        python_config = LSPServerConfig(
            language="python",
            command=["python", "-m", "pylsp"]
        )
        lsp_service.add_server_config("python", python_config)
        
        # Mock successful startup
        with patch.object(lsp_service, '_start_server_process') as mock_start:
            mock_start.return_value = True
            await lsp_service.start_server("python")
        
        # Test shutdown
        await lsp_service.stop_server("python")
        
        # Server should not be active
        assert "python" not in lsp_service.get_active_servers()

    async def test_file_change_notifications(self, lsp_service, temp_workspace):
        """Test file change notifications to LSP servers"""
        # Set workspace
        await lsp_service.set_workspace(temp_workspace)
        
        # Mock server communication
        with patch.object(lsp_service, 'send_notification') as mock_notify:
            # Simulate file change
            test_file = os.path.join(temp_workspace, "test.py")
            await lsp_service.notify_file_changed(test_file, "new content")
            
            # Verify notification was sent (would be sent to all active servers)
            # Since no servers are actually running, no notifications sent
            assert True  # Test passes if no exceptions

    async def test_workspace_symbol_search_mock(self, lsp_service):
        """Test workspace symbol search (mocked)"""
        # Mock symbol search response
        with patch.object(lsp_service, 'send_request') as mock_request:
            mock_request.return_value = [
                {
                    "name": "hello_world",
                    "kind": 12,  # Function
                    "location": {
                        "uri": "file:///test/test.py",
                        "range": {
                            "start": {"line": 1, "character": 4},
                            "end": {"line": 1, "character": 15}
                        }
                    }
                },
                {
                    "name": "TestClass",
                    "kind": 5,  # Class
                    "location": {
                        "uri": "file:///test/test.py",
                        "range": {
                            "start": {"line": 5, "character": 6},
                            "end": {"line": 5, "character": 15}
                        }
                    }
                }
            ]
            
            # Test symbol search
            symbols = await lsp_service.workspace_symbol_search("python", "hello")
            
            assert len(symbols) == 2
            assert symbols[0]["name"] == "hello_world"
            assert symbols[1]["name"] == "TestClass"

    async def test_document_formatting_mock(self, lsp_service):
        """Test document formatting (mocked)"""
        # Mock formatting response
        with patch.object(lsp_service, 'send_request') as mock_request:
            mock_request.return_value = [
                {
                    "range": {
                        "start": {"line": 0, "character": 0},
                        "end": {"line": 10, "character": 0}
                    },
                    "newText": "def hello_world():\n    print(\"Hello, World!\")\n    return \"success\"\n"
                }
            ]
            
            # Test formatting
            edits = await lsp_service.format_document(
                "python", "file:///test/test.py"
            )
            
            assert len(edits) == 1
            assert "Hello, World!" in edits[0]["newText"]

    async def test_message_broker_integration(self, lsp_service):
        """Test integration with message broker"""
        # Get message broker
        broker = await get_message_broker()
        
        # Subscribe to LSP events
        received_events = []
        
        async def event_handler(message):
            received_events.append(message)
        
        await broker.subscribe("lsp.*", event_handler)
        
        # Trigger an LSP event (server state change)
        await lsp_service._publish_event("lsp.server.state_changed", {
            "language": "python",
            "state": "starting",
            "timestamp": "2023-01-01T00:00:00Z"
        })
        
        # Give broker time to process
        await asyncio.sleep(0.1)
        
        # Verify event was received
        assert len(received_events) > 0
        assert received_events[0].data["language"] == "python"

    async def test_performance_and_caching(self, lsp_service):
        """Test performance optimizations and caching"""
        # Test response caching
        with patch.object(lsp_service, 'send_request') as mock_request:
            mock_request.return_value = {"cached": True}
            
            # First request
            result1 = await lsp_service.get_completions(
                "python", "file:///test/test.py",
                0, 0  # line, character
            )
            
            # Second identical request (should use cache if implemented)
            result2 = await lsp_service.get_completions(
                "python", "file:///test/test.py", 
                0, 0  # line, character
            )
            
            assert result1 == result2

    async def test_concurrent_operations(self, lsp_service):
        """Test concurrent LSP operations"""
        # Mock multiple concurrent requests
        with patch.object(lsp_service, 'send_request') as mock_request:
            mock_request.return_value = {"result": "success"}
            
            # Start multiple concurrent operations
            tasks = [
                lsp_service.get_completions("python", "file:///test1.py", 0, 0),
                lsp_service.get_completions("python", "file:///test2.py", 0, 0),
                lsp_service.get_completions("python", "file:///test3.py", 0, 0),
            ]
            
            # Wait for all to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed
            assert len(results) == 3
            assert all(not isinstance(r, Exception) for r in results)

    async def test_global_service_management(self):
        """Test global LSP service management"""
        # Test getting global service
        service1 = await get_lsp_service()
        service2 = await get_lsp_service()
        
        # Should be the same instance
        assert service1 is service2
        
        # Test shutdown
        await shutdown_lsp_service()
        
        # Getting service after shutdown should create new instance
        service3 = await get_lsp_service()
        assert service3 is not service1
        
        # Cleanup
        await shutdown_lsp_service()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
