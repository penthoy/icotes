/**
 * Enhanced WebSocket Service
 * 
 * Integrates the ConnectionManager, error handling, message queuing,
 * and health monitoring into a unified, high-performance WebSocket service.
 */

import { EventEmitter } from 'eventemitter3';
import { ConnectionManager, ServiceType, ServiceConnection } from './connection-manager';
import { WebSocketErrorHandler, WebSocketError, ErrorRecoveryHelper } from './websocket-errors';
import { MessageQueueManager, QueuedMessage } from './message-queue';
import { ConnectionHealthMonitor, DiagnosticResult } from './connection-monitor';
import { BackendConfig } from '../types/backend-types';

export interface WebSocketConfig extends BackendConfig {
  enableMessageQueue: boolean;
  enableHealthMonitoring: boolean;
  enableAutoRecovery: boolean;
  maxConcurrentConnections: number;
  messageTimeout: number;
  batchConfig: {
    maxSize: number;
    maxWaitTime: number;
    enableCompression: boolean;
  };
}

export interface ConnectionOptions {
  serviceType: ServiceType;
  terminalId?: string;
  sessionId?: string;
  autoReconnect?: boolean;
  maxRetries?: number;
  priority?: 'low' | 'normal' | 'high' | 'critical';
  timeout?: number;
}

export interface MessageOptions {
  priority?: 'low' | 'normal' | 'high' | 'critical';
  timeout?: number;
  expectResponse?: boolean;
  retries?: number;
}

export class WebSocketService extends EventEmitter {
  private connectionManager: ConnectionManager;
  private messageQueueManager: MessageQueueManager;
  private healthMonitor: ConnectionHealthMonitor;
  private config: WebSocketConfig;
  
  private messageIdCounter = 0;
  private pendingMessages = new Map<string, { resolve: Function; reject: Function; timeout: NodeJS.Timeout }>();
  
  private readonly DEFAULT_CONFIG: WebSocketConfig = {
    websocket_url: '',
    http_base_url: '',
    reconnect_attempts: 5,
    reconnect_delay: 1000,
    request_timeout: 10000,
    heartbeat_interval: 30000,
    enableMessageQueue: true,
    enableHealthMonitoring: true,
    enableAutoRecovery: true,
    maxConcurrentConnections: 10,
    messageTimeout: 10000,
    batchConfig: {
      maxSize: 10,
      maxWaitTime: 100,
      enableCompression: true
    }
  };

  constructor(config?: Partial<WebSocketConfig>) {
    super();
    
    this.config = { ...this.DEFAULT_CONFIG, ...config };
    
    // Initialize core components
    this.connectionManager = new ConnectionManager(this.config);
    this.messageQueueManager = new MessageQueueManager();
    this.healthMonitor = new ConnectionHealthMonitor();
    
    this.setupEventHandlers();
  }

  /**
   * Connect to a WebSocket service
   */
  async connect(options: ConnectionOptions): Promise<string> {
    try {
      // Emit connecting status for BackendContext compatibility
      this.emit('connection_status', 'connecting');
      
      // Check connection limits
      const existingConnections = this.connectionManager.getConnectionsByType(options.serviceType);
      if (existingConnections.length >= this.config.maxConcurrentConnections) {
        throw new Error(`Maximum concurrent connections (${this.config.maxConcurrentConnections}) reached for ${options.serviceType}`);
      }

      // Create connection
      const connectionId = await this.connectionManager.connect(options.serviceType, {
        terminalId: options.terminalId,
        sessionId: options.sessionId,
        autoReconnect: options.autoReconnect !== false,
        maxReconnectAttempts: options.maxRetries || this.config.reconnect_attempts
      });

      // Wait for connection to be established
      await this.waitForConnection(connectionId, options.timeout || this.config.request_timeout);

      // Setup message queue for this service type
      if (this.config.enableMessageQueue) {
        this.setupMessageQueue(options.serviceType, connectionId);
      }

      // Add to health monitoring
      if (this.config.enableHealthMonitoring) {
        const connection = this.connectionManager.getConnectionStatus(connectionId);
        if (connection) {
          this.healthMonitor.addConnection(connection);
        }
      }

      this.emit('connected', { connectionId, serviceType: options.serviceType });
      return connectionId;

    } catch (error) {
      const wsError = WebSocketErrorHandler.categorizeError(error as Event, {
        serviceType: options.serviceType,
        timestamp: Date.now()
      });
      
      WebSocketErrorHandler.logError(wsError);
      this.emit('error', wsError);
      throw error;
    }
  }

