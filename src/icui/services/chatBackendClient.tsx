/**
 * Chat Backend Client - ICUI Framework
 * WebSocket and HTTP API client for chat functionality
 */

import { 
  ChatMessage, 
  ConnectionStatus, 
  ChatConfig, 
  MessageOptions,
  WebSocketMessage,
  StreamingMessageData,
  ChatMessageCallback,
  ChatStatusCallback,
  AgentType
} from '../types/chatTypes';
import { constructBackendUrl, constructWebSocketUrl, constructApiUrl } from '../utils/urlHelpers';
import { notificationService } from './notificationService';

export class ChatBackendClient {
  private baseUrl: string;
  private websocket: WebSocket | null = null;
  private messageCallbacks: ChatMessageCallback[] = [];
  private statusCallbacks: ChatStatusCallback[] = [];
  private streamingMessage: ChatMessage | null = null;
  private processedMessageIds: Set<string> = new Set(); // Track processed complete messages
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private isDisconnecting = false;

  constructor() {
    this.baseUrl = constructBackendUrl();
    
    // Clean up old message IDs periodically to prevent memory leaks
    setInterval(() => {
      if (this.processedMessageIds.size > 1000) {
        console.log('🧹 Cleaning up old processed message IDs');
        // Keep only the most recent 500 message IDs
        const idsArray = Array.from(this.processedMessageIds);
        this.processedMessageIds.clear();
        // Add back the last 500
        idsArray.slice(-500).forEach(id => this.processedMessageIds.add(id));
      }
    }, 60000); // Clean up every minute
  }

  // WebSocket connection management
  async connectWebSocket(): Promise<boolean> {
    try {
      // Prevent multiple connection attempts
      if (this.websocket?.readyState === WebSocket.OPEN) {
        console.warn('Chat WebSocket already connected');
        return true;
      }
      
      if (this.websocket?.readyState === WebSocket.CONNECTING) {
        console.warn('Chat WebSocket connection already in progress');
        return false;
      }
      
      const wsUrl = constructWebSocketUrl('/ws/chat');
      console.log('Connecting to Chat WebSocket:', wsUrl);
      
      this.websocket = new WebSocket(wsUrl);
      
      this.websocket.onopen = () => {
        console.log('Chat WebSocket connected - agentic backend ready');
        this.reconnectAttempts = 0;
        this.isDisconnecting = false;
        this.notifyStatus({ 
          connected: true, 
          timestamp: Date.now(),
          chat: { sessionId: this.generateSessionId() }
        });
        notificationService.success('Connected to agentic chat service');
      };
      
      this.websocket.onmessage = (event) => {
        this.handleWebSocketMessage(event);
      };
      
      this.websocket.onclose = (event) => {
        this.handleWebSocketClose(event);
      };
      
      this.websocket.onerror = (error) => {
        console.error('Chat WebSocket error:', error);
        this.notifyStatus({ 
          connected: false, 
          timestamp: Date.now(),
          error: 'WebSocket connection failed'
        });
      };
      
      return true;
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      this.notifyStatus({ 
        connected: false, 
        timestamp: Date.now(),
        error: error instanceof Error ? error.message : 'Unknown connection error'
      });
      return false;
    }
  }

