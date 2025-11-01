# Context Router Display Names Fix (Task #4)

## Issue
The chat/hop integration was displaying context UUIDs instead of friendly hop names in tool outputs:
- **Before**: `eb491c42-989a-477a-b9a5-88bd31d36085:/path/to/image.png`
- **After**: `hop1:/path/to/image.png`

This occurred in:
1. Tool result data structures (e.g., image generation)
2. Message logs and debugging output
3. Widget displays showing file paths

## Root Cause
Tools were returning the raw `contextId` (UUID) instead of converting it to the friendly credential name:
- `context.get('contextId')` → `eb491c42-989a-477a-b9a5-88bd31d36085` (wrong)
- Should be → `hop1` (correct, from hop session's credentialName)

The path_utils module already had `_friendly_namespace_for_context()` helper to do this conversion, but tools weren't using it.

## Solution

### 1. Updated `backend/icpy/agent/tools/imagen_tool.py`

**Added import:**
```python
try:
    from ...services.path_utils import _friendly_namespace_for_context
except ImportError:
    _friendly_namespace_for_context = None  # Graceful fallback
```

**Converted context_id to friendly name before returning result:**
```python
# Convert context_id to friendly name (hop1, local, etc) for display
context_id = context.get('contextId', 'local')
context_name = context_id
try:
    if _friendly_namespace_for_context is not None:
        context_name = await _friendly_namespace_for_context(context_id)
except Exception as e:
    logger.warning(f"[ImagenTool] Failed to get friendly namespace for context {context_id}: {e}")
    context_name = context_id

# Then use context_name in result:
result_data = {
    "context": context_name,  # Now displays friendly name (hop1, local, etc)
    "contextHost": context.get('host')
    # ... other fields
}
```

**Impact:**
- Image generation tool results now show `hop1` instead of UUID
- When logged via ToolResultFormatter, friendly name appears in logs
- Widgets receive friendly name in `context` field

### 2. Supporting Systems

The following systems now work correctly to provide friendly names:

**Path Utils (`backend/icpy/services/path_utils.py`):**
- `_friendly_namespace_for_context(context_id)` → queries HopService for credentialName
- `format_namespaced_path(context_id, abs_path)` → returns `hop1:/path` format
- `get_display_path_info(path)` → returns structured path with friendly names

**Tools using path utils:**
- `semantic_search_tool.py` - uses `get_display_path_info()` for search results
- `read_file_tool.py` - uses helpers for display
- `create_file_tool.py` - uses helpers for display
- `replace_string_tool.py` - uses helpers for display

### 3. Frontend Integration

Frontend components already receive paths in the format:
```json
{
  "context": "hop1",           // Friendly name (now correct)
  "absolutePath": "/path/to/file.png",
  "contextHost": "192.168.2.211"
}
```

ImageGenerationWidget and other widgets can now reliably display:
- Path with namespace: `hop1:/path/to/file.png`
- Instead of: `eb491c42-...:/path/to/file.png`

## Testing

### Manual Test Scenario
1. Activate a hop connection (e.g., hop1 with SSH credentials)
2. Request agent to generate and save an image
3. Observe tool result in chat message:
   - Context should show: `"context": "hop1"`
   - Not: `"context": "eb491c42-989a-477a-b9a5-88bd31d36085"`
4. Message should log friendly name correctly

### Expected Outputs

**Tool Result (imagen_tool):**
```json
{
  "prompt": "...",
  "context": "hop1",           // ✓ Friendly name
  "contextHost": "192.168.2.211",
  "absolutePath": "/home/user/images/generated.png",
  "savedToWorkspace": true,
  ...
}
```

**Log Output:**
```
[ImagenTool] emit result | ctx=hop1 host=192.168.2.211 saved=True abs=/home/user/images/generated.png ...
```

**Message Display:**
- Image widget shows: `context: hop1` (friendly label in metadata)
- Tool output shows: `hop1:/home/user/images/generated.png` format

## Files Modified
- `backend/icpy/agent/tools/imagen_tool.py` (added import and context name conversion)

## Backward Compatibility
- Graceful fallback to context_id if `_friendly_namespace_for_context` unavailable
- Existing code using UUID still works (no breaking changes)
- Will benefit from friendly names once fix is deployed

## Related Tasks
- **Phase 4 Task #2**: [Drag-drop remote hop image embedding fix](./drag_drop_remote_hop_image_embedding_fix.md)
- **Phase 4 Task #3**: Session debug sidecar (pending)

## Future Improvements
1. Apply same fix to other tools that display context information
2. Create utility helper in base_tool.py for context name conversion
3. Add unit tests for _friendly_namespace_for_context() with various context IDs
4. Update widget components to display namespace badge in UI
