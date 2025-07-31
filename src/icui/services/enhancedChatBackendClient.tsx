/**
 * Enhanced Chat Backend Client
 * 
 * Integrates all WebSocket improvements: connection management, error handling,
 * message queuing, health monitoring, and migration support for chat service.
 */

import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { EnhancedWebSocketService } from '../../services/enhanced-websocket-service';
import { log } from '../../services/frontend-logger';
import type { ConnectionOptions, MessageOptions } from '../../services/enhanced-websocket-service';
import type { ConnectionHealth } from '../../services/connection-manager';
import { notificationService } from './notificationService';
import { ConnectionStatus } from '../types/chatTypes';

// Local types for WebSocket messages
interface WebSocketMessage {
  type: string;
  data?: any;
  id?: string;
  timestamp?: string;
}

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
  
  // Streaming state management (like deprecated client)
  private streamingMessage: ChatMessage | null = null;
  private processedMessageIds: Set<string> = new Set();
  
  // Health monitoring
  private healthStatus: any = null;
  private connectionStats: any = null;

  constructor() {
    this.initializeEnhancedService();
    
    // Clean up old message IDs periodically to prevent memory leaks
    setInterval(() => {
      if (this.processedMessageIds.size > 1000) {
        // Keep only the most recent 500 message IDs
        const idsArray = Array.from(this.processedMessageIds);
        this.processedMessageIds.clear();
        // Add back the last 500
        idsArray.slice(-500).forEach(id => this.processedMessageIds.add(id));
      }
    }, 60000); // Clean up every minute
  }

  /**
   * Initialize enhanced WebSocket service
   */
  private initializeEnhancedService(): void {
    // Configure enhanced service for chat with minimal features to avoid disconnects
    this.enhancedService = new EnhancedWebSocketService({
      enableMessageQueue: false, // Disable queuing
      enableHealthMonitoring: false, // Disable health monitoring
      enableAutoRecovery: false, // Disable auto recovery
      maxConcurrentConnections: 1,
      messageTimeout: 60000, // Longer timeout
      batchConfig: {
        maxSize: 1,
        maxWaitTime: 0,
        enableCompression: false // Disable compression
      }
    });

    // Enhanced service event handlers
    this.enhancedService.on('connection_opened', (data: any) => {
      log.info('EnhancedChatBackendClient', 'Enhanced service connected', data);
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
      log.info('EnhancedChatBackendClient', 'Enhanced service connected (legacy event)', data);
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
      log.info('EnhancedChatBackendClient', 'Enhanced service disconnected', data);
      
      this.notifyStatus({
        connected: false,
        timestamp: new Date(),
        chat: { sessionId: this.currentSessionId },
        error: 'Connection lost'
      });
    });

    this.enhancedService.on('disconnected', (data: any) => {
      log.info('EnhancedChatBackendClient', 'Enhanced service disconnected (legacy event)', data);
      
      this.notifyStatus({
        connected: false,
        timestamp: new Date(),
        chat: { sessionId: this.currentSessionId },
        error: 'Connection lost'
      });
    });

    this.enhancedService.on('message', (data: any) => {
      // console.log('[EnhancedChatBackendClient] Raw message received:', data);
      if (data.connectionId === this.connectionId) {
        // Use rawData if available (original JSON string), otherwise stringify the parsed message
        const messageData = data.rawData || JSON.stringify(data.message);
        // console.log('[EnhancedChatBackendClient] Processing message for connectionId:', this.connectionId, 'data:', messageData);
        this.handleWebSocketMessage({ data: messageData });
      } else {
        // console.log('[EnhancedChatBackendClient] Message not for this connection:', data.connectionId, 'expected:', this.connectionId);
      }
    });

    this.enhancedService.on('error', (error: any) => {
      log.error('EnhancedChatBackendClient', 'Enhanced service error', { error });
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
        log.warn('EnhancedChatBackendClient', 'Enhanced service already connected');
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

      log.info('EnhancedChatBackendClient', 'Connecting with options', options);
      this.connectionId = await this.enhancedService.connect(options);
      log.info('EnhancedChatBackendClient', 'Connected with ID', { connectionId: this.connectionId });
      
      return true;
    } catch (error) {
      log.error('EnhancedChatBackendClient', 'Enhanced connection failed', { error });
      
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
    const agentType = options?.agentType || agentId; // Use explicit agentType if provided
    const streaming = options?.streaming ?? true;

    const message = {
      type: 'message', // Backend expects 'message', not 'chat'
      content: content,
      metadata: {
        session_id: sessionId,
        agentType: agentType, // Use the explicit agentType or fallback to agentId
        streaming: streaming,
        timestamp: new Date()
      }
    };

    const messageOptions: MessageOptions = {
      priority: 'normal', // Lower priority
      timeout: 60000, // Longer timeout
      expectResponse: false, // Don't expect response
      retries: 0 // No retries to avoid loops
    };

    try {
      // console.log('[EnhancedChatBackendClient] Sending enhanced message:', message);
      
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
      log.error('EnhancedChatBackendClient', 'Send message failed', { error });
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
    try {
      // Use HTTP API to get message history from chat.db
      const limit = maxMessages || 50;
      let baseUrl = (window as any).__ICUI_API_URL__ || 
                    (import.meta as any).env?.VITE_API_URL || 
                    `${window.location.protocol}//${window.location.host}`;
      
      // Remove trailing /api if present to avoid double /api in URL
      if (baseUrl.endsWith('/api')) {
        baseUrl = baseUrl.slice(0, -4);
      }
      
      const url = `${baseUrl}/api/chat/messages?limit=${limit}&offset=0`;
      // console.log('[EnhancedChatBackendClient] Fetching message history from:', url);
      
      const response = await fetch(url);
      
      if (!response.ok) {
        console.warn('[EnhancedChatBackendClient] Failed to fetch message history:', response.status);
        return [];
      }
      
      const result = await response.json();
      // console.log('[EnhancedChatBackendClient] Message history result:', result);
      
      const messages = result.data || [];
      
      return messages.map((msg: any) => ({
        id: msg.id,
        role: msg.sender === 'user' ? 'user' : 'assistant',
        content: msg.content,
        timestamp: new Date(msg.timestamp),
        sender: msg.sender,
        metadata: {
          agentId: msg.agentId,
          agentName: msg.agentName,
          agentType: msg.agentType,
          messageType: msg.messageType,
          workflowId: msg.workflowId,
          taskId: msg.taskId,
          capabilities: msg.capabilities,
          context: msg.context
        }
      }));
    } catch (error) {
      console.error('[EnhancedChatBackendClient] Failed to load message history:', error);
      return [];
    }
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
    try {
      // Use HTTP API to clear message history - use POST to /api/chat/clear like deprecated client
      let baseUrl = (window as any).__ICUI_API_URL__ || 
                    (import.meta as any).env?.VITE_API_URL || 
                    `${window.location.protocol}//${window.location.host}`;
      
      // Remove trailing /api if present to avoid double /api in URL
      if (baseUrl.endsWith('/api')) {
        baseUrl = baseUrl.slice(0, -4);
      }
      
      const url = `${baseUrl}/api/chat/clear`;
      // console.log('[EnhancedChatBackendClient] Clearing messages at:', url);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (!response.ok) {
        throw new Error(`Failed to clear messages: ${response.status} ${response.statusText}`);
      }
      
      // console.log('[EnhancedChatBackendClient] Messages cleared successfully');
    } catch (error) {
      console.error('[EnhancedChatBackendClient] Failed to clear messages:', error);
      throw error;
    }
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
      // console.log('[EnhancedChatBackendClient] handleWebSocketMessage called with:', event.data);
      
      // Check if event.data is valid before parsing
      if (!event.data || event.data === 'undefined' || typeof event.data !== 'string') {
        console.warn('[EnhancedChatBackendClient] Invalid message data received:', event.data);
        return;
      }

      const data = JSON.parse(event.data);
      // console.log('[EnhancedChatBackendClient] Message parsed:', data);
      
      if (data.type === 'message') {
        // console.log('[EnhancedChatBackendClient] Handling complete message');
        this.handleCompleteMessage(data);
      } else if (data.type === 'message_stream') {
        // console.log('[EnhancedChatBackendClient] Handling streaming message');
        this.handleStreamingMessage(data);
      } else if (data.type === 'typing') {
        // console.log('[EnhancedChatBackendClient] Handling typing indicator');
        this.handleTypingIndicator(data);
      } else if (data.type === 'agent_status') {
        // console.log('[EnhancedChatBackendClient] Handling agent status');
        this.handleAgentStatus(data);
      } else if (data.type === 'error') {
        // console.log('[EnhancedChatBackendClient] Handling error message');
        this.handleErrorMessage(data);
      } else {
        // console.log('[EnhancedChatBackendClient] Unknown message type:', data.type, 'full data:', data);
      }
    } catch (error) {
      console.error('[EnhancedChatBackendClient] Error parsing message:', error, 'raw data:', event.data);
    }
  }

  private handleCompleteMessage(data: any): void {
    const messageId = data.id || Math.random().toString(36);
    
    // Skip if we've already processed this message ID via streaming
    if (this.processedMessageIds.has(messageId)) {
      // console.log('[EnhancedChatBackendClient] Skipping duplicate complete message:', messageId);
      return;
    }
    
    const message: ChatMessage = {
      id: messageId,
      role: data.role || 'assistant',
      content: data.content || '',
      timestamp: new Date(data.timestamp || Date.now()),
      sender: data.role === 'user' ? 'user' : 'ai', // Map role to sender
      metadata: {
        agentId: data.agentId,
        agentName: data.agentName,
        agentType: data.agentType,
        messageType: data.messageType || 'text',
        model: data.model,
        agent: data.agent_id,
        streaming: false,
        tokens: data.tokens,
        latency: data.latency,
        isStreaming: false,
        streamComplete: true
      }
    };
    
    // Mark this message ID as processed
    this.processedMessageIds.add(messageId);
    
    // Don't notify callbacks for user messages (they're echoed back from backend)
    // The UI already shows user messages when they're sent
    if (message.sender === 'user') {
      // console.log('[EnhancedChatBackendClient] Ignoring user message echo:', messageId);
      return;
    }
    
    this.messageCallbacks.forEach(callback => callback(message));
    this.isStreaming = false;
  }

  private handleStreamingMessage(data: any): void {
    // console.log('[EnhancedChatBackendClient] Streaming message data:', data);
    
    if (data.stream_start) {
      // Start new streaming message
      const messageId = data.id || Date.now().toString();
      // console.log('[EnhancedChatBackendClient] Starting streaming message:', messageId);
      
      // Mark this message ID as processed to prevent duplicate complete messages
      this.processedMessageIds.add(messageId);
      
      this.streamingMessage = {
        id: messageId,
        content: '',
        role: 'assistant',
        sender: 'ai',
        timestamp: new Date(),
        metadata: {
          agentId: data.agentId,
          agentName: data.agentName,
          agentType: data.agentType,
          messageType: 'streaming',
          isStreaming: true,
          streamComplete: false
        }
      };
      
      this.messageCallbacks.forEach(callback => callback(this.streamingMessage!));
      this.isStreaming = true;
      
    } else if (data.stream_chunk && this.streamingMessage) {
      // Append chunk to streaming message
      // console.log('[EnhancedChatBackendClient] Appending chunk:', data.chunk);
      this.streamingMessage.content += data.chunk;
      this.messageCallbacks.forEach(callback => callback({ 
        ...this.streamingMessage!,
        metadata: {
          ...this.streamingMessage!.metadata!,
          isStreaming: true
        }
      }));
      
      // Also call stream callbacks for backward compatibility
      this.streamCallbacks.forEach(callback => 
        callback({
          content: data.chunk || '',
          done: false
        })
      );
      
    } else if (data.stream_end && this.streamingMessage) {
      // Complete streaming message
      // console.log('[EnhancedChatBackendClient] Ending streaming message:', this.streamingMessage.id);
      this.streamingMessage.metadata!.streamComplete = true;
      this.streamingMessage.metadata!.isStreaming = false;
      this.messageCallbacks.forEach(callback => callback({ 
        ...this.streamingMessage!,
        metadata: {
          ...this.streamingMessage!.metadata!,
          isStreaming: false,
          streamComplete: true
        }
      }));
      
      // Call stream callbacks with done flag
      this.streamCallbacks.forEach(callback => 
        callback({
          content: '',
          done: true
        })
      );
      
      this.streamingMessage = null;
      this.isStreaming = false;
    } else {
      console.warn('[EnhancedChatBackendClient] ⚠️ Unhandled streaming message:', data);
      
      // Fallback to old streaming format for compatibility
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
  }

  private handleTypingIndicator(data: any): void {
    this.typingCallbacks.forEach(callback => callback(data.typing || false));
  }

  private handleAgentStatus(data: any): void {
    console.log('[EnhancedChatBackendClient] Agent status:', data);
  }

  private handleErrorMessage(data: any): void {
    const error = data.error || 'Unknown chat error';
      log.error('EnhancedChatBackendClient', 'Chat error', { error });
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
   * Helper method to notify message callbacks (like deprecated client)
   */
  private notifyMessage(message: ChatMessage): void {
    this.messageCallbacks.forEach(callback => callback(message));
  }

  /**
   * Helper method to notify status callbacks  
   */
  private notifyStatus(status: ChatStatus): void {
    this.statusCallbacks.forEach(callback => callback(status));
  }

  /**
   * Utility methods
   */
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

// Compatibility exports for existing code
export { EnhancedChatBackendClient as ChatBackendClient };
export const chatBackendClient = enhancedChatBackendClient;
