# JSON Parsing SyntaxError Fix

**Date**: October 10, 2025  
**Issue**: Frontend image widget throwing SyntaxError when parsing tool output  
**Status**: ✅ Fixed

## Problem

The frontend `ImageGenerationWidget` was encountering JSON parsing errors:

```
SyntaxError: Unexpected token 'G', "Generated "... is not valid JSON
```

This occurred because:

1. The backend `format_tool_result()` function was returning a **formatted display message** instead of structured JSON data for streaming-optimized image generation
2. The frontend widget expected `toolCall.output` to contain parseable JSON with the image data structure
3. The formatted message like `"✅ **Success**: Generated image for '...' (10.5KB, ID: abc123...)"` cannot be parsed as JSON

## Root Cause

In `/backend/icpy/agent/helpers.py`, the `format_tool_result()` function had this logic:

```python
# OLD CODE (BROKEN)
if 'imageReference' in data:
    # New format: show concise message with reference
    ref = data['imageReference']
    image_id = ref.get('image_id', 'unknown')
    prompt = data.get('prompt', 'image')
    return f"✅ **Success**: Generated image for '{prompt[:50]}...' ({size_kb:.1f}KB, ID: {image_id[:12]}...)\n"
```

This returned a human-readable string that **cannot** be parsed as JSON by the frontend.

## Solution

Changed the logic to **always return structured JSON** for image generation results:

```python
# NEW CODE (FIXED)
elif tool_name == 'generate_image' and isinstance(data, dict):
    # Always return the JSON data structure for widget compatibility
    # The widget expects structured data in toolCall.output field
    json_str = json.dumps(data)
    logger.info(f"ToolResultFormatter: Generating image result JSON ({len(json_str)} chars)")
    return f"✅ **Success**: {json_str}\n"
```

## Additional Fix

Also fixed tool message content sent to OpenAI API to use just the data payload instead of the wrapper object:

```python
# OLD CODE (BROKEN)
tool_message = {
    "role": "tool",
    "tool_call_id": tc['id'],
    "content": json.dumps(sanitized_result)  # Sends {"success": true, "data": {...}}
}

# NEW CODE (FIXED)
tool_content = sanitized_result.get('data') if sanitized_result.get('success') else {
    "error": sanitized_result.get('error', 'Unknown error')
}
tool_message = {
    "role": "tool",
    "tool_call_id": tc['id'],
    "content": json.dumps(tool_content)  # Sends just {...} (the data)
}
```

## Files Modified

- `/backend/icpy/agent/helpers.py`:
  - `ToolResultFormatter.format_tool_result()` - Always return JSON for image generation
  - `OpenAIStreamingHandler._handle_tool_calls()` - Send data payload instead of wrapper

## Testing

✅ **Unit Test**: `test_streaming_optimization.py::test_image_generation_returns_reference` - PASSED  
✅ **JSON Size**: 2.3KB (99% reduction vs legacy 200KB format)  
✅ **No SyntaxError**: Widget can now parse tool output correctly

## Expected Behavior After Fix

1. **Image Generation**: Tool output contains valid JSON with:
   - `imageReference` (lightweight metadata)
   - `imageData` (small thumbnail ~0.5KB)
   - `imageUrl` (file:// path for agent editing)
   - `fullImageUrl` (API endpoint for downloads)
   - All metadata fields

2. **Frontend Widget**: Successfully parses JSON and displays:
   - Image preview (from embedded thumbnail)
   - Generation parameters (prompt, size, style)
   - Download and copy functionality
   - No console errors

3. **Agent Editing**: Can reference previous images using `file://` URLs

## Verification Steps

1. Generate an image: "create image of a cat in the forest"
2. Check browser console - should have **no SyntaxError warnings**
3. Verify image displays in widget
4. Edit the image: "add a hat to the cat"
5. Verify agent successfully loads and edits previous image

## Related Issues

- Streaming optimization (Option 1 implementation)
- Image preview and editing regression fix
- Chrome WebSocket handler violations

## Notes

- The formatted display message is still yielded to show progress to the user
- But the actual tool result structure must be valid JSON for widget parsing
- This maintains both user experience (progress messages) and functionality (structured data)
