/**
 * Message Queue System for WebSocket Communications
 * 
 * Provides message batching, queuing, and optimization features to reduce
 * WebSocket overhead and improve performance across all services.
 */

export interface QueuedMessage {
  id: string;
  message: any;
  timestamp: number;
  priority: 'low' | 'normal' | 'high' | 'critical';
  serviceType: string;
  connectionId: string;
  retries: number;
  maxRetries: number;
}

export interface BatchConfig {
  maxSize: number;
  maxWaitTime: number;
  enableCompression: boolean;
  priorityBatching: boolean;
}

export interface QueueStatistics {
  totalMessages: number;
  queuedMessages: number;
  sentMessages: number;
  failedMessages: number;
  averageLatency: number;
  batchesSent: number;
  compressionRatio: number;
}

export class MessageQueue {
  private queue: QueuedMessage[] = [];
  private batchTimer: NodeJS.Timeout | null = null;
  private statistics: QueueStatistics = {
    totalMessages: 0,
    queuedMessages: 0,
    sentMessages: 0,
    failedMessages: 0,
    averageLatency: 0,
    batchesSent: 0,
    compressionRatio: 1.0
  };

  private config: BatchConfig = {
    maxSize: 10,
    maxWaitTime: 100, // ms
    enableCompression: true,
    priorityBatching: true
  };

  protected sendCallback: (messages: QueuedMessage[]) => Promise<void>;
  private messageIdCounter = 0;

  constructor(sendCallback: (messages: QueuedMessage[]) => Promise<void>, config?: Partial<BatchConfig>) {
    this.sendCallback = sendCallback;
    if (config) {
      this.config = { ...this.config, ...config };
    }
  }

  /**
   * Add message to queue
   */
  enqueue(
    message: any, 
    connectionId: string, 
    serviceType: string, 
    priority: QueuedMessage['priority'] = 'normal',
    maxRetries: number = 3
  ): string {
    const messageId = this.generateMessageId();
    
    const queuedMessage: QueuedMessage = {
      id: messageId,
      message,
      timestamp: Date.now(),
      priority,
      serviceType,
      connectionId,
      retries: 0,
      maxRetries
    };

    // Insert message based on priority
    if (this.config.priorityBatching) {
      this.insertByPriority(queuedMessage);
    } else {
      this.queue.push(queuedMessage);
    }

    this.statistics.totalMessages++;
    this.statistics.queuedMessages = this.queue.length;

    // Check if we should flush immediately
    if (priority === 'critical' || this.queue.length >= this.config.maxSize) {
      this.flush();
    } else if (!this.batchTimer) {
      // Schedule batch flush
      this.batchTimer = setTimeout(() => this.flush(), this.config.maxWaitTime);
    }

    return messageId;
  }

  /**
   * Remove message from queue by ID
   */
  dequeue(messageId: string): QueuedMessage | null {
    const index = this.queue.findIndex(msg => msg.id === messageId);
    if (index !== -1) {
      const message = this.queue.splice(index, 1)[0];
      this.statistics.queuedMessages = this.queue.length;
      return message;
    }
    return null;
  }

  /**
   * Get message by ID
   */
  getMessage(messageId: string): QueuedMessage | null {
    return this.queue.find(msg => msg.id === messageId) || null;
  }

  /**
   * Get all queued messages for a connection
   */
  getMessagesForConnection(connectionId: string): QueuedMessage[] {
    return this.queue.filter(msg => msg.connectionId === connectionId);
  }

  /**
   * Clear all messages for a connection
   */
  clearConnection(connectionId: string): void {
    this.queue = this.queue.filter(msg => msg.connectionId !== connectionId);
    this.statistics.queuedMessages = this.queue.length;
  }

  /**
   * Retry failed message
   */
  retryMessage(messageId: string): boolean {
    const message = this.getMessage(messageId);
    if (!message) {
      return false;
    }

    if (message.retries >= message.maxRetries) {
      console.warn(`Message ${messageId} exceeded max retries (${message.maxRetries})`);
      this.dequeue(messageId);
      this.statistics.failedMessages++;
      return false;
    }

    message.retries++;
    message.timestamp = Date.now(); // Update timestamp for retry
    
    // Move to front of queue for immediate processing
    this.dequeue(messageId);
    this.queue.unshift(message);
    
    return true;
  }

