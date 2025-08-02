/**
 * Enhanced Terminal Service Integration
 * 
 * Shows how to integrate the enhanced WebSocket service with the existing
 * terminal implementation while maintaining backward compatibility.
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { webSocketMigration } from '../services/websocket-migration';
import { ServiceType } from '../services/connection-manager';

export interface EnhancedTerminalProps {
  terminalId?: string;
  onTerminalReady?: (terminal: Terminal) => void;
  onTerminalOutput?: (output: string) => void;
  onTerminalExit?: (code: number) => void;
  useEnhancedService?: boolean; // Flag to enable/disable enhanced service
}

export interface EnhancedTerminalHandle {
  terminal: Terminal | null;
  sendInput: (input: string) => void;
  clear: () => void;
  focus: () => void;
  resize: () => void;
  getHealthInfo: () => any;
  runDiagnostics: () => Promise<any>;
  getRecommendations: () => string[];
}

export const EnhancedTerminal = React.forwardRef<EnhancedTerminalHandle, EnhancedTerminalProps>(({
  terminalId: propTerminalId,
  onTerminalReady,
  onTerminalOutput,
  onTerminalExit,
  useEnhancedService = false // Default to false for gradual rollout
}, ref) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const terminal = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const serviceRef = useRef<any>(null);
  const terminalId = useRef<string>(propTerminalId || Math.random().toString(36).substring(2));
  
  const [isConnected, setIsConnected] = useState(false);
  const [serviceType, setServiceType] = useState<'enhanced' | 'legacy'>('legacy');
  const [healthInfo, setHealthInfo] = useState<any>(null);

  // Initialize terminal
  useEffect(() => {
    if (!terminalRef.current) return;

    // Create terminal instance
    terminal.current = new Terminal({
      scrollback: 1000,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      cursorStyle: 'block',
      cursorBlink: true,
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4',
        cursor: '#d4d4d4',
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
        brightBlack: '#666666',
        brightRed: '#f14c4c',
        brightGreen: '#23d18b',
        brightYellow: '#f5f543',
        brightBlue: '#3b8eea',
        brightMagenta: '#d670d6',
        brightCyan: '#29b8db',
        brightWhite: '#ffffff',
      }
    });

    // Create fit addon
    fitAddon.current = new FitAddon();
    terminal.current.loadAddon(fitAddon.current);

    // Open terminal
    terminal.current.open(terminalRef.current);
    fitAddon.current.fit();

    // Focus terminal
    terminal.current.focus();

    onTerminalReady?.(terminal.current);

    return () => {
      if (terminal.current) {
        terminal.current.dispose();
      }
    };
  }, [onTerminalReady]);

  // Initialize service (enhanced or legacy)
  useEffect(() => {
    const initializeService = async () => {
      try {
        if (useEnhancedService) {
          // Try enhanced service first
          try {
            serviceRef.current = webSocketMigration.getService('terminal');
            
            // Test if enhanced service is actually being used
            const migrationStatus = webSocketMigration.getMigrationStatus();
            if (migrationStatus.servicesUsingEnhanced.includes('terminal')) {
              setServiceType('enhanced');
              console.log('✨ Using Enhanced WebSocket Service for terminal');
            } else {
              setServiceType('legacy');
              console.log('🔄 Falling back to Legacy service for terminal');
            }
          } catch (error) {
            console.warn('Enhanced service failed, falling back to legacy:', error);
            serviceRef.current = createLegacyTerminalService();
            setServiceType('legacy');
          }
        } else {
          // Use legacy service
          serviceRef.current = createLegacyTerminalService();
          setServiceType('legacy');
          console.log('📡 Using Legacy WebSocket service for terminal');
        }

        // Connect to service
        await connectToService();

      } catch (error) {
        console.error('Failed to initialize terminal service:', error);
        terminal.current?.write('\r\n\x1b[31mFailed to initialize terminal service\x1b[0m\r\n');
      }
    };

    initializeService();

    return () => {
      if (serviceRef.current && typeof serviceRef.current.disconnect === 'function') {
        serviceRef.current.disconnect();
      }
    };
  }, [useEnhancedService]);

  // Connect to service
  const connectToService = async () => {
    if (!serviceRef.current || !terminal.current) return;

    try {
      terminal.current.write('Connecting to terminal service...\r\n');

      // Setup event handlers
      serviceRef.current.onMessage?.((data: string) => {
        if (terminal.current) {
          terminal.current.write(data);
          onTerminalOutput?.(data);
        }
      });

      serviceRef.current.onStatus?.((status: any) => {
        setIsConnected(status.connected);
        if (status.connected) {
          terminal.current?.write('\r\n\x1b[32mConnected!\x1b[0m\r\n');
          terminal.current?.write(`Terminal ID: ${terminalId.current}\r\n`);
          terminal.current?.write('Ready for commands...\r\n');
        } else {
          terminal.current?.write('\r\n\x1b[31mDisconnected\x1b[0m\r\n');
        }
      });

      // Handle terminal input
      terminal.current.onData((data) => {
        if (serviceRef.current && isConnected) {
          serviceRef.current.sendInput?.(data);
        }
      });

      // Connect
      const connected = await serviceRef.current.connectWebSocket?.({
        terminalId: terminalId.current
      });

      if (!connected) {
        throw new Error('Failed to connect to terminal service');
      }

      // Update health info for enhanced service
      if (serviceType === 'enhanced' && serviceRef.current.getHealthInfo) {
        const updateHealthInfo = () => {
          const health = serviceRef.current.getHealthInfo();
          setHealthInfo(health);
        };

        updateHealthInfo();
        // Update health info every 10 seconds
        const healthInterval = setInterval(updateHealthInfo, 10000);
        return () => clearInterval(healthInterval);
      }

    } catch (error) {
      console.error('Terminal connection failed:', error);
      terminal.current?.write('\r\n\x1b[31mConnection failed\x1b[0m\r\n');
      setIsConnected(false);
    }
  };

  // Expose handle methods
  React.useImperativeHandle(ref, () => ({
    terminal: terminal.current,
    sendInput: (input: string) => {
      if (serviceRef.current && isConnected) {
        serviceRef.current.sendInput?.(input);
      }
    },
    clear: () => {
      terminal.current?.clear();
    },
    focus: () => {
      terminal.current?.focus();
    },
    resize: () => {
      if (fitAddon.current) {
        fitAddon.current.fit();
      }
    },
    getHealthInfo: () => {
      if (serviceType === 'enhanced' && serviceRef.current?.getHealthInfo) {
        return serviceRef.current.getHealthInfo();
      }
      return { serviceType, isConnected, terminalId: terminalId.current };
    },
    runDiagnostics: async () => {
      if (serviceType === 'enhanced' && serviceRef.current?.runDiagnostics) {
        return await serviceRef.current.runDiagnostics();
      }
      return { error: 'Diagnostics only available with enhanced service' };
    },
    getRecommendations: () => {
      if (serviceType === 'enhanced' && serviceRef.current?.getRecommendations) {
        return serviceRef.current.getRecommendations();
      }
      return ['Enable enhanced service for performance recommendations'];
    }
  }));

  // Create legacy terminal service
  const createLegacyTerminalService = () => {
    let websocket: WebSocket | null = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;

    return {
      async connectWebSocket(options: any = {}) {
        try {
          const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/terminal/${options.terminalId || terminalId.current}`;
          websocket = new WebSocket(wsUrl);

          return new Promise((resolve, reject) => {
            if (!websocket) {
              reject(new Error('WebSocket not initialized'));
              return;
            }

            websocket.onopen = () => {
              reconnectAttempts = 0;
              resolve(true);
            };

            websocket.onerror = (error) => {
              reject(error);
            };

            websocket.onclose = (event) => {
              if (event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
                // Attempt reconnection
                setTimeout(() => {
                  reconnectAttempts++;
                  this.connectWebSocket(options);
                }, 1000 * Math.pow(2, reconnectAttempts));
              }
            };
          });
        } catch (error) {
          return false;
        }
      },

      sendInput(input: string) {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
          websocket.send(input);
        }
      },

      onMessage(callback: Function) {
        if (websocket) {
          websocket.onmessage = (event) => callback(event.data);
        }
      },

      onStatus(callback: Function) {
        if (websocket) {
          websocket.onopen = () => callback({ connected: true });
          websocket.onclose = () => callback({ connected: false });
        }
      },

      disconnect() {
        if (websocket) {
          websocket.close();
          websocket = null;
        }
      }
    };
  };

  return (
    <div className="enhanced-terminal-container" style={{ width: '100%', height: '100%' }}>
      {/* Terminal */}
      <div 
        ref={terminalRef}
        style={{ width: '100%', height: 'calc(100% - 40px)' }}
      />
      
      {/* Status Bar */}
      <div className="terminal-status-bar" style={{
        height: '40px',
        backgroundColor: '#2d2d2d',
        borderTop: '1px solid #3e3e3e',
        display: 'flex',
        alignItems: 'center',
        padding: '0 12px',
        fontSize: '12px',
        color: '#cccccc',
        gap: '12px'
      }}>
        <span>
          {isConnected ? '🟢' : '🔴'} {isConnected ? 'Connected' : 'Disconnected'}
        </span>
        
        <span>
          {serviceType === 'enhanced' ? '✨ Enhanced' : '📡 Legacy'} Service
        </span>
        
        {serviceType === 'enhanced' && healthInfo && (
          <span>
            🏥 Health: {healthInfo.score?.overall || 'N/A'}%
          </span>
        )}
        
        <span style={{ marginLeft: 'auto' }}>
          Terminal: {terminalId.current}
        </span>
      </div>
    </div>
  );
});

