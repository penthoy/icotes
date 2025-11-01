# Image Generation Three Critical Issues Fix

**Date**: October 10, 2025  
**Issues**: Image editing failure, Low-quality thumbnail display, Wrong aspect ratio  
**Status**: ✅ Fixed

## Problems

### 1. Image Editing Failure
**Error**: "Failed to decode provided image for editing"

The agent attempted to edit images but passed the wrong value in `image_data`:
```json
{'image_data': 'img_1760079261502_93f6da8d.png', 'mode': 'edit', ...}
```

**Root Cause**: The `imageData` field (thumbnail base64) was included in the sanitized tool result sent to the LLM. When the LLM saw `imageData`, it used that field's value instead of `imageUrl` (file:// path) for editing.

### 2. Low-Quality Thumbnail Display
**Issue**: Generated images displayed in low quality (~100x100px thumbnail) instead of full resolution

The frontend widget prioritized `imageData` (embedded thumbnail) over `fullImageUrl` (API endpoint for full image).

```tsx
// OLD PRIORITY (WRONG)
Priority 1: imageData (thumbnail ~100x100px)
Priority 2: imageUrl (file:// path)

// Should be:
Priority 1: fullImageUrl (high-quality API endpoint)
Priority 2: imageUrl (file:// path)
Priority 3: imageData (thumbnail fallback)
```

### 3. Wrong Aspect Ratio
**Issue**: Model generated 1920x1080 (16:9) images instead of 1024x1024 (1:1) default

The agent chose `'aspect_ratio': '16:9'` despite instructions to default to 1:1. The GroqKimiAgent's custom system prompt didn't include the aspect ratio instruction from BASE_SYSTEM_PROMPT_TEMPLATE.

## Solutions

### Fix 1: Image Editing - Remove imageData from LLM Context

**File**: `/backend/icpy/agent/helpers.py` - `_sanitize_tool_result_for_llm()`

