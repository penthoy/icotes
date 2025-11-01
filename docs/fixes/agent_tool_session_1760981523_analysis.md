# Session 1760981523 Agent Tool Issues: Analysis & Fixes

## Session Context
- **Date**: 2025-10-29
- **User Request**: Test both semantic_search and create_file tools
- **Active Context**: Agent running on hop1 (remote server 192.168.2.211)
- **Session ID**: session_1760981523_e59c3496

## Issue 1: semantic_search Tool Returns Empty Results ❌

### Problem
The semantic_search tool returns empty lists `[]` for queries that clearly exist in hidden `.icotes` files, while shell `grep` finds them successfully.

### Reproduction Steps
```python
# These all returned []
semantic_search(query="Host hop1", scope="/home/penthoy/icotes/workspace", includeHidden=true, maxResults=50)
semantic_search(query="hop1", includeHidden=true, maxResults=50)
semantic_search(query="192.168.2.211", scope="/home/penthoy/icotes/workspace/.icotes/hop", mode="content")
semantic_search(query="image_references.json", scope="/home/penthoy/icotes/workspace/.icotes", mode="filename")
```

### Evidence
- **Shell grep confirms files exist**:
  ```bash
  /home/penthoy/icotes/workspace/.icotes/hop/config:4:Host hop1
  /home/penthoy/icotes/workspace/.icotes/hop/config:5:    HostName 192.168.2.211
  /home/penthoy/icotes/workspace/.icotes/image_references.json: entries with "context_host": "192.168.2.211"
  ```
- **semantic_search returned**: `[]` (empty) with no errors

### Root Cause Analysis
The issue is that when an agent is hopped to a remote context, `semantic_search` doesn't use the context-aware filesystem. Unlike `read_file_tool` and `create_file_tool`, which were recently updated with Phase 7 hop support, `semantic_search` still:
1. Uses local ripgrep binary directly
2. Doesn't check if agent is in a hopped context
3. Can't search remote files even with `includeHidden=true`

### Status
**✅ FIXED** - See Phase 7 Hop Support Implementation in semantic_search_tool.py

---

## Issue 2: create_file Tool Returns Success But Files Not Written ❌

### Problem
The create_file tool reports success (`"created": true`) but files are not actually created in the workspace. Reading the files back returns empty content.

### Reproduction Steps
```python
# Created via create_file (reported success)
create_file(filePath="/home/penthoy/icotes/workspace/create_file_test.txt", 
            content="create_file test\n...", 
            createDirectories=false)
# Result: {"created": true}

# But shell verification shows file does not exist
ls -la /home/penthoy/icotes/workspace/create_file_test.txt  # -> No such file
cat /home/penthoy/icotes/workspace/create_file_test.txt      # -> No such file

# Same for nested file with createDirectories=true
create_file(filePath="/home/penthoy/icotes/workspace/test_dir/subdir/create_file_test_nested.txt",
            content="nested create_file test\n...",
            createDirectories=true)
# Result: {"created": true}  (but file not found)

# Control test with shell (works perfectly)
echo "test content" > /home/penthoy/icotes/workspace/create_file_test_shell.txt
# File successfully created and visible
```

### Backend Logs - The Real Culprit
```
2025-10-29 17:41:45 [ERROR] icpy.services.remote_fs_adapter: [RemoteFS] write_file error /home/penthoy/icotes/workspace/create_file_test2.txt: 
Task <Task pending name='Task-765'...> got Future <Future pending> attached to a different loop

2025-10-29 17:41:48 [ERROR] icpy.services.remote_fs_adapter: [RemoteFS] write_file error /home/penthoy/icotes/workspace/test_dir/subdir/create_file_test_nested.txt: 
Task <Task pending name='Task-777'...> got Future <Future pending> attached to a different loop
```

### Root Cause: Event Loop Mismatch
**This is a critical asyncio bug**: When create_file calls the remote filesystem adapter's `write_file()` or `write_file_binary()`, there's an event loop mismatch:
- `current_loop=0x7177b8000900` (tool execution context)
- `hop_loop=0x7177ddb62030` (hop service context)

