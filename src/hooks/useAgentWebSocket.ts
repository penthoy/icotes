import { useEffect, useRef } from 'react';
import { configService } from '@/services/config-service';

interface AgentWebSocketMessage {
  type: string;
  event: string;
  data: {
    type: string;
    agents?: string[];
    timestamp: number;
    message?: string;
  };
  timestamp: number;
}

interface UseAgentWebSocketOptions {
  onAgentsReloaded?: (agents: string[]) => void;
  onError?: (error: Error) => void;
  enabled?: boolean;
}

export const useAgentWebSocket = (options: UseAgentWebSocketOptions = {}) => {
  const { onAgentsReloaded, onError, enabled = true } = options;
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 2000; // 2 seconds

  const connect = async () => {
    try {
      // Get WebSocket URL from config
      const config = await configService.getConfig();
      let wsUrl: string;
      
      if (config.ws_url) {
        wsUrl = config.ws_url;
      } else {
        // Fallback: construct WebSocket URL from API URL
        const apiUrl = config.api_url || config.base_url || `${window.location.protocol}//${window.location.host}`;
        wsUrl = apiUrl.replace(/^http/, 'ws') + '/ws';
      }

      console.log(`🔌 Connecting to agent WebSocket: ${wsUrl}`);
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ Agent WebSocket connected');
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const message: AgentWebSocketMessage = JSON.parse(event.data);
          
          if (message.type === 'agent_event' && message.event === 'agents.reloaded') {
            console.log('🔄 Received agents reloaded event:', message.data);
            
            if (onAgentsReloaded && message.data.agents) {
              onAgentsReloaded(message.data.agents);
            }
          }
        } catch (error) {
          console.warn('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = (event) => {
        console.log(`🔌 Agent WebSocket closed: ${event.code} ${event.reason}`);
        wsRef.current = null;
        
        // Auto-reconnect if enabled and within limits
        if (enabled && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(`🔄 Attempting to reconnect (${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay * reconnectAttemptsRef.current); // Exponential backoff
        }
      };

      ws.onerror = (error) => {
        console.error('❌ Agent WebSocket error:', error);
        if (onError) {
          onError(new Error('WebSocket connection error'));
        }
      };

    } catch (error) {
      console.error('❌ Failed to connect to agent WebSocket:', error);
      if (onError) {
        onError(error as Error);
      }
    }
  };

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Component unmounting');
      wsRef.current = null;
    }
  };

  useEffect(() => {
    if (enabled) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [enabled]);

  return {
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
    reconnect: connect,
    disconnect
  };
}; 