  /**
   * Disconnect from a WebSocket service
   */
  async disconnect(connectionId: string): Promise<void> {
    try {
      // Cancel any pending messages for this connection
      this.cancelPendingMessages(connectionId);

      // Clear message queue
      if (this.config.enableMessageQueue) {
        this.messageQueueManager.clearConnection(connectionId);
      }

      // Remove from health monitoring
      if (this.config.enableHealthMonitoring) {
        this.healthMonitor.removeConnection(connectionId);
      }

      // Disconnect
      await this.connectionManager.disconnect(connectionId, 'User requested disconnect');

      this.emit('disconnected', { connectionId });

    } catch (error) {
      console.error('Error during disconnect:', error);
      throw error;
    }
  }

  /**
   * Send message with enhanced features
   */
  async sendMessage(
    connectionId: string, 
    message: any, 
    options: MessageOptions = {}
  ): Promise<any> {
    const connection = this.connectionManager.getConnectionStatus(connectionId);
    if (!connection) {
      throw new Error(`Connection ${connectionId} not found`);
    }

    const messageId = this.generateMessageId();
    
    let messageWithId: any;
    if (typeof message === 'string') {
      // If message is already a JSON string, parse it, add metadata, then stringify again
      try {
        const parsedMessage = JSON.parse(message);
        messageWithId = JSON.stringify({
          ...parsedMessage,
          id: messageId,
          timestamp: Date.now()
        });
      } catch (e) {
        // If it's not valid JSON, treat as plain string message
        messageWithId = JSON.stringify({
          content: message,
          id: messageId,
          timestamp: Date.now()
        });
      }
    } else {
      // If message is an object, add metadata and stringify
      messageWithId = JSON.stringify({
        id: messageId,
        timestamp: Date.now(),
        ...message
      });
    }

    try {
      if (this.config.enableMessageQueue && options.priority !== 'critical') {
        // Use message queue for non-critical messages
        return await this.sendViaQueue(connectionId, messageWithId, options);
      } else {
        // Send directly for critical messages
        return await this.sendDirect(connectionId, messageWithId, options);
      }
    } catch (error) {
      const wsError = WebSocketErrorHandler.categorizeError(error as Event, {
        connectionId,
        serviceType: connection.type,
        timestamp: Date.now()
      });
      
      WebSocketErrorHandler.logError(wsError);
      
      // Attempt recovery if enabled
      if (this.config.enableAutoRecovery && WebSocketErrorHandler.shouldRetry(wsError)) {
        return await this.attemptMessageRecovery(connectionId, messageWithId, options, wsError);
      }
      
      throw error;
    }
  }

  /**
   * Get connection status
   */
  getConnectionStatus(connectionId: string): ServiceConnection | null {
    return this.connectionManager.getConnectionStatus(connectionId);
  }

  /**
   * Check if service has any active connections (legacy compatibility)
   */
  isConnected(): boolean {
    const stats = this.connectionManager.getStatistics();
    return (stats.byStatus.connected || 0) > 0;
  }

  /**
   * Get health information
   */
  getHealthInfo(connectionId?: string) {
    if (connectionId) {
      return {
        connection: this.connectionManager.getConnectionStatus(connectionId),
        health: this.healthMonitor.getHealthScore(connectionId),
        metrics: this.healthMonitor.getHealthMetrics(connectionId)
      };
    }

    return {
      summary: this.healthMonitor.getHealthSummary(),
      connections: this.connectionManager.getStatistics(),
      queues: this.messageQueueManager.getAllStatistics()
    };
  }

  /**
   * Run diagnostics on a connection
   */
  async runDiagnostics(connectionId: string): Promise<DiagnosticResult | null> {
    if (!this.config.enableHealthMonitoring) {
      throw new Error('Health monitoring is disabled');
    }

    return await this.healthMonitor.runDiagnostics(connectionId);
  }

  /**
   * Get performance recommendations
   */
  getRecommendations(connectionId: string): string[] {
    if (!this.config.enableHealthMonitoring) {
      return ['Health monitoring is disabled - enable it for recommendations'];
    }

    return this.healthMonitor.getRecommendations(connectionId);
  }

  /**
   * Update service configuration
   */
  updateConfig(config: Partial<WebSocketConfig>): void {
    this.config = { ...this.config, ...config };
    
    // Update message queue configs
    if (config.batchConfig) {
      this.messageQueueManager.updateAllConfigs(config.batchConfig);
    }
  }

