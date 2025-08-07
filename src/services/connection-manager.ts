/**
 * Unified Connection Manager for WebSocket Services
 * 
 * This service provides centralized connection management for all WebSocket services
 * including terminal, chat, and main backend connections. It implements standardized
 * reconnection logic, error handling, and health monitoring.
 */

import { BackendConfig } from '../types/backend-types';
import { EventEmitter } from 'eventemitter3';
import { configService } from './config-service';

export type ServiceType = 'main' | 'chat' | 'terminal';
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface ConnectionOptions {
  terminalId?: string;
  sessionId?: string;
  [key: string]: any;
}

export interface ServiceConnection {
  id: string;
  type: ServiceType;
  status: ConnectionStatus;
  websocket: WebSocket | null;
  reconnectAttempts: number;
  maxReconnectAttempts: number;
  lastError?: string;
  metadata?: Record<string, any>;
  createdAt: number;
  connectedAt?: number;
  lastActivity?: number;
}

export interface ConnectionHealth {
  connectionId: string;
  serviceType: ServiceType;
  status: ConnectionStatus;
  latency: number;
  messagesPerSecond: number;
  errorRate: number;
  uptime: number;
  lastSeen: number;
  reconnectAttempts: number;
  maxReconnectAttempts: number;
}

export interface ReconnectionConfig {
  baseDelay: number;
  maxDelay: number;
  maxAttempts: number;
  jitterEnabled: boolean;
}

export class ReconnectionManager {
  private static readonly DEFAULT_CONFIG: ReconnectionConfig = {
    baseDelay: 1000,
    maxDelay: 30000,
    maxAttempts: 5,
    jitterEnabled: true
  };

  static calculateDelay(attempt: number, config: Partial<ReconnectionConfig> = {}): number {
    const { baseDelay, maxDelay, jitterEnabled } = { ...this.DEFAULT_CONFIG, ...config };
    
    const delay = Math.min(
      baseDelay * Math.pow(2, attempt),
      maxDelay
    );
    
    // Add jitter to prevent thundering herd
    if (jitterEnabled) {
      return delay + Math.random() * 1000;
    }
    
    return delay;
  }

