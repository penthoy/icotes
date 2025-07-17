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
import { getWebSocketService } from '../../../src/services';
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
    const [currentTerminalId, setCurrentTerminalId] = useState<string | undefined>(terminalId);
    const [terminalSession, setTerminalSession] = useState<TerminalSession | null>(null);
    const [isTerminalReady, setIsTerminalReady] = useState(false);
    const [isDarkTheme, setIsDarkTheme] = useState(false);
    
    // Backend hooks
    const { actions, terminals } = useBackendState();
    const { isConnected } = useBackendContext();
    const wsService = useRef(getWebSocketService());
    
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
          if (currentTerminalId) {
            // Send input to backend terminal
            actions.sendTerminalInput(currentTerminalId, data).catch(error => {
              console.error('Failed to send terminal input:', error);
            });
          }
        });
        
        terminalInstance.onResize(({ rows, cols }) => {
          if (currentTerminalId) {
            // Resize backend terminal
            wsService.current.send({
              type: 'terminal.resize',
              payload: {
                terminalId: currentTerminalId,
                data: { rows, cols }
              }
            });
          }
        });
        
        setIsTerminalReady(true);
        onTerminalReady?.(terminalInstance);
        
      } catch (error) {
        console.error('Failed to initialize terminal:', error);
      }
    }, [isDarkTheme, isConnected, currentTerminalId, actions, onTerminalReady]);
    
    /**
     * Create or connect to terminal session
     */
    const setupTerminalSession = useCallback(async () => {
      if (!isConnected) return;
      
      try {
        let session: TerminalSession;
        
        if (currentTerminalId) {
          // Find existing session
          const existingSession = terminals.find(t => t.id === currentTerminalId);
          if (existingSession) {
            session = existingSession;
          } else {
            // Create new session with specific ID (if backend supports it)
            session = await actions.createTerminal(`Terminal ${currentTerminalId}`);
          }
        } else {
          // Create new session
          session = await actions.createTerminal('Backend Terminal');
          setCurrentTerminalId(session.id);
        }
        
        setTerminalSession(session);
        
        // Subscribe to terminal output via WebSocket
        wsService.current.on('terminal.output', (data: any) => {
          if (data.terminalId === session.id && terminal.current) {
            terminal.current.write(data.data);
            onTerminalOutput?.(data.data);
          }
        });
        
        // Subscribe to terminal exit events
        wsService.current.on('terminal.exit', (data: any) => {
          if (data.terminalId === session.id) {
            onTerminalExit?.(data.code || 0);
          }
        });
        
        // Subscribe to terminal events
        wsService.current.send({
          type: 'terminal.subscribe',
          payload: {
            terminalId: session.id
          }
        });
        
      } catch (error) {
        console.error('Failed to setup terminal session:', error);
      }
    }, [isConnected, currentTerminalId, terminals, actions, onTerminalOutput, onTerminalExit]);
    
    /**
     * Cleanup terminal
     */
    const cleanupTerminal = useCallback(() => {
      if (terminal.current) {
        terminal.current.dispose();
        terminal.current = null;
      }
      
      if (fitAddon.current) {
        fitAddon.current = null;
      }
      
      // Unsubscribe from WebSocket events
      if (currentTerminalId) {
        wsService.current.send({
          type: 'terminal.unsubscribe',
          terminalId: currentTerminalId
        });
      }
      
      setIsTerminalReady(false);
    }, [currentTerminalId]);
    
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
    
    // Initialize xterm.js terminal
    useEffect(() => {
      if (isConnected && terminalSession) {
        initializeTerminal();
      }
      
      return () => {
        cleanupTerminal();
      };
    }, [isConnected, terminalSession, initializeTerminal, cleanupTerminal]);
    
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
                  terminalSession.status === 'running' ? 'bg-green-500' : 
                  terminalSession.status === 'stopped' ? 'bg-yellow-500' : 
                  'bg-red-500'
                }`}></span>
                <span className="text-gray-600 dark:text-gray-400">
                  {terminalSession.status}
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
      </div>
    );
  }
);

BackendConnectedTerminal.displayName = 'BackendConnectedTerminal';

export default BackendConnectedTerminal;