// Example usage component
export const TerminalExample: React.FC = () => {
  const terminalRef = useRef<EnhancedTerminalHandle>(null);
  const [useEnhanced, setUseEnhanced] = useState(false);
  const [diagnostics, setDiagnostics] = useState<any>(null);

  const handleRunDiagnostics = async () => {
    if (terminalRef.current) {
      const result = await terminalRef.current.runDiagnostics();
      setDiagnostics(result);
    }
  };

  const handleGetRecommendations = () => {
    if (terminalRef.current) {
      const recommendations = terminalRef.current.getRecommendations();
      console.log('Recommendations:', recommendations);
    }
  };

  return (
    <div style={{ height: '600px', display: 'flex', flexDirection: 'column' }}>
      {/* Controls */}
      <div style={{ padding: '10px', backgroundColor: '#f5f5f5', borderBottom: '1px solid #ddd' }}>
        <label style={{ marginRight: '10px' }}>
          <input
            type="checkbox"
            checked={useEnhanced}
            onChange={(e) => setUseEnhanced(e.target.checked)}
          />
          Use Enhanced WebSocket Service
        </label>
        
        <button onClick={handleRunDiagnostics} style={{ marginRight: '10px' }}>
          Run Diagnostics
        </button>
        
        <button onClick={handleGetRecommendations}>
          Get Recommendations
        </button>
      </div>

      {/* Terminal */}
      <div style={{ flex: 1 }}>
        <EnhancedTerminal
          ref={terminalRef}
          useEnhancedService={useEnhanced}
          onTerminalReady={(terminal) => {
            console.log('Terminal ready:', terminal);
          }}
          onTerminalOutput={(output) => {
            // console.log('Terminal output:', output);
          }}
        />
      </div>

      {/* Diagnostics */}
      {diagnostics && (
        <div style={{ 
          padding: '10px', 
          backgroundColor: '#f9f9f9', 
          borderTop: '1px solid #ddd',
          maxHeight: '200px',
          overflow: 'auto'
        }}>
          <h4>Diagnostics Results:</h4>
          <pre>{JSON.stringify(diagnostics, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};
