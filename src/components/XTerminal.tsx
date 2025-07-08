import React, { useEffect, useRef, useState, useCallback, forwardRef, useImperativeHandle } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import { Button } from "./ui/button";
import { Trash2, Square, RotateCcw } from "lucide-react";

interface XTerminalProps {
  theme?: "light" | "dark";
  onClear?: () => void;
  className?: string;
  onResize?: (height: number) => void;
}

export interface XTerminalRef {
  fit: () => void;
}

const XTerminal: React.ForwardRefRenderFunction<XTerminalRef, XTerminalProps> = ({
  theme = "dark",
  onClear,
  className = "",
  onResize,
}, ref) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const terminal = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const websocket = useRef<WebSocket | null>(null);
  const resizeTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const terminalId = useRef<string>(Math.random().toString(36).substring(7));

  const connectWebSocket = useCallback(() => {
    if (websocket.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setIsReconnecting(true);

    let wsUrl: string;
    const envWsUrl = import.meta.env.VITE_WS_URL;
    
    if (envWsUrl && envWsUrl.trim() !== '') {
      wsUrl = `${envWsUrl}/ws/terminal/${terminalId.current}`;
    } else {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host;
      wsUrl = `${protocol}//${host}/ws/terminal/${terminalId.current}`;
    }

    websocket.current = new WebSocket(wsUrl);

    websocket.current.onopen = () => {
      setIsConnected(true);
      setIsReconnecting(false);
      // Terminal WebSocket connected successfully
      if (terminal.current) {
        terminal.current.clear();
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
      console.log("Terminal WebSocket closed:", event.code, event.reason);
      if (terminal.current && event.code !== 1000) {
        terminal.current.write("\r\n\x1b[31mTerminal disconnected\x1b[0m\r\n");
      }
    };

    websocket.current.onerror = (error) => {
      console.error("WebSocket error:", error);
      setIsConnected(false);
      setIsReconnecting(false);
      if (terminal.current) {
        terminal.current.write("\r\n\x1b[31mTerminal connection error\x1b[0m\r\n");
      }
    };
  }, []);

  // Improved fit function that respects xterm.js natural scrolling
  const fitWithBoundaryConstraints = useCallback(() => {
    if (!terminal.current || !fitAddon.current || !terminalRef.current) return;
    
    const container = terminalRef.current;
    const rect = container.getBoundingClientRect();
    
    // Only fit if container has valid dimensions
    if (rect.width > 20 && rect.height > 20) {
      try {
        // Use the FitAddon's built-in fit method which handles scrolling properly
        fitAddon.current.fit();
        
        console.log("Terminal fitted successfully:", {
          width: rect.width,
          height: rect.height,
          cols: terminal.current.cols,
          rows: terminal.current.rows
        });
      } catch (error) {
        console.warn("Error fitting terminal:", error);
      }
    } else {
      console.warn("Terminal container too small for fitting:", {
        width: rect.width,
        height: rect.height
      });
    }
  }, []);

  const initializeTerminal = useCallback(() => {
    if (!terminalRef.current || terminal.current) return;

    try {
      terminal.current = new Terminal({
        theme: theme === "dark" ? {
          background: "#1e1e1e",
          foreground: "#cccccc",
          cursor: "#cccccc",
          cursorAccent: "#1e1e1e",
          selectionBackground: "#264f78",
          black: "#000000",
          brightBlack: "#666666",
          red: "#cd3131",
          brightRed: "#f14c4c",
          green: "#0dbc79",
          brightGreen: "#23d18b",
          yellow: "#e5e510",
          brightYellow: "#f5f543",
          blue: "#2472c8",
          brightBlue: "#3b8eea",
          magenta: "#bc3fbc",
          brightMagenta: "#d670d6",
          cyan: "#11a8cd",
          brightCyan: "#29b8db",
          white: "#e5e5e5",
          brightWhite: "#ffffff",
        } : {
          background: "#ffffff",
          foreground: "#000000",
          cursor: "#000000",
          cursorAccent: "#ffffff",
          selectionBackground: "#0078d4",
          black: "#000000",
          brightBlack: "#666666",
          red: "#cd3131",
          brightRed: "#f14c4c",
          green: "#00bc00",
          brightGreen: "#23d18b",
          yellow: "#949800",
          brightYellow: "#f5f543",
          blue: "#0451a5",
          brightBlue: "#3b8eea",
          magenta: "#bc05bc",
          brightMagenta: "#d670d6",
          cyan: "#0598bc",
          brightCyan: "#29b8db",
          white: "#e5e5e5",
          brightWhite: "#ffffff",
        },
        fontFamily: '"Cascadia Code", "Fira Code", "SF Mono", Monaco, Menlo, "Courier New", monospace',
        fontSize: 13,
        fontWeight: "normal",
        lineHeight: 1.2,
        cursorBlink: true,
        cursorStyle: "block",
        cursorWidth: 1,
        allowTransparency: false,
        convertEol: true,
        fastScrollModifier: "alt",
        fastScrollSensitivity: 5,
        scrollback: 2000, // Increased scrollback for better history
        tabStopWidth: 4,
        scrollOnUserInput: true,
        altClickMovesCursor: true,
        rightClickSelectsWord: true,
        macOptionIsMeta: true,
        windowOptions: {},
      });

      fitAddon.current = new FitAddon();
      terminal.current.loadAddon(fitAddon.current);
      terminal.current.open(terminalRef.current);

      // Multiple fit attempts to ensure proper sizing
      setTimeout(() => {
        fitWithBoundaryConstraints();
      }, 100);
      
      setTimeout(() => {
        fitWithBoundaryConstraints();
      }, 300);
      
      setTimeout(() => {
        fitWithBoundaryConstraints();
      }, 500);

      terminal.current.onData((data) => {
        if (websocket.current?.readyState === WebSocket.OPEN) {
          websocket.current.send(data);
        }
      });

      terminal.current.onResize((size) => {
        if (websocket.current?.readyState === WebSocket.OPEN) {
          websocket.current.send(JSON.stringify({
            type: "resize",
            cols: size.cols,
            rows: size.rows,
          }));
        }
      });

      console.log("Terminal initialized successfully");
    } catch (error) {
      console.error("Failed to initialize terminal:", error);
    }
  }, [theme, fitWithBoundaryConstraints]);

  useImperativeHandle(ref, () => ({
    fit: () => {
      fitWithBoundaryConstraints();
    }
  }));

  const debouncedFit = useCallback(() => {
    if (resizeTimeoutRef.current) {
      clearTimeout(resizeTimeoutRef.current);
    }
    resizeTimeoutRef.current = setTimeout(() => {
      fitWithBoundaryConstraints();
    }, 200);
  }, [fitWithBoundaryConstraints]);

  // Initialize terminal and WebSocket connection
  useEffect(() => {
    initializeTerminal();
    connectWebSocket();

    return () => {
      if (websocket.current) {
        websocket.current.close();
      }
      if (terminal.current) {
        terminal.current.dispose();
        terminal.current = null;
      }
    };
  }, [initializeTerminal, connectWebSocket]);

  // Handle resize events
  useEffect(() => {
    const handleResize = () => {
      debouncedFit();
    };

    window.addEventListener("resize", handleResize);

    let resizeObserver: ResizeObserver | null = null;
    
    if (terminalRef.current) {
      resizeObserver = new ResizeObserver(() => {
        debouncedFit();
      });
      resizeObserver.observe(terminalRef.current);
    }

    return () => {
      window.removeEventListener("resize", handleResize);
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
      if (resizeTimeoutRef.current) {
        clearTimeout(resizeTimeoutRef.current);
      }
    };
  }, [debouncedFit]);

  return (
    <div className={`flex flex-col h-full ${className}`} 
         style={{ 
           backgroundColor: theme === "dark" ? "#1e1e1e" : "#ffffff"
         }}>
      <div className="flex items-center justify-between p-2 bg-muted/30 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            <div
              className={`w-2 h-2 rounded-full ${
                isConnected ? "bg-green-500" : "bg-red-500"
              }`}
              title={isConnected ? "Connected" : "Disconnected"}
            />
            <span className="text-xs text-muted-foreground">
              {isReconnecting ? "Reconnecting..." : isConnected ? "Connected" : "Disconnected"}
            </span>
          </div>
        </div>
        
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              if (terminal.current) {
                terminal.current.clear();
              }
              onClear?.();
            }}
            className="p-1 h-7"
            title="Clear terminal"
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-hidden" style={{ minHeight: '200px' }}>
        <div 
          ref={terminalRef} 
          className="w-full h-full"
          style={{ 
            minHeight: '150px',
            backgroundColor: theme === "dark" ? "#1e1e1e" : "#ffffff"
          }}
        />
      </div>
    </div>
  );
};

export default forwardRef(XTerminal);