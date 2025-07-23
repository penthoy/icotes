/**
 * Backend-Connected Terminal Component
 * Updated to follow simpleterminal.tsx pattern - the most complete terminal implementation
 * 
 * This component provides a direct WebSocket connection to ICPY backend terminal service,
 * following the proven pattern from SimpleTerminal.tsx for maximum reliability.
 * 
 * Features:
 * - Direct WebSocket connection to ICPY backend (no complex state management)
 * - Clean terminal functionality using XTerm.js
 * - No local echo (backend handles all character echoing)  
 * - Proper scrolling behavior and theming
 * - Connection status monitoring
 * - Error handling and reconnection logic
 * - Responsive terminal sizing with FitAddon
 * - Copy/Paste functionality via backend clipboard API
 * - Keyboard shortcuts: Ctrl+Shift+C (copy), Ctrl+Shift+V (paste)
 */

import React, { useRef, useEffect, useState, useCallback, useImperativeHandle, forwardRef } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';

// Enhanced clipboard functionality (same as SimpleTerminal)
class EnhancedClipboard {
  private fallbackText: string = '';
  
  async copy(text: string): Promise<boolean> {
    if (!text) return false;
    
    // Store as fallback immediately
    this.fallbackText = text;
    
    let success = false;
    
    // Try server-side clipboard FIRST (most reliable cross-platform)
    if (await this.tryServerClipboard(text)) {
      console.log('✓ Clipboard copy via server (system clipboard)');
      success = true;
    }
    
    // Try browser native API (will fail in most cases due to security)
    if (await this.tryNativeClipboard(text)) {
      console.log('✓ Clipboard copy via native API');
      success = true;
    }
    
    // Always show success message since we have server fallback
    if (success) {
      this.showClipboardNotification('Text copied to system clipboard', 'success');
    } else {
      this.showClipboardNotification('Text stored in session clipboard', 'warning');
    }
    
    return true; // Always return true since we have fallbacks
  }

  async paste(): Promise<string> {
    // Try server-side clipboard FIRST
    const serverText = await this.tryServerPaste();
    if (serverText) {
      console.log('✓ Clipboard paste via server');
      return serverText;
    }
    
    // Try browser native API
    const nativeText = await this.tryNativePaste();
    if (nativeText) {
      console.log('✓ Clipboard paste via native API');
      return nativeText;
    }
    
    // Use fallback
    console.log('⚠ Using session clipboard fallback');
    return this.fallbackText;
  }

  private async tryNativeClipboard(text: string): Promise<boolean> {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (error) {
      console.log('Native clipboard write failed (expected):', error);
    }
    return false;
  }

  private async tryNativePaste(): Promise<string | null> {
    try {
      return await navigator.clipboard.readText();
    } catch (error) {
      console.log('Native clipboard read failed (expected):', error);
    }
    return null;
  }

