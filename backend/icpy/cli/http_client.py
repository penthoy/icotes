"""
HTTP Client for icpy CLI

This module provides HTTP client functionality for communicating with the icpy backend
REST API from the command-line interface.

Key Features:
- HTTP requests to icpy backend REST API
- JSON-RPC protocol support over HTTP
- Error handling and response processing
- Authentication and session management
- Request timeout and retry logic

Author: GitHub Copilot
Date: July 16, 2025
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from urllib.parse import urlparse, quote
import os

import aiohttp
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


# Keep helper at module scope so default_factory can call it
def _resolve_backend_url_from_env() -> str:
    host = os.getenv("BACKEND_HOST") or os.getenv("HOSTNAME")
    port = os.getenv("PORT")
    site = os.getenv("SITE_URL")

    # If SITE_URL looks like a full URL, extract components
    if not host and site:
        parsed = urlparse(site if "://" in site else f"http://{site}")
        host = parsed.hostname or host
        port = port or (str(parsed.port) if parsed.port else None)
        scheme = parsed.scheme or "http"
    else:
        scheme = "http"

    host = host or "localhost"
    port = port or "8000"
    return f"{scheme}://{host}:{port}"


@dataclass
class CliConfig:
    """Configuration for CLI operations"""
    # Resolution order:
    # 1) ICPY_BACKEND_URL (full URL)
    # 2) BACKEND_HOST or HOSTNAME (host only) + PORT
    # 3) SITE_URL (extract host/port if it's a URL) + PORT
    # 4) http://localhost:8000
    backend_url: str = field(default_factory=lambda: (
        os.getenv("ICPY_BACKEND_URL")
        or _resolve_backend_url_from_env()
    ))
    timeout: int = 30
    retry_count: int = 3
    retry_delay: float = 1.0
    api_key: Optional[str] = None
    verbose: bool = False


class HttpClient:
    """
    HTTP client for communicating with icpy backend REST API
    
    Provides methods for making HTTP requests to the backend services
    with proper error handling, retries, and JSON-RPC protocol support.
    """
    
    def __init__(self, config: CliConfig):
        """
        Initialize HTTP client with configuration
        
        Args:
            config: Configuration object containing backend URL and other settings
        """
        self.config = config
        self.session = None
        self._setup_session()
    
    def _setup_session(self) -> None:
        """
        Set up HTTP session with retry strategy and authentication
        """
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.retry_count,
            backoff_factor=self.config.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set up headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'icpy-cli/1.0'
        })
        
        # Add authentication if provided
        if self.config.api_key:
            self.session.headers['Authorization'] = f'Bearer {self.config.api_key}'
    
    def check_connection(self) -> bool:
        """
        Check if the backend is reachable
        
        Returns:
            bool: True if backend is reachable, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.config.backend_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            if self.config.verbose:
                logger.error(f"Connection check failed: {e}")
            return False
    
    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make HTTP request to backend API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request data (for POST/PUT requests)
            
        Returns:
            Dict containing response data
            
        Raises:
            Exception: On request failure or HTTP error
        """
        url = f"{self.config.backend_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=self.config.timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, timeout=self.config.timeout)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, timeout=self.config.timeout)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, timeout=self.config.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Handle different response content types
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.json()
            else:
                return {'data': response.text}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            raise Exception(f"Request failed: {e}")
    
    def json_rpc_request(self, method: str, params: Optional[Dict] = None, 
                        request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Make JSON-RPC request to backend
        
        Args:
            method: JSON-RPC method name
            params: Method parameters
            request_id: Request ID (generated if not provided)
            
        Returns:
            Dict containing JSON-RPC response
            
        Raises:
            Exception: On RPC error or HTTP error
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": request_id
        }
        
        response = self.make_request('POST', '/api/jsonrpc', request_data)
        
        # Handle JSON-RPC errors
        if 'error' in response:
            error = response['error']
            raise Exception(f"JSON-RPC Error {error.get('code', 'Unknown')}: {error.get('message', 'Unknown error')}")
        
        return response.get('result', {})
    
    def get_workspace_list(self) -> List[Dict[str, Any]]:
        """
        Get list of available workspaces
        
        Returns:
            List of workspace information
        """
        response = self.make_request('GET', '/api/workspaces')
        return response.get('data', [])
    
    def get_workspace_info(self, workspace_id: str) -> Dict[str, Any]:
        """
        Get information about a specific workspace
        
        Args:
            workspace_id: Workspace identifier
            
        Returns:
            Workspace information
        """
        return self.make_request('GET', f'/api/workspaces/{workspace_id}')
    
    def open_file(self, file_path: str, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Open a file in the editor
        
        Args:
            file_path: Path to the file to open
            workspace_id: Optional workspace ID
            
        Returns:
            Operation result
        """
        # For now, we'll just get the file content to simulate opening
        return self.get_file_content(file_path)
    
    def create_terminal(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new terminal session
        
        Args:
            workspace_id: Optional workspace ID
            
        Returns:
            Terminal session information
        """
        data = {'workspace_id': workspace_id} if workspace_id else {}
        response = self.make_request('POST', '/api/terminals', data)
        return response.get('data', {})
    
    def get_terminal_list(self) -> List[Dict[str, Any]]:
        """
        Get list of active terminal sessions
        
        Returns:
            List of terminal session information
        """
        response = self.make_request('GET', '/api/terminals')
        return response.get('data', [])
    
    def send_terminal_input(self, terminal_id: str, input_data: str) -> Dict[str, Any]:
        """
        Send input to a terminal session
        
        Args:
            terminal_id: Terminal session ID
            input_data: Input data to send
            
        Returns:
            Operation result
        """
        data = {'input': input_data}
        return self.make_request('POST', f'/api/terminals/{terminal_id}/input', data)
    
    def get_file_content(self, file_path: str) -> Dict[str, Any]:
        """
        Get content of a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            File content and metadata
        """
        return self.make_request('GET', f'/api/files/content?path={quote(file_path, safe="")}')
    
    def save_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Save content to a file
        
        Args:
            file_path: Path to the file
            content: File content to save
            
        Returns:
            Operation result
        """
        data = {
            'path': file_path,
            'content': content
        }
        return self.make_request('POST', '/api/files/save', data)
    
    def list_directory(self, dir_path: str) -> List[Dict[str, Any]]:
        """
        List contents of a directory
        
        Args:
            dir_path: Directory path
            
        Returns:
            Directory contents
        """
        return self.make_request('GET', f'/api/files/list?path={quote(dir_path, safe="")}')
    
    def close(self) -> None:
        """
        Close HTTP session and cleanup resources
        """
        if self.session:
            self.session.close()
            self.session = None
