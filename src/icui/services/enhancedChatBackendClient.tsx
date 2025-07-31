/**
 * Enhanced Chat Backend Client
 * 
 * Integrates all WebSocket improvements: connection management, error handling,
 * message queuing, health monitoring, and migration support for chat service.
 */

import { EnhancedWebSocketService, ConnectionOptions, MessageOptions } from '../../services/enhanced-websocket-service';
import { WebSocketMigrationHelper } from '../../services/websocket-migration';
import { notificationService } from './notificationService';
import { ConnectionStatus } from '../types/chatTypes';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  sender: 'user' | 'ai' | 'system';
  metadata?: {
    agentId?: string;
    agentName?: string;
    agentType?: 'openai' | 'crewai' | 'langchain' | 'langgraph';
    messageType?: 'text' | 'code' | 'error' | 'system' | 'streaming';
    workflowId?: string;
    taskId?: string;
    capabilities?: string[];
    context?: any;
    isStreaming?: boolean;
    streamComplete?: boolean;
    // Enhanced fields for backward compatibility
    model?: string;
    agent?: string;
    streaming?: boolean;
    tokens?: number;
    latency?: number;
  };
}

export interface ChatSession {
  id: string;
  name: string;
  messages: ChatMessage[];
  created: number;
  updated: number;
  metadata?: {
    agent?: string;
    model?: string;
    temperature?: number;
  };
}

export interface ChatStatus {
  connected: boolean;
  timestamp: Date; // Changed to Date for consistency
  chat: {
    sessionId: string;
    agentId?: string;
    model?: string;
  };
  error?: string;
}

export interface AgentConfig {
  id: string;
  name: string;
  description: string;
  model: string;
  temperature: number;
  system_prompt: string;
  tools?: any[];
}

export class EnhancedChatBackendClient {
  private enhancedService: EnhancedWebSocketService | null = null;
  private migrationHelper: WebSocketMigrationHelper | null = null;
  private connectionId: string | null = null;
  
  // Event handlers
  private statusCallbacks: ((status: ChatStatus) => void)[] = [];
  private messageCallbacks: ((message: ChatMessage) => void)[] = [];
  private streamCallbacks: ((data: { content: string; done: boolean }) => void)[] = [];
  private typingCallbacks: ((typing: boolean) => void)[] = [];
  private errorCallbacks: ((error: string) => void)[] = [];
  
  // Session management
  private currentSessionId: string = '';
  private selectedAgent: string = 'personal_agent';
  private isStreaming: boolean = false;
  private reconnectAttempts: number = 0;
  private isDisconnecting: boolean = false;
  
  // Health monitoring
  private healthStatus: any = null;
  private connectionStats: any = null;

  constructor() {
    this.initializeEnhancedService();
  }

  /**
   * Initialize enhanced WebSocket service
   */
  private initializeEnhancedService(): void {
    // Configure enhanced service for chat
    this.enhancedService = new EnhancedWebSocketService({
      enableMessageQueue: true,
      enableHealthMonitoring: true,
      enableAutoRecovery: true,
      maxConcurrentConnections: 3,
      messageTimeout: 30000, // Chat needs longer timeout
      batchConfig: {
        maxSize: 1, // No batching for chat - preserve message order
        maxWaitTime: 0,
        enableCompression: true
      }
    });

    // Set up migration helper
    this.migrationHelper = new WebSocketMigrationHelper({
      migrateChat: true,
      fallbackToLegacy: true,
      testMode: false
    });

    // Enhanced service event handlers
    this.enhancedService.on('connection_opened', (data: any) => {
      console.log('[EnhancedChatBackendClient] Enhanced service connected:', data);
      this.reconnectAttempts = 0;
      this.isDisconnecting = false;
      
      this.notifyStatus({
        connected: true,
        timestamp: new Date(),
        chat: { sessionId: this.generateSessionId() }
      });
      
      notificationService.success('Connected to enhanced agentic chat service');
    });

    // Also listen for legacy events for compatibility
    this.enhancedService.on('connected', (data: any) => {
      console.log('[EnhancedChatBackendClient] Enhanced service connected (legacy event):', data);
      this.reconnectAttempts = 0;
      this.isDisconnecting = false;
      
      this.notifyStatus({
        connected: true,
        timestamp: new Date(),
        chat: { sessionId: this.generateSessionId() }
      });
      
      notificationService.success('Connected to enhanced agentic chat service');
    });

    this.enhancedService.on('connection_closed', (data: any) => {
      console.log('[EnhancedChatBackendClient] Enhanced service disconnected:', data);
      
      this.notifyStatus({
        connected: false,
        timestamp: new Date(),
        chat: { sessionId: this.currentSessionId },
        error: 'Connection lost'
      });
    });

    this.enhancedService.on('disconnected', (data: any) => {
      console.log('[EnhancedChatBackendClient] Enhanced service disconnected (legacy event):', data);
      
      this.notifyStatus({
        connected: false,
        timestamp: new Date(),
        chat: { sessionId: this.currentSessionId },
        error: 'Connection lost'
      });
    });

    this.enhancedService.on('message', (data: any) => {
      if (data.connectionId === this.connectionId) {
        // Use rawData if available (original JSON string), otherwise stringify the parsed message
        const messageData = data.rawData || JSON.stringify(data.message);
        this.handleWebSocketMessage({ data: messageData });
      }
    });

    this.enhancedService.on('error', (error: any) => {
      console.error('[EnhancedChatBackendClient] Enhanced service error:', error);
      this.handleError(error.message || 'Unknown enhanced service error');
    });

    this.enhancedService.on('healthUpdate', (health: any) => {
      this.healthStatus = health;
      console.log('[EnhancedChatBackendClient] Health update:', health);
    });

    this.enhancedService.on('connectionClosed', (data: any) => {
      if (data.connectionId === this.connectionId) {
        console.log('[EnhancedChatBackendClient] Connection closed:', data);
        this.connectionId = null;
        
        this.notifyStatus({
          connected: false,
          timestamp: new Date(),
          chat: { sessionId: this.currentSessionId },
          error: data.reason || 'Connection closed'
        });
      }
    });
  }

