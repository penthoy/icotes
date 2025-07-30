# Code-Server Terminal Context Behavior Implementation Guide

## Executive Summary

This guide analyzes how code-server implements terminal context behavior, including clipboard operations, keyboard shortcuts, and standard terminal shortcuts like Ctrl+C, Ctrl+U, etc. Based on extensive research of the code-server codebase, this provides actionable patterns for recreating VS Code-like terminal behavior.

## 1. Architecture Overview

### Multi-Process Terminal Architecture
```
Browser (xterm.js) ↔ WebSocket ↔ VS Code Server ↔ PTY Host ↔ Shell Process
```

**Key Components:**
- **Frontend**: xterm.js terminal emulator with addons
- **Backend**: Node.js PTY processes managed by VS Code server
- **Communication**: WebSocket protocol for real-time data
- **Integration**: VS Code's native terminal services

### Core Libraries Used
- `@xterm/xterm`: Terminal emulator
- `@xterm/addon-fit`: Viewport fitting
- `@xterm/addon-web-links`: URL handling
- `node-pty`: Backend PTY management
- Native VS Code terminal services

## 2. Clipboard Integration Strategy

### Code-Server's Clipboard Solution (v4.90.0+)

Code-server implements clipboard functionality through a **server-side approach** rather than browser-based clipboard APIs:

```bash
# Terminal clipboard integration
echo "hello world" | code-server --stdin-to-clipboard
# or
echo "hello world" | code-server -c
```

**Implementation Pattern:**
```javascript
// Server-side clipboard handler
app.post('/clipboard', (req, res) => {
  const text = req.body.text;
  // Store in server-side clipboard buffer
  clipboardBuffer = text;
  res.json({ success: true });
});

// Terminal integration
terminal.onSelectionChange(() => {
  const selection = terminal.getSelection();
  if (selection) {
    // Send to server-side clipboard
    fetch('/clipboard', {
      method: 'POST',
      body: JSON.stringify({ text: selection })
    });
  }
});
```

### Why Browser Clipboard APIs Fail

From the failed implementation analysis, browser clipboard APIs fail because:

1. **Security Restrictions**: `navigator.clipboard` requires HTTPS/localhost
2. **Context Requirements**: Clipboard access needs user gesture
3. **Browser Differences**: Inconsistent support across browsers
4. **Development Environment**: HTTP contexts block clipboard access

### Recommended Clipboard Approach

**Option 1: Server-Side Clipboard (Recommended)**
```javascript
// Create server-side clipboard endpoint
class ServerClipboard {
  constructor() {
    this.buffer = '';
  }
  
  write(text) {
    this.buffer = text;
    // Optional: integrate with system clipboard
    return Promise.resolve();
  }
  
  read() {
    return Promise.resolve(this.buffer);
  }
}

// Terminal integration
terminal.onSelectionChange(() => {
  const selection = terminal.getSelection();
  if (selection) {
    serverClipboard.write(selection);
  }
});
```

**Option 2: Terminal Command Integration**
```javascript
// Pipe to clipboard command
terminal.onData((data) => {
  if (data.match(/\| clip$/)) {
    // Intercept pipe to clipboard
    const output = getPreviousOutput();
    serverClipboard.write(output);
  }
});
```

## 3. Keyboard Shortcuts Implementation

### VS Code Terminal Shortcuts

Code-server handles terminal shortcuts through VS Code's keyboard service:

```json
// keybindings.json
{
  "key": "ctrl+c",
  "command": "workbench.action.terminal.sendSequence",
  "args": { "text": "\u0003" },
  "when": "terminalFocus"
},
{
  "key": "ctrl+shift+c",
  "command": "workbench.action.terminal.copySelection",
  "when": "terminalFocus && terminalTextSelected"
},
{
  "key": "ctrl+shift+v",
  "command": "workbench.action.terminal.paste",
  "when": "terminalFocus"
}
```

### Implementation Pattern

```javascript
// Keyboard shortcut handler
class TerminalKeyboardHandler {
  constructor(terminal) {
    this.terminal = terminal;
    this.setupKeyBindings();
  }
  
  setupKeyBindings() {
    // Copy with Ctrl+Shift+C
    this.bindKey('ctrl+shift+c', () => {
      const selection = this.terminal.getSelection();
      if (selection) {
        this.copyToClipboard(selection);
      }
    });
    
    // Paste with Ctrl+Shift+V
    this.bindKey('ctrl+shift+v', async () => {
      const text = await this.readFromClipboard();
      if (text) {
        this.terminal.paste(text);
      }
    });
    
    // Terminal control sequences
    this.bindKey('ctrl+c', () => {
      this.terminal.write('\x03'); // SIGINT
    });
    
    this.bindKey('ctrl+u', () => {
      this.terminal.write('\x15'); // Clear line
    });
    
    this.bindKey('ctrl+k', () => {
      this.terminal.write('\x0B'); // Clear to end of line
    });
  }
  
  bindKey(combination, handler) {
    document.addEventListener('keydown', (event) => {
      if (this.matchesCombination(event, combination)) {
        event.preventDefault();
        handler();
      }
    });
  }
}
```