  /**
   * Export diagnostic data
   */
  exportDiagnostics(): any {
    return {
      config: this.config,
      connections: this.connectionManager.getStatistics(),
      messageQueues: this.messageQueueManager.getAllStatistics(),
      healthData: this.config.enableHealthMonitoring ? this.healthMonitor.exportHealthData() : null,
      errors: WebSocketErrorHandler.getErrorStatistics(),
      timestamp: Date.now()
    };
  }

  /**
   * Destroy service and cleanup
   */
  destroy(): void {
    // Clear all pending messages
    for (const [messageId, pending] of this.pendingMessages) {
      clearTimeout(pending.timeout);
      pending.reject(new Error('Service destroyed'));
    }
    this.pendingMessages.clear();

    // Cleanup components
    this.connectionManager.destroy();
    this.messageQueueManager.destroy();
    this.healthMonitor.destroy();

    // Clear all listeners
    this.removeAllListeners();
  }

  // Private helper methods

  private setupEventHandlers(): void {
    // Connection Manager events
    this.connectionManager.on('connection_opened', (data) => {
      this.emit('connection_opened', data);
      this.emit('connection_status', 'connected'); // For BackendContext compatibility
    });

    this.connectionManager.on('connection_closed', (data) => {
      this.handleConnectionClosed(data);
      this.emit('connection_closed', data);
      this.emit('connection_status', 'disconnected'); // For BackendContext compatibility
    });

    this.connectionManager.on('connection_error', (data) => {
      this.handleConnectionError(data);
      this.emit('connection_error', data);
      this.emit('connection_status', 'error'); // For BackendContext compatibility
    });

    this.connectionManager.on('message', (data) => {
      this.handleIncomingMessage(data);
    });
  }

