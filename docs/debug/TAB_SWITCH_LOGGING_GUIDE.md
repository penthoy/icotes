# Tab Switch Logging Guide

## What Was Added

Enhanced logging has been added to capture ALL tab interactions - clicks, drags, and activations. Every action now produces immediate console output.

## Log Prefixes to Watch For

When you interact with tabs, you should see these logs in the browser console:

### Component Lifecycle
- `[TAB-CONTAINER-MOUNT]` - When a tab container is created
- `[TAB-CONTAINER-UNMOUNT]` - When a tab container is destroyed
- `[PANEL-AREA-MOUNT]` - When a panel area is created
- `[PANEL-AREA-UNMOUNT]` - When a panel area is destroyed

### Tab Clicks
- `[TAB-CLICK]` - **Immediate** log when you click on any tab
  - Shows: tab title, tab ID, and area ID
  - Example: `[TAB-CLICK] User clicked tab: Chat History (id: chat-history-123) in area: top-center`

### Tab Activation Flow
- `[TAB-ACTIVATE-REQUEST]` - Request to activate a tab (from click or programmatic)
- `[TAB-ACTIVATE-BLOCKED]` - Activation blocked (drag in progress or rapid switching)
- `[TAB-ACTIVATE-DEBOUNCE]` - Setting up 100ms debounce timer
- `[TAB-ACTIVATE-EXECUTE]` - Actually executing the activation (after debounce)
- `[PANEL-AREA]` - Panel area handling the activation

### Drag and Drop
- `[TAB-DRAG-START]` - When you start dragging a tab
  - Shows: tab title, tab ID, source area
- `[TAB-DROP]` - When you drop on a tab position
  - Shows: drop position index and area ID
- `[PANEL-AREA-DRAG]` - Panel area detecting drag enter/leave
  - Shows: area ID and drag counter
- `[PANEL-AREA-DROP]` - Panel area receiving a dropped panel
  - Shows: panel ID, source area, target area, whether accepted/rejected

## Testing Steps

### Test 1: Simple Tab Click
1. Open browser DevTools (F12) → Console tab
2. Click on "Chat History" tab
3. **Expected logs (immediate)**:
   ```
   [TAB-CLICK] User clicked tab: Chat History (id: ...) in area: ...
   [TAB-ACTIVATE-REQUEST] Requesting tab activation: ..., current: ..., area: ...
   [TAB-ACTIVATE-DEBOUNCE] Setting up debounced activation for: ...
   [TAB-ACTIVATE-EXECUTE] Executing activation for: ..., was: ...
   [PANEL-AREA] Tab activate request in area ...: ...
   [PANEL-AREA] Tab activated in area ...: ...
   ```

### Test 2: Click Another Tab (e.g., Hop)
1. Click on "Hop" tab
2. **Expected logs (immediate)**:
   ```
   [TAB-CLICK] User clicked tab: Hop (id: ...) in area: ...
   [TAB-ACTIVATE-REQUEST] Requesting tab activation: ..., current: ..., area: ...
   [TAB-ACTIVATE-DEBOUNCE] Setting up debounced activation for: ...
   [TAB-ACTIVATE-EXECUTE] Executing activation for: ..., was: ...
   [PANEL-AREA] Tab activate request in area ...: ...
   [PANEL-AREA] Tab activated in area ...: ...
   ```

### Test 3: Drag Tab to Different Area
1. Click and hold on a tab (e.g., "Chat History")
2. Drag it to another area
3. Release to drop
4. **Expected logs**:
   ```
   [TAB-DRAG-START] User started dragging tab: Chat History (id: ...) from area: ...
   [PANEL-AREA-DRAG] Drag enter area ..., counter: 1
   [PANEL-AREA-DRAG] Started drag over area ...
   [TAB-DROP] User dropped on tab position ... in area: ...
   [PANEL-AREA-DROP] Drop event in area ...
   [PANEL-AREA-DROP] Panel: ..., Source: ..., Target: ...
   [PANEL-AREA-DROP] Accepting panel drop, will activate: ...
   [PANEL-AREA-DRAG] Drag leave area ..., counter: 0
   [PANEL-AREA-DRAG] Ended drag over area ...
   ```

### Test 4: Rapid Tab Switching (Circuit Breaker)
1. Click rapidly between tabs (more than 6 times in 1 second)
2. **Expected logs**:
   ```
   [TAB-CLICK] User clicked tab: ...
   [TAB-ACTIVATE-REQUEST] Requesting tab activation: ...
   ... (several more) ...
   [TAB-ACTIVATE-BLOCKED] Rapid switching detected - count: 7
   [WARN] [TAB-ACTIVATE-BLOCKED] Rapid switching detected - count: 7
   ```

## What Logs Go to Backend

All `console.log`, `console.warn`, `console.error`, and `console.debug` statements are captured by the frontend logger and sent to the backend at `/api/logs/frontend` every 5 seconds (or immediately for errors).

These logs are written to:
- **Frontend perspective**: Console (real-time)
- **Backend perspective**: `logs/frontend.log` (batched every 5 seconds)

## Troubleshooting

### If you don't see ANY logs:
1. Make sure DevTools Console is open
2. Clear any console filters
3. Refresh the page to ensure new code is loaded

### If logs stop appearing:
1. Check if console has a filter active (clear it)
2. Look for any errors in console that might have stopped execution
3. Refresh the page

### To see backend logs:
```bash
# Watch frontend logs in real-time
tail -f logs/frontend.log

# Or view last 50 lines
tail -50 logs/frontend.log
```

## Backend Correlation

After clicking tabs, wait 5 seconds (or trigger an error) and then check:
```bash
tail -100 logs/frontend.log | grep -E "\[TAB-|PANEL-AREA"
```

This will show all tab-related logs that made it to the backend.

## Key Changes Made

1. **ICUITabContainer.tsx**:
   - Added `console.log` for every tab click with tab details
   - Added `console.log` for drag start/drop with tab and area info
   - Added detailed logging throughout `requestActivate` function
   - Added mount/unmount lifecycle logs

2. **ICUIPanelArea.tsx**:
   - Added logging to `handleTabActivate` with area context
   - Added drag enter/leave/drop logging with area and panel details
   - Added mount/unmount lifecycle logs

3. **frontend-logger.ts**:
   - Added `console.debug` interception (previously missing)
   - All debug logs now go to backend

## Notes

- All logs are **immediate** - you should see them the instant you click or drag
- Logs include context: tab names, IDs, area IDs, etc.
- The logging is verbose by design for debugging purposes
- No behavior changes - only observability improvements