  private async tryServerClipboard(text: string): Promise<boolean> {
    try {
      const response = await fetch('/clipboard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      return response.ok;
    } catch (error) {
      console.error('Server clipboard write error:', error);
    }
    return false;
  }

  private async tryServerPaste(): Promise<string | null> {
    try {
      const response = await fetch('/clipboard');
      const result = await response.json();
      
      if (result.success && result.text) {
        return result.text;
      }
    } catch (error) {
      console.error('Server clipboard paste error:', error);
    }
    return null;
  }

  private showClipboardNotification(message: string, type: 'success' | 'warning'): void {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 px-4 py-2 rounded shadow-lg z-50 transition-opacity ${
      type === 'success' ? 'bg-green-500 text-white' : 'bg-yellow-500 text-black'
    }`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
      notification.style.opacity = '0';
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 300);
    }, 3000);
  }
}

interface BackendConnectedTerminalProps {
  className?: string;
  terminalId?: string;
  onTerminalReady?: (terminal: Terminal) => void;
  onTerminalOutput?: (output: string) => void;
  onTerminalExit?: (code: number) => void;
}

export interface BackendConnectedTerminalRef {
  terminal: Terminal | null;
  sendInput: (input: string) => void;
  clear: () => void;
  focus: () => void;
  resize: () => void;
  destroy: () => void;
}

const BackendConnectedTerminal = forwardRef<BackendConnectedTerminalRef, BackendConnectedTerminalProps>(({
  className = '',
  terminalId: propTerminalId,
  onTerminalReady,
  onTerminalOutput,
  onTerminalExit
}, ref) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const websocket = useRef<WebSocket | null>(null);
  const terminalId = useRef<string>(propTerminalId || Math.random().toString(36).substring(2));
  const terminal = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const resizeObserver = useRef<ResizeObserver | null>(null);
  const resizeTimeout = useRef<NodeJS.Timeout | null>(null);
  const [isDarkTheme, setIsDarkTheme] = useState(false);

  // Clipboard handlers (same as SimpleTerminal)
  const handleCopy = useCallback(async () => {
    const selection = terminal.current?.getSelection();
    if (selection) {
      const clipboard = new EnhancedClipboard();
      await clipboard.copy(selection);
    }
  }, []);

  const handlePaste = useCallback(async () => {
    const clipboard = new EnhancedClipboard();
    const text = await clipboard.paste();
    if (text && websocket.current?.readyState === WebSocket.OPEN) {
      websocket.current.send(text);
    }
  }, []);

  // Theme detection (following ICUIEnhancedTerminalPanel pattern with debouncing)
  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    
    const detectTheme = () => {
      // Debounce theme detection to prevent rapid changes
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        const htmlElement = document.documentElement;
        const isDark = htmlElement.classList.contains('dark') || 
                       htmlElement.classList.contains('icui-theme-github-dark') ||
                       htmlElement.classList.contains('icui-theme-monokai') ||
                       htmlElement.classList.contains('icui-theme-one-dark') ||
                       htmlElement.classList.contains('icui-theme-dracula') ||
                       htmlElement.classList.contains('icui-theme-solarized-dark');
        setIsDarkTheme(isDark);
      }, 50); // 50ms debounce
    };

    detectTheme();
    
    // Create observer to watch for theme changes
    const observer = new MutationObserver(detectTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });

    return () => {
      clearTimeout(timeoutId);
      observer.disconnect();
    };
  }, []);

  // Main terminal initialization - runs only once (following SimpleTerminal pattern)
  useEffect(() => {
    if (!terminalRef.current) return;
    
    // Get theme colors from CSS variables
    const computedStyle = getComputedStyle(document.documentElement);
    const getThemeVar = (varName: string) => computedStyle.getPropertyValue(varName).trim();
    
    // Create terminal with theme-aware colors using ICUI CSS variables
    terminal.current = new Terminal({
      scrollback: 1000,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      cursorStyle: 'block',
      cursorBlink: true,
      theme: {
        // Use ICUI CSS variables for background to match other panels
        background: getThemeVar('--icui-bg-primary') || (isDarkTheme ? '#1e1e1e' : '#ffffff'),
        foreground: getThemeVar('--icui-text-primary') || (isDarkTheme ? '#d4d4d4' : '#000000'),
        cursor: getThemeVar('--icui-text-primary') || (isDarkTheme ? '#d4d4d4' : '#000000'),
        cursorAccent: getThemeVar('--icui-bg-primary') || (isDarkTheme ? '#1e1e1e' : '#ffffff'),
        selectionBackground: isDarkTheme ? '#264f78' : '#add6ff',
        // Use ICUI terminal color variables
        black: getThemeVar('--icui-terminal-black') || '#000000',
        brightBlack: getThemeVar('--icui-terminal-bright-black') || '#666666',
        red: getThemeVar('--icui-terminal-red') || '#cd3131',
        brightRed: getThemeVar('--icui-terminal-bright-red') || '#f14c4c',
        green: getThemeVar('--icui-terminal-green') || '#0dbc79',
        brightGreen: getThemeVar('--icui-terminal-bright-green') || '#23d18b',
        yellow: getThemeVar('--icui-terminal-yellow') || '#e5e510',
        brightYellow: getThemeVar('--icui-terminal-bright-yellow') || '#f5f543',
        blue: getThemeVar('--icui-terminal-blue') || '#2472c8',
        brightBlue: getThemeVar('--icui-terminal-bright-blue') || '#3b8eea',
        magenta: getThemeVar('--icui-terminal-magenta') || '#bc3fbc',
        brightMagenta: getThemeVar('--icui-terminal-bright-magenta') || '#d670d6',
        cyan: getThemeVar('--icui-terminal-cyan') || '#11a8cd',
        brightCyan: getThemeVar('--icui-terminal-bright-cyan') || '#29b8db',
        white: getThemeVar('--icui-terminal-white') || '#e5e5e5',
        brightWhite: getThemeVar('--icui-terminal-bright-white') || '#ffffff',
      },
    });

    // Create and load FitAddon
    fitAddon.current = new FitAddon();
    terminal.current.loadAddon(fitAddon.current);

    // CRITICAL: Open terminal BEFORE fitting (code-server pattern)
    terminal.current.open(terminalRef.current);
    
    // Fit after opening
    fitAddon.current.fit();

    // Write initial messages
    terminal.current.write('BackendConnectedTerminal initialized!\r\n');
    terminal.current.write('Terminal ID: ' + terminalId.current + '\r\n');
    terminal.current.write('Connecting to backend...\r\n');

    // Handle user input: send to backend. NO LOCAL ECHO - let backend handle it
    terminal.current.onData((data) => {
      if (websocket.current?.readyState === WebSocket.OPEN) {
        websocket.current.send(data);
        onTerminalOutput?.(data);
      }
    });

    // Connect to backend via WebSocket using .env configuration (same as SimpleTerminal)
    const envWsUrl = (import.meta as any).env?.VITE_WS_URL as string | undefined;
    let wsUrl: string;
    if (envWsUrl && envWsUrl.trim() !== '') {
      // Use configured WebSocket URL from .env
      wsUrl = `${envWsUrl}/terminal/${terminalId.current}`;
    } else {
      // Fallback to dynamic URL construction
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      wsUrl = `${protocol}//${host}/ws/terminal/${terminalId.current}`;
    }
    
    websocket.current = new WebSocket(wsUrl);
    
    websocket.current.onopen = () => {
      terminal.current?.write('\r\n\x1b[32mConnected to backend!\x1b[0m\r\n');
      // Clear screen on connect
      terminal.current?.clear();
      terminal.current?.write('BackendConnectedTerminal - Backend Connected!\r\n');
      terminal.current?.write('Terminal ID: ' + terminalId.current + '\r\n');
      terminal.current?.write('Ready for commands...\r\n');
      
      // Change to workspace directory if configured
      const workspaceRoot = (import.meta as any).env?.VITE_WORKSPACE_ROOT as string | undefined;
      if (workspaceRoot && websocket.current?.readyState === WebSocket.OPEN) {
        // Send cd command to change to workspace directory
        websocket.current.send(`cd "${workspaceRoot}"\r`);
        terminal.current?.write(`Changing to workspace: ${workspaceRoot}\r\n`);
      }
      
      onTerminalReady?.(terminal.current);
    };
    
    websocket.current.onmessage = (event) => {
      if (terminal.current) {
        terminal.current.write(event.data);
        onTerminalOutput?.(event.data);
      }
    };
    
    websocket.current.onclose = (event) => {
      if (event.code !== 1000) {
        terminal.current?.write("\r\n\x1b[31mTerminal disconnected\x1b[0m\r\n");
      }
      onTerminalExit?.(event.code || 0);
    };
    
    websocket.current.onerror = (error) => {
      console.error('[BackendConnectedTerminal] WebSocket error:', error);
      terminal.current?.write("\r\n\x1b[31mTerminal connection error\x1b[0m\r\n");
    };

    // Resize handling with debounce (same as SimpleTerminal)
    const handleResize = () => {
      if (resizeTimeout.current) {
        clearTimeout(resizeTimeout.current);
      }
      resizeTimeout.current = setTimeout(() => {
        if (fitAddon.current && terminal.current) {
          fitAddon.current.fit();
        }
      }, 100);
    };

    // Window resize listener
    window.addEventListener('resize', handleResize);

    // ResizeObserver for container changes
    if (terminalRef.current) {
      resizeObserver.current = new ResizeObserver(handleResize);
      resizeObserver.current.observe(terminalRef.current);
    }

    return () => {
      // Cleanup
      if (websocket.current) {
        websocket.current.close();
      }
      if (terminal.current) {
        terminal.current.dispose();
      }
      if (resizeTimeout.current) {
        clearTimeout(resizeTimeout.current);
      }
      if (resizeObserver.current) {
        resizeObserver.current.disconnect();
      }
      window.removeEventListener('resize', handleResize);
    };
  }, [onTerminalReady, onTerminalOutput, onTerminalExit]); // Removed isDarkTheme dependency

  // Separate effect to update terminal theme when isDarkTheme changes
  useEffect(() => {
    if (terminal.current && terminal.current.options) {
      // Add a small delay to ensure CSS variables have propagated
      const themeUpdateTimeout = setTimeout(() => {
        // Get theme colors from CSS variables
        const computedStyle = getComputedStyle(document.documentElement);
        const getThemeVar = (varName: string) => computedStyle.getPropertyValue(varName).trim();
        
        const newTheme = {
          // Use ICUI CSS variables for background to match other panels
          background: getThemeVar('--icui-bg-primary') || (isDarkTheme ? '#1e1e1e' : '#ffffff'),
          foreground: getThemeVar('--icui-text-primary') || (isDarkTheme ? '#d4d4d4' : '#000000'),
          cursor: getThemeVar('--icui-text-primary') || (isDarkTheme ? '#d4d4d4' : '#000000'),
          cursorAccent: getThemeVar('--icui-bg-primary') || (isDarkTheme ? '#1e1e1e' : '#ffffff'),
          selectionBackground: isDarkTheme ? '#264f78' : '#add6ff',
          // Use ICUI terminal color variables
          black: getThemeVar('--icui-terminal-black') || '#000000',
          brightBlack: getThemeVar('--icui-terminal-bright-black') || '#666666',
          red: getThemeVar('--icui-terminal-red') || '#cd3131',
          brightRed: getThemeVar('--icui-terminal-bright-red') || '#f14c4c',
          green: getThemeVar('--icui-terminal-green') || '#0dbc79',
          brightGreen: getThemeVar('--icui-terminal-bright-green') || '#23d18b',
          yellow: getThemeVar('--icui-terminal-yellow') || '#e5e510',
          brightYellow: getThemeVar('--icui-terminal-bright-yellow') || '#f5f543',
          blue: getThemeVar('--icui-terminal-blue') || '#2472c8',
          brightBlue: getThemeVar('--icui-terminal-bright-blue') || '#3b8eea',
          magenta: getThemeVar('--icui-terminal-magenta') || '#bc3fbc',
          brightMagenta: getThemeVar('--icui-terminal-bright-magenta') || '#d670d6',
          cyan: getThemeVar('--icui-terminal-cyan') || '#11a8cd',
          brightCyan: getThemeVar('--icui-terminal-bright-cyan') || '#29b8db',
          white: getThemeVar('--icui-terminal-white') || '#e5e5e5',
          brightWhite: getThemeVar('--icui-terminal-bright-white') || '#ffffff',
        };
        
        // Update theme without reinitializing terminal
        if (terminal.current) {
          terminal.current.options.theme = newTheme;
          terminal.current.refresh(0, terminal.current.rows - 1);
        }
      }, 100); // 100ms delay

      return () => clearTimeout(themeUpdateTimeout);
    }
  }, [isDarkTheme]);

  // Keyboard shortcuts for copy/paste (same as SimpleTerminal)
  useEffect(() => {
    const handleKeyDown = async (event: KeyboardEvent) => {
      // Only handle keyboard shortcuts when terminal is focused or as global shortcuts
      if ((event.ctrlKey || event.metaKey) && event.shiftKey) {
        if (event.key === 'C' || event.key === 'c') {
          event.preventDefault();
          await handleCopy();
        } else if (event.key === 'V' || event.key === 'v') {
          event.preventDefault();
          await handlePaste();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleCopy, handlePaste]);

  // Apply critical CSS for viewport scrolling (same as SimpleTerminal)
  useEffect(() => {
    // Get theme colors from CSS variables for viewport styling
    const computedStyle = getComputedStyle(document.documentElement);
    const bgColor = computedStyle.getPropertyValue('--icui-bg-primary').trim() || 
                   (isDarkTheme ? '#1e1e1e' : '#ffffff');
    
    const styleElement = document.createElement('style');
    styleElement.id = 'backend-connected-terminal-styles'; // Add ID for easier cleanup
    styleElement.textContent = `
      .backend-connected-terminal-container .xterm .xterm-viewport {
        background-color: ${bgColor} !important;
        overflow-y: scroll !important;
        position: absolute !important;
        top: 0 !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
      }
      
      .backend-connected-terminal-container .xterm .xterm-screen {
        position: relative !important;
      }
      
      .backend-connected-terminal-container .xterm .xterm-screen canvas {
        position: absolute !important;
        left: 0 !important;
        top: 0 !important;
      }
    `;
    
    // Remove any existing styles with the same ID first
    const existingStyle = document.getElementById('backend-connected-terminal-styles');
    if (existingStyle) {
      existingStyle.remove();
    }
    
    document.head.appendChild(styleElement);

    return () => {
      // Clean up the style element
      const elementToRemove = document.getElementById('backend-connected-terminal-styles');
      if (elementToRemove) {
        elementToRemove.remove();
      }
    };
  }, [isDarkTheme]); // Add isDarkTheme dependency to update when theme changes

  // Additional effect to force update terminal viewport background when theme changes
  useEffect(() => {
    if (!terminalRef.current || !terminal.current) return;

    // Add a small delay to ensure CSS variables have propagated
    const updateTimeout = setTimeout(() => {
      // Force update viewport background directly
      const terminalViewport = terminalRef.current?.querySelector('.xterm-viewport');
      if (terminalViewport) {
        const computedStyle = getComputedStyle(document.documentElement);
        const bgColor = computedStyle.getPropertyValue('--icui-bg-primary').trim() || 
                       (isDarkTheme ? '#1e1e1e' : '#ffffff');
        (terminalViewport as HTMLElement).style.backgroundColor = bgColor;
      }
    }, 100); // 100ms delay to ensure CSS variables are updated

    return () => clearTimeout(updateTimeout);
  }, [isDarkTheme]); // Update viewport background when theme changes

  // Expose terminal methods via ref (matching SimpleTerminal pattern)
  useImperativeHandle(ref, () => ({
    terminal: terminal.current,
    sendInput: (input: string) => {
      if (websocket.current?.readyState === WebSocket.OPEN) {
        websocket.current.send(input);
      }
    },
    clear: () => {
      terminal.current?.clear();
    },
    focus: () => {
      terminal.current?.focus();
    },
    resize: () => {
      if (fitAddon.current) {
        fitAddon.current.fit();
      }
    },
    destroy: () => {
      if (websocket.current) {
        websocket.current.close();
      }
      if (terminal.current) {
        terminal.current.dispose();
      }
    }
  }));

  return (
    <div className={`backend-connected-terminal ${className}`}>
      <div className="backend-connected-terminal-container h-full w-full">
        <div ref={terminalRef} className="h-full w-full" />
      </div>
    </div>
  );
});

BackendConnectedTerminal.displayName = 'BackendConnectedTerminal';

export default BackendConnectedTerminal;
