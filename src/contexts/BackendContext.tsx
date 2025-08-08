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
const getDefaultBackendConfig = (): BackendConfig => {
  // Use Vite environment variables if available, otherwise construct dynamically
  const websocketUrl = import.meta.env.VITE_WS_URL || 
    (typeof window !== 'undefined' 
      ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`
      : 'ws://localhost:8000/ws');

  const httpBaseUrl = import.meta.env.VITE_API_URL || 
    (typeof window !== 'undefined' 
      ? `${window.location.protocol}//${window.location.host}`
      : 'http://localhost:8000');

  return {
    websocket_url: websocketUrl,
    http_base_url: httpBaseUrl,
    request_timeout: 10000,
    reconnect_attempts: 5,
    reconnect_delay: 1000,
    heartbeat_interval: 30000,
    enable_logging: import.meta.env.DEV
  };
};

const defaultBackendConfig = getDefaultBackendConfig();

export interface BackendContextType {
  // Services
  backendClient: any | null; // Will be null until initialized
  webSocketService: ReturnType<typeof getWebSocketService>;
  
  // Connection state
  connectionStatus: ConnectionStatus;
  isConnected: boolean;
  isConnecting: boolean;
  isClientReady: boolean;
  
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
  const [backendClient, setBackendClient] = useState<any>(null);
  const [isClientReady, setIsClientReady] = useState(false);
  const [webSocketService] = useState(() => getWebSocketService(config));
  
  // Initialize backend client asynchronously
  useEffect(() => {
    const initClient = async () => {
      try {
        const client = await getBackendClient(config);
        setBackendClient(client);
        setIsClientReady(true);
        console.log('✅ BackendClient initialized in BackendContext');
      } catch (error) {
        console.error('❌ Failed to initialize BackendClient in context:', error);
        setError('Failed to initialize backend client');
      }
    };
    
    initClient();
  }, [config]);
  
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
      
      // For the main backend context, use 'main' service type
      await webSocketService.connect({
        serviceType: 'main',
        sessionId: `backend-${Date.now()}`,
        autoReconnect: true,
        maxRetries: 5
      });
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
    isClientReady,
    
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
