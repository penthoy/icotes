/**
 * Enhanced Clipboard Service for ICUI
 * 
 * Multi-layer clipboard system that bypasses browser security limitations
 * by providing multiple fallback strategies, similar to code-server's approach.
 * 
 * Fallback Hierarchy:
 * 1. Browser native Clipboard API (when available in secure context)
 * 2. Server-side clipboard bridge with system integration
 * 3. In-memory fallback for session continuity
 * 
 * @author ICUI Development Team
 */

import { EventEmitter } from 'events';

export interface ClipboardEntry {
  content: string;
  timestamp: string;
  method: string;
  length: number;
}

export interface ClipboardCapabilities {
  hasNativeAccess: boolean;
  hasServerAccess: boolean;
  hasFileAccess: boolean;
  isSecureContext: boolean;
  canInstallPWA: boolean;
  platform: string;
  availableMethods: string[];
}

export interface ClipboardNotification {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  method?: string;
  duration?: number;
}

export interface ClipboardResult {
  success: boolean;
  content?: string;
  method?: string;
  error?: string;
  metadata?: any;
}

export class ClipboardService extends EventEmitter {
  private fallbackContent: string = '';
  private history: ClipboardEntry[] = [];
  private maxHistory: number = 50;
  private capabilities: ClipboardCapabilities;
  private notificationCallback?: (notification: ClipboardNotification) => void;
  private watcherInterval?: NodeJS.Timeout;

  constructor() {
    super();
    this.capabilities = this.initializeCapabilities();
    this.initializeService();
  }

  private initializeCapabilities(): ClipboardCapabilities {
    return {
      hasNativeAccess: !!(navigator.clipboard && window.isSecureContext),
      hasServerAccess: false, // Will be updated after server check
      hasFileAccess: true, // Always available as fallback
      isSecureContext: window.isSecureContext,
      canInstallPWA: this.detectPWASupport(),
      platform: navigator.platform,
      availableMethods: this.getAvailableMethods()
    };
  }

  private getAvailableMethods(): string[] {
    const methods = ['fallback'];
    if (this.capabilities.hasNativeAccess) methods.push('native');
    return methods;
  }

  private detectPWASupport(): boolean {
    return 'serviceWorker' in navigator && 
           window.matchMedia('(display-mode: standalone)').matches === false;
  }

  private async initializeService(): Promise<void> {
    await this.updateServerCapabilities();
    this.emit('ready', this.capabilities);
  }

  private async updateServerCapabilities(): Promise<void> {
    try {
      const response = await fetch('/clipboard/status', { 
        method: 'GET',
        signal: AbortSignal.timeout(2000)
      });
      if (response.ok) {
        const serverStatus = await response.json();
        if (serverStatus.success && serverStatus.status) {
          this.capabilities.hasServerAccess = true;
          const serverMethods = serverStatus.status.available_methods || [];
          this.capabilities.availableMethods = [
            ...this.capabilities.availableMethods.filter(m => m !== 'server'),
            ...serverMethods
          ];
        }
      }
    } catch (error) {
      console.debug('Server clipboard status check failed:', error);
    }
  }

  // Core clipboard operations
  async copy(text: string): Promise<ClipboardResult> {
    if (!text) {
      return this.notifyResult({ success: false, error: 'No text provided' });
    }

    this.fallbackContent = text;
    this.addToHistory(text, 'fallback');

    // Try native clipboard first
    const nativeResult = await this.tryNativeWrite(text);
    if (nativeResult.success) {
      await this.syncToServer(text);
      this.notify({ type: 'success', message: 'Copied via native clipboard', method: 'native' });
      this.emit('copy', { text, method: 'native' });
      return nativeResult;
    }

    // Try server-side clipboard
    const serverResult = await this.tryServerWrite(text);
    if (serverResult.success) {
      this.notify({ type: 'success', message: 'Copied via server clipboard', method: 'server' });
      this.emit('copy', { text, method: 'server' });
      return serverResult;
    }

    // Fallback always succeeds
    this.notify({ type: 'warning', message: 'Using in-memory fallback', method: 'fallback' });
    this.emit('copy', { text, method: 'fallback' });
    return { success: true, method: 'fallback' };
  }

  async copyWithHistory(text: string): Promise<ClipboardResult> {
    return await this.copy(text); // History is automatically tracked
  }

  async paste(): Promise<ClipboardResult> {
    const nativeResult = await this.tryNativeRead();
    if (nativeResult.success && nativeResult.content) {
      this.emit('paste', { text: nativeResult.content, method: 'native' });
      return nativeResult;
    }

    const serverResult = await this.tryServerRead();
    if (serverResult.success && serverResult.content) {
      this.emit('paste', { text: serverResult.content, method: 'server' });
      return serverResult;
    }

    this.emit('paste', { text: this.fallbackContent, method: 'fallback' });
    return {
      success: true,
      content: this.fallbackContent,
      method: 'fallback'
    };
  }

  // History operations
  getHistory(limit: number = 10): ClipboardEntry[] {
    return this.history.slice(0, limit);
  }

  getLocalHistory(): string[] {
    return this.history.map(entry => entry.content);
  }

  async getServerHistory(): Promise<string[]> {
    try {
      const response = await fetch('/clipboard/history');
      const result = await response.json();
      if (result.success && result.history) {
        return result.history.map((entry: any) => entry.content || entry);
      }
    } catch (error) {
      console.debug('Server history fetch failed:', error);
    }
    return [];
  }

