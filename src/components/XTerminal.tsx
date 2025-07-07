import React, { useEffect, useRef, useState, useCallback } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import { Button } from "./ui/button";
import { Trash2, Square, RotateCcw } from "lucide-react";

interface XTerminalProps {
  theme?: "light" | "dark";
  onClear?: () => void;
  className?: string;
}

const XTerminal: React.FC<XTerminalProps> = ({
  theme = "dark",
  onClear,
  className = "",
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

    // Get the WebSocket URL - handle production environment properly
    let wsUrl: string;
    const envWsUrl = import.meta.env.VITE_WS_URL;
    
    if (envWsUrl && envWsUrl.trim() !== '') {
      // Use environment variable and append terminal endpoint
      wsUrl = `${envWsUrl}/ws/terminal/${terminalId.current}`;
    } else {
      // Dynamic URL construction for production
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host; // includes port if present
      wsUrl = `${protocol}//${host}/ws/terminal/${terminalId.current}`;
    }

    console.log("Connecting to WebSocket:", wsUrl);

    websocket.current = new WebSocket(wsUrl);

    websocket.current.onopen = () => {
      setIsConnected(true);
      setIsReconnecting(false);
      console.log("Terminal WebSocket connected successfully");
      if (terminal.current) {
        // Clear any previous connection messages
        terminal.current.clear();
      }
    };

    websocket.current.onmessage = (event) => {
      if (terminal.current) {
        // Write data immediately without any processing delay
        terminal.current.write(event.data);
      }
    };

    websocket.current.onclose = (event) => {
      setIsConnected(false);
      setIsReconnecting(false);
      console.log("Terminal WebSocket closed:", event.code, event.reason);
      if (terminal.current && event.code !== 1000) {
        // Only show disconnection message if it wasn't a normal close
        terminal.current.write(
          "\r\n\x1b[31mTerminal disconnected\x1b[0m\r\n",
        );
      }
    };

    websocket.current.onerror = (error) => {
      console.error("WebSocket error:", error);
      setIsConnected(false);
      setIsReconnecting(false);
      if (terminal.current) {
        terminal.current.write(
          "\r\n\x1b[31mTerminal connection error\x1b[0m\r\n",
        );
      }
    };
  }, []);

  const initializeTerminal = useCallback(() => {
    if (!terminalRef.current || terminal.current) return;

    try {
      // Create terminal instance
      terminal.current = new Terminal({
        theme:
          theme === "dark"
            ? {
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
              }
            : {
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
        scrollback: 1000,
        tabStopWidth: 4,
      });

      // Create fit addon
      fitAddon.current = new FitAddon();
      terminal.current.loadAddon(fitAddon.current);

      // Open terminal
      terminal.current.open(terminalRef.current);

      // Wait for terminal to be fully rendered before fitting
      setTimeout(() => {
        if (terminal.current && fitAddon.current && terminalRef.current) {
          try {
            // Check if container has dimensions
            const rect = terminalRef.current.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
              fitAddon.current.fit();
              console.log("Terminal fitted successfully");
            } else {
              console.warn("Terminal container has no dimensions, retrying...");
              // Retry after a longer delay
              setTimeout(() => {
                try {
                  if (fitAddon.current && terminal.current) {
                    fitAddon.current.fit();
                  }
                } catch (retryError) {
                  console.warn("Retry fit failed:", retryError);
                }
              }, 500);
            }
          } catch (error) {
            console.warn("Error fitting terminal:", error);
          }
        }
      }, 100);

      // Handle data from terminal (user input)
      terminal.current.onData((data) => {
        if (websocket.current?.readyState === WebSocket.OPEN) {
          // Send data immediately without any buffering
          websocket.current.send(data);
        }
      });

      // Handle terminal resize
      terminal.current.onResize((size) => {
        if (websocket.current?.readyState === WebSocket.OPEN) {
          websocket.current.send(
            JSON.stringify({
              type: "resize",
              cols: size.cols,
              rows: size.rows,
            }),
          );
        }
      });

      // Connect to WebSocket
      connectWebSocket();

      // Show welcome message after a short delay
      setTimeout(() => {
        if (terminal.current) {
          terminal.current.write(
            "\x1b[32mConnecting to terminal...\x1b[0m\r\n",
          );
          terminal.current.write(
            `\x1b[36mTerminal ID: ${terminalId.current}\x1b[0m\r\n`,
          );
        }
      }, 100);
    } catch (error) {
      console.error("Error initializing terminal:", error);
    }
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
      if (fitAddon.current && terminal.current && terminalRef.current) {
        // Small delay to ensure container has updated size
        setTimeout(() => {
          try {
            // Check if container has valid dimensions before fitting
            const rect = terminalRef.current?.getBoundingClientRect();
            if (rect && rect.width > 0 && rect.height > 0) {
              fitAddon.current?.fit();
            } else {
              console.warn(
                "Cannot fit terminal: container has invalid dimensions",
              );
            }
          } catch (error) {
            console.warn("Error fitting terminal on resize:", error);
          }
        }, 50);
      }
    };

    window.addEventListener("resize", handleResize);

    // Also fit when container might change size
    const resizeObserver = new ResizeObserver((entries) => {
      try {
        // Check if the observed element has valid dimensions
        const entry = entries[0];
        if (
          entry &&
          entry.contentRect.width > 0 &&
          entry.contentRect.height > 0
        ) {
          handleResize();
        }
      } catch (error) {
        console.warn("Error in resize observer:", error);
      }
    });

    if (terminalRef.current) {
      resizeObserver.observe(terminalRef.current);
    }

    return () => {
      window.removeEventListener("resize", handleResize);
      resizeObserver.disconnect();
    };
  }, []);

  // Force fit when component is fully mounted
  useEffect(() => {
    const timer = setTimeout(() => {
      if (fitAddon.current && terminal.current && terminalRef.current) {
        try {
          // Ensure container is visible and has dimensions
          const rect = terminalRef.current.getBoundingClientRect();
          if (rect.width > 0 && rect.height > 0) {
            fitAddon.current.fit();
            console.log("Terminal fitted on mount");
          } else {
            console.warn("Terminal container not ready for fitting on mount");
            // Try again after a longer delay
            setTimeout(() => {
              try {
                if (
                  fitAddon.current &&
                  terminal.current &&
                  terminalRef.current
                ) {
                  const retryRect = terminalRef.current.getBoundingClientRect();
                  if (retryRect.width > 0 && retryRect.height > 0) {
                    fitAddon.current.fit();
                    console.log("Terminal fitted on retry");
                  }
                }
              } catch (retryError) {
                console.warn("Error fitting terminal on retry:", retryError);
              }
            }, 500);
          }
        } catch (error) {
          console.warn("Error fitting terminal on mount:", error);
        }
      }
    }, 200);

    return () => clearTimeout(timer);
  }, []);

  // Handle theme changes
  useEffect(() => {
    if (terminal.current) {
      terminal.current.options.theme =
        theme === "dark"
          ? {
              background: "#1a1a1a",
              foreground: "#ffffff",
              cursor: "#ffffff",
              black: "#000000",
              brightBlack: "#666666",
              red: "#ff6b6b",
              brightRed: "#ff8e8e",
              green: "#51cf66",
              brightGreen: "#69db7c",
              yellow: "#ffd43b",
              brightYellow: "#ffec99",
              blue: "#339af0",
              brightBlue: "#74c0fc",
              magenta: "#f06292",
              brightMagenta: "#f48fb1",
              cyan: "#22d3ee",
              brightCyan: "#67e8f9",
              white: "#f8f9fa",
              brightWhite: "#ffffff",
            }
          : {
              background: "#ffffff",
              foreground: "#000000",
              cursor: "#000000",
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
      websocket.current.send("\x03"); // Send Ctrl+C
    }
  };

  return (
    <div className={`flex flex-col h-full bg-background ${className}`}>
      <div className="flex items-center justify-between p-2 border-b border-border bg-muted/30 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Terminal</span>
          <div
            className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : isReconnecting ? "bg-yellow-500" : "bg-red-500"}`}
          />
          <span className="text-xs text-muted-foreground">
            {isConnected
              ? "Connected"
              : isReconnecting
                ? "Connecting..."
                : "Disconnected"}
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
        <div ref={terminalRef} className="w-full h-full" />
      </div>
    </div>
  );
};

export default XTerminal;
