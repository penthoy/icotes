/**
 import React, { useState, useCallback, useRef, useEffect } from 'react';
import { 
  ChatMessage, 
  ConnectionStatus, 
  ChatConfig, 
  MessageOptions,
  AgentType 
} from '../types/chatTypes';
import { ChatBackendClient } from '../services/chatBackendClient';
import { notificationService } from '../services/notificationService';sages Hook - ICUI Framework
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
    console.log('🚀🚀🚀 CUSTOM AGENT MESSAGE FUNCTION CALLED 🚀🚀🚀', { content, agentName });
    console.log('🔥 This should appear in console when you send a message!');
    
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
        
        const timestamp = new Date().toISOString().split('T')[1];
        console.log(`🚀 [${timestamp}] Initiating WebSocket streaming for agent:`, agentName);
        console.log(`📡 [${timestamp}] WebSocket URL:`, wsUrl);
        
        const ws = new WebSocket(wsUrl);
        let streamingMessageId = `agent_${Date.now()}_${Math.random().toString(36).substring(2)}`;
        let accumulatedContent = '';
        let lastUpdateTime = 0;
        const UPDATE_THROTTLE_MS = 50; // Update every 50ms for smooth streaming
        
        // Timing measurements
        const sendButtonClickTime = performance.now();
        let firstChunkReceivedTime: number | null = null;
        let streamCompleteTime: number | null = null;
        
        console.log(`🔗 [${timestamp}] Created WebSocket connection, message ID:`, streamingMessageId);
        console.log(`⏱️ [${timestamp}] Send button clicked at:`, sendButtonClickTime);
        
        ws.onopen = () => {
          const wsConnectedTime = performance.now();
          console.log('✅ Custom Agent WebSocket connected for agent:', agentName);
          console.log(`⏱️ WebSocket connected after: ${(wsConnectedTime - sendButtonClickTime).toFixed(2)}ms`);
          
          // Send the message
          const messageToSend = {
            type: "message",
            content: content,
            history: chatHistory
          };
          console.log('📤 Sending message to WebSocket:', messageToSend);
          const messageSentTime = performance.now();
          ws.send(JSON.stringify(messageToSend));
          console.log(`⏱️ Message sent after: ${(messageSentTime - sendButtonClickTime).toFixed(2)}ms`);
        };

        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          const timestamp = new Date().toISOString().split('T')[1];
          const currentTime = performance.now();
          
          // Record first chunk timing
          if (data.type === "stream_chunk" && firstChunkReceivedTime === null) {
            firstChunkReceivedTime = currentTime;
            console.log(`🎯 [${timestamp}] FIRST CHUNK RECEIVED!`);
            console.log(`⏱️ Time from send button to first chunk: ${(firstChunkReceivedTime - sendButtonClickTime).toFixed(2)}ms`);
          }
          
          console.log(`🔄 [${timestamp}] Frontend WebSocket message:`, {
            type: data.type,
            contentLength: data.content?.length,
            chunk: data.content?.substring(0, 50) + (data.content?.length > 50 ? '...' : ''),
            accumulatedLength: accumulatedContent.length,
            timeSinceSend: `${(currentTime - sendButtonClickTime).toFixed(2)}ms`
          });
          
          if (data.type === "stream_chunk") {
            accumulatedContent += data.content;
            console.log(`📝 [${timestamp}] Adding chunk:`, {
              chunkLength: data.content.length,
              newAccumulatedLength: accumulatedContent.length,
              chunkContent: data.content
            });
            
            // Smart throttled updates for smooth streaming
            const updateUI = (forceUpdate = false) => {
              const now = Date.now();
              if (forceUpdate || now - lastUpdateTime >= UPDATE_THROTTLE_MS) {
                lastUpdateTime = now;
                
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
                  
                  console.log(`⚡ [${timestamp}] SMOOTH React update - chunk ${data.content.length} chars, total: ${accumulatedContent.length}`);
                  
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
              }
            };
            
            updateUI();
          } else if (data.type === "stream_complete") {
            streamCompleteTime = performance.now();
            const timestamp = new Date().toISOString().split('T')[1];
            
            console.log(`🏁 [${timestamp}] STREAM COMPLETE for agent:`, agentName);
            console.log(`⏱️ TIMING SUMMARY:`);
            console.log(`   📤 Send button to first chunk: ${firstChunkReceivedTime ? (firstChunkReceivedTime - sendButtonClickTime).toFixed(2) : 'N/A'}ms`);
            console.log(`   🔄 First chunk to completion: ${firstChunkReceivedTime ? (streamCompleteTime - firstChunkReceivedTime).toFixed(2) : 'N/A'}ms`);
            console.log(`   🎯 Total send to completion: ${(streamCompleteTime - sendButtonClickTime).toFixed(2)}ms`);
            console.log(`   📝 Final content length: ${accumulatedContent.length} characters`);
            
            // Force final update to ensure complete message is shown
            setMessages(prev => {
              const existingIndex = prev.findIndex(m => m.id === streamingMessageId);
              if (existingIndex >= 0) {
                const newMessages = [...prev];
                const completedMessage = { ...newMessages[existingIndex] };
                completedMessage.content = accumulatedContent; // Ensure final content
                if (completedMessage.metadata) {
                  completedMessage.metadata.isStreaming = false;
                  completedMessage.metadata.streamComplete = true;
                }
                newMessages[existingIndex] = completedMessage;
                console.log(`✅ [${timestamp}] Marked message as complete:`, completedMessage.id);
                return newMessages;
              }
              return prev;
            });
            ws.close();
          } else if (data.type === "error") {
            const timestamp = new Date().toISOString().split('T')[1];
            console.error(`❌ [${timestamp}] WebSocket error from backend:`, data.message);
            throw new Error(data.message);
          } else {
            const timestamp = new Date().toISOString().split('T')[1];
            console.log(`📦 [${timestamp}] Unknown message type:`, data);
          }
        };
        
        ws.onerror = (error) => {
          const timestamp = new Date().toISOString().split('T')[1];
          console.error(`❌ [${timestamp}] WebSocket connection error for agent ${agentName}:`, error);
          // Fallback to HTTP API
          fallbackToHttp();
        };
        
        ws.onclose = (event) => {
          const timestamp = new Date().toISOString().split('T')[1];
          console.log(`🔌 [${timestamp}] WebSocket closed for agent ${agentName}:`, {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean
          });
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
