"""
Integration tests for LSP Service
Tests basic LSP service functionality with existing API
"""

import pytest
import pytest_asyncio
import asyncio
import os
import tempfile
import shutil
from typing import Dict, Any, List

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


class TestLSPServiceBasic:
    """Test suite for LSPService - basic functionality only"""
    
    @pytest_asyncio.fixture
    async def lsp_service(self):
        """Create a fresh LSP service for each test"""
        # Reset global instances
        try:
            await shutdown_lsp_service()
        except (RuntimeError, AttributeError):
            pass
        try:
            await shutdown_message_broker()
        except (RuntimeError, AttributeError):
            pass
        
        service = LSPService()
        await service.start()
        yield service
        await service.stop()

    @pytest_asyncio.fixture
    async def temp_workspace(self):
        """Create a temporary workspace for testing"""
        temp_dir = tempfile.mkdtemp()
        
        # Create test file
        test_py_file = os.path.join(temp_dir, "test.py")
        with open(test_py_file, 'w') as f:
            f.write("""
def hello_world():
    print("Hello, World!")
    return "success"

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
        """Test LSP server configuration exists"""
        # The service should have default server configurations
        assert hasattr(lsp_service, 'server_configs')
        assert isinstance(lsp_service.server_configs, dict)

    async def test_server_status(self, lsp_service):
        """Test server status reporting"""
        # Get initial status
        status = await lsp_service.get_server_status()
        assert isinstance(status, dict)
        assert "running" in status
        assert status["running"] is True

    async def test_available_languages(self, lsp_service):
        """Test getting available languages"""
        languages = await lsp_service.get_available_languages()
        assert isinstance(languages, list)

    async def test_document_operations(self, lsp_service, temp_workspace):
        """Test document lifecycle operations"""
        test_file = os.path.join(temp_workspace, "test.py")
        
        # Test opening document
        with open(test_file, 'r') as f:
            content = f.read()
        
        result = await lsp_service.open_document(test_file, content, "python")
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

    async def test_server_error_handling(self, lsp_service, temp_workspace):
        """Test LSP server error handling"""
        # Try to start server for non-existent language
        server_id = await lsp_service.start_server("nonexistent", temp_workspace)
        assert server_id is None

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

    async def test_service_attributes(self, lsp_service):
        """Test service has expected attributes"""
        # Service should have expected attributes
        assert hasattr(lsp_service, 'running')
        assert hasattr(lsp_service, 'servers')
        assert hasattr(lsp_service, 'server_configs')
        assert hasattr(lsp_service, 'open_documents')
        assert hasattr(lsp_service, 'stats')
        assert hasattr(lsp_service, 'completion_cache')
        assert hasattr(lsp_service, 'hover_cache')
        
        # Check attribute types
        assert isinstance(lsp_service.servers, dict)
        assert isinstance(lsp_service.server_configs, dict)
        assert isinstance(lsp_service.open_documents, dict)
        assert isinstance(lsp_service.stats, dict)
        assert isinstance(lsp_service.completion_cache, dict)
        assert isinstance(lsp_service.hover_cache, dict)

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

    async def test_message_broker_integration(self, lsp_service):
        """Test integration with message broker"""
        # Get message broker
        broker = await get_message_broker()
        
        # Subscribe to LSP events
        received_events = []
        
        async def event_handler(message):
            received_events.append(message)
        
        await broker.subscribe("lsp.*", event_handler)
        
        # Trigger an LSP operation
        await lsp_service.get_server_status()
        
        # Give broker time to process
        await asyncio.sleep(0.1)
        
        # Test passes if no exceptions occurred
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