Remove `imageData` from sanitized results sent to LLM, keep only `imageUrl` (file:// path):

```python
# Before (BROKEN)
sanitized = {
    "success": True,
    "data": {
        "imageReference": data.get('imageReference'),
        "imageData": data.get('imageData'),  # ❌ LLM uses this instead of imageUrl
        "imageUrl": data.get('imageUrl'),
        ...
    }
}

# After (FIXED)
sanitized = {
    "success": True,
    "data": {
        "imageReference": data.get('imageReference'),
        "imageUrl": data.get('imageUrl'),  # ✅ REQUIRED for edit mode
        "filePath": data.get('filePath'),
        ...
        # Intentionally omit imageData, thumbnailUrl, fullImageUrl - not needed by LLM
    }
}
```

**Why This Works**:
- LLM now only sees `imageUrl` (file:// path) which is the correct format for editing
- `imageData` (thumbnail) is only in the unsanitized version sent to frontend widget
- Agent system prompt instructs to use `imageUrl` fields from previous responses

### Fix 2: High-Quality Image Display - Reorder Priority

**File**: `/src/icui/components/chat/widgets/ImageGenerationWidget.tsx` - `imageSrc` useMemo

Changed priority to favor high-quality `fullImageUrl`:

```tsx
// Before (WRONG)
const imageSrc = useMemo(() => {
  if (generationData.imageData) {  // ❌ Priority 1: Low-quality thumbnail
    return `data:image/png;base64,${generationData.imageData}`;
  }
  if (generationData.imageUrl) {  // Priority 2: Full image via file://
    ...
  }
  return null;
}, [generationData]);

// After (FIXED)
const imageSrc = useMemo(() => {
  if ((generationData as any).fullImageUrl) {  // ✅ Priority 1: High-quality API endpoint
    return (generationData as any).fullImageUrl;
  }
  if (generationData.imageUrl) {  // Priority 2: Full image via file://
    if (generationData.imageUrl.startsWith('file://')) {
      const filePath = generationData.imageUrl.replace('file://', '');
      return `/api/files/raw?path=${encodeURIComponent(filePath)}`;
    }
    return generationData.imageUrl;
  }
  if (generationData.imageData) {  // Priority 3: Thumbnail fallback
    return `data:image/png;base64,${generationData.imageData}`;
  }
  return null;
}, [generationData]);
```

**Benefits**:
- Full resolution images display immediately (via cached API endpoint)
- Thumbnail only used as fallback if API endpoints unavailable
- Better user experience with high-quality images

### Fix 3: Default Aspect Ratio - Add Instruction to Agent Prompt

**File**: `/backend/icpy/agent/agents/groq_kimi_agent.py` - system_prompt

Added explicit aspect ratio instruction:

```python
# Before (MISSING)
system_prompt = (
    f"You are {AGENT_NAME}, a helpful AI assistant with access to tools...\n\n"
    "CRITICAL - Image Handling:\n"
    "- When user asks to modify/edit/change an attached image...\n"
    "- Set mode='edit' when modifying existing images...\n\n"
    # ❌ No aspect ratio guidance
)

# After (FIXED)
system_prompt = (
    f"You are {AGENT_NAME}, a helpful AI assistant with access to tools...\n\n"
    "CRITICAL - Image Handling:\n"
    "- When user asks to modify/edit/change an attached image...\n"
    "- Set mode='edit' when modifying existing images...\n"
    "- For image generation: default to aspect_ratio='1:1' (square) unless user explicitly requests "
    "a different format or content clearly requires specific orientation.\n\n"  # ✅ Added
)
```

**Also Added Enhanced Logging**:

**File**: `/backend/icpy/agent/tools/imagen_tool.py` - `execute()`

Added detailed logging to understand agent's parameter choices:

```python
logger.info(f"=== ImagenTool.execute START ===")
logger.info(f"  kwargs: {kwargs}")  # Log all parameters
logger.info(f"  aspect_ratio: {kwargs.get('aspect_ratio', 'NOT SET')}")  # Specific aspect ratio check
logger.info(f"  image_data value: {preview}")  # What's being passed for editing
```

## Files Modified

1. `/backend/icpy/agent/helpers.py` - Remove imageData from LLM sanitized results
2. `/src/icui/components/chat/widgets/ImageGenerationWidget.tsx` - Prioritize fullImageUrl
3. `/backend/icpy/agent/agents/groq_kimi_agent.py` - Add aspect ratio instruction
4. `/backend/icpy/agent/tools/imagen_tool.py` - Enhanced logging

## Testing

### Test Case 1: Image Editing
```
1. User: "create image of a cat in the forest"
   Expected: Image generated successfully at 1024x1024 (1:1)

2. User: "add a hat to it"
   Expected: 
   - Agent uses file:// URL from previous response
   - ImagenTool successfully decodes image
   - Edit mode works correctly
   - New image shows cat with hat
```

### Test Case 2: Image Quality
```
1. Generate any image
2. Check displayed image in widget
   Expected:
   - Full resolution image loads (1920x1080 or 1024x1024)
   - Image is crisp and clear
   - Not blurry/pixelated thumbnail
```

### Test Case 3: Default Aspect Ratio
```
1. User: "create an image of a dog"
   Expected: Image generated at 1024x1024 (1:1) by default

2. User: "create a panoramic image of a mountain"
   Expected: Image generated at appropriate wide format (model can override for landscape content)

3. User: "create a 16:9 image of a sunset"
   Expected: Image generated at 1920x1080 (16:9) as explicitly requested
```

## Verification Steps

1. **Check Backend Logs** for imagen_tool parameters:
   ```
   === ImagenTool.execute START ===
     kwargs: {'prompt': '...', 'aspect_ratio': '1:1', ...}
     image_data value: file:///home/.../img_xxx.png  (for edits)
     mode: edit (for edits) / generate (for new images)
   ```

2. **Check Frontend Widget** displays high-quality images:
   - Open browser DevTools Network tab
   - Look for `/api/media/image/` or `/api/files/raw` requests
   - Verify full-size images are loading

3. **Test Image Editing** works end-to-end:
   - Generate initial image
   - Request modification ("add X to it")
   - Verify no "Failed to decode" errors
   - Verify modification applied to correct base image

## Expected Behavior After Fix

✅ **Image Editing**: 
- Agent correctly uses `file://` URLs from `imageUrl` field
- ImagenTool successfully loads previous images
- Edit mode works reliably

✅ **Image Quality**:
- Widget displays full resolution images by default
- Thumbnail only used as fallback
- Images are crisp and clear

✅ **Aspect Ratio**:
- Default 1024x1024 (1:1) for generic image requests
- Agent can still choose different ratios when appropriate
- User can explicitly request any aspect ratio

## Related Issues

- JSON parsing SyntaxError fix
- Streaming optimization (Option 1)
- Image preview and editing regression

## Notes

- The unsanitized tool result (sent to frontend) still contains all fields including `imageData`, `thumbnailUrl`, `fullImageUrl`
- Only the sanitized version (sent to LLM for context) has fields removed
- This separation allows optimal data for both LLM reasoning and UI display
- Thumbnail remains useful for instant preview during generation, but full image loads immediately after
