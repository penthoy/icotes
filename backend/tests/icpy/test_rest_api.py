"""
Tests for icpy REST API

This module contains comprehensive tests for the HTTP REST API endpoints,
ensuring proper functionality, error handling, and integration with
the underlying services.

Author: GitHub Copilot
Date: July 16, 2025
"""

import asyncio
import json
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
import httpx

from icpy.api.rest_api import RestAPI, get_rest_api
from icpy.core.message_broker import MessageBroker
from icpy.core.connection_manager import ConnectionManager
from icpy.services.workspace_service import WorkspaceService
from icpy.services.filesystem_service import FileSystemService
from icpy.services.terminal_service import TerminalService

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    return FastAPI(title="Test App", version="1.0.0")


@pytest.fixture
def mock_message_broker():
    """Create mock message broker."""
    broker = AsyncMock(spec=MessageBroker)
    broker.publish = AsyncMock()
    return broker


@pytest.fixture
def mock_connection_manager():
    """Create mock connection manager."""
    manager = AsyncMock(spec=ConnectionManager)
    manager.handle_request = AsyncMock()
    return manager


@pytest.fixture
def mock_workspace_service():
    """Create mock workspace service."""
    service = AsyncMock(spec=WorkspaceService)
    service.list_workspaces = AsyncMock(return_value=[])
    service.create_workspace = AsyncMock(return_value={"id": "test_workspace", "name": "Test Workspace"})
    service.get_workspace = AsyncMock(return_value={"id": "test_workspace", "name": "Test Workspace"})
    service.update_workspace = AsyncMock(return_value={"id": "test_workspace", "name": "Updated Workspace"})
    service.delete_workspace = AsyncMock()
    service.activate_workspace = AsyncMock()
    return service


@pytest.fixture
def mock_filesystem_service():
    """Create mock filesystem service."""
    service = AsyncMock(spec=FileSystemService)
    service.list_directory = AsyncMock(return_value=[])
    service.read_file = AsyncMock(return_value="test content")
    service.write_file = AsyncMock()
    service.delete_file = AsyncMock()
    service.search_files = AsyncMock(return_value=[])
    service.get_file_info = AsyncMock(return_value={"path": "/test", "size": 100})
    return service


@pytest.fixture
def mock_terminal_service():
    """Create mock terminal service."""
    service = AsyncMock(spec=TerminalService)
    service.list_terminals = AsyncMock(return_value=[])
    service.create_terminal = AsyncMock(return_value={"id": "test_terminal", "name": "Test Terminal"})
    service.get_terminal = AsyncMock(return_value={"id": "test_terminal", "name": "Test Terminal"})
    service.send_input = AsyncMock()
    service.resize_terminal = AsyncMock()
    service.destroy_terminal = AsyncMock()
    return service


@pytest.fixture
def client_with_rest_api(app, mock_message_broker, mock_connection_manager, 
                        mock_workspace_service, mock_filesystem_service, mock_terminal_service):
    """Create test client with REST API configured."""
    with patch('icpy.api.rest_api.get_message_broker', return_value=mock_message_broker), \
         patch('icpy.api.rest_api.get_connection_manager', return_value=mock_connection_manager), \
         patch('icpy.api.rest_api.get_workspace_service', return_value=mock_workspace_service), \
         patch('icpy.api.rest_api.get_filesystem_service', return_value=mock_filesystem_service), \
         patch('icpy.api.rest_api.get_terminal_service', return_value=mock_terminal_service):
        
        # Create REST API instance
        api = RestAPI(app)
        
        # Initialize synchronously for testing
        async def init_api():
            await api.initialize()
        
        # Run initialization in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(init_api())
        
        return TestClient(app)


