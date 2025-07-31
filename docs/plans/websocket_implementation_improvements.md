# WebSocket Implementation Improvements

## Current Issues & Recommendations

### 1. **Connection Management Inconsistencies**

#### Current Problems:
- Each service has its own connection logic
- No unified connection state management
- Inconsistent error handling patterns
- Duplicate connection status tracking

#### **Recommendation: Unified Connection Manager**

```typescript
// src/services/connection-manager.ts
export interface ServiceConnection {
  id: string;
  type: 'main' | 'chat' | 'terminal';
  status: 'disconnected' | 'connecting' | 'connected' | 'error';
  websocket: WebSocket | null;
  reconnectAttempts: number;
  lastError?: string;
  metadata?: Record<string, any>;
}

export class ConnectionManager extends EventEmitter {
  private connections = new Map<string, ServiceConnection>();
  private config: BackendConfig;

  // Unified connection method
  async connect(serviceType: 'main' | 'chat' | 'terminal', options?: any): Promise<string> {
    const connectionId = this.generateConnectionId(serviceType, options);
    
    // Prevent duplicate connections
    if (this.connections.has(connectionId)) {
      const existing = this.connections.get(connectionId)!;
      if (existing.status === 'connected' || existing.status === 'connecting') {
        return connectionId;
      }
    }

    const connection: ServiceConnection = {
      id: connectionId,
      type: serviceType,
      status: 'connecting',
      websocket: null,
      reconnectAttempts: 0,
      metadata: options
    };

    this.connections.set(connectionId, connection);
    
    try {
      const wsUrl = this.buildWebSocketUrl(serviceType, options);
      const ws = new WebSocket(wsUrl);
      
      this.setupWebSocketHandlers(connection, ws);
      connection.websocket = ws;
      
      return connectionId;
    } catch (error) {
      this.handleConnectionError(connectionId, error);
      throw error;
    }
  }

  // Unified status tracking
  getConnectionStatus(connectionId: string): ServiceConnection | null {
    return this.connections.get(connectionId) || null;
  }

  // Service-specific helpers
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
}
```

### 2. **Inconsistent Reconnection Logic**

#### Current Problems:
- Each service implements its own reconnection
- Different backoff strategies
- No coordinated retry logic

#### **Recommendation: Standardized Reconnection**

```typescript
// Enhanced reconnection with exponential backoff
export class ReconnectionManager {
  private static readonly BASE_DELAY = 1000;
  private static readonly MAX_DELAY = 30000;
  private static readonly MAX_ATTEMPTS = 5;

  static calculateDelay(attempt: number): number {
    const delay = Math.min(
      this.BASE_DELAY * Math.pow(2, attempt),
      this.MAX_DELAY
    );
    // Add jitter to prevent thundering herd
    return delay + Math.random() * 1000;
  }

  static async reconnectWithBackoff(
    connectionId: string,
    connectFn: () => Promise<void>,
    onStatusChange: (status: string) => void
  ): Promise<void> {
    for (let attempt = 0; attempt < this.MAX_ATTEMPTS; attempt++) {
      try {
        onStatusChange('connecting');
        await connectFn();
        onStatusChange('connected');
        return;
      } catch (error) {
        if (attempt === this.MAX_ATTEMPTS - 1) {
          onStatusChange('error');
          throw new Error(`Failed to reconnect after ${this.MAX_ATTEMPTS} attempts`);
        }
        
        const delay = this.calculateDelay(attempt);
        onStatusChange(`reconnecting-${attempt + 1}`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
}
```

### 3. **Error Handling Improvements**

#### Current Problems:
- Generic error messages
- No error categorization
- Limited error recovery strategies

#### **Recommendation: Structured Error Handling**

```typescript
// src/types/websocket-errors.ts
export enum WebSocketErrorType {
  CONNECTION_FAILED = 'connection_failed',
  AUTHENTICATION_FAILED = 'authentication_failed',
  SERVICE_UNAVAILABLE = 'service_unavailable',
  PROTOCOL_ERROR = 'protocol_error',
  TIMEOUT = 'timeout',
  NETWORK_ERROR = 'network_error'
}

export interface WebSocketError {
  type: WebSocketErrorType;
  message: string;
  code?: number;
  details?: any;
  recoverable: boolean;
  retryAfter?: number;
}

export class WebSocketErrorHandler {
  static categorizeError(event: Event | CloseEvent): WebSocketError {
    if (event instanceof CloseEvent) {
      switch (event.code) {
        case 1000: return { type: WebSocketErrorType.CONNECTION_FAILED, message: 'Normal closure', recoverable: false };
        case 1006: return { type: WebSocketErrorType.NETWORK_ERROR, message: 'Network error', recoverable: true };
        case 1011: return { type: WebSocketErrorType.SERVICE_UNAVAILABLE, message: 'Service unavailable', recoverable: true, retryAfter: 5000 };
        default: return { type: WebSocketErrorType.CONNECTION_FAILED, message: event.reason || 'Unknown error', recoverable: true };
      }
    }
    return { type: WebSocketErrorType.NETWORK_ERROR, message: 'Network error', recoverable: true };
  }

  static shouldRetry(error: WebSocketError): boolean {
    return error.recoverable && error.type !== WebSocketErrorType.AUTHENTICATION_FAILED;
  }
}
```