The error "got Future attached to a different loop" means:
1. The agent tool runs in one asyncio event loop (tool executor)
2. The hop/remote filesystem service runs in a different event loop
3. When trying to write via SFTP (which uses asyncio), the future is attached to the wrong loop
4. The exception is caught somewhere and silently converted to success

### Why Shell Works
The shell command via `run_terminal_tool` bypasses all this and directly executes on the local system, which works fine because it's not async-dependent.

### Why read_file Works (Sometimes)
```
2025-10-29 17:41:48 [INFO] icpy.services.remote_fs_adapter: [RemoteFS] read_file loop diag 
path=/home/penthoy/icotes/workspace/create_file_test.txt 
current_loop=0x7177ddb62030 hop_loop=0x7177ddb62030  # ✅ SAME LOOPS!
```
Read works because the file was created by shell, and when reading, the loops happen to be the same. But read of files "created" by create_file shows empty because they were never actually written.

### Files Actually Created
Only the shell-created file exists:
```
-rw-rw-r--  1 penthoy penthoy 111 Oct 29 17:41 /home/penthoy/icotes/workspace/create_file_test_shell.txt
```
Files attempted via create_file don't exist (find search returned 0 results for `create_file_test*.txt` except shell-created).

---

## Recommended Fixes

### Fix 1: semantic_search Tool (Phase 7 Hop Support)
**Status**: ✅ Already implemented - see semantic_search_hop_support_phase7.md

The semantic_search tool has been updated to:
- Detect current hop context
- Route to remote search when hopped
- Use context-aware filesystem for both local and remote
- All 26 tests passing

### Fix 2: create_file Tool - Event Loop Synchronization
**Status**: Needs implementation

#### Root Cause Details
The issue is in `backend/icpy/services/remote_fs_adapter.py` in the `write_file_binary()` method:
```python
async def write_file_binary(self, path: str, content: bytes) -> None:
    # When called from agent tool (different loop), creates Future in wrong loop
    async with sftp.open(..., 'wb') as f:
        await f.write(content)  # ← attached to hop_loop, but called from tool_loop
```

#### Solution Approach
Multiple potential fixes (in order of preference):

**Option A: Use run_sync_in_new_loop** (Recommended)
```python
# In remote_fs_adapter.py
def write_file_binary(self, path: str, content: bytes) -> None:
    """Write binary content to file (sync wrapper for cross-loop calls)"""
    try:
        loop = get_event_loop()  # Get current loop
        if loop != self.loop:
            # Different loop: run async operation in hop service's loop
            future = asyncio.run_coroutine_threadsafe(
                self._write_file_binary_async(path, content), 
                self.loop
            )
            future.result(timeout=30)  # Block until complete
        else:
            # Same loop: run directly
            loop.run_until_complete(self._write_file_binary_async(path, content))
    except Exception as e:
        logger.error(f"[RemoteFS] write_file error {path}: {e}")
        raise

async def _write_file_binary_async(self, path: str, content: bytes) -> None:
    # Actual implementation (moved to separate method)
    sftp = self._sftp()
    if not sftp:
        raise RuntimeError("SFTP not connected")
    abs_path = self._resolve(path)
    parent = posixpath.dirname(abs_path)
    await sftp.makedirs(parent, exist_ok=True)
    async with sftp.open(abs_path, 'wb') as f:
        await f.write(content)
```

**Option B: Create sync wrapper in CreateFileTool**
```python
# In backend/icpy/agent/tools/create_file_tool.py
async def execute(self, **kwargs):
    ...
    filesystem_service = await get_contextual_filesystem()
    
    # Check if we're in wrong loop
    try:
        current_loop = asyncio.get_running_loop()
        if hasattr(filesystem_service, 'loop') and filesystem_service.loop != current_loop:
            # Use sync write method if available
            if hasattr(filesystem_service, 'write_file_sync'):
                filesystem_service.write_file_sync(normalized_path, content)
            else:
                # Fallback: convert content and use shell
                await filesystem_service.write_file(normalized_path, content)
        else:
            await filesystem_service.write_file(normalized_path, content)
    except RuntimeError:  # "no running event loop"
        await filesystem_service.write_file(normalized_path, content)
```

