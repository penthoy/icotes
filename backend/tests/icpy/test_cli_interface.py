"""
Integration tests for icpy CLI Interface

This module contains comprehensive tests for the CLI interface functionality,
including file operations, terminal management, workspace operations, and
interactive mode testing.

Author: GitHub Copilot
Date: July 16, 2025
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any, Optional

# Add the backend directory to the Python path for testing
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Try to import CLI modules
try:
    from icpy.cli.icpy_cli import IcpyCLI
    from icpy.cli.http_client import HttpClient, CliConfig
    from icpy.cli.command_handlers import CommandHandlers
except ImportError as e:
    # Skip tests if CLI modules are not available
    import pytest
    pytest.skip(f"CLI modules not available: {e}", allow_module_level=True)


class TestHttpClient:
    """Test HTTP client functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.config = CliConfig(
            backend_url="http://localhost:8000",
            timeout=5,
            verbose=True
        )
        self.client = HttpClient(self.config)
    
    def teardown_method(self):
        """Clean up test environment"""
        if self.client:
            self.client.close()
    
    @patch('requests.Session.get')
    def test_check_connection_success(self, mock_get):
        """Test successful connection check"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = self.client.check_connection()
        assert result is True
        mock_get.assert_called_once()
    
    @patch('requests.Session.get')
    def test_check_connection_failure(self, mock_get):
        """Test connection check failure"""
        mock_get.side_effect = Exception("Connection failed")
        
        result = self.client.check_connection()
        assert result is False
    
    @patch('requests.Session.get')
    def test_make_request_get(self, mock_get):
        """Test GET request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {'status': 'success'}
        mock_get.return_value = mock_response
        
        result = self.client.make_request('GET', '/test')
        assert result == {'status': 'success'}
        mock_get.assert_called_once()
    
    @patch('requests.Session.post')
    def test_make_request_post(self, mock_post):
        """Test POST request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {'status': 'success'}
        mock_post.return_value = mock_response
        
        data = {'key': 'value'}
        result = self.client.make_request('POST', '/test', data)
        assert result == {'status': 'success'}
        mock_post.assert_called_once()
    
    @patch('requests.Session.post')
    def test_json_rpc_request(self, mock_post):
        """Test JSON-RPC request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {
            'jsonrpc': '2.0',
            'result': {'data': 'test'},
            'id': 'test-id'
        }
        mock_post.return_value = mock_response
        
        result = self.client.json_rpc_request('test_method', {'param': 'value'})
        assert result == {'data': 'test'}
    
    @patch('requests.Session.post')
    def test_json_rpc_request_error(self, mock_post):
        """Test JSON-RPC request with error"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {
            'jsonrpc': '2.0',
            'error': {'code': -32000, 'message': 'Test error'},
            'id': 'test-id'
        }
        mock_post.return_value = mock_response
        
        with pytest.raises(Exception) as exc_info:
            self.client.json_rpc_request('test_method', {'param': 'value'})
        assert 'Test error' in str(exc_info.value)
    
    @patch('requests.Session.get')
    def test_get_workspace_list(self, mock_get):
        """Test workspace list retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = [
            {'workspace_id': 'ws1', 'name': 'Workspace 1'},
            {'workspace_id': 'ws2', 'name': 'Workspace 2'}
        ]
        mock_get.return_value = mock_response
        
        result = self.client.get_workspace_list()
        assert len(result) == 2
        assert result[0]['workspace_id'] == 'ws1'
    
    @patch('requests.Session.post')
    def test_open_file(self, mock_post):
        """Test file opening"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {'status': 'success', 'file_id': 'file123'}
        mock_post.return_value = mock_response
        
        result = self.client.open_file('/path/to/file.py')
        assert result['status'] == 'success'
        assert result['file_id'] == 'file123'
    
    @patch('requests.Session.post')
    def test_create_terminal(self, mock_post):
        """Test terminal creation"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {'terminal_id': 'term123', 'status': 'active'}
        mock_post.return_value = mock_response
        
        result = self.client.create_terminal()
        assert result['terminal_id'] == 'term123'
        assert result['status'] == 'active'


