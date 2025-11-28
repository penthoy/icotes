/**
 * ICUI Terminal Component - Version 1.0
 *
 * This is the terminal using modern WebSocket service integration.
 * Features:
 * - Clean terminal functionality using XTerm.js
 * - Enhanced WebSocket service integration
 * - No local echo (backend handles all character echoing)  
 * - Proper scrolling behavior and theming
 * - Connection status monitoring
 * - Error handling and reconnection logic
 * - Responsive terminal sizing with FitAddon
 * - Copy/Paste functionality via backend clipboard API
 * - Keyboard shortcuts: Ctrl+Shift+C (copy), Ctrl+Shift+V (paste)
 */

import React, { useRef, useEffect, useState, useCallback, useImperativeHandle, forwardRef } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { notificationService } from '../../services/notificationService';
import { configService } from '../../../services/config-service';

/**
 * Enhanced Clipboard with Multi-Layer Fallback Strategy
 * 
 * Fallback hierarchy:
 * 1. Server-side clipboard (always works - file-based fallback on server)
 * 2. Native browser clipboard (only works in secure context with permissions)
 * 3. In-memory fallback (session-local, always works)
 * 
 * Key insight: Server clipboard is AUTHORITATIVE for paste operations
 * because native clipboard read is heavily restricted by browsers.
 */
class EnhancedClipboard {
  private fallbackText: string = '';
  private static instance: EnhancedClipboard | null = null;
  
  /**
   * Get singleton instance to maintain fallback state across calls
   */
  static getInstance(): EnhancedClipboard {
    if (!EnhancedClipboard.instance) {
      EnhancedClipboard.instance = new EnhancedClipboard();
    }
    return EnhancedClipboard.instance;
  }
  
  /**
   * Check if we're in a secure context (HTTPS or localhost)
   * Native clipboard API is only available in secure contexts
   */
  private isSecureContext(): boolean {
    return window.isSecureContext || 
           location.hostname === 'localhost' ||
           location.hostname === '127.0.0.1' ||
           location.hostname === '::1';
  }
  
  /**
   * Copy text to clipboard using multi-layer strategy
   * Priority: Server (authoritative) → Native (best effort) → Memory fallback
   */
  async copy(text: string): Promise<boolean> {
    if (!text) return false;
    
    // Store as fallback immediately
    this.fallbackText = text;
    
    let serverSuccess = false;
    let nativeSuccess = false;
    
    // Try server-side clipboard FIRST (most reliable, works on HTTP and HTTPS)
    serverSuccess = await this.tryServerClipboard(text);
    
    // Always TRY native clipboard (writeText sometimes works even on HTTP)
    nativeSuccess = await this.tryNativeClipboard(text);
    
    // Show notification based on what worked
    if (nativeSuccess) {
      this.showClipboardNotification('Copied to system clipboard', 'success');
    } else if (serverSuccess) {
      this.showClipboardNotification('Copied (paste with Ctrl+Shift+V)', 'success');
    }
    
    return serverSuccess || nativeSuccess;
  }

  /**
   * Paste text from clipboard using multi-layer strategy
   * Priority: Server (authoritative) → Native (if secure + permitted) → Memory fallback
   * 
   * IMPORTANT: Server is tried FIRST because native clipboard.readText() 
   * is heavily restricted and often fails even in secure contexts.
   */
  async paste(): Promise<string> {
    // SERVER FIRST - this is the authoritative source
    const serverText = await this.tryServerPaste();
    if (serverText) return serverText;
    
    // Try native clipboard only in secure context
    if (this.isSecureContext()) {
      const nativeText = await this.tryNativePaste();
      if (nativeText) return nativeText;
    }
    
    // Memory fallback (works within same session)
    return this.fallbackText || '';
  }

