# Hop Context Awareness Fixes

**Date**: October 20, 2025  
**Branch**: 43-bug-fix-and-stability-improvement  
**Related**: Continuation of hop imagen absolute path bug fix

## Overview

After fixing the hop imagen absolute path bug, two new issues emerged related to hop context awareness:

1. **Slow Image Loading**: Images generated on remote hop took ~1 minute to load in the UI widget
2. **Agent Path Confusion**: After hopping to different locations, the agent had trouble with correct workspace paths

## Issue #1: Slow Image Loading in Widget

### Problem

When an image was generated on a hopped remote server (e.g., hop1 @ 192.168.2.211), the UI widget would take almost a full minute to display the image after expanding the widget.

### Root Cause

The media API endpoint (`/api/media/image/{image_id}`) was not hop-aware:

1. ImageReference stored in tool result included `context` and `contextHost` fields
2. But the ImageReference dataclass itself didn't have these fields
3. The media endpoint tried to serve the file from local filesystem using `absolute_path`
4. File existed on remote hop1, not locally → 404 error
5. After ~1 minute timeout, it fell back to serving the thumbnail
6. This caused the perceived delay

**Key Insight**: The media endpoint only had access to the ImageReference object (from the reference service), not the full tool result that included context metadata.

### Solution

**Step 1**: Extend ImageReference dataclass to store context information

```python
# backend/icpy/services/image_reference_service.py

@dataclass
class ImageReference:
    # ... existing fields ...
    context_id: Optional[str] = None  # Context ID where image was created
    context_host: Optional[str] = None  # Host address if created on remote hop
```

**Step 2**: Update create_reference() to accept and store context

```python
async def create_reference(
    self,
    image_data: str,
    filename: str,
    prompt: str,
    model: str,
    mime_type: str = "image/png",
    *,
    only_thumbnail_if_missing: bool = True,
    context_id: Optional[str] = None,  # NEW
    context_host: Optional[str] = None,  # NEW
) -> ImageReference:
```

**Step 3**: Update imagen_tool to pass context info

```python
# backend/icpy/agent/tools/imagen_tool.py

context = await get_current_context()
ref = await image_service.create_reference(
    image_data=raw_base64,
    filename=saved_path or f"{image_id}.png",
    prompt=str(prompt),
    model=self._model,
    mime_type=mime_type,
    only_thumbnail_if_missing=True,
    context_id=context.get('contextId'),  # NEW
    context_host=context.get('host'),  # NEW
)
```

**Step 4**: Make media endpoint hop-aware

```python
# backend/icpy/api/endpoints/media.py

# Check if this image was created on a remote hop context
is_remote = image_ref.context_id and image_ref.context_id != "local" and image_ref.context_host

if is_remote and not thumbnail:
    # Image is on remote hop - fetch it via RemoteFS
    router_instance = await get_context_router()
    remote_fs = await router_instance.get_filesystem()
    
    if hasattr(remote_fs, 'read_file_binary'):
        image_data = await remote_fs.read_file_binary(image_ref.absolute_path)
        if image_data:
            return Response(
                content=image_data,
                media_type=image_ref.mime_type,
                headers={"Content-Disposition": f"inline; filename={image_ref.current_filename}"}
            )
```

### Impact

- Images generated on remote hops now load instantly in the UI
- No more 1-minute timeout delays
- Proper separation of local vs remote image serving

## Issue #2: Agent Path Confusion After Hopping

### Problem

When the user hopped to a different location or changed the workspace path, the agent would get confused about which workspace root to use. It would often investigate paths before generating images correctly.

### Root Cause

The agent's system prompt included workspace context from `create_agent_context()` which uses `_detect_workspace_root()`:

1. `_detect_workspace_root()` reads `WORKSPACE_ROOT` environment variable
2. This env var is static and doesn't update when user hops to remote servers
3. Agent was told it was in `/home/penthoy/icotes/workspace` even when hopped to `/home/penthoy/icotes/`
4. This mismatch caused the agent to be confused about correct paths

**Key Insight**: The system prompt was providing static local workspace information, but the actual execution context was dynamic (could be local or remote hop).

### Solution

Update `add_context_to_agent_prompt()` to dynamically fetch and include current hop context:

