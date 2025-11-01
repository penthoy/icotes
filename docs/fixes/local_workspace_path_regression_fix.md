# Local Workspace Path Regression Fix

## Issue
Tools were failing when agent used `local:/workspace/xxx` paths. The tools would try to access literal `/workspace/xxx` instead of resolving to the actual WORKSPACE_ROOT from .env.

**Error seen**:
```
Target: local:/workspace/tool_test/test_file.txt
Error: Failed to read file
```

The file should have been created at `/home/penthoy/icotes/workspace/tool_test/test_file.txt` but tools were looking for `/workspace/tool_test/test_file.txt` (which doesn't exist).

## Root Cause

When `context_router.parse_namespaced_path()` parses `local:/workspace/xxx`, it returns:
```python
("local", "/workspace/xxx")
```

The problem is that tools' `_validate_path()` method treated `/workspace/xxx` as an absolute path without realizing it should be resolved relative to WORKSPACE_ROOT.

**Flow**:
1. Agent says: `local:/workspace/tool_test/test_file.txt`
2. Router parses: `context_id="local"`, `abs_path="/workspace/tool_test/test_file.txt"`
3. Tool's `_validate_path()` sees absolute path starting with `/`
4. Tool tries to access literal `/workspace/tool_test/test_file.txt` ❌
5. Should access: `$WORKSPACE_ROOT/tool_test/test_file.txt` ✓

## Solution

Updated `_validate_path()` in three tools to handle `/workspace/` prefix specially:

### Files Modified:
- `backend/icpy/agent/tools/create_file_tool.py`
- `backend/icpy/agent/tools/read_file_tool.py`
- `backend/icpy/agent/tools/replace_string_tool.py`

### Code Change:
```python
def _validate_path(self, file_path: str, workspace_root: str) -> Optional[str]:
    try:
        workspace_root = os.path.abspath(workspace_root)
        
        if os.path.isabs(file_path):
            # NEW: Handle /workspace/ prefix specially
            if file_path.startswith('/workspace/') or file_path.startswith('/workspace\\'):
                relative_path = file_path[11:]  # Remove '/workspace/' (11 chars)
                normalized_path = os.path.abspath(os.path.join(workspace_root, relative_path))
            elif file_path == '/workspace':
                normalized_path = os.path.abspath(workspace_root)
            else:
                # Already absolute path - use as-is
                normalized_path = os.path.abspath(file_path)
        else:
            # ... existing relative path handling ...
```

**Logic**:
- If path is `/workspace/xxx`, strip the `/workspace/` prefix
- Treat remainder as relative path from WORKSPACE_ROOT
- Join with actual workspace root from .env: `/home/penthoy/icotes/workspace/xxx`

## Testing

### Test Case 1: Create file with local:/workspace/ prefix
```python
# Agent command
create_file(filePath="local:/workspace/test.txt", content="Hello")

# Expected behavior:
# - Router parses: ("local", "/workspace/test.txt")
# - Tool strips /workspace/, gets "test.txt"
# - Resolves to: /home/penthoy/icotes/workspace/test.txt ✓
```

### Test Case 2: Read file with local:/workspace/ prefix
```python
# Agent command
read_file(filePath="local:/workspace/tool_test/test_file.txt")

# Expected behavior:
# - Router parses: ("local", "/workspace/tool_test/test_file.txt")
# - Tool strips /workspace/, gets "tool_test/test_file.txt"
# - Resolves to: /home/penthoy/icotes/workspace/tool_test/test_file.txt ✓
```

### Test Case 3: Already absolute path (bypass workspace)
```python
# Agent command (when allowed)
read_file(filePath="local:/home/penthoy/icotes/workspace/test.txt")

# Expected behavior:
# - Router parses: ("local", "/home/penthoy/icotes/workspace/test.txt")
# - Tool sees absolute path not starting with /workspace/
# - Uses as-is, validates it's within workspace ✓
```

## Impact

This fix ensures that when agents use the `local:/workspace/` notation (which is a logical way to refer to workspace files), the tools correctly resolve paths relative to the actual WORKSPACE_ROOT from .env.

### Before Fix:
- ❌ `local:/workspace/test.txt` → tried to access `/workspace/test.txt` (doesn't exist)
- Error: "Failed to read file"

### After Fix:
- ✓ `local:/workspace/test.txt` → resolves to `/home/penthoy/icotes/workspace/test.txt`
- Works correctly

## Related Issues

This fix complements the UUID display fix (task #1 from roadmap). Both are part of improving the chat-hop integration for phase 4.

## Configuration

The fix relies on WORKSPACE_ROOT being set correctly in `.env`:
```properties
WORKSPACE_ROOT=/home/penthoy/icotes/workspace
```

Tools fall back to this environment variable when WorkspaceService is unavailable.
