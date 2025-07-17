/**
 * Backend-Connected Terminal Component
 * 
 * This component integrates the ICUIEnhancedTerminalPanel with the ICPY backend,
 * providing real-time terminal sessions through WebSocket communication.
 * 
 * Features:
 * - Real PTY sessions via backend terminal service
 * - Bidirectional terminal I/O through WebSocket
 * - Terminal lifecycle management (create, destroy, resize)
 * - Multiple terminal support
 * - Connection status monitoring
 * - Error handling and recovery
 */

import React, { useRef, useEffect, useState, useCallback, useImperativeHandle, forwardRef } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { useBackendState } from '../../../src/hooks/useBackendState';
import { useBackendContext } from '../../../src/contexts/BackendContext';
import { TerminalSession } from '../../../src/types/backend-types';
import '@xterm/xterm/css/xterm.css';

interface BackendConnectedTerminalProps {
  terminalId?: string;
  onTerminalReady?: (terminal: Terminal) => void;
  onTerminalOutput?: (output: string) => void;
  onTerminalExit?: (code: number) => void;
  className?: string;
}

export interface BackendConnectedTerminalRef {
  terminal: Terminal | null;
  fit: () => void;
  resize: (rows: number, cols: number) => void;
  clear: () => void;
  writeText: (text: string) => void;
  focus: () => void;
}

/**
 * Backend-Connected Terminal Component
 */
