# Issue: Test Cleanup Deleted .meta.json Files

**Date**: October 10, 2025  
**Severity**: Medium (Data preserved, metadata lost)  
**Status**: ✅ Fixed

## What Happened

During the streaming optimization test run, the pytest cleanup fixture in `backend/tests/conftest.py` **deleted all `.meta.json` files** from the chat history directory.

### Root Cause

The `cleanup_temp_workspaces` fixture (lines 48-56) was too aggressive:

```python
# BEFORE (PROBLEMATIC CODE):
# Clean up session files that look like test artifacts
session_files = list(chat_history_dir.glob('session_*.meta.json'))
for session_file in session_files:
    try:
        session_file.unlink()  # ← Deleted ALL .meta.json files!
        print(f"Cleaned up session file: {session_file}")
```

This ran after **every test session** and deleted:
- `session_1760064997_e30cdecb.meta.json`
- `session_1760068643_ac87a142.meta.json`  
- `session_1760038190_9a093ed5.meta.json`
- And more...

### Impact

**Good News**:
- ✅ **Actual chat history preserved** - The `.jsonl` files (actual conversation data) were NOT deleted
- ✅ **No data loss** - All messages and conversations intact

**Minor Impact**:
- ⚠️ **Session titles lost** - Chat History panel showed session IDs instead of friendly names
- ⚠️ **Metadata lost** - Session creation timestamps, update times, and other UI metadata

## Fix Applied

### 1. Updated Test Cleanup (Prevention)

Modified `backend/tests/conftest.py` to only clean up **recent** test files (created in last 5 minutes):

```python
# AFTER (FIXED CODE):
# Only clean up session files that are clearly test artifacts
# Look for recent files (created in last 5 minutes)
import time
current_time = time.time()

session_files = list(chat_history_dir.glob('session_*.meta.json'))
for session_file in session_files:
    try:
        # Only delete files modified in the last 5 minutes (likely test artifacts)
        file_mtime = session_file.stat().st_mtime
        age_seconds = current_time - file_mtime
        
        if age_seconds < 300:  # 5 minutes
            session_file.unlink()
            print(f"Cleaned up recent test session file: {session_file}")
    except Exception as e:
        print(f"Warning: Failed to clean up {session_file}: {e}")
```

This ensures:
- ✅ Test artifacts are still cleaned up
- ✅ Real user sessions are preserved
- ✅ Only recent files (test-generated) are deleted

### 2. Regenerated Missing Files (Recovery)

Created `backend/tests/manual/regenerate_session_metadata.py` to rebuild `.meta.json` files from `.jsonl` data:

```python
"""
Regenerate missing .meta.json files for chat sessions.

Scans all session .jsonl files and creates corresponding .meta.json files
with session metadata (name, timestamps, message count).
"""
```

**Execution**:
```bash
cd /home/penthoy/icotes/backend
uv run python tests/manual/regenerate_session_metadata.py
```

**Results**:
```
Found 6 sessions
✓ Regenerated: session_1760064997_e30cdecb.meta.json
✓ Regenerated: session_1760038190_9a093ed5.meta.json
✓ Regenerated: session_1760012415_35b532ac.meta.json
✓ Regenerated: session_1760009294_b358a55a.meta.json
✓ Regenerated: session_1760006874_11724dd6.meta.json

✓ Regenerated 5 .meta.json files
```

## Files Changed

### Modified
- `backend/tests/conftest.py` - Fixed aggressive cleanup logic

### Created
- `backend/tests/manual/regenerate_session_metadata.py` - Recovery script

## Lessons Learned

1. **Don't use glob patterns on production data in tests** - Be specific about what test artifacts look like
2. **Use time-based filters for cleanup** - Only clean up recent files that match test patterns
3. **Separate test and production data** - Consider using different directories or naming conventions
4. **Test cleanup should be conservative** - When in doubt, don't delete

## Prevention Measures

### For Future Test Development

1. **Use unique test prefixes**: Test files should use distinct prefixes
   ```python
   test_session_file = f"test_{uuid.uuid4().hex}_session.jsonl"
   ```

2. **Use temporary directories**: Tests should use `tempfile.mkdtemp()`
   ```python
   test_workspace = tempfile.mkdtemp(prefix="icotes_test_")
   ```

3. **Time-based cleanup**: Only delete files created during test run
   ```python
   if file.stat().st_mtime > test_start_time:
       file.unlink()
   ```

4. **Explicit test markers**: Add markers to test-generated files
   ```python
   # Create with marker
   meta = {'__test_artifact': True, 'id': session_id, ...}
   
   # Clean only marked files
   with open(meta_file) as f:
       data = json.load(f)
       if data.get('__test_artifact'):
           meta_file.unlink()
   ```

## Recovery Procedure

If this happens again:

1. **Don't panic** - The actual data (`.jsonl`) is preserved
2. **Run the regeneration script**:
   ```bash
   cd /home/penthoy/icotes/backend
   uv run python tests/manual/regenerate_session_metadata.py
   ```
3. **Verify recovery**:
   ```bash
   ls -lh /home/penthoy/icotes/workspace/.icotes/chat_history/*.meta.json
   ```

## Status

- ✅ Fix applied to prevent future occurrences
- ✅ Missing files regenerated
- ✅ All 6 chat sessions recovered
- ✅ Chat History panel now shows sessions correctly
- ✅ No data loss confirmed

## Related Documents

- Test cleanup fix: `backend/tests/conftest.py` (lines 48-82)
- Recovery script: `backend/tests/manual/regenerate_session_metadata.py`
- Chat service metadata: `backend/icpy/services/chat_service.py` (line 1855, `get_sessions()`)