  static async reconnectWithBackoff(
    connectionId: string,
    connectFn: () => Promise<void>,
    onStatusChange: (status: ConnectionStatus, error?: string) => void,
    config: Partial<ReconnectionConfig> = {}
  ): Promise<void> {
    const { maxAttempts } = { ...this.DEFAULT_CONFIG, ...config };
    
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        onStatusChange('connecting');
        await connectFn();
        onStatusChange('connected');
        return;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        
        if (attempt === maxAttempts - 1) {
          onStatusChange('error', `Failed to reconnect after ${maxAttempts} attempts: ${errorMessage}`);
          throw new Error(`Failed to reconnect after ${maxAttempts} attempts`);
        }
        
        const delay = this.calculateDelay(attempt, config);
        onStatusChange('connecting', `Reconnecting in ${delay/1000}s... (attempt ${attempt + 1}/${maxAttempts})`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
}

export class ConnectionManager extends EventEmitter {
  private connections = new Map<string, ServiceConnection>();
  private config: BackendConfig;
  private healthData = new Map<string, ConnectionHealth>();
  private pingInterval: NodeJS.Timeout | null = null;
  private cleanupInterval: NodeJS.Timeout | null = null;

  constructor(config: BackendConfig) {
    super();
    this.config = config;
    this.startHealthMonitoring();
  }

  /**
   * Connect to a service with unified connection logic
   */
  async connect(
    serviceType: ServiceType, 
    options?: { 
      terminalId?: string;
      sessionId?: string;
      maxReconnectAttempts?: number;
      autoReconnect?: boolean;
      [key: string]: any;
    }
  ): Promise<string> {
    const connectionId = this.generateConnectionId(serviceType, options);
    
    // Prevent duplicate connections
    if (this.connections.has(connectionId)) {
      const existing = this.connections.get(connectionId)!;
      if (existing.status === 'connected' || existing.status === 'connecting') {
        console.warn(`Connection ${connectionId} already exists with status: ${existing.status}`);
        return connectionId;
      }
    }

    const connection: ServiceConnection = {
      id: connectionId,
      type: serviceType,
      status: 'connecting',
      websocket: null,
      reconnectAttempts: 0,
      maxReconnectAttempts: options?.maxReconnectAttempts || this.config.reconnect_attempts || 5,
      metadata: options,
      createdAt: Date.now()
    };

    this.connections.set(connectionId, connection);
    
    try {
      const wsUrl = await this.buildWebSocketUrl(serviceType, options);
      const ws = new WebSocket(wsUrl);
      
      this.setupWebSocketHandlers(connection, ws);
      connection.websocket = ws;
      
      this.emit('connection_created', { connectionId, serviceType, wsUrl });
      return connectionId;
    } catch (error) {
      this.handleConnectionError(connectionId, error);
      throw error;
    }
  }

  /**
   * Disconnect a specific connection
   */
  async disconnect(connectionId: string, reason?: string): Promise<void> {
    const connection = this.connections.get(connectionId);
    if (!connection) {
      console.warn(`Connection ${connectionId} not found`);
      return;
    }

    if (connection.websocket) {
      connection.websocket.close(1000, reason || 'Disconnected by user');
    }

    this.connections.delete(connectionId);
    this.healthData.delete(connectionId);
    
    this.emit('connection_removed', { connectionId, reason });
  }

  /**
   * Send message through a specific connection
   */
  async sendMessage(connectionId: string, message: any): Promise<void> {
    const connection = this.connections.get(connectionId);
    if (!connection || !connection.websocket) {
      throw new Error(`Connection ${connectionId} not found or not connected`);
    }

    if (connection.websocket.readyState !== WebSocket.OPEN) {
      throw new Error(`Connection ${connectionId} is not open (state: ${connection.websocket.readyState})`);
    }

    const messageData = typeof message === 'string' ? message : JSON.stringify(message);
    connection.websocket.send(messageData);
    
    // Update activity tracking
    connection.lastActivity = Date.now();
    this.updateHealthMetrics(connectionId, { messagesSent: 1 });
  }

  /**
   * Get connection status
   */
  getConnectionStatus(connectionId: string): ServiceConnection | null {
    return this.connections.get(connectionId) || null;
  }

  /**
   * Get all connections for a service type
   */
  getConnectionsByType(serviceType: ServiceType): ServiceConnection[] {
    return Array.from(this.connections.values()).filter(c => c.type === serviceType);
  }

  /**
   * Service-specific helpers
   */
  getMainConnection(): ServiceConnection | null {
    return Array.from(this.connections.values()).find(c => c.type === 'main') || null;
  }

  getChatConnection(): ServiceConnection | null {
    return Array.from(this.connections.values()).find(c => c.type === 'chat') || null;
  }

  getTerminalConnection(terminalId: string): ServiceConnection | null {
    return Array.from(this.connections.values())
      .find(c => c.type === 'terminal' && c.metadata?.terminalId === terminalId) || null;
  }

  /**
   * Get health report for all connections
   */
  getHealthReport(): ConnectionHealth[] {
    return Array.from(this.healthData.values());
  }

  /**
   * Get connection statistics
   */
  getStatistics(): { totalConnections: number; byStatus: Record<ConnectionStatus, number>; byType: Record<ServiceType, number> } {
    const connections = Array.from(this.connections.values());
    
    const byStatus = connections.reduce((acc, conn) => {
      acc[conn.status] = (acc[conn.status] || 0) + 1;
      return acc;
    }, {} as Record<ConnectionStatus, number>);
    
    const byType = connections.reduce((acc, conn) => {
      acc[conn.type] = (acc[conn.type] || 0) + 1;
      return acc;
    }, {} as Record<ServiceType, number>);

    return {
      totalConnections: connections.length,
      byStatus,
      byType
    };
  }

  /**
   * Cleanup and destroy the connection manager
   */
  destroy(): void {
    // Close all connections
    for (const [connectionId] of this.connections) {
      this.disconnect(connectionId, 'Connection manager destroyed');
    }

    // Clear intervals
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }

    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }

    // Clear all listeners
    this.removeAllListeners();
  }

  // Private methods

