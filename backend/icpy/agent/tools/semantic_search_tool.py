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
        
        # Phase 7: Use context-aware filesystem
        if is_remote:
            logger.info(f"[SemanticSearch] Using remote filesystem search for query: {query}, fileTypes={file_types}")
            return await self._execute_remote_search(query, scope, file_types, include_hidden, max_results)
        
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
            
            # Validate that search_path exists and is accessible
            if not os.path.exists(search_path):
                return ToolResult(
                    success=False,
                    error=f"Search path does not exist: {search_path}. When root='workspace', searches are constrained to the workspace directory ({base_root}). To search the repo, use root='repo'."
                )
            
            if not os.path.isdir(search_path):
                return ToolResult(
                    success=False,
                    error=f"Search path is not a directory: {search_path}"
                )
            
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
    
    async def _execute_remote_search(self, query: str, scope: Optional[str], file_types: Optional[List[str]],
                                     include_hidden: bool, max_results: int) -> ToolResult:
        """Execute search on remote filesystem using context-aware filesystem service
        
        Phase 7: Works with RemoteFileSystemAdapter when hopped to a remote server.
        Uses the filesystem service's search_files method for content search.
        
        Phase 8 Update: Added filename-only search fallback using run_in_terminal + find
        to support queries like "cat" with fileTypes=["png"].
        
        Note: Remote search is constrained to the remote workspace root. Searches
        outside the workspace boundary will return empty results.
        """
        try:
            filesystem_service = await get_contextual_filesystem()
            
            # Log a warning if scope is provided (remote search ignores scope for now)
            if scope:
                logger.warning(f"[SemanticSearch] Remote search ignores scope parameter (requested: {scope}). Searching workspace root only.")
            
            # Get current context to determine workspace root
            from .context_helpers import get_current_context
            context = await get_current_context()
            workspace_root = context.get("workspaceRoot") or context.get("cwd") or "/"
            
            # If fileTypes are provided, try filename-based search first using find command
            if file_types:
                logger.info(f"[SemanticSearch] Remote filename search: query={query}, types={file_types}")
                try:
                    # Build find command for filename search with extension filters
                    # Use -iname for case-insensitive matching
                    name_patterns = []
                    for ft in file_types:
                        if ft:
                            clean_ext = ft.lstrip('.')
                            # Match files containing query in name AND having the extension
                            name_patterns.append(f"-iname '*{query}*.{clean_ext}'")
                    
                    if name_patterns:
                        pattern_expr = " -o ".join(name_patterns)
                        find_cmd = f"find {workspace_root} -type f \\( {pattern_expr} \\) -maxdepth 10 -print 2>/dev/null | head -n {max_results}"
                        
                        logger.info(f"[SemanticSearch] Executing remote find: {find_cmd}")
                        
                        # Execute find via terminal
                        from .context_helpers import get_contextual_terminal
                        terminal = await get_contextual_terminal()
                        result = await terminal.execute_command(find_cmd)
                        
                        logger.info(f"[SemanticSearch] Remote find result: {result}")
                        
                        if result and result.get("output"):
                            output = result["output"].strip()
                            logger.info(f"[SemanticSearch] Remote find output length: {len(output)} chars")
                            if output:
                                # Parse find output (one file per line)
                                file_paths = [line.strip() for line in output.split('\n') if line.strip()]
                                logger.info(f"[SemanticSearch] Found {len(file_paths)} files via remote find")
                                
                                # Format results with namespaced paths
                                from icpy.services.path_utils import format_namespaced_path
                                ctx_id = context.get("contextId", "local")
                                
                                formatted_results = []
                                for fpath in file_paths[:max_results]:
                                    formatted_path = await format_namespaced_path(ctx_id, fpath)
                                    formatted_results.append({
                                        "file": fpath,
                                        "filePath": formatted_path,
                                        "line": None,
                                        "snippet": None
                                    })
                                
                                if formatted_results:
                                    logger.info(f"[SemanticSearch] Found {len(formatted_results)} files via remote find")
                                    return ToolResult(success=True, data=formatted_results)
                            else:
                                logger.info(f"[SemanticSearch] Remote find returned empty output")
                        else:
                            logger.info(f"[SemanticSearch] Remote find returned no result object")
                except Exception as e:
                    logger.warning(f"[SemanticSearch] Remote filename search failed, falling back to content search: {e}", exc_info=True)
            
            # Fallback to content-based search
            logger.info(f"[SemanticSearch] Searching remote filesystem for content: {query}")
            search_results = await filesystem_service.search_files(
                query=query,
                search_content=True,  # Enable content search
                file_types=None,  # TODO: Convert fileTypes to FileType objects if needed
                max_results=max_results
            )
            
            logger.info(f"[SemanticSearch] Remote content search returned {len(search_results)} results")
            
            # Convert search results to the expected format (file, line, snippet)
            from icpy.services.path_utils import format_namespaced_path
            ctx_id = context.get("contextId", "local")
            
            formatted_results = []
            for result in search_results:
                # Results from search_files have: file_info, matches, score, context
                file_info = result.get('file_info') if isinstance(result, dict) else getattr(result, 'file_info', None)
                matches = result.get('matches') if isinstance(result, dict) else getattr(result, 'matches', [])
                
                if file_info:
                    # Extract file path from file_info dict
                    file_path = file_info.get('path') if isinstance(file_info, dict) else getattr(file_info, 'path', '')
                    formatted_path = await format_namespaced_path(ctx_id, file_path)
                    
                    entry = {
                        "file": file_path,
                        "filePath": formatted_path,
                        "line": None,  # Remote search doesn't provide line numbers yet
                        "snippet": matches[0] if matches else query
                    }
                    formatted_results.append(entry)
            
            logger.debug(f"[SemanticSearch] Found {len(formatted_results)} remote results")
            
            # If no results and a scope was provided, add a helpful message
            if not formatted_results and scope:
                return ToolResult(
                    success=True,
                    data=[],
                    error=f"No results found. Note: Remote search is constrained to the workspace root and cannot search arbitrary paths like '{scope}'. To search outside the workspace, use run_in_terminal with 'rg' or 'find' commands."
                )
            
            return ToolResult(success=True, data=self._cap_results(formatted_results, max_results))
            
        except Exception as e:
            logger.error(f"Error executing remote search for query '{query}': {e}")
            return ToolResult(success=False, error=f"Remote search failed: {str(e)}") 