  async getCombinedHistory(): Promise<string[]> {
    const localHistory = this.getLocalHistory();
    const serverHistory = await this.getServerHistory();
    
    // Combine and deduplicate
    const combined = [...localHistory];
    serverHistory.forEach(item => {
      if (!combined.includes(item)) {
        combined.push(item);
      }
    });
    
    return combined;
  }

  async clearHistory(): Promise<boolean> {
    this.history = [];
    try {
      await fetch('/clipboard/clear', { method: 'POST' });
      this.notify({ type: 'success', message: 'Clipboard history cleared' });
      return true;
    } catch (error) {
      this.notify({ type: 'error', message: 'Failed to clear server history' });
      return false;
    }
  }

  async copyFromHistory(index: number): Promise<ClipboardResult> {
    const entry = this.history[index];
    if (!entry) {
      return { success: false, error: 'Invalid history index' };
    }
    return await this.copy(entry.content);
  }

  // Capabilities and status
  getCapabilities(): ClipboardCapabilities {
    return { ...this.capabilities };
  }

  hasClipboardAccess(): boolean {
    return this.capabilities.hasNativeAccess || this.capabilities.hasServerAccess;
  }

  async testServerConnection(): Promise<boolean> {
    try {
      const response = await fetch('/clipboard/status', { 
        signal: AbortSignal.timeout(3000) 
      });
      return response.ok;
    } catch (error) {
      return false;
    }
  }

  getCapabilityDescription(): string {
    const methods = this.capabilities.availableMethods;
    if (methods.includes('native')) return 'Full clipboard access';
    if (methods.includes('server')) return 'Server-based clipboard';
    return 'Limited clipboard (fallback only)';
  }

  getDetailedCapabilities(): Record<string, any> {
    return {
      ...this.capabilities,
      fallbackStorage: !!this.fallbackContent,
      historyCount: this.history.length
    };
  }

  canInstallPWA(): boolean {
    return this.capabilities.canInstallPWA;
  }

  getPWASuggestion(): string | null {
    if (this.canInstallPWA() && !this.capabilities.hasNativeAccess) {
      return 'Install as PWA for better clipboard access';
    }
    return null;
  }

  // Clipboard watching
  startClipboardWatcher(callback: (content: string) => void): () => void {
    if (this.watcherInterval) {
      clearInterval(this.watcherInterval);
    }

    let lastContent = '';
    this.watcherInterval = setInterval(async () => {
      const result = await this.paste();
      if (result.success && result.content && result.content !== lastContent) {
        lastContent = result.content;
        callback(result.content);
      }
    }, 1000);

    return () => {
      if (this.watcherInterval) {
        clearInterval(this.watcherInterval);
        this.watcherInterval = undefined;
      }
    };
  }

  // Notification system
  setNotificationCallback(callback: (notification: ClipboardNotification) => void): void {
    this.notificationCallback = callback;
  }

  private notify(notification: ClipboardNotification): void {
    if (this.notificationCallback) {
      this.notificationCallback(notification);
    }
    this.emit('notification', notification);
  }

  private notifyResult(result: ClipboardResult): ClipboardResult {
    if (!result.success && result.error) {
      this.notify({ type: 'error', message: result.error });
    }
    return result;
  }

  // Private implementation methods
  private async tryNativeWrite(text: string): Promise<ClipboardResult> {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return { success: true, method: 'native' };
      }
    } catch (error) {
      console.debug('Native clipboard write failed:', error);
    }
    return { success: false, error: 'Native clipboard not available' };
  }

  private async tryNativeRead(): Promise<ClipboardResult> {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        const text = await navigator.clipboard.readText();
        return { success: true, content: text, method: 'native' };
      }
    } catch (error) {
      console.debug('Native clipboard read failed:', error);
    }
    return { success: false, error: 'Native clipboard not available' };
  }

  private async tryServerWrite(text: string): Promise<ClipboardResult> {
    try {
      const response = await fetch('/clipboard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
        signal: AbortSignal.timeout(5000)
      });

      const result = await response.json();
      if (result.success) {
        this.addToHistory(text, result.metadata?.method || 'server');
        return {
          success: true,
          method: result.metadata?.method || 'server',
          metadata: result.metadata
        };
      } else {
        return { success: false, error: result.message };
      }
    } catch (error) {
      console.debug('Server clipboard write failed:', error);
      return { success: false, error: String(error) };
    }
  }

  private async tryServerRead(): Promise<ClipboardResult> {
    try {
      const response = await fetch('/clipboard', {
        signal: AbortSignal.timeout(5000)
      });
      
      const result = await response.json();
      if (result.success && result.text) {
        return {
          success: true,
          content: result.text,
          method: result.metadata?.method || 'server',
          metadata: result.metadata
        };
      } else {
        return { success: false, error: result.message };
      }
    } catch (error) {
      console.debug('Server clipboard read failed:', error);
      return { success: false, error: String(error) };
    }
  }

  private async syncToServer(text: string): Promise<void> {
    try {
      await fetch('/clipboard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
        signal: AbortSignal.timeout(3000)
      });
    } catch (error) {
      console.debug('Server sync failed:', error);
    }
  }

  private addToHistory(content: string, method: string): void {
    const entry: ClipboardEntry = {
      content,
      timestamp: new Date().toISOString(),
      method,
      length: content.length
    };

    this.history = this.history.filter(h => h.content !== content);
    this.history.unshift(entry);
    
    if (this.history.length > this.maxHistory) {
      this.history = this.history.slice(0, this.maxHistory);
    }

    this.emit('history-updated', this.history);
  }
}

// Global service instance
export const clipboardService = new ClipboardService();

export default ClipboardService;