  /**
   * Connect to enhanced chat service
   */
  async connectWebSocket(): Promise<boolean> {
    try {
      // Prevent multiple connection attempts
      if (this.connectionId && this.enhancedService) {
        console.warn('[EnhancedChatBackendClient] Enhanced service already connected');
        return true;
      }

      if (!this.enhancedService) {
        throw new Error('Enhanced service not initialized');
      }

      const options: ConnectionOptions = {
        serviceType: 'chat',
        sessionId: this.currentSessionId || this.generateSessionId(),
        autoReconnect: true,
        maxRetries: 5,
        priority: 'high',
        timeout: 15000
      };

      console.log('[EnhancedChatBackendClient] Connecting with options:', options);
      this.connectionId = await this.enhancedService.connect(options);
      console.log('[EnhancedChatBackendClient] Connected with ID:', this.connectionId);
      
      return true;
    } catch (error) {
      console.error('[EnhancedChatBackendClient] Enhanced connection failed:', error);
      
      // Fallback to legacy service
      if (this.migrationHelper) {
        console.log('[EnhancedChatBackendClient] Attempting fallback to legacy service');
        try {
          const legacyService = this.migrationHelper.getService('chat');
          // Use legacy service - would need to implement adapter
          console.warn('[EnhancedChatBackendClient] Using legacy service adapter');
        } catch (fallbackError) {
          console.error('[EnhancedChatBackendClient] Fallback also failed:', fallbackError);
        }
      }
      
      this.notifyStatus({
        connected: false,
        timestamp: new Date(),
        chat: { sessionId: this.currentSessionId },
        error: error instanceof Error ? error.message : 'Unknown connection error'
      });
      
      return false;
    }
  }

  /**
   * Send message with enhanced features
   */
  async sendMessage(
    content: string, 
    options?: {
      sessionId?: string;
      agentId?: string;
      agentType?: 'openai' | 'crewai' | 'langchain' | 'langgraph'; // Added for compatibility
      streaming?: boolean;
      priority?: 'low' | 'normal' | 'high' | 'critical';
      timeout?: number;
    }
  ): Promise<void> {
    if (!this.connectionId || !this.enhancedService) {
      throw new Error('Enhanced chat service not connected');
    }

    const sessionId = options?.sessionId || this.currentSessionId || this.generateSessionId();
    const agentId = options?.agentId || this.selectedAgent;
    const streaming = options?.streaming ?? true;

    const message = {
      type: 'chat',
      session_id: sessionId,
      content: content,
      agent_id: agentId,
      streaming: streaming,
      timestamp: new Date()
    };

    const messageOptions: MessageOptions = {
      priority: options?.priority || 'high',
      timeout: options?.timeout || 30000,
      expectResponse: true,
      retries: 2
    };

    try {
      console.log('[EnhancedChatBackendClient] Sending enhanced message:', message);
      
      await this.enhancedService.sendMessage(
        this.connectionId,
        JSON.stringify(message),
        messageOptions
      );
      
      this.isStreaming = streaming;
      
      // Update current session
      if (!this.currentSessionId) {
        this.currentSessionId = sessionId;
      }
      
    } catch (error) {
      console.error('[EnhancedChatBackendClient] Send message failed:', error);
      throw error;
    }
  }