class TestCommandHandlers:
    """Test command handler functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.config = CliConfig(verbose=True)
        self.handlers = CommandHandlers(self.config)
    
    def teardown_method(self):
        """Clean up test environment"""
        if self.handlers:
            self.handlers.cleanup()
    
    @patch.object(HttpClient, 'check_connection')
    @patch.object(HttpClient, 'open_file')
    @patch('os.path.exists')
    @patch('os.path.abspath')
    def test_handle_file_open_success(self, mock_abspath, mock_exists, mock_open_file, mock_check_connection):
        """Test successful file opening"""
        mock_abspath.return_value = '/abs/path/to/file.py'
        mock_exists.return_value = True
        mock_check_connection.return_value = True
        mock_open_file.return_value = {'status': 'success', 'file_id': 'file123'}
        
        result = self.handlers.handle_file_open('/path/to/file.py')
        assert result is True
        mock_open_file.assert_called_once_with('/abs/path/to/file.py', None)
    
    @patch.object(HttpClient, 'check_connection')
    @patch('os.path.exists')
    def test_handle_file_open_file_not_exists(self, mock_exists, mock_check_connection):
        """Test file opening when file doesn't exist"""
        mock_exists.return_value = False
        mock_check_connection.return_value = True
        
        result = self.handlers.handle_file_open('/nonexistent/file.py')
        assert result is False
    
    @patch.object(HttpClient, 'check_connection')
    @patch.object(HttpClient, 'create_terminal')
    def test_handle_terminal_create_success(self, mock_create_terminal, mock_check_connection):
        """Test successful terminal creation"""
        mock_check_connection.return_value = True
        mock_create_terminal.return_value = {'terminal_id': 'term123', 'status': 'active'}
        
        result = self.handlers.handle_terminal_create()
        assert result is True
        mock_create_terminal.assert_called_once()
    
    @patch.object(HttpClient, 'check_connection')
    def test_handle_terminal_create_no_connection(self, mock_check_connection):
        """Test terminal creation when backend is disconnected"""
        mock_check_connection.return_value = False
        
        result = self.handlers.handle_terminal_create()
        assert result is False
    
    @patch.object(HttpClient, 'check_connection')
    @patch.object(HttpClient, 'get_terminal_list')
    def test_handle_terminal_list_success(self, mock_get_terminal_list, mock_check_connection):
        """Test successful terminal listing"""
        mock_check_connection.return_value = True
        mock_get_terminal_list.return_value = [
            {'terminal_id': 'term1', 'status': 'active', 'workspace_id': 'ws1'},
            {'terminal_id': 'term2', 'status': 'active', 'workspace_id': 'ws2'}
        ]
        
        result = self.handlers.handle_terminal_list()
        assert result is True
        mock_get_terminal_list.assert_called_once()
    
    @patch.object(HttpClient, 'check_connection')
    @patch.object(HttpClient, 'get_terminal_list')
    def test_handle_terminal_list_empty(self, mock_get_terminal_list, mock_check_connection):
        """Test terminal listing when no terminals exist"""
        mock_check_connection.return_value = True
        mock_get_terminal_list.return_value = []
        
        result = self.handlers.handle_terminal_list()
        assert result is True
    
    @patch.object(HttpClient, 'check_connection')
    @patch.object(HttpClient, 'get_workspace_list')
    def test_handle_workspace_list_success(self, mock_get_workspace_list, mock_check_connection):
        """Test successful workspace listing"""
        mock_check_connection.return_value = True
        mock_get_workspace_list.return_value = [
            {'workspace_id': 'ws1', 'name': 'Workspace 1', 'active': True},
            {'workspace_id': 'ws2', 'name': 'Workspace 2', 'active': False}
        ]
        
        result = self.handlers.handle_workspace_list()
        assert result is True
        mock_get_workspace_list.assert_called_once()
    
    @patch.object(HttpClient, 'check_connection')
    @patch.object(HttpClient, 'get_workspace_info')
    def test_handle_workspace_info_success(self, mock_get_workspace_info, mock_check_connection):
        """Test successful workspace info retrieval"""
        mock_check_connection.return_value = True
        mock_get_workspace_info.return_value = {
            'workspace_id': 'ws1',
            'name': 'Test Workspace',
            'status': 'active',
            'files': [{'path': '/test/file.py', 'modified': False}],
            'terminals': [{'terminal_id': 'term1', 'status': 'active'}]
        }
        
        result = self.handlers.handle_workspace_info('ws1')
        assert result is True
        mock_get_workspace_info.assert_called_once_with('ws1')
    
    @patch.object(HttpClient, 'check_connection')
    @patch.object(HttpClient, 'list_directory')
    @patch('os.path.exists')
    @patch('os.path.abspath')
    def test_handle_file_list_success(self, mock_abspath, mock_exists, mock_list_directory, mock_check_connection):
        """Test successful directory listing"""
        mock_abspath.return_value = '/abs/path/to/dir'
        mock_exists.return_value = True
        mock_check_connection.return_value = True
        mock_list_directory.return_value = [
            {'name': 'file1.py', 'type': 'file', 'size': 100},
            {'name': 'subdir', 'type': 'directory', 'size': 0}
        ]
        
        result = self.handlers.handle_file_list('/path/to/dir')
        assert result is True
        mock_list_directory.assert_called_once_with('/abs/path/to/dir')
    
    @patch.object(HttpClient, 'check_connection')
    @patch.object(HttpClient, 'get_workspace_list')
    @patch.object(HttpClient, 'get_terminal_list')
    def test_handle_status_success(self, mock_get_terminal_list, mock_get_workspace_list, mock_check_connection):
        """Test successful status check"""
        mock_check_connection.return_value = True
        mock_get_workspace_list.return_value = [{'workspace_id': 'ws1'}]
        mock_get_terminal_list.return_value = [{'terminal_id': 'term1'}]
        
        result = self.handlers.handle_status()
        assert result is True
        mock_check_connection.assert_called_once()
        mock_get_workspace_list.assert_called_once()
        mock_get_terminal_list.assert_called_once()
    
    @patch.object(HttpClient, 'check_connection')
    def test_handle_status_no_connection(self, mock_check_connection):
        """Test status check when backend is disconnected"""
        mock_check_connection.return_value = False
        
        result = self.handlers.handle_status()
        assert result is False


