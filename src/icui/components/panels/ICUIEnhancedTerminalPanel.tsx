/**
 * ICUI Enhanced Terminal Panel
 * Advanced terminal with theme support and enhanced features
 * Based on ICUITerminalPanel but with enhanced theming and ICUI integration
 */

import React, { useRef, useEffect, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import '@xterm/xterm/css/xterm.css';

interface ICUIEnhancedTerminalPanelProps {
  className?: string;
}

export const ICUIEnhancedTerminalPanel: React.FC<ICUIEnhancedTerminalPanelProps> = ({ className = '' }) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const websocket = useRef<WebSocket | null>(null);
  const terminalId = useRef<string>(Math.random().toString(36).substring(2));
  const terminal = useRef<Terminal | null>(null);
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

  // Initialize terminal once (performance optimization)
  useEffect(() => {
    if (!terminalRef.current) return;
    
    // Create terminal with enhanced theme-aware colors using ICUI CSS variables
    terminal.current = new Terminal({
      cols: 80,
      rows: 24,
      fontSize: 14,
      fontFamily: 'monospace',
      theme: {
        background: 'var(--icui-bg-primary)',
        foreground: 'var(--icui-text-primary)',
        cursor: 'var(--icui-text-primary)',
        cursorAccent: 'var(--icui-bg-primary)',
        selectionBackground: 'var(--icui-accent)',
        black: '#000000',
        brightBlack: 'var(--icui-terminal-bright-black)',
        red: 'var(--icui-terminal-red)',
        brightRed: 'var(--icui-terminal-bright-red)',
        green: 'var(--icui-terminal-green)',
        brightGreen: 'var(--icui-terminal-bright-green)',
        yellow: 'var(--icui-terminal-yellow)',
        brightYellow: 'var(--icui-terminal-bright-yellow)',
        blue: 'var(--icui-terminal-blue)',
        brightBlue: 'var(--icui-terminal-bright-blue)',
        magenta: 'var(--icui-terminal-magenta)',
        brightMagenta: 'var(--icui-terminal-bright-magenta)',
        cyan: 'var(--icui-terminal-cyan)',
        brightCyan: 'var(--icui-terminal-bright-cyan)',
        white: 'var(--icui-terminal-white)',
        brightWhite: 'var(--icui-terminal-bright-white)',
      },
    });

    // Open the terminal
    terminal.current.open(terminalRef.current);
    
    // Write a welcome message with theme awareness
    terminal.current.write('ICUIEnhancedTerminalPanel initialized!\r\n');

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
      background: 'var(--icui-bg-primary)',
      foreground: 'var(--icui-text-primary)',
      cursor: 'var(--icui-text-primary)',
      cursorAccent: 'var(--icui-bg-primary)',
      selectionBackground: 'var(--icui-accent)',
      black: '#000000',
      brightBlack: 'var(--icui-terminal-bright-black)',
      red: 'var(--icui-terminal-red)',
      brightRed: 'var(--icui-terminal-bright-red)',
      green: 'var(--icui-terminal-green)',
      brightGreen: 'var(--icui-terminal-bright-green)',
      yellow: 'var(--icui-terminal-yellow)',
      brightYellow: 'var(--icui-terminal-bright-yellow)',
      blue: 'var(--icui-terminal-blue)',
      brightBlue: 'var(--icui-terminal-bright-blue)',
      magenta: 'var(--icui-terminal-magenta)',
      brightMagenta: 'var(--icui-terminal-bright-magenta)',
      cyan: 'var(--icui-terminal-cyan)',
      brightCyan: 'var(--icui-terminal-bright-cyan)',
      white: 'var(--icui-terminal-white)',
      brightWhite: 'var(--icui-terminal-bright-white)',
    };
  }, [isDarkTheme]); // Only update theme when it changes

  return (
    <div className={`icui-enhanced-terminal-panel h-full flex flex-col ${className}`} style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
      {/* Terminal Content Area */}
      <div className="flex-1 overflow-hidden" style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
        <div
          className={`icui-terminal ${className}`}
          style={{
            height: '100%',
            width: '100%',
            backgroundColor: 'var(--icui-bg-primary)',
            overflow: 'auto',
          }}
        >
          <div
            ref={terminalRef}
            style={{
              height: '100%',
              width: '100%',
              minHeight: '100%',
              minWidth: '100%',
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default ICUIEnhancedTerminalPanel; 