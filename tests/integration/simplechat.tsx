/**
 * Simple Chat Implementation - Phase 6 Production Integration
 * Production-Ready ICPY Phase 6 Agentic Backend Integration
 * 
 * This component is fully integrated with the production ICPY Phase 6 agentic backend
 * featuring real OpenAI, CrewAI, LangChain, and LangGraph integration. All REST API
 * endpoints and WebSocket connections are functional with production-level reliability.
 * 
 * PHASE 6 PRODUCTION FEATURES:
 * - Production WebSocket connection to `/ws/chat` with real agent responses
 * - Fully functional REST API integration for all chat operations
 * - Production chat service with SQLite message persistence
 * - Agent management integration with multiple AI frameworks
 * - Real-time typing indicators and status updates
 * - Message history with pagination and persistence
 * - Agent capability detection and framework selection
 * - Production-grade error handling and reliability
 * 
 * API ENDPOINTS (Phase 6 Production Ready):
 * - WebSocket: `/ws/chat` - Real-time bidirectional agent communication ✅
 * - GET `/api/chat/messages?limit=N` - Persistent message history retrieval ✅
 * - GET/POST `/api/chat/config` - Chat configuration and agent settings ✅
 * - GET `/api/agents/status` - Agent availability and capabilities ✅
 * - POST `/api/chat/clear` - Clear message history ✅
 * - POST `/api/agents/` - Create new agents with templates ✅
 * - POST `/api/agents/{id}/execute` - Execute agent tasks ✅
 * 
 * FRAMEWORKS SUPPORTED:
 * - OpenAI SDK with real GPT model calls and streaming
 * - CrewAI with actual crew agent execution
 * - LangChain & LangGraph with workflow engine integration
 * - Automatic framework detection and capability reporting
 * 
 * Usage:
 * - Access at `/simple-chat` route
 * - Automatically connects to production agentic backend
 * - Real agent responses with framework-specific capabilities
 * - Message persistence across sessions
 * - Multi-agent workflow support via backend templates
 * 
 * @see icpy_6_summary.md - Phase 6 implementation details
 * @see backend/icpy/services/chat_service.py - Backend chat service
 * @see backend/icpy/services/agent_service.py - Agent management
 * @see docs/ticket_icpy6.md - Integration completion status
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';

// Chat message interface - updated for Phase 6 integration
interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'ai' | 'system';
  timestamp: Date;
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
  };
}

// Connection status interface - enhanced for Phase 6
interface ConnectionStatus {
  connected: boolean;
  agent?: {
    available: boolean;
    id?: string;
    name?: string;
    type?: 'openai' | 'crewai' | 'langchain' | 'langgraph';
    capabilities?: string[];
    status?: 'idle' | 'busy' | 'error' | 'starting';
    frameworks?: string[];
    apiKeyStatus?: Record<string, boolean>;
  };
  chat?: {
    sessionId?: string;
    messageCount?: number;
    lastActivity?: string;
  };
  timestamp?: number;
  error?: string;
}

// Chat configuration interface - Phase 6 enhanced
interface ChatConfig {
  agentId: string;
  agentName: string;
  agentType?: 'openai' | 'crewai' | 'langchain' | 'langgraph';
  systemPrompt?: string;
  maxMessages?: number;
  autoScroll?: boolean;
  streamingEnabled?: boolean;
  capabilities?: string[];
  frameworks?: {
    openai?: { model?: string; temperature?: number };
    crewai?: { crew?: string; role?: string };
    langchain?: { chain?: string; memory?: boolean };
    langgraph?: { graph?: string; nodes?: string[] };
  };
  persistence?: {
    enabled: boolean;
    retention?: number;
  };
}

// Simple notification system
class ChatNotificationService {
  static show(message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info'): void {
    const notification = document.createElement('div');
    const colors = {
      success: 'bg-green-500 text-white',
      error: 'bg-red-500 text-white', 
      warning: 'bg-yellow-500 text-black',
      info: 'bg-blue-500 text-white'
    };
    
    notification.className = `fixed top-4 right-4 px-4 py-2 rounded shadow-lg z-50 transition-opacity ${colors[type]}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
      notification.style.opacity = '0';
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 300);
    }, 3000);
  }
}

// Chat backend client - Phase 6 production integration
class ChatBackendClient {
  private baseUrl: string;
  private websocket: WebSocket | null = null;
  private messageCallbacks: ((message: ChatMessage) => void)[] = [];
  private statusCallbacks: ((status: ConnectionStatus) => void)[] = [];
  private streamingMessage: ChatMessage | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private isDisconnecting = false;

  constructor() {
    // Smart URL construction for Cloudflare tunnel compatibility
    const envBackendUrl = (import.meta as any).env?.VITE_BACKEND_URL as string | undefined;
    const envApiUrl = (import.meta as any).env?.VITE_API_URL as string | undefined;
    const primaryUrl = envBackendUrl || envApiUrl;
    
    // Check if we're accessing through a different domain than configured
    const currentHost = window.location.host;
    let envHost = '';
    
    // Safely extract host from environment URL
    if (primaryUrl && primaryUrl.trim() !== '') {
      try {
        envHost = new URL(primaryUrl).host;
      } catch (error) {
        console.warn('Could not parse environment URL:', primaryUrl);
      }
    }
    
    if (primaryUrl && primaryUrl.trim() !== '' && currentHost === envHost) {
      this.baseUrl = primaryUrl;
    } else {
      // Use current origin for compatibility
      this.baseUrl = window.location.origin;
    }
    
    // Removed console.log to prevent unnecessary output on every keystroke
    // console.log('SimpleChat Phase 6 initialized with URL:', this.baseUrl);
  }

  // WebSocket connection management - Phase 6 production features
  async connectWebSocket(): Promise<boolean> {
    try {
      const wsUrl = this.baseUrl.replace(/^http/, 'ws') + '/ws/chat';
      console.log('Connecting to Phase 6 Chat WebSocket:', wsUrl);
      
      this.websocket = new WebSocket(wsUrl);
      
      this.websocket.onopen = () => {
        console.log('Phase 6 Chat WebSocket connected - agentic backend ready');
        this.reconnectAttempts = 0;
        this.isDisconnecting = false; // Reset disconnecting flag on successful connection
        this.notifyStatus({ 
          connected: true, 
          timestamp: Date.now(),
          chat: { sessionId: this.generateSessionId() }
        });
        ChatNotificationService.show('Connected to agentic chat service', 'success');
      };
      
      this.websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('Phase 6 message received:', data);
          
          if (data.type === 'message') {
            // Handle complete messages
            const message: ChatMessage = {
              id: data.id || Date.now().toString(),
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
            this.notifyMessage(message);
          } else if (data.type === 'message_stream') {
            // Handle streaming messages - Phase 6 feature
            this.handleStreamingMessage(data);
          } else if (data.type === 'typing') {
            // Handle typing indicators
            this.notifyStatus({
              connected: true,
              agent: {
                available: true,
                status: data.isTyping ? 'busy' : 'idle',
                ...data.agent
              },
              timestamp: Date.now()
            });
          } else if (data.type === 'agent_status') {
            // Handle agent status updates
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
          } else if (data.type === 'error') {
            // Handle errors from backend
            const errorMessage: ChatMessage = {
              id: Date.now().toString(),
              content: data.message || 'An error occurred',
              sender: 'system',
              timestamp: new Date(),
              metadata: { messageType: 'error', context: data.details }
            };
            this.notifyMessage(errorMessage);
          }
        } catch (error) {
          console.error('Error parsing Phase 6 WebSocket message:', error);
        }
      };
      
      this.websocket.onclose = (event) => {
        console.log('Phase 6 Chat WebSocket disconnected:', event.code, event.reason);
        this.notifyStatus({ 
          connected: false, 
          timestamp: Date.now(),
          error: `Connection closed: ${event.reason || 'Unknown reason'}`
        });
        
        // Only auto-reconnect if not intentionally disconnecting
        if (!this.isDisconnecting && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectTimeout = setTimeout(() => {
            if (!this.isDisconnecting) { // Double-check before reconnecting
              this.reconnectAttempts++;
              console.log(`Attempting reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
              this.connectWebSocket();
            }
          }, this.reconnectDelay * this.reconnectAttempts);
        } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          ChatNotificationService.show('Chat service disconnected - max reconnect attempts reached', 'error');
        }
      };
      
      this.websocket.onerror = (error) => {
        console.error('Phase 6 Chat WebSocket error:', error);
        this.notifyStatus({ 
          connected: false, 
          timestamp: Date.now(),
          error: 'WebSocket connection failed'
        });
      };
      
      return true;
    } catch (error) {
      console.error('Failed to connect to Phase 6 WebSocket:', error);
      this.notifyStatus({ 
        connected: false, 
        timestamp: Date.now(),
        error: error instanceof Error ? error.message : 'Unknown connection error'
      });
      return false;
    }
  }

  // Handle streaming messages - Phase 6 feature
  private handleStreamingMessage(data: any): void {
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
      this.streamingMessage = {
        id: data.id || Date.now().toString(),
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
      // Append chunk to streaming message - only update content, don't create new message
      console.log('📝 Adding chunk:', data.chunk);
      this.streamingMessage.content += data.chunk;
      // Update the existing message object and notify about the change
      this.notifyMessage({ 
        ...this.streamingMessage,
        metadata: {
          ...this.streamingMessage.metadata!,
          isStreaming: true  // Ensure it's still marked as streaming
        }
      });
    } else if (data.stream_end && this.streamingMessage) {
      // Complete streaming message - set isStreaming: false to stop the "streaming..." indicator
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

  // Send message via WebSocket - Phase 6 enhanced
  async sendMessage(content: string, options?: {
    agentType?: 'openai' | 'crewai' | 'langchain' | 'langgraph';
    framework?: any;
    streaming?: boolean;
    context?: any;
  }): Promise<void> {
    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected to Phase 6 backend');
    }
    
    const message = {
      type: 'message', // Changed from 'user_message' to match backend expectation
      content,
      sender: 'user',
      timestamp: new Date().toISOString(),
      sessionId: this.generateSessionId(),
      options: {
        agentType: options?.agentType || 'openai',
        streaming: options?.streaming !== false,
        framework: options?.framework,
        context: options?.context
      }
    };
    
    console.log('Sending Phase 6 message:', message);
    this.websocket.send(JSON.stringify(message));
  }

  // Get message history via HTTP - Phase 6 Production Implementation
  async getMessageHistory(limit: number = 50, offset: number = 0): Promise<ChatMessage[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/chat/messages?limit=${limit}&offset=${offset}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      const messages = result.data || [];
      console.log('Phase 6 message history loaded:', messages.length, 'messages');
      
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
      console.error('Failed to load Phase 6 message history:', error);
      return []; // Return empty array on error
    }
  }

  // Get chat configuration - Phase 6 Production Implementation
  async getChatConfig(): Promise<ChatConfig> {
    try {
      const response = await fetch(`${this.baseUrl}/api/chat/config`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      const config = result.data;
      console.log('Phase 6 chat config loaded:', config);
      
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
      console.error('Failed to load Phase 6 chat config:', error);
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

  // Update chat configuration - Phase 6 feature
  async updateChatConfig(config: Partial<ChatConfig>): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/chat/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      console.log('Phase 6 chat config updated');
      ChatNotificationService.show('Chat configuration updated', 'success');
    } catch (error) {
      console.error('Failed to update Phase 6 chat config:', error);
      ChatNotificationService.show('Failed to update configuration', 'error');
    }
  }

  // Check agent status - Phase 6 Production Implementation
  async getAgentStatus(): Promise<ConnectionStatus> {
    try {
      const response = await fetch(`${this.baseUrl}/api/agents/status`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      const data = result.data;
      console.log('Phase 6 agent status:', data);
      
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
      console.error('Failed to check Phase 6 agent status:', error);
      // Return basic fallback status on error
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

  // Clear chat messages - Phase 6 feature
  async clearMessages(): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/chat/clear`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      console.log('Phase 6 messages cleared');
      ChatNotificationService.show('Chat history cleared', 'success');
    } catch (error) {
      console.error('Failed to clear Phase 6 messages:', error);
      ChatNotificationService.show('Failed to clear messages', 'error');
    }
  }

  // Create new agent - Phase 6 feature
  async createAgent(template: string, config?: any): Promise<string> {
    try {
      const response = await fetch(`${this.baseUrl}/api/agents/`, {
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
      console.log('Phase 6 agent created:', data.agentId);
      ChatNotificationService.show(`Agent created: ${data.agentName}`, 'success');
      return data.agentId;
    } catch (error) {
      console.error('Failed to create Phase 6 agent:', error);
      ChatNotificationService.show('Failed to create agent', 'error');
      throw error;
    }
  }

  // Execute agent task - Phase 6 feature
  async executeAgentTask(agentId: string, task: any): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/agents/${agentId}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(task)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      console.log('Phase 6 agent task executed');
    } catch (error) {
      console.error('Failed to execute Phase 6 agent task:', error);
      throw error;
    }
  }

  // Generate session ID for chat tracking
  private generateSessionId(): string {
    return `chat_${Date.now()}_${Math.random().toString(36).substring(2)}`;
  }

  // Event subscription methods
  onMessage(callback: (message: ChatMessage) => void): void {
    this.messageCallbacks.push(callback);
  }

  onStatus(callback: (status: ConnectionStatus) => void): void {
    this.statusCallbacks.push(callback);
  }

  // Cleanup - Phase 6 enhanced
  disconnect(): void {
    this.isDisconnecting = true;
    
    // Clear any pending reconnection attempts
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.websocket) {
      this.websocket.close(1000, 'Component unmounting'); // Normal closure
      this.websocket = null;
    }
    this.messageCallbacks = [];
    this.statusCallbacks = [];
    this.streamingMessage = null;
    this.reconnectAttempts = 0;
    console.log('Phase 6 chat client disconnected');
  }

  // Stop reconnection attempts - useful for navigation/cleanup
  stopReconnection(): void {
    this.isDisconnecting = true;
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent further attempts
  }

  private notifyMessage(message: ChatMessage): void {
    this.messageCallbacks.forEach(callback => callback(message));
  }

  private notifyStatus(status: ConnectionStatus): void {
    this.statusCallbacks.forEach(callback => callback(status));
  }
}

interface SimpleChatProps {
  className?: string;
}

const SimpleChat: React.FC<SimpleChatProps> = ({ className = '' }) => {
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({ connected: false });
  const [chatConfig, setChatConfig] = useState<ChatConfig>({
    agentId: 'default',
    agentName: 'AI Assistant',
    agentType: 'openai',
    maxMessages: 100,
    autoScroll: true,
    streamingEnabled: true,
    capabilities: [],
    frameworks: {},
    persistence: { enabled: true, retention: 30 }
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [selectedAgentType, setSelectedAgentType] = useState<'openai' | 'crewai' | 'langchain' | 'langgraph'>('openai');
  const isInitializing = useRef(false);

  const backendClient = useRef(new ChatBackendClient());

  // Theme detection
  useEffect(() => {
    const detectTheme = () => {
      const isDark = document.documentElement.classList.contains('dark') ||
                    document.body.classList.contains('dark') ||
                    window.matchMedia('(prefers-color-scheme: dark)').matches;
      setIsDarkTheme(isDark);
    };

    detectTheme();
    const observer = new MutationObserver(detectTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });

    return () => observer.disconnect();
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatConfig.autoScroll && chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, chatConfig.autoScroll]);

  // Initialize chat - Phase 6 enhanced
  const initializeChat = useCallback(async () => {
    // Prevent multiple simultaneous initializations
    if (isInitializing.current) {
      console.log('Phase 6 chat initialization already in progress, skipping...');
      return;
    }
    
    isInitializing.current = true;
    setIsLoading(true);
    
    try {
      console.log('Initializing Phase 6 Chat System...');
      
      // Load configuration
      const config = await backendClient.current.getChatConfig();
      setChatConfig(config);
      console.log('Phase 6 config loaded:', config);
      
      // Load message history with persistence
      const history = await backendClient.current.getMessageHistory(config.maxMessages);
      setMessages(history);
      console.log('Phase 6 message history loaded:', history.length, 'messages');
      
      // Check agent status and framework availability
      const status = await backendClient.current.getAgentStatus();
      setConnectionStatus(status);
      console.log('Phase 6 agent status:', status);
      
      // Set default agent type from config
      if (config.agentType) {
        setSelectedAgentType(config.agentType);
      }
      
      // Connect WebSocket for real-time communication
      const wsConnected = await backendClient.current.connectWebSocket();
      console.log('Phase 6 WebSocket connection:', wsConnected ? 'SUCCESS' : 'FAILED');
      
      // Set up event listeners for Phase 6 features
      backendClient.current.onMessage((message: ChatMessage) => {
        console.log('Phase 6 message received:', message);
        
        if (message.metadata?.isStreaming || message.metadata?.streamComplete) {
          // Handle streaming messages - update existing or add new
          setMessages(prev => {
            const existingIndex = prev.findIndex(m => m.id === message.id);
            if (existingIndex >= 0) {
              const updated = [...prev];
              updated[existingIndex] = message;
              return updated;
            } else {
              return [...prev, message];
            }
          });
        } else {
          // Handle complete messages - only add if not already exists
          setMessages(prev => {
            const existingIndex = prev.findIndex(m => m.id === message.id);
            if (existingIndex >= 0) {
              // Message already exists, don't add duplicate
              console.log('Skipping duplicate message:', message.id);
              return prev;
            } else {
              return [...prev, message];
            }
          });
        }
        
        // Update typing status
        setIsTyping(false);
      });
      
      backendClient.current.onStatus((status: ConnectionStatus) => {
        console.log('Phase 6 status update:', status);
        setConnectionStatus(status);
        
        // Update typing indicator based on agent status
        if (status.agent?.status === 'busy') {
          setIsTyping(true);
        } else if (status.agent?.status === 'idle') {
          setIsTyping(false);
        }
      });

      ChatNotificationService.show('Phase 6 agentic chat initialized', 'success');
      
    } catch (error) {
      console.error('Failed to initialize Phase 6 chat:', error);
      ChatNotificationService.show('Failed to initialize Phase 6 chat system', 'error');
    } finally {
      setIsLoading(false);
      isInitializing.current = false;
    }
  }, []);

  // Handle sending a message - Phase 6 enhanced with framework selection
  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() || !connectionStatus.connected) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: inputValue,
      sender: 'user',
      timestamp: new Date(),
      metadata: {
        agentType: selectedAgentType,
        messageType: 'text'
      }
    };

    // setMessages(prev => [...prev, userMessage]);
    const messageContent = inputValue;
    setInputValue('');
    setIsTyping(true);

    try {
      // Send message with Phase 6 framework selection
      await backendClient.current.sendMessage(messageContent, {
        agentType: selectedAgentType,
        streaming: chatConfig.streamingEnabled,
        framework: chatConfig.frameworks?.[selectedAgentType] || {}
      });
      
      console.log(`Phase 6 message sent via ${selectedAgentType} framework`);
      
    } catch (error) {
      console.error('Failed to send Phase 6 message:', error);
      ChatNotificationService.show(`Failed to send message via ${selectedAgentType}`, 'error');
      setIsTyping(false);
      
      // Add error message with framework context
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: `Failed to send message via ${selectedAgentType} framework. Please check connection and API keys.`,
        sender: 'system',
        timestamp: new Date(),
        metadata: { 
          messageType: 'error', 
          agentType: selectedAgentType,
          context: { framework: selectedAgentType, error: error instanceof Error ? error.message : 'Unknown error' }
        }
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  }, [inputValue, connectionStatus.connected, selectedAgentType, chatConfig]);

  // Clear chat messages - Phase 6 with backend sync
  const handleClearChat = useCallback(async () => {
    try {
      await backendClient.current.clearMessages();
      setMessages([]);
      console.log('Phase 6 chat cleared');
    } catch (error) {
      console.error('Failed to clear Phase 6 chat:', error);
      // Clear locally even if backend fails
      setMessages([]);
      ChatNotificationService.show('Chat cleared locally (backend sync failed)', 'warning');
    }
  }, []);

  // Switch agent framework - Phase 6 feature
  const handleSwitchAgent = useCallback(async (agentType: 'openai' | 'crewai' | 'langchain' | 'langgraph') => {
    try {
      setSelectedAgentType(agentType);
      
      // Update chat configuration
      const updatedConfig = { ...chatConfig, agentType };
      await backendClient.current.updateChatConfig(updatedConfig);
      setChatConfig(updatedConfig);
      
      console.log(`Phase 6 switched to ${agentType} framework`);
      ChatNotificationService.show(`Switched to ${agentType.toUpperCase()} framework`, 'info');
    } catch (error) {
      console.error('Failed to switch Phase 6 agent:', error);
      ChatNotificationService.show('Failed to switch agent framework', 'error');
    }
  }, [chatConfig]);

  // Create new agent - Phase 6 feature
  const handleCreateAgent = useCallback(async (template: string) => {
    try {
      setIsLoading(true);
      const agentId = await backendClient.current.createAgent(template, {
        agentType: selectedAgentType,
        framework: chatConfig.frameworks?.[selectedAgentType] || {}
      });
      
      // Refresh agent status
      const status = await backendClient.current.getAgentStatus();
      setConnectionStatus(status);
      
      console.log(`Phase 6 agent created: ${agentId}`);
    } catch (error) {
      console.error('Failed to create Phase 6 agent:', error);
      ChatNotificationService.show('Failed to create agent', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [selectedAgentType, chatConfig]);

  // Handle Enter key press
  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  // Reconnect to chat - Phase 6 enhanced
  const handleReconnect = useCallback(() => {
    console.log('Attempting Phase 6 reconnection...');
    initializeChat();
  }, [initializeChat]);

  // Initialize on mount - safe for React StrictMode
  useEffect(() => {
    let mounted = true;
    
    const init = async () => {
      if (mounted) {
        await initializeChat();
      }
    };
    
    init();
    
    return () => {
      mounted = false;
      backendClient.current.disconnect();
    };
  }, [initializeChat]);

  // Get status indicator color - Phase 6 enhanced
  const getStatusColor = () => {
    if (!connectionStatus.connected) return 'bg-red-500';
    if (connectionStatus.agent?.status === 'busy') return 'bg-yellow-500';
    if (connectionStatus.agent?.available) return 'bg-green-500';
    return 'bg-gray-500';
  };

  // Get agent framework display
  const getAgentFrameworkDisplay = () => {
    const agent = connectionStatus.agent;
    if (!agent) return '';
    
    const frameworkEmojis = {
      openai: '🤖',
      crewai: '👥',
      langchain: '🔗',
      langgraph: '📊'
    };
    
    return `${frameworkEmojis[agent.type as keyof typeof frameworkEmojis] || '🔧'} ${agent.type?.toUpperCase() || 'AI'}`;
  };

  // Get message styling based on sender and theme - Phase 6 enhanced
  const getMessageStyle = (message: ChatMessage) => {
    const baseStyle = "max-w-[80%] p-3 rounded-lg text-sm";
    
    if (message.sender === 'user') {
      return `${baseStyle} ${isDarkTheme ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'}`;
    } else if (message.sender === 'system') {
      const isError = message.metadata?.messageType === 'error';
      if (isError) {
        return `${baseStyle} ${isDarkTheme ? 'bg-red-700 text-red-200' : 'bg-red-100 text-red-800'} italic`;
      }
      return `${baseStyle} ${isDarkTheme ? 'bg-gray-600 text-gray-300' : 'bg-gray-300 text-gray-700'} italic`;
    } else {
      // AI messages with framework-specific styling
      const agentType = message.metadata?.agentType;
      const isStreaming = message.metadata?.isStreaming;
      
      let bgColor = isDarkTheme ? 'bg-gray-700 text-white' : 'bg-gray-200 text-gray-900';
      
      if (agentType === 'openai') {
        bgColor = isDarkTheme ? 'bg-green-800 text-green-100' : 'bg-green-100 text-green-900';
      } else if (agentType === 'crewai') {
        bgColor = isDarkTheme ? 'bg-purple-800 text-purple-100' : 'bg-purple-100 text-purple-900';
      } else if (agentType === 'langchain') {
        bgColor = isDarkTheme ? 'bg-orange-800 text-orange-100' : 'bg-orange-100 text-orange-900';
      } else if (agentType === 'langgraph') {
        bgColor = isDarkTheme ? 'bg-indigo-800 text-indigo-100' : 'bg-indigo-100 text-indigo-900';
      }
      
      return `${baseStyle} ${bgColor} ${isStreaming ? 'animate-pulse' : ''}`;
    }
  };

  const themeClasses = isDarkTheme
    ? 'bg-gray-900 text-white border-gray-700'
    : 'bg-white text-gray-900 border-gray-300';

  const headerThemeClasses = isDarkTheme
    ? 'bg-gray-800 border-gray-700'
    : 'bg-gray-50 border-gray-300';

  const inputThemeClasses = isDarkTheme
    ? 'bg-gray-300 text-black border-gray-500 placeholder-gray-600'
    : 'bg-white text-black border-gray-300 placeholder-gray-500';

  const buttonThemeClasses = isDarkTheme
    ? 'bg-blue-600 hover:bg-blue-700 text-white disabled:bg-gray-700'
    : 'bg-blue-500 hover:bg-blue-600 text-white disabled:bg-gray-400';

  if (isLoading) {
    return (
      <div className={`simple-chat-panel h-full flex items-center justify-center ${themeClasses} ${className}`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
          <div className="text-sm opacity-70">Initializing Phase 6 Agentic Chat...</div>
          <div className="text-xs opacity-50 mt-1">Loading AI frameworks and agent services</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`simple-chat-panel h-full flex flex-col border ${themeClasses} ${className}`}>
      {/* Header - Phase 6 Enhanced */}
      <div className={`flex items-center justify-between p-3 border-b ${headerThemeClasses}`}>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${getStatusColor()}`} />
          <span className="text-sm font-medium">
            {chatConfig.agentName}
            {connectionStatus.agent?.type && (
              <span className="ml-2 text-xs opacity-70">
                {getAgentFrameworkDisplay()}
              </span>
            )}
          </span>
          {isTyping && (
            <span className="text-xs opacity-60 animate-pulse">typing...</span>
          )}
        </div>
        
        {/* Framework Selector - Phase 6 Feature */}
        <div className="flex items-center space-x-2">
          <select
            value={selectedAgentType}
            onChange={(e) => handleSwitchAgent(e.target.value as any)}
            className={`text-xs px-2 py-1 rounded border ${inputThemeClasses}`}
            disabled={!connectionStatus.connected}
          >
            <option value="openai">🤖 OpenAI</option>
            <option value="crewai">👥 CrewAI</option>
            <option value="langchain">🔗 LangChain</option>
            <option value="langgraph">📊 LangGraph</option>
          </select>
          
          {!connectionStatus.connected && (
            <button
              onClick={handleReconnect}
              className="text-xs px-2 py-1 rounded hover:opacity-80 transition-opacity bg-blue-500 text-white"
            >
              Reconnect
            </button>
          )}
          <button
            onClick={handleClearChat}
            className="text-xs px-2 py-1 rounded hover:opacity-80 transition-opacity bg-gray-500 text-white"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Agent Status Bar - Phase 6 Feature */}
      {connectionStatus.agent && (
        <div className={`px-3 py-1 text-xs border-b ${headerThemeClasses}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span>Status: {connectionStatus.agent.status || 'unknown'}</span>
              {connectionStatus.agent.capabilities && connectionStatus.agent.capabilities.length > 0 && (
                <span>• Capabilities: {connectionStatus.agent.capabilities.slice(0, 3).join(', ')}</span>
              )}
            </div>
            {connectionStatus.chat && (
              <div className="opacity-60">
                Messages: {connectionStatus.chat.messageCount || messages.length}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Messages container */}
      <div 
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto p-3 space-y-3"
      >
        {messages.length === 0 ? (
          <div className="text-center py-8 opacity-60">
            <div className="text-sm mb-2">
              {connectionStatus.connected 
                ? `${chatConfig.agentName} (${selectedAgentType.toUpperCase()}) is ready!`
                : 'Connecting to Phase 6 agentic services...'
              }
            </div>
            <div className="text-xs">
              Phase 6 Features: Real AI frameworks • Message persistence • Streaming responses
            </div>
            {connectionStatus.agent?.frameworks && connectionStatus.agent.frameworks.length > 0 && (
              <div className="text-xs mt-1 opacity-50">
                Available: {connectionStatus.agent.frameworks.join(', ')}
              </div>
            )}
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={getMessageStyle(message)}>
                <div className="whitespace-pre-wrap">{message.content}</div>
                <div className="text-xs opacity-60 mt-1 flex items-center justify-between">
                  <span>
                    {message.timestamp.toLocaleTimeString()}
                    {message.metadata?.agentName && (
                      <span className="ml-2">• {message.metadata.agentName}</span>
                    )}
                    {message.metadata?.agentType && (
                      <span className="ml-1">({message.metadata.agentType})</span>
                    )}
                  </span>
                  {message.metadata?.isStreaming && (
                    <span className="text-xs animate-pulse">streaming...</span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Input area - Phase 6 Enhanced */}
      <div className={`p-3 border-t ${headerThemeClasses}`}>
        <div className="flex space-x-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={connectionStatus.connected 
              ? `Message ${selectedAgentType.toUpperCase()} agent...` 
              : "Connecting to Phase 6 backend..."
            }
            disabled={!connectionStatus.connected}
            className={`flex-1 px-3 py-2 rounded-md border focus:outline-none text-sm transition-colors ${inputThemeClasses}`}
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || !connectionStatus.connected}
            className={`px-4 py-2 rounded-md transition-colors text-sm disabled:cursor-not-allowed ${buttonThemeClasses}`}
          >
            Send
          </button>
        </div>
        
        {/* Enhanced Status Footer - Phase 6 */}
        <div className="text-xs mt-2 opacity-60">
          <div className="flex items-center justify-between">
            <span>
              Press Enter to send • Shift+Enter for new line
              {chatConfig.streamingEnabled && ' • Streaming enabled'}
            </span>
            <span>
              Phase 6: {connectionStatus.connected ? 'Connected' : 'Disconnected'}
              {connectionStatus.agent?.apiKeyStatus && Object.values(connectionStatus.agent.apiKeyStatus).some(Boolean) && (
                <span className="ml-2 text-green-500">• API Ready</span>
              )}
            </span>
          </div>
        </div>
        
        {connectionStatus.error && (
          <div className="text-xs mt-1 text-red-500">
            Error: {connectionStatus.error}
          </div>
        )}
      </div>
    </div>
  );
};

export default SimpleChat;