  // Handle WebSocket messages
  private handleWebSocketMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);
      console.log('WebSocket message received:', data);
      
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
      console.error('Error parsing WebSocket message:', error);
    }
  }

  // Handle complete messages
  private handleCompleteMessage(data: any): void {
    const messageId = data.id || Date.now().toString();
    
    // Skip if we've already processed this message ID via streaming
    if (this.processedMessageIds.has(messageId)) {
      console.log('🚫 Skipping duplicate complete message:', messageId);
      return;
    }
    
    const message: ChatMessage = {
      id: messageId,
      content: data.content,
      sender: data.sender || 'ai',
      timestamp: new Date(data.timestamp || Date.now()),
      metadata: {
        agentId: data.agentId,
        agentName: data.agentName,
        agentType: data.agentType,
        messageType: data.messageType || 'text',
        workflowId: data.workflowId,
        taskId: data.taskId,
        capabilities: data.capabilities,
        context: data.context,
        isStreaming: false,
        streamComplete: true
      }
    };
    
    // Mark this message ID as processed
    this.processedMessageIds.add(messageId);
    this.notifyMessage(message);
  }

  // Handle streaming messages
  private handleStreamingMessage(data: StreamingMessageData): void {
    console.log('🔄 Frontend handleStreamingMessage:', {
      stream_start: data.stream_start,
      stream_chunk: data.stream_chunk, 
      stream_end: data.stream_end,
      id: data.id,
      chunk: data.chunk,
      currentStreamingMessage: this.streamingMessage?.id
    });
    
    if (data.stream_start) {
      // Start new streaming message
      console.log('🚀 Starting new streaming message');
      const messageId = data.id || Date.now().toString();
      
      // Mark this message ID as processed to prevent duplicate complete messages
      this.processedMessageIds.add(messageId);
      
      this.streamingMessage = {
        id: messageId,
        content: '',
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
      this.notifyMessage(this.streamingMessage);
    } else if (data.stream_chunk && this.streamingMessage) {
      // Append chunk to streaming message
      console.log('📝 Adding chunk:', data.chunk);
      this.streamingMessage.content += data.chunk;
      this.notifyMessage({ 
        ...this.streamingMessage,
        metadata: {
          ...this.streamingMessage.metadata!,
          isStreaming: true
        }
      });
    } else if (data.stream_end && this.streamingMessage) {
      // Complete streaming message
      console.log('✅ Ending streaming message');
      this.streamingMessage.metadata!.streamComplete = true;
      this.streamingMessage.metadata!.isStreaming = false;
      this.notifyMessage({ 
        ...this.streamingMessage,
        metadata: {
          ...this.streamingMessage.metadata!,
          isStreaming: false,
          streamComplete: true
        }
      });
      this.streamingMessage = null;
    } else {
      console.warn('⚠️ Unhandled streaming message:', data);
    }
  }

  // Handle typing indicators
  private handleTypingIndicator(data: any): void {
    this.notifyStatus({
      connected: true,
      agent: {
        available: true,
        status: data.isTyping ? 'busy' : 'idle',
        ...data.agent
      },
      timestamp: Date.now()
    });
  }

  // Handle agent status updates
  private handleAgentStatus(data: any): void {
    this.notifyStatus({
      connected: true,
      agent: {
        available: data.available,
        id: data.agentId,
        name: data.agentName,
        type: data.agentType,
        capabilities: data.capabilities,
        status: data.status,
        frameworks: data.frameworks,
        apiKeyStatus: data.apiKeyStatus
      },
      timestamp: Date.now()
    });
  }

  // Handle error messages
  private handleErrorMessage(data: any): void {
    const errorMessage: ChatMessage = {
      id: Date.now().toString(),
      content: data.message || 'An error occurred',
      sender: 'system',
      timestamp: new Date(),
      metadata: { messageType: 'error', context: data.details }
    };
    this.notifyMessage(errorMessage);
  }

  // Handle WebSocket connection close
  private handleWebSocketClose(event: CloseEvent): void {
    console.log('Chat WebSocket disconnected:', event.code, event.reason);
    
    // Clear processed message IDs on disconnect
    this.processedMessageIds.clear();
    
    this.notifyStatus({ 
      connected: false, 
      timestamp: Date.now(),
      error: `Connection closed: ${event.reason || 'Unknown reason'}`
    });
    
    // Auto-reconnect logic
    if (!this.isDisconnecting && this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectTimeout = setTimeout(() => {
        if (!this.isDisconnecting) {
          this.reconnectAttempts++;
          console.log(`Attempting reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
          this.connectWebSocket();
        }
      }, this.reconnectDelay * this.reconnectAttempts);
    } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      notificationService.error('Chat service disconnected - max reconnect attempts reached');
    }
  }

  // Send message via WebSocket
  async sendMessage(content: string, options: MessageOptions = {}): Promise<void> {
    console.log('🚀 [ChatBackendClient] sendMessage called:', { content, options });
    
    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
      console.error('❌ [ChatBackendClient] WebSocket not connected! State:', this.websocket?.readyState);
      throw new Error('WebSocket not connected to backend');
    }
    
    const message: WebSocketMessage = {
      type: 'message',
      content,
      sender: 'user',
      timestamp: new Date().toISOString(),
      sessionId: this.generateSessionId(),
      options: {
        agentType: options.agentType || 'openai',
        streaming: options.streaming !== false,
        framework: options.framework,
        context: options.context
      }
    };
    
    // Convert to backend format with metadata
    const backendMessage = {
      type: 'message',
      content,
      sender: 'user',
      timestamp: Date.now(),
      metadata: {
        agentType: options.agentType || 'openai'
      }
    };
    
    console.log('📤 [ChatBackendClient] Sending WebSocket message:', backendMessage);
    console.log('🔗 [ChatBackendClient] WebSocket URL:', this.websocket.url);
    console.log('🔌 [ChatBackendClient] WebSocket state:', this.websocket.readyState);
    
    this.websocket.send(JSON.stringify(backendMessage));
    console.log('✅ [ChatBackendClient] Message sent successfully');
  }

  // Get message history via HTTP
  async getMessageHistory(limit: number = 50, offset: number = 0): Promise<ChatMessage[]> {
    try {
      const url = constructApiUrl(`/api/chat/messages?limit=${limit}&offset=${offset}`);
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      const messages = result.data || [];
      console.log('Message history loaded:', messages.length, 'messages');
      
      return messages.map((msg: any) => ({
        id: msg.id,
        content: msg.content,
        sender: msg.sender,
        timestamp: new Date(msg.timestamp),
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
      console.error('Failed to load message history:', error);
      return [];
    }
  }

  // Get chat configuration
  async getChatConfig(): Promise<ChatConfig> {
    try {
      const url = constructApiUrl('/api/chat/config');
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      const config = result.data;
      console.log('Chat config loaded:', config);
      
      return {
        agentId: config.agent_id || 'default',
        agentName: config.agent_name || 'AI Assistant',
        agentType: config.agent_type || 'openai',
        systemPrompt: config.system_prompt,
        maxMessages: config.max_messages || 100,
        autoScroll: config.auto_scroll !== false,
        streamingEnabled: config.streaming_enabled !== false,
        capabilities: config.capabilities || [],
        frameworks: config.frameworks || {},
        persistence: {
          enabled: config.persistence?.enabled !== false,
          retention: config.message_retention_days || 30
        }
      };
    } catch (error) {
      console.error('Failed to load chat config:', error);
      // Return default config on error
      return {
        agentId: 'default',
        agentName: 'AI Assistant',
        agentType: 'openai',
        maxMessages: 100,
        autoScroll: true,
        streamingEnabled: true,
        capabilities: ['chat'],
        frameworks: {},
        persistence: { enabled: true, retention: 30 }
      };
    }
  }

  // Update chat configuration
  async updateChatConfig(config: Partial<ChatConfig>): Promise<void> {
    try {
      const url = constructApiUrl('/api/chat/config');
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      console.log('Chat config updated');
      notificationService.success('Chat configuration updated');
    } catch (error) {
      console.error('Failed to update chat config:', error);
      notificationService.error('Failed to update configuration');
    }
  }

  // Check agent status
  async getAgentStatus(): Promise<ConnectionStatus> {
    try {
      const url = constructApiUrl('/api/agents/status');
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      const data = result.data;
      console.log('Agent status:', data);
      
      return {
        connected: true,
        agent: {
          available: data.available || false,
          id: data.agent_id,
          name: data.name || 'AI Assistant',
          type: data.type || 'openai',
          capabilities: data.capabilities || [],
          status: data.status || 'idle',
          frameworks: Object.keys(data.frameworks || {}),
          apiKeyStatus: data.apiKeyStatus || {}
        },
        chat: {
          sessionId: data.sessionId,
          messageCount: data.messageCount,
          lastActivity: data.lastActivity
        },
        timestamp: Date.now()
      };
    } catch (error) {
      console.error('Failed to check agent status:', error);
      return {
        connected: false,
        agent: {
          available: false,
          id: null,
          name: 'AI Assistant',
          type: 'openai',
          capabilities: [],
          status: 'error',
          frameworks: [],
          apiKeyStatus: {}
        },
        chat: {
          sessionId: null,
          messageCount: 0,
          lastActivity: null
        },
        timestamp: Date.now()
      };
    }
  }

  // Clear chat messages
  async clearMessages(): Promise<void> {
    try {
      const url = constructApiUrl('/api/chat/clear');
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      console.log('Messages cleared');
      notificationService.success('Chat history cleared');
    } catch (error) {
      console.error('Failed to clear messages:', error);
      notificationService.error('Failed to clear messages');
    }
  }

  // Create new agent
  async createAgent(template: string, config?: any): Promise<string> {
    try {
      const url = constructApiUrl('/api/agents/');
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template,
          config: config || {}
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Agent created:', data.agentId);
      notificationService.success(`Agent created: ${data.agentName}`);
      return data.agentId;
    } catch (error) {
      console.error('Failed to create agent:', error);
      notificationService.error('Failed to create agent');
      throw error;
    }
  }

  // Execute agent task
  async executeAgentTask(agentId: string, task: any): Promise<void> {
    try {
      const url = constructApiUrl(`/api/agents/${agentId}/execute`);
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(task)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      console.log('Agent task executed');
    } catch (error) {
      console.error('Failed to execute agent task:', error);
      throw error;
    }
  }

  // Generate session ID
  private generateSessionId(): string {
    return `chat_${Date.now()}_${Math.random().toString(36).substring(2)}`;
  }

  // Event subscription methods
  onMessage(callback: ChatMessageCallback): void {
    this.messageCallbacks.push(callback);
  }

  onStatus(callback: ChatStatusCallback): void {
    this.statusCallbacks.push(callback);
  }

  // Cleanup
  disconnect(): void {
    this.isDisconnecting = true;
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.websocket) {
      this.websocket.close(1000, 'Component unmounting');
      this.websocket = null;
    }
    
    this.messageCallbacks = [];
    this.statusCallbacks = [];
    this.streamingMessage = null;
    this.reconnectAttempts = 0;
    console.log('Chat client disconnected');
  }

  // Stop reconnection attempts
  stopReconnection(): void {
    this.isDisconnecting = true;
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    this.reconnectAttempts = this.maxReconnectAttempts;
  }

  // Notify message callbacks
  private notifyMessage(message: ChatMessage): void {
    this.messageCallbacks.forEach(callback => callback(message));
  }

  // Notify status callbacks
  private notifyStatus(status: ConnectionStatus): void {
    this.statusCallbacks.forEach(callback => callback(status));
  }
}
