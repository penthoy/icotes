/**
 * WebSocket Service for ICUI-ICPY Integration
 * 
 * This service provides a robust WebSocket client implementation for real-time
 * communication with the ICPY backend. It includes automatic reconnection,
 * event-based message handling, connection status tracking, and error recovery.
 */

import {
  ConnectionStatus,
  WebSocketMessage,
  JsonRpcRequest,
  JsonRpcResponse,
  JsonRpcNotification,
  EventHandler,
  EventHandlerMap,
  PendingRequest,
  ConnectionRecovery,
  ConnectionStatistics,
  BackendConfig
} from '../types/backend-types';

export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private heartbeatInterval = 30000;
  private requestTimeout = 10000;
  
  private eventHandlers: EventHandlerMap = new Map();
  private connectionStatus: ConnectionStatus = 'disconnected';
  private pendingRequests: Map<string, PendingRequest> = new Map();
  private connectionRecovery: ConnectionRecovery = {
    subscription_topics: [],
    pending_requests: [],
    connection_timestamp: 0
  };
  
  private statistics: ConnectionStatistics = {
    messages_sent: 0,
    messages_received: 0,
    reconnect_count: 0,
    last_reconnect: '',
    uptime: 0,
    latency: 0
  };
  
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private connectStartTime = 0;
  private lastPingTime = 0;
  
  constructor(private config: BackendConfig) {
    this.maxReconnectAttempts = config.reconnect_attempts;
    this.reconnectDelay = config.reconnect_delay;
    this.requestTimeout = config.request_timeout;
    this.heartbeatInterval = config.heartbeat_interval;
  }

  /**
   * Connect to the WebSocket server
   */
  async connect(url?: string): Promise<void> {
    const wsUrl = url || this.config.websocket_url;
    
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.warn('WebSocket already connected');
      return;
    }

    // Prevent multiple simultaneous connection attempts
    if (this.connectionStatus === 'connecting') {
      console.warn('WebSocket connection already in progress');
      return;
    }

    this.connectionStatus = 'connecting';
    this.connectStartTime = Date.now();
    this.emit('connection_status_changed', { status: this.connectionStatus });

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.connectionStatus = 'connected';
          this.reconnectAttempts = 0;
          this.statistics.uptime = Date.now() - this.connectStartTime;
          this.connectionRecovery.connection_timestamp = Date.now();
          
          this.emit('connection_status_changed', { status: this.connectionStatus });
          this.emit('connected');
          
          // Start heartbeat
          this.startHeartbeat();
          
          // Restore subscriptions if reconnecting
          this.restoreSubscriptions();
          
          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason);
          this.connectionStatus = 'disconnected';
          this.emit('connection_status_changed', { status: this.connectionStatus });
          this.emit('disconnected', { code: event.code, reason: event.reason });
          
          this.stopHeartbeat();
          
          // Attempt reconnection if not intentional
          if (event.code !== 1000) {
            this.scheduleReconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.connectionStatus = 'error';
          this.emit('connection_status_changed', { status: this.connectionStatus });
          this.emit('error', error);
          
          reject(error);
        };
        
      } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
        this.connectionStatus = 'error';
        this.emit('connection_status_changed', { status: this.connectionStatus });
        reject(error);
      }
    });
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    this.stopHeartbeat();
    
    if (this.ws) {
      this.ws.close(1000, 'Client initiated disconnect');
      this.ws = null;
    }
    
    this.connectionStatus = 'disconnected';
    this.emit('connection_status_changed', { status: this.connectionStatus });
    
    // Reject all pending requests
    this.pendingRequests.forEach(request => {
      if (request.timeout) {
        clearTimeout(request.timeout);
      }
      request.reject(new Error('Connection closed'));
    });
    this.pendingRequests.clear();
  }

  /**
   * Send a message to the WebSocket server
   */
  send(message: WebSocketMessage): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    const messageWithTimestamp = {
      ...message,
      timestamp: Date.now()
    };

    try {
      this.ws.send(JSON.stringify(messageWithTimestamp));
      this.statistics.messages_sent++;
    } catch (error) {
      console.error('Failed to send message:', error);
      throw error;
    }
  }

  /**
   * Send a JSON-RPC request and return a promise with the response
   */
  async request<T = any>(method: string, params?: any): Promise<T> {
    const id = this.generateRequestId();
    const request: JsonRpcRequest = {
      jsonrpc: '2.0',
      method,
      params,
      id
    };

    return new Promise((resolve, reject) => {
      // Store pending request
      const pendingRequest: PendingRequest = {
        id,
        method,
        timestamp: Date.now(),
        resolve,
        reject,
        timeout: setTimeout(() => {
          this.pendingRequests.delete(id);
          reject(new Error(`Request timeout: ${method}`));
        }, this.requestTimeout)
      };

      this.pendingRequests.set(id, pendingRequest);

      try {
        this.send({ type: 'json-rpc', payload: request });
      } catch (error) {
        this.pendingRequests.delete(id);
        if (pendingRequest.timeout) {
          clearTimeout(pendingRequest.timeout);
        }
        reject(error);
      }
    });
  }

  /**
   * Send a JSON-RPC notification (no response expected)
   */
  notify(method: string, params?: any): void {
    const notification: JsonRpcNotification = {
      jsonrpc: '2.0',
      method,
      params
    };

    this.send({ type: 'json-rpc', payload: notification });
  }

  /**
   * Subscribe to an event
   */
  on(event: string, handler: EventHandler): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event)!.push(handler);
  }

  /**
   * Unsubscribe from an event
   */
  off(event: string, handler: EventHandler): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index !== -1) {
        handlers.splice(index, 1);
        if (handlers.length === 0) {
          this.eventHandlers.delete(event);
        }
      }
    }
  }

  /**
   * Emit an event to all subscribed handlers
   */
  emit(event: string, data?: any): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`Error in event handler for ${event}:`, error);
        }
      });
    }
  }

  /**
   * Get current connection status
   */
  getConnectionStatus(): ConnectionStatus {
    return this.connectionStatus;
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.connectionStatus === 'connected' && this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Get connection statistics
   */
  getStatistics(): ConnectionStatistics {
    return { ...this.statistics };
  }

  /**
   * Reconnect to the WebSocket server
   */
  reconnect(): void {
    console.log('Manual reconnection requested');
    this.disconnect();
    this.connect();
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(event: MessageEvent): void {
    this.statistics.messages_received++;
    
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      // Handle different message types
      switch (message.type) {
        case 'json-rpc':
          this.handleJsonRpcMessage(message.payload);
          break;
        case 'event':
          this.handleEventMessage(message.payload);
          break;
        case 'pong':
          this.handlePongMessage(message.payload);
          break;
        case 'heartbeat':
          // Handle heartbeat messages (backend sends these)
          this.handleHeartbeatMessage(message.payload);
          break;
        case 'welcome':
          // Handle welcome messages from backend
          this.handleWelcomeMessage(message.payload);
          break;
        case 'subscribed':
          // Handle subscription confirmation from backend
          this.handleSubscriptionMessage(message.payload, true);
          break;
        case 'unsubscribed':
          // Handle unsubscription confirmation from backend
          this.handleSubscriptionMessage(message.payload, false);
          break;
        default:
          console.warn('Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  /**
   * Handle JSON-RPC messages (responses and notifications)
   */
  private handleJsonRpcMessage(payload: JsonRpcResponse | JsonRpcNotification): void {
    // Check if it's a response (has id)
    if ('id' in payload && payload.id !== undefined) {
      const response = payload as JsonRpcResponse;
      const pendingRequest = this.pendingRequests.get(String(response.id));
      
      if (pendingRequest) {
        if (pendingRequest.timeout) {
          clearTimeout(pendingRequest.timeout);
        }
        this.pendingRequests.delete(String(response.id));
        
        if (response.error) {
          pendingRequest.reject(new Error(response.error.message));
        } else {
          pendingRequest.resolve(response.result);
        }
      }
    } else {
      // It's a notification
      const notification = payload as JsonRpcNotification;
      this.emit(notification.method, notification.params);
    }
  }

  /**
   * Handle event messages from the backend
   */
  private handleEventMessage(payload: any): void {
    if (payload.type) {
      this.emit(payload.type, payload.data);
    }
  }

  /**
   * Handle pong messages for heartbeat
   */
  private handlePongMessage(payload: any): void {
    // Check if payload and timestamp exist before accessing
    if (payload && payload.timestamp && payload.timestamp === this.lastPingTime) {
      this.statistics.latency = Date.now() - this.lastPingTime;
    }
  }

  /**
   * Handle heartbeat messages from backend
   */
  private handleHeartbeatMessage(payload: any): void {
    // Backend sends heartbeat messages, we can respond with pong
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.send({
        type: 'pong',
        payload: { timestamp: Date.now() }
      });
    }
  }

  /**
   * Handle welcome messages from backend
   */
  private handleWelcomeMessage(payload: any): void {
    // Backend sends welcome message on connection
    console.log('Received welcome message from backend:', payload);
    this.emit('welcome', payload);
  }

  /**
   * Handle subscription/unsubscription confirmation messages from backend
   */
  private handleSubscriptionMessage(payload: any, isSubscribed: boolean): void {
    const action = isSubscribed ? 'subscribed to' : 'unsubscribed from';
    const topics = payload.topics || [];
    
    // Log subscription status for debugging
    if (topics.length > 0) {
      console.log(`WebSocket ${action} topics:`, topics);
    }
    
    // Emit subscription event for components that need to track subscription status
    this.emit(isSubscribed ? 'subscribed' : 'unsubscribed', {
      topics,
      timestamp: payload.timestamp
    });
  }

  /**
   * Start heartbeat mechanism
   */
  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.lastPingTime = Date.now();
        this.send({
          type: 'ping',
          payload: { timestamp: this.lastPingTime }
        });
      }
    }, this.heartbeatInterval);
  }

  /**
   * Stop heartbeat mechanism
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * Schedule reconnection with exponential backoff
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.emit('max_reconnects_reached');
      return;
    }

    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectDelay
    );

    console.log(`Scheduling reconnection attempt ${this.reconnectAttempts + 1} in ${delay}ms`);
    
    this.reconnectTimer = setTimeout(() => {
      // Check if we're still disconnected before reconnecting
      if (this.connectionStatus === 'disconnected' || this.connectionStatus === 'error') {
        this.reconnectAttempts++;
        this.statistics.reconnect_count++;
        this.statistics.last_reconnect = new Date().toISOString();
        
        this.emit('reconnecting', { attempt: this.reconnectAttempts });
        this.connect().catch(error => {
          console.error('Reconnection failed:', error);
        });
      }
    }, delay);
  }

  /**
   * Restore subscriptions after reconnection
   */
  private restoreSubscriptions(): void {
    // Restore topic subscriptions
    this.connectionRecovery.subscription_topics.forEach(topic => {
      this.notify('subscribe', { topic });
    });
  }

  /**
   * Generate a unique request ID
   */
  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Default configuration
const getDefaultConfig = (): BackendConfig => {
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
    reconnect_attempts: 3, // Reduced from 5
    reconnect_delay: 2000, // Increased from 1000
    request_timeout: 10000,
    heartbeat_interval: 30000
  };
};

const defaultConfig = getDefaultConfig();

// Singleton instance
let websocketService: WebSocketService | null = null;

/**
 * Get the singleton WebSocket service instance
 */
export function getWebSocketService(config?: Partial<BackendConfig>): WebSocketService {
  if (!websocketService) {
    const finalConfig = { ...defaultConfig, ...config };
    websocketService = new WebSocketService(finalConfig);
  }
  return websocketService;
}

/**
 * Reset the singleton instance (useful for testing)
 */
export function resetWebSocketService(): void {
  if (websocketService) {
    websocketService.disconnect();
    websocketService = null;
  }
}

export default WebSocketService;
