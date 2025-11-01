# ImagenTool Bug Fixes - Widget Size and Empty File Issues

**Date:** January 2025  
**Issues Fixed:** 2 critical bugs identified during manual testing

## Issues Identified

### Issue 1: Widget Size Display Incorrect ❌
**Problem:** The ImageGenerationWidget displayed "Size: 1024x1024" even when the image was generated at 512x512 resolution.

**Root Cause:** 
- Widget read `size` from tool input parameters (line 64 of ImageGenerationWidget.tsx)
- Tool did not include actual image dimensions in output
- Input size was just a default fallback, not the actual generated image size

**Impact:** Misleading information shown to user about actual image dimensions

### Issue 2: Custom Named File Empty (0 bytes) ❌
**Problem:** When using custom filename (e.g., "icon.png"), the file was created but had 0 bytes and was corrupted.

**Root Cause:**
- `_save_image_to_workspace()` called `filesystem_service.write_file()` with binary `image_bytes`
- The `write_file()` method signature expects `content: str`, not bytes
- Method tried to write bytes as string, resulting in empty/corrupted file
- Auto-generated files worked because they were written differently (legacy code path)

**Impact:** User couldn't use custom filenames - files were unusable

## Fixes Implemented

### Fix 1: Add Actual Image Dimensions to Output ✅

**Changes:**
1. **Added `_get_image_dimensions()` method** (`imagen_tool.py`):
   - Uses PIL to extract actual width and height from image bytes
   - Returns `(width, height)` tuple or `None` if PIL unavailable
   - Handles errors gracefully

2. **Updated `execute()` method** (`imagen_tool.py`):
   - Calls `_get_image_dimensions()` after resizing
   - Adds three new fields to result data:
     - `"size"`: String format "512x512" (matches widget expectation)
     - `"width"`: Integer width in pixels
     - `"height"`: Integer height in pixels
   - Logs actual dimensions for debugging

3. **Updated ImageGenerationWidget** (`ImageGenerationWidget.tsx`):
   - Added code to override `data.size` from output if available
   - Falls back to input size (1024x1024) if output doesn't specify
   - Now displays actual image dimensions, not requested dimensions

**Result:** Widget now correctly shows "Size: 512x512" when image is generated at that resolution

### Fix 2: Fix Binary File Write ✅

**Changes to `_save_image_to_workspace()` method:**

1. **For Local Context:**
   - Write bytes directly using standard Python `open(filepath, 'wb')`
   - No longer uses `filesystem_service.write_file()` for binary data
   - Ensures directory exists with `os.makedirs()`
   - Fully reliable for local file writes

2. **For Remote Context (Hop):**
   - Detects if context is remote using `context_name != 'local'`
   - Gets RemoteFileSystemAdapter from ContextRouter
   - Writes directly via SFTP using `sftp.open(remote_path, 'wb')`
   - Handles bytes natively without string conversion
   - Falls back to local write if remote fails

3. **Removed Problematic Code:**
   - No longer passes bytes to `filesystem_service.write_file()`
   - Avoids the string/bytes type mismatch entirely

**Result:** Custom filenames now work correctly, files have proper content and size

## Code Changes Summary

### File: `backend/icpy/agent/tools/imagen_tool.py`

**New Method Added:**
```python
def _get_image_dimensions(self, image_bytes: bytes) -> Optional[Tuple[int, int]]:
    """Extract actual dimensions from image bytes."""
    if not PIL_AVAILABLE:
        return None
    try:
        img = Image.open(io.BytesIO(image_bytes))
        return img.size  # Returns (width, height)
    except Exception as e:
        logger.error(f"Failed to get image dimensions: {e}")
        return None
```

**Modified: `_save_image_to_workspace()` method** (~100 lines):
- Split into local and remote write paths
- Local: Direct binary file write with `open(filepath, 'wb')`
- Remote: Direct SFTP write via `sftp.open(remote_path, 'wb')`
- Removed dependency on `filesystem_service.write_file()` for binary data

**Modified: `execute()` method**:
- Added call to `_get_image_dimensions(image_bytes)` after resizing
- Added three new fields to result_data: `size`, `width`, `height`
- Proper dimension reporting in result

