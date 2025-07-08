/**
 * ICUI Terminal Panel - Reference Implementation
 * A minimal, working terminal panel for the ICUI framework
 */

import React, { useRef, useEffect } from 'react';
import { Terminal } from '@xterm/xterm';
import '@xterm/xterm/css/xterm.css';

interface ICUITerminalPanelProps {
  className?: string;
}

const ICUITerminalPanel: React.FC<ICUITerminalPanelProps> = ({ className = '' }) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const websocket = useRef<WebSocket | null>(null);
  const terminalId = useRef<string>(Math.random().toString(36).substring(2));
  const terminal = useRef<Terminal | null>(null);

  useEffect(() => {
    if (!terminalRef.current) return;

    console.log('ICUITerminalPanel: Creating terminal...');
    
    // Create the most basic terminal possible
    terminal.current = new Terminal({
      cols: 80,
      rows: 24,
      fontSize: 14,
      fontFamily: 'monospace',
      theme: {
        background: '#000000',
        foreground: '#ffffff',
      },
    });

    // Open the terminal
    terminal.current.open(terminalRef.current);
    
    // Write a simple test message
    terminal.current.write('ICUITerminalPanel initialized!\r\n');

    // Handle user input and send to WebSocket if connected
    terminal.current.onData((data) => {
      if (websocket.current?.readyState === WebSocket.OPEN) {
        websocket.current.send(data);
      } else {
        terminal.current?.write(data);
      }
    });

    // Connect to backend via WebSocket using same logic as XTerminal
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

    console.log('ICUITerminalPanel: Terminal opened and ready');

    return () => {
      websocket.current?.close();
      if (terminal.current) {
        terminal.current.dispose();
        terminal.current = null;
      }
    };
  }, []);

  return (
    <div
      className={`icui-terminal ${className}`}
      style={{
        height: '100%',
        width: '100%',
        backgroundColor: '#000000', // Match terminal background
        overflow: 'auto', // Enable scrollbars when content overflows
      }}
    >
      <div
        ref={terminalRef}
        style={{
          height: '100%',
          width: '100%',
          minHeight: '100%', // Ensure inner content expands
          minWidth: '100%',
        }}
      />
    </div>
  );
};

export default ICUITerminalPanel;