class TestIcpyCLI:
    """Test CLI interface functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.cli = IcpyCLI()
    
    def test_create_parser(self):
        """Test argument parser creation"""
        parser = self.cli.create_parser()
        assert parser is not None
        assert parser.prog == 'icpy'
    
    def test_parser_file_argument(self):
        """Test file argument parsing"""
        parser = self.cli.create_parser()
        args = parser.parse_args(['test.py'])
        assert args.file == 'test.py'
    
    def test_parser_terminal_argument(self):
        """Test terminal argument parsing"""
        parser = self.cli.create_parser()
        args = parser.parse_args(['--terminal'])
        assert args.terminal is True
    
    def test_parser_workspace_argument(self):
        """Test workspace argument parsing"""
        parser = self.cli.create_parser()
        args = parser.parse_args(['--workspace', 'list'])
        assert args.workspace == 'list'
    
    def test_parser_interactive_argument(self):
        """Test interactive argument parsing"""
        parser = self.cli.create_parser()
        args = parser.parse_args(['--interactive'])
        assert args.interactive is True
    
    def test_parser_verbose_argument(self):
        """Test verbose argument parsing"""
        parser = self.cli.create_parser()
        args = parser.parse_args(['--verbose'])
        assert args.verbose is True
    
    def test_parser_backend_url_argument(self):
        """Test backend URL argument parsing"""
        parser = self.cli.create_parser()
        args = parser.parse_args(['--backend-url', 'http://localhost:9000'])
        assert args.backend_url == 'http://localhost:9000'
    
    def test_update_config(self):
        """Test configuration update from arguments"""
        parser = self.cli.create_parser()
        args = parser.parse_args(['--backend-url', 'http://localhost:9000', '--verbose'])
        
        self.cli.update_config(args)
        assert self.cli.config.backend_url == 'http://localhost:9000'
        assert self.cli.config.verbose is True
        assert self.cli.handlers is not None
    
    @patch.object(CommandHandlers, 'handle_file_open')
    def test_run_file_open(self, mock_handle_file_open):
        """Test running file open command"""
        mock_handle_file_open.return_value = True
        
        result = self.cli.run(['test.py'])
        assert result == 0
        mock_handle_file_open.assert_called_once_with('test.py', None)
    
    @patch.object(CommandHandlers, 'handle_terminal_create')
    def test_run_terminal_create(self, mock_handle_terminal_create):
        """Test running terminal create command"""
        mock_handle_terminal_create.return_value = True
        
        result = self.cli.run(['--terminal'])
        assert result == 0
        mock_handle_terminal_create.assert_called_once_with(None)
    
    @patch.object(CommandHandlers, 'handle_workspace_list')
    def test_run_workspace_list(self, mock_handle_workspace_list):
        """Test running workspace list command"""
        mock_handle_workspace_list.return_value = True
        
        result = self.cli.run(['--workspace', 'list'])
        assert result == 0
        mock_handle_workspace_list.assert_called_once()
    
    @patch.object(CommandHandlers, 'handle_status')
    def test_run_status(self, mock_handle_status):
        """Test running status command"""
        mock_handle_status.return_value = True
        
        result = self.cli.run(['--status'])
        assert result == 0
        mock_handle_status.assert_called_once()
    
    @patch.object(CommandHandlers, 'handle_interactive_mode')
    def test_run_interactive(self, mock_handle_interactive_mode):
        """Test running interactive mode"""
        mock_handle_interactive_mode.return_value = True
        
        result = self.cli.run(['--interactive'])
        assert result == 0
        mock_handle_interactive_mode.assert_called_once()
    
    @patch.object(CommandHandlers, 'handle_file_open')
    def test_run_file_open_failure(self, mock_handle_file_open):
        """Test running file open command with failure"""
        mock_handle_file_open.return_value = False
        
        result = self.cli.run(['test.py'])
        assert result == 1
        mock_handle_file_open.assert_called_once_with('test.py', None)


class TestCLIIntegration:
    """Integration tests for CLI functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.backend_process = None
        self.cli_script = os.path.join(os.path.dirname(__file__), '..', 'icpy_cli.py')
    
    def teardown_method(self):
        """Clean up test environment"""
        if self.backend_process:
            self.backend_process.terminate()
            self.backend_process.wait()
    
    def test_cli_help(self):
        """Test CLI help command"""
        try:
            result = subprocess.run(
                [sys.executable, self.cli_script, '--help'],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert result.returncode == 0
            assert 'icpy' in result.stdout
            assert 'Command-line interface' in result.stdout
        except FileNotFoundError:
            pytest.skip("CLI script not found")
    
    def test_cli_status_no_backend(self):
        """Test CLI status when backend is not running"""
        try:
            result = subprocess.run(
                [sys.executable, self.cli_script, '--status'],
                capture_output=True,
                text=True,
                timeout=10
            )
            # Should fail gracefully when backend is not running
            assert 'Backend: Disconnected' in result.stdout or result.returncode != 0
        except FileNotFoundError:
            pytest.skip("CLI script not found")
    
    def test_cli_file_open_nonexistent(self):
        """Test CLI file open with nonexistent file"""
        try:
            result = subprocess.run(
                [sys.executable, self.cli_script, '/nonexistent/file.py'],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert result.returncode != 0
            assert 'Error' in result.stdout or 'does not exist' in result.stdout
        except FileNotFoundError:
            pytest.skip("CLI script not found")
    
    def test_cli_invalid_command(self):
        """Test CLI with invalid command"""
        try:
            result = subprocess.run(
                [sys.executable, self.cli_script, '--invalid-command'],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert result.returncode != 0
            assert 'error' in result.stderr.lower() or 'unrecognized' in result.stderr.lower()
        except FileNotFoundError:
            pytest.skip("CLI script not found")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
