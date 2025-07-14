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

import React, { useRef, useEffect, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css'; // MUST be imported first

interface ICUIEnhancedTerminalPanelProps {
  className?: string;
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
  const typedCount = useRef<number>(0);
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  
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
    
    // Create terminal with enhanced theme-aware colors using ICUI CSS variables
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
    
    // Write a welcome message with theme awareness
    terminal.current.write('ICUIEnhancedTerminalPanel initialized! Try running: history\r\n');

    // Handle user input: send to backend AND perform local echo for instant feedback
    terminal.current.onData((data) => {
      // Send data to backend if connected
      if (websocket.current?.readyState === WebSocket.OPEN) {
        websocket.current.send(data);
      }

      // Local echo for printable characters & backspace (latency reduction)
      // Printable ASCII range 0x20 - 0x7E
      // Only echo printable characters locally. Avoid echoing backspace/DEL
      // because the remote shell will send the appropriate cursor control
      // sequences ("\b \b") which could otherwise be duplicated and become
      // visible (e.g., "\b \b").
      if (/^[\x20-\x7E]+$/.test(data)) {
        terminal.current?.write(data);
        typedCount.current += data.length; // should be 1
      } else if (data === '\b' || data === '\x7f') {
         if (typedCount.current > 0) {
           // Echo backspace locally by moving cursor left, erasing char, moving left again
           terminal.current?.write('\b \b');
           typedCount.current -= 1;
         }
      } else if (data === '\r' || data === '\n') {
        // Reset counter at end of line
        typedCount.current = 0;
      }
    });

    // Connect to backend via WebSocket using same logic as ICUITerminalPanel
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
      // Clear screen on connect
      terminal.current?.clear();
    };
    websocket.current.onmessage = (event) => {
      terminal.current?.write(event.data);
    };
    websocket.current.onclose = (event) => {
      if (event.code !== 1000) {
        terminal.current?.write("\r\n\x1b[31mTerminal disconnected\x1b[0m\r\n");
      }
    };
    websocket.current.onerror = (error) => {
      terminal.current?.write("\r\n\x1b[31mTerminal connection error\x1b[0m\r\n");
    };

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
  }, []); // Only create terminal once on mount

  // Update terminal theme when theme changes (performance optimization)
  useEffect(() => {
    if (!terminal.current) return;
    
    // Update terminal theme without recreating the entire terminal
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
  }, [isDarkTheme]); // Only update theme when it changes

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
    </div>
  );
};

export default ICUIEnhancedTerminalPanel; 