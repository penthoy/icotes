import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { Button } from './ui/button';
import { Trash2, Square, RotateCcw } from 'lucide-react';

interface XTerminalProps {
  theme?: 'light' | 'dark';
  onClear?: () => void;
  className?: string;
}

const XTerminal: React.FC<XTerminalProps> = ({
  theme = 'dark',
  onClear,
  className = '',
}) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const terminal = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const websocket = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const terminalId = useRef<string>(Math.random().toString(36).substring(7));

  const connectWebSocket = useCallback(() => {
    if (websocket.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setIsReconnecting(true);
    
    // Get the WebSocket URL - adapt for remote environment
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let wsUrl: string;
    
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      // Local development
      wsUrl = `${protocol}//localhost:8000/ws/terminal/${terminalId.current}`;
    } else {
      // Remote environment - construct the WebSocket URL properly
      const host = window.location.hostname;
      const port = 8000;
      wsUrl = `${protocol}//${host}:${port}/ws/terminal/${terminalId.current}`;
    }
    
    websocket.current = new WebSocket(wsUrl);

    websocket.current.onopen = () => {
      setIsConnected(true);
      setIsReconnecting(false);
      if (terminal.current) {
        terminal.current.write('\\r\\n\\x1b[32mTerminal connected\\x1b[0m\\r\\n');
      }
    };

    websocket.current.onmessage = (event) => {
      if (terminal.current) {
        terminal.current.write(event.data);
      }
    };

    websocket.current.onclose = (event) => {
      setIsConnected(false);
      setIsReconnecting(false);
      if (terminal.current) {
        terminal.current.write('\\r\\n\\x1b[31mTerminal disconnected\\x1b[0m\\r\\n');
      }
    };

    websocket.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
      setIsReconnecting(false);
      if (terminal.current) {
        terminal.current.write('\\r\\n\\x1b[31mTerminal connection error\\x1b[0m\\r\\n');
      }
    };
  }, []);

  const initializeTerminal = useCallback(() => {
    if (!terminalRef.current || terminal.current) return;

    // Create terminal instance
    terminal.current = new Terminal({
      theme: theme === 'dark' ? {
        background: '#1a1a1a',
        foreground: '#ffffff',
        cursor: '#ffffff',
        black: '#000000',
        brightBlack: '#666666',
        red: '#ff6b6b',
        brightRed: '#ff8e8e',
        green: '#51cf66',
        brightGreen: '#69db7c',
        yellow: '#ffd43b',
        brightYellow: '#ffec99',
        blue: '#339af0',
        brightBlue: '#74c0fc',
        magenta: '#f06292',
        brightMagenta: '#f48fb1',
        cyan: '#22d3ee',
        brightCyan: '#67e8f9',
        white: '#f8f9fa',
        brightWhite: '#ffffff',
      } : {
        background: '#ffffff',
        foreground: '#000000',
        cursor: '#000000',
      },
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      fontSize: 14,
      cursorBlink: true,
      cursorStyle: 'block',
      allowTransparency: true,
    });

    // Create fit addon
    fitAddon.current = new FitAddon();
    terminal.current.loadAddon(fitAddon.current);

    // Open terminal
    terminal.current.open(terminalRef.current);
    
    // Fit terminal to container
    fitAddon.current?.fit();

    // Handle data from terminal (user input)
    terminal.current.onData((data) => {
      if (websocket.current?.readyState === WebSocket.OPEN) {
        websocket.current.send(data);
      }
    });

    // Handle terminal resize
    terminal.current.onResize((size) => {
      if (websocket.current?.readyState === WebSocket.OPEN) {
        websocket.current.send(JSON.stringify({
          type: 'resize',
          cols: size.cols,
          rows: size.rows
        }));
      }
    });

    // Connect to WebSocket
    connectWebSocket();

    // Show welcome message
    terminal.current.write('\\x1b[32mConnecting to terminal...\\x1b[0m\\r\\n');
    terminal.current.write(`\\x1b[36mTerminal ID: ${terminalId.current}\\x1b[0m\\r\\n`);
  }, [theme, connectWebSocket]);

  useEffect(() => {
    initializeTerminal();

    // Cleanup function
    return () => {
      if (websocket.current) {
        websocket.current.close();
      }
      if (terminal.current) {
        terminal.current.dispose();
        terminal.current = null;
      }
    };
  }, [initializeTerminal]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (fitAddon.current && terminal.current) {
        // Small delay to ensure container has updated size
        setTimeout(() => {
          fitAddon.current?.fit();
        }, 10);
      }
    };

    window.addEventListener('resize', handleResize);
    
    // Also fit when container might change size
    const resizeObserver = new ResizeObserver(() => {
      handleResize();
    });
    
    if (terminalRef.current) {
      resizeObserver.observe(terminalRef.current);
    }

    return () => {
      window.removeEventListener('resize', handleResize);
      resizeObserver.disconnect();
    };
  }, []);

  // Force fit when component is fully mounted
  useEffect(() => {
    const timer = setTimeout(() => {
      if (fitAddon.current && terminal.current) {
        fitAddon.current.fit();
      }
    }, 100);
    
    return () => clearTimeout(timer);
  }, []);

  // Handle theme changes
  useEffect(() => {
    if (terminal.current) {
      terminal.current.options.theme = theme === 'dark' ? {
        background: '#1a1a1a',
        foreground: '#ffffff',
        cursor: '#ffffff',
        black: '#000000',
        brightBlack: '#666666',
        red: '#ff6b6b',
        brightRed: '#ff8e8e',
        green: '#51cf66',
        brightGreen: '#69db7c',
        yellow: '#ffd43b',
        brightYellow: '#ffec99',
        blue: '#339af0',
        brightBlue: '#74c0fc',
        magenta: '#f06292',
        brightMagenta: '#f48fb1',
        cyan: '#22d3ee',
        brightCyan: '#67e8f9',
        white: '#f8f9fa',
        brightWhite: '#ffffff',
      } : {
        background: '#ffffff',
        foreground: '#000000',
        cursor: '#000000',
      };
    }
  }, [theme]);

  const handleClear = () => {
    if (terminal.current) {
      terminal.current.clear();
    }
    onClear?.();
  };

  const handleReconnect = () => {
    if (websocket.current) {
      websocket.current.close();
    }
    connectWebSocket();
  };

  const handleKill = () => {
    if (websocket.current) {
      websocket.current.send('\\x03'); // Send Ctrl+C
    }
  };

  return (
    <div className={`flex flex-col h-full bg-background ${className}`}>
      <div className="flex items-center justify-between p-2 border-b border-border bg-muted/30 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Terminal</span>
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : isReconnecting ? 'bg-yellow-500' : 'bg-red-500'}`} />
          <span className="text-xs text-muted-foreground">
            {isConnected ? 'Connected' : isReconnecting ? 'Connecting...' : 'Disconnected'}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleKill}
            className="h-6 w-6 p-0"
            disabled={!isConnected}
            title="Kill current process (Ctrl+C)"
          >
            <Square className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleReconnect}
            className="h-6 w-6 p-0"
            disabled={isReconnecting}
            title="Reconnect terminal"
          >
            <RotateCcw className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClear}
            className="h-6 w-6 p-0"
            title="Clear terminal"
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      </div>
      
      <div className="flex-1 min-h-0 overflow-hidden">
        <div 
          ref={terminalRef} 
          className="w-full h-full"
        />
      </div>
    </div>
  );
};

export default XTerminal;
