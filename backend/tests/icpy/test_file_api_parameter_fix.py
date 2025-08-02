#!/usr/bin/env python3
"""
Direct validation test for the file API parameter mapping fix.
This test directly validates that the filesystem service gets called with correct parameters
without relying on the full REST API test infrastructure.

This ensures our bug fix for the 500 error on PUT /api/files is properly validated.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from icpy.api.rest_api import RestAPI
from icpy.services.filesystem_service import FileSystemService
from fastapi import FastAPI


class TestFileApiParameterFix:
    """Test that validates the specific parameter mapping bug fix."""
    
    @pytest.mark.asyncio
    async def test_filesystem_service_parameter_mapping(self):
        """Test filesystem service gets called with correct parameters."""
        # Create mock filesystem service
        mock_filesystem_service = AsyncMock(spec=FileSystemService)
        mock_filesystem_service.write_file = AsyncMock()
        
        # Create a FastAPI app
        app = FastAPI()
        
        # Create REST API instance with mocked services
        with patch('icpy.api.rest_api.get_filesystem_service', return_value=mock_filesystem_service), \
             patch('icpy.api.rest_api.get_message_broker'), \
             patch('icpy.api.rest_api.get_connection_manager'), \
             patch('icpy.api.rest_api.get_workspace_service'), \
             patch('icpy.api.rest_api.get_terminal_service'):
            
            api = RestAPI(app)
            await api.initialize()
            
            # Find the update_file endpoint
            update_file_endpoint = None
            for route in app.routes:
                if hasattr(route, 'path') and route.path == '/api/files' and hasattr(route, 'methods') and 'PUT' in route.methods:
                    update_file_endpoint = route.endpoint
                    break
            
            assert update_file_endpoint is not None, "PUT /api/files endpoint not found"
            
            # Create a mock request object
            class MockRequest:
                def __init__(self, path, content, encoding=None, create_dirs=False):
                    self.path = path
                    self.content = content
                    self.encoding = encoding
                    self.create_dirs = create_dirs
            
            # Test the endpoint directly
            test_path = "/workspace/test_file.py"
            test_content = "print('Hello, World!')"
            test_encoding = "utf-8"
            test_create_dirs = True
            
            request = MockRequest(test_path, test_content, test_encoding, test_create_dirs)
            
            # Call the endpoint
            response = await update_file_endpoint(request)
            
            # Verify the response
            assert response.success is True
            assert response.message == "File updated successfully"
            
            # Most importantly: verify filesystem service was called with correct parameter names
            mock_filesystem_service.write_file.assert_called_once_with(
                file_path=test_path,  # This was the bug - it was called 'path' before
                content=test_content,
                encoding=test_encoding,
                create_dirs=test_create_dirs
            )
    
    @pytest.mark.asyncio 
    async def test_filesystem_service_with_none_content(self):
        """Test filesystem service handles None content correctly."""
        mock_filesystem_service = AsyncMock(spec=FileSystemService)
        mock_filesystem_service.write_file = AsyncMock()
        
        app = FastAPI()
        
        with patch('icpy.api.rest_api.get_filesystem_service', return_value=mock_filesystem_service), \
             patch('icpy.api.rest_api.get_message_broker'), \
             patch('icpy.api.rest_api.get_connection_manager'), \
             patch('icpy.api.rest_api.get_workspace_service'), \
             patch('icpy.api.rest_api.get_terminal_service'):
            
            api = RestAPI(app)
            await api.initialize()
            
            # Find the update_file endpoint
            update_file_endpoint = None
            for route in app.routes:
                if hasattr(route, 'path') and route.path == '/api/files' and hasattr(route, 'methods') and 'PUT' in route.methods:
                    update_file_endpoint = route.endpoint
                    break
            
            class MockRequest:
                def __init__(self, path, content, encoding=None, create_dirs=False):
                    self.path = path
                    self.content = content
                    self.encoding = encoding
                    self.create_dirs = create_dirs
            
            # Test with None content
            request = MockRequest("/workspace/empty.txt", None)
            response = await update_file_endpoint(request)
            
            assert response.success is True
            
            # Verify None content gets converted to empty string
            mock_filesystem_service.write_file.assert_called_once()
            call_kwargs = mock_filesystem_service.write_file.call_args.kwargs
            assert call_kwargs["content"] == ""  # None should be converted to empty string
            assert call_kwargs["file_path"] == "/workspace/empty.txt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
