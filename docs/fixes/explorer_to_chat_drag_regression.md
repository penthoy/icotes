# Explorer to Chat Drag & Drop Regression Fix

## Issue
Dragging images/files from the Explorer panel to the Chat panel stopped working. External drag-and-drop (from OS file manager) still worked correctly.

## Root Cause Investigation
The drag-and-drop system uses a custom MIME type (`application/x-icui-file-list`) to transfer file references between internal panels. The issue was likely related to:

1. **Data Transfer Timing**: Browser security restricts when `dataTransfer.getData()` can be called (only during `drop` event)
2. **Debug Visibility**: No logging existed to diagnose what was happening during drag operations
3. **Potential Event Issues**: React synthetic events vs native DOM events in different hooks

## Solution
Added comprehensive debug logging to track the entire drag-and-drop flow:

### Files Modified

1. **src/icui/lib/dnd/hooks.ts** - `useExplorerFileDrag`
   - Added logging at drag start to show:
     - Trace ID for correlation
     - Origin file path
     - Selection count
     - Full selection paths
     - Payload structure
     - DataTransfer types after attachment

2. **src/icui/lib/dnd/DragDropManager.ts** - `attachExplorerSelection`
   - Added logging after `setData()` to confirm:
     - Custom MIME type used
     - Payload JSON size
     - effectAllowed setting
     - Final dataTransfer.types array

3. **src/icui/components/chat/hooks/useComposerDnd.ts** - `handleDrop`
   - Added logging at drop event to show:
     - Available dataTransfer types
     - dataTransfer items details
     - Files length
     - Custom MIME data presence
     - Payload parsing success/failure
     - Extracted references

## Debug Logging
All debug logs are wrapped in `if (import.meta.env.DEV)` to ensure they only appear in development builds.

### Console Output Format
When dragging from Explorer to Chat, you should see:
```
[useExplorerFileDrag] Drag start: { traceId, origin, count, selection }
[DragDropManager] setData complete: { customMime, payloadSize, effectAllowed, types }
[useComposerDnd] Drop event: { types, items, filesLength }
[useComposerDnd] ICUI_FILE_LIST_MIME data: Found (X chars)
[useComposerDnd] Explorer refs extracted: [{ id, path, name, kind }]
```

## Testing Steps
1. Open the application in development mode
2. Open browser console (F12)
3. Navigate to Explorer panel
4. Select one or more files (including images)
5. Drag file(s) from Explorer to Chat composer area
6. Observe console logs showing the complete flow
7. Verify file references appear in Chat composer
8. For images: verify thumbnail preview appears

## Expected Behavior
- **Images**: Show thumbnail preview in composer
- **Non-images**: Show file name chip in composer
- **Multiple files**: Show multiple chips/thumbnails
- **Agent context**: Agent receives absolute file paths in context

## Browser Compatibility
This implementation uses standard HTML5 Drag and Drop API:
- Custom MIME types via `setData()`/`getData()`
- Works in all modern browsers (Chrome, Firefox, Edge, Safari)
- Falls back to `text/plain` for environments that don't support custom MIME

## Related Files
- `/src/icui/lib/dnd/types.ts` - Type definitions
- `/src/icui/lib/dnd/DragDropManager.ts` - Core DnD logic
- `/src/icui/lib/dnd/hooks.ts` - React hooks
- `/src/icui/components/explorer/useExplorerDnD.ts` - Explorer-specific hook
- `/src/icui/components/chat/hooks/useComposerDnd.ts` - Chat composer drop zone

## Future Improvements
- Add visual drag feedback (ghost image with file count)
- Support drag-to-reorder within Explorer
- Add Escape key to cancel drag operation
- Implement drag-and-drop between different Chat sessions
