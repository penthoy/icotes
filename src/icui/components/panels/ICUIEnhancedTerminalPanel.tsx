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
  const [isDarkTheme, setIsDarkTheme] = useState(false);

  // Enhanced theme detection - matches ICUIEnhancedEditorPanel pattern
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
    
    // Create observer to watch for theme changes
    const observer = new MutationObserver(detectTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });

    return () => observer.disconnect();
  }, []);

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

    // Handle user input and send to WebSocket if connected
    terminal.current.onData((data) => {
      if (websocket.current?.readyState === WebSocket.OPEN) {
        websocket.current.send(data);
      } else {
        terminal.current?.write(data);
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
  }, [isDarkTheme]); // Recreate terminal when theme changes

  return (
    <div className={`icui-enhanced-terminal-panel h-full flex flex-col ${className}`} style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
      {/* Header - following enhanced panel pattern */}
      <div className="flex items-center justify-between px-3 py-2 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)' }}>
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium" style={{ color: 'var(--icui-text-primary)' }}>Terminal</span>
          <span className="text-xs px-2 py-1 rounded" style={{ backgroundColor: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-muted)' }}>
            {isDarkTheme ? 'Dark' : 'Light'} Theme
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => terminal.current?.clear()}
            className="text-xs px-2 py-1 rounded hover:opacity-80 transition-opacity"
            style={{ backgroundColor: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-primary)' }}
          >
            Clear
          </button>
        </div>
      </div>

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

      {/* Status Bar - following enhanced panel pattern */}
      <div className="px-3 py-1 border-t text-xs flex justify-between" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderTopColor: 'var(--icui-border-subtle)', color: 'var(--icui-text-muted)' }}>
        <span>Terminal Session: {terminalId.current}</span>
        <span>Enhanced Terminal • Theme: {isDarkTheme ? 'Dark' : 'Light'}</span>
      </div>
    </div>
  );
};

export default ICUIEnhancedTerminalPanel; 