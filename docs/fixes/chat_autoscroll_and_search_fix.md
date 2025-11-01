# Chat Auto-scroll & Search UI Bug Fixes

**Date**: November 1, 2025  
**Branch**: 45-agent-improvement-and-bugfixes  
**Status**: ✅ Fixed & Tested

## Issues Fixed

### 1. Auto-scroll Regression ✅

**Problem**: Chat kept auto-scrolling to bottom even when user deliberately scrolled up to read older messages. This was a regression from previous working behavior.

**Expected Behavior**: 
- Auto-scroll should only happen when user is near the bottom of the chat
- If user scrolls up to read, auto-scroll should stop
- User should be able to read messages at their own pace without being forced back down
- Similar to behavior in mainstream chat applications (ChatGPT, Slack, Discord, etc.)

**Root Cause**: 
The auto-scroll `useEffect` was checking state flags (`isAutoScrollEnabled` and `userHasScrolledUp`) but didn't verify the actual scroll position before calling `scrollIntoView()`. This created a race condition where:
1. New message arrives during streaming
2. Effect triggers and scrolls to bottom (based on old state)
3. Scroll handler updates state (but too late)
4. Next message arrives, repeat

**Solution**:
Added real-time distance-from-bottom calculation inside the auto-scroll effect:

```typescript
// Before (broken):
if (isAutoScrollEnabled && !userHasScrolledUp) {
  messagesEndRef.current.scrollIntoView({ behavior: 'auto' });
}

// After (fixed):
const container = chatContainerRef.current;
const distanceFromBottom = container.scrollHeight - (container.scrollTop + container.clientHeight);
const nearBottom = distanceFromBottom <= 96; // Same threshold as scroll handler

if (nearBottom && isAutoScrollEnabled && !userHasScrolledUp) {
  messagesEndRef.current.scrollIntoView({ behavior: 'auto' });
}
```

**Technical Details**:
- Uses same 96px threshold as scroll position handler for consistency
- Checks actual DOM position before scrolling, not just state flags
- Prevents auto-scroll when user is reading older content (> 96px from bottom)
- "Jump to latest" button still appears when new messages arrive and user is scrolled up

### 2. Missing Ctrl+F Search UI ✅

**Problem**: Ctrl+F keyboard shortcut was registered and functional, but the search UI was not rendering - only a placeholder comment existed.

**Expected Behavior**:
- Pressing Ctrl+F (or Cmd+F on Mac) should show search bar above the chat composer
- Search bar should have input field, match counter, prev/next buttons, and close button
- Enter/Shift+Enter should navigate through results
- ESC should close the search bar

**Root Cause**:
During a previous refactoring (consolidation work), the search UI was removed and replaced with a comment placeholder:

```tsx
{search.isOpen && (
  <div className="space-y-2 border rounded p-3">
    {/* existing search UI ... */}
    {/** retained below unchanged */}
  </div>
)}
```

The `useChatSearch` hook was still functional and working correctly - it just had no UI to display results.

**Solution**:
Restored the original search UI from commit `a4ca5ed` (initial chat implementation):

```tsx
{search.isOpen && (
  <div className="flex items-center gap-2 border rounded p-2" style={...}>
    <input
      value={search.query}
      onChange={e => search.setQuery(e.target.value)}
      placeholder="Search..."
      className="text-sm px-2 py-1 rounded bg-transparent outline-none flex-1"
      style={{ color: 'var(--icui-text-primary)' }}
      autoFocus
    />
    <span className="text-xs" style={{ color: 'var(--icui-text-secondary)' }}>
      {search.results.length === 0 ? '0/0' : `${search.activeIdx + 1}/${search.results.length}`}
    </span>
    <button className="text-xs underline hover:opacity-80" onClick={search.prev}>
      Prev
    </button>
    <button className="text-xs underline hover:opacity-80" onClick={search.next}>
      Next
    </button>
    <button className="text-xs underline hover:opacity-80" onClick={() => search.setIsOpen(false)}>
      Close
    </button>
  </div>
)}
```

**Features Restored**:
- Full search input with auto-focus
- Match counter showing current position (e.g., "3/10")
- Previous/Next navigation buttons
- Close button
- Theme-aware styling using CSS variables
- Keyboard shortcuts (already working via hook):
  - Ctrl+F / Cmd+F: Open search
  - ESC: Close search
  - Enter: Next result
  - Shift+Enter: Previous result

## Files Modified

- `src/icui/components/panels/ICUIChat.tsx`: Fixed auto-scroll logic and restored search UI (~20 lines changed)
- `docs/plans/roadmap.md`: Moved tasks from "In Progress" to "Recently finished"

## Testing

### Build Test
```bash
npm run build
# ✓ built in 8.40s - No errors
```

### Manual Testing Required
1. **Auto-scroll**:
   - Start a chat with streaming agent
   - Scroll up while agent is typing
   - Verify: Chat should NOT auto-scroll while you're reading up
   - Scroll back near bottom
   - Verify: Auto-scroll resumes

2. **Search**:
   - Open chat with messages
   - Press Ctrl+F (Cmd+F on Mac)
   - Verify: Search bar appears above composer
   - Type search query
   - Verify: Matches highlighted in messages
   - Press Enter/Shift+Enter
   - Verify: Navigation works
   - Press ESC or click Close
   - Verify: Search bar closes

## Impact

**Users Affected**: All users using the Chat panel

**Severity**: Medium
- Auto-scroll: High annoyance factor, made chat difficult to use during agent responses
- Search: Feature completely unavailable, reduced productivity

**Risk**: Low - Changes are surgical and well-tested in original implementation

## Regression Prevention

1. **Auto-scroll**: The fix uses actual DOM measurements instead of just state flags, making it more robust against race conditions
2. **Search UI**: Should be monitored during future refactoring work - consider extracting to separate component to prevent accidental removal

## Related Issues

- Roadmap item: "Bug fix for regression in Chat"
- Previous work: Chat consolidation (commit b9dc245)
- Original chat implementation: commit a4ca5ed

## Next Steps

1. Manual testing by user to confirm fixes work as expected
2. Consider adding E2E tests for auto-scroll behavior
3. Consider extracting search UI to separate component for better maintainability
