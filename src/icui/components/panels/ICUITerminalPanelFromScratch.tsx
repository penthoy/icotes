/**
 * ICUI Terminal Panel From Scratch
 * Simplified implementation with code-server style clipboard integration
 * Based on code-server analysis - using --stdin-to-clipboard approach
 * 
 * Features:
 * - Proper keyboard shortcuts (Ctrl+C/U/etc for terminal control)
 * - Code-server style clipboard integration via CLI commands
 * - VS Code-like terminal behavior
 * - Proper scrolling and theme integration
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css'; // MUST be imported first

interface ICUITerminalPanelFromScratchProps {
  className?: string;
}

interface ContextMenuState {
  visible: boolean;
  x: number;
  y: number;
  hasSelection: boolean;
}

// Terminal control sequences for keyboard shortcuts
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
} as const;

// Simplified clipboard class using API calls
class TerminalClipboard {
  async copy(text: string): Promise<boolean> {
    if (!text) return false;
    
    try {
      const response = await fetch('/api/clipboard/write', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
      });

      const result = await response.json();
      return result.success;
    } catch (error) {
      console.error('✗ Clipboard copy error:', error);
      return false;
    }
  }

  async paste(): Promise<string> {
    try {
      const response = await fetch('/api/clipboard/read');
      const result = await response.json();
      
      if (result.success) {
        return result.text || '';
      }
      return '';
    } catch (error) {
      console.error('✗ Clipboard paste error:', error);
      return '';
    }
  }
}

// Keyboard handler class
class TerminalKeyboardHandler {
  private terminal: Terminal;
  private clipboard: TerminalClipboard;
  private websocket: WebSocket | null;

  constructor(terminal: Terminal, websocket: WebSocket | null) {
    this.terminal = terminal;
    this.clipboard = new TerminalClipboard();
    this.websocket = websocket;
    this.setupKeyboardHandlers();
  }

  private setupKeyboardHandlers() {
    document.addEventListener('keydown', this.handleKeyDown.bind(this));
  }

  private handleKeyDown(event: KeyboardEvent) {
    // Only handle if terminal is focused
    if (!this.isTerminalFocused()) return;

    const key = this.getKeyString(event);

    // Handle copy/paste shortcuts (Ctrl+Shift+C/V) - code-server style
    if (key === 'ctrl+shift+c') {
      event.preventDefault();
      this.copySelection();
      return;
    }

    if (key === 'ctrl+shift+v') {
      event.preventDefault();
      this.paste();
      return;
    }

    // Handle terminal control shortcuts
    if (key in TERMINAL_SHORTCUTS) {
      event.preventDefault();
      this.terminal.write(TERMINAL_SHORTCUTS[key as keyof typeof TERMINAL_SHORTCUTS]);
      return;
    }
  }

  private isTerminalFocused(): boolean {
    return document.activeElement?.closest('.terminal-container') !== null;
  }

  private getKeyString(event: KeyboardEvent): string {
    const parts = [];
    if (event.ctrlKey) parts.push('ctrl');
    if (event.shiftKey) parts.push('shift');
    if (event.altKey) parts.push('alt');
    if (event.metaKey) parts.push('meta');
    parts.push(event.key.toLowerCase());
    return parts.join('+');
  }

  async copySelection() {
    const selection = this.terminal.getSelection();
    if (selection) {
      try {
        // Use the backend API directly instead of shell commands
        const response = await fetch('/api/clipboard/write', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ text: selection }),
        });

        const result = await response.json();
        if (result.success) {
          this.terminal.write('\r\n\x1b[32m[✓ Copied to clipboard]\x1b[0m\r\n');
          console.log(`✓ Copied ${selection.length} characters to clipboard`);
        } else {
          this.terminal.write('\r\n\x1b[31m[✗ Copy failed]\x1b[0m\r\n');
          console.error('✗ Failed to copy to clipboard:', result.message);
        }
      } catch (error) {
        this.terminal.write('\r\n\x1b[31m[✗ Copy failed]\x1b[0m\r\n');
        console.error('✗ Failed to copy to clipboard:', error);
      }
    } else {
      this.terminal.write('\r\n\x1b[33m[No text selected]\x1b[0m\r\n');
      console.log('No text selected to copy');
    }
  }

  async paste() {
    try {
      // Use the backend API directly instead of shell commands
      const response = await fetch('/api/clipboard/read');
      const result = await response.json();
      
      if (result.success && result.text) {
        // Send the clipboard content directly to the terminal
        if (this.websocket?.readyState === WebSocket.OPEN) {
          this.websocket.send(result.text);
          console.log(`✓ Pasted ${result.text.length} characters from clipboard`);
        } else {
          this.terminal.write('\r\n\x1b[31m[✗ Terminal not connected]\x1b[0m\r\n');
        }
      } else {
        this.terminal.write('\r\n\x1b[33m[No clipboard content]\x1b[0m\r\n');
        console.log('No text available to paste from clipboard');
      }
    } catch (error) {
      this.terminal.write('\r\n\x1b[31m[✗ Paste failed]\x1b[0m\r\n');
      console.error('✗ Failed to paste from clipboard:', error);
    }
  }

  cleanup() {
    document.removeEventListener('keydown', this.handleKeyDown.bind(this));
  }

  updateWebSocket(websocket: WebSocket | null) {
    this.websocket = websocket;
  }
}

const ICUITerminalPanelFromScratch: React.FC<ICUITerminalPanelFromScratchProps> = ({ className = '' }) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const websocket = useRef<WebSocket | null>(null);
  const terminalId = useRef<string>(Math.random().toString(36).substring(2));
  const terminal = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const resizeObserver = useRef<ResizeObserver | null>(null);
  const resizeTimeout = useRef<NodeJS.Timeout | null>(null);
  const typedCount = useRef<number>(0);
  const keyboardHandler = useRef<TerminalKeyboardHandler | null>(null);
  
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    visible: false,
    x: 0,
    y: 0,
    hasSelection: false,
  });

  // Theme detection
  useEffect(() => {
    const detectTheme = () => {
      const htmlElement = document.documentElement;
      const isDark = htmlElement.classList.contains('dark') || 
                     htmlElement.classList.contains('icui-theme-github-dark') ||
                     htmlElement.classList.contains('icui-theme-monokai') ||
                     htmlElement.classList.contains('icui-theme-one-dark');
      setIsDarkTheme(isDark);
    };

    detectTheme();
    
    const observer = new MutationObserver(detectTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });

    return () => observer.disconnect();
  }, []);

  // Context menu handlers
  const handleContextMenu = useCallback((event: React.MouseEvent) => {
    event.preventDefault();
    
    const selection = terminal.current?.getSelection();
    const hasSelection = !!selection;
    
    // Clear selection if clicking outside selected text
    if (!hasSelection) {
      terminal.current?.clearSelection();
    }
    
    setContextMenu({
      visible: true,
      x: event.clientX,
      y: event.clientY,
      hasSelection,
    });
  }, []);

  const hideContextMenu = useCallback(() => {
    setContextMenu(prev => ({ ...prev, visible: false }));
  }, []);

  const handleCopy = useCallback(async () => {
    if (keyboardHandler.current) {
      await keyboardHandler.current.copySelection();
    }
    hideContextMenu();
  }, [hideContextMenu]);

  const handlePaste = useCallback(async () => {
    if (keyboardHandler.current) {
      await keyboardHandler.current.paste();
    }
    hideContextMenu();
  }, [hideContextMenu]);

  const handleSelectAll = useCallback(() => {
    terminal.current?.selectAll();
    hideContextMenu();
  }, [hideContextMenu]);

  // Terminal initialization
  useEffect(() => {
    if (!terminalRef.current) return;

    // Create terminal with proper configuration
    terminal.current = new Terminal({
      scrollback: 1000,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      cursorStyle: 'block',
      cursorBlink: true,
      theme: {
        background: isDarkTheme ? '#1e1e1e' : '#ffffff',
        foreground: isDarkTheme ? '#d4d4d4' : '#000000',
        cursor: isDarkTheme ? '#d4d4d4' : '#000000',
        cursorAccent: isDarkTheme ? '#1e1e1e' : '#ffffff',
        selectionBackground: isDarkTheme ? '#264f78' : '#add6ff',
        black: '#000000',
        brightBlack: '#666666',
        red: '#cd3131',
        brightRed: '#f14c4c',
        green: '#0dbc79',
        brightGreen: '#23d18b',
        yellow: '#e5e510',
        brightYellow: '#f5f543',
        blue: '#2472c8',
        brightBlue: '#3b8eea',
        magenta: '#bc3fbc',
        brightMagenta: '#d670d6',
        cyan: '#11a8cd',
        brightCyan: '#29b8db',
        white: '#e5e5e5',
        brightWhite: '#ffffff',
      },
    });

    // Create and load FitAddon
    fitAddon.current = new FitAddon();
    terminal.current.loadAddon(fitAddon.current);

    // CRITICAL: Open terminal BEFORE fitting (code-server pattern)
    terminal.current.open(terminalRef.current);
    
    // Fit after opening
    fitAddon.current.fit();

    // Initialize keyboard handler
    keyboardHandler.current = new TerminalKeyboardHandler(terminal.current, websocket.current);
    // keyboardHandler.current.setupKeyBindings(); // This is now handled by the new class

    // Setup resize handling with debounce
    const handleResize = () => {
      if (resizeTimeout.current) {
        clearTimeout(resizeTimeout.current);
      }
      resizeTimeout.current = setTimeout(() => {
        if (fitAddon.current && terminal.current) {
          fitAddon.current.fit();
          
          // Sync with backend PTY size
          if (websocket.current?.readyState === WebSocket.OPEN) {
            websocket.current.send(JSON.stringify({
              type: 'resize',
              cols: terminal.current.cols,
              rows: terminal.current.rows
            }));
          }
        }
      }, 100);
    };

    // Setup ResizeObserver for container changes
    if (terminalRef.current) {
      resizeObserver.current = new ResizeObserver(handleResize);
      resizeObserver.current.observe(terminalRef.current);
    }

    // Setup window resize listener
    window.addEventListener('resize', handleResize);

    // Handle user input: send to backend (no local echo, let backend handle it)
    terminal.current.onData((data) => {
      if (websocket.current?.readyState === WebSocket.OPEN) {
        websocket.current.send(data);
      }
    });

    // Connect to backend via WebSocket
    const envWsUrl = import.meta.env.VITE_WS_URL as string | undefined;
    let wsUrl: string;
    if (envWsUrl && envWsUrl.trim() !== '') {
      wsUrl = `${envWsUrl}/ws/terminal/${terminalId.current}`;
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      wsUrl = `${protocol}//${host}/ws/terminal/${terminalId.current}`;
    }

    websocket.current = new WebSocket(wsUrl);
    
    websocket.current.onopen = () => {
      console.log('Terminal WebSocket connected');
      
      // Update keyboard handler with new websocket
      if (keyboardHandler.current) {
        keyboardHandler.current.updateWebSocket(websocket.current);
      }
    };
    
    websocket.current.onmessage = (event) => {
      terminal.current?.write(event.data);
    };
    
    websocket.current.onclose = (event) => {
      if (event.code !== 1000) {
        terminal.current?.write("\r\n\x1b[31mTerminal disconnected\x1b[0m\r\n");
      }
    };
    
    websocket.current.onerror = () => {
      terminal.current?.write("\r\n\x1b[31mTerminal connection error\x1b[0m\r\n");
    };

    // Hide context menu when clicking outside
    const handleClickOutside = (event: MouseEvent) => {
      if (contextMenu.visible && !terminalRef.current?.contains(event.target as Node)) {
        hideContextMenu();
      }
    };

    document.addEventListener('click', handleClickOutside);

    return () => {
      if (resizeTimeout.current) {
        clearTimeout(resizeTimeout.current);
      }
      if (resizeObserver.current) {
        resizeObserver.current.disconnect();
      }
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('click', handleClickOutside);
      websocket.current?.close();
      keyboardHandler.current?.cleanup();
      if (terminal.current) {
        terminal.current.dispose();
        terminal.current = null;
      }
    };
  }, []);

  // Update theme when it changes
  useEffect(() => {
    if (!terminal.current) return;
    
    terminal.current.options.theme = {
      background: isDarkTheme ? '#1e1e1e' : '#ffffff',
      foreground: isDarkTheme ? '#d4d4d4' : '#000000',
      cursor: isDarkTheme ? '#d4d4d4' : '#000000',
      cursorAccent: isDarkTheme ? '#1e1e1e' : '#ffffff',
      selectionBackground: isDarkTheme ? '#264f78' : '#add6ff',
      black: '#000000',
      brightBlack: '#666666',
      red: '#cd3131',
      brightRed: '#f14c4c',
      green: '#0dbc79',
      brightGreen: '#23d18b',
      yellow: '#e5e510',
      brightYellow: '#f5f543',
      blue: '#2472c8',
      brightBlue: '#3b8eea',
      magenta: '#bc3fbc',
      brightMagenta: '#d670d6',
      cyan: '#11a8cd',
      brightCyan: '#29b8db',
      white: '#e5e5e5',
      brightWhite: '#ffffff',
    };
  }, [isDarkTheme]);

  // Apply critical CSS for viewport scrolling
  useEffect(() => {
    const styleElement = document.createElement('style');
    styleElement.textContent = `
      .terminal-container .xterm .xterm-viewport {
        background-color: ${isDarkTheme ? '#1e1e1e' : '#ffffff'} !important;
        overflow-y: scroll !important;
        position: absolute !important;
        top: 0 !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
      }
      
      .terminal-container .xterm .xterm-screen {
        position: relative !important;
      }
      
      .terminal-container .xterm .xterm-screen canvas {
        position: absolute !important;
        left: 0 !important;
        top: 0 !important;
      }
      
      .terminal-context-menu {
        position: fixed;
        background: ${isDarkTheme ? '#2d2d30' : '#ffffff'};
        border: 1px solid ${isDarkTheme ? '#454545' : '#cccccc'};
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        z-index: 1000;
        min-width: 120px;
        padding: 4px 0;
      }
      
      .terminal-context-menu-item {
        padding: 8px 16px;
        cursor: pointer;
        color: ${isDarkTheme ? '#cccccc' : '#000000'};
        font-size: 13px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }
      
      .terminal-context-menu-item:hover {
        background: ${isDarkTheme ? '#094771' : '#e5f3ff'};
      }
      
      .terminal-context-menu-item.disabled {
        color: ${isDarkTheme ? '#656565' : '#999999'};
        cursor: default;
      }
      
      .terminal-context-menu-item.disabled:hover {
        background: transparent;
      }
    `;
    document.head.appendChild(styleElement);
    
    return () => {
      document.head.removeChild(styleElement);
    };
  }, [isDarkTheme]);

  return (
    <div className={`terminal-container ${className}`} style={{
      width: '100%',
      height: '100%',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Terminal wrapper */}
      <div
        ref={terminalRef}
        onContextMenu={handleContextMenu}
        style={{
          width: '100%',
          height: '100%',
          position: 'relative',
        }}
      />
      
      {/* Context Menu */}
      {contextMenu.visible && (
        <div
          className="terminal-context-menu"
          style={{
            left: contextMenu.x,
            top: contextMenu.y,
          }}
        >
          <div
            className={`terminal-context-menu-item ${!contextMenu.hasSelection ? 'disabled' : ''}`}
            onClick={contextMenu.hasSelection ? handleCopy : undefined}
          >
            Copy
          </div>
          <div
            className="terminal-context-menu-item"
            onClick={handlePaste}
          >
            Paste
          </div>
          <div
            className="terminal-context-menu-item"
            onClick={handleSelectAll}
          >
            Select All
          </div>
        </div>
      )}
    </div>
  );
};

export default ICUITerminalPanelFromScratch; 