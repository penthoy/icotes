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
  const typedCount = useRef<number>(0);

  useEffect(() => {
    if (!terminalRef.current) return;
    
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

    // Handle user input: send to backend and perform local echo for instant feedback
    terminal.current.onData((data) => {
      if (websocket.current?.readyState === WebSocket.OPEN) {
        websocket.current.send(data);
      }

      // Local echo for printable characters only. Avoid echoing backspace/DEL
      // because the remote shell will handle character deletions and emit
      // the correct control sequence. Echoing them locally causes the raw
      // "\b \b" characters to appear.
      if (/^[\x20-\x7E]+$/.test(data)) {
        terminal.current?.write(data);
        typedCount.current += data.length;
      } else if (data === '\b' || data === '\x7f') {
        if (typedCount.current > 0) {
          terminal.current?.write('\b \b');
          typedCount.current -= 1;
        }
      } else if (data === '\r' || data === '\n') {
        typedCount.current = 0;
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
