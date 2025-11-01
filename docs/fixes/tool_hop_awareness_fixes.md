# Tool Hop Awareness Fixes

**Date**: October 30, 2025  
**Branch**: 45-agent-improvement-and-bugfixes  
**Context**: Addressing issues reported in agent tool testing sessions where tools behaved inconsistently when hopped to remote servers.

## Issues Identified

From the agent test reports in sessions `session_1761793068_9768fb5b` and `session_1761796142_6b72623d`:

1. **Namespace confusion in file operations**: `local:/workspace/...` paths were being written to the remote hop instead of the local machine when the agent was hopped.

2. **run_in_terminal executed locally regardless of hop**: Commands ran on the local machine even when hopped to remote, causing files created via terminal to be invisible to remote file tools.

3. **semantic_search returned empty results**: Searches for files outside WORKSPACE_ROOT (e.g., `/home/penthoy/icotes/backend`) returned no results without explanation.

4. **Unclear error messages**: read_file returned generic "Failed to read file" without hints about namespacing or workspace boundaries.

## Fixes Implemented

### 1. File Tool Namespace Routing (create_file, read_file, replace_string_in_file)

**Problem**: Tools always used the active context's filesystem, so `local:/...` paths mistakenly wrote to the remote hop.

**Solution**: 
- Modified all file tools to respect the requested namespace by calling `router.get_filesystem_for_namespace(ctx_id)` instead of using the active context.
- `local:/...` now always writes to the local WORKSPACE_ROOT, even when hopped.
- `hop1:/...` writes to the remote workspace.

**Files Changed**:
- `backend/icpy/agent/tools/create_file_tool.py`
- `backend/icpy/agent/tools/read_file_tool.py`
- `backend/icpy/agent/tools/replace_string_in_file.py`

**Code Pattern**:
```python
# Old: always used active context
filesystem_service = await get_filesystem_service()

# New: respects requested namespace
if get_context_router is not None:
    router = await get_context_router()
    filesystem_service = await router.get_filesystem_for_namespace(ctx_id)
else:
    filesystem_service = await get_filesystem_service()
```

### 2. Path Info Namespace Consistency

**Problem**: Tools formatted path info using the active context, so outputs showed `hop1:/...` for `local:/...` inputs when hopped.

**Solution**: Force the namespace when building pathInfo so outputs match the requested namespace:
```python
# Force the intended namespace
path_info = await self._format_path_info(f"{ctx_id}:{normalized_path}")
```

**Result**: `local:/workspace/file.txt` now correctly returns `local:/home/penthoy/icotes/workspace/file.txt` in pathInfo, not `hop1:/...`

### 3. run_in_terminal Hop Awareness

**Problem**: The tool used `asyncio.subprocess` directly, always executing on the local machine regardless of hop context.

**Solution**: 
- Detect hop context using `get_context_router()` and `get_hop_service()`
- If hopped and SSH connection available, use `ssh_conn.run(command)` to execute remotely
- If local or no SSH connection, use subprocess as before
- Added `context` field to results (`"local"` or `"remote"`) for transparency

**Files Changed**:
- `backend/icpy/agent/tools/run_terminal_tool.py`

**Code Pattern**:
```python
# Determine execution context
is_remote = False
ssh_conn = None
if HOP_AVAILABLE:
    router = await get_context_router()
    context = await router.get_context()
    if context.contextId != "local" and context.status == "connected":
        hop = await get_hop_service()
        ssh_conn = hop.get_active_connection()
        if ssh_conn:
            is_remote = True

if is_remote and ssh_conn:
    return await self._execute_remote(ssh_conn, command, is_background)
else:
    return await self._execute_local(command, is_background)
```

**Remote Execution**:
- Foreground: `result = await ssh_conn.run(command, check=False)`
- Background: `nohup {command} > /dev/null 2>&1 & echo $!`

### 4. read_file Error Message Improvements