```python
# backend/icpy/agent/helpers.py

def add_context_to_agent_prompt(base_prompt: str, workspace_root: Optional[str] = None) -> str:
    """
    Includes dynamic hop context information so agent knows current workspace location.
    Works in both sync and async contexts by using asyncio.
    """
    context = create_agent_context(workspace_root)
    
    # Add dynamic hop context information
    try:
        import asyncio
        from .tools.context_helpers import get_current_context
        
        # Handle both sync and async contexts
        try:
            loop = asyncio.get_running_loop()
            # In async context - run in thread pool
            def get_context_sync():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(get_current_context())
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(get_context_sync)
                hop_context = future.result(timeout=2)
        except RuntimeError:
            # No event loop - safe to create one
            hop_context = asyncio.run(get_current_context())
        
        context_id = hop_context.get('contextId', 'local')
        is_hopped = context_id != 'local' and hop_context.get('status') == 'connected'
        
        if is_hopped:
            hop_info = f"""
**Current Context**: Hopped to remote server
- Context ID: `{context_id}`
- Host: `{hop_context.get('host', 'unknown')}`
- Username: `{hop_context.get('username', 'unknown')}`
- Current Directory: `{hop_context.get('cwd', '/')}`
- **Active Workspace Root**: `{hop_context.get('cwd', '/')}` ⚠️ Use this for file operations!

**Important**: When working with files, use the active workspace root shown above.
"""
            context['hop_context'] = hop_info
        else:
            context['hop_context'] = f"""
**Current Context**: Local (no hop active)
- **Active Workspace Root**: `{context['workspace_root']}`
"""
    except Exception as e:
        logger.warning(f"Failed to get hop context: {e}")
        context['hop_context'] = ""
    
    context_section = format_agent_context_for_prompt(context)
    return f"{base_prompt}\n\n{context_section}"
```

Also updated `format_agent_context_for_prompt()` to include the hop_context section:

```python
def format_agent_context_for_prompt(context: Dict[str, Any]) -> str:
    # ... existing code ...
    
    # Include hop context if present
    hop_context_str = context.get('hop_context', '')
    
    return f"""
## Agent Context Information

{time_info}

{hop_context_str}

{workspace_info if not hop_context_str else ''}

{caps_info}
...
"""
```

### Impact

- Agent now receives dynamic context in every request
- When hopped to remote, agent sees the remote workspace root and uses it correctly
- When local, agent sees local workspace root
- No more path confusion or unnecessary investigation
- Agent immediately knows where to save files based on current hop state

## Testing

### Test Case 1: Image Generation on Remote Hop

1. Hop to remote server (e.g., hop1)
2. Generate an image: "create an image of a cat"
3. Verify image loads quickly in widget (< 2 seconds)
4. Check logs: should see `[Media API] Image is on remote context` and successful fetch

### Test Case 2: Path Awareness After Hopping

1. Start in local context
2. Hop to remote (e.g., hop1 with workspace `/home/penthoy/icotes/`)
3. Generate an image immediately
4. Verify agent uses correct path without investigation
5. Check agent received hop context in system prompt

### Test Case 3: Multiple Hop Changes

1. Hop to remote1, generate image
2. Hop to local, generate image
3. Hop to remote2, generate image
4. Verify each image uses correct workspace and loads quickly

## Files Modified

1. `backend/icpy/services/image_reference_service.py`
   - Added `context_id` and `context_host` fields to ImageReference dataclass
   - Updated `create_reference()` signature

2. `backend/icpy/agent/tools/imagen_tool.py`
   - Pass context info when creating image reference

3. `backend/icpy/api/endpoints/media.py`
   - Made `/api/media/image/{image_id}` hop-aware
   - Fetch from remote FS when needed

4. `backend/icpy/agent/helpers.py`
   - Updated `add_context_to_agent_prompt()` to fetch current hop context dynamically
   - Updated `format_agent_context_for_prompt()` to include hop context section
   - Made it work in both sync and async contexts

## Related Issues

- Original hop imagen absolute path bug (fixed previously)
- Part of broader hop context awareness initiative

## Future Improvements

1. Consider caching hop context in ContextRouter to avoid repeated async calls
2. Add hop context to other tool results (not just images)
3. Consider making agent's chat function fully async for cleaner code
4. Add hop context visualization in UI to show user which context they're in

## Lessons Learned

1. **Dataclass vs Dict**: Tool results can have extra fields not in dataclasses - services need those fields in the dataclass to use them
2. **Static vs Dynamic Context**: Environment variables are static - need to fetch dynamic context at request time
3. **Sync/Async Bridge**: Python's asyncio.run() and ThreadPoolExecutor can bridge sync functions that need async data
4. **Logging is Critical**: Detailed logging at each layer helped identify the multi-layer issue quickly
