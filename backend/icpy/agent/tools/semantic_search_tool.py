"""
Semantic search tool for agents using ripgrep
"""

import asyncio
import logging
import os
import subprocess
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)




class SemanticSearchTool(BaseTool):
    """Tool for searching code using ripgrep"""
    
    def __init__(self):
        super().__init__()
        self.name = "semantic_search"
        self.description = "Search for code or files using natural language descriptions"
        self.parameters = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (uses fixed-string matching by default)"
                },
                "scope": {
                    "type": "string",
                    "description": "Directory scope to search within (optional)"
                },
                "fileTypes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File extensions to filter by (optional)"
                }
            },
            "required": ["query"]
        }
    
    def _build_ripgrep_command(self, query: str, workspace_root: str, scope: Optional[str], file_types: Optional[List[str]]) -> List[str]:
        """Build ripgrep command with appropriate flags"""
        cmd = ["rg", "-n", "-H", "--no-heading"]
        
        # Use fixed-string mode by default for deterministic behavior
        cmd.append("-F")
        
        # Add file type filters
        if file_types:
            for file_type in file_types:
                # Remove leading dot if present
                clean_type = file_type.lstrip('.')
                cmd.extend(["-t", clean_type])
        
        # Add the query
        cmd.append(query)
        
        # Add search path
        if scope:
            # Handle absolute paths
            if os.path.isabs(scope):
                search_path = scope
            else:
                # For relative paths, check if they already include workspace
                if scope.startswith('workspace/') or scope.startswith('workspace\\'):
                    # Remove 'workspace/' prefix and join with workspace_root
                    relative_scope = scope[10:]  # Remove 'workspace/' (10 chars)
                    search_path = os.path.join(workspace_root, relative_scope)
                elif scope == 'workspace':
                    search_path = workspace_root
                else:
                    # Normal relative path from workspace root
                    search_path = os.path.join(workspace_root, scope)
        else:
            search_path = workspace_root
        cmd.append(search_path)
        
        return cmd
    
    def _parse_ripgrep_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse ripgrep output into structured results"""
        results = []
        lines = output.strip().split('\n') if output.strip() else []
        
        for line in lines:
            if not line:
                continue
                
            # ripgrep format: file:line:content
            parts = line.split(':', 2)
            if len(parts) >= 3:
                try:
                    file_path = parts[0]
                    line_num = int(parts[1])
                    snippet = parts[2]
                    
                    results.append({
                        "file": file_path,
                        "line": line_num,
                        "snippet": snippet
                    })
                except (ValueError, IndexError):
                    # Skip malformed lines
                    continue
        
        # Cap results at 50
        return results[:50]
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the semantic search"""
        try:
            query = kwargs.get("query")
            scope = kwargs.get("scope")
            file_types = kwargs.get("fileTypes")
            
            if query is None:
                return ToolResult(success=False, error="query is required")
            
            if not query.strip():
                return ToolResult(success=False, error="query cannot be empty")
            
            # Get workspace root from environment or default
            workspace_root = os.environ.get('WORKSPACE_ROOT')
            if not workspace_root:
                # Default to workspace directory relative to backend
                # From: /path/to/icotes/backend/icpy/agent/tools -> /path/to/icotes/workspace
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                workspace_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(backend_dir)))), 'workspace')
            
            # Build ripgrep command
            cmd = self._build_ripgrep_command(query, workspace_root, scope, file_types)
            
            logger.info(f"Executing search: {' '.join(cmd)}")
            
            # Execute ripgrep
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            # Handle different return codes
            if result.returncode == 0:
                # Found matches
                results = self._parse_ripgrep_output(result.stdout)
                return ToolResult(success=True, data=results)
            elif result.returncode == 1:
                # No matches found (this is normal)
                return ToolResult(success=True, data=[])
            else:
                # Error occurred
                error_msg = result.stderr if result.stderr else f"ripgrep failed with code {result.returncode}"
                return ToolResult(success=False, error=error_msg)
                
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error="Search timed out after 30 seconds")
        except FileNotFoundError:
            return ToolResult(success=False, error="ripgrep (rg) not found. Please install ripgrep.")
        except Exception as e:
            logger.error(f"Error executing search for query '{kwargs.get('query')}': {e}")
            return ToolResult(success=False, error=f"Search failed: {str(e)}") 