**Problem**: Generic "Failed to read file" error without context about workspace boundaries or namespace requirements.

**Solution**: 
- Check if file exists using `filesystem_service.get_file_info()` before reading
- Provide context-specific hints:
  - **Local**: Suggests using `local:/...` or relative paths if outside workspace
  - **Remote**: Suggests using correct namespace like `hop1:/...`

**Example Error Messages**:
```
Failed to read file: /path ( not found or unreadable). The path may be outside WORKSPACE_ROOT or not exist. Try 'local:/<path-within-workspace>' or a relative path.

Failed to read file: /path ( not found or unreadable). The file may not exist on the remote host or the path is incorrect. Try prefixing with the correct namespace like 'hop1:/...'.
```

### 5. semantic_search Error Messaging

**Problem**: Empty results when searching outside workspace without explanation.

**Solution**: 
- Validate search path exists before executing ripgrep
- Return helpful error when path doesn't exist:
  ```
  Search path does not exist: /path. When root='workspace', searches are constrained to the workspace directory. To search the repo, use root='repo'.
  ```
- For remote searches with scope parameter, add note that scope is ignored:
  ```
  No results found. Note: Remote search is constrained to the workspace root and cannot search arbitrary paths like '/home/penthoy/icotes/backend'. To search outside the workspace, use run_in_terminal with 'rg' or 'find' commands.
  ```

**Files Changed**:
- `backend/icpy/agent/tools/semantic_search_tool.py`

## Testing Recommendations

1. **Create files with explicit namespaces when hopped**:
   ```python
   # When hopped to hop1:
   create_file("local:/workspace/test.txt", "local content")  # → writes to local machine
   create_file("hop1:/home/user/test.txt", "remote content")  # → writes to remote
   ```

2. **Use run_in_terminal for commands on the current hop**:
   ```python
   # When hopped, this now runs remotely:
   run_in_terminal("echo test > /home/user/file.txt")
   read_file("hop1:/home/user/file.txt")  # → reads the file created remotely
   ```

3. **Check semantic_search scope constraints**:
   - Use `root='repo'` to search the project repository instead of workspace
   - For remote hops, use `run_in_terminal("rg 'pattern' /path")` to search arbitrary paths

## Behavioral Changes

### Before
- `local:/workspace/file.txt` when hopped → wrote to **remote** workspace ❌
- `run_in_terminal("echo test > file.txt")` when hopped → created file on **local** machine ❌
- `semantic_search(scope="/backend")` → empty results, no explanation ❌
- `read_file("/path")` failed → generic error ❌

### After
- `local:/workspace/file.txt` when hopped → writes to **local** workspace ✅
- `run_in_terminal("echo test > file.txt")` when hopped → creates file on **remote** machine ✅
- `semantic_search(scope="/backend")` → clear error about workspace constraints ✅
- `read_file("/path")` failed → context-aware hint about namespace or workspace ✅

## Migration Notes

- **No breaking changes** for existing agent code that doesn't use namespaced paths
- File tools now return `context` field in results for debugging
- run_in_terminal results now include `"context": "local"` or `"context": "remote"`
- Path info outputs now consistently use the requested namespace, not the active context

## Related Documentation

- `docs/fixes/context_router_display_names_fix.md` - UUID → friendly name display
- `docs/fixes/local_workspace_path_regression_fix.md` - /workspace/ prefix handling
- Session logs: `workspace/.icotes/chat_history/session_1761793068_9768fb5b.jsonl`, `session_1761796142_6b72623d.jsonl`

## Future Improvements

1. **semantic_search remote scope support**: Extend RemoteFileSystemAdapter to support arbitrary path searches via SSH `rg` execution
2. **run_in_terminal namespace parameter**: Allow explicit namespace like `run_in_terminal("cmd", namespace="hop1")` for multi-hop scenarios
3. **Tool result schemas**: Standardize `context`, `namespace`, `pathInfo` fields across all tools for consistency
