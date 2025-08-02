/**
 * Simple Terminal Implementation
 * Based on ICUITerminalPanel.tsx - A minimal, working terminal for ICUI-ICPY integration
 * 
 * This component provides a simplified terminal implementation that directly connects
 * to the ICPY backend via WebSocket, without the complexity of the full backend state
 * management system. It's designed to debug and test terminal connectivity issues.
 * 
 * FIXES APPLIED:
 * - Removed local echo to prevent character duplication (backend handles echo)
 * - Applied proper scrolling container structure from ICUIEnhancedTerminalPanel
 * - Added FitAddon for proper terminal sizing and resizing
 * - Proper CSS injection for xterm viewport scrolling
 * - Theme-aware colors with automatic theme detection
 * - Proper cleanup and resource management
 * - Added clipboard functionality with backend API integration
 * 
 * Features:
 * - Direct WebSocket connection to ICPY backend
 * - Basic terminal functionality using XTerm.js
 * - No local echo (backend handles all character echoing)
 * - Proper scrolling behavior (no more black screen issues)
 * - Connection status monitoring
 * - Error handling and reconnection logic
 * - Theme-aware styling (dark/light mode support)
 * - Responsive terminal sizing with FitAddon
 * - Copy/Paste functionality via backend clipboard API (POST /clipboard, GET /clipboard)
 * - Keyboard shortcuts: Ctrl+Shift+C (copy), Ctrl+Shift+V (paste)
 * - Clean, minimal implementation for debugging
 * 
 * Usage:
 * - Access at /simple-terminal route
 * - Automatically connects to backend on mount
 * - Provides visual feedback for connection status
 * - Automatically fits to container size
 * - Select text and press Ctrl+Shift+C to copy
 * - Press Ctrl+Shift+V to paste from clipboard
 * 
 * @see ICUITerminalPanel.tsx - Original reference implementation
 * @see ICUIEnhancedTerminalPanel.tsx - Full enhanced terminal (fixes applied from here)
 * @see BackendConnectedTerminal.tsx - Full backend-integrated terminal
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';

// Simple clipboard class using backend API calls
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
      console.log('✓ Clipboard paste via server (system clipboard)');
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
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch (error) {
      // Silently fail - this is expected in most cases
    }
    return false;
  }

  private async tryNativePaste(): Promise<string | null> {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        return await navigator.clipboard.readText();
      }
    } catch (error) {
      // Silently fail - this is expected in most cases
    }
    return null;
  }

  private async tryServerClipboard(text: string): Promise<boolean> {
    try {
      const response = await fetch('/clipboard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });

      const result = await response.json();
      if (result.success) {
        return true;
      } else {
        console.error('Server clipboard failed:', result.message);
      }
    } catch (error) {
      console.error('Server clipboard error:', error);
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
    // Create a temporary notification element
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 px-4 py-2 rounded shadow-lg z-50 transition-opacity ${
      type === 'success' ? 'bg-green-500 text-white' : 'bg-yellow-500 text-black'
    }`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
      notification.style.opacity = '0';
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 300);
    }, 3000);
  }

  async getStatus(): Promise<any> {
    try {
      const response = await fetch('/clipboard/status');
      return await response.json();
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
}

interface SimpleTerminalProps {
  className?: string;
}

const SimpleTerminal: React.FC<SimpleTerminalProps> = ({ className = '' }) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const websocket = useRef<WebSocket | null>(null);
  const terminalId = useRef<string>(Math.random().toString(36).substring(2));
  const terminal = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const resizeObserver = useRef<ResizeObserver | null>(null);
  const resizeTimeout = useRef<NodeJS.Timeout | null>(null);
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [clipboardStatus, setClipboardStatus] = useState<any>(null);
  const [clipboardMethods, setClipboardMethods] = useState<string[]>([]);

  // Clipboard handlers
  const handleCopy = useCallback(async () => {
    const selection = terminal.current?.getSelection();
    if (selection) {
      const clipboard = new EnhancedClipboard();
      const success = await clipboard.copy(selection);
      // Success feedback is handled by the clipboard service notifications
    }
  }, []);

  const handlePaste = useCallback(async () => {
    const clipboard = new EnhancedClipboard();
    const text = await clipboard.paste();
    if (text && websocket.current?.readyState === WebSocket.OPEN) {
      websocket.current.send(text);
      // Paste feedback is handled by the clipboard service
    }
  }, []);

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

  useEffect(() => {
    if (!terminalRef.current) return;
    
    // Create terminal with proper theme-aware colors
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

    // Write initial messages
    terminal.current.write('SimpleTerminal initialized!\r\n');
    terminal.current.write('Terminal ID: ' + terminalId.current + '\r\n');
    terminal.current.write('Connecting to backend...\r\n');

    // Handle user input: send to backend. NO LOCAL ECHO - let backend handle it
    terminal.current.onData((data) => {
      if (websocket.current?.readyState === WebSocket.OPEN) {
        websocket.current.send(data);
      }
    });

    // Connect to backend via WebSocket using .env configuration
    const envWsUrl = (import.meta as any).env?.VITE_WS_URL as string | undefined;
    let wsUrl: string;
    if (envWsUrl && envWsUrl.trim() !== '') {
      // Use configured WebSocket URL from .env
      wsUrl = `${envWsUrl}/ws/terminal/${terminalId.current}`;
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
      terminal.current?.write('SimpleTerminal - Backend Connected!\r\n');
      terminal.current?.write('Terminal ID: ' + terminalId.current + '\r\n');
      terminal.current?.write('Ready for commands...\r\n');
    };
    
    websocket.current.onmessage = (event) => {
      if (terminal.current) {
        terminal.current.write(event.data);
      }
    };
    
    websocket.current.onclose = (event) => {
      if (event.code !== 1000) {
        terminal.current?.write("\r\n\x1b[31mTerminal disconnected\x1b[0m\r\n");
      }
    };
    
    websocket.current.onerror = (error) => {
      console.error('[SimpleTerminal] WebSocket error:', error);
      terminal.current?.write("\r\n\x1b[31mTerminal connection error\x1b[0m\r\n");
    };

    // Resize handling with debounce
    const handleResize = () => {
      if (resizeTimeout.current) {
        clearTimeout(resizeTimeout.current);
      }
      resizeTimeout.current = setTimeout(() => {
        if (fitAddon.current && terminal.current) {
          fitAddon.current.fit();
          
          // Send resize info to backend
          const dims = fitAddon.current.proposeDimensions();
          if (dims && websocket.current?.readyState === WebSocket.OPEN) {
            websocket.current.send(JSON.stringify({
              type: 'resize',
              cols: dims.cols,
              rows: dims.rows
            }));
          }
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
      if (resizeTimeout.current) {
        clearTimeout(resizeTimeout.current);
      }
      if (resizeObserver.current) {
        resizeObserver.current.disconnect();
      }
      window.removeEventListener('resize', handleResize);
      
      websocket.current?.close();
      if (terminal.current) {
        terminal.current.dispose();
        terminal.current = null;
      }
    };
  }, [isDarkTheme]);

  // Keyboard shortcuts for copy/paste
  useEffect(() => {
    const handleKeyDown = async (event: KeyboardEvent) => {
      const isTerminalFocused = terminalRef.current?.contains(document.activeElement);
      if (!isTerminalFocused) return;

      // Ctrl+Shift+C for copy
      if (event.ctrlKey && event.shiftKey && (event.key === 'C' || event.key === 'c')) {
        event.preventDefault();
        await handleCopy();
      }

      // Ctrl+Shift+V for paste
      if (event.ctrlKey && event.shiftKey && (event.key === 'V' || event.key === 'v')) {
        event.preventDefault();
        await handlePaste();
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleCopy, handlePaste]);

  // Check clipboard status on mount
  useEffect(() => {
    const checkClipboardStatus = async () => {
      const clipboard = new EnhancedClipboard();
      const status = await clipboard.getStatus();
      
      if (status.success) {
        setClipboardStatus(status.status);
        setClipboardMethods(status.status.available_methods || []);
        // Clipboard capabilities logged only during development
      }
    };

    checkClipboardStatus();
  }, []);

  // Apply critical CSS for viewport scrolling (fixes scrolling issues)
  useEffect(() => {
    const styleElement = document.createElement('style');
    styleElement.textContent = `
      .simple-terminal-container .xterm .xterm-viewport {
        background-color: ${isDarkTheme ? '#1e1e1e' : '#ffffff'} !important;
        overflow-y: scroll !important;
        position: absolute !important;
        top: 0 !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
      }
      
      .simple-terminal-container .xterm .xterm-screen {
        position: relative !important;
      }
      
      .simple-terminal-container .xterm .xterm-screen canvas {
        position: absolute !important;
        left: 0 !important;
        top: 0 !important;
      }
    `;
    document.head.appendChild(styleElement);
    
    return () => {
      if (document.head.contains(styleElement)) {
        document.head.removeChild(styleElement);
      }
    };
  }, [isDarkTheme]);

  return (
    <div className={`simple-terminal ${className}`}>
      <div className="bg-blue-100 border-b p-2 text-sm">
        <div className="font-semibold">Simple Terminal</div>
        <div className="text-xs text-gray-600">
          Direct WebSocket connection to ICPY backend
        </div>
        <div className="text-xs text-gray-500 mt-1">
          Copy: Ctrl+Shift+C | Paste: Ctrl+Shift+V
          {clipboardStatus && (
            <span className="ml-3 text-blue-600">
              Clipboard: {clipboardStatus.capabilities?.read ? '✓ System' : '⚠ Session only'}
            </span>
          )}
        </div>
        {clipboardStatus && (
          <div className="text-xs text-gray-500 mt-1">
            <span className="font-medium">Clipboard:</span> {clipboardMethods.join(', ')} 
            {window.isSecureContext && navigator.clipboard ? ' + native' : ''}
          </div>
        )}
      </div>
      
      <div className="simple-terminal-container" style={{
        width: '100%',
        height: '400px',
        position: 'relative',
        overflow: 'hidden', // Container manages overall overflow
      }}>
        {/* Terminal wrapper - NO overflow styling, following code-server pattern */}
        <div
          ref={terminalRef}
          style={{
            width: '100%',
            height: '100%',
            position: 'relative',
            // Do NOT set overflow properties here - let xterm.js handle it
          }}
        />
      </div>
    </div>
  );
};

export default SimpleTerminal;