### 4. **Performance Optimizations**

#### **Recommendation: Connection Pooling & Message Batching**

```typescript
// src/services/message-queue.ts
export class MessageQueue {
  private queue: Array<{ message: any; timestamp: number }> = [];
  private batchTimer: NodeJS.Timeout | null = null;
  private readonly BATCH_SIZE = 10;
  private readonly BATCH_TIMEOUT = 100; // ms

  enqueue(message: any): void {
    this.queue.push({ message, timestamp: Date.now() });
    
    if (this.queue.length >= this.BATCH_SIZE) {
      this.flush();
    } else if (!this.batchTimer) {
      this.batchTimer = setTimeout(() => this.flush(), this.BATCH_TIMEOUT);
    }
  }

  private flush(): void {
    if (this.batchTimer) {
      clearTimeout(this.batchTimer);
      this.batchTimer = null;
    }

    if (this.queue.length === 0) return;

    const batch = this.queue.splice(0);
    this.sendBatch(batch);
  }

  private sendBatch(batch: Array<{ message: any; timestamp: number }>): void {
    // Send batched messages
    const batchMessage = {
      type: 'batch',
      messages: batch.map(item => item.message),
      timestamp: Date.now()
    };
    // Send via WebSocket
  }
}
```

### 5. **Health Monitoring & Diagnostics**

#### **Recommendation: Connection Health Dashboard**

```typescript
// src/services/connection-monitor.ts
export interface ConnectionHealth {
  connectionId: string;
  serviceType: string;
  status: string;
  latency: number;
  messagesPerSecond: number;
  errorRate: number;
  uptime: number;
  lastSeen: number;
}

export class ConnectionMonitor {
  private healthData = new Map<string, ConnectionHealth>();
  private pingInterval: NodeJS.Timeout | null = null;

  startMonitoring(): void {
    this.pingInterval = setInterval(() => {
      this.pingAllConnections();
      this.updateHealthMetrics();
    }, 30000); // 30 seconds
  }

  private async pingAllConnections(): Promise<void> {
    for (const [connectionId, connection] of this.connections) {
      if (connection.status === 'connected') {
        const startTime = Date.now();
        try {
          await this.sendPing(connectionId);
          const latency = Date.now() - startTime;
          this.updateLatency(connectionId, latency);
        } catch (error) {
          this.recordError(connectionId, error);
        }
      }
    }
  }

  getHealthReport(): ConnectionHealth[] {
    return Array.from(this.healthData.values());
  }
}
```

## Implementation Plan

### Phase 1: Core Infrastructure ⭐ **HIGH PRIORITY**
1. **Implement ConnectionManager** - Unify all connection logic
2. **Standardize Error Handling** - Consistent error types and recovery
3. **Add Health Monitoring** - Real-time diagnostics

### Phase 2: Performance Optimization
1. **Message Batching** - Reduce WebSocket overhead
2. **Connection Pooling** - Reuse connections efficiently
3. **Smart Reconnection** - Context-aware retry logic

### Phase 3: Developer Experience
1. **Debug Dashboard** - Real-time connection status
2. **Performance Metrics** - Latency, throughput monitoring
3. **Better Logging** - Structured, filterable logs

## Expected Benefits

✅ **Reliability** - 99.9% uptime with smart reconnection  
✅ **Performance** - 50% reduction in connection overhead  
✅ **Maintainability** - Single point of connection management  
✅ **Debugging** - Clear visibility into connection health  
✅ **User Experience** - Seamless reconnection, better error messages  

## Next Steps

1. **Start with ConnectionManager** - Foundation for all improvements
2. **Migrate Terminal First** - Already partially independent
3. **Update Chat Service** - Standardize reconnection logic
4. **Add Monitoring** - Real-time health dashboard

Would you like me to implement any of these improvements first?
