# Read File Widget UUID Display Fix

## Issue
When using `read_file` tool on a remote hop connection, file paths are displayed with raw UUID context IDs instead of friendly hop names.

### Symptoms
- **Local session**: Paths show as `local:/home/penthoy/icotes/workspace/file.png` ✓
- **Remote hop session**: Paths show as `eb491c42-989a-477a-b9a5-88bd31d36085:/home/penthoy/icotes/workspace/file.png` ✗
- **Expected**: Paths should show as `hop1:/home/penthoy/icotes/workspace/file.png` ✓

### Example from Session Logs
**Remote session (session_1761852041_98482fe7.jsonl)**:
```json
{
  "filePath": "eb491c42-989a-477a-b9a5-88bd31d36085:/home/penthoy/icotes/workspace/friendly_cat_with_pink_hat.png"
}
```

**Local session (session_1761851629_a05ff6cd.jsonl)**:
```json
{
  "filePath": "local:/home/penthoy/icotes/workspace/cat_with_green_hat.png"
}
```

## Root Cause Analysis

### Tool Chain
1. **read_file_tool.py**: Calls `format_namespaced_path(ctx_id, normalized_path)` (line 374, 440)
2. **path_utils.py**: `format_namespaced_path()` calls `_friendly_namespace_for_context(context_id)`
3. **path_utils.py**: `_friendly_namespace_for_context()` looks up friendly name from hop sessions

### Investigation
The UUID (`eb491c42-989a-477a-b9a5-88bd31d36085`) is the internal `contextId` from the hop session. The function should convert this to the friendly `credentialName` (e.g., "hop1").

### Potential Issues
1. **Session Lookup Failure**: `_friendly_namespace_for_context` cannot find matching session
2. **Missing credentialName**: Session exists but `credentialName` field is not set
3. **Case Sensitivity**: `contextId` vs `context_id` field name mismatch
4. **Timing Issue**: Session not fully initialized when path formatting occurs

## Fix Applied

### Changes to path_utils.py

Added comprehensive INFO-level logging to `_friendly_namespace_for_context()`:

**Line ~26-60**: Debug logging for session lookup
```python
import logging
logger = logging.getLogger(__name__)

# ... at start of function
logger.info(f"[PathUtils] Looking up friendly name for context_id={context_id}")
logger.info(f"[PathUtils] Available sessions: {[(s.get('contextId'), s.get('credentialName')) for s in sessions]}")

# ... in loop
logger.info(f"[PathUtils] Checking session {idx}: cid={cid}, target={context_id}, credentialName={s.get('credentialName')}")
if cid == context_id:
    # ... on match
    logger.info(f"[PathUtils] Found credentialName: {ns}")
    # ... or fallback
    logger.info(f"[PathUtils] No credentialName, using hop{idx}")

# ... on no match
logger.warning(f"[PathUtils] Context {context_id} not found in sessions, returning hop1 fallback")

# ... on exception
logger.error(f"[PathUtils] Error looking up friendly name: {e}", exc_info=True)
```

### Benefits
1. **Visibility**: Can see exactly which sessions are available and what names they have
2. **Debugging**: Can identify if context_id matches any session
3. **Field verification**: Can confirm if `credentialName` is set or missing
4. **Silent failure detection**: Logs when fallback to "hop1" occurs unexpectedly

## Testing Plan

### Prerequisites
1. Have an active remote hop connection (hop1 at 192.168.2.211)
2. Have some files in the remote workspace (e.g., cat PNG files)

### Test Steps
1. Restart backend to load updated logging
2. Open chat session on remote hop
3. Send query: "can you read the cat_with_green_hat.png file?"
4. Monitor backend logs: `tail -f /home/penthoy/icotes/logs/backend.log | grep PathUtils`
5. Check read_file tool output in chat session

### Expected Log Output
```
[PathUtils] Looking up friendly name for context_id=eb491c42-989a-477a-b9a5-88bd31d36085
[PathUtils] Available sessions: [('local', None), ('eb491c42-989a-477a-b9a5-88bd31d36085', 'hop1')]
[PathUtils] Checking session 1: cid=eb491c42-989a-477a-b9a5-88bd31d36085, target=eb491c42-989a-477a-b9a5-88bd31d36085, credentialName=hop1
[PathUtils] Found credentialName: hop1
```

### Expected Tool Output
```
✅ **Success**: {
  "isImage": True,
  "imageReference": {...},
  "filePath": "hop1:/home/penthoy/icotes/workspace/cat_with_green_hat.png",
  "absolutePath": "/home/penthoy/icotes/workspace/cat_with_green_hat.png",
  "contextId": "eb491c42-989a-477a-b9a5-88bd31d36085"
}
```

### Possible Diagnostic Outcomes

**Scenario A: credentialName is missing**
```
[PathUtils] Checking session 1: cid=eb491c42-..., target=eb491c42-..., credentialName=None
[PathUtils] No credentialName, using hop1
```
→ Fix: Ensure `credentialName` is set when hop session is created

**Scenario B: contextId mismatch**
```
[PathUtils] Checking session 1: cid=some-other-uuid, target=eb491c42-..., credentialName=hop1
[PathUtils] Context eb491c42-... not found in sessions, returning hop1 fallback
```
→ Fix: Investigate why context IDs don't match (session cleanup issue?)

**Scenario C: No remote sessions**
```
[PathUtils] Available sessions: [('local', None)]
[PathUtils] Context eb491c42-... not found in sessions, returning hop1 fallback
```
→ Fix: Hop session is disconnected or not properly registered

## Related Issues

This fix is related to:
1. **Semantic search remote hop bug**: Both issues stem from hop context handling
2. **Widget display**: Widgets rely on `filePath` field for display labels
3. **imagen_tool path bug** (previously fixed): Similar issue with absolute path reporting

## Files Modified
- `/home/penthoy/icotes/backend/icpy/services/path_utils.py`
  - Lines ~26-60: Added comprehensive logging to `_friendly_namespace_for_context()`

## Status
- [x] Added comprehensive INFO-level logging
- [ ] Restart backend server
- [ ] Test read_file on remote hop with logs
- [ ] Identify actual root cause from logs
- [ ] Implement targeted fix if credentialName is missing or context lookup fails