  /**
   * Get available agents with enhanced caching
   */
  async getAgents(): Promise<AgentConfig[]> {
    if (!this.connectionId || !this.enhancedService) {
      throw new Error('Enhanced chat service not connected');
    }

    try {
      const message = {
        type: 'get_agents',
        timestamp: new Date()
      };

      await this.enhancedService.sendMessage(
        this.connectionId,
        JSON.stringify(message),
        {
          priority: 'normal',
          timeout: 10000,
          retries: 1
        }
      );

      // Note: Response handling would need to be implemented through message events
      // For now, return empty array as placeholder
      return [];
    } catch (error) {
      console.error('[EnhancedChatBackendClient] Get agents failed:', error);
      throw error;
    }
  }

  /**
   * Get chat configuration (legacy compatibility)
   */
  async getChatConfig(): Promise<any> {
    return {
      agentType: this.selectedAgent,
      model: 'gpt-4',
      temperature: 0.7
    };
  }

  /**
   * Get message history (legacy compatibility)
   */
  async getMessageHistory(maxMessages?: number): Promise<ChatMessage[]> {
    // Return empty array as placeholder - would need to implement message storage
    return [];
  }

  /**
   * Get agent status (legacy compatibility)
   */
  async getAgentStatus(): Promise<any> {
    return {
      connected: this.isConnected,
      agentId: this.selectedAgent,
      status: 'ready'
    };
  }

  /**
   * Clear messages (legacy compatibility)
   */
  async clearMessages(): Promise<void> {
    // Implementation would depend on message storage system
    console.log('[EnhancedChatBackendClient] Clear messages requested');
  }

  /**
   * Update chat configuration (legacy compatibility)
   */
  async updateChatConfig(newConfig: any): Promise<void> {
    if (newConfig.agentType) {
      this.selectedAgent = newConfig.agentType;
    }
  }

  /**
   * Create agent (legacy compatibility)
   */
  async createAgent(template: any, agentConfig: any): Promise<any> {
    if (!this.connectionId || !this.enhancedService) {
      throw new Error('Enhanced chat service not connected');
    }

    try {
      const message = {
        type: 'create_agent',
        template,
        config: agentConfig,
        timestamp: new Date()
      };

      await this.enhancedService.sendMessage(
        this.connectionId,
        JSON.stringify(message),
        {
          priority: 'normal',
          timeout: 15000,
          retries: 1
        }
      );

      return { success: true, agentId: `agent_${Date.now()}` };
    } catch (error) {
      console.error('[EnhancedChatBackendClient] Create agent failed:', error);
      throw error;
    }
  }

  /**
   * Execute agent task (legacy compatibility)
   */
  async executeAgentTask(agentId: string, task: any): Promise<void> {
    if (!this.connectionId || !this.enhancedService) {
      throw new Error('Enhanced chat service not connected');
    }

    try {
      const message = {
        type: 'execute_task',
        agent_id: agentId,
        task,
        timestamp: new Date()
      };

      await this.enhancedService.sendMessage(
        this.connectionId,
        JSON.stringify(message),
        {
          priority: 'high',
          timeout: 30000,
          retries: 1
        }
      );
    } catch (error) {
      console.error('[EnhancedChatBackendClient] Execute agent task failed:', error);
      throw error;
    }
  }

  /**
   * Handle WebSocket messages (adapted from original)
   */
  private handleWebSocketMessage(event: { data: string }): void {
    try {
      const data = JSON.parse(event.data);
      console.log('[EnhancedChatBackendClient] Message received:', data);
      
      if (data.type === 'message') {
        this.handleCompleteMessage(data);
      } else if (data.type === 'message_stream') {
        this.handleStreamingMessage(data);
      } else if (data.type === 'typing') {
        this.handleTypingIndicator(data);
      } else if (data.type === 'agent_status') {
        this.handleAgentStatus(data);
      } else if (data.type === 'error') {
        this.handleErrorMessage(data);
      }
    } catch (error) {
      console.error('[EnhancedChatBackendClient] Error parsing message:', error);
    }
  }

  private handleCompleteMessage(data: any): void {
    const message: ChatMessage = {
      id: data.message_id || Math.random().toString(36),
      role: data.role || 'assistant',
      content: data.content || '',
      timestamp: data.timestamp || Date.now(),
      sender: data.role === 'user' ? 'user' : 'ai', // Map role to sender
      metadata: {
        model: data.model,
        agent: data.agent_id,
        streaming: false,
        tokens: data.tokens,
        latency: data.latency
      }
    };
    
    this.messageCallbacks.forEach(callback => callback(message));
    this.isStreaming = false;
  }