### Standard Terminal Shortcuts

```javascript
const TERMINAL_SHORTCUTS = {
  'ctrl+c': '\x03',    // SIGINT
  'ctrl+d': '\x04',    // EOF
  'ctrl+u': '\x15',    // Clear line backward
  'ctrl+k': '\x0B',    // Clear line forward
  'ctrl+l': '\x0C',    // Clear screen
  'ctrl+a': '\x01',    // Move to beginning
  'ctrl+e': '\x05',    // Move to end
  'ctrl+w': '\x17',    // Delete word backward
  'ctrl+z': '\x1A',    // Suspend process
  'ctrl+r': '\x12',    // Reverse search
  'ctrl+s': '\x13',    // Forward search
  'ctrl+q': '\x11',    // Resume output
  'ctrl+x': '\x18',    // Cancel
  'ctrl+y': '\x19',    // Yank
  'ctrl+t': '\x14',    // Transpose
  'ctrl+f': '\x06',    // Forward char
  'ctrl+b': '\x02',    // Backward char
  'ctrl+n': '\x0E',    // Next line
  'ctrl+p': '\x10',    // Previous line
  'ctrl+v': '\x16',    // Literal next
  'ctrl+o': '\x0F',    // Open line
  'ctrl+g': '\x07',    // Bell/cancel
  'ctrl+h': '\x08',    // Backspace
  'ctrl+i': '\x09',    // Tab
  'ctrl+j': '\x0A',    // Newline
  'ctrl+m': '\x0D',    // Carriage return
};
```

## 4. Context Menu Implementation

### Code-Server Context Menu Pattern

Code-server uses VS Code's context menu system rather than custom browser menus:

```javascript
// Context menu integration
terminal.onRightClick((event) => {
  const selection = terminal.getSelection();
  const menuItems = [
    {
      id: 'copy',
      label: 'Copy',
      enabled: !!selection,
      action: () => this.copySelection()
    },
    {
      id: 'paste',
      label: 'Paste',
      enabled: true,
      action: () => this.pasteFromClipboard()
    },
    {
      id: 'selectAll',
      label: 'Select All',
      enabled: true,
      action: () => terminal.selectAll()
    }
  ];
  
  showContextMenu(event.clientX, event.clientY, menuItems);
});
```

### Right-Click Behavior

```javascript
// Right-click clears selection and shows menu
terminal.element.addEventListener('contextmenu', (event) => {
  event.preventDefault();
  
  // Clear selection if clicking outside selected text
  if (!this.isClickInSelection(event)) {
    terminal.clearSelection();
  }
  
  this.showContextMenu(event);
});
```

## 5. Terminal Configuration

### Settings Integration

Code-server respects VS Code terminal settings:

```javascript
// Terminal configuration
const terminalConfig = {
  scrollback: settings.get('terminal.integrated.scrollback', 1000),
  fontSize: settings.get('terminal.integrated.fontSize', 14),
  fontFamily: settings.get('terminal.integrated.fontFamily', 'monospace'),
  cursorStyle: settings.get('terminal.integrated.cursorStyle', 'block'),
  cursorBlink: settings.get('terminal.integrated.cursorBlink', true),
  
  // Keyboard behavior
  'keyboard.dispatch': settings.get('keyboard.dispatch', 'code'),
  
  // Copy behavior
  'terminal.integrated.copyOnSelection': settings.get('terminal.integrated.copyOnSelection', false),
  'terminal.integrated.rightClickBehavior': settings.get('terminal.integrated.rightClickBehavior', 'default')
};
```

### Termux/Mobile Settings

For mobile environments (like Termux), code-server uses:

```json
{
  "keyboard.dispatch": "keyCode",
  "terminal.integrated.fontSize": 12,
  "terminal.integrated.fontFamily": "monospace"
}
```

## 6. Progressive Web App (PWA) Support

### Keyboard Shortcut Enhancement

Code-server recommends PWA installation for better keyboard support:

```javascript
// PWA keyboard handling
if (window.navigator.standalone || window.matchMedia('(display-mode: standalone)').matches) {
  // Enhanced keyboard support in PWA mode
  document.addEventListener('keydown', (event) => {
    // Prevent browser shortcuts from interfering
    if (event.ctrlKey || event.metaKey) {
      event.preventDefault();
      this.handleTerminalShortcut(event);
    }
  });
}
```

