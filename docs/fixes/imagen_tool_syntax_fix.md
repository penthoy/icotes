# Imagen Tool Syntax Fix

**Date**: October 8, 2025  
**Issue**: Syntax error from malformed apply_patch operation  
**Status**: ✅ Fixed

## Problem

The previous apply_patch operation incorrectly merged code blocks into the wrong locations in `imagen_tool.py`, causing:
- Code inserted inside the `parameters` dictionary definition
- Unclosed brackets and parentheses
- `SyntaxError: closing parenthesis ']' does not match opening parenthesis '{' on line 78`

## Root Cause

The `apply_patch` tool inserted:
- Aspect ratio normalization logic inside the `width` parameter definition
- Post-processing code inside the parameters structure
- Missing closing brackets for the parameters dict

## Fix Applied

### 1. Restored Parameters Structure
```python
self.parameters = {
    "type": "object",
    "properties": {
        "prompt": {...},
        "image_data": {...},
        "image_mime_type": {...},
        "mode": {...},
        "save_to_workspace": {...},
        "filename": {...},
        "aspect_ratio": {...},
        "width": {...},
        "height": {...}  # FIXED: Properly closed
    },
    "required": ["prompt"]
}
```

### 2. Moved Aspect Ratio Logic to Correct Location
The aspect ratio normalization code was moved from inside the parameters dict to the proper location in the `execute()` method:

```python
# Get expected dimensions from aspect ratio (used only for post-process guidance)
expected_width, expected_height = None, None
if aspect_ratio and aspect_ratio in ASPECT_RATIO_SPECS:
    # Normalize target dimensions (longest side = 1024)
    raw_w, raw_h, _ = ASPECT_RATIO_SPECS[aspect_ratio]
    ratio = raw_w / raw_h
    if ratio >= 1:
        expected_width = 1024
        expected_height = int(round(1024 / ratio))
    else:
        expected_height = 1024
        expected_width = int(round(1024 * ratio))
    # ... augment prompt ...
```

### 3. Fixed Post-Processing Section
The aspect ratio enforcement logic was properly placed in the post-processing section:

```python
# Post-processing & aspect enforcement
if aspect_ratio and target_width and target_height and PIL_AVAILABLE and original_dimensions:
    ow, oh = original_dimensions
    if (ow, oh) != (target_width, target_height):
        # Crop and resize to match aspect ratio
        # ...
```

### 4. Verified Truncation Logic
The image data truncation logic with `imageReference` and thumbnail generation is properly placed at the end:

```python
# Build lightweight reference and optionally strip heavy fields
include_full_b64 = os.environ.get("INCLUDE_FULL_IMAGE_BASE64", "0") not in ("0", "false", "False")
# ... thumbnail generation ...
if not include_full_b64:
    if "imageData" in result_data:
        del result_data["imageData"]
```

## Verification

```bash
cd /home/penthoy/icotes/backend
export PYTHONPATH=$(pwd)
python -m py_compile icpy/agent/tools/imagen_tool.py
# No errors ✅
```

## Files Modified

- `/home/penthoy/icotes/backend/icpy/agent/tools/imagen_tool.py`

## Testing Recommendations

1. **Syntax Check**: ✅ Passed
2. **Import Check**: Run `python -c "from icpy.agent.tools.imagen_tool import ImagenTool; print('OK')"`
3. **Generation Test**: Generate an image with `aspect_ratio="16:9"` and verify:
   - Image dimensions are correct (e.g., 1024x576)
   - `imageData` is stripped from stored message
   - `imageReference` contains thumbnail
   - File is saved to workspace

## Related Issues

- Regression fix for base64 truncation (docs/plans/image_truncate_plan.md Phase 1)
- Aspect ratio enforcement implementation
- Syntax error from malformed patch operation

## Lessons Learned

- The `apply_patch` tool can sometimes incorrectly merge code blocks
- Always verify syntax after major structural changes
- Consider using `replace_string_in_file` with explicit context for critical sections
- Test compilation immediately after patching complex files
