/**
 * Chat Backend Client
 * 
 * Integrates all WebSocket improvements: connection management, error handling,
 * message queuing, health monitoring, and migration support for chat service.
 */

import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { WebSocketService } from '../../services/websocket-service-impl';
import { log } from '../../services/frontend-logger';
import { configService } from '../../services/config-service';
import type { ConnectionOptions, MessageOptions } from '../../services/websocket-service-impl';
import type { ConnectionHealth } from '../../services/connection-manager';
import { notificationService } from './notificationService';
import { ConnectionStatus } from '../types/chatTypes';

// Local types for WebSocket messages
interface WebSocketMessage {
  type: string;
  data?: any;
  id?: string;
}

// Tool call event data interface for type safety
interface ToolCallEventData {
  type?: 'tool_call_start' | 'tool_call_progress' | 'tool_call_complete' | 'tool_call_error' | string;
  toolId?: string;
  id?: string;
  toolName?: string;
  name?: string;
  category?: 'file' | 'code' | 'data' | 'network' | 'custom';
  status?: 'pending' | 'running' | 'success' | 'error';
  progress?: number;
  input?: any;
  output?: any;
  result?: any;
  error?: string;
  startedAt?: string | Date;
  endedAt?: string | Date;
  metadata?: Record<string, any>;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  sender: 'user' | 'ai' | 'system';
  metadata?: {
    // Session correlation (used for replay buffering + history merge)
    session_id?: string;
    sessionId?: string;
    session?: string;
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
    error?: boolean;  // Flag to indicate this is an error message
    // For backward compatibility
    model?: string;
    agent?: string;
    streaming?: boolean;
    tokens?: number;
    latency?: number;
    toolCalls?: any[]; // Added for tool calls
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

export class ChatBackendClient {
  private wsService: WebSocketService | null = null;
  private connectionId: string | null = null;
  
  // Event handlers
  private statusCallbacks: ((status: ChatStatus) => void)[] = [];
  private messageCallbacks: ((message: ChatMessage) => void)[] = [];
  private streamCallbacks: ((data: { content: string; done: boolean }) => void)[] = [];
  private typingCallbacks: ((typing: boolean) => void)[] = [];
  private errorCallbacks: ((error: string) => void)[] = [];

  // Replay buffer for late subscribers.
  // Important: we keep this even when there are already subscribers, because the chat panel
  // may mount later than another consumer and would otherwise miss messages until refresh.
  // Key format: `${sessionKey}:${messageId}`.
  private pendingMessages: Map<string, ChatMessage> = new Map();
  private pendingMessageOrder: string[] = [];
  private readonly maxPendingMessages: number = 300;
  
  // Session management
  private currentSessionId: string = '';
  private selectedAgent: string = 'personal_agent';
  private isStreaming: boolean = false;
  private reconnectAttempts: number = 0;
  private isDisconnecting: boolean = false;
  // Client-side interrupt flag to immediately stop processing incoming stream chunks
  private stopRequested: boolean = false;
  
  // Streaming state management (like deprecated client)
  private streamingMessage: ChatMessage | null = null;
  private processedMessageIds: Set<string> = new Set();
 
  // Tool-call tracking
  private toolCallState: Map<string, any> = new Map();
  private toolMessageIds: Map<string, string> = new Map();
  
  // Health monitoring
  private healthStatus: any = null;
  private connectionStats: any = null;

  constructor() {
    this.initializeWebSocketService();
    
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

  private isSurgicalIterateEnabled(): boolean {
    try {
      const g: any = typeof globalThis !== 'undefined' ? globalThis : undefined;
      const forced = Boolean(g && (g as any).__ICOTES_SURGICAL_ITERATE__);
      const ls = g && (g as any).localStorage;
      const flag = ls && typeof ls.getItem === 'function' ? ls.getItem('icotes:surgicaliterate') : null;
      return forced || flag === '1' || flag === 'true';
    } catch {
      return false;
    }
  }

  private getSessionKeyForMessage(message: ChatMessage): string {
    try {
      const meta: any = (message as any).metadata || {};
      const raw = meta.session_id || meta.sessionId || meta.session || '';
      const key = String(raw || '').trim();
      return key || this.currentSessionId || 'unknown';
    } catch {
      return this.currentSessionId || 'unknown';
    }
  }

  private makePendingKey(sessionKey: string, messageId: string): string {
    const sk = sessionKey || 'unknown';
    const mid = messageId || '';
    return `${sk}:${mid}`;
  }

  /**
   * Initialize WebSocket service
   */
  private initializeWebSocketService(): void {
    // Configure service for chat with minimal features to avoid disconnects
    this.wsService = new WebSocketService({
      enableMessageQueue: false, // Disable queuing
      enableHealthMonitoring: false, // Disable health monitoring
      enableAutoRecovery: false, // Disable auto recovery
      maxConcurrentConnections: 10, // Increased from 1 to allow multiple tabs/sessions
      messageTimeout: 60000, // Longer timeout
      batchConfig: {
        maxSize: 1,
        maxWaitTime: 0,
        enableCompression: false // Disable compression
      }
    });

    // Service event handlers
    this.wsService.on('connection_opened', (data: any) => {
      log.debug('ChatBackendClient', 'Service connected', data);
      if (process.env.NODE_ENV === 'development') {
        console.log('[ChatBackendClient] Connection opened:', data);
      }
      this.reconnectAttempts = 0;
      this.isDisconnecting = false;
      
      this.notifyStatus({
        connected: true,
        timestamp: new Date(),
        chat: { sessionId: this.generateSessionId() }
      });

      notificationService.success('Connected to chat service', { key: 'chat:connected' });
    });

    // Also listen for legacy events for compatibility
    this.wsService.on('connected', (data: any) => {
      log.debug('ChatBackendClient', 'Service connected (legacy event)', data);
      this.reconnectAttempts = 0;
      this.isDisconnecting = false;
      
      this.notifyStatus({
        connected: true,
        timestamp: new Date(),
        chat: { sessionId: this.generateSessionId() }
      });

      notificationService.success('Connected to agentic chat service', { key: 'chat:connected' });
    });

    this.wsService.on('connection_closed', (data: any) => {
      log.debug('ChatBackendClient', 'Service disconnected', data);
      if (process.env.NODE_ENV === 'development') {
        console.log('[ChatBackendClient] Connection closed:', data);
      }
      
      this.notifyStatus({
        connected: false,
        timestamp: new Date(),
        chat: { sessionId: this.currentSessionId },
        error: 'Connection lost'
      });
    });

    this.wsService.on('disconnected', (data: any) => {
      log.debug('ChatBackendClient', 'Service disconnected (legacy event)', data);
      
      this.notifyStatus({
        connected: false,
        timestamp: new Date(),
        chat: { sessionId: this.currentSessionId },
        error: 'Connection lost'
      });
    });

    this.wsService.on('message', (data: any) => {
      if (data.connectionId === this.connectionId) {
        // Use rawData if available (original JSON string), otherwise stringify the parsed message
        const messageData = data.rawData || JSON.stringify(data.message);
        this.handleWebSocketMessage({ data: messageData });
      }
    });

    this.wsService.on('error', (error: any) => {
      log.error('ChatBackendClient', 'Service error', { error });
      this.handleError(error.message || 'Unknown service error');
    });

    this.wsService.on('healthUpdate', (health: any) => {
      this.healthStatus = health;
      // Reduced debug: Only log health issues, not routine updates
      if (health.status === 'unhealthy') {
        console.log('[ChatBackendClient] Health issue:', health);
      }
    });

    this.wsService.on('connectionClosed', (data: any) => {
      if (data.connectionId === this.connectionId) {
        // Reduced debug: Only log unexpected connection closures
        if (data.reason && data.reason !== 'normal closure') {
          console.log('[ChatBackendClient] Unexpected connection closure:', data);
        }
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
   * Connect to chat service
   */
  async connectWebSocket(): Promise<boolean> {
    try {
      // Prevent multiple connection attempts
      if (this.connectionId && this.wsService) {
        log.warn('ChatBackendClient', 'Service already connected');
        return true;
      }

      if (!this.wsService) {
        throw new Error('Service not initialized');
      }

      const options: ConnectionOptions = {
        serviceType: 'chat',
        sessionId: this.currentSessionId || this.generateSessionId(),
        autoReconnect: true,
        maxRetries: 5,
        priority: 'high',
        timeout: 15000
      };

      log.info('ChatBackendClient', 'Connecting with options', options);
      this.connectionId = await this.wsService.connect(options);
      log.info('ChatBackendClient', 'Connected with ID', { connectionId: this.connectionId });
      
      return true;
    } catch (error) {
      log.error('ChatBackendClient', 'Service connection failed', { error });
      
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
   * Send message with features
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
      // Phase 2: media attachments (pass-through, backend normalizes)
      attachments?: any[];
    }
  ): Promise<void> {
    if (!this.connectionId || !this.wsService) {
      throw new Error('Chat service not connected');
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
        timestamp: new Date(),
        // Include attachments if provided; backend will normalize
        attachments: options?.attachments && Array.isArray(options.attachments) ? options.attachments : undefined
      }
    };

    const messageOptions: MessageOptions = {
      priority: 'normal', // Lower priority
      timeout: 60000, // Longer timeout
      expectResponse: false, // Don't expect response
      retries: 0 // No retries to avoid loops
    };

    try {
      // console.log('[ChatBackendClient] Sending message:', message);
      
      await this.wsService.sendMessage(
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
      log.error('ChatBackendClient', 'Send message failed', { error });
      throw error;
    }
  }

  /**
   * Stop/interrupt current streaming response
   */
  async stopStreaming(): Promise<void> {
    if (!this.connectionId || !this.wsService) {
      throw new Error('Chat service not connected');
    }

    // Set client-side interrupt so UI stops immediately even if backend delays
    this.stopRequested = true;
    // Also proactively update local streaming state
    if (this.isStreaming) {
      this.handleStreamStopped({ message: 'Client interrupt requested' });
    }

    const stopMessage = {
      type: 'stop',
      session_id: this.currentSessionId,
      timestamp: new Date().toISOString()
    };

    const messageOptions: MessageOptions = {
      priority: 'high', // High priority for stop messages
      timeout: 5000, // Short timeout
      expectResponse: false,
      retries: 0
    };

    try {
      await this.wsService.sendMessage(
        this.connectionId,
        JSON.stringify(stopMessage),
        messageOptions
      );
    } catch (error) {
      console.error('[ChatBackendClient] Failed to stop streaming:', error);
      // Even if sending the stop message fails, keep the local interrupt behavior
      this.handleError('Failed to send stop signal; stream already stopped locally.');
    }
  }

  /**
   * Get available agents with caching
   */
  async getAgents(): Promise<AgentConfig[]> {
    if (!this.connectionId || !this.wsService) {
      throw new Error('Chat service not connected');
    }

    try {
      const message = {
        type: 'get_agents',
        timestamp: new Date()
      };

      await this.wsService.sendMessage(
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
      console.error('[ChatBackendClient] Get agents failed:', error);
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
  async getMessageHistory(maxMessages?: number, sessionId?: string): Promise<ChatMessage[]> {
    try {
      // Use HTTP API to get message history from chat.db
      const limit = maxMessages || 50;
      
      // Use config service for dynamic API URL resolution (prioritizes backend /api/config)
      let baseUrl: string;
      try {
        const config = await configService.getConfig();
        baseUrl = config.api_url || config.base_url;
      } catch (error) {
        console.warn('[ChatBackendClient] Failed to get config, using fallbacks:', error);
        // Fallback to environment variables
        baseUrl = (window as any).__ICUI_API_URL__ || 
                  (import.meta as any).env?.VITE_API_URL || 
                  (import.meta as any).env?.VITE_BACKEND_URL ||
                  `${window.location.protocol}//${window.location.host}`;
      }
      
      // Remove trailing /api if present to avoid double /api in URL
      if (baseUrl.endsWith('/api')) {
        baseUrl = baseUrl.slice(0, -4);
      }
      
      const params = new URLSearchParams({ limit: String(limit), offset: '0' });
      const effectiveSession = sessionId || this.currentSessionId;
      if (effectiveSession) params.set('session_id', effectiveSession);
      const url = `${baseUrl}/api/chat/messages?${params.toString()}`;
      
      const response = await fetch(url);
      
      if (!response.ok) {
        console.warn('[ChatBackendClient] Failed to fetch message history:', response.status);
        return [];
      }
      
      const result = await response.json();
      const messages = result.data || [];
      
      return messages.map((msg: any) => ({
        id: msg.id,
        role: msg.sender === 'user' ? 'user' : 'assistant',
        content: msg.content,
        timestamp: new Date(msg.timestamp),
        sender: msg.sender,
        // Map attachments if present (backend stores as list of dicts)
        attachments: Array.isArray(msg.attachments) ? msg.attachments.map((a: any) => ({
          id: a.id || a.attachment_id || a.rel_path || a.path || String(Math.random()),
          kind: a.kind === 'images' ? 'image' : (a.kind === 'audio' ? 'audio' : 'file'),
          path: a.relative_path || a.rel_path || a.path || a.url || '',
          mime: a.mime_type || a.mime || 'application/octet-stream',
          size: a.size_bytes || a.size || 0,
          meta: (() => {
            const m = a.meta && typeof a.meta === 'object' ? { ...a.meta } : {};
            if (a.filename && !m.filename) m.filename = a.filename;
            // Mark explorer refs by id/path heuristics
            if (typeof (a.id || '') === 'string' && String(a.id).startsWith('explorer-')) {
              (m as any).source = 'explorer';
            }
            return Object.keys(m).length ? m : undefined;
          })()
        })) : undefined,
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
      console.error('[ChatBackendClient] Failed to load message history:', error);
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
      
      // Use config service for dynamic API URL resolution (prioritizes backend /api/config)
      let baseUrl: string;
      try {
        const config = await configService.getConfig();
        baseUrl = config.api_url || config.base_url;
      } catch (error) {
        console.warn('[ChatBackendClient] Failed to get config, using fallbacks:', error);
        // Fallback to environment variables
        baseUrl = (window as any).__ICUI_API_URL__ || 
                  (import.meta as any).env?.VITE_API_URL || 
                  (import.meta as any).env?.VITE_BACKEND_URL ||
                  `${window.location.protocol}//${window.location.host}`;
      }
      
      // Remove trailing /api if present to avoid double /api in URL
      if (baseUrl.endsWith('/api')) {
        baseUrl = baseUrl.slice(0, -4);
      }
      
      const params = new URLSearchParams();
      if (this.currentSessionId) {
        params.set('session_id', this.currentSessionId);
      }
      const url = `${baseUrl}/api/chat/clear?${params.toString()}`;
      // console.log('[ChatBackendClient] Clearing messages at:', url);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (!response.ok) {
        throw new Error(`Failed to clear messages: ${response.status} ${response.statusText}`);
      }
      
      // console.log('[ChatBackendClient] Messages cleared successfully');
    } catch (error) {
      console.error('[ChatBackendClient] Failed to clear messages:', error);
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
    if (!this.connectionId || !this.wsService) {
      throw new Error('Chat service not connected');
    }

    try {
      const message = {
        type: 'create_agent',
        template,
        config: agentConfig,
        timestamp: new Date()
      };

      await this.wsService.sendMessage(
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
      console.error('[ChatBackendClient] Create agent failed:', error);
      throw error;
    }
  }

  /**
   * Execute agent task (legacy compatibility)
   */
  async executeAgentTask(agentId: string, task: any): Promise<void> {
    if (!this.connectionId || !this.wsService) {
      throw new Error('Chat service not connected');
    }

    try {
      const message = {
        type: 'execute_task',
        agent_id: agentId,
        task,
        timestamp: new Date()
      };

      await this.wsService.sendMessage(
        this.connectionId,
        JSON.stringify(message),
        {
          priority: 'high',
          timeout: 30000,
          retries: 1
        }
      );
    } catch (error) {
      console.error('[ChatBackendClient] Execute agent task failed:', error);
      throw error;
    }
  }

  /**
   * Handle WebSocket messages (adapted from original)
   */
  private handleWebSocketMessage(event: { data: string }): void {
    try {
      console.log('[ChatBackendClient] handleWebSocketMessage called with type:', JSON.parse(event.data)?.type);
      
      // Check if event.data is valid before parsing
      if (!event.data || event.data === 'undefined' || typeof event.data !== 'string') {
        console.warn('[ChatBackendClient] Invalid message data received:', event.data);
        return;
      }

      const data = JSON.parse(event.data);
      // console.log('[ChatBackendClient] Message parsed:', data);
      
      if (data.type === 'message') {
        this.handleCompleteMessage(data);
      } else if (data.type === 'message_stream') {
        console.log('[ChatBackendClient] Streaming message:', data.stream_start ? 'START' : data.stream_chunk ? 'CHUNK' : 'END');
        this.handleStreamingMessage(data);
      } else if (data.type === 'stream_stopped') {
        // console.log('[ChatBackendClient] Handling stream stopped');
        this.handleStreamStopped(data);
      } else if (data.type === 'typing') {
        // console.log('[ChatBackendClient] Handling typing indicator');
        this.handleTypingIndicator(data);
      } else if (data.type === 'agent_status') {
        // console.log('[ChatBackendClient] Handling agent status');
        this.handleAgentStatus(data);
      } else if (data.type === 'error') {
        // console.log('[ChatBackendClient] Handling error message');
        this.handleErrorMessage(data);
      } else if (data.type === 'connected' && (data.session_id || data.sessionId)) {
        // Capture session id on handshake
        const sessionId = data.session_id || data.sessionId;
        if (sessionId && !this.currentSessionId) {
          this.currentSessionId = String(sessionId);
        }
        this.notifyStatus({
          connected: true,
          timestamp: new Date(),
          chat: { sessionId: this.currentSessionId || String(sessionId) }
        });
      } else if (data.type === 'config' && data.config?.session_id) {
        // Some backends send session id with config
        if (!this.currentSessionId) {
          this.currentSessionId = String(data.config.session_id);
        }
      } else if (
        data.type === 'tool_call_start' ||
        data.type === 'tool_call_progress' ||
        data.type === 'tool_call_complete' ||
        data.type === 'tool_call_error'
      ) {
        this.handleToolCallEvent(data);
      } else {
        // console.log('[ChatBackendClient] Unknown message type:', data.type, 'full data:', data);
      }
    } catch (error) {
      console.error('[ChatBackendClient] Error parsing message:', error, 'raw data:', event.data);
    }
  }

  private handleCompleteMessage(data: any): void {
    const messageId = data.id || Math.random().toString(36);
    
    // Skip if we've already processed this message ID via streaming
    if (this.processedMessageIds.has(messageId)) {
      // console.log('[ChatBackendClient] Skipping duplicate complete message:', messageId);
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
      // console.log('[ChatBackendClient] Ignoring user message echo:', messageId);
      return;
    }
    
    this.notifyMessage(message);
    this.isStreaming = false;
  }

  private handleStreamingMessage(data: any): void {
    // If we've been interrupted (stopRequested), ignore further chunks/ends
    // Don't check isStreaming here because stream_chunk may arrive before stream_start
    if (this.stopRequested && (data.stream_chunk || data.stream_end)) {
      // Silently ignore to prevent UI flicker
      return;
    }
    
    // Normalize common fields that may arrive from older backends
    const chunkText: string = (data.chunk ?? data.content ?? '') as string;
    const msgId: string = String(data.id || Date.now());

    if (data.stream_start) {
  // Reset any prior stop request on new stream
  this.stopRequested = false;
      // Start new streaming message
      const messageId = msgId;
      
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
      
      this.notifyMessage(this.streamingMessage!);
      this.isStreaming = true;
      
    } else if (data.stream_chunk) {
      // If a chunk arrives before start due to network reordering, initialize lazily
      if (!this.streamingMessage) {
        // Create a streaming message on-the-fly so the UI shows the typing indicator
        this.streamingMessage = {
          id: msgId,
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
        this.notifyMessage(this.streamingMessage!);
        this.isStreaming = true;
        // track to avoid duplicate complete messages
        this.processedMessageIds.add(msgId);
      }
      // If a stop was requested, ignore further chunks and finalize locally
      if (this.stopRequested) {
        this.handleStreamStopped({ message: 'Client interrupted during streaming' });
        return;
      }
      // Append chunk to streaming message
      this.streamingMessage.content += chunkText || '';
      this.notifyMessage({
        ...this.streamingMessage!,
        metadata: {
          ...this.streamingMessage!.metadata!,
          isStreaming: true
        }
      });
      
      // Also call stream callbacks for backward compatibility
      this.streamCallbacks.forEach(callback => 
        callback({
          content: chunkText || '',
          done: false
        })
      );
      
    } else if (data.stream_end) {
      // If end arrives without an open streaming message, create and complete a minimal one
      if (!this.streamingMessage) {
        this.streamingMessage = {
          id: msgId,
          content: '',
          role: 'assistant',
          sender: 'ai',
          timestamp: new Date(),
          metadata: {
            agentId: data.agentId,
            agentName: data.agentName,
            agentType: data.agentType,
            messageType: 'streaming',
            isStreaming: false,
            streamComplete: true
          }
        };
        this.processedMessageIds.add(msgId);
      }
      // Complete streaming message
      // console.log('[ChatBackendClient] Ending streaming message:', this.streamingMessage.id);
      this.streamingMessage.metadata!.streamComplete = true;
      this.streamingMessage.metadata!.isStreaming = false;
      
      // Force immediate notification to ensure message appears without refresh
      const finalMessage = {
        ...this.streamingMessage!,
        metadata: {
          ...this.streamingMessage!.metadata!,
          isStreaming: false,
          streamComplete: true
        }
      };

      // Go through notifyMessage so late subscribers can replay this final state
      this.notifyMessage(finalMessage);
      
      // Call stream callbacks with done flag
      this.streamCallbacks.forEach(callback => 
        callback({
          content: '',
          done: true
        })
      );
      
      this.streamingMessage = null;
      this.isStreaming = false;
      this.stopRequested = false;
    } else {
      // As a last resort, treat messages with content/chunk as legacy stream events
      if (typeof chunkText === 'string' && chunkText.length > 0) {
        // Create a minimal streaming message to surface content
        if (!this.streamingMessage) {
          this.streamingMessage = {
            id: msgId,
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
          this.notifyMessage(this.streamingMessage!);
          this.isStreaming = true;
          this.processedMessageIds.add(msgId);
        }
        this.streamingMessage.content += chunkText;
        // Go through notifyMessage so it is replayable for late subscribers
        this.notifyMessage({ ...this.streamingMessage! });
        // Do not end here; wait for an explicit end or next phase
      } else {
        console.warn('[ChatBackendClient] ⚠️ Unhandled streaming message:', data);
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
  }

  private handleStreamStopped(data: any): void {
    // Handle stream interruption
    this.isStreaming = false;
    this.streamingMessage = null;
    // Keep stopRequested=true after a client interrupt so stray chunks are ignored
    
    // Notify typing stopped
    this.typingCallbacks.forEach(callback => callback(false));
    
    // Notify stream callbacks that streaming is done
    this.streamCallbacks.forEach(callback => 
      callback({
        content: '',
        done: true
      })
    );
    
    // Log the stop event
    console.log('[ChatBackendClient] Stream stopped:', data.message || 'Streaming interrupted');
  }

  private handleTypingIndicator(data: any): void {
    this.typingCallbacks.forEach(callback => callback(data.is_typing ?? data.typing ?? false));
  }

  private handleAgentStatus(data: any): void {
    console.log('[ChatBackendClient] Agent status:', data);
  }

  private handleErrorMessage(data: any): void {
    const error = data.error || data.message || 'Unknown chat error';
    log.error('ChatBackendClient', 'Chat error', { error });
    
    // Create a visible error message in the chat
    const errorMessage: ChatMessage = {
      id: `error_${Date.now()}_${Math.random().toString(36).substring(2)}`,
      role: 'assistant',
      sender: 'ai',
      content: `Error: ${typeof error === 'object' ? JSON.stringify(error, null, 2) : error}`,
      timestamp: new Date(),
      metadata: {
        messageType: 'error',
        isStreaming: false,
        streamComplete: true,
        error: true
      }
    };
    
    // Go through notifyMessage so late subscribers can replay
    this.notifyMessage(errorMessage);
    
    // Also call error callbacks
    this.handleError(typeof error === 'object' ? JSON.stringify(error) : error);
    
    // End any active streaming
    if (this.streamingMessage) {
      this.streamingMessage.metadata!.streamComplete = true;
      this.streamingMessage.metadata!.isStreaming = false;
      this.notifyMessage({ ...this.streamingMessage! });
      this.streamingMessage = null;
    }
    this.isStreaming = false;
    this.typingCallbacks.forEach(callback => callback(false));
  }

  private handleError(error: string): void {
    this.errorCallbacks.forEach(callback => callback(error));
    notificationService.error(`Chat Error: ${error}`);
  }

  private handleToolCallEvent(data: ToolCallEventData): void {
    const toolId = String(data.toolId || data.id || `tool_${Date.now()}`);
    const toolName = String(data.toolName || data.name || 'Tool');
    const category = data.category || 'custom';
    const now = new Date();
    const existing = this.toolCallState.get(toolId) || {};
    let status: 'pending' | 'running' | 'success' | 'error' = existing.status || 'pending';
    let progress: number | undefined = existing.progress;
    let output = existing.output;
    let error = existing.error;
    let startedAt: Date | string | undefined = existing.startedAt;
    let endedAt: Date | string | undefined = existing.endedAt;

    if (data.type === 'tool_call_start') {
      status = 'running';
      progress = typeof data.progress === 'number' ? data.progress : 0;
      startedAt = now.toISOString();
    } else if (data.type === 'tool_call_progress') {
      status = 'running';
      if (typeof data.progress === 'number') progress = data.progress;
    } else if (data.type === 'tool_call_complete') {
      status = 'success';
      progress = typeof data.progress === 'number' ? data.progress : 100;
      output = data.result ?? data.output;
      endedAt = now.toISOString();
    } else if (data.type === 'tool_call_error') {
      status = 'error';
      error = String(data.error || 'Unknown tool error');
      endedAt = now.toISOString();
    }

    const toolMeta = {
      id: toolId,
      toolName,
      status,
      progress,
      input: data.input,
      output,
      error,
      category,
      startedAt,
      endedAt,
      metadata: data.metadata || {}
    };

    // Update state
    this.toolCallState.set(toolId, toolMeta);

    if (this.streamingMessage) {
      // Attach to current streaming message
      const currentToolCalls = (this.streamingMessage.metadata as any)?.toolCalls as any[] | undefined;
      let toolCalls: any[] = Array.isArray(currentToolCalls) ? [...currentToolCalls] : [];
      const idx = toolCalls.findIndex(tc => tc.id === toolId);
      if (idx >= 0) toolCalls[idx] = toolMeta; else toolCalls.push(toolMeta);

      this.streamingMessage = {
        ...this.streamingMessage,
        metadata: {
          ...(this.streamingMessage.metadata || {}),
          toolCalls
        }
      };

      // Emit updated streaming message
      this.notifyMessage(this.streamingMessage!);
    } else {
      // Emit or update a synthetic tool message
      const existingMessageId = this.toolMessageIds.get(toolId);
      const syntheticMessageId = existingMessageId || `tool_${toolId}`;
      this.toolMessageIds.set(toolId, syntheticMessageId);

      const synthetic: ChatMessage = {
        id: syntheticMessageId,
        content: '',
        timestamp: new Date(),
        sender: 'ai',
        metadata: {
          messageType: 'system',
          isStreaming: status === 'running',
          streamComplete: status === 'success' || status === 'error',
          toolCalls: [toolMeta]
        }
      } as any;

      this.notifyMessage(synthetic);
    }
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

    // Immediately emit current status so late subscribers reflect accurate state
    try {
      const current: ChatStatus = {
        connected: this.isConnected,
        timestamp: new Date(),
        chat: {
          sessionId: this.currentSessionId || this.generateSessionId(),
          agentId: this.selectedAgent,
          model: undefined as any,
        },
        error: undefined,
      };
      adaptedCallback(current);
    } catch (e) {
      // best-effort; ignore
    }
  }

  onMessage(callback: (message: ChatMessage) => void): void {
    this.messageCallbacks.push(callback);

    // Replay buffered messages to the newly-registered subscriber.
    // Do NOT clear the buffer: other panels/consumers may mount later.
    if (this.pendingMessageOrder.length > 0) {
      const enabled = this.isSurgicalIterateEnabled();
      const sessionKey = this.currentSessionId || 'unknown';
      try {
        if (enabled) {
          console.debug('[SURGICALITERATE][ChatBackendClient] onMessage subscribe', {
            sessionKey,
            callbacks: this.messageCallbacks.length,
            bufferedTotal: this.pendingMessageOrder.length,
          });
        }

        // Prefer replaying current session, but always include any 'unknown' buffered
        // messages (these can happen before the client learns the session id).
        const prefix = `${sessionKey}:`;
        const unknownPrefix = 'unknown:';
        for (const key of this.pendingMessageOrder) {
          // When sessionKey is 'unknown', only replay messages with 'unknown:' prefix
          // to prevent leaking messages from other sessions
          if (sessionKey === 'unknown') {
            if (!key.startsWith(unknownPrefix)) continue;
          } else {
            // When we have a real session ID, replay messages for that session
            if (!key.startsWith(prefix) && !key.startsWith(unknownPrefix)) continue;
          }
          const msg = this.pendingMessages.get(key);
          if (msg) callback(msg);
        }
      } catch (e) {
        console.error('[ChatBackendClient] Error replaying buffered messages:', e);
      }
    }
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
    const enabled = this.isSurgicalIterateEnabled();

    // Attach current session id to messages that don't have it yet.
    // This avoids replay-buffering under 'unknown:' when stream_start arrives
    // before the handshake/status updates set currentSessionId.
    const meta: any = (message as any).metadata || undefined;
    const hasSession = Boolean(meta && (meta.session_id || meta.sessionId || meta.session));
    if (!hasSession && this.currentSessionId) {
      message = {
        ...message,
        metadata: {
          ...(message.metadata || {}),
          session_id: this.currentSessionId,
        },
      };
    }

    const msgId = String((message as any).id || '');
    const sessionKey = this.getSessionKeyForMessage(message);
    const pendingKey = this.makePendingKey(sessionKey, msgId);

    // Always update replay buffer
    if (msgId) {
      if (!this.pendingMessages.has(pendingKey)) {
        this.pendingMessageOrder.push(pendingKey);
      }
      this.pendingMessages.set(pendingKey, message);
      while (this.pendingMessageOrder.length > this.maxPendingMessages) {
        const oldest = this.pendingMessageOrder.shift();
        if (oldest) this.pendingMessages.delete(oldest);
      }
    }

    if (enabled) {
      console.debug('[SURGICALITERATE][ChatBackendClient] notifyMessage', {
        sessionKey,
        id: msgId,
        callbacks: this.messageCallbacks.length,
        buffered: this.pendingMessageOrder.length,
        messageType: (message as any).metadata?.messageType,
        isStreaming: (message as any).metadata?.isStreaming,
        streamComplete: (message as any).metadata?.streamComplete,
        contentLen: typeof (message as any).content === 'string' ? (message as any).content.length : 0,
      });
    }

    if (this.messageCallbacks.length > 0) {
      this.messageCallbacks.forEach(callback => callback(message));
    }
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
    
    if (this.connectionId && this.wsService) {
      try {
        await this.wsService.disconnect(this.connectionId);
      } catch (error) {
        console.warn('[ChatBackendClient] Disconnect error:', error);
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
    
    if (this.wsService) {
      try {
        this.wsService.destroy();
      } catch (error) {
        console.warn('[ChatBackendClient] Service destruction error:', error);
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
export const chatBackendClient = new ChatBackendClient();