  /**
   * Flush queue immediately
   */
  async flush(): Promise<void> {
    if (this.batchTimer) {
      clearTimeout(this.batchTimer);
      this.batchTimer = null;
    }

    if (this.queue.length === 0) {
      return;
    }

    const batch = this.queue.splice(0);
    this.statistics.queuedMessages = 0;

    try {
      // Group messages by connection for efficient sending
      const connectionGroups = this.groupByConnection(batch);
      
      for (const [connectionId, messages] of connectionGroups) {
        await this.sendBatch(connectionId, messages);
      }
      
      this.statistics.sentMessages += batch.length;
      this.statistics.batchesSent++;
      
      // Update average latency
      const totalLatency = batch.reduce((sum, msg) => sum + (Date.now() - msg.timestamp), 0);
      const avgLatency = totalLatency / batch.length;
      this.statistics.averageLatency = (this.statistics.averageLatency + avgLatency) / 2;
      
    } catch (error) {
      console.error('Failed to send batch:', error);
      this.statistics.failedMessages += batch.length;
      
      // Re-queue messages that can be retried
      batch.forEach(msg => {
        if (msg.retries < msg.maxRetries) {
          this.queue.unshift(msg);
        }
      });
      this.statistics.queuedMessages = this.queue.length;
    }
  }

  /**
   * Get queue statistics
   */
  getStatistics(): QueueStatistics {
    return { ...this.statistics };
  }

  /**
   * Clear statistics
   */
  clearStatistics(): void {
    this.statistics = {
      totalMessages: 0,
      queuedMessages: this.queue.length,
      sentMessages: 0,
      failedMessages: 0,
      averageLatency: 0,
      batchesSent: 0,
      compressionRatio: 1.0
    };
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<BatchConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Get current configuration
   */
  getConfig(): BatchConfig {
    return { ...this.config };
  }

  /**
   * Destroy queue and cleanup
   */
  destroy(): void {
    if (this.batchTimer) {
      clearTimeout(this.batchTimer);
      this.batchTimer = null;
    }
    
    this.queue = [];
    this.statistics.queuedMessages = 0;
  }

  // Private helper methods

  private generateMessageId(): string {
    return `msg-${Date.now()}-${++this.messageIdCounter}`;
  }

  private insertByPriority(message: QueuedMessage): void {
    const priorityOrder = { critical: 0, high: 1, normal: 2, low: 3 };
    const messagePriority = priorityOrder[message.priority];
    
    // Find insertion point
    let insertIndex = this.queue.length;
    for (let i = 0; i < this.queue.length; i++) {
      const queuedPriority = priorityOrder[this.queue[i].priority];
      if (messagePriority < queuedPriority) {
        insertIndex = i;
        break;
      }
    }
    
    this.queue.splice(insertIndex, 0, message);
  }

  private groupByConnection(messages: QueuedMessage[]): Map<string, QueuedMessage[]> {
    const groups = new Map<string, QueuedMessage[]>();
    
    for (const message of messages) {
      const existing = groups.get(message.connectionId) || [];
      existing.push(message);
      groups.set(message.connectionId, existing);
    }
    
    return groups;
  }

  private async sendBatch(connectionId: string, messages: QueuedMessage[]): Promise<void> {
    if (messages.length === 1) {
      // Single message - send directly
      await this.sendCallback([messages[0]]);
      return;
    }

    // Create batch message
    const batchMessage: QueuedMessage = {
      id: this.generateMessageId(),
      message: {
        type: 'batch',
        messages: messages.map(msg => ({
          id: msg.id,
          data: msg.message,
          timestamp: msg.timestamp,
          priority: msg.priority
        })),
        timestamp: Date.now(),
        compressed: this.config.enableCompression
      },
      timestamp: Date.now(),
      priority: 'normal',
      serviceType: messages[0].serviceType,
      connectionId,
      retries: 0,
      maxRetries: 1
    };

    // Apply compression if enabled
    if (this.config.enableCompression) {
      const originalSize = JSON.stringify(batchMessage.message).length;
      batchMessage.message = await this.compressMessage(batchMessage.message);
      const compressedSize = JSON.stringify(batchMessage.message).length;
      
      const compressionRatio = originalSize / compressedSize;
      this.statistics.compressionRatio = (this.statistics.compressionRatio + compressionRatio) / 2;
    }

    await this.sendCallback([batchMessage]);
  }

  private async compressMessage(message: any): Promise<any> {
    // Simple compression strategy - could be enhanced with actual compression algorithms
    try {
      const messageStr = JSON.stringify(message);
      
      // For now, just remove unnecessary whitespace and optimize structure
      const optimized = {
        ...message,
        _compressed: true,
        _original_size: messageStr.length
      };
      
      // In a real implementation, you might use libraries like:
      // - pako for gzip compression
      // - lz-string for string compression
      // - Custom binary protocols
      
      return optimized;
    } catch (error) {
      console.warn('Message compression failed:', error);
      return message;
    }
  }
}

/**
 * Priority Queue for critical messages
 */
export class PriorityMessageQueue extends MessageQueue {
  private criticalQueue: QueuedMessage[] = [];
  