  private generateConnectionId(serviceType: ServiceType, options?: ConnectionOptions): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8);
    
    if (serviceType === 'terminal' && 'terminalId' in options) {
      return `terminal-${options.terminalId}-${timestamp}-${random}`;
    }
    
    if (serviceType === 'chat' && 'sessionId' in options) {
      return `chat-${options.sessionId}-${timestamp}-${random}`;
    }
    
    return `${serviceType}-${timestamp}-${random}`;
  }

  private async buildWebSocketUrl(serviceType: ServiceType, options?: ConnectionOptions): Promise<string> {
    try {
      // Get config from the dynamic config service (which prioritizes backend /api/config)
      const config = await configService.getConfig();
      const wsUrl = config.ws_url;
      
      console.log(`🔗 Using WebSocket URL from config service: ${wsUrl}`);
      
      // Parse the WebSocket URL to get base URL
      const url = new URL(wsUrl);
      const baseUrl = `${url.protocol}//${url.host}`;
      
      switch (serviceType) {
        case 'terminal':
          const terminalId = options?.terminalId || Math.random().toString(36).substring(2);
          return `${baseUrl}/ws/terminal/${terminalId}`;
        case 'chat':
          return `${baseUrl}/ws/chat`;
        case 'main':
          return `${baseUrl}/ws`;
        default:
          throw new Error(`Unknown service type: ${serviceType}`);
      }
    } catch (error) {
      console.error('❌ Failed to get config, falling back to environment variables:', error);
      
      // Fallback to environment variables (for compatibility)
      const envWsUrl = (import.meta as any).env?.VITE_WS_URL as string | undefined;
      
      // Build base URL
      let baseUrl: string;
      if (envWsUrl) {
        // VITE_WS_URL should be like 'ws://host:port/ws', extract the base
        const url = new URL(envWsUrl);
        baseUrl = `${url.protocol}//${url.host}`;
      } else {
        // Fallback to constructing from current location
        baseUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;
      }
      
      switch (serviceType) {
        case 'terminal':
          const terminalId = options?.terminalId || Math.random().toString(36).substring(2);
          return `${baseUrl}/ws/terminal/${terminalId}`;
        case 'chat':
          return `${baseUrl}/ws/chat`;
        case 'main':
          return `${baseUrl}/ws`;
        default:
          throw new Error(`Unknown service type: ${serviceType}`);
      }
    }
  }

  private setupWebSocketHandlers(connection: ServiceConnection, ws: WebSocket): void {
    ws.onopen = () => {
      console.log(`Connection ${connection.id} opened`);
      connection.status = 'connected';
      connection.connectedAt = Date.now();
      connection.reconnectAttempts = 0;
      connection.lastActivity = Date.now();
      
      this.initializeHealthData(connection);
      this.emit('connection_opened', { connectionId: connection.id, serviceType: connection.type });
    };

    ws.onmessage = (event) => {
      connection.lastActivity = Date.now();
      this.updateHealthMetrics(connection.id, { messagesReceived: 1 });
      this.emit('message', { connectionId: connection.id, data: event.data, serviceType: connection.type });
    };

    ws.onclose = (event) => {
      console.log(`Connection ${connection.id} closed:`, event.code, event.reason);
      connection.status = event.code === 1000 ? 'disconnected' : 'error';
      connection.websocket = null;
      
      if (event.code !== 1000) {
        connection.lastError = event.reason || `Connection closed with code ${event.code}`;
        
        // Auto-reconnect if enabled and within limits
        if (connection.metadata?.autoReconnect !== false && 
            connection.reconnectAttempts < connection.maxReconnectAttempts) {
          this.scheduleReconnection(connection);
        }
      }
      
      this.emit('connection_closed', { 
        connectionId: connection.id, 
        serviceType: connection.type, 
        code: event.code, 
        reason: event.reason 
      });
    };

    ws.onerror = (error) => {
      console.error(`Connection ${connection.id} error:`, error);
      connection.status = 'error';
      connection.lastError = 'WebSocket error occurred';
      this.updateHealthMetrics(connection.id, { errors: 1 });
      this.emit('connection_error', { connectionId: connection.id, serviceType: connection.type, error });
    };
  }

  private handleConnectionError(connectionId: string, error: any): void {
    const connection = this.connections.get(connectionId);
    if (connection) {
      connection.status = 'error';
      connection.lastError = error instanceof Error ? error.message : 'Unknown error';
      this.updateHealthMetrics(connectionId, { errors: 1 });
    }
    
    console.error(`Connection ${connectionId} error:`, error);
    this.emit('connection_error', { connectionId, error });
  }

  private scheduleReconnection(connection: ServiceConnection): void {
    const delay = ReconnectionManager.calculateDelay(connection.reconnectAttempts);
    connection.reconnectAttempts++;
    
    console.log(`Scheduling reconnection for ${connection.id} in ${delay}ms (attempt ${connection.reconnectAttempts})`);
    
    setTimeout(async () => {
      if (connection.status === 'error' && this.connections.has(connection.id)) {
        console.log(`Attempting reconnection for ${connection.id}`);
        try {
          const wsUrl = await this.buildWebSocketUrl(connection.type, connection.metadata);
          const ws = new WebSocket(wsUrl);
          this.setupWebSocketHandlers(connection, ws);
          connection.websocket = ws;
          connection.status = 'connecting';
        } catch (error) {
          this.handleConnectionError(connection.id, error);
        }
      }
    }, delay);
  }

  private initializeHealthData(connection: ServiceConnection): void {
    this.healthData.set(connection.id, {
      connectionId: connection.id,
      serviceType: connection.type,
      status: connection.status,
      latency: 0,
      messagesPerSecond: 0,
      errorRate: 0,
      uptime: 0,
      lastSeen: Date.now(),
      reconnectAttempts: connection.reconnectAttempts,
      maxReconnectAttempts: connection.maxReconnectAttempts
    });
  }

  private updateHealthMetrics(connectionId: string, updates: { 
    messagesSent?: number; 
    messagesReceived?: number; 
    errors?: number; 
    latency?: number;
  }): void {
    const health = this.healthData.get(connectionId);
    if (!health) return;

    if (updates.messagesSent) {
      // Update messages per second calculation
      const now = Date.now();
      const timeDiff = (now - health.lastSeen) / 1000;
      if (timeDiff > 0) {
        health.messagesPerSecond = updates.messagesSent / timeDiff;
      }
    }

    if (updates.messagesReceived) {
      health.lastSeen = Date.now();
    }

    if (updates.errors) {
      health.errorRate += updates.errors;
    }

    if (updates.latency !== undefined) {
      health.latency = updates.latency;
    }

    const connection = this.connections.get(connectionId);
    if (connection) {
      health.status = connection.status;
      health.uptime = connection.connectedAt ? Date.now() - connection.connectedAt : 0;
      health.reconnectAttempts = connection.reconnectAttempts;
    }
  }

  private startHealthMonitoring(): void {
    // Health monitoring ping every 30 seconds
    this.pingInterval = setInterval(() => {
      this.pingAllConnections();
      this.updateAllHealthMetrics();
    }, 30000);

    // Cleanup stale connections every 5 minutes
    this.cleanupInterval = setInterval(() => {
      this.cleanupStaleConnections();
    }, 300000);
  }

  private async pingAllConnections(): Promise<void> {
    for (const [connectionId, connection] of this.connections) {
      if (connection.status === 'connected' && connection.websocket) {
        const startTime = Date.now();
        try {
          // Send ping message based on service type
          const pingMessage = { type: 'ping', timestamp: startTime };
          await this.sendMessage(connectionId, pingMessage);
          
          // Note: Actual latency will be calculated when pong is received
          // This is just a placeholder for the ping attempt
        } catch (error) {
          console.warn(`Failed to ping connection ${connectionId}:`, error);
          this.updateHealthMetrics(connectionId, { errors: 1 });
        }
      }
    }
  }

  private updateAllHealthMetrics(): void {
    for (const [connectionId, connection] of this.connections) {
      this.updateHealthMetrics(connectionId, {});
    }
  }

  private cleanupStaleConnections(): void {
    const now = Date.now();
    const staleThreshold = 300000; // 5 minutes

    for (const [connectionId, connection] of this.connections) {
      const lastActivity = connection.lastActivity || connection.createdAt;
      if (now - lastActivity > staleThreshold && connection.status === 'error') {
        console.log(`Cleaning up stale connection: ${connectionId}`);
        this.disconnect(connectionId, 'Stale connection cleanup');
      }
    }
  }
}
