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
 * - Clean, minimal implementation for debugging
 * 
 * Usage:
 * - Access at /simple-terminal route
 * - Automatically connects to backend on mount
 * - Provides visual feedback for connection status
 * - Automatically fits to container size
 * 
 * @see ICUITerminalPanel.tsx - Original reference implementation
 * @see ICUIEnhancedTerminalPanel.tsx - Full enhanced terminal (fixes applied from here)
 * @see BackendConnectedTerminal.tsx - Full backend-integrated terminal
 */

import React, { useRef, useEffect, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';

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
    
    console.log('[SimpleTerminal] Initializing terminal...');
    
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
      console.log('[SimpleTerminal] Data input:', data);
      
      if (websocket.current?.readyState === WebSocket.OPEN) {
        websocket.current.send(data);
      }
    });

    // Connect to backend via WebSocket
    const envWsUrl = (import.meta as any).env?.VITE_WS_URL as string | undefined;
    let wsUrl: string;
    if (envWsUrl && envWsUrl.trim() !== '') {
      wsUrl = `${envWsUrl}/ws/terminal/${terminalId.current}`;
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      wsUrl = `${protocol}//${host}/ws/terminal/${terminalId.current}`;
    }
    
    console.log('[SimpleTerminal] Connecting to WebSocket:', wsUrl);
    
    websocket.current = new WebSocket(wsUrl);
    
    websocket.current.onopen = () => {
      console.log('[SimpleTerminal] WebSocket connected');
      terminal.current?.write('\r\n\x1b[32mConnected to backend!\x1b[0m\r\n');
      // Clear screen on connect
      terminal.current?.clear();
      terminal.current?.write('SimpleTerminal - Backend Connected!\r\n');
      terminal.current?.write('Terminal ID: ' + terminalId.current + '\r\n');
      terminal.current?.write('Ready for commands...\r\n');
    };
    
    websocket.current.onmessage = (event) => {
      console.log('[SimpleTerminal] WebSocket message:', event.data);
      if (terminal.current) {
        terminal.current.write(event.data);
      }
    };
    
    websocket.current.onclose = (event) => {
      console.log('[SimpleTerminal] WebSocket closed:', event.code, event.reason);
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
      console.log('[SimpleTerminal] Cleanup');
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
