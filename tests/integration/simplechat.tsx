/**
 * Simple Chat Implementation
 * Based on ICUIChatPanel.tsx - A minimal, working chat interface for ICUI-ICPY integration
 * 
 * This component provides a simplified chat implementation that directly connects
 * to the ICPY backend via WebSocket and HTTP APIs, without the complexity of the full
 * backend state management system. It's designed to showcase agentic coding capabilities
 * and test AI assistant connectivity issues.
 * 
 * Features:
 * - Direct WebSocket connection to ICPY backend for real-time chat
 * - HTTP API fallback for message history and configuration
 * - Basic chat functionality with user/AI message distinction
 * - Connection status monitoring with visual feedback
 * - Error handling and recovery mechanisms
 * - Theme-aware styling (dark/light mode support)
 * - Auto-scroll to latest messages
 * - Message persistence via backend API
 * - Typing indicators and connection status
 * - Clean, minimal implementation for debugging agentic workflows
 * 
 * Integration Points:
 * - WebSocket: /ws/chat for real-time messaging
 * - HTTP: /api/chat/messages for message history
 * - HTTP: /api/chat/config for chat configuration
 * - HTTP: /api/agents/status for agent availability
 * 
 * Usage:
 * - Access at /simple-chat route
 * - Automatically connects to backend on mount
 * - Provides visual feedback for connection and agent status
 * - Send messages to interact with AI agents
 * - Message history persisted across sessions
 * 
 * @see ICUIChatPanel.tsx - Original reference implementation
 * @see BackendConnectedChat.tsx - Full backend-integrated chat (future)
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';

// Chat message interface
interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'ai' | 'system';
  timestamp: Date;
  metadata?: {
    agentId?: string;
    agentName?: string;
    messageType?: 'text' | 'code' | 'error' | 'system';
    context?: any;
  };
}

// Connection status interface
interface ConnectionStatus {
  connected: boolean;
  agent?: {
    available: boolean;
    name?: string;
    type?: string;
    capabilities?: string[];
  };
  timestamp?: number;
  error?: string;
}

// Chat configuration interface
interface ChatConfig {
  agentId: string;
  agentName: string;
  systemPrompt?: string;
  maxMessages?: number;
  autoScroll?: boolean;
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

// Chat backend client
class ChatBackendClient {
  private baseUrl: string;
  private websocket: WebSocket | null = null;
  private messageCallbacks: ((message: ChatMessage) => void)[] = [];
  private statusCallbacks: ((status: ConnectionStatus) => void)[] = [];

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
    
    console.log('SimpleChat initialized with URL:', this.baseUrl);
    console.log('Current host:', currentHost, 'Env host:', envHost);
  }

  // WebSocket connection management
  async connectWebSocket(): Promise<boolean> {
    try {
      const wsUrl = this.baseUrl.replace(/^http/, 'ws') + '/ws/chat';
      console.log('Connecting to WebSocket:', wsUrl);
      
      this.websocket = new WebSocket(wsUrl);
      
      this.websocket.onopen = () => {
        console.log('Chat WebSocket connected');
        this.notifyStatus({ connected: true, timestamp: Date.now() });
        ChatNotificationService.show('Connected to chat service', 'success');
      };
      
      this.websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'message') {
            const message: ChatMessage = {
              id: data.id || Date.now().toString(),
              content: data.content,
              sender: data.sender || 'ai',
              timestamp: new Date(data.timestamp || Date.now()),
              metadata: data.metadata
            };
            this.notifyMessage(message);
          } else if (data.type === 'status') {
            this.notifyStatus({
              connected: true,
              agent: data.agent,
              timestamp: Date.now()
            });
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      this.websocket.onclose = () => {
        console.log('Chat WebSocket disconnected');
        this.notifyStatus({ 
          connected: false, 
          timestamp: Date.now(),
          error: 'WebSocket connection closed'
        });
        ChatNotificationService.show('Chat service disconnected', 'warning');
      };
      
      this.websocket.onerror = (error) => {
        console.error('Chat WebSocket error:', error);
        this.notifyStatus({ 
          connected: false, 
          timestamp: Date.now(),
          error: 'WebSocket connection failed'
        });
        ChatNotificationService.show('Chat connection failed', 'error');
      };
      
      return true;
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      this.notifyStatus({ 
        connected: false, 
        timestamp: Date.now(),
        error: error instanceof Error ? error.message : 'Unknown connection error'
      });
      return false;
    }
  }

  // Send message via WebSocket
  async sendMessage(content: string, metadata?: any): Promise<void> {
    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }
    
    const message = {
      type: 'message',
      content,
      sender: 'user',
      timestamp: new Date().toISOString(),
      metadata
    };
    
    this.websocket.send(JSON.stringify(message));
  }

  // Get message history via HTTP
  async getMessageHistory(limit: number = 50): Promise<ChatMessage[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/chat/messages?limit=${limit}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      return data.messages.map((msg: any) => ({
        id: msg.id,
        content: msg.content,
        sender: msg.sender,
        timestamp: new Date(msg.timestamp),
        metadata: msg.metadata
      }));
    } catch (error) {
      console.error('Failed to load message history:', error);
      ChatNotificationService.show('Failed to load message history', 'error');
      return [];
    }
  }

  // Get chat configuration
  async getChatConfig(): Promise<ChatConfig> {
    try {
      const response = await fetch(`${this.baseUrl}/api/chat/config`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const config = await response.json();
      return {
        agentId: config.agentId || 'default',
        agentName: config.agentName || 'AI Assistant',
        systemPrompt: config.systemPrompt,
        maxMessages: config.maxMessages || 100,
        autoScroll: config.autoScroll !== false
      };
    } catch (error) {
      console.error('Failed to load chat config:', error);
      return {
        agentId: 'default',
        agentName: 'AI Assistant',
        maxMessages: 100,
        autoScroll: true
      };
    }
  }

  // Check agent status
  async getAgentStatus(): Promise<ConnectionStatus> {
    try {
      const response = await fetch(`${this.baseUrl}/api/agents/status`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      return {
        connected: true,
        agent: {
          available: data.available || false,
          name: data.name,
          type: data.type,
          capabilities: data.capabilities || []
        },
        timestamp: Date.now()
      };
    } catch (error) {
      console.error('Failed to check agent status:', error);
      return {
        connected: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: Date.now()
      };
    }
  }

  // Event subscription methods
  onMessage(callback: (message: ChatMessage) => void): void {
    this.messageCallbacks.push(callback);
  }

  onStatus(callback: (status: ConnectionStatus) => void): void {
    this.statusCallbacks.push(callback);
  }

  // Cleanup
  disconnect(): void {
    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
    }
    this.messageCallbacks = [];
    this.statusCallbacks = [];
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
    maxMessages: 100,
    autoScroll: true
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [isTyping, setIsTyping] = useState(false);

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

  // Initialize chat
  const initializeChat = useCallback(async () => {
    setIsLoading(true);
    
    try {
      // Load configuration
      const config = await backendClient.current.getChatConfig();
      setChatConfig(config);
      
      // Load message history
      const history = await backendClient.current.getMessageHistory(config.maxMessages);
      setMessages(history);
      
      // Check agent status
      const status = await backendClient.current.getAgentStatus();
      setConnectionStatus(status);
      
      // Connect WebSocket
      await backendClient.current.connectWebSocket();
      
      // Set up event listeners
      backendClient.current.onMessage((message: ChatMessage) => {
        setMessages(prev => [...prev, message]);
        setIsTyping(false);
      });
      
      backendClient.current.onStatus((status: ConnectionStatus) => {
        setConnectionStatus(status);
      });
      
    } catch (error) {
      console.error('Failed to initialize chat:', error);
      ChatNotificationService.show('Failed to initialize chat', 'error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Handle sending a message
  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() || !connectionStatus.connected) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: inputValue,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    try {
      await backendClient.current.sendMessage(inputValue);
    } catch (error) {
      console.error('Failed to send message:', error);
      ChatNotificationService.show('Failed to send message', 'error');
      setIsTyping(false);
      
      // Add error message
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: 'Failed to send message. Please check your connection.',
        sender: 'system',
        timestamp: new Date(),
        metadata: { messageType: 'error' }
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  }, [inputValue, connectionStatus.connected]);

  // Handle Enter key press
  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  // Clear chat messages
  const handleClearChat = useCallback(() => {
    setMessages([]);
    ChatNotificationService.show('Chat cleared', 'info');
  }, []);

  // Reconnect to chat
  const handleReconnect = useCallback(() => {
    initializeChat();
  }, [initializeChat]);

  // Initialize on mount
  useEffect(() => {
    initializeChat();
    
    return () => {
      backendClient.current.disconnect();
    };
  }, []);

  // Get status indicator color
  const getStatusColor = () => {
    if (!connectionStatus.connected) return 'bg-red-500';
    if (connectionStatus.agent?.available) return 'bg-green-500';
    return 'bg-yellow-500';
  };

  // Get message styling based on sender and theme
  const getMessageStyle = (message: ChatMessage) => {
    const baseStyle = "max-w-[80%] p-3 rounded-lg text-sm";
    
    if (message.sender === 'user') {
      return `${baseStyle} ${isDarkTheme ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'}`;
    } else if (message.sender === 'system') {
      return `${baseStyle} ${isDarkTheme ? 'bg-gray-600 text-gray-300' : 'bg-gray-300 text-gray-700'} italic`;
    } else {
      return `${baseStyle} ${isDarkTheme ? 'bg-gray-700 text-white' : 'bg-gray-200 text-gray-900'}`;
    }
  };

  const themeClasses = isDarkTheme
    ? 'bg-gray-900 text-white border-gray-700'
    : 'bg-white text-gray-900 border-gray-300';

  const headerThemeClasses = isDarkTheme
    ? 'bg-gray-800 border-gray-700'
    : 'bg-gray-50 border-gray-300';

  const inputThemeClasses = isDarkTheme
    ? 'bg-gray-800 text-white border-gray-600 focus:border-blue-500'
    : 'bg-white text-gray-900 border-gray-300 focus:border-blue-500';

  const buttonThemeClasses = isDarkTheme
    ? 'bg-blue-600 hover:bg-blue-700 text-white disabled:bg-gray-700'
    : 'bg-blue-500 hover:bg-blue-600 text-white disabled:bg-gray-400';

  if (isLoading) {
    return (
      <div className={`simple-chat-panel h-full flex items-center justify-center ${themeClasses} ${className}`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
          <div className="text-sm opacity-70">Initializing chat...</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`simple-chat-panel h-full flex flex-col border ${themeClasses} ${className}`}>
      {/* Header */}
      <div className={`flex items-center justify-between p-3 border-b ${headerThemeClasses}`}>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${getStatusColor()}`} />
          <span className="text-sm font-medium">{chatConfig.agentName}</span>
          {connectionStatus.agent?.type && (
            <span className="text-xs opacity-60">({connectionStatus.agent.type})</span>
          )}
          {isTyping && (
            <span className="text-xs opacity-60 animate-pulse">typing...</span>
          )}
        </div>
        <div className="flex space-x-2">
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

      {/* Messages container */}
      <div 
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto p-3 space-y-3"
      >
        {messages.length === 0 ? (
          <div className="text-center py-8 opacity-60">
            <div className="text-sm">
              {connectionStatus.connected 
                ? `${chatConfig.agentName} is ready to help! Send a message to get started.`
                : 'Connecting to chat service...'
              }
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={getMessageStyle(message)}>
                <div className="whitespace-pre-wrap">{message.content}</div>
                <div className="text-xs opacity-60 mt-1">
                  {message.timestamp.toLocaleTimeString()}
                  {message.metadata?.agentName && (
                    <span className="ml-2">• {message.metadata.agentName}</span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Input area */}
      <div className={`p-3 border-t ${headerThemeClasses}`}>
        <div className="flex space-x-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={connectionStatus.connected ? "Type your message..." : "Connecting..."}
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
        <div className="text-xs mt-2 opacity-60">
          Press Enter to send • Shift+Enter for new line
          {connectionStatus.agent?.capabilities && connectionStatus.agent.capabilities.length > 0 && (
            <span className="ml-2">
              • Capabilities: {connectionStatus.agent.capabilities.join(', ')}
            </span>
          )}
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
