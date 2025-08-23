/**
 * ICUI Terminal Test Component
 * 
 * WebSocket integration testing terminal with Enhanced WebSocket service.
 * Specialized component for testing Enhanced WebSocket service functionality.
 */

import React, { useEffect, useRef, useState, useCallback, forwardRef, useImperativeHandle } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { EnhancedWebSocketService, ConnectionOptions } from '../../services/websocket-service-impl';
import { WebSocketMigrationHelper } from '../../services/websocket-migration';
import { useWebSocketService } from '../../contexts/BackendContext';

// Enhanced clipboard functionality (same as original)
class EnhancedClipboard {
  async copy(text: string): Promise<void> {
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(text);
      } else {
        this.fallbackCopy(text);
      }
    } catch (error) {
      console.warn('Copy failed, trying fallback:', error);
      this.fallbackCopy(text);
    }
  }

  async paste(): Promise<string> {
    try {
      if (navigator.clipboard) {
        return await navigator.clipboard.readText();
      } else {
        return '';
      }
    } catch (error) {
      console.warn('Paste failed:', error);
      return '';
    }
  }

  private fallbackCopy(text: string): void {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      document.execCommand('copy');
    } catch (err) {
      console.error('Fallback copy failed:', err);
    }
    document.body.removeChild(textArea);
  }
}

interface ICUITerminalTestProps {
  className?: string;
  terminalId?: string;
  onTerminalReady?: (terminal: Terminal) => void;
  onTerminalOutput?: (data: string) => void;
  onTerminalExit?: (code: number) => void;
}

export interface ICUITerminalTestRef {
  getTerminal: () => Terminal | null;
  clear: () => void;
  focus: () => void;
  write: (data: string) => void;
  fit: () => void;
  getConnectionId: () => string | null;
  getHealthStatus: () => any;
}

