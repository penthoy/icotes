# Experience Distillation: Terminal Cursor/Arrow Key Bug

## Session Overview
Attempted to fix a persistent terminal bug where pressing up/down arrow keys causes the cursor to move up and delete previous lines instead of navigating command history. Despite multiple systematic approaches, the issue remains unresolved.

## Problem Description

### Symptoms
- Pressing UP arrow key: Cursor moves up one line and deletes/overwrites content
- Pressing DOWN arrow key: Cursor moves down one line and deletes/overwrites content
- Expected behavior: Arrow keys should navigate through bash command history
- Working reference: `/simple-terminal` route works correctly with arrow key navigation

### Environment
- Frontend: React + TypeScript + XTerm.js + WebSocket
- Backend: Python FastAPI + PTY + bash
- Terminal implementation: ICUITerminal.tsx (broken) vs simpleterminal.tsx (working)

## What Was Tried

### Attempt 1: WebSocket URL Path Fix
**Theory**: ICUITerminal was connecting to wrong WebSocket endpoint
**Changes Made**:
- Fixed WebSocket URL from `/terminal/` to `/ws/terminal/` when using environment variable
- Updated `ICUITerminal.tsx` line 312: `wsUrl = \`${envWsUrl}/ws/terminal/${terminalId.current}\``
**Result**: No improvement - cursor behavior unchanged

### Attempt 2: Terminal Configuration Simplification
**Theory**: Complex terminal options were interfering with input handling
**Changes Made**:
- Removed advanced XTerm.js options from ICUITerminal.tsx:
  - `allowTransparency`, `convertEol`, `scrollOnUserInput`
  - `altClickMovesCursor`, `rightClickSelectsWord`, `macOptionIsMeta`
  - `fastScrollModifier`, `fastScrollSensitivity`, `tabStopWidth`
  - `screenReaderMode`, `windowsMode`
- Simplified to match working SimpleTerminal configuration (scrollback, fontSize, fontFamily, cursorStyle, cursorBlink, theme only)
**Result**: No improvement - cursor behavior unchanged

### Attempt 3: DOM Structure Fix
**Theory**: Container hierarchy and CSS styling was interfering with XTerm.js rendering
**Changes Made**:
- Updated ICUITerminal JSX structure to match SimpleTerminal:
```tsx
// Old structure:
<div className="icui-terminal-container h-full w-full">
  <div ref={terminalRef} className="h-full w-full" />
</div>

// New structure:
<div className="icui-terminal-container flex-grow" style={{ position: 'relative', overflow: 'hidden' }}>
  <div ref={terminalRef} className="h-full w-full" style={{ position: 'relative' }} />
</div>
```
**Result**: No improvement - cursor behavior unchanged

### Attempt 4: CSS Injection Simplification
**Theory**: Complex CSS injection was causing viewport/canvas misalignment
**Changes Made**:
- Removed complex CSS variable integration and multiple style effects
- Simplified to exact SimpleTerminal CSS injection pattern:
```css
.icui-terminal-container .xterm .xterm-viewport {
  background-color: ${isDarkTheme ? '#1e1e1e' : '#ffffff'} !important;
  overflow-y: scroll !important;
  position: absolute !important;
  top: 0 !important; bottom: 0 !important; left: 0 !important; right: 0 !important;
}
```
- Removed ID-based style management and additional viewport background updates
**Result**: No improvement - cursor behavior unchanged

### Attempt 5: Backend PTY Configuration Fix
**Theory**: Backend was using canonical mode instead of raw mode for PTY
**Root Cause Analysis**:
- Found backend using `ICANON` (canonical mode) which processes input line-by-line
- Canonical mode breaks real-time character processing needed for terminal emulators
- Arrow keys get processed as escape sequences that interfere with shell command history

**Changes Made** in `backend/terminal.py`:
```python
# OLD (canonical mode):
attrs[3] |= termios.ICANON   # Enable canonical mode for line editing
attrs[3] |= termios.ECHO     # Enable echo so we see what we type

# NEW (raw mode):
attrs[3] &= ~termios.ICANON  # Disable canonical mode - process char by char  
attrs[3] &= ~termios.ECHO    # Disable local echo - let shell handle it
```
- Disabled canonical mode, local echo, output processing
- Set immediate character processing (`VMIN=1, VTIME=0`)
**Result**: No improvement - cursor behavior unchanged

