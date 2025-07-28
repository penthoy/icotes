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
  sendCustomAgentMessage: (content: string, agentName: string) => Promise<void>;
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

  // Send message to custom agent
  const sendCustomAgentMessage = useCallback(async (content: string, agentName: string) => {
    try {
      setIsLoading(true);
      
      // Add user message immediately to UI
      const userMessage: ChatMessage = {
        id: `user_${Date.now()}_${Math.random().toString(36).substring(2)}`,
        content,
        sender: 'user',
        timestamp: new Date(),
        metadata: {
          messageType: 'text',
          agentType: agentName as any
        }
      };
      
      setMessages(prev => {
        const newMessages = [...prev, userMessage];
        return newMessages.length > maxMessages ? newMessages.slice(-maxMessages) : newMessages;
      });

      // Prepare chat history for the API call
      const chatHistory = messages.map(msg => ({
        role: msg.sender === 'user' ? 'user' : 'assistant',
        content: msg.content
      }));

      // Try WebSocket streaming first, fallback to HTTP
      const useStreaming = true; // You can make this configurable
      
      if (useStreaming) {
        // Use WebSocket for streaming
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/custom-agents/${agentName}/stream`;
        
        const ws = new WebSocket(wsUrl);
        let streamingMessageId = `agent_${Date.now()}_${Math.random().toString(36).substring(2)}`;
        let accumulatedContent = '';
        
        ws.onopen = () => {
          // Send the message
          ws.send(JSON.stringify({
            type: "message",
            content: content,
            history: chatHistory
          }));
        };
        
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          
          if (data.type === "stream_chunk") {
            accumulatedContent += data.content;
            
            // Update or create the streaming message
            setMessages(prev => {
              const existingIndex = prev.findIndex(m => m.id === streamingMessageId);
              
              const streamingMessage: ChatMessage = {
                id: streamingMessageId,
                content: accumulatedContent,
                sender: 'ai',
                timestamp: new Date(),
                metadata: {
                  messageType: 'text',
                  agentType: agentName as any,
                  isStreaming: true
                }
              };
              
              if (existingIndex >= 0) {
                // Update existing message
                const newMessages = [...prev];
                newMessages[existingIndex] = streamingMessage;
                return newMessages.length > maxMessages ? newMessages.slice(-maxMessages) : newMessages;
              } else {
                // Add new message
                const newMessages = [...prev, streamingMessage];
                return newMessages.length > maxMessages ? newMessages.slice(-maxMessages) : newMessages;
              }
            });
          } else if (data.type === "stream_complete") {
            // Mark streaming as complete
            setMessages(prev => {
              const existingIndex = prev.findIndex(m => m.id === streamingMessageId);
              if (existingIndex >= 0) {
                const newMessages = [...prev];
                const completedMessage = { ...newMessages[existingIndex] };
                if (completedMessage.metadata) {
                  completedMessage.metadata.isStreaming = false;
                  completedMessage.metadata.streamComplete = true;
                }
                newMessages[existingIndex] = completedMessage;
                return newMessages;
              }
              return prev;
            });
            ws.close();
          } else if (data.type === "error") {
            throw new Error(data.message);
          }
        };
        
        ws.onerror = () => {
          // Fallback to HTTP API
          fallbackToHttp();
        };
        
        const fallbackToHttp = async () => {
          try {
            const response = await fetch('/api/custom-agents/chat', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                agent_name: agentName,
                message: content,
                history: chatHistory
              }),
            });

            const data = await response.json();
            
            if (data.success) {
              // Add agent response to UI
              const agentMessage: ChatMessage = {
                id: `agent_${Date.now()}_${Math.random().toString(36).substring(2)}`,
                content: data.response,
                sender: 'ai',
                timestamp: new Date(),
                metadata: {
                  messageType: 'text',
                  agentType: agentName as any
                }
              };
              
              setMessages(prev => {
                const newMessages = [...prev, agentMessage];
                return newMessages.length > maxMessages ? newMessages.slice(-maxMessages) : newMessages;
              });
            } else {
              throw new Error(data.error || 'Custom agent call failed');
            }
          } catch (httpError) {
            console.error('HTTP fallback also failed:', httpError);
            throw httpError;
          }
        };
      } else {
        // Use HTTP API directly (non-streaming)
        const response = await fetch('/api/custom-agents/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            agent_name: agentName,
            message: content,
            history: chatHistory
          }),
        });

        const data = await response.json();
        
        if (data.success) {
          // Add agent response to UI
          const agentMessage: ChatMessage = {
            id: `agent_${Date.now()}_${Math.random().toString(36).substring(2)}`,
            content: data.response,
            sender: 'ai',
            timestamp: new Date(),
            metadata: {
              messageType: 'text',
              agentType: agentName as any
            }
          };
          
          setMessages(prev => {
            const newMessages = [...prev, agentMessage];
            return newMessages.length > maxMessages ? newMessages.slice(-maxMessages) : newMessages;
          });
        } else {
          throw new Error(data.error || 'Custom agent call failed');
        }
      }
      
    } catch (error) {
      console.error('Failed to send message to custom agent:', error);
      notificationService.error(`Failed to send message to ${agentName}`);
    } finally {
      setIsLoading(false);
    }
  }, [messages, maxMessages]);

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
    sendCustomAgentMessage,
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
