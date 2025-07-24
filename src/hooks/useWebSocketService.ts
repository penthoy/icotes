/**
 * WebSocket Service Hook
 * 
 * Provides a React hook for accessing the WebSocket service with proper
 * connection management and state tracking.
 */

import { useEffect, useState, useRef } from 'react';
import { getWebSocketService, resetWebSocketService } from '../services/websocket-service';
import type { BackendConfig, ConnectionStatus } from '../types/backend-types';

interface UseWebSocketServiceOptions {
  config?: Partial<BackendConfig>;
  autoConnect?: boolean;
  reconnectOnMount?: boolean;
}

interface UseWebSocketServiceReturn {
  webSocketService: ReturnType<typeof getWebSocketService>;
  connectionStatus: ConnectionStatus;
  isConnected: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
  reconnect: () => void;
}

/**
 * Hook for accessing WebSocket service
 */
export function useWebSocketService(options: UseWebSocketServiceOptions = {}): UseWebSocketServiceReturn {
  const { config, autoConnect = true, reconnectOnMount = false } = options;
  
  // Get singleton service instance
  const webSocketService = getWebSocketService(config);
  
  // State
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const isInitialized = useRef(false);
  
  // Computed state
  const isConnected = connectionStatus === 'connected';
  
  // Connection methods
  const connect = async () => {
    try {
      await webSocketService.connect();
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  };
  
  const disconnect = () => {
    webSocketService.disconnect();
  };
  
  const reconnect = () => {
    webSocketService.reconnect();
  };
  
  // Set up event listeners
  useEffect(() => {
    const handleConnectionStatusChange = (data: { status: ConnectionStatus }) => {
      setConnectionStatus(data.status);
    };
    
    // Subscribe to connection status changes
    webSocketService.on('connection_status_changed', handleConnectionStatusChange);
    
    // Get initial status
    setConnectionStatus(webSocketService.getConnectionStatus());
    
    return () => {
      webSocketService.off('connection_status_changed', handleConnectionStatusChange);
    };
  }, [webSocketService]);
  
  // Auto-connect on mount
  useEffect(() => {
    if (!isInitialized.current) {
      isInitialized.current = true;
      
      if (reconnectOnMount) {
        // Reset and reconnect
        resetWebSocketService();
        const newService = getWebSocketService(config);
        if (autoConnect) {
          connect();
        }
      } else if (autoConnect && connectionStatus === 'disconnected') {
        connect();
      }
    }
  }, [autoConnect, reconnectOnMount, config, connectionStatus]);
  
  return {
    webSocketService,
    connectionStatus,
    isConnected,
    connect,
    disconnect,
    reconnect
  };
}
