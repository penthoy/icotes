# Tab Switch Bug Logging - Phase 2: State Synchronization Tracking

## Problem Identified

The initial tab click/drag logging (Phase 1) works perfectly for **user-initiated** tab switches. However, when the **automatic rapid switching bug** occurs, NO logs appear because the switching is happening through a different code path - likely through automatic state synchronization between parent and child components.

## Root Cause Hypothesis

Based on the ticket analysis, the bug is caused by a **state synchronization feedback loop** between:
1. `ICUILayout` (parent) - manages global `activePanelId` per area
2. `ICUIPanelArea` (child) - manages local `localActiveTabId` 
3. Multiple `useEffect` hooks that try to sync these states

The feedback loop:
```
ICUILayout updates activePanelId 
  → ICUIPanelArea syncs localActiveTabId 
    → ICUIPanelArea calls onPanelActivate 
      → ICUILayout updates activePanelId 
        → (infinite loop)
```

## New Logging Added (Phase 2)

### 1. ICUILayout State Changes
**File**: `src/icui/components/ICUILayout.tsx`

**Added**:
- `[LAYOUT-ACTIVATE]` - Logs every panel activation request at the layout level
  - Shows area ID, panel ID being activated
  - Shows previous → new active panel
  - Detects no-op cases (already active)
  - Logs parent callback invocations

- `[LAYOUT-STATE-CHANGE]` - Logs whenever the layout's state changes
  - Tracks all areas where `activePanelId` changed
  - Shows before → after for each area
  - Detects cascading updates across multiple areas

### 2. ICUIPanelArea Prop Synchronization
**File**: `src/icui/components/ICUIPanelArea.tsx`

**Added**:
- `[PANEL-AREA-SYNC]` - Logs when prop `activePanelId` changes from parent
  - Detects parent → child state synchronization
  - Shows what triggered the local state update
  - Includes area ID for correlation

- `[PANEL-AREA-FALLBACK]` - Logs automatic tab selection when active tab is removed
  - Shows when fallback logic activates
  - Shows which tab is auto-selected
  - Shows when parent is notified (potential feedback trigger)

- `[PANEL-AREA-ADD]` - Logs when new panels are added and auto-activated
  - Shows when new panel is detected
  - Shows whether it's auto-activated or not
  - Shows parent's expected active vs actual

### 3. Enhanced Component Lifecycle
**Both files** now include mount/unmount logging:
- `[TAB-CONTAINER-MOUNT/UNMOUNT]` (from Phase 1)
- `[PANEL-AREA-MOUNT/UNMOUNT]` (from Phase 1)

## What to Look For When Bug Occurs

### Sign 1: Rapid State Synchronization
Look for rapid alternation between:
```
[LAYOUT-STATE-CHANGE] Active panels changed: ["center: hop -> chat-history"]
[PANEL-AREA-SYNC] Prop change detected in area center: activePanelId changed from chat-history to hop
[PANEL-AREA] Tab activated in area center: hop
[LAYOUT-ACTIVATE] Panel activation requested - Area: center, Panel: chat-history
```

### Sign 2: Feedback Loop Pattern
Look for the same two panels switching back and forth:
```
[LAYOUT-ACTIVATE] Activating panel in area center: A -> B
[PANEL-AREA-SYNC] Prop change detected: B
[PANEL-AREA] Tab activate request: B
[LAYOUT-ACTIVATE] Activating panel in area center: B -> A
[PANEL-AREA-SYNC] Prop change detected: A
[PANEL-AREA] Tab activate request: A
(repeats rapidly)
```

### Sign 3: Unexpected Parent Callbacks
Look for callbacks being invoked when they shouldn't:
```
[PANEL-AREA-FALLBACK] Notifying parent of auto-selection: hop in area center
[LAYOUT-ACTIVATE] Panel activation requested - Area: center, Panel: hop
```

### Sign 4: Component Remounting
If components are being destroyed and recreated:
```
[PANEL-AREA-UNMOUNT] ICUIPanelArea unmounting, id: center
[PANEL-AREA-MOUNT] ICUIPanelArea mounted, id: center
```

## Testing Steps

### Step 1: Refresh Browser
Load the new code with enhanced logging

### Step 2: Normal Operations (Baseline)
1. Click between tabs normally
2. Observe clean, sequential logs:
   - `[TAB-CLICK]` → `[TAB-ACTIVATE-REQUEST]` → `[TAB-ACTIVATE-EXECUTE]` 
   - `[PANEL-AREA]` → `[LAYOUT-ACTIVATE]`
   - No rapid repetitions

### Step 3: Trigger the Bug
Perform actions that trigger the bug (e.g., open Chat History + Hop panels, switch rapidly)

### Step 4: Capture Logs Immediately
When rapid switching starts:
1. **Do NOT close console** - the logs are streaming
2. Scroll up to see the pattern that started the loop
3. Look for the FIRST occurrence of the feedback pattern
4. Note which components/areas are involved

### Step 5: Export Evidence
```javascript
// In browser console, copy all logs
copy(document.querySelectorAll('.console-message').textContent)

// Or manually select and copy the relevant section showing:
// - Last few normal operations before bug
// - First signs of rapid switching
// - The repeating pattern during bug
```

## Expected Findings

Based on the ticket, we expect to see:

1. **No user click events during rapid switching**
   - If no `[TAB-CLICK]` appears, confirms it's automatic

2. **State synchronization storm**
   - Rapid `[LAYOUT-STATE-CHANGE]` and `[PANEL-AREA-SYNC]` logs
   - Same two tabs alternating

3. **Specific trigger pattern**
   - Likely involves `[PANEL-AREA-FALLBACK]` or `[PANEL-AREA-ADD]`
   - Might involve multiple areas updating simultaneously
   - Could involve session change events (from Chat History)

4. **Missing circuit breaker activation**
   - Our circuit breaker only blocks user clicks
   - Programmatic state changes bypass it

## Files Modified

- `src/icui/components/ICUILayout.tsx`
  - Added `useRef` import
  - Added layout state change tracker
  - Enhanced `handlePanelActivate` with detailed logging

- `src/icui/components/ICUIPanelArea.tsx`
  - Enhanced prop sync logging with context
  - Enhanced fallback logic logging
  - Enhanced new panel detection logging
  - Added area ID to all logs for correlation

## Next Steps After Bug Reproduction

Once we capture the feedback loop pattern, we can:

1. **Identify the exact trigger**
   - Which useEffect is firing?
   - Which component initiated the loop?
   - What state change started it?

2. **Implement targeted fix**
   - Add guards to prevent redundant callbacks
   - Add debouncing to state synchronization
   - Break the feedback loop at the source

3. **Verify fix**
   - Same logging should show the pattern stops
   - Circuit breaker or guard prevents escalation

## Important Notes

- All logs include area IDs and panel IDs for correlation
- Timestamps are automatic via browser console
- Log format is consistent: `[PREFIX] Description: details`
- Logs are designed to be greppable: search for `[LAYOUT-`, `[PANEL-AREA-`, `[TAB-`

## Summary

**Phase 1** logged user interactions (clicks, drags)  
**Phase 2** logs automatic state synchronization (the actual bug source)

With both phases active, we should now see:
- User actions clearly labeled with `[TAB-CLICK]`
- Automatic updates labeled with `[LAYOUT-STATE-CHANGE]`, `[PANEL-AREA-SYNC]`, etc.
- The exact sequence that causes the feedback loop
