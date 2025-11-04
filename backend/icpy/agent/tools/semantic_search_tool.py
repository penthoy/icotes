"""
Semantic search tool for agents using ripgrep with smart fallbacks.

Phases implemented:
- Phase 1: Use workspace service root; add filename search; case-insensitive fallback; hidden files option.
- Phase 2: Tokenized AND regex, OR tokens fallback; context lines and max results controls; mode selection.
- Phase 3: Root selection (workspace or repo via env), better scope handling.
- Phase 7 (Hop Support): Uses ContextRouter to work with active hop context (local or remote)
"""

import asyncio
import logging
import os
import subprocess
import re
from typing import Dict, Any, Optional, List, Tuple
from .base_tool import BaseTool, ToolResult
from .context_helpers import get_contextual_filesystem
from ...services import get_workspace_service
from icpy.services.path_utils import get_display_path_info

logger = logging.getLogger(__name__)




class SemanticSearchTool(BaseTool):
    """Tool for searching code using ripgrep"""
    
    def __init__(self):
        super().__init__()
        self.name = "semantic_search"
        self.description = (
            "Search for code or files using ripgrep with smart fallbacks. "
            "Returns namespaced file paths (pathInfo) for each match."
        )
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
                    "description": "Search mode: smart (auto), content, filename, or regex"
                },
                "root": {
                    "type": "string",
                    "enum": ["workspace", "repo"],
                    "description": "Select base directory: workspace (default) or repo (uses PROJECT_ROOT if set)."
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

    def _python_filename_fallback(self, query: str, base_root: str, include_hidden: bool, max_results: int, file_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Fallback filename search using os.walk when ripgrep yields nothing.

        Enhancements:
        - Supports optional extension filters passed via file_types (e.g., ["png", "jpg"]).
        - Performs case-insensitive substring match on file names.
        - If query is empty or '.'/'.*', lists first N files respecting filters.
        """
        results: List[Dict[str, Any]] = []
        try:
            if not os.path.isdir(base_root):
                return []
            q = (query or '').strip()
            list_all = q in ('.', '.*') or q == ''
            qlower = q.lower()

            # Normalize extensions (no leading dot, lowercase)
            exts: Optional[List[str]] = None
            if file_types:
                exts = [e.lstrip('.').lower() for e in file_types if isinstance(e, str) and e.strip()]

            for root_dir, dirs, files in os.walk(base_root):
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                for fname in files:
                    if not include_hidden and fname.startswith('.'):
                        continue
                    if exts and not any(fname.lower().endswith('.' + e) for e in exts):
                        continue
                    if list_all or qlower in fname.lower():
                        full = os.path.join(root_dir, fname)
                        results.append({"file": full, "line": None, "snippet": None})
                        if len(results) >= max(0, int(max_results)):
                            return results
            return results
        except Exception:
            return []
    
    async def _get_base_root(self, root: Optional[str]) -> str:
        """Determine base root directory to search with robust existence fallback."""
        def _derive_workspace_from_repo() -> str:
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(backend_dir))))
            return os.path.join(repo_root, 'workspace')

        workspace_root = None
        try:
            ws = await get_workspace_service()
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
        except Exception:
            workspace_root = None

        # Environment override
        if not workspace_root:
            workspace_root = os.environ.get('WORKSPACE_ROOT')

        # Derive from repository layout
        if not workspace_root:
            workspace_root = _derive_workspace_from_repo()

        # If nothing resolved yet, derive from repo layout
        # Note: Do not override explicit service/env-provided roots even if they don't exist (tests may mock these)
        if not workspace_root:
            workspace_root = _derive_workspace_from_repo()

        # repo root selection
        if root == 'repo':
            repo_root = os.environ.get('PROJECT_ROOT')
            if repo_root:
                return repo_root
            # Fallback to repo root derived from backend path
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(backend_dir))))

        return workspace_root
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the semantic search
        
        Phase 7 Update: Uses context-aware filesystem to support both local and remote (hop) searching.
        For local: Uses ripgrep for fast content search
        For remote: Uses filesystem service's search_files method
        """
        query = kwargs.get("query")
        scope = kwargs.get("scope")
        file_types = kwargs.get("fileTypes")
        include_hidden = bool(kwargs.get("includeHidden", False))
        context_lines = int(kwargs.get("contextLines", 2) or 2)
        if context_lines < 0:
            context_lines = 0
        max_results = int(kwargs.get("maxResults", 50) or 50)
        mode = kwargs.get("mode", "smart")
        root = kwargs.get("root", "workspace")
        
        if query is None:
            return ToolResult(success=False, error="query is required")
        
        if not query.strip():
            return ToolResult(success=False, error="query cannot be empty")
        
        # Phase 7: Check if we're in a remote context (hopped)
        try:
            from .context_helpers import get_current_context
            context = await get_current_context()
            is_remote = context.get("contextId") != "local" and context.get("status") == "connected"
            logger.info(f"[SemanticSearch] Context: {context['contextId']}, remote={is_remote}, status={context.get('status')}")
        except Exception as e:
            logger.info(f"[SemanticSearch] Could not determine context: {e}")
            is_remote = False
        
        # Phase 7: Use remote filesystem search when available; fallback to terminal strategy
        if is_remote:
            logger.info(f"[SemanticSearch] Using remote context for query: {query}, fileTypes={file_types}, mode={mode}")
            try:
                # Prefer context-aware filesystem's own search capability if present (unit-test friendly)
                fs = await get_contextual_filesystem()
                if hasattr(fs, 'search_files') and callable(getattr(fs, 'search_files')):
                    logger.info("[SemanticSearch] Using filesystem.search_files() remote strategy")
                    # Note: RemoteFileSystemAdapter.search_files doesn't accept 'scope' parameter
                    # The search is always relative to the current working directory
                    raw = await fs.search_files(
                        query=query,
                        search_content=True,
                        file_types=file_types,
                        max_results=max_results
                    )
                    results: List[Dict[str, Any]] = []
                    # Normalize results from adapter into common shape
                    if isinstance(raw, list):
                        for item in raw[: max(0, int(max_results))]:
                            try:
                                if isinstance(item, dict):
                                    fi = item.get('file_info') or {}
                                    path = fi.get('path') or item.get('path') or item.get('file')
                                    snippet = None
                                    matches = item.get('matches')
                                    if isinstance(matches, list) and matches:
                                        snippet = str(matches[0])
                                    results.append({
                                        'file': path,
                                        'line': None,
                                        'snippet': snippet,
                                    })
                                elif isinstance(item, str):
                                    results.append({'file': item, 'line': None, 'snippet': None})
                            except Exception:
                                continue
                    return ToolResult(success=True, data=self._cap_results(results, max_results))
            except Exception as e:
                logger.error(f"[SemanticSearch] Remote filesystem search failed: {e}", exc_info=True)
                return ToolResult(success=False, error=f"Remote search failed: {str(e)}")

            # Fallback to terminal-based remote search if filesystem route not available
            logger.info("[SemanticSearch] Falling back to terminal-based remote search strategy")
            return await self._execute_remote_search(query, scope, file_types, include_hidden, max_results, mode)
        
        # Local search using ripgrep (original behavior)
        logger.info(f"[SemanticSearch] Using local ripgrep search for query: {query}")
        return await self._execute_local_search(query, scope, file_types, include_hidden, context_lines, mode, max_results, root)
    
    async def _execute_local_search(self, query: str, scope: Optional[str], file_types: Optional[List[str]],
                                    include_hidden: bool, context_lines: int, mode: str, max_results: int, root: str = "workspace") -> ToolResult:
        """Execute search using local ripgrep (original behavior)"""
        try:
            # Determine base root and full search path
            base_root = await self._get_base_root(root)
            search_path = self._build_path(base_root, scope)
            
            # Do not require actual existence checks here; subprocess is mocked in tests
            
            # Mode: filename-only detection when smart or filename (but not content mode)
            if mode in ("smart", "filename") and mode != "content" and self._looks_like_filename(query):
                cmd = ["rg", "--files"]
                if include_hidden:
                    cmd.append("--hidden")
                # use glob pattern to match anywhere; add extension filters if provided
                cmd.extend(["-g", f"*{query}*"])
                if file_types:
                    for ft in file_types:
                        if ft:
                            cmd.extend(["-g", f"*.{ft.lstrip('.')}" ])
                cmd.append(search_path)
                logger.info(f"Executing filename search: {' '.join(cmd)}")
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if r.returncode == 0 and r.stdout.strip():
                    results = self._parse_ripgrep_output(r.stdout)
                    # Enrich with namespaced path info without breaking compatibility
                    for item in results:
                        try:
                            file_abs = item.get("file")
                            if file_abs:
                                path_info = await get_display_path_info(file_abs)
                                item["filePath"] = path_info.get("formatted_path")
                                item["pathInfo"] = path_info
                        except Exception:
                            # Best-effort enrichment; ignore failures
                            pass
                    return ToolResult(success=True, data=self._cap_results(results, max_results))
                # Fallback: Python filename scan if rg returned nothing
                py_results = self._python_filename_fallback(query, search_path, include_hidden, max_results, file_types)
                if py_results:
                    for item in py_results:
                        try:
                            file_abs = item.get("file")
                            if file_abs:
                                path_info = await get_display_path_info(file_abs)
                                item["filePath"] = path_info.get("formatted_path")
                                item["pathInfo"] = path_info
                        except Exception:
                            pass
                    return ToolResult(success=True, data=self._cap_results(py_results, max_results))
                # else continue to content passes

            # NEW: If fileTypes are provided or mode is explicitly 'filename', try a filename scan even
            # when the heuristic doesn't think it's a filename (e.g., query='cat', fileTypes=['png']).
            if (mode in ("smart", "filename") and (file_types or mode == "filename")):
                py_results = self._python_filename_fallback(query, search_path, include_hidden, max_results, file_types)
                if py_results:
                    for item in py_results:
                        try:
                            file_abs = item.get("file")
                            if file_abs:
                                path_info = await get_display_path_info(file_abs)
                                item["filePath"] = path_info.get("formatted_path")
                                item["pathInfo"] = path_info
                        except Exception:
                            pass
                    return ToolResult(success=True, data=self._cap_results(py_results, max_results))
            
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
                    for item in results:
                        try:
                            file_abs = item.get("file")
                            if file_abs:
                                path_info = await get_display_path_info(file_abs)
                                item["filePath"] = path_info.get("formatted_path")
                                item["pathInfo"] = path_info
                        except Exception:
                            pass
                    return ToolResult(success=True, data=self._cap_results(results, max_results))
                elif result.returncode not in (0, 1):
                    error_msg = result.stderr if result.stderr else f"ripgrep failed with code {result.returncode}"
                    return ToolResult(success=False, error=error_msg)
            
            # No matches - last resort filename fallback for broad/short queries or when types provided
            if (mode in ("smart", "filename") and (self._looks_like_filename(query) or file_types)) or query in (".", ".*"):
                py_results = self._python_filename_fallback(query, search_path, include_hidden, max_results, file_types)
                if py_results:
                    for item in py_results:
                        try:
                            file_abs = item.get("file")
                            if file_abs:
                                path_info = await get_display_path_info(file_abs)
                                item["filePath"] = path_info.get("formatted_path")
                                item["pathInfo"] = path_info
                        except Exception:
                            pass
                    return ToolResult(success=True, data=self._cap_results(py_results, max_results))
            return ToolResult(success=True, data=[])
                
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error="Search timed out after 30 seconds")
        except FileNotFoundError:
            return ToolResult(success=False, error="ripgrep (rg) not found. Please install ripgrep.")
        except Exception as e:
            logger.error(f"Error executing local search for query '{query}': {e}")
            return ToolResult(success=False, error=f"Search failed: {str(e)}")
    
    def _escape_shell_arg(self, arg: str) -> str:
        """Escape shell argument to prevent command injection."""
        # Replace single quotes with '\'' (close quote, escaped quote, open quote)
        return "'" + arg.replace("'", "'\\''") + "'"
    
    def _build_ripgrep_remote_cmd(self, query: str, workspace_root: str, file_types: Optional[List[str]], 
                                   include_hidden: bool, max_results: int, mode: str = "content") -> str:
        """Build ripgrep command for remote execution via SSH."""
        # Escape query for shell
        escaped_query = self._escape_shell_arg(query)
        escaped_root = self._escape_shell_arg(workspace_root)
        
        if mode == "filename":
            # Filename-only search
            cmd = f"rg --files {escaped_root}"
            if include_hidden:
                cmd += " --hidden"
            if file_types:
                for ft in file_types:
                    clean_ext = ft.lstrip('.')
                    cmd += f" -g '*.{clean_ext}'"
            cmd += f" | rg -i {escaped_query} | head -n {max_results}"
        else:
            # Content search
            cmd = f"rg -n -H --no-heading -i {escaped_query} {escaped_root}"
            if include_hidden:
                cmd += " --hidden"
            if file_types:
                for ft in file_types:
                    clean_ext = ft.lstrip('.')
                    cmd += f" -t {clean_ext}"
            cmd += f" | head -n {max_results}"
        
        return cmd
    
    def _build_grep_remote_cmd(self, query: str, workspace_root: str, file_types: Optional[List[str]], 
                                max_results: int) -> str:
        """Build grep command as fallback when ripgrep not available."""
        escaped_query = self._escape_shell_arg(query)
        escaped_root = self._escape_shell_arg(workspace_root)
        
        # Use grep -r for recursive search
        cmd = f"grep -rnH -i {escaped_query} {escaped_root}"
        
        # Add file type filters if specified
        if file_types:
            include_patterns = []
            for ft in file_types:
                clean_ext = ft.lstrip('.')
                include_patterns.append(f"--include='*.{clean_ext}'")
            cmd += " " + " ".join(include_patterns)
        
        cmd += f" 2>/dev/null | head -n {max_results}"
        return cmd
    
    def _build_find_remote_cmd(self, query: str, workspace_root: str, file_types: Optional[List[str]], 
                                max_results: int) -> str:
        """Build find command for filename-only search as last resort fallback."""
        escaped_root = self._escape_shell_arg(workspace_root)
        
        if file_types:
            # Build find with extension filters
            name_patterns = []
            # Avoid duplicating dots/extensions when the query itself looks like an extension (e.g. ".png")
            q_for_name = query.lstrip('.') if query else ''
            for ft in file_types:
                clean_ext = ft.lstrip('.')
                # Use shell pattern matching (no need to escape * inside single quotes)
                if q_for_name:
                    name_patterns.append(f"-iname '*{q_for_name}*.{clean_ext}'")
                else:
                    name_patterns.append(f"-iname '*.{clean_ext}'")
            
            if name_patterns:
                pattern_expr = " -o ".join(name_patterns)
                cmd = f"find {escaped_root} -type f \\( {pattern_expr} \\) -maxdepth 10 2>/dev/null | head -n {max_results}"
            else:
                cmd = f"find {escaped_root} -type f -iname '*{query}*' -maxdepth 10 2>/dev/null | head -n {max_results}"
        else:
            # Simple filename search
            cmd = f"find {escaped_root} -type f -iname '*{query}*' -maxdepth 10 2>/dev/null | head -n {max_results}"
        
        return cmd
    
    def _parse_search_output(self, output: str, search_type: str = "content") -> List[Dict[str, Any]]:
        """Parse output from ripgrep/grep commands.
        
        Args:
            output: Command output string
            search_type: "content" for rg/grep output (file:line:content), "filename" for find output
        
        Returns:
            List of result dicts with file, line, snippet fields
        """
        results = []
        if not output or not output.strip():
            return results
        
        lines = output.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            if search_type == "filename":
                # Find output: just file paths
                results.append({
                    "file": line.strip(),
                    "line": None,
                    "snippet": None
                })
            else:
                # Ripgrep/grep output: file:line:content
                parts = line.split(':', 2)
                if len(parts) >= 3:
                    try:
                        results.append({
                            "file": parts[0].strip(),
                            "line": int(parts[1].strip()),
                            "snippet": parts[2].strip()
                        })
                    except (ValueError, IndexError):
                        # Skip malformed lines
                        continue
                elif len(parts) == 1:
                    # Might be filename-only result
                    results.append({
                        "file": parts[0].strip(),
                        "line": None,
                        "snippet": None
                    })
        
        return results
    
    async def _execute_remote_search(self, query: str, scope: Optional[str], file_types: Optional[List[str]],
                                     include_hidden: bool, max_results: int, mode: str = "smart") -> ToolResult:
        """Execute search on remote server using ripgrep/grep/find via terminal.
        
        Phase 1 Implementation: Uses run_in_terminal to execute search commands on remote server.
        
        Fallback chain:
        1. Try ripgrep (rg) - fast, full-featured
        2. Fall back to grep - slower but commonly available
        3. Fall back to find - filename only, last resort
        
        Args:
            query: Search query string
            scope: Optional directory scope (relative to workspace root)
            file_types: Optional list of file extensions to filter
            include_hidden: Include hidden files in search
            max_results: Maximum number of results to return
        
        Returns:
            ToolResult with list of search results or error
        """
        try:
            from .context_helpers import get_current_context, get_contextual_terminal
            from icpy.services.path_utils import format_namespaced_path
            import posixpath
            
            import time
            # Get current context
            context = await get_current_context()
            workspace_root = context.get("workspaceRoot") or context.get("cwd") or "/"
            ctx_id = context.get("contextId", "local")
            
            # Apply scope if provided
            if scope:
                if scope.startswith('/'):
                    search_path = scope
                else:
                    search_path = posixpath.join(workspace_root, scope)
            else:
                search_path = workspace_root
            
            logger.info(f"[SemanticSearch] Remote search: query='{query}', path='{search_path}', types={file_types}, mode={mode}")
            logger.info("[SemanticSearch] Starting timer for remote search")
            _t0 = time.perf_counter()
            selected_strategy = "none"
            
            # Get terminal for command execution (for compatibility in tests),
            # but prefer a robust hop-aware runner when direct execution is unavailable.
            terminal = await get_contextual_terminal()

            async def _run_cmd(cmd: str, explain: str) -> dict:
                """Run a shell command in the active context and return a dict with output/error/status.

                Preference order:
                1) Use terminal.execute_command if available (keeps unit tests compatible)
                2) Fallback to RunTerminalTool which handles remote execution via SSH with ephemeral fallback
                """
                # Path A: direct terminal service (mocked in tests)
                if hasattr(terminal, 'execute_command') and callable(getattr(terminal, 'execute_command')):
                    logger.debug("[SemanticSearch] Executing via terminal.execute_command")
                    return await terminal.execute_command(cmd)
                # Path B: robust hop-aware command runner
                try:
                    from .run_terminal_tool import RunTerminalTool
                    runner = RunTerminalTool()
                    logger.info("[SemanticSearch] Executing via RunTerminalTool fallback (hop-aware)")
                    r = await runner.execute(command=cmd, explanation=explain, isBackground=False)
                    if r and r.success and isinstance(r.data, dict):
                        return r.data
                    # Normalize error shape
                    return {
                        "status": -1,
                        "output": "",
                        "error": r.error if r and getattr(r, 'error', None) else "unknown error",
                        "context": "unknown"
                    }
                except Exception as e:
                    logger.warning(f"[SemanticSearch] Fallback RunTerminalTool failed: {e}")
                    return {"status": -1, "output": "", "error": str(e)}
            
            # Determine search mode (respect explicit mode when provided)
            if mode == "filename":
                is_filename_search = True
            elif mode == "content":
                is_filename_search = False
            else:
                is_filename_search = self._looks_like_filename(query) or (file_types and not query.strip())
            
            # Strategy 1: Try ripgrep
            try:
                logger.info("[SemanticSearch] Trying ripgrep (rg)...")
                mode = "filename" if is_filename_search else "content"
                rg_cmd = self._build_ripgrep_remote_cmd(query, search_path, file_types, include_hidden, max_results, mode)
                logger.info(f"[SemanticSearch] Command: {rg_cmd}")
                
                result = await _run_cmd(rg_cmd, "Semantic search via ripgrep")
                
                if result and isinstance(result, dict) and result.get("output") is not None:
                    output = str(result.get("output", "")).strip()
                    try:
                        err_str = str(result.get("error", ""))
                        logger.info(
                            f"[SemanticSearch] rg finished: status={result.get('status')} ctx={result.get('context', '?')} "
                            f"out_len={len(output)} err_len={len(err_str)}"
                        )
                    except Exception:
                        pass
                    if output and "command not found" not in output.lower() and "rg: not found" not in output.lower():
                        # Parse ripgrep output
                        search_type = "filename" if is_filename_search else "content"
                        results = self._parse_search_output(output, search_type)
                        
                        if results:
                            selected_strategy = "ripgrep"
                            logger.info(f"[SemanticSearch] Ripgrep found {len(results)} results")
                            
                            # Format with namespaced paths
                            formatted_results = []
                            for item in results:
                                file_path = item["file"]
                                formatted_path = await format_namespaced_path(ctx_id, file_path)
                                formatted_results.append({
                                    "file": file_path,
                                    "filePath": formatted_path,
                                    "line": item.get("line"),
                                    "snippet": item.get("snippet")
                                })
                            
                            _dt = time.perf_counter() - _t0
                            logger.info(f"[SemanticSearch] Remote search completed in {_dt:.3f}s (strategy=ripgrep, results={len(results)})")
                            return ToolResult(success=True, data=self._cap_results(formatted_results, max_results))
                        else:
                            logger.info("[SemanticSearch] Ripgrep returned no results")
                    else:
                        logger.info("[SemanticSearch] Ripgrep not available, trying grep...")
                else:
                    logger.info("[SemanticSearch] Ripgrep command failed, trying grep...")
            except Exception as e:
                logger.warning(f"[SemanticSearch] Ripgrep failed: {e}, trying grep...")
            
            # Strategy 2: Try grep (only for content search)
            if not is_filename_search:
                try:
                    logger.info("[SemanticSearch] Trying grep...")
                    grep_cmd = self._build_grep_remote_cmd(query, search_path, file_types, max_results)
                    logger.info(f"[SemanticSearch] Command: {grep_cmd}")
                    
                    result = await _run_cmd(grep_cmd, "Semantic search via grep")
                    
                    if result and isinstance(result, dict) and result.get("output") is not None:
                        output = str(result.get("output", "")).strip()
                        try:
                            err_str = str(result.get("error", ""))
                            logger.info(
                                f"[SemanticSearch] grep finished: status={result.get('status')} ctx={result.get('context', '?')} "
                                f"out_len={len(output)} err_len={len(err_str)}"
                            )
                        except Exception:
                            pass
                        if output and "command not found" not in output.lower():
                            # Parse grep output
                            results = self._parse_search_output(output, "content")
                            
                            if results:
                                selected_strategy = "grep"
                                logger.info(f"[SemanticSearch] Grep found {len(results)} results")
                                
                                # Format with namespaced paths
                                formatted_results = []
                                for item in results:
                                    file_path = item["file"]
                                    formatted_path = await format_namespaced_path(ctx_id, file_path)
                                    formatted_results.append({
                                        "file": file_path,
                                        "filePath": formatted_path,
                                        "line": item.get("line"),
                                        "snippet": item.get("snippet")
                                    })
                                
                                _dt = time.perf_counter() - _t0
                                logger.info(f"[SemanticSearch] Remote search completed in {_dt:.3f}s (strategy=grep, results={len(results)})")
                                return ToolResult(success=True, data=self._cap_results(formatted_results, max_results))
                            else:
                                logger.info("[SemanticSearch] Grep returned no results")
                        else:
                            logger.info("[SemanticSearch] Grep not available, trying find...")
                    else:
                        logger.info("[SemanticSearch] Grep command failed, trying find...")
                except Exception as e:
                    logger.warning(f"[SemanticSearch] Grep failed: {e}, trying find...")
            
            # Strategy 3: Fall back to find (filename-only)
            try:
                logger.info("[SemanticSearch] Trying find (filename-only)...")
                find_cmd = self._build_find_remote_cmd(query, search_path, file_types, max_results)
                logger.info(f"[SemanticSearch] Command: {find_cmd}")
                
                result = await _run_cmd(find_cmd, "Semantic search via find")
                
                if result and isinstance(result, dict) and result.get("output") is not None:
                    output = str(result.get("output", "")).strip()
                    try:
                        err_str = str(result.get("error", ""))
                        logger.info(
                            f"[SemanticSearch] find finished: status={result.get('status')} ctx={result.get('context', '?')} "
                            f"out_len={len(output)} err_len={len(err_str)}"
                        )
                    except Exception:
                        pass
                    if output:
                        # Parse find output
                        results = self._parse_search_output(output, "filename")
                        
                        if results:
                            selected_strategy = "find"
                            logger.info(f"[SemanticSearch] Find found {len(results)} results")
                            
                            # Format with namespaced paths
                            formatted_results = []
                            for item in results:
                                file_path = item["file"]
                                formatted_path = await format_namespaced_path(ctx_id, file_path)
                                formatted_results.append({
                                    "file": file_path,
                                    "filePath": formatted_path,
                                    "line": None,
                                    "snippet": None
                                })
                            
                            _dt = time.perf_counter() - _t0
                            logger.info(f"[SemanticSearch] Remote search completed in {_dt:.3f}s (strategy=find, results={len(results)})")
                            return ToolResult(success=True, data=self._cap_results(formatted_results, max_results))
                        else:
                            logger.info("[SemanticSearch] Find returned no results")
                    else:
                        logger.info("[SemanticSearch] Find returned empty output")
                else:
                    logger.info("[SemanticSearch] Find command failed")
            except Exception as e:
                logger.warning(f"[SemanticSearch] Find failed: {e}")
            
            # No results from any strategy
            logger.info("[SemanticSearch] All search strategies exhausted, no results found")
            _dt = time.perf_counter() - _t0
            logger.info(f"[SemanticSearch] Remote search completed in {_dt:.3f}s (strategy={selected_strategy}, results=0)")
            return ToolResult(
                success=True,
                data=[],
                error="No results found. Tip: Ensure ripgrep (rg) or grep is installed on the remote server for better search results. Run 'sudo apt install ripgrep' or 'sudo yum install ripgrep' to install."
            )
            
        except Exception as e:
            logger.error(f"[SemanticSearch] Error executing remote search for query '{query}': {e}", exc_info=True)
            return ToolResult(success=False, error=f"Remote search failed: {str(e)}") 