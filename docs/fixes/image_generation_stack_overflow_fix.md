# Stack Overflow Fix: Image Generation Widget Crash

## Issue
When dragging an image from Explorer to Chat and asking the agent to edit it (e.g., "add a hat to it"), the webapp would crash with a "Maximum call stack size exceeded" error, causing the page to go completely blank.

## Root Cause
The imagen_tool returns a large JSON response that includes:
1. `imageReference` object with metadata
2. `thumbnail_base64` field containing ~10KB+ of base64-encoded image data

When the agent formats the tool response as `✅ **Success**: {entire_json_object}` in the message content, this huge JSON (including the giant base64 string) gets embedded in the message text.

The `cleanupLeakedCode()` function in `genericmodel.tsx` uses a regex pattern to remove these Success blocks:
```typescript
.replace(/✅\s*\*\*Success\*\*:\s*\{[\s\S]*?\}\s*\n/g, '')
```

This regex pattern with `[\s\S]*?` (non-greedy match) causes **catastrophic backtracking** when dealing with a 10KB+ string, leading to stack overflow.

## Solution
Replaced the dangerous regex with a safer line-by-line parser that:

1. **Iterates through lines** instead of using regex
2. **Tracks brace depth** to properly detect when Success blocks end
3. **Skips Success block lines** without causing backtracking
4. **Increases threshold** for long-line detection from 300 to 500 chars (to catch base64 strings)

### Files Modified
- `src/icui/components/chat/modelhelper/genericmodel.tsx` - `cleanupLeakedCode()` method

### Code Changes
```typescript
// OLD (causes catastrophic backtracking on large JSON):
.replace(/✅\s*\*\*Success\*\*:\s*\{[\s\S]*?\}\s*\n/g, '')

// NEW (safe line-by-line parsing):
const lines = cleaned.split('\n');
const filtered: string[] = [];
let inSuccessBlock = false;
let braceDepth = 0;

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  
  // Detect start of Success block
  if (/✅\s*\*\*Success\*\*:\s*\{/.test(line)) {
    inSuccessBlock = true;
    braceDepth = 1;
    // Track braces...
    continue;
  }
  
  // Track braces while in block...
  if (inSuccessBlock) {
    // Skip until block ends
    continue;
  }
  
  filtered.push(line);
}
```

## Testing
1. Drag image from Explorer to Chat ✅
2. Ask agent to edit the image (e.g., "add a hat")  ✅
3. Agent successfully generates edited image ✅
4. Webapp displays result without crashing ✅
5. No stack overflow errors in console ✅

## Related Issues
- **Explorer drag-drop regression** - Also fixed in the same session (added debug logging)
- **Image Reference System** - The `thumbnail_base64` is part of Phase 1 storage optimization

## Prevention
To prevent similar issues in the future:

1. **Avoid regex patterns with `[\s\S]*?` on user-generated content** - These cause catastrophic backtracking on large inputs
2. **Use line-by-line parsing** for structured data with nesting
3. **Set reasonable size limits** for embedded data (thumbnails should be small, ~5-10KB max)
4. **Test with large payloads** during development

## Performance Impact
- **Before**: Stack overflow crash (100% failure rate)
- **After**: Fast line-by-line parsing (~O(n) complexity, no backtracking)
- **Message processing**: No noticeable performance impact

## Notes
The drag-and-drop from Explorer to Chat **IS working correctly**. The agent receives the image reference properly. The crash only happened during the cleanup phase when processing the tool response message content.
