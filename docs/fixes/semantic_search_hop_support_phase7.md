## Semantic Search Tool Phase 7: Hop Support Implementation ✅

### Overview
Updated the `semantic_search_tool` to support both local and remote (hopped) filesystems, making it consistent with how `read_file_tool` and `create_file_tool` handle hop contexts.

### Problem Addressed
The semantic search tool was using `ripgrep` (a local binary) directly, which meant it could only search the local filesystem. When an agent hopped to a remote server, the tool would fail because:
1. Ripgrep cannot be executed on the remote server from the local Docker container
2. Even if it could, it would search the local filesystem, not the remote filesystem

### Solution Implemented

#### Architecture Changes
- **Context Detection**: Added Phase 7 detection to check if the agent is in a hopped context
- **Dual Execution Paths**:
  - **Local Search**: Uses ripgrep binary (original behavior preserved)
  - **Remote Search**: Uses the filesystem service's `search_files()` method which works with RemoteFileSystemAdapter
- **Graceful Fallback**: If context detection fails, defaults to local search

#### Code Changes
**File**: `backend/icpy/agent/tools/semantic_search_tool.py`

1. **Updated imports**: Added `get_contextual_filesystem` from `context_helpers`
2. **Modified execute() method**: 
   - Now checks current context using `get_current_context()`
   - Routes to appropriate search implementation
   - Safely handles context detection failures
3. **New method `_execute_local_search()`**:
   - Extracted original ripgrep logic
   - Preserves all existing search modes (smart, content, filename, regex)
   - Maintains backward compatibility
4. **New method `_execute_remote_search()`**:
   - Uses context-aware filesystem service
   - Converts results to expected format (file, line, snippet)
   - Includes proper error handling

#### Consistency with Other Tools
Now follows the same pattern as `read_file_tool.py` and `create_file_tool.py`:
```python
# All three tools now use:
from .context_helpers import get_contextual_filesystem
filesystem_service = await get_contextual_filesystem()
```

This ensures consistent behavior across all agent tools when working with hopped connections.

### Test Coverage

**New test file**: `backend/tests/icpy/agent/tools/test_semantic_search_hop_support.py`

7 new comprehensive tests covering:
1. ✅ Remote search when hopped to remote server
2. ✅ Local search when not hopped (no active connection)
3. ✅ Context detection error fallback to local search
4. ✅ Remote search with empty results
5. ✅ Remote search error handling (e.g., SFTP connection lost)
6. ✅ Remote search result formatting and conversion
7. ✅ Remote search respecting max_results parameter

**Total test results**: 26/26 tests passing
- 7 new hop support tests (100% pass)
- 13 existing semantic search tool tests (100% pass)
- 6 semantic search enhancement tests (100% pass)

### Files Modified
1. `backend/icpy/agent/tools/semantic_search_tool.py` - Added Phase 7 hop support
2. `backend/tests/icpy/agent/tools/test_semantic_search_hop_support.py` - New test file

### Features
- ✅ Remote file searching when hopped to SSH server
- ✅ Local ripgrep search unchanged (backward compatible)
- ✅ Graceful fallback to local search on context detection errors
- ✅ Proper result formatting from both local and remote sources
- ✅ Comprehensive error handling and logging
- ✅ Respects maxResults parameter for both local and remote
- ✅ Works seamlessly with existing ContextRouter infrastructure

### How It Works

**When searching on a local filesystem**:
```
User calls semantic_search(query="helper")
  ↓
Detects contextId="local" or context detection fails
  ↓
Uses _execute_local_search()
  ↓
Executes ripgrep with smart fallback passes
  ↓
Returns results with line numbers and snippets
```

**When searching on a remote hopped server**:
```
User calls semantic_search(query="helper") after hopping to "hop1"
  ↓
Detects contextId="hop1" and status="connected"
  ↓
Uses _execute_remote_search()
  ↓
Calls filesystem_service.search_files() (which uses RemoteFileSystemAdapter)
  ↓
SFTP searches files on remote server
  ↓
Converts results to expected format
  ↓
Returns results with absolute remote paths
```

### Implementation Notes
- The RemoteFileSystemAdapter's `search_files()` currently does filename + shallow content matching
- For now, remote searches don't provide line numbers (marked as None in results)
- This can be enhanced in future phases to provide better remote search capabilities
- All logging is debug/info level for production safety

### Backward Compatibility
✅ 100% backward compatible
- All existing ripgrep parameters work unchanged (scope, fileTypes, includeHidden, mode, root, contextLines)
- Local search behavior identical to before
- Only addition is detection and routing to remote search when appropriate