class TestRestAPI:
    """Test suite for REST API functionality."""

    def test_health_check(self, client_with_rest_api):
        """Test health check endpoint."""
        response = client_with_rest_api.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "status" in data["data"]
        assert data["data"]["status"] == "healthy"

    def test_get_stats(self, client_with_rest_api):
        """Test statistics endpoint."""
        response = client_with_rest_api.get("/api/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "total_requests" in data["data"]

    def test_jsonrpc_endpoint(self, client_with_rest_api, mock_connection_manager):
        """Test JSON-RPC endpoint."""
        # Mock successful response
        mock_connection_manager.handle_request.return_value = MagicMock(
            to_dict=lambda: {"jsonrpc": "2.0", "result": "success", "id": 1}
        )
        
        response = client_with_rest_api.post("/api/jsonrpc", json={
            "jsonrpc": "2.0",
            "method": "test.method",
            "params": {"key": "value"},
            "id": 1
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["result"] == "success"
        assert data["id"] == 1

    def test_list_workspaces(self, client_with_rest_api, mock_workspace_service):
        """Test list workspaces endpoint."""
        mock_workspace_service.list_workspaces.return_value = [
            {"id": "ws1", "name": "Workspace 1"},
            {"id": "ws2", "name": "Workspace 2"}
        ]
        
        response = client_with_rest_api.get("/api/workspaces")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["data"][0]["name"] == "Workspace 1"

    def test_create_workspace(self, client_with_rest_api, mock_workspace_service):
        """Test create workspace endpoint."""
        mock_workspace_service.create_workspace.return_value = {
            "id": "new_workspace",
            "name": "New Workspace"
        }
        
        response = client_with_rest_api.post("/api/workspaces", json={
            "name": "New Workspace",
            "description": "A new workspace"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "New Workspace"
        assert data["message"] == "Workspace created successfully"

    def test_get_workspace(self, client_with_rest_api, mock_workspace_service):
        """Test get workspace endpoint."""
        mock_workspace_service.get_workspace.return_value = {
            "id": "test_workspace",
            "name": "Test Workspace"
        }
        
        response = client_with_rest_api.get("/api/workspaces/test_workspace")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "test_workspace"

    def test_get_workspace_not_found(self, client_with_rest_api, mock_workspace_service):
        """Test get workspace endpoint with non-existent workspace."""
        mock_workspace_service.get_workspace.return_value = None
        
        response = client_with_rest_api.get("/api/workspaces/nonexistent")
        assert response.status_code == 404

    def test_update_workspace(self, client_with_rest_api, mock_workspace_service):
        """Test update workspace endpoint."""
        mock_workspace_service.update_workspace.return_value = {
            "id": "test_workspace",
            "name": "Updated Workspace"
        }
        
        response = client_with_rest_api.put("/api/workspaces/test_workspace", json={
            "name": "Updated Workspace",
            "description": "Updated description"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Workspace updated successfully"

    def test_delete_workspace(self, client_with_rest_api, mock_workspace_service):
        """Test delete workspace endpoint."""
        response = client_with_rest_api.delete("/api/workspaces/test_workspace")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Workspace deleted successfully"

    def test_activate_workspace(self, client_with_rest_api, mock_workspace_service):
        """Test activate workspace endpoint."""
        response = client_with_rest_api.post("/api/workspaces/test_workspace/activate")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Workspace activated successfully"

    def test_list_files(self, client_with_rest_api, mock_filesystem_service):
        """Test list files endpoint."""
        mock_filesystem_service.list_directory.return_value = [
            {"name": "file1.txt", "type": "file"},
            {"name": "dir1", "type": "directory"}
        ]
        
        response = client_with_rest_api.get("/api/files?path=/test")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2

    def test_get_file_content(self, client_with_rest_api, mock_filesystem_service):
        """Test get file content endpoint."""
        mock_filesystem_service.read_file.return_value = "test file content"
        
        response = client_with_rest_api.get("/api/files/content?path=/test/file.txt")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["content"] == "test file content"

    def test_get_file_content_not_found(self, client_with_rest_api, mock_filesystem_service):
        """Test get file content endpoint with non-existent file."""
        mock_filesystem_service.read_file.side_effect = FileNotFoundError()
        
        response = client_with_rest_api.get("/api/files/content?path=/nonexistent/file.txt")
        assert response.status_code == 404

    def test_create_file(self, client_with_rest_api, mock_filesystem_service):
        """Test create file endpoint."""
        response = client_with_rest_api.post("/api/files", json={
            "path": "/test/new_file.txt",
            "content": "new file content"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "File created successfully"

    def test_update_file(self, client_with_rest_api, mock_filesystem_service):
        """Test update file endpoint."""
        response = client_with_rest_api.put("/api/files", json={
            "path": "/test/existing_file.txt",
            "content": "updated content"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "File updated successfully"

    def test_delete_file(self, client_with_rest_api, mock_filesystem_service):
        """Test delete file endpoint."""
        response = client_with_rest_api.delete("/api/files?path=/test/file.txt")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "File deleted successfully"

    def test_search_files(self, client_with_rest_api, mock_filesystem_service):
        """Test search files endpoint."""
        mock_filesystem_service.search_files.return_value = [
            {"path": "/test/file1.txt", "matches": ["match1"]},
            {"path": "/test/file2.txt", "matches": ["match2"]}
        ]
        
        response = client_with_rest_api.post("/api/files/search", json={
            "query": "test query",
            "path": "/test"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2

    def test_get_file_info(self, client_with_rest_api, mock_filesystem_service):
        """Test get file info endpoint."""
        mock_filesystem_service.get_file_info.return_value = {
            "path": "/test/file.txt",
            "size": 1024,
            "modified": "2025-01-01T00:00:00Z"
        }
        
        response = client_with_rest_api.get("/api/files/info?path=/test/file.txt")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["size"] == 1024

    def test_get_file_info_not_found(self, client_with_rest_api, mock_filesystem_service):
        """Test get file info endpoint with non-existent file."""
        mock_filesystem_service.get_file_info.side_effect = FileNotFoundError()
        
        response = client_with_rest_api.get("/api/files/info?path=/nonexistent/file.txt")
        assert response.status_code == 404

    def test_list_terminals(self, client_with_rest_api, mock_terminal_service):
        """Test list terminals endpoint."""
        mock_terminal_service.list_terminals.return_value = [
            {"id": "term1", "name": "Terminal 1"},
            {"id": "term2", "name": "Terminal 2"}
        ]
        
        response = client_with_rest_api.get("/api/terminals")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2

    def test_create_terminal(self, client_with_rest_api, mock_terminal_service):
        """Test create terminal endpoint."""
        mock_terminal_service.create_terminal.return_value = {
            "id": "new_terminal",
            "name": "New Terminal"
        }
        
        response = client_with_rest_api.post("/api/terminals", json={
            "name": "New Terminal",
            "shell": "/bin/bash"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "New Terminal"

    def test_get_terminal(self, client_with_rest_api, mock_terminal_service):
        """Test get terminal endpoint."""
        mock_terminal_service.get_terminal.return_value = {
            "id": "test_terminal",
            "name": "Test Terminal"
        }
        
        response = client_with_rest_api.get("/api/terminals/test_terminal")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == "test_terminal"

    def test_get_terminal_not_found(self, client_with_rest_api, mock_terminal_service):
        """Test get terminal endpoint with non-existent terminal."""
        mock_terminal_service.get_terminal.return_value = None
        
        response = client_with_rest_api.get("/api/terminals/nonexistent")
        assert response.status_code == 404

    def test_send_terminal_input(self, client_with_rest_api, mock_terminal_service):
        """Test send terminal input endpoint."""
        response = client_with_rest_api.post("/api/terminals/test_terminal/input", json={
            "data": "ls -la\n"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Input sent successfully"

    def test_resize_terminal(self, client_with_rest_api, mock_terminal_service):
        """Test resize terminal endpoint."""
        response = client_with_rest_api.post("/api/terminals/test_terminal/resize", json={
            "rows": 30,
            "cols": 120
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Terminal resized successfully"

    def test_delete_terminal(self, client_with_rest_api, mock_terminal_service):
        """Test delete terminal endpoint."""
        response = client_with_rest_api.delete("/api/terminals/test_terminal")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Terminal deleted successfully"

    def test_error_handling(self, client_with_rest_api, mock_workspace_service):
        """Test error handling in endpoints."""
        mock_workspace_service.list_workspaces.side_effect = Exception("Test error")
        
        response = client_with_rest_api.get("/api/workspaces")
        assert response.status_code == 500

    def test_request_logging_middleware(self, client_with_rest_api):
        """Test request logging middleware."""
        # Make a request to trigger the middleware
        response = client_with_rest_api.get("/api/health")
        assert response.status_code == 200
        
        # Check that stats are updated
        stats_response = client_with_rest_api.get("/api/stats")
        assert stats_response.status_code == 200
        
        stats_data = stats_response.json()
        assert stats_data["data"]["total_requests"] > 0

    def test_openapi_documentation(self, client_with_rest_api):
        """Test OpenAPI documentation endpoint."""
        response = client_with_rest_api.get("/api/openapi.json")
        assert response.status_code == 200
        
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "icpy REST API"


class TestFileApiRegression:
    """Regression tests for file API bug fixes."""
    
    def test_put_files_parameter_mapping(self, client_with_rest_api, mock_filesystem_service):
        """Test that PUT /api/files correctly maps parameters to filesystem service.
        
        This test covers the specific bug where the REST API was passing incorrect
        parameter names to the filesystem service, causing 500 errors.
        """
        # Test data
        test_path = "/workspace/test_file.py"
        test_content = "print('Hello, World!')\n"
        test_encoding = "utf-8"
        test_create_dirs = True
        
        # Make the request
        response = client_with_rest_api.put("/api/files", json={
            "path": test_path,
            "content": test_content,
            "encoding": test_encoding,
            "create_dirs": test_create_dirs
        })
        
        # Verify the response is successful
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "File updated successfully"
        
        # Most importantly: verify the filesystem service was called with correct parameters
        mock_filesystem_service.write_file.assert_called_once_with(
            file_path=test_path,
            content=test_content,
            encoding=test_encoding,
            create_dirs=test_create_dirs
        )
    
    def test_put_files_with_defaults(self, client_with_rest_api, mock_filesystem_service):
        """Test PUT /api/files with default parameter values."""
        test_path = "/workspace/simple_file.txt"
        test_content = "Simple content"
        
        # Make request with minimal parameters
        response = client_with_rest_api.put("/api/files", json={
            "path": test_path,
            "content": test_content
        })
        
        # Verify success
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify correct parameters were passed (including defaults)
        mock_filesystem_service.write_file.assert_called_once_with(
            file_path=test_path,
            content=test_content,
            encoding=None,  # Default from FileOperationRequest
            create_dirs=False  # Default from FileOperationRequest
        )
    
    def test_put_files_empty_content(self, client_with_rest_api, mock_filesystem_service):
        """Test PUT /api/files handles empty content correctly."""
        test_path = "/workspace/empty_file.txt"
        
        # Make request with None content
        response = client_with_rest_api.put("/api/files", json={
            "path": test_path,
            "content": None
        })
        
        # Verify success
        assert response.status_code == 200
        
        # Verify empty string was passed to filesystem service
        mock_filesystem_service.write_file.assert_called_once()
        call_args = mock_filesystem_service.write_file.call_args
        assert call_args.kwargs["content"] == ""
    
    def test_put_files_filesystem_error_handling(self, client_with_rest_api, mock_filesystem_service):
        """Test PUT /api/files handles filesystem service errors properly."""
        # Configure mock to raise an exception
        mock_filesystem_service.write_file.side_effect = Exception("Permission denied")
        
        # Make request
        response = client_with_rest_api.put("/api/files", json={
            "path": "/readonly/file.txt",
            "content": "test content"
        })
        
        # Verify error response
        assert response.status_code == 500
        assert "Permission denied" in response.json()["detail"]
    
    def test_put_files_missing_path(self, client_with_rest_api, mock_filesystem_service):
        """Test PUT /api/files handles missing path parameter."""
        # Make request without path
        response = client_with_rest_api.put("/api/files", json={
            "content": "test content"
        })
        
        # Should return validation error (422)
        assert response.status_code == 422
        
        # Filesystem service should not have been called
        mock_filesystem_service.write_file.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
