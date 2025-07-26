/**
 * Chat Messages Hook - ICUI Framework
 * Custom React hook for managing chat message state and operations
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { 
  ChatMessage, 
  ConnectionStatus, 
  ChatConfig,
  MessageOptions,
  AgentType
} from '../types/chatTypes';
import { ChatBackendClient } from '../services/chatBackendClient';
import { notificationService } from '../services/notificationService';

export interface UseChatMessagesOptions {
  autoConnect?: boolean;
  maxMessages?: number;
  persistence?: boolean;
  autoScroll?: boolean;
}

export interface UseChatMessagesReturn {
  // State
  messages: ChatMessage[];
  connectionStatus: ConnectionStatus;
  config: ChatConfig | null;
  isLoading: boolean;
  
  // Actions
  sendMessage: (content: string, options?: MessageOptions) => Promise<void>;
  clearMessages: () => Promise<void>;
  updateConfig: (config: Partial<ChatConfig>) => Promise<void>;
  connect: () => Promise<boolean>;
  disconnect: () => void;
  
  // Agent operations
  createAgent: (template: string, config?: any) => Promise<string>;
  executeAgentTask: (agentId: string, task: any) => Promise<void>;
  getAgentStatus: () => Promise<void>;
  
  // UI helpers
  scrollToBottom: () => void;
  isConnected: boolean;
  hasMessages: boolean;
}

export const useChatMessages = (options: UseChatMessagesOptions = {}): UseChatMessagesReturn => {
  const {
    autoConnect = true,
    maxMessages = 100,
    persistence = true,
    autoScroll = true
  } = options;

  // State
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    connected: false,
    timestamp: Date.now()
  });
  const [config, setConfig] = useState<ChatConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Refs
  const clientRef = useRef<ChatBackendClient | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isInitializedRef = useRef(false);

  // Get or create client instance
  const getClient = useCallback((): ChatBackendClient => {
    if (!clientRef.current) {
      clientRef.current = new ChatBackendClient();
      
      // Set up message callback
      clientRef.current.onMessage((message: ChatMessage) => {
        // Ignore user messages that are broadcast back
        if (message.sender === 'user') {
          return;
        }
        
        setMessages(prevMessages => {
          // Find existing message by ID
          const existingIndex = prevMessages.findIndex(m => m.id === message.id);
          
          if (existingIndex >= 0) {
            // Update existing message
            const updatedMessages = [...prevMessages];
            updatedMessages[existingIndex] = { ...message };
            
            // Apply max messages limit
            if (updatedMessages.length > maxMessages) {
              return updatedMessages.slice(-maxMessages);
            }
            
            return updatedMessages;
          } else {
            // Add new message
            const newMessages = [...prevMessages, message];
            
            // Apply max messages limit
            if (newMessages.length > maxMessages) {
              return newMessages.slice(-maxMessages);
            }
            
            return newMessages;
          }
        });
      });
      
      // Set up status callback
      clientRef.current.onStatus(setConnectionStatus);
    }
    
    return clientRef.current;
  }, [maxMessages]);

  // Initialize chat
  const initialize = useCallback(async () => {
    try {
      setIsLoading(true);
      const client = getClient();
      
      // Load configuration
      const chatConfig = await client.getChatConfig();
      setConfig(chatConfig);
      
      // Load message history if persistence is enabled
      if (persistence) {
        const history = await client.getMessageHistory(maxMessages);
        setMessages(history);
      }
      
      // Get initial agent status
      const status = await client.getAgentStatus();
      setConnectionStatus(status);
      
    } catch (error) {
      console.error('Failed to initialize chat:', error);
      notificationService.error('Failed to initialize chat');
    } finally {
      setIsLoading(false);
    }
  }, [getClient, maxMessages, persistence]);

  // Connect to WebSocket
  const connect = useCallback(async (): Promise<boolean> => {
    try {
      const client = getClient();
      const success = await client.connectWebSocket();
      
      if (success && !isInitializedRef.current) {
        await initialize();
        isInitializedRef.current = true;
      }
      
      return success;
    } catch (error) {
      console.error('Failed to connect:', error);
      return false;
    }
  }, [getClient, initialize]);

  // Disconnect
  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect();
    }
  }, []);

  // Send message
  const sendMessage = useCallback(async (content: string, options: MessageOptions = {}) => {
    try {
      const client = getClient();
      
      // Add user message immediately to UI
      const userMessage: ChatMessage = {
        id: `user_${Date.now()}_${Math.random().toString(36).substring(2)}`,
        content,
        sender: 'user',
        timestamp: new Date(),
        metadata: {
          messageType: 'text',
          agentType: options.agentType || config?.agentType || 'openai'
        }
      };
      
      setMessages(prev => {
        const newMessages = [...prev, userMessage];
        return newMessages.length > maxMessages ? newMessages.slice(-maxMessages) : newMessages;
      });
      
      // Send via backend
      await client.sendMessage(content, {
        ...options,
        agentType: options.agentType || config?.agentType || 'openai'
      });
      
    } catch (error) {
      console.error('Failed to send message:', error);
      notificationService.error('Failed to send message');
    }
  }, [getClient, config, maxMessages]);

  // Clear messages
  const clearMessages = useCallback(async () => {
    try {
      const client = getClient();
      await client.clearMessages();
      setMessages([]);
    } catch (error) {
      console.error('Failed to clear messages:', error);
      notificationService.error('Failed to clear messages');
    }
  }, [getClient]);

  // Update configuration
  const updateConfig = useCallback(async (newConfig: Partial<ChatConfig>) => {
    try {
      const client = getClient();
      await client.updateChatConfig(newConfig);
      
      // Update local config
      setConfig(prev => prev ? { ...prev, ...newConfig } : null);
    } catch (error) {
      console.error('Failed to update config:', error);
      notificationService.error('Failed to update configuration');
    }
  }, [getClient]);

  // Create agent
  const createAgent = useCallback(async (template: string, agentConfig?: any): Promise<string> => {
    const client = getClient();
    return await client.createAgent(template, agentConfig);
  }, [getClient]);

  // Execute agent task
  const executeAgentTask = useCallback(async (agentId: string, task: any) => {
    const client = getClient();
    await client.executeAgentTask(agentId, task);
  }, [getClient]);

  // Get agent status
  const getAgentStatus = useCallback(async () => {
    try {
      const client = getClient();
      const status = await client.getAgentStatus();
      setConnectionStatus(status);
    } catch (error) {
      console.error('Failed to get agent status:', error);
    }
  }, [getClient]);

  // Scroll to bottom
  const scrollToBottom = useCallback(() => {
    if (messagesEndRef.current && autoScroll) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [autoScroll]);

  // Auto-scroll when messages change
  useEffect(() => {
    if (autoScroll) {
      scrollToBottom();
    }
  }, [messages, autoScroll, scrollToBottom]);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect && !isInitializedRef.current) {
      connect();
    }
    
    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  // Computed values
  const isConnected = connectionStatus.connected;
  const hasMessages = messages.length > 0;

  return {
    // State
    messages,
    connectionStatus,
    config,
    isLoading,
    
    // Actions
    sendMessage,
    clearMessages,
    updateConfig,
    connect,
    disconnect,
    
    // Agent operations
    createAgent,
    executeAgentTask,
    getAgentStatus,
    
    // UI helpers
    scrollToBottom,
    isConnected,
    hasMessages
  };
};