  enqueue(
    message: any, 
    connectionId: string, 
    serviceType: string, 
    priority: QueuedMessage['priority'] = 'normal',
    maxRetries: number = 3
  ): string {
    const messageId = super.enqueue(message, connectionId, serviceType, priority, maxRetries);
    
    // Move critical messages to separate queue for immediate processing
    if (priority === 'critical') {
      const queuedMessage = this.getMessage(messageId);
      if (queuedMessage) {
        this.dequeue(messageId);
        this.criticalQueue.push(queuedMessage);
        
        // Process critical messages immediately
        setTimeout(() => this.processCritical(), 0);
      }
    }
    
    return messageId;
  }

  private async processCritical(): Promise<void> {
    if (this.criticalQueue.length === 0) return;
    
    const criticalMessages = this.criticalQueue.splice(0);
    
    try {
      await this.sendCallback(criticalMessages);
    } catch (error) {
      console.error('Failed to send critical messages:', error);
      // Critical messages that fail should be logged but not retried to avoid blocking
    }
  }
}

/**
 * Message Queue Manager
 * Manages multiple queues for different services
 */
export class MessageQueueManager {
  private queues = new Map<string, MessageQueue>();
  private defaultConfig: BatchConfig = {
    maxSize: 10,
    maxWaitTime: 100,
    enableCompression: true,
    priorityBatching: true
  };

  /**
   * Create or get queue for a service
   */
  getQueue(
    serviceType: string, 
    sendCallback: (messages: QueuedMessage[]) => Promise<void>,
    config?: Partial<BatchConfig>
  ): MessageQueue {
    if (!this.queues.has(serviceType)) {
      const queueConfig = { ...this.defaultConfig, ...config };
      this.queues.set(serviceType, new MessageQueue(sendCallback, queueConfig));
    }
    
    return this.queues.get(serviceType)!;
  }

  /**
   * Remove queue for a service
   */
  removeQueue(serviceType: string): void {
    const queue = this.queues.get(serviceType);
    if (queue) {
      queue.destroy();
      this.queues.delete(serviceType);
    }
  }

  /**
   * Get statistics for all queues
   */
  getAllStatistics(): Record<string, QueueStatistics> {
    const stats: Record<string, QueueStatistics> = {};
    
    for (const [serviceType, queue] of this.queues) {
      stats[serviceType] = queue.getStatistics();
    }
    
    return stats;
  }

  /**
   * Clear all queues for a connection
   */
  clearConnection(connectionId: string): void {
    for (const queue of this.queues.values()) {
      queue.clearConnection(connectionId);
    }
  }

  /**
   * Update configuration for all queues
   */
  updateAllConfigs(config: Partial<BatchConfig>): void {
    for (const queue of this.queues.values()) {
      queue.updateConfig(config);
    }
  }

  /**
   * Destroy all queues
   */
  destroy(): void {
    for (const queue of this.queues.values()) {
      queue.destroy();
    }
    this.queues.clear();
  }
}