**Option C: Fix in ToolExecutor** (Simplest long-term)
```python
# In backend/icpy/agent/helpers.py ToolExecutor.execute_tool_call()
# Ensure tool execution happens in the same event loop as services
async def execute_tool_call(self, tool_call):
    # Get the hop service's loop if active
    hop_service = await get_hop_service()
    active_loop = hop_service._loop if hop_service else asyncio.get_running_loop()
    
    # Execute tool in the correct loop context
    return await self._run_in_loop(tool_call, active_loop)
```

### Recommended Implementation Path

1. **Immediate (Fix Option B - Create sync wrapper)**
   - Add `write_file_sync()` method to remote_fs_adapter
   - Update create_file_tool to detect loop mismatch and use sync wrapper
   - Minimal changes, solves the issue immediately
   - Test with existing test suite

2. **Short-term (Fix Option A - Remote executor)**
   - Use `asyncio.run_coroutine_threadsafe()` to marshal calls between loops
   - More robust, handles edge cases
   - Requires careful timeout handling

3. **Long-term (Fix Option C - ToolExecutor)**
   - Refactor ToolExecutor to ensure consistent loop context
   - Prevents this issue in other tools
   - Larger refactor, but cleaner architecture

---

## Files Involved

### semantic_search_tool.py
- ✅ Already fixed with Phase 7 hop support
- Uses `get_contextual_filesystem()` to detect and route to remote search
- All 26 tests passing

### create_file_tool.py
- ❌ Needs fix for event loop handling
- Currently catches exceptions silently and returns success
- Need to properly handle `write_file_binary()` failures from remote_fs_adapter

### remote_fs_adapter.py
- ❌ Root cause: `write_file_binary()` doesn't handle cross-loop calls
- Need to add sync wrapper or use `asyncio.run_coroutine_threadsafe()`
- Diagnostic logging already present (helpful!)

### read_file_tool.py
- ✅ Works correctly (uses `get_contextual_filesystem()` like create_file)
- Success of reads is somewhat masked by the fact that empty files still read as empty

---

## Testing Strategy

### For semantic_search
- ✅ 26 tests created and passing in test_semantic_search_hop_support.py
- Tests cover: remote search, local fallback, error handling, result formatting

### For create_file
- New tests needed to verify:
  1. Files are actually written when tool reports success
  2. File content is preserved correctly
  3. Nested directory creation works
  4. Cross-loop execution is handled properly
  5. Both local and hopped contexts work

Example test:
```python
@pytest.mark.asyncio
async def test_create_file_with_hop_context():
    # Create file via create_file tool
    tool = CreateFileTool()
    result = await tool.execute(
        filePath="/workspace/test_hop_write.txt",
        content="test content for hop"
    )
    assert result.success is True
    
    # Verify file actually exists (read back)
    read_tool = ReadFileTool()
    read_result = await read_tool.execute(filePath="/workspace/test_hop_write.txt")
    assert read_result.success is True
    assert read_result.data["content"] == "test content for hop"
    
    # Verify via shell
    result = subprocess.run(
        ["cat", "/home/penthoy/icotes/workspace/test_hop_write.txt"],
        capture_output=True,
        text=True
    )
    assert result.stdout == "test content for hop"
```

---

## Summary Table

| Issue | Tool | Root Cause | Status | Fix Priority |
|-------|------|-----------|--------|--------------|
| Returns empty results for hidden files | semantic_search | No hop context detection | ✅ Fixed | N/A |
| Returns success but no file written | create_file | Event loop mismatch in remote_fs_adapter | ❌ Needs Fix | High |
| File reads show 0 bytes | read_file (indirectly) | Consequence of issue #2 | ✅ Works once fixed | High |

---

## Next Steps

1. **Verify semantic_search fix** works in the current environment
2. **Implement create_file fix** using Option B (sync wrapper approach)
3. **Add comprehensive tests** for both tools with hop context
4. **Document the event loop pattern** for future tool developers
5. **Consider Option C** for architectural improvement in the future