const BackendConnectedTerminal = forwardRef<BackendConnectedTerminalRef, BackendConnectedTerminalProps>(
  ({ terminalId, onTerminalReady, onTerminalOutput, onTerminalExit, className = '' }, ref) => {
    // Refs and state
    const terminalRef = useRef<HTMLDivElement>(null);
    const terminal = useRef<Terminal | null>(null);
    const fitAddon = useRef<FitAddon | null>(null);
    const websocket = useRef<WebSocket | null>(null);
    const [currentTerminalId, setCurrentTerminalId] = useState<string | undefined>(terminalId);
    const [terminalSession, setTerminalSession] = useState<TerminalSession | null>(null);
    const [isTerminalReady, setIsTerminalReady] = useState(false);
    const [isDarkTheme, setIsDarkTheme] = useState(false);
    const [isWebSocketConnected, setIsWebSocketConnected] = useState(false);
    
    // Backend hooks
    const { actions, terminals } = useBackendState();
    const { isConnected } = useBackendContext();
    
    // Function to get terminals from backend
    const getTerminalsFromBackend = useCallback(async () => {
      try {
        const response = await fetch('http://192.168.2.195:8000/api/terminals');
        const data = await response.json();
        return data.success ? data.data : [];
      } catch (error) {
        console.error('Failed to fetch terminals from backend:', error);
        return [];
      }
    }, []);
    
    // Debug logging
    console.log('[BackendConnectedTerminal] State update:', {
      terminalId,
      currentTerminalId,
      isConnected,
      terminalsLength: terminals.length,
      terminalsIds: terminals.map(t => t.id),
      terminalSession: terminalSession?.id,
      isTerminalReady,
      isWebSocketConnected
    });
    
    // Theme detection
    useEffect(() => {
      const detectTheme = () => {
        const htmlElement = document.documentElement;
        const isDark = htmlElement.classList.contains('dark') || 
                       htmlElement.classList.contains('icui-theme-github-dark') ||
                       htmlElement.classList.contains('icui-theme-monokai');
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
    
    /**
     * Initialize terminal
     */
    const initializeTerminal = useCallback(async () => {
      if (!terminalRef.current || !isConnected) return;
      
      try {
        console.log('[BackendConnectedTerminal] Initializing terminal...');
        
        // Create terminal instance
        const terminalInstance = new Terminal({
          theme: isDarkTheme ? {
            background: '#1a1a1a',
            foreground: '#ffffff',
            cursor: '#ffffff',
            selectionBackground: '#4a4a4a',
          } : {
            background: '#ffffff',
            foreground: '#000000',
            cursor: '#000000',
            selectionBackground: '#c8c8c8',
          },
          fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
          fontSize: 14,
          lineHeight: 1.2,
          cursorBlink: true,
          scrollback: 1000,
          allowTransparency: false,
        });
        
        // Create fit addon
        const fitAddonInstance = new FitAddon();
        terminalInstance.loadAddon(fitAddonInstance);
        
        // Open terminal
        terminalInstance.open(terminalRef.current);
        
        // Store references
        terminal.current = terminalInstance;
        fitAddon.current = fitAddonInstance;
        
        // Fit terminal to container
        setTimeout(() => {
          fitAddonInstance.fit();
        }, 100);
        
        // Set up terminal event handlers
        terminalInstance.onData((data) => {
          if (websocket.current?.readyState === WebSocket.OPEN) {
            console.log('[BackendConnectedTerminal] Sending input to terminal:', data);
            websocket.current.send(data);
          }
        });
        
        terminalInstance.onResize(({ rows, cols }) => {
          if (websocket.current?.readyState === WebSocket.OPEN) {
            console.log('[BackendConnectedTerminal] Resizing terminal:', { rows, cols });
            websocket.current.send(JSON.stringify({
              type: 'resize',
              cols,
              rows
            }));
          }
        });
        
        setIsTerminalReady(true);
        onTerminalReady?.(terminalInstance);
        
        console.log('[BackendConnectedTerminal] Terminal initialized successfully');
        
      } catch (error) {
        console.error('[BackendConnectedTerminal] Failed to initialize terminal:', error);
      }
    }, [isDarkTheme, isConnected, onTerminalReady]);
    
    /**
     * Connect to terminal WebSocket
     */
    const connectTerminalWebSocket = useCallback(async () => {
      if (!currentTerminalId || !isConnected) return;
      
      try {
        console.log('[BackendConnectedTerminal] Connecting to terminal WebSocket:', currentTerminalId);
        
        // Close existing connection
        if (websocket.current) {
          websocket.current.close();
        }
        
        // Small delay to prevent rapid reconnection
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Create WebSocket connection to terminal endpoint
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const backendHost = '192.168.2.195:8000';  // Backend server host
        const wsUrl = `${protocol}//${backendHost}/ws/terminal/${currentTerminalId}`;
        
        console.log('[BackendConnectedTerminal] Connecting to WebSocket URL:', wsUrl);
        
        websocket.current = new WebSocket(wsUrl);
        
        websocket.current.onopen = () => {
          console.log('[BackendConnectedTerminal] Terminal WebSocket connected');
          setIsWebSocketConnected(true);
          
          // Clear terminal on connect
          if (terminal.current) {
            terminal.current.clear();
          }
        };
        
        websocket.current.onmessage = (event) => {
          if (terminal.current) {
            console.log('[BackendConnectedTerminal] Received terminal output:', event.data);
            terminal.current.write(event.data);
            onTerminalOutput?.(event.data);
          }
        };
        
        websocket.current.onclose = (event) => {
          console.log('[BackendConnectedTerminal] Terminal WebSocket closed:', event.code, event.reason);
          setIsWebSocketConnected(false);
          
          if (terminal.current && event.code !== 1000) {
            terminal.current.write("\r\n\x1b[31mTerminal disconnected\x1b[0m\r\n");
          }
        };
        
        websocket.current.onerror = (error) => {
          console.error('[BackendConnectedTerminal] Terminal WebSocket error:', error);
          setIsWebSocketConnected(false);
          
          if (terminal.current) {
            terminal.current.write("\r\n\x1b[31mTerminal connection error\x1b[0m\r\n");
          }
        };
        
      } catch (error) {
        console.error('[BackendConnectedTerminal] Failed to connect terminal WebSocket:', error);
      }
    }, [currentTerminalId, isConnected, onTerminalOutput]);
    
    /**
     * Connect to existing terminal session - DO NOT CREATE NEW TERMINALS
     */
    const setupTerminalSession = useCallback(async () => {
      if (!isConnected || !currentTerminalId) return;
      
      try {
        console.log('[BackendConnectedTerminal] Setting up terminal session for ID:', currentTerminalId);
        
        // Find existing session - DO NOT CREATE NEW ONES
        const existingSession = terminals.find(t => t.id === currentTerminalId);
        if (existingSession) {
          console.log('[BackendConnectedTerminal] Using existing terminal session:', existingSession.id);
          setTerminalSession(existingSession);
          
          // Connect to terminal WebSocket
          await connectTerminalWebSocket();
        } else {
          console.error('[BackendConnectedTerminal] Terminal session not found:', currentTerminalId);
          console.log('[BackendConnectedTerminal] Available terminals:', terminals.map(t => t.id));
          
          // Fallback: Try to fetch the terminal from backend directly
          try {
            const backendTerminals = await getTerminalsFromBackend();
            const backendTerminal = backendTerminals.find(t => t.id === currentTerminalId);
            
            if (backendTerminal) {
              console.log('[BackendConnectedTerminal] Found terminal on backend:', backendTerminal);
              setTerminalSession(backendTerminal);
              
              // Connect to terminal WebSocket
              await connectTerminalWebSocket();
            } else {
              console.error('[BackendConnectedTerminal] Terminal not found on backend either:', currentTerminalId);
            }
          } catch (error) {
            console.error('[BackendConnectedTerminal] Failed to fetch terminal from backend:', error);
            
            // Last resort: Try to connect to WebSocket anyway if we have a terminal ID
            if (currentTerminalId) {
              console.log('[BackendConnectedTerminal] Attempting direct WebSocket connection as last resort');
              setTerminalSession({ 
                id: currentTerminalId, 
                name: 'Terminal', 
                status: 'running' 
              } as TerminalSession);
              await connectTerminalWebSocket();
            }
          }
        }
        
      } catch (error) {
        console.error('[BackendConnectedTerminal] Failed to setup terminal session:', error);
      }
    }, [isConnected, currentTerminalId, terminals, connectTerminalWebSocket, getTerminalsFromBackend]);
    
    /**
     * Cleanup terminal
     */
    const cleanupTerminal = useCallback(() => {
      console.log('[BackendConnectedTerminal] Cleaning up terminal...');
      
      if (websocket.current) {
        websocket.current.close();
        websocket.current = null;
      }
      
      if (terminal.current) {
        terminal.current.dispose();
        terminal.current = null;
      }
      
      if (fitAddon.current) {
        fitAddon.current = null;
      }
      
      setIsTerminalReady(false);
      setIsWebSocketConnected(false);
    }, []);
    
    /**
     * Imperative handle for ref
     */
    useImperativeHandle(ref, () => ({
      terminal: terminal.current,
      fit: () => {
        if (fitAddon.current) {
          fitAddon.current.fit();
        }
      },
      resize: (rows: number, cols: number) => {
        if (terminal.current) {
          terminal.current.resize(cols, rows);
        }
      },
      clear: () => {
        if (terminal.current) {
          terminal.current.clear();
        }
      },
      writeText: (text: string) => {
        if (terminal.current) {
          terminal.current.write(text);
        }
      },
      focus: () => {
        if (terminal.current) {
          terminal.current.focus();
        }
      }
    }), []);
    
    // Initialize terminal when component mounts or connection changes
    useEffect(() => {
      if (isConnected) {
        setupTerminalSession();
      }
      
      return () => {
        cleanupTerminal();
      };
    }, [isConnected, setupTerminalSession, cleanupTerminal]);
    
    // Initialize xterm.js terminal (separate effect, no cleanup to avoid double cleanup)
    useEffect(() => {
      if (isConnected && terminalSession) {
        initializeTerminal();
      }
    }, [isConnected, terminalSession, initializeTerminal]);
    
    // Handle terminal ID changes
    useEffect(() => {
      if (terminalId !== currentTerminalId) {
        setCurrentTerminalId(terminalId);
      }
    }, [terminalId, currentTerminalId]);
    
    // Handle window resize
    useEffect(() => {
      const handleResize = () => {
        if (fitAddon.current) {
          setTimeout(() => {
            fitAddon.current?.fit();
          }, 100);
        }
      };
      
      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
    }, []);
    
    return (
      <div className={`backend-connected-terminal ${className}`}>
        {/* Connection Status */}
        {!isConnected && (
          <div className="flex items-center justify-center h-full bg-gray-100 dark:bg-gray-800">
            <div className="text-center">
              <div className="text-red-500 mb-2">Backend Disconnected</div>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                Terminal requires backend connection
              </div>
            </div>
          </div>
        )}
        
        {/* Terminal Session Info */}
        {isConnected && terminalSession && (
          <div className="backend-terminal-info px-2 py-1 bg-gray-100 dark:bg-gray-800 border-b text-xs">
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">
                Terminal: {terminalSession.name} (ID: {terminalSession.id})
              </span>
              <div className="flex items-center space-x-2">
                <span className={`w-2 h-2 rounded-full ${
                  isWebSocketConnected ? 'bg-green-500' : 'bg-red-500'
                }`}></span>
                <span className="text-gray-600 dark:text-gray-400">
                  {isWebSocketConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>
          </div>
        )}
        
        {/* Terminal Container */}
        <div className="terminal-container flex-1 relative">
          {!isTerminalReady && isConnected && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-50 dark:bg-gray-900">
              <div className="text-center">
                <div className="text-blue-500 mb-2">Initializing Terminal...</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  Setting up backend connection
                </div>
              </div>
            </div>
          )}
          
          <div 
            ref={terminalRef}
            className="terminal-element w-full h-full"
            style={{ 
              height: '100%',
              display: isTerminalReady ? 'block' : 'none'
            }}
          />
        </div>
        
        {/* Test Toolbar */}
        <div className="terminal-test-toolbar p-1 bg-gray-200 dark:bg-gray-700 border-t flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2">
            <button 
              className="px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
              onClick={() => {
                if (terminal.current) {
                  terminal.current.clear();
                }
              }}
            >
              Clear Terminal
            </button>
            <button 
              className="px-2 py-1 bg-green-500 text-white rounded hover:bg-green-600"
              onClick={() => {
                if (terminal.current) {
                  terminal.current.write('\r\necho "Terminal test successful at $(date)"\r\n');
                }
              }}
            >
              Test Echo Command
            </button>
            <button 
              className="px-2 py-1 bg-purple-500 text-white rounded hover:bg-purple-600"
              onClick={() => {
                if (websocket.current?.readyState === WebSocket.OPEN) {
                  websocket.current.send('ls -la\r\n');
                }
              }}
            >
              Send LS Command
            </button>
          </div>
          <div className="text-gray-500 dark:text-gray-400">
            Test URL: http://192.168.2.195:8000/integration
          </div>
        </div>
      </div>
    );
  }
);

BackendConnectedTerminal.displayName = 'BackendConnectedTerminal';

export default BackendConnectedTerminal;
