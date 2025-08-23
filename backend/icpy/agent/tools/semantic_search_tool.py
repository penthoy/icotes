"""
Semantic search tool for agents using ripgrep with smart fallbacks.

Phases implemented:
- Phase 1: Use workspace service root; add filename search; case-insensitive fallback; hidden files option.
- Phase 2: Tokenized AND regex, OR tokens fallback; context lines and max results controls; mode selection.
- Phase 3: Root selection (workspace or repo via env), better scope handling.
"""

import asyncio
import logging
import os
import subprocess
import re
from typing import Dict, Any, Optional, List, Tuple
from .base_tool import BaseTool, ToolResult
from ...services import get_workspace_service

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
                },
                "includeHidden": {
                    "type": "boolean",
                    "description": "Include hidden files (adds --hidden)"
                },
                "contextLines": {
                    "type": "integer",
                    "description": "Number of context lines to include in broadened passes (default 2)"
                },
                "maxResults": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 50)"
                },
                "mode": {
                    "type": "string",
                    "enum": ["smart", "content", "filename", "regex"],
                    "description": "Search mode (smart=auto)"
                },
                "root": {
                    "type": "string",
                    "enum": ["workspace", "repo"],
                    "description": "Select root base directory (workspace=default, repo uses PROJECT_ROOT env if set)"
                }
            },
            "required": ["query"]
        }
    
    def _build_ripgrep_command(self, query: str, workspace_root: str, scope: Optional[str], file_types: Optional[List[str]], include_hidden: bool = False) -> List[str]:
        """Build ripgrep command with appropriate flags"""
        cmd = ["rg", "-n", "-H", "--no-heading"]
        
        # Use fixed-string mode by default for deterministic behavior
        cmd.append("-F")
        
        # Hidden files if requested
        if include_hidden:
            cmd.append("--hidden")
        
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
    
    def _build_path(self, base_root: str, scope: Optional[str]) -> str:
        """Resolve search path from base root and optional scope."""
        if scope:
            if os.path.isabs(scope):
                return scope
            # allow 'workspace/...' style inputs by removing prefix
            if scope.startswith('workspace/') or scope.startswith('workspace\\'):
                scope = scope.split('/', 1)[1] if '/' in scope else scope.split('\\', 1)[1]
            return os.path.join(base_root, scope)
        return base_root
    
    def _parse_ripgrep_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse ripgrep -n output (file:line:content) or filename-only lists."""
        results: List[Dict[str, Any]] = []
        lines = output.strip().split('\n') if output.strip() else []
        
        for line in lines:
            if not line:
                continue
            # filename-only (e.g., rg --files)
            if ':' not in line:
                results.append({"file": line, "line": None, "snippet": None})
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
        return results
    
    def _cap_results(self, results: List[Dict[str, Any]], max_results: int) -> List[Dict[str, Any]]:
        # Cap at non-negative limit; 0 should return an empty list
        return results[: max(0, int(max_results))]
    
    def _looks_like_filename(self, query: str) -> bool:
        """Heuristic to decide if query looks like a filename/path."""
        if '/' in query or '\\' in query:
            return True
        # has an extension and reasonable length
        if '.' in query:
            last = query.split('.')[-1]
            if 1 <= len(last) <= 6 and len(query) <= 128:
                return True
        return False
    
    def _tokenize(self, query: str) -> List[str]:
        tokens = re.split(r"[^A-Za-z0-9_]+", query)
        return [t for t in tokens if len(t) >= 3]
    
    def _and_regex(self, tokens: List[str]) -> str:
        parts = [re.escape(t) for t in tokens]
        return ".*".join(parts)
    
    async def _get_base_root(self, root: Optional[str]) -> str:
        """Determine base root directory to search."""
        try:
            ws = await get_workspace_service()
            workspace_root = None
            # Some tests mock get_workspace_root
            if hasattr(ws, 'get_workspace_root'):
                try:
                    maybe_root = ws.get_workspace_root()
                    # Support both sync and async mocks/implementations
                    if asyncio.iscoroutine(maybe_root):
                        workspace_root = await maybe_root
                    else:
                        workspace_root = maybe_root
                except Exception:
                    workspace_root = None
            # Fallback to env or default workspace dir
            if not workspace_root:
                env_root = os.environ.get('WORKSPACE_ROOT')
                if env_root:
                    workspace_root = env_root
                else:
                    backend_dir = os.path.dirname(os.path.abspath(__file__))
                    workspace_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(backend_dir)))), 'workspace')
        except Exception:
            # If service unavailable, use environment/default
            env_root = os.environ.get('WORKSPACE_ROOT')
            if env_root:
                workspace_root = env_root
            else:
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                workspace_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(backend_dir)))), 'workspace')
        
        if root == 'repo':
            repo_root = os.environ.get('PROJECT_ROOT')
            if repo_root:
                return repo_root
        return workspace_root
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the semantic search"""
        try:
            query = kwargs.get("query")
            scope = kwargs.get("scope")
            file_types = kwargs.get("fileTypes")
            include_hidden = bool(kwargs.get("includeHidden", False))
            context_lines = int(kwargs.get("contextLines", 2) or 2)
            max_results = int(kwargs.get("maxResults", 50) or 50)
            mode = kwargs.get("mode", "smart")
            root = kwargs.get("root", "workspace")
            
            if query is None:
                return ToolResult(success=False, error="query is required")
            
            if not query.strip():
                return ToolResult(success=False, error="query cannot be empty")
            
            # Determine base root and full search path
            base_root = await self._get_base_root(root)
            search_path = self._build_path(base_root, scope)
            
            # Mode: filename-only detection when smart or filename (but not content mode)
            if mode in ("smart", "filename") and mode != "content" and self._looks_like_filename(query):
                cmd = ["rg", "--files"]
                if include_hidden:
                    cmd.append("--hidden")
                # use glob pattern to match anywhere
                glob = f"*{query}*"
                cmd.extend(["-g", glob, search_path])
                logger.info(f"Executing filename search: {' '.join(cmd)}")
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if r.returncode == 0 and r.stdout.strip():
                    results = self._parse_ripgrep_output(r.stdout)
                    return ToolResult(success=True, data=self._cap_results(results, max_results))
                # else continue to content passes
            
            # Content search passes
            passes: List[Tuple[List[str], str]] = []
            
            # If regex mode, use the query as-is in a regex pass and skip fixed-string passes
            if mode == "regex":
                cmd_regex = ["rg", "-n", "-H", "--no-heading", "-C", str(context_lines), "-e", query]
                if include_hidden:
                    cmd_regex.append("--hidden")
                if file_types:
                    for file_type in file_types:
                        cmd_regex.extend(["-t", file_type.lstrip('.')])
                cmd_regex.append(search_path)
                passes.append((cmd_regex, "regex"))
            else:
                # Pass 1: exact fixed string, case-sensitive
                cmd1 = self._build_ripgrep_command(query, base_root, scope, file_types, include_hidden)
                # _build_ripgrep_command already includes the search path
                passes.append((cmd1, "exact"))
                
                # Pass 2: case-insensitive exact
                cmd2 = [c for c in cmd1]
                if "-i" not in cmd2:
                    cmd2.insert(1, "-i")
                passes.append((cmd2, "ci_exact"))
            
            # Tokenization for later passes (skip for regex mode)
            tokens = [] if mode == "regex" else self._tokenize(query)
            if tokens:
                # Pass 3: AND ordered regex with context lines (case-insensitive)
                and_pattern = self._and_regex(tokens)
                cmd3 = ["rg", "-n", "-H", "--no-heading", "-i", "-C", str(context_lines), "-e", and_pattern]
                if include_hidden:
                    cmd3.append("--hidden")
                if file_types:
                    for file_type in file_types:
                        clean = file_type.lstrip('.')
                        cmd3.extend(["-t", clean])
                cmd3.append(search_path)
                passes.append((cmd3, "and_regex"))
                
                # Pass 4: OR tokens with multiple -e flags
                cmd4 = ["rg", "-n", "-H", "--no-heading", "-i", "-C", str(context_lines)]
                if include_hidden:
                    cmd4.append("--hidden")
                if file_types:
                    for file_type in file_types:
                        clean = file_type.lstrip('.')
                        cmd4.extend(["-t", clean])
                for t in tokens:
                    cmd4.extend(["-e", re.escape(t)])
                cmd4.append(search_path)
                passes.append((cmd4, "or_tokens"))
            
            # Execute passes until results found or all tried
            for cmd, label in passes:
                try:
                    logger.info(f"Executing search ({label}): {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                except subprocess.TimeoutExpired:
                    continue
                if result.returncode == 0 and result.stdout is not None:
                    results = self._parse_ripgrep_output(result.stdout)
                    return ToolResult(success=True, data=self._cap_results(results, max_results))
                elif result.returncode not in (0, 1):
                    error_msg = result.stderr if result.stderr else f"ripgrep failed with code {result.returncode}"
                    return ToolResult(success=False, error=error_msg)
            
            # No matches
            return ToolResult(success=True, data=[])
                
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error="Search timed out after 30 seconds")
        except FileNotFoundError:
            return ToolResult(success=False, error="ripgrep (rg) not found. Please install ripgrep.")
        except Exception as e:
            logger.error(f"Error executing search for query '{kwargs.get('query')}': {e}")
            return ToolResult(success=False, error=f"Search failed: {str(e)}") 