  private handleStreamingMessage(data: any): void {
    this.streamCallbacks.forEach(callback => 
      callback({
        content: data.content || '',
        done: data.done || false
      })
    );
    
    if (data.done) {
      this.isStreaming = false;
    }
  }

  private handleTypingIndicator(data: any): void {
    this.typingCallbacks.forEach(callback => callback(data.typing || false));
  }

  private handleAgentStatus(data: any): void {
    console.log('[EnhancedChatBackendClient] Agent status:', data);
  }

  private handleErrorMessage(data: any): void {
    const error = data.error || 'Unknown chat error';
    console.error('[EnhancedChatBackendClient] Chat error:', error);
    this.handleError(error);
  }

  private handleError(error: string): void {
    this.errorCallbacks.forEach(callback => callback(error));
    notificationService.error(`Chat Error: ${error}`);
  }

  /**
   * Event subscription methods
   */
  onStatus(callback: (status: ChatStatus) => void): void;
  onStatus(callback: (status: ConnectionStatus) => void): void;
  onStatus(callback: ((status: ChatStatus) => void) | ((status: ConnectionStatus) => void)): void {
    // Create adapter for ConnectionStatus compatibility
    const adaptedCallback = (chatStatus: ChatStatus) => {
      // Check if callback expects ConnectionStatus by trying to call with converted status
      const connectionStatus: ConnectionStatus = {
        connected: chatStatus.connected,
        timestamp: chatStatus.timestamp.getTime(), // Convert Date to number
        agent: {
          available: chatStatus.connected,
          id: chatStatus.chat.agentId,
          name: chatStatus.chat.model,
        },
        chat: {
          sessionId: chatStatus.chat.sessionId,
        },
        error: chatStatus.error,
      };
      
      try {
        // Try to call with ConnectionStatus first
        (callback as (status: ConnectionStatus) => void)(connectionStatus);
      } catch {
        // Fallback to ChatStatus
        (callback as (status: ChatStatus) => void)(chatStatus);
      }
    };
    
    this.statusCallbacks.push(adaptedCallback);
  }

  onMessage(callback: (message: ChatMessage) => void): void {
    this.messageCallbacks.push(callback);
  }

  onStream(callback: (data: { content: string; done: boolean }) => void): void {
    this.streamCallbacks.push(callback);
  }

  onTyping(callback: (typing: boolean) => void): void {
    this.typingCallbacks.push(callback);
  }

  onError(callback: (error: string) => void): void {
    this.errorCallbacks.push(callback);
  }

  /**
   * Utility methods
   */
  private notifyStatus(status: ChatStatus): void {
    this.statusCallbacks.forEach(callback => callback(status));
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substring(2)}`;
  }

  /**
   * Getters for current state
   */
  get isConnected(): boolean {
    return this.connectionId !== null;
  }

  get currentSession(): string {
    return this.currentSessionId;
  }

  get selectedAgentId(): string {
    return this.selectedAgent;
  }

  get streamingStatus(): boolean {
    return this.isStreaming;
  }

  get healthMonitoring(): any {
    return this.healthStatus;
  }

  get connectionStatistics(): any {
    return this.connectionStats;
  }

  /**
   * Configuration methods
   */
  setSelectedAgent(agentId: string): void {
    this.selectedAgent = agentId;
  }

  setCurrentSession(sessionId: string): void {
    this.currentSessionId = sessionId;
  }

  /**
   * Disconnect and cleanup
   */
  async disconnect(): Promise<void> {
    this.isDisconnecting = true;
    
    if (this.connectionId && this.enhancedService) {
      try {
        await this.enhancedService.disconnect(this.connectionId);
      } catch (error) {
        console.warn('[EnhancedChatBackendClient] Disconnect error:', error);
      }
    }
    
    this.connectionId = null;
    this.currentSessionId = '';
    
    this.notifyStatus({
      connected: false,
      timestamp: new Date(),
      chat: { sessionId: '' }
    });
  }

  /**
   * Destroy service and cleanup
   */
  destroy(): void {
    this.disconnect();
    
    if (this.enhancedService) {
      try {
        this.enhancedService.destroy();
      } catch (error) {
        console.warn('[EnhancedChatBackendClient] Service destruction error:', error);
      }
    }
    
    // Clear callbacks
    this.statusCallbacks.length = 0;
    this.messageCallbacks.length = 0;
    this.streamCallbacks.length = 0;
    this.typingCallbacks.length = 0;
    this.errorCallbacks.length = 0;
  }
}

// Create singleton instance
export const enhancedChatBackendClient = new EnhancedChatBackendClient();