## 7. Implementation Recommendations

### Priority 1: Server-Side Clipboard

```javascript
// 1. Implement server-side clipboard
class TerminalClipboard {
  constructor() {
    this.buffer = '';
    this.setupEndpoints();
  }
  
  setupEndpoints() {
    // POST /api/clipboard/write
    // GET /api/clipboard/read
  }
  
  async write(text) {
    await fetch('/api/clipboard/write', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
  }
  
  async read() {
    const response = await fetch('/api/clipboard/read');
    return response.text();
  }
}
```

### Priority 2: Keyboard Shortcuts

```javascript
// 2. Implement keyboard handler
class TerminalKeyboard {
  constructor(terminal, clipboard) {
    this.terminal = terminal;
    this.clipboard = clipboard;
    this.setupShortcuts();
  }
  
  setupShortcuts() {
    // Copy/Paste shortcuts
    this.addShortcut('ctrl+shift+c', () => this.copySelection());
    this.addShortcut('ctrl+shift+v', () => this.paste());
    
    // Terminal control shortcuts
    Object.entries(TERMINAL_SHORTCUTS).forEach(([key, sequence]) => {
      this.addShortcut(key, () => this.terminal.write(sequence));
    });
  }
}
```

### Priority 3: Auto-Copy on Selection

```javascript
// 3. Auto-copy behavior
terminal.onSelectionChange(() => {
  const selection = terminal.getSelection();
  if (selection && settings.copyOnSelection) {
    this.clipboard.write(selection);
  }
});
```

### Priority 4: Context Menu

```javascript
// 4. Context menu
terminal.attachCustomKeyEventHandler((event) => {
  if (event.type === 'contextmenu') {
    this.showContextMenu(event);
    return false;
  }
  return true;
});
```

## 8. Testing Strategy

### Verification Steps

1. **Keyboard Shortcuts**: Test all Ctrl+X combinations
2. **Copy/Paste**: Verify selection copy and paste functionality
3. **Context Menu**: Test right-click behavior
4. **Terminal Control**: Verify Ctrl+C, Ctrl+U, etc. work
5. **Auto-Copy**: Test selection-based copying
6. **Cross-Browser**: Test in Chrome, Firefox, Safari

### Test Cases

```javascript
// Test keyboard shortcuts
const tests = [
  { keys: 'ctrl+c', expected: '\x03' },
  { keys: 'ctrl+u', expected: '\x15' },
  { keys: 'ctrl+shift+c', expected: 'copy' },
  { keys: 'ctrl+shift+v', expected: 'paste' }
];
```

## 9. Known Issues and Workarounds

### iPad/Mobile Issues

- **Ctrl+C Issue**: Use keyboard shortcut remapping
- **Copy/Paste**: Limited by iOS restrictions
- **Context Menu**: May not work on touch devices

### Browser Limitations

- **Clipboard Access**: Use server-side solution
- **Keyboard Shortcuts**: Install as PWA for better support
- **Right-Click**: May be blocked in some contexts

## 10. Migration from Failed Implementation

### Steps to Fix Current Code

1. **Remove Browser Clipboard Code**: Delete all `navigator.clipboard` usage
2. **Implement Server Clipboard**: Add server-side clipboard endpoints
3. **Add Keyboard Handler**: Implement proper shortcut handling
4. **Update Terminal Config**: Use proper xterm.js configuration
5. **Test Systematically**: Verify each feature works independently

### Code Cleanup

```javascript
// Remove these patterns:
// - navigator.clipboard.writeText()
// - navigator.clipboard.readText()
// - document.execCommand('copy')
// - Context menu popups

// Replace with:
// - Server-side clipboard API
// - Keyboard shortcut handlers
// - Terminal sequence writers
// - VS Code-style context menus
```

## Conclusion

Code-server succeeds with terminal context behavior by:

1. **Using server-side clipboard** instead of browser APIs
2. **Implementing proper keyboard shortcuts** with terminal sequences
3. **Respecting VS Code terminal patterns** and configurations
4. **Using PWA mode** for enhanced keyboard support
5. **Handling mobile limitations** with appropriate workarounds

The key insight is that **browser limitations require server-side solutions** for clipboard functionality, while keyboard shortcuts must be implemented with proper terminal control sequences rather than relying on browser clipboard APIs.

Focus on implementing the server-side clipboard first, then add keyboard shortcuts, and finally enhance with context menus and auto-copy features. This approach mirrors code-server's successful implementation pattern.
