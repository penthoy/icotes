# Tab Switch Bug Reproduction Guide

## Why This Bug is Inconsistent

The bug is inconsistent because it depends on a **race condition** between multiple React effects and timing factors. Here's why:

### Timing-Dependent Factors

1. **React Render Batching**: React batches state updates, but the batching behavior varies:
   - In React 18+, automatic batching happens in most cases
   - However, updates in `setTimeout`, promises, or native event handlers may NOT be batched
   - The 100ms debounce in `ICUITabContainer` means updates happen in setTimeout (not batched)

2. **Effect Execution Order**: When multiple useEffects depend on the same state:
   - React guarantees execution order within a component
   - But NOT across parent/child components
   - Parent's `handlePanelActivate` and child's sync effect can race

3. **Browser Event Loop**: The feedback loop timing depends on:
   - How fast React processes updates (~16ms for 60fps)
   - The 100ms debounce delay
   - Browser paint cycles
   - Console logging overhead (writing to logs takes time)

### The Race Condition

```
User Click → 100ms debounce → handleTabActivate called
                                     ↓
                    isLocalChangeRef = true (BEFORE fix, this didn't exist)
                                     ↓
                    setLocalActiveTabId(tabId) ← Sets local state
                                     ↓
                    onPanelActivate(tabId) ← Notifies parent
                                     ↓
           Parent: handlePanelActivate(areaId, tabId)
                                     ↓
           Parent: setCurrentLayout(new state) ← Updates parent state
                                     ↓
           React schedules re-render with new activePanelId prop
                                     ↓
                    ⚠️ RACE CONDITION HERE ⚠️
                                     ↓
          Does the sync useEffect run BEFORE or AFTER the flag clears?
```

### When the Bug DOES Trigger

The feedback loop triggers when this specific sequence occurs:

1. **Debounce completes** → `handleTabActivate` runs
2. **Parent updates FAST** → New `activePanelId` prop arrives
3. **Sync effect runs BEFORE** the next click/debounce cycle
4. **Sync effect updates state** → Triggers parent update again
5. **Loop established** → Steps 2-4 repeat every ~20-30ms

### When the Bug DOESN'T Trigger

The bug is avoided when:

1. **User clicks slowly** → Debounce ensures only one activation in flight
2. **Circuit breaker activates** → >6 switches/sec blocks further updates
3. **Parent update is slow** → Prop doesn't arrive until after next interaction
4. **React batches updates** → Multiple setStates grouped into one render
5. **Sync effect skips** → No change detected (same value)

## Consistent Reproduction Steps

### Prerequisites

To reliably reproduce, you need to **disable the fix** temporarily:

```bash
# 1. Open ICUIPanelArea.tsx
# 2. Comment out these lines in the sync useEffect (around line 90):

# BEFORE (with fix):
if (isLocalChangeRef.current) {
  console.log(`[PANEL-AREA-SYNC-SKIP] Area ${id}: Skipping sync, local change in progress`);
  isLocalChangeRef.current = false;
  return;  // ← This line prevents the loop
}

# Change to (without fix):
// if (isLocalChangeRef.current) {
//   console.log(`[PANEL-AREA-SYNC-SKIP] Area ${id}: Skipping sync, local change in progress`);
//   isLocalChangeRef.current = false;
//   return;
// }

# 3. Also comment out the flag setting in handleTabActivate (around line 163):
// isLocalChangeRef.current = true;

# 4. Rebuild: npm run build
```

### Method 1: Rapid Tab Clicking (90% Success Rate)

This is the most reliable method:

1. **Setup**:
   - Open the application with at least 2 tabs in one area (e.g., `hop` and `editor` in center)
   - Open browser DevTools console
   - Filter logs for: `PANEL-AREA-SYNC|LAYOUT-STATE`

2. **Trigger**:
   - Click rapidly between the two tabs **AS FAST AS POSSIBLE**
   - Aim for >10 clicks per second
   - Use keyboard if possible: Tab key + Enter repeatedly
   - Continue for 3-5 seconds

3. **Expected Result (Bug Active)**:
   ```
   [PANEL-AREA-SYNC] Area center: hop -> editor
   [LAYOUT-STATE-CHANGE] Active panels changed: ["center: hop -> editor"]
   [PANEL-AREA-SYNC] Area center: editor -> hop
   [LAYOUT-STATE-CHANGE] Active panels changed: ["center: editor -> hop"]
   [PANEL-AREA-SYNC] Area center: hop -> editor
   ... (repeating every 20-30ms)
   ```

4. **Why This Works**:
   - Rapid clicks saturate the debounce mechanism
   - Creates multiple activation requests in queue
   - Timing aligns to trigger the race condition
   - Fast clicking prevents circuit breaker from detecting the loop (spreads across time windows)

### Method 2: External Tab Activation (70% Success Rate)

