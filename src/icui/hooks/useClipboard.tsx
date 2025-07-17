/**
 * React Hook for Enhanced Clipboard Operations
 * 
 * Provides easy-to-use clipboard functionality with automatic state management,
 * notifications, and history tracking.
 */

import { useState, useEffect, useCallback } from 'react';
import { clipboardService, ClipboardResult, ClipboardCapabilities, ClipboardNotification } from '../services/ClipboardService';

export interface UseClipboardOptions {
  enableNotifications?: boolean;
  enableHistory?: boolean;
  onNotification?: (notification: ClipboardNotification) => void;
}

export interface UseClipboardReturn {
  // Core operations
  copy: (text: string) => Promise<ClipboardResult>;
  paste: () => Promise<ClipboardResult>;
  copyWithHistory: (text: string) => Promise<ClipboardResult>;
  
  // State
  capabilities: ClipboardCapabilities;
  isSupported: boolean;
  lastError: string | null;
  
  // History
  localHistory: string[];
  getServerHistory: () => Promise<string[]>;
  getCombinedHistory: () => Promise<string[]>;
  clearHistory: () => Promise<boolean>;
  copyFromHistory: (index: number) => Promise<ClipboardResult>;
  
  // Utilities
  testConnection: () => Promise<boolean>;
  getCapabilityDescription: () => string;
  getDetailedCapabilities: () => Record<string, any>;
  canInstallPWA: () => boolean;
  getPWASuggestion: () => string | null;
  
  // Clipboard watching
  startWatching: (callback: (content: string) => void) => () => void;
}

export function useClipboard(options: UseClipboardOptions = {}): UseClipboardReturn {
  const [capabilities, setCapabilities] = useState<ClipboardCapabilities>(
    clipboardService.getCapabilities()
  );
  const [lastError, setLastError] = useState<string | null>(null);
  const [localHistory, setLocalHistory] = useState<string[]>([]);

  // Initialize clipboard service with notification callback
  useEffect(() => {
    if (options.enableNotifications && options.onNotification) {
      clipboardService.setNotificationCallback(options.onNotification);
    }
    
    // Load initial history
    if (options.enableHistory) {
      setLocalHistory(clipboardService.getLocalHistory());
    }
  }, [options.enableNotifications, options.enableHistory, options.onNotification]);

  // Wrapped copy function with error handling
  const copy = useCallback(async (text: string): Promise<ClipboardResult> => {
    try {
      setLastError(null);
      const result = await clipboardService.copy(text);
      
      if (!result.success && result.error) {
        setLastError(result.error);
      }
      
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setLastError(errorMessage);
      return { success: false, error: errorMessage };
    }
  }, []);

  // Wrapped paste function with error handling
  const paste = useCallback(async (): Promise<ClipboardResult> => {
    try {
      setLastError(null);
      const result = await clipboardService.paste();
      
      if (!result.success && result.error) {
        setLastError(result.error);
      }
      
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setLastError(errorMessage);
      return { success: false, error: errorMessage };
    }
  }, []);

  // Enhanced copy with history tracking
  const copyWithHistory = useCallback(async (text: string): Promise<ClipboardResult> => {
    try {
      setLastError(null);
      const result = await clipboardService.copyWithHistory(text);
      
      if (result.success && options.enableHistory) {
        setLocalHistory(clipboardService.getLocalHistory());
      }
      
      if (!result.success && result.error) {
        setLastError(result.error);
      }
      
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setLastError(errorMessage);
      return { success: false, error: errorMessage };
    }
  }, [options.enableHistory]);

  // History operations
  const getServerHistory = useCallback(async (): Promise<string[]> => {
    try {
      return await clipboardService.getServerHistory();
    } catch (error) {
      console.warn('Failed to get server history:', error);
      return [];
    }
  }, []);

  const getCombinedHistory = useCallback(async (): Promise<string[]> => {
    try {
      return await clipboardService.getCombinedHistory();
    } catch (error) {
      console.warn('Failed to get combined history:', error);
      return [];
    }
  }, []);

  const clearHistory = useCallback(async (): Promise<boolean> => {
    try {
      const result = await clipboardService.clearHistory();
      if (result && options.enableHistory) {
        setLocalHistory([]);
      }
      return result;
    } catch (error) {
      console.warn('Failed to clear history:', error);
      return false;
    }
  }, [options.enableHistory]);

  const copyFromHistory = useCallback(async (index: number): Promise<ClipboardResult> => {
    try {
      setLastError(null);
      const result = await clipboardService.copyFromHistory(index);
      
      if (!result.success && result.error) {
        setLastError(result.error);
      }
      
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setLastError(errorMessage);
      return { success: false, error: errorMessage };
    }
  }, []);

  // Utility functions
  const testConnection = useCallback(async (): Promise<boolean> => {
    try {
      return await clipboardService.testServerConnection();
    } catch (error) {
      console.warn('Connection test failed:', error);
      return false;
    }
  }, []);

  const getCapabilityDescription = useCallback((): string => {
    return clipboardService.getCapabilityDescription();
  }, []);

  const getDetailedCapabilities = useCallback((): Record<string, any> => {
    return clipboardService.getDetailedCapabilities();
  }, []);

  const canInstallPWA = useCallback((): boolean => {
    return clipboardService.canInstallPWA();
  }, []);

  const getPWASuggestion = useCallback((): string | null => {
    return clipboardService.getPWASuggestion();
  }, []);

  const startWatching = useCallback((callback: (content: string) => void): (() => void) => {
    return clipboardService.startClipboardWatcher(callback);
  }, []);

  return {
    // Core operations
    copy,
    paste,
    copyWithHistory,
    
    // State
    capabilities,
    isSupported: clipboardService.hasClipboardAccess(),
    lastError,
    
    // History
    localHistory,
    getServerHistory,
    getCombinedHistory,
    clearHistory,
    copyFromHistory,
    
    // Utilities
    testConnection,
    getCapabilityDescription,
    getDetailedCapabilities,
    canInstallPWA,
    getPWASuggestion,
    
    // Clipboard watching
    startWatching,
  };
}

export default useClipboard;