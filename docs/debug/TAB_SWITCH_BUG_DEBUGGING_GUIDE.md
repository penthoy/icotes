# Tab Switch Bug Debugging Guide

## Overview
This document explains how to use the comprehensive debugging tools added to help diagnose and fix the tab switch bug.

## What Was Fixed

### 1. HTML Form Validation Errors (CRITICAL)
**Problem**: Thousands of validation errors appearing in browser console: "A form field element should have an id or name attribute"

**Fixed Files**:
- `src/icui/components/ICUIBaseHeader.tsx` - Added `id` and `name` to theme selector
- `src/icui/components/panels/ICUIChatHistory.tsx` - Added `id` and `name` to search input and rename inputs

**Impact**: This was likely the PRIMARY cause of the tab switch lag. Each form element without proper attributes generates validation errors, and during rapid re-renders (like tab switching), thousands of these errors accumulate, causing severe performance degradation.

### 2. Comprehensive Debug Logging System
Added a new `debugLogger` utility that tracks:
- Component lifecycle (mount, unmount, render)
- Tab operations (activation, blocking, drag)
- Command registry operations (registration, execution, duplicates)
- Performance timing for all operations
- Automatic detection of excessive re-renders and registrations

## How to Use the Debug Tools

### Frontend Debug Logger

#### Enable Debug Logging
Open browser console and run:
```javascript
// Enable debug logging
icuiDebugHelpers.enable()

// Or set in localStorage before reload
localStorage.setItem('icui-debug-logging', 'true')
```

#### View Summary
```javascript
// Print comprehensive summary
icuiDebugHelpers.summary()

// View all logs
icuiDebugHelpers.logs()

// Filter logs by component
icuiDebugHelpers.logs({ component: 'ICUIChatHistory' })

// Filter logs by action type
icuiDebugHelpers.logs({ action: 'lifecycle' })

// Filter logs since timestamp
icuiDebugHelpers.logs({ since: Date.now() - 5000 }) // Last 5 seconds
```

#### Export Logs for Bug Reports
```javascript
// Export all logs as JSON
const logData = icuiDebugHelpers.export()
console.log(logData)

// Copy to clipboard (if available)
copy(logData)
```

#### Clear Logs
```javascript
icuiDebugHelpers.clear()
```

#### Disable Debug Logging
```javascript
icuiDebugHelpers.disable()
```

### Backend Debug Logging

#### Enable Backend Debug Logging
Set environment variable before starting backend:
```bash
export ICUI_DEBUG_LOGGING=true
cd backend
python main.py
```

Or add to `.env` file:
```
ICUI_DEBUG_LOGGING=true
```

#### What Gets Logged
- All HTTP requests with timing
- Request/response duration in milliseconds
- Slow request warnings (>500ms)
- Request ID for correlation with frontend
- Response time headers for frontend tracking

#### View Logs
Backend logs will appear in the terminal where you started the server:
```
DEBUG:__main__:[a1b2c3d4] GET /api/chat/sessions - Start
DEBUG:__main__:[a1b2c3d4] GET /api/chat/sessions - Complete (200) in 45.23ms
WARNING:__main__:[e5f6g7h8] SLOW REQUEST: POST /api/chat/message took 523.45ms
```

## Reproducing and Capturing the Bug

### Step 1: Enable All Debug Logging
```bash
# Terminal 1: Start backend with debug logging
cd backend
export ICUI_DEBUG_LOGGING=true
python main.py

# Terminal 2: Start frontend
cd ..
npm run dev
```

### Step 2: Open Browser Console
1. Open Chrome DevTools (F12)
2. Go to Console tab
3. Run: `icuiDebugHelpers.enable()`

### Step 3: Trigger the Bug
1. Perform tab operations that trigger the bug:
   - Drag chat history panel between docks
   - Rapidly switch between tabs
   - Open/close multiple panels quickly

### Step 4: Capture Debug Data

#### When Bug Occurs:
```javascript
// Immediately capture data
const bugReport = icuiDebugHelpers.export()

// Check for warning patterns
icuiDebugHelpers.summary()

// Look for specific issues:
// - High render counts in last second
// - Excessive command registrations
// - Slow performance markers
```

