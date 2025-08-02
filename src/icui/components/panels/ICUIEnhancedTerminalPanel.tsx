/**
 * ICUI Enhanced Terminal Panel
 * Advanced terminal with theme support and enhanced features
 * Based on ICUITerminalPanel but with enhanced theming and ICUI integration
 * 
 * SCROLLING FIX APPLIED:
 * - Uses proper xterm.css viewport classes with overflow-y: scroll
 * - Follows code-server DOM structure pattern
 * - Lets xterm.js handle scrolling internally through .xterm-viewport
 * - Uses FitAddon with proper initialization order
 * - Container has explicit height constraints
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css'; // MUST be imported first

interface ICUIEnhancedTerminalPanelProps {
  className?: string;
}

interface ContextMenuState {
  visible: boolean;
  x: number;
  y: number;
  hasSelection: boolean;
}

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
      if (!result.success) {
        console.error('✗ Clipboard copy failed on backend:', result.message);
      }
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


export const ICUIEnhancedTerminalPanel: React.FC<ICUIEnhancedTerminalPanelProps> = ({ className = '' }) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const websocket = useRef<WebSocket | null>(null);
  const terminalId = useRef<string>(Math.random().toString(36).substring(2));
  const terminal = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const resizeObserver = useRef<ResizeObserver | null>(null);
  const resizeTimeout = useRef<NodeJS.Timeout | null>(null);
  // Track how many printable characters have been locally echoed on the current line
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    visible: false,
    x: 0,
    y: 0,
    hasSelection: false,
  });
  
  // Enhanced theme detection with debounce for performance
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
                       htmlElement.classList.contains('icui-theme-one-dark');
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

  // Initialize terminal once (performance optimization) - SCROLLING FIX APPLIED
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
    
    // Wait for DOM to be ready and then fit with safety checks
    setTimeout(() => {
      if (fitAddon.current && terminal.current && terminalRef.current) {
        try {
          // Check if container has valid dimensions before fitting
          const rect = terminalRef.current.getBoundingClientRect();
          if (rect.width > 0 && rect.height > 0) {
            fitAddon.current.fit();
          }
        } catch (error) {
          console.warn('Enhanced terminal fit error during initialization:', error);
          // Retry after a longer delay
          setTimeout(() => {
            if (fitAddon.current && terminal.current) {
              try {
                fitAddon.current.fit();
              } catch (retryError) {
                console.warn('Enhanced terminal fit retry failed:', retryError);
              }
            }
          }, 500);
        }
      }
    }, 100);

    // Handle user input: send to backend. Local echo is now disabled.
    // The backend PTY will handle echoing characters back to us.
    terminal.current.onData((data) => {
      if (websocket.current?.readyState === WebSocket.OPEN) {
        websocket.current.send(data);
      }
    });

    // Connect to backend via WebSocket
    const envWsUrl = import.meta.env.VITE_WS_URL as string | undefined;
    let wsUrl: string;
    
    if (envWsUrl) {
      wsUrl = `${envWsUrl}/ws/terminal/${terminalId.current}`;
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      wsUrl = `${protocol}//${host}/ws/terminal/${terminalId.current}`;
    }

    websocket.current = new WebSocket(wsUrl);

    websocket.current.onopen = () => {
      // WebSocket connection established
    };

    websocket.current.onmessage = (event) => {
      if (terminal.current) {
        terminal.current.write(event.data);
      }
    };

    websocket.current.onclose = () => {
      // WebSocket connection closed
    };

    websocket.current.onerror = (error) => {
      // Handle WebSocket connection errors
    };

    // Resize handling with debounce and safety checks
    const handleResize = () => {
      if (resizeTimeout.current) {
        clearTimeout(resizeTimeout.current);
      }
      resizeTimeout.current = setTimeout(() => {
        if (fitAddon.current && terminal.current && terminalRef.current) {
          try {
            // Check if container has valid dimensions before fitting
            const rect = terminalRef.current.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
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
          } catch (error) {
            console.warn('Enhanced terminal fit error during resize:', error);
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

    // Cleanup
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
  }, []); // Only run once on mount

  // Clipboard and context menu handlers
  const handleCopy = useCallback(async () => {
    const selection = terminal.current?.getSelection();
    if (selection) {
      const clipboard = new TerminalClipboard();
      await clipboard.copy(selection);
    }
    setContextMenu(prev => ({ ...prev, visible: false }));
  }, []);

  const handlePaste = useCallback(async () => {
    const clipboard = new TerminalClipboard();
    const text = await clipboard.paste();
    if (text && websocket.current?.readyState === WebSocket.OPEN) {
      websocket.current.send(text);
    }
    setContextMenu(prev => ({ ...prev, visible: false }));
  }, []);

  const handleContextMenu = useCallback((event: MouseEvent) => {
    event.preventDefault();
    const selection = terminal.current?.getSelection() || '';
    setContextMenu({
      visible: true,
      x: event.clientX,
      y: event.clientY,
      hasSelection: !!selection,
    });
  }, []);

  const handleClickOutside = useCallback((event: MouseEvent) => {
    if (contextMenu.visible) {
      setContextMenu(prev => ({ ...prev, visible: false }));
    }
  }, [contextMenu.visible]);

  // Effect for context menu and keyboard shortcuts
  useEffect(() => {
    const termEl = terminalRef.current;
    if (termEl) {
      termEl.addEventListener('contextmenu', handleContextMenu);
      document.addEventListener('click', handleClickOutside);
    }

    const handleKeyDown = async (event: KeyboardEvent) => {
      const isTerminalFocused = terminalRef.current?.contains(document.activeElement);
      if (!isTerminalFocused) return;
      
      const clipboard = new TerminalClipboard();

      // Ctrl+Shift+C for copy
      if (event.ctrlKey && event.shiftKey && (event.key === 'C' || event.key === 'c')) {
        event.preventDefault();
        handleCopy();
      }

      // Ctrl+Shift+V for paste
      if (event.ctrlKey && event.shiftKey && (event.key === 'V' || event.key === 'v')) {
        event.preventDefault();
        handlePaste();
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      if (termEl) {
        termEl.removeEventListener('contextmenu', handleContextMenu);
        document.removeEventListener('click', handleClickOutside);
      }
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleContextMenu, handleClickOutside, handleCopy, handlePaste]);

  // Only update theme when it changes
  useEffect(() => {
    if (terminal.current) {
      // Get theme colors from CSS variables
      const computedStyle = getComputedStyle(document.documentElement);
      const getThemeVar = (varName: string) => computedStyle.getPropertyValue(varName).trim();

      // Update terminal theme with CSS variables
      terminal.current.options.theme = {
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
    }
  }, [isDarkTheme]);

  // Apply critical CSS for viewport scrolling with theme-aware colors
  useEffect(() => {
    const styleElement = document.createElement('style');
    const computedStyle = getComputedStyle(document.documentElement);
    const terminalBg = computedStyle.getPropertyValue('--icui-bg-primary').trim() || (isDarkTheme ? '#1e1e1e' : '#ffffff');
    
    styleElement.textContent = `
      .terminal-container .xterm .xterm-viewport {
        background-color: ${terminalBg} !important;
        overflow-y: scroll !important;
        position: absolute !important;
        top: 0 !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
      }
      
      .terminal-container .xterm .xterm-screen {
        position: relative !important;
        background-color: ${terminalBg} !important;
      }
      
      .terminal-container .xterm .xterm-screen canvas {
        position: absolute !important;
        left: 0 !important;
        top: 0 !important;
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
      {contextMenu.visible && (
        <div
          className="absolute rounded-md shadow-lg py-1 z-50"
          style={{
            top: contextMenu.y,
            left: contextMenu.x,
            backgroundColor: 'var(--icui-bg-secondary)',
            border: '1px solid var(--icui-br-primary)',
            color: 'var(--icui-text-primary)',
          }}
        >
          {contextMenu.hasSelection && (
            <button
              onClick={handleCopy}
              className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-700"
            >
              Copy
            </button>
          )}
          <button
            onClick={handlePaste}
            className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-700"
          >
            Paste
          </button>
        </div>
      )}
    </div>
  );
};

export default ICUIEnhancedTerminalPanel; 