  private async waitForConnection(connectionId: string, timeout: number): Promise<void> {
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error(`Connection timeout after ${timeout}ms`));
      }, timeout);

      const checkConnection = () => {
        const connection = this.connectionManager.getConnectionStatus(connectionId);
        if (connection?.status === 'connected') {
          clearTimeout(timeoutId);
          resolve();
        } else if (connection?.status === 'error') {
          clearTimeout(timeoutId);
          reject(new Error(connection.lastError || 'Connection failed'));
        } else {
          // Still connecting, check again
          setTimeout(checkConnection, 100);
        }
      };

      checkConnection();
    });
  }

  private setupMessageQueue(serviceType: ServiceType, connectionId: string): void {
    const sendCallback = async (messages: QueuedMessage[]) => {
      for (const message of messages) {
        try {
          await this.connectionManager.sendMessage(message.connectionId, message.message);
          
          // Update health metrics
          if (this.config.enableHealthMonitoring) {
            this.healthMonitor.updateMetrics(message.connectionId, {
              messagesSent: 1,
              bytesSent: JSON.stringify(message.message).length
            });
          }
        } catch (error) {
          console.error(`Failed to send queued message ${message.id}:`, error);
          throw error;
        }
      }
    };

    this.messageQueueManager.getQueue(serviceType, sendCallback, this.config.batchConfig);
  }

  private async sendViaQueue(
    connectionId: string, 
    message: any, 
    options: MessageOptions
  ): Promise<any> {
    const connection = this.connectionManager.getConnectionStatus(connectionId);
    if (!connection) {
      throw new Error(`Connection ${connectionId} not found`);
    }

    const queue = this.messageQueueManager.getQueue(
      connection.type,
      async () => {}, // Will be handled by existing callback
      this.config.batchConfig
    );

    const messageId = queue.enqueue(
      message,
      connectionId,
      connection.type,
      options.priority || 'normal',
      options.retries || 3
    );

    if (options.expectResponse) {
      // Extract message ID from string or object
      let actualMessageId: string;
      if (typeof message === 'string') {
        try {
          const parsed = JSON.parse(message);
          actualMessageId = parsed.id;
        } catch (e) {
          // If no ID can be extracted, skip waiting for response
          return;
        }
      } else {
        actualMessageId = message.id;
      }
      
      if (actualMessageId) {
        return await this.waitForResponse(actualMessageId, options.timeout || this.config.messageTimeout);
      }
    }
  }

  private async sendDirect(
    connectionId: string, 
    message: any, 
    options: MessageOptions
  ): Promise<any> {
    await this.connectionManager.sendMessage(connectionId, message);

    // Update health metrics
    if (this.config.enableHealthMonitoring) {
      this.healthMonitor.updateMetrics(connectionId, {
        messagesSent: 1,
        bytesSent: typeof message === 'string' ? message.length : JSON.stringify(message).length
      });
    }

    if (options.expectResponse) {
      // Extract message ID from string or object
      let messageId: string;
      if (typeof message === 'string') {
        try {
          const parsed = JSON.parse(message);
          messageId = parsed.id;
        } catch (e) {
          // If no ID can be extracted, skip waiting for response
          return;
        }
      } else {
        messageId = message.id;
      }
      
      if (messageId) {
        return await this.waitForResponse(messageId, options.timeout || this.config.messageTimeout);
      }
    }
  }

  private async waitForResponse(messageId: string, timeout: number): Promise<any> {
    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        this.pendingMessages.delete(messageId);
        reject(new Error(`Message response timeout after ${timeout}ms`));
      }, timeout);

      this.pendingMessages.set(messageId, {
        resolve,
        reject,
        timeout: timeoutId
      });
    });
  }

  private async attemptMessageRecovery(
    connectionId: string,
    message: any,
    options: MessageOptions,
    error: WebSocketError
  ): Promise<any> {
    console.log(`Attempting recovery for message ${message.id} on connection ${connectionId}`);

    try {
      await ErrorRecoveryHelper.executeRecovery(error, (message) => {
        this.emit('recovery_progress', { connectionId, message });
      });

      // Retry the message
      return await this.sendMessage(connectionId, message, {
        ...options,
        retries: (options.retries || 0) - 1
      });
    } catch (recoveryError) {
      console.error('Message recovery failed:', recoveryError);
      throw error; // Throw original error
    }
  }

  private handleConnectionClosed(data: { connectionId: string; serviceType: string; code: number; reason: string }): void {
    // Cancel pending messages for this connection
    this.cancelPendingMessages(data.connectionId);

    // Clear message queue
    if (this.config.enableMessageQueue) {
      this.messageQueueManager.clearConnection(data.connectionId);
    }

    // Update health monitoring
    if (this.config.enableHealthMonitoring) {
      this.healthMonitor.updateMetrics(data.connectionId, {
        errorCount: data.code !== 1000 ? 1 : 0
      });
    }
  }

  private handleConnectionError(data: { connectionId: string; serviceType: string; error: any }): void {
    // Update health metrics
    if (this.config.enableHealthMonitoring) {
      this.healthMonitor.updateMetrics(data.connectionId, {
        errorCount: 1
      });
    }
  }

  private handleIncomingMessage(data: { connectionId: string; data: string; serviceType: string }): void {
    try {
      // Update health metrics first
      if (this.config.enableHealthMonitoring) {
        this.healthMonitor.updateMetrics(data.connectionId, {
          messagesReceived: 1,
          bytesReceived: data.data.length
        });
      }

      // Try to parse as JSON first, but handle raw text gracefully
      let message: any;
      let isRawData = false;
      
      try {
        message = JSON.parse(data.data);
      } catch (parseError) {
        // Not JSON - handle as raw data (for terminal, etc.)
        isRawData = true;
        message = {
          type: 'raw_data',
          data: data.data,
          connectionId: data.connectionId,
          serviceType: data.serviceType,
          timestamp: Date.now()
        };
      }

      // Handle response messages (only for JSON messages)
      if (!isRawData && message.id && this.pendingMessages.has(message.id)) {
        const pending = this.pendingMessages.get(message.id)!;
        clearTimeout(pending.timeout);
        this.pendingMessages.delete(message.id);
        pending.resolve(message);
        return;
      }

      // Handle ping/pong for latency tracking (only for JSON messages)
      if (!isRawData && message.type === 'pong' && message.timestamp) {
        const latency = Date.now() - message.timestamp;
        if (this.config.enableHealthMonitoring) {
          this.healthMonitor.updateMetrics(data.connectionId, { latency });
        }
        return;
      }

      // Emit regular message
      this.emit('message', {
        connectionId: data.connectionId,
        serviceType: data.serviceType,
        message,
        rawData: data.data  // Keep original string for compatibility
      });

    } catch (error) {
      console.error('Error parsing incoming message:', error);
      this.emit('parse_error', {
        connectionId: data.connectionId,
        serviceType: data.serviceType,
        data: data.data,
        error
      });
    }
  }

  private cancelPendingMessages(connectionId: string): void {
    for (const [messageId, pending] of this.pendingMessages) {
      // In a more sophisticated implementation, you'd track which messages belong to which connection
      clearTimeout(pending.timeout);
      pending.reject(new Error(`Connection ${connectionId} closed`));
    }
    // For now, clear all pending messages - in production you'd be more selective
  }

  private generateMessageId(): string {
    return `msg-${Date.now()}-${++this.messageIdCounter}`;
  }
}
