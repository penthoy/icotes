/**
 * Backend Context for ICUI-ICPY Integration
 * 
 * This context provides backend client access throughout the application
 * and manages the global backend connection state.
 */

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { getWebSocketService, getBackendClient } from '../services';
import type { 
  ConnectionStatus, 
  BackendConfig
} from '../types/backend-types';

// Backend configuration
const defaultBackendConfig: BackendConfig = {
  websocket_url: process.env.VITE_WEBSOCKET_URL || 'ws://192.168.2.195:8000/ws/enhanced',
  http_base_url: process.env.VITE_API_URL || 'http://192.168.2.195:8000',
  request_timeout: 10000,
  reconnect_attempts: 5,
  reconnect_delay: 1000,
  heartbeat_interval: 30000,
  enable_logging: process.env.NODE_ENV === 'development'
};

export interface BackendContextType {
  // Services
  backendClient: ReturnType<typeof getBackendClient>;
  webSocketService: ReturnType<typeof getWebSocketService>;
  
  // Connection state
  connectionStatus: ConnectionStatus;
  isConnected: boolean;
  isConnecting: boolean;
  
  // Configuration
  config: BackendConfig;
  
  // Connection methods
  connect: () => Promise<void>;
  disconnect: () => void;
  
  // Error state
  error: string | null;
  clearError: () => void;
}

const BackendContext = createContext<BackendContextType | undefined>(undefined);

export interface BackendContextProviderProps {
  children: ReactNode;
  config?: Partial<BackendConfig>;
}

/**
 * Backend Context Provider
 * 
 * Provides backend services and connection management to all child components
 */
export const BackendContextProvider: React.FC<BackendContextProviderProps> = ({ 
  children, 
  config: customConfig 
}) => {
  // Merge custom config with defaults
  const config = { ...defaultBackendConfig, ...customConfig };
  
  // Initialize services
  const [backendClient] = useState(() => getBackendClient(config));
  const [webSocketService] = useState(() => getWebSocketService(config));
  
  // State
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [error, setError] = useState<string | null>(null);
  
  // Computed state
  const isConnected = connectionStatus === 'connected';
  const isConnecting = connectionStatus === 'connecting';
  
  /**
   * Clear error state
   */
  const clearError = () => {
    setError(null);
  };
  
  /**
   * Connect to backend
   */
  const connect = async () => {
    try {
      setConnectionStatus('connecting');
      setError(null);
      
      await webSocketService.connect(config.websocket_url);
      setConnectionStatus('connected');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to connect to backend';
      setError(errorMessage);
      setConnectionStatus('disconnected');
      throw err;
    }
  };
  
  /**
   * Disconnect from backend
   */
  const disconnect = () => {
    try {
      webSocketService.disconnect();
      setConnectionStatus('disconnected');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to disconnect from backend';
      setError(errorMessage);
    }
  };
  
  /**
   * Handle WebSocket connection status changes
   */
  useEffect(() => {
    const handleConnectionStatus = (status: ConnectionStatus) => {
      setConnectionStatus(status);
    };
    
    const handleConnectionError = (error: any) => {
      const errorMessage = error?.message || 'Connection error occurred';
      setError(errorMessage);
      setConnectionStatus('disconnected');
    };
    
    // Subscribe to connection events
    webSocketService.on('connection_status', handleConnectionStatus);
    webSocketService.on('connection_error', handleConnectionError);
    
    return () => {
      webSocketService.off('connection_status', handleConnectionStatus);
      webSocketService.off('connection_error', handleConnectionError);
    };
  }, [webSocketService]);
  
  /**
   * Auto-connect on mount if configured
   */
  useEffect(() => {
    if (config.auto_connect !== false) {
      connect().catch(console.error);
    }
  }, [config.auto_connect]);
  
  const contextValue: BackendContextType = {
    // Services
    backendClient,
    webSocketService,
    
    // Connection state
    connectionStatus,
    isConnected,
    isConnecting,
    
    // Configuration
    config,
    
    // Connection methods
    connect,
    disconnect,
    
    // Error state
    error,
    clearError,
  };
  
  return (
    <BackendContext.Provider value={contextValue}>
      {children}
    </BackendContext.Provider>
  );
};

/**
 * Hook to use backend context
 * 
 * @throws {Error} If used outside of BackendContextProvider
 */
export const useBackendContext = (): BackendContextType => {
  const context = useContext(BackendContext);
  
  if (context === undefined) {
    throw new Error('useBackendContext must be used within a BackendContextProvider');
  }
  
  return context;
};

/**
 * Hook to get backend client
 */
export const useBackendClient = () => {
  const { backendClient } = useBackendContext();
  return backendClient;
};

/**
 * Hook to get WebSocket service
 */
export const useWebSocketService = () => {
  const { webSocketService } = useBackendContext();
  return webSocketService;
};

/**
 * Hook to get connection status
 */
export const useConnectionStatus = () => {
  const { connectionStatus, isConnected, isConnecting, error } = useBackendContext();
  return { connectionStatus, isConnected, isConnecting, error };
};