const ICUITerminalTest = forwardRef<ICUITerminalTestRef, ICUITerminalTestProps>(({
  className = '',
  terminalId: propTerminalId,
  onTerminalReady,
  onTerminalOutput,
  onTerminalExit
}, ref) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const terminal = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const resizeObserver = useRef<ResizeObserver | null>(null);
  const resizeTimeout = useRef<NodeJS.Timeout | null>(null);
  
  // Enhanced WebSocket service
  const enhancedService = useRef<EnhancedWebSocketService | null>(null);
  const migrationHelper = useRef<WebSocketMigrationHelper | null>(null);
  const connectionId = useRef<string | null>(null);
  
  // Legacy service for migration support
  const legacyWebSocketService = useWebSocketService();
  
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [healthStatus, setHealthStatus] = useState<any>(null);
  
  const terminalId = useRef<string>(propTerminalId || Math.random().toString(36).substring(2));

  // Theme detection
  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    
    const detectTheme = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        const computedStyle = getComputedStyle(document.documentElement);
        const bgColor = computedStyle.getPropertyValue('--background').trim();
        const isDark = bgColor.includes('0 0% 3.9%') || bgColor.includes('222.2 84% 4.9%');
        setIsDarkTheme(isDark);
      }, 100);
    };

    detectTheme();
    const observer = new MutationObserver(detectTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class', 'data-theme']
    });

    return () => {
      clearTimeout(timeoutId);
      observer.disconnect();
    };
  }, []);

  // Enhanced clipboard handlers
  const handleCopy = useCallback(async () => {
    const selection = terminal.current?.getSelection();
    if (selection) {
      const clipboard = new EnhancedClipboard();
      await clipboard.copy(selection);
    }
  }, []);

  const handlePaste = useCallback(async () => {
    const clipboard = new EnhancedClipboard();
    const text = await clipboard.paste();
    if (text && connectionId.current && enhancedService.current) {
      try {
        await enhancedService.current.sendMessage(connectionId.current, text, {
          priority: 'high',
          timeout: 5000
        });
      } catch (error) {
        console.warn('Failed to send paste data:', error);
      }
    }
  }, []);

  // Initialize enhanced WebSocket service
  const initializeEnhancedService = useCallback(() => {
    if (enhancedService.current) return;

    // Configure enhanced service with optimized settings
    enhancedService.current = new EnhancedWebSocketService({
      enableMessageQueue: true,
      enableHealthMonitoring: true,
      enableAutoRecovery: true,
      maxConcurrentConnections: 10, // Increased from 5 to allow multiple terminal instances
      messageTimeout: 10000,
      batchConfig: {
        maxSize: 5,
        maxWaitTime: 50,
        enableCompression: false // Disabled for terminal real-time data
      }
    });

    // Set up migration helper for fallback support
    migrationHelper.current = new WebSocketMigrationHelper({
      migrateTerminal: true,
      fallbackToLegacy: true,
      testMode: false
    });

    // Enhanced service event handlers - listen for both connection_opened and connected
    enhancedService.current.on('connection_opened', (data: any) => {
      // Reduced debug: Enhanced service connected
      // console.log('[ICUITerminalTest] Enhanced service connected:', data);
      setIsConnected(true);
      
      if (terminal.current) {
        terminal.current.write('\r\n\x1b[32mEnhanced Terminal Connected!\x1b[0m\r\n');
        terminal.current.write(`Terminal ID: ${terminalId.current}\r\n`);
        terminal.current.write('Enhanced WebSocket with connection management, error handling, and health monitoring\r\n');
        terminal.current.write('Ready for commands...\r\n');
      }
      
      onTerminalReady?.(terminal.current!);
    });

    enhancedService.current.on('connected', (data: any) => {
      // Reduced debug: console.log('[ICUITerminalTest] Enhanced service connected (legacy event):', data);
      setIsConnected(true);
      onTerminalReady?.(terminal.current!);
    });

    enhancedService.current.on('connection_closed', (data: any) => {
      // Reduced debug: console.log('[ICUITerminalTest] Enhanced service disconnected:', data);
      setIsConnected(false);
      if (terminal.current) {
        terminal.current.write('\r\n\x1b[31mTerminal disconnected\x1b[0m\r\n');
      }
    });

    enhancedService.current.on('disconnected', (data: any) => {
      // Reduced debug: console.log('[ICUITerminalTest] Enhanced service disconnected (legacy event):', data);
      setIsConnected(false);
      if (terminal.current) {
        terminal.current.write('\r\n\x1b[31mTerminal disconnected\x1b[0m\r\n');
      }
    });

    enhancedService.current.on('message', (data: any) => {
      if (terminal.current && data.connectionId === connectionId.current) {
        try {
          terminal.current.write(data.message);
          onTerminalOutput?.(data.message);
        } catch (error) {
          console.warn('Terminal write error:', error);
        }
      }
    });

    enhancedService.current.on('error', (error: any) => {
      console.error('[ICUITerminalTest] Enhanced service error:', error);
      if (terminal.current) {
        terminal.current.write(`\r\n\x1b[31mConnection error: ${error.message}\x1b[0m\r\n`);
      }
    });

    enhancedService.current.on('healthUpdate', (health: any) => {
      setHealthStatus(health);
      // Reduced debug: Only log health issues
      if (health.status === 'unhealthy') {
        console.log('[ICUITerminalTest] Health issue:', health);
      }
    });

    enhancedService.current.on('connectionClosed', (data: any) => {
      if (data.connectionId === connectionId.current) {
        // Reduced debug: Only log unexpected connection closures
        if (data.reason && data.reason !== 'normal closure') {
          console.log('[ICUITerminalTest] Unexpected connection closure:', data);
        }
        setIsConnected(false);
        connectionId.current = null;
        onTerminalExit?.(data.code || 0);
      }
    });
  }, [onTerminalReady, onTerminalOutput, onTerminalExit]);

  // Connect to terminal service
  const connectToTerminal = useCallback(async () => {
    if (!enhancedService.current || connectionId.current) return;

    try {
      const options: ConnectionOptions = {
        serviceType: 'terminal',
        terminalId: terminalId.current,
        autoReconnect: true,
        maxRetries: 5,
        priority: 'high',
        timeout: 10000
      };

      console.log('[ICUITerminalTest] Connecting with options:', options);
      connectionId.current = await enhancedService.current.connect(options);
      // Reduced debug: Only log in development mode
      if (process.env.NODE_ENV === 'development') {
        console.log('[ICUITerminalTest] Connected with ID:', connectionId.current);
      }
      
    } catch (error) {
      console.error('[ICUITerminalTest] Connection failed:', error);
      
      // Fallback to legacy service using migration helper
      if (migrationHelper.current) {
        console.log('[ICUITerminalTest] Attempting fallback to legacy service');
        try {
          const legacyService = migrationHelper.current.getService('terminal');
          // Use legacy service connection logic here
        } catch (fallbackError) {
          console.error('[ICUITerminalTest] Fallback also failed:', fallbackError);
        }
      }
    }
  }, []);

  // Initialize terminal
  useEffect(() => {
    if (!terminalRef.current || terminal.current) return;

    // Initialize enhanced service first
    initializeEnhancedService();

    // Create terminal with optimized theme
    const terminalTheme = isDarkTheme ? {
      background: '#0a0a0a',
      foreground: '#ffffff',
      cursor: '#ffffff',
    } : {
      background: '#ffffff',
      foreground: '#000000',
      cursor: '#000000',
    };

    terminal.current = new Terminal({
      theme: terminalTheme,
      fontFamily: '"Cascadia Code", "Fira Code", "JetBrains Mono", monospace',
      fontSize: 14,
      lineHeight: 1.2,
      cursorBlink: true,
      allowTransparency: false,
      convertEol: true
    });

    fitAddon.current = new FitAddon();
    terminal.current.loadAddon(fitAddon.current);
    terminal.current.open(terminalRef.current);
    fitAddon.current.fit();

    // Connect to terminal service
    connectToTerminal();

    // Setup terminal event handlers
    terminal.current.onData((data) => {
      if (connectionId.current && enhancedService.current) {
        enhancedService.current.sendMessage(connectionId.current, data, {
          priority: 'high',
          timeout: 1000
        }).catch(console.warn);
      }
    });

    // Handle terminal selection for copy
    terminal.current.onSelectionChange(() => {
      // Copy selection on Ctrl+C when text is selected
    });

    // Setup resize handling
    resizeObserver.current = new ResizeObserver(() => {
      if (resizeTimeout.current) {
        clearTimeout(resizeTimeout.current);
      }
      resizeTimeout.current = setTimeout(() => {
        if (fitAddon.current) {
          fitAddon.current.fit();
        }
      }, 100);
    });

    if (terminalRef.current) {
      resizeObserver.current.observe(terminalRef.current);
    }

    // Focus terminal
    terminal.current.focus();

    return () => {
      if (resizeTimeout.current) {
        clearTimeout(resizeTimeout.current);
      }
      if (resizeObserver.current) {
        resizeObserver.current.disconnect();
      }
      if (terminal.current) {
        terminal.current.dispose();
      }
      if (connectionId.current && enhancedService.current) {
        enhancedService.current.disconnect(connectionId.current);
      }
    };
  }, [isDarkTheme, initializeEnhancedService, connectToTerminal]);

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    getTerminal: () => terminal.current,
    clear: () => terminal.current?.clear(),
    focus: () => terminal.current?.focus(),
    write: (data: string) => terminal.current?.write(data),
    fit: () => fitAddon.current?.fit(),
    getConnectionId: () => connectionId.current,
    getHealthStatus: () => healthStatus
  }));

  return (
    <div className={`icui-terminal-enhanced ${className}`}>
      <div 
        ref={terminalRef}
        className="terminal-container"
        style={{ 
          width: '100%', 
          height: '100%',
          backgroundColor: isDarkTheme ? '#0a0a0a' : '#ffffff'
        }}
        onContextMenu={(e) => {
          e.preventDefault();
          handlePaste();
        }}
      />
      {!isConnected && (
        <div className="connection-status">
          <span style={{ color: '#ff6b6b' }}>Connecting...</span>
        </div>
      )}
    </div>
  );
});

ICUITerminalTest.displayName = 'ICUITerminalTest';

export default ICUITerminalTest;