  /**
   * Try to write to native browser clipboard
   * Only works in secure contexts (HTTPS/localhost)
   */
  private async tryNativeClipboard(text: string): Promise<boolean> {
    // Try native clipboard API first
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch {
      // Expected to fail in non-secure contexts
    }
    
    // Fallback: execCommand copy via hidden textarea (works on HTTP during user gesture)
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      ta.style.top = '0';
      ta.setAttribute('readonly', '');
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return ok;
    } catch {
      return false;
    }
  }

  /**
   * Try to read from native browser clipboard
   * This is VERY restricted - requires secure context + user permission + focus
   */
  private async tryNativePaste(): Promise<string | null> {
    try {
      if (navigator.clipboard?.readText) {
        const text = await navigator.clipboard.readText();
        return text || null;
      }
    } catch {
      // Expected to fail - clipboard.readText is heavily restricted
    }
    return null;
  }

  /**
   * Write to server-side clipboard (always works)
   * Server uses file-based fallback if system clipboard unavailable
   */
  private async tryServerClipboard(text: string): Promise<boolean> {
    try {
      const response = await fetch('/clipboard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * Read from server-side clipboard (authoritative source)
   */
  private async tryServerPaste(): Promise<string | null> {
    try {
      const response = await fetch('/clipboard');
      if (!response.ok) return null;
      
      const result = await response.json();
      return (result.success && result.text) ? result.text : null;
    } catch {
      return null;
    }
  }

  /**
   * Show notification to user about clipboard operation
   */
  private showClipboardNotification(message: string, type: 'success' | 'warning'): void {
    notificationService.show(message, type === 'success' ? 'success' : 'warning', {
      position: 'top-right',
      duration: 2000,
      dismissible: true,
      key: `terminal:clipboard:${type}`,
    });
  }
}

interface ICUITerminalProps {
  className?: string;
  terminalId?: string;
  onTerminalReady?: (terminal: Terminal) => void;
  onTerminalOutput?: (output: string) => void;
  onTerminalExit?: (code: number) => void;
}

export interface ICUITerminalRef {
  terminal: Terminal | null;
  sendInput: (input: string) => void;
  clear: () => void;
  focus: () => void;
  resize: () => void;
  destroy: () => void;
}

const ICUITerminal = forwardRef<ICUITerminalRef, ICUITerminalProps>(({
  className = '',
  terminalId: propTerminalId,
  onTerminalReady,
  onTerminalOutput,
  onTerminalExit
}, ref) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const websocket = useRef<WebSocket | null>(null);
  const terminalId = useRef<string>(propTerminalId || Math.random().toString(36).substring(2));
  const terminal = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const resizeObserver = useRef<ResizeObserver | null>(null);
  const resizeTimeout = useRef<NodeJS.Timeout | null>(null);
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef<number>(0);
  const maxReconnectAttempts = 5;
  const [isConnected, setIsConnected] = useState(false);

  // Clipboard handlers - use singleton to maintain fallback state
  const handleCopy = useCallback(async () => {
    const selection = terminal.current?.getSelection();
    if (selection) {
      const clipboard = EnhancedClipboard.getInstance();
      await clipboard.copy(selection);
    }
  }, []);

  // Legacy paste handler for context menu fallback
  const handlePaste = useCallback(async () => {
    // Try capturing user paste via hidden textarea
    const captureViaHidden = () => new Promise<string>((resolve) => {
      const ta = document.createElement('textarea');
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      ta.style.top = '0';
      ta.style.opacity = '0';
      ta.setAttribute('aria-hidden', 'true');
      document.body.appendChild(ta);

      let resolved = false;
      
      const cleanup = (text: string) => {
        if (resolved) return;
        resolved = true;
        clearTimeout(timeoutId);
        try { document.removeEventListener('paste', onPaste as any, true); } catch {}
        try { if (document.body.contains(ta)) document.body.removeChild(ta); } catch {}
        resolve(text);
      };

      const onPaste = (e: ClipboardEvent) => {
        try { e.preventDefault(); } catch {}
        let txt = e.clipboardData?.getData('text/plain') || '';
        setTimeout(() => {
          if (!txt) txt = ta.value;
          cleanup(txt || '');
        }, 0);
      };

      document.addEventListener('paste', onPaste as any, true);
      ta.focus();
      
      // Cleanup timeout if paste never fires (e.g., user cancels)
      const timeoutId = setTimeout(() => cleanup(''), 3000);
    });

    let text = await captureViaHidden();

    // Fallback to server/native strategy for intra-app paste
    if (!text) {
      const clipboard = EnhancedClipboard.getInstance();
      text = await clipboard.paste();
    }

    if (!text) return;

    if (websocket.current?.readyState === WebSocket.OPEN) {
      websocket.current.send(text);
    } else {
      terminal.current?.write(text);
    }
  }, []);

  // Track whether terminal is focused for key handling
  const terminalFocusRef = useRef<boolean>(false);
  const pasteInProgressRef = useRef<boolean>(false);

  // Unified paste capture that sets up hidden textarea BEFORE default paste executes
  const captureSystemPaste = useCallback((): Promise<string> => {
    return new Promise((resolve) => {
      if (pasteInProgressRef.current) {
        resolve('');
        return;
      }
      pasteInProgressRef.current = true;
      const ta = document.createElement('textarea');
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      ta.style.top = '0';
      ta.style.opacity = '0';
      ta.setAttribute('aria-hidden', 'true');
      ta.setAttribute('autocomplete', 'off');
      ta.setAttribute('autocorrect', 'off');
      ta.setAttribute('autocapitalize', 'off');
      ta.setAttribute('spellcheck', 'false');
      document.body.appendChild(ta);

      let resolved = false;

      const cleanup = (text: string) => {
        if (resolved) return;
        resolved = true;
        clearTimeout(timeoutId);
        try { document.removeEventListener('paste', onPaste as any, true); } catch {}
        try { if (document.body.contains(ta)) document.body.removeChild(ta); } catch {}
        pasteInProgressRef.current = false;
        resolve(text);
      };

      const onPaste = (e: ClipboardEvent) => {
        let txt = '';
        try {
          txt = e.clipboardData?.getData('text/plain') || '';
        } catch {}
        // Allow default so content also goes into textarea (as fallback)
        setTimeout(() => {
          if (!txt) txt = ta.value;
          cleanup(txt);
        }, 0);
      };

      document.addEventListener('paste', onPaste as any, true);
      ta.focus();
      
      // Cleanup timeout if paste never fires (e.g., user cancels)
      const timeoutId = setTimeout(() => cleanup(''), 3000);
    });
  }, []);

  // Theme detection
  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    
    const detectTheme = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        const htmlElement = document.documentElement;
        const isDark = htmlElement.classList.contains('dark') || 
                       htmlElement.classList.contains('icui-theme-github-dark') ||
                       htmlElement.classList.contains('icui-theme-monokai') ||
                       htmlElement.classList.contains('icui-theme-one-dark') ||
                       htmlElement.classList.contains('icui-theme-dracula') ||
                       htmlElement.classList.contains('icui-theme-solarized-dark');
        setIsDarkTheme(isDark);
      }, 50);
    };

    detectTheme();
    
    const observer = new MutationObserver(detectTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });

    return () => {
      clearTimeout(timeoutId);
      observer.disconnect();
    };
  }, []);

  // Main terminal initialization
  useEffect(() => {
    if (!terminalRef.current) return;
    
    const computedStyle = getComputedStyle(document.documentElement);
    const getThemeVar = (varName: string) => computedStyle.getPropertyValue(varName).trim();
    
    terminal.current = new Terminal({
      scrollback: 1000,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      cursorStyle: 'block',
      cursorBlink: true,
      theme: {
        background: getThemeVar('--icui-bg-primary') || (isDarkTheme ? '#1e1e1e' : '#ffffff'),
        foreground: getThemeVar('--icui-text-primary') || (isDarkTheme ? '#d4d4d4' : '#000000'),
        cursor: getThemeVar('--icui-text-primary') || (isDarkTheme ? '#d4d4d4' : '#000000'),
        cursorAccent: getThemeVar('--icui-bg-primary') || (isDarkTheme ? '#1e1e1e' : '#ffffff'),
        selectionBackground: isDarkTheme ? '#264f78' : '#add6ff',
        black: getThemeVar('--icui-terminal-black') || '#000000',
        brightBlack: getThemeVar('--icui-terminal-bright-black') || '#666666',
        red: getThemeVar('--icui-terminal-red') || '#cd3131',
        brightRed: getThemeVar('--icui-terminal-bright-red') || '#f14c4c',
        green: getThemeVar('--icui-terminal-green') || '#0dbc79',
        brightGreen: getThemeVar('--icui-terminal-bright-green') || '#23d18b',
        yellow: getThemeVar('--icui-terminal-yellow') || '#e5e510',
        brightYellow: getThemeVar('--icui-terminal-bright-yellow') || '#f5f543',
        blue: getThemeVar('--icui-terminal-blue') || '#2472c8',
        brightBlue: getThemeVar('--icui-terminal-bright-blue') || '#3b8eea',
        magenta: getThemeVar('--icui-terminal-magenta') || '#bc3fbc',
        brightMagenta: getThemeVar('--icui-terminal-bright-magenta') || '#d670d6',
        cyan: getThemeVar('--icui-terminal-cyan') || '#11a8cd',
        brightCyan: getThemeVar('--icui-terminal-bright-cyan') || '#29b8db',
        white: getThemeVar('--icui-terminal-white') || '#e5e5e5',
        brightWhite: getThemeVar('--icui-terminal-bright-white') || '#ffffff',
      },
    });

    fitAddon.current = new FitAddon();
    terminal.current.loadAddon(fitAddon.current);

    // Intercept copy/paste before xterm.js but allow default paste event to fire for capture
    terminal.current.attachCustomKeyEventHandler((event: KeyboardEvent) => {
      if (!terminalFocusRef.current) return true; // Only when terminal focused
      if (event.type !== 'keydown' || event.repeat) return true;

      const isCtrl = event.ctrlKey || event.metaKey;
      const key = event.key.toLowerCase();

      // COPY variants (we suppress default to avoid selection clearing)
      if (isCtrl && key === 'c') {
        if (event.shiftKey || terminal.current?.hasSelection()) {
          event.preventDefault();
          handleCopy();
          return false;
        }
      }

      // PASTE variants: we do NOT preventDefault so native paste event fires
      if (isCtrl && key === 'v') {
        // Setup capture before default executes
        captureSystemPaste().then(text => {
          if (!text) {
            // Always restore terminal focus even if nothing was pasted
            terminal.current?.focus();
            return;
          }
          if (websocket.current?.readyState === WebSocket.OPEN) {
            websocket.current.send(text);
          } else {
            terminal.current?.write(text);
          }
          // Ensure terminal regains focus so Enter works immediately
          terminal.current?.focus();
        });
        return false; // prevent xterm from double handling; keep default paste for textarea only
      }

      return true;
    });

    terminal.current.open(terminalRef.current);
    // Focus tracking
    const onTerminalMouseDown = () => { terminalFocusRef.current = true; };
    const onDocMouseDown = (e: MouseEvent) => {
      if (!terminalRef.current) return;
      if (!terminalRef.current.contains(e.target as Node)) {
        terminalFocusRef.current = false;
      }
    };
    terminalRef.current.addEventListener('mousedown', onTerminalMouseDown);
    document.addEventListener('mousedown', onDocMouseDown);
    
    setTimeout(() => {
      if (fitAddon.current && terminal.current && terminalRef.current) {
        try {
          const rect = terminalRef.current.getBoundingClientRect();
          if (rect.width > 0 && rect.height > 0) {
            fitAddon.current.fit();
          }
        } catch (error) {
          console.warn('Terminal fit error during initialization:', error);
          setTimeout(() => {
            if (fitAddon.current && terminal.current) {
              try {
                fitAddon.current.fit();
              } catch (retryError) {
                console.warn('Terminal fit retry failed:', retryError);
              }
            }
          }, 500);
        }
      }
    }, 100);

    terminal.current.focus();
    terminal.current.write('ICUITerminal initialized!\r\n');
    terminal.current.write('Terminal ID: ' + terminalId.current + '\r\n');
    terminal.current.write('Connecting to backend...\r\n');

    // Connect using enhanced WebSocket service
    const connectToTerminal = async () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = null;
      }

      if (websocket.current) {
        websocket.current.close();
        websocket.current = null;
      }

      try {
        // Get WebSocket URL from config service (which prioritizes backend /api/config)
        const config = await configService.getConfig();
        const wsBaseUrl = config.ws_url;
        
        // Parse the WebSocket URL to get base URL and construct terminal URL
        const url = new URL(wsBaseUrl);
        
        // SAAS PROTOCOL FIX: Auto-detect protocol based on current page
        const currentProtocol = window.location.protocol;
        const shouldUseSecure = currentProtocol === 'https:';
        const finalProtocol = shouldUseSecure ? 'wss:' : url.protocol;
        
        if ((import.meta as any).env?.VITE_DEBUG_PROTOCOL === 'true') {
          console.log(`🔒 ICUITerminal protocol detection: page=${currentProtocol}, config=${url.protocol}, final=${finalProtocol}`);
        }
        
        const baseUrl = `${finalProtocol}//${url.host}`;
        const wsUrl = `${baseUrl}/ws/terminal/${terminalId.current}`;
        
        websocket.current = new WebSocket(wsUrl);
        
      } catch (error) {
        console.error('❌ Failed to get config, falling back to environment variables:', error);
        
        // Fallback to environment variables (for compatibility)
        const envWsUrl = (import.meta as any).env?.VITE_WS_URL as string | undefined;
        let wsUrl: string;
        if (envWsUrl && envWsUrl.trim() !== '') {
          try {
            // SAAS PROTOCOL FIX: Parse and fix protocol for environment URL too
            const envUrl = new URL(envWsUrl);
            const currentProtocol = window.location.protocol;
            const shouldUseSecure = currentProtocol === 'https:';
            const finalProtocol = shouldUseSecure ? 'wss:' : envUrl.protocol;
            
            if ((import.meta as any).env?.VITE_DEBUG_PROTOCOL === 'true') {
              console.log(`🔒 ICUITerminal fallback protocol: page=${currentProtocol}, env=${envUrl.protocol}, final=${finalProtocol}`);
            }
            wsUrl = `${finalProtocol}//${envUrl.host}${envUrl.pathname}/terminal/${terminalId.current}`;
          } catch {
            // If parsing fails, fall back to simple construction
            wsUrl = `${envWsUrl}/terminal/${terminalId.current}`;
          }
        } else {
          const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
          const host = window.location.host;
          wsUrl = `${protocol}//${host}/ws/terminal/${terminalId.current}`;
        }
        
        websocket.current = new WebSocket(wsUrl);
      }
      
      websocket.current.onopen = () => {
        // Reduced debug: Only log in development mode
        if (process.env.NODE_ENV === 'development') {
          console.log(`[ICUITerminal] Connected to terminal ${terminalId.current}`);
        }
        setIsConnected(true);
        reconnectAttempts.current = 0;
        terminal.current?.clear();
        terminal.current?.write('Terminal ID: ' + terminalId.current + '\r\n');
        
        // Don't automatically cd to workspace - let the backend terminal start in the correct directory
        // The backend terminal_startup.sh or backend terminal.py should handle workspace directory setup
        
        terminal.current?.focus();
        onTerminalReady?.(terminal.current);
      };
      
      websocket.current.onmessage = (event) => {
        if (terminal.current) {
          try {
            // Use raw data like the enhanced terminal approach
            const rawData = event.data;
            terminal.current.write(rawData);
            onTerminalOutput?.(rawData);
          } catch (error) {
            console.warn('Terminal write error:', error);
            const data = event.data;
            for (let i = 0; i < data.length; i += 1024) {
              const chunk = data.slice(i, i + 1024);
              terminal.current.write(chunk);
            }
          }
        }
      };
      
      websocket.current.onclose = (event) => {
        // Reduced debug: Only log disconnections in development or on error
        if (process.env.NODE_ENV === 'development' || event.code !== 1000) {
          console.log(`[ICUITerminal] Disconnected from terminal ${terminalId.current}:`, event.code, event.reason);
        }
        setIsConnected(false);
        
        if (event.code !== 1000) {
          terminal.current?.write("\r\n\x1b[31mTerminal disconnected\x1b[0m\r\n");
          
          if (reconnectAttempts.current < maxReconnectAttempts) {
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000);
            reconnectAttempts.current++;
            
            terminal.current?.write(`\r\n\x1b[33mReconnecting in ${delay/1000}s... (attempt ${reconnectAttempts.current}/${maxReconnectAttempts})\x1b[0m\r\n`);
            
            reconnectTimeout.current = setTimeout(async () => {
              await connectToTerminal();
            }, delay);
          } else {
            terminal.current?.write("\r\n\x1b[31mMax reconnection attempts reached. Please refresh to try again.\x1b[0m\r\n");
          }
        }
        
        onTerminalExit?.(event.code || 0);
      };
      
      websocket.current.onerror = (error) => {
        console.error('[ICUITerminal] WebSocket error:', error);
        terminal.current?.write("\r\n\x1b[31mTerminal connection error\x1b[0m\r\n");
      };
    };

    terminal.current.onData((data) => {
      if (websocket.current?.readyState === WebSocket.OPEN) {
        try {
          websocket.current.send(data);
          onTerminalOutput?.(data);
        } catch (sendError) {
          console.error('❌ WebSocket send error:', sendError);
        }
      } else {
        terminal.current?.write("\r\n\x1b[31mTerminal disconnected - attempting reconnection...\x1b[0m\r\n");
        if (reconnectAttempts.current < maxReconnectAttempts) {
          connectToTerminal().catch(error => {
            console.error('❌ Error during reconnection:', error);
          });
        }
      }
    });

    // Connect terminal directly without centralized WebSocket service dependency
    connectToTerminal().catch(error => {
      console.error('❌ Error during initial connection:', error);
    });

    const handleResize = () => {
      if (resizeTimeout.current) {
        clearTimeout(resizeTimeout.current);
      }
      resizeTimeout.current = setTimeout(() => {
        if (fitAddon.current && terminal.current && terminalRef.current) {
          try {
            const rect = terminalRef.current.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
              fitAddon.current.fit();
            }
          } catch (error) {
            console.warn('Terminal fit error during resize:', error);
          }
        }
      }, 100);
    };

    window.addEventListener('resize', handleResize);

    if (terminalRef.current) {
      resizeObserver.current = new ResizeObserver(handleResize);
      resizeObserver.current.observe(terminalRef.current);
    }

    return () => {
      try { terminalRef.current?.removeEventListener('mousedown', onTerminalMouseDown); } catch {}
      try { document.removeEventListener('mousedown', onDocMouseDown); } catch {}
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = null;
      }
      
      if (websocket.current) {
        websocket.current.close();
        websocket.current = null;
      }
      
      if (terminal.current) {
        terminal.current.dispose();
      }
      if (resizeTimeout.current) {
        clearTimeout(resizeTimeout.current);
      }
      if (resizeObserver.current) {
        resizeObserver.current.disconnect();
      }
      window.removeEventListener('resize', handleResize);
    };
  }, [onTerminalReady, onTerminalOutput, onTerminalExit, handleCopy, handlePaste]);

  // Theme update effect
  useEffect(() => {
    if (terminal.current && terminal.current.options) {
      const themeUpdateTimeout = setTimeout(() => {
        const computedStyle = getComputedStyle(document.documentElement);
        const getThemeVar = (varName: string) => computedStyle.getPropertyValue(varName).trim();
        
        const newTheme = {
          background: getThemeVar('--icui-bg-primary') || (isDarkTheme ? '#1e1e1e' : '#ffffff'),
          foreground: getThemeVar('--icui-text-primary') || (isDarkTheme ? '#d4d4d4' : '#000000'),
          cursor: getThemeVar('--icui-text-primary') || (isDarkTheme ? '#d4d4d4' : '#000000'),
          cursorAccent: getThemeVar('--icui-bg-primary') || (isDarkTheme ? '#1e1e1e' : '#ffffff'),
          selectionBackground: isDarkTheme ? '#264f78' : '#add6ff',
          black: getThemeVar('--icui-terminal-black') || '#000000',
          brightBlack: getThemeVar('--icui-terminal-bright-black') || '#666666',
          red: getThemeVar('--icui-terminal-red') || '#cd3131',
          brightRed: getThemeVar('--icui-terminal-bright-red') || '#f14c4c',
          green: getThemeVar('--icui-terminal-green') || '#0dbc79',
          brightGreen: getThemeVar('--icui-terminal-bright-green') || '#23d18b',
          yellow: getThemeVar('--icui-terminal-yellow') || '#e5e510',
          brightYellow: getThemeVar('--icui-terminal-bright-yellow') || '#f5f543',
          blue: getThemeVar('--icui-terminal-blue') || '#2472c8',
          brightBlue: getThemeVar('--icui-terminal-bright-blue') || '#3b8eea',
          magenta: getThemeVar('--icui-terminal-magenta') || '#bc3fbc',
          brightMagenta: getThemeVar('--icui-terminal-bright-magenta') || '#d670d6',
          cyan: getThemeVar('--icui-terminal-cyan') || '#11a8cd',
          brightCyan: getThemeVar('--icui-terminal-bright-cyan') || '#29b8db',
          white: getThemeVar('--icui-terminal-white') || '#e5e5e5',
          brightWhite: getThemeVar('--icui-terminal-bright-white') || '#ffffff',
        };
        
        if (terminal.current) {
          terminal.current.options.theme = newTheme;
          terminal.current.refresh(0, terminal.current.rows - 1);
        }
      }, 100);

      return () => clearTimeout(themeUpdateTimeout);
    }
  }, [isDarkTheme]);

  // CSS styles for viewport scrolling
  useEffect(() => {
    const computedStyle = getComputedStyle(document.documentElement);
    const bgColor = computedStyle.getPropertyValue('--icui-bg-primary').trim() || 
                   (isDarkTheme ? '#1e1e1e' : '#ffffff');
    
    const styleElement = document.createElement('style');
    const styleElementId = `icui-terminal-styles-${terminalId.current}`;
    styleElement.id = styleElementId;
    styleElement.textContent = `
      .icui-terminal-container .xterm .xterm-viewport {
        background-color: ${bgColor} !important;
        overflow-y: scroll !important;
        position: absolute !important;
        top: 0 !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
      }
      
      .icui-terminal-container .xterm .xterm-screen {
        position: relative !important;
      }
      
      .icui-terminal-container .xterm .xterm-screen canvas {
        position: absolute !important;
        left: 0 !important;
        top: 0 !important;
      }
    `;
    
    const existingStyle = document.getElementById(styleElementId);
    if (existingStyle) {
      existingStyle.remove();
    }
    
    document.head.appendChild(styleElement);

    return () => {
      const elementToRemove = document.getElementById(styleElementId);
      if (elementToRemove) {
        elementToRemove.remove();
      }
    };
  }, [isDarkTheme]);

  // Force update terminal viewport background when theme changes
  useEffect(() => {
    if (!terminalRef.current || !terminal.current) return;

    const updateTimeout = setTimeout(() => {
      const terminalViewport = terminalRef.current?.querySelector('.xterm-viewport');
      if (terminalViewport) {
        const computedStyle = getComputedStyle(document.documentElement);
        const bgColor = computedStyle.getPropertyValue('--icui-bg-primary').trim() || 
                       (isDarkTheme ? '#1e1e1e' : '#ffffff');
        (terminalViewport as HTMLElement).style.backgroundColor = bgColor;
      }
    }, 100);

    return () => clearTimeout(updateTimeout);
  }, [isDarkTheme]);

  // Expose terminal methods via ref
  useImperativeHandle(ref, () => ({
    terminal: terminal.current,
    sendInput: (input: string) => {
      if (websocket.current?.readyState === WebSocket.OPEN) {
        websocket.current.send(input);
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
    destroy: () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = null;
      }
      
      if (websocket.current) {
        websocket.current.close();
        websocket.current = null;
      }
      
      if (terminal.current) {
        terminal.current.dispose();
      }
    }
  }));

  // Handle right-click context menu for copy/paste
  const handleContextMenu = useCallback(async (event: React.MouseEvent) => {
    event.preventDefault();
    
    // Simple approach: if text is selected, copy it; otherwise paste
    const selection = terminal.current?.getSelection();
    if (selection) {
      console.log('[Terminal] Context menu - copy selected');
      await handleCopy();
    } else {
      console.log('[Terminal] Context menu - paste');
      await handlePaste();
    }
  }, [handleCopy, handlePaste]);

  return (
    <div className={`icui-terminal ${className}`}>
      <div className="icui-terminal-container h-full w-full">
        <div 
          ref={terminalRef} 
          className="h-full w-full" 
          onContextMenu={handleContextMenu}
        />
      </div>
    </div>
  );
});

ICUITerminal.displayName = 'ICUITerminal';

export default ICUITerminal;