### File: `src/icui/components/chat/widgets/ImageGenerationWidget.tsx`

**Modified: Output parsing section** (~5 lines):
```typescript
// Override size from output if available (actual dimensions)
if (output.size) {
  data.size = output.size;
}
```

## Testing Recommendations

### Test Case 1: Default Size
```
"Generate a blue circle"
```
**Expected:** 
- Widget shows "Size: 1024x1024" (default generation size)
- File downloads correctly
- Custom filename works

### Test Case 2: Custom Resolution
```
"Generate a red square at 512x512 resolution and save it as test_square"
```
**Expected:**
- Widget shows "Size: 512x512" (actual generated size)
- Downloaded file is 512x512 pixels
- File "test_square.png" exists and is valid (not 0 bytes)
- File opens correctly in image viewer

### Test Case 3: Custom Resolution with Custom Name
```
"Generate an icon for icotes with 256x256 resolution and name it app_icon"
```
**Expected:**
- Widget shows "Size: 256x256"
- File "app_icon.png" is 256x256 pixels
- File has proper content (not empty)
- File size is reasonable (10-50KB typically)

### Test Case 4: Remote Hop + Custom Name
```
# After connecting to hop
"Generate a diagram at 800x600 resolution and save it as architecture on the remote server"
```
**Expected:**
- Image generated on remote server
- File "architecture.png" exists on remote
- File is valid 800x600 pixel image
- Widget shows "Size: 800x600"

## Technical Details

### Why Direct Binary Write?

The filesystem services have different signatures:
- **Local FileSystemService:** `write_file(path: str, content: str)`
- **Remote SFTP:** Native binary support via `sftp.open(path, 'wb')`

Rather than trying to make one interface work for both, we now:
1. Detect context (local vs remote)
2. Use appropriate low-level write method
3. Bypass the abstraction layer for binary data

This is more reliable and follows the "right tool for the job" principle.

### Dimension Detection

Using PIL (Pillow) for dimension detection because:
- Already a dependency for resizing
- Reliable and fast
- Handles all image formats we support
- Provides exact pixel dimensions

## Backward Compatibility

✅ **Fully backward compatible:**
- Auto-generated filenames still work (unchanged)
- Images without custom names use old path
- Widget falls back to input size if output doesn't specify
- No breaking changes to tool interface
- Existing tool calls continue to work

## Files Modified

1. `backend/icpy/agent/tools/imagen_tool.py` - Main fixes
2. `src/icui/components/chat/widgets/ImageGenerationWidget.tsx` - Widget display fix

## Additional Fix: Widget Size During Generation

### Issue 3: Widget Shows 1024x1024 During Generation ❌
**Problem:** While generating, widget displayed "Size: 1024x1024" even when requesting 2048x2048 or 512x512.

**Root Cause:** 
- Widget checked for `input.size` parameter
- Phase 7 uses `input.width` and `input.height` instead
- Default fallback was "1024x1024" when `input.size` not found

**Solution:**
- Updated widget to check for `width`/`height` parameters first
- Constructs size string from width/height (e.g., "2048x2048")
- Falls back to `input.size` or default only if width/height not specified
- Now correctly shows requested dimensions during generation

**Code Change:**
```typescript
// Check for width/height parameters first (Phase 7 resolution control)
if (input.width || input.height) {
  const w = input.width || 'auto';
  const h = input.height || 'auto';
  data.size = `${w}x${h}`;  // Shows "2048x2048" during generation
} else {
  data.size = input.size || '1024x1024';  // Fallback
}
```

**Result:** Widget now shows correct dimensions throughout the entire generation process

## Summary

All three issues have been fixed:

1. ✅ **Widget Size Display:** Now shows actual generated image dimensions after completion
2. ✅ **Empty File Issue:** Custom filenames now create valid, properly-sized image files
3. ✅ **Widget Size During Generation:** Shows requested dimensions while generating (not default 1024x1024)

The fixes properly handle both local and remote (hop) contexts, and maintain full backward compatibility with existing functionality.