## Analysis of Working vs Broken Implementation

### SimpleTerminal.tsx (Working)
- Uses `/ws/terminal/` WebSocket endpoint ✓
- Simple terminal configuration ✓  
- Basic container structure with `position: relative, overflow: hidden` ✓
- Simple CSS injection ✓
- Standalone route at `/simple-terminal` ✓

### ICUITerminal.tsx (Broken)
- Now uses `/ws/terminal/` WebSocket endpoint ✓
- Now uses simple terminal configuration ✓
- Now uses basic container structure ✓
- Now uses simple CSS injection ✓
- Embedded within ICUI panel system ✗

## Remaining Differences

### Context Differences
1. **Panel Integration**: ICUITerminal is embedded within ICUI's complex panel/layout system
2. **CSS Environment**: ICUITerminal inherits CSS from ICUI framework, themes, and layout components
3. **React Context**: ICUITerminal may be affected by ICUI's React context providers
4. **Event Handling**: ICUI panel system may be intercepting or interfering with keyboard events

### Potential Root Causes Not Yet Investigated
1. **CSS Inheritance**: ICUI framework CSS may be overriding XTerm.js styling
2. **Event Bubbling**: ICUI panel system may be capturing keyboard events before they reach XTerm.js
3. **Focus Management**: ICUI layout system may be interfering with terminal focus
4. **Z-index/Layering**: Terminal rendering layers may be misaligned due to ICUI CSS
5. **Container Dimensions**: ICUI panel sizing may be affecting XTerm.js viewport calculations

## Technical Verification

### What Works
- WebSocket connection establishes successfully ✓
- Terminal connects to backend and shows connection messages ✓
- Basic typing and command execution works ✓
- Simple-terminal route functions correctly with arrow keys ✓

### What Fails
- UP/DOWN arrow keys cause cursor to move vertically instead of history navigation ✗
- Previous lines get overwritten/deleted when cursor moves up ✗
- Terminal behavior doesn't match VS Code or standard terminal emulators ✗

## Next Investigation Directions

### High Priority
1. **CSS Isolation**: Completely isolate ICUITerminal from ICUI CSS using iframe or shadow DOM
2. **Event Debugging**: Add keyboard event listeners to trace where arrow key events are being captured/modified
3. **XTerm.js Debugging**: Enable XTerm.js debug mode to see internal state during arrow key presses
4. **Container Testing**: Extract ICUITerminal to standalone route to test if panel integration is the issue

### Medium Priority
1. **Theme System**: Investigate if ICUI theme system is interfering with terminal rendering
2. **React Effects**: Review all useEffect hooks that might be interfering with terminal state
3. **Focus Management**: Ensure terminal has proper focus and no competing focus handlers

### Low Priority
1. **XTerm.js Version**: Compare XTerm.js versions between working and broken implementations
2. **Browser DevTools**: Use browser performance/rendering tools to analyze DOM mutations during arrow key presses

## Code State

### Files Modified
- `/home/penthoy/icotes/src/icui/components/ICUITerminal.tsx`: WebSocket URL, terminal config, DOM structure, CSS injection simplified
- `/home/penthoy/icotes/backend/terminal.py`: PTY configuration changed from canonical to raw mode

### Build Status
- Frontend builds successfully ✓
- Backend changes require server restart to take effect ✓
- No TypeScript or compilation errors ✓

## Key Insight
Despite making ICUITerminal.tsx nearly identical to the working SimpleTerminal.tsx, the bug persists. This strongly suggests the issue is **environmental** - related to how ICUITerminal is embedded within the ICUI panel system rather than intrinsic to the terminal component itself.

The bug is likely caused by CSS inheritance, event handling conflicts, or rendering context differences between the standalone SimpleTerminal page and the embedded ICUI panel environment.