#### Analyze the Data:
```javascript
// Check component render frequency
const logs = icuiDebugHelpers.logs()
const chatHistoryRenders = logs.filter(l => 
  l.component === 'ICUIChatHistory' && 
  l.action.includes('render')
)
console.log(`ICUIChatHistory rendered ${chatHistoryRenders.length} times`)

// Check tab operations during bug
const tabOps = logs.filter(l => l.action.includes('tab:'))
console.table(tabOps.map(l => ({
  time: new Date(l.timestamp).toISOString(),
  action: l.action,
  details: JSON.stringify(l.details)
})))

// Check for command registration spam
const commandOps = logs.filter(l => l.action.includes('command:'))
const commandCounts = {}
commandOps.forEach(op => {
  const id = op.details?.commandId || 'unknown'
  commandCounts[id] = (commandCounts[id] || 0) + 1
})
console.table(commandCounts)
```

### Step 5: Save the Report
```javascript
// Export and save
const report = {
  timestamp: new Date().toISOString(),
  userAgent: navigator.userAgent,
  bugDescription: "Describe what you observed",
  debugLogs: icuiDebugHelpers.export(),
  browserErrors: "Check Console errors tab and paste here"
}

// Copy to save as file
copy(JSON.stringify(report, null, 2))
```

## What to Look For

### Frontend Signs of Issues

1. **Excessive Renders**:
   - Component renders >10 times per second
   - Look for: `"High render frequency detected"` warnings

2. **Command Registration Spam**:
   - Same command registered multiple times quickly
   - Look for: `"High command registration frequency"` warnings

3. **Slow Operations**:
   - Tab activation taking >100ms
   - Command execution taking >100ms
   - Look for: `"Slow operation detected"` warnings

4. **Validation Errors**:
   - Form validation errors in Console
   - Should be eliminated after the fixes

### Backend Signs of Issues

1. **Slow API Responses**:
   - Requests taking >500ms
   - Look for: `"SLOW REQUEST"` warnings

2. **Request Patterns**:
   - Rapid-fire duplicate requests
   - Requests during drag operations

## Performance Markers

The debug logger automatically tracks performance for key operations:

- `chat-history-command-registration` - Time to register chat history commands
- `command-execute-{commandId}` - Time to execute specific commands
- `tab-activation-{tabId}` - Time to activate a specific tab

Access via browser performance tools:
```javascript
// View all performance marks
performance.getEntriesByType('mark').filter(m => m.name.startsWith('icui-'))

// View all performance measures
performance.getEntriesByType('measure').filter(m => m.name.startsWith('icui-'))
```

## Troubleshooting

### Debug Logging Not Working?

1. **Check if enabled**:
   ```javascript
   localStorage.getItem('icui-debug-logging')
   // Should return 'true'
   ```

2. **Check console for init message**:
   Look for: `"[DebugLogger] Debug logging enabled"`

3. **Manually enable in code** (temporary):
   Edit `src/icui/utils/debugLogger.ts` and change:
   ```typescript
   this.enabled = true; // Force enable
   ```

### Backend Logging Not Working?

1. **Check environment variable**:
   ```bash
   echo $ICUI_DEBUG_LOGGING
   # Should output: true
   ```

2. **Check server startup logs**:
   Look for: `"Debug logging middleware enabled"`

3. **Verify log level**:
   Backend uses Python's `logging.DEBUG` level, ensure it's not filtered

## Next Steps After Capturing Data

1. **Save the debug export** to a file: `tab-switch-bug-report-YYYY-MM-DD.json`

2. **Update the ticket** (`docs/tickets/tab_switch_bug_ticket.md`) with:
   - When the bug occurred
   - What actions triggered it
   - Key findings from the debug logs
   - Any new patterns observed

3. **Analyze patterns**:
   - Compare render counts across components
   - Identify which operations are slow
   - Look for correlation between frontend and backend timing

4. **Iterate on fixes**:
   - If excessive renders found, add memoization
   - If slow API calls, optimize backend
   - If command registration spam, add more guards

## Tips for Effective Debugging

1. **Start with a clean slate**: Clear logs before reproducing
2. **Document steps**: Write down exactly what you did to trigger the bug
3. **Compare good vs bad**: Capture logs during normal operation vs buggy operation
4. **Focus on timing**: Look for operations that coincide with the bug
5. **Check correlations**: Do frontend slow operations match backend slow requests?

## Contact & Reporting

When reporting findings, include:
- Full debug export (JSON)
- Screenshots of browser console warnings
- Backend terminal logs during the issue
- Steps to reproduce
- Browser version and OS

This comprehensive debugging setup should help us finally identify and fix the root cause of the tab switch bug!