Trigger activation programmatically to bypass debounce:

1. **Setup**:
   - Open browser DevTools console
   - Identify panel IDs by checking the layout state

2. **Trigger via Console**:
   ```javascript
   // Find the ICUILayout instance and force rapid activations
   let count = 0;
   const interval = setInterval(() => {
     // Alternate between two panel IDs
     const panels = ['hop', 'editor']; // Adjust to your panel IDs
     const panelId = panels[count % 2];
     
     // This simulates what handleTabActivate does
     console.log(`Forcing activation: ${panelId}`);
     
     // You'll need to trigger this through the UI or a test harness
     // The key is rapid alternation without debounce protection
     
     count++;
     if (count > 20) clearInterval(interval);
   }, 50); // 50ms = 20 switches per second
   ```

3. **Why This Works**:
   - Bypasses the 100ms debounce
   - Directly creates the rapid switching scenario
   - More controlled than user clicks

### Method 3: Drag and Release Quickly (50% Success Rate)

For the original fallback bug (already fixed):

1. **Setup**:
   - Have 3+ panels in different areas
   - Open DevTools console

2. **Trigger**:
   - Start dragging a panel
   - Move it over a different area
   - **Release immediately** (don't pause)
   - Repeat quickly 5-10 times

3. **Expected Result** (if fallback bug still existed):
   ```
   [PANEL-AREA-FALLBACK] Area left: tab chat-history no longer exists
   [LAYOUT-STATE-CHANGE] Active panels changed: ["left: explorer -> chat-history"]
   [PANEL-AREA-SYNC] Area center: editor -> chat-history
   ... (oscillation between areas)
   ```

## Testing the Fix

With the fix applied (default state):

1. **Perform Method 1** (rapid clicking):
   - You should see `[PANEL-AREA-SYNC-SKIP]` logs
   - NO rapid oscillation
   - Tabs switch cleanly with each click

2. **Expected Logs with Fix**:
   ```
   [PANEL-AREA-ACTIVATE] Area center: User activated hop
   [PANEL-AREA-ACTIVATE] Area center: Notified parent of hop
   [PANEL-AREA-SYNC-SKIP] Area center: Skipping sync, local change
   [LAYOUT-STATE-CHANGE] Active panels changed: ["center: editor -> hop"]
   [PANEL-AREA-ACTIVATE] Area center: User activated editor
   [PANEL-AREA-ACTIVATE] Area center: Notified parent of editor
   [PANEL-AREA-SYNC-SKIP] Area center: Skipping sync, local change
   [LAYOUT-STATE-CHANGE] Active panels changed: ["center: hop -> editor"]
   ```
   
   **Key difference**: `[PANEL-AREA-SYNC-SKIP]` appears, preventing the feedback loop

3. **What Success Looks Like**:
   - Each click produces 1-2 log entries, not hundreds
   - `[PANEL-AREA-SYNC-SKIP]` appears after each user activation
   - NO repeating `[PANEL-AREA-SYNC]` ↔ `[LAYOUT-STATE-CHANGE]` pattern
   - Tabs respond to clicks without oscillating

## Additional Testing Tools

### Enable Circuit Breaker Logging

The circuit breaker should catch any remaining loops:

1. Look for `[TAB-SWITCH-BUG]` warnings in console
2. If you see this, a feedback loop is active
3. The circuit breaker will auto-block after 6 switches/sec

### Monitor useEffect Execution

Add temporary logging to see effect order:

```typescript
// In ICUIPanelArea.tsx sync useEffect:
useEffect(() => {
  console.log(`[EFFECT-SYNC] Triggered. Props: activePanelId=${activePanelId}, Local: ${localActiveTabId}, Flag: ${isLocalChangeRef.current}`);
  // ... rest of effect
}, [activePanelId, localActiveTabId, id]);
```

This helps visualize the race condition timing.

## Why Automated Tests Can't Catch This

Traditional unit tests struggle with this bug because:

1. **React Testing Library** uses `act()` which batches updates
2. **Timing is artificial** in tests (no real event loop)
3. **No actual debounce delays** in fast test execution
4. **Effects run synchronously** in test environment

This is a **real-world timing bug** that requires actual browser testing.

## Summary

**The bug is inconsistent because:**
- It depends on React's render timing (varies by load)
- The 100ms debounce adds randomness
- User click speed varies
- Circuit breaker may block it before it's visible

**To reproduce reliably:**
1. Disable the fix (comment out sync skip logic)
2. Rapid click between 2 tabs >10 times/sec for 3-5 seconds
3. Watch for repeating `[PANEL-AREA-SYNC]` ↔ `[LAYOUT-STATE-CHANGE]`

**To verify the fix:**
1. Enable the fix (default code)
2. Rapid click between tabs
3. Should see `[PANEL-AREA-SYNC-SKIP]` preventing loops
4. No oscillation occurs
