// Chat Messages Hook - ICUI Framework
// Centralizes on the singleton chatBackendClient to avoid duplicate clients/sockets

import { useState, useCallback, useEffect, useRef } from 'react';
import { 
  ChatMessage, 
  ConnectionStatus, 
  ChatConfig,
  MessageOptions,
  AgentType
} from '../types/chatTypes';
import { chatBackendClient as singletonClient } from '../services/chat-backend-client-impl';
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
  
  // Typing state
  isTyping: boolean;
  
  // Actions
  sendMessage: (content: string, options?: MessageOptions) => Promise<void>;
  sendCustomAgentMessage: (content: string, agentName: string, options?: MessageOptions) => Promise<void>;
  stopStreaming: () => Promise<void>;
  clearMessages: () => Promise<void>;
  updateConfig: (config: Partial<ChatConfig>) => Promise<void>;
  connect: () => Promise<boolean>;
  disconnect: () => void;
  reloadMessages: (sessionId?: string) => Promise<void>;
  
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
  const [isTyping, setIsTyping] = useState(false);

  // Refs
  const clientRef = useRef<typeof singletonClient | null>(null);
  // For components that want to auto-scroll, we keep a virtual ref and provide a helper
  const messagesEndRef = useRef<HTMLElement | null>(null);
  const isInitializedRef = useRef(false);
  const isConnectingRef = useRef(false);
  // Streaming update throttling (50ms batching) to reduce re-renders under high chunk rates
  const streamingQueueRef = useRef<Map<string, ChatMessage>>(new Map());
  const flushScheduledRef = useRef<number | null>(null);
  const lastFlushTsRef = useRef<number>(0);
  const FLUSH_INTERVAL_MS = 50;
  // Keep a ref of latest state to build committed arrays without stale closures
  const stateRef = useRef<{ messages: ChatMessage[] }>({ messages: [] });
  useEffect(() => { stateRef.current.messages = messages; }, [messages]);

  const scheduleFlush = useCallback(() => {
    if (flushScheduledRef.current !== null) return;
    const doFlush = () => {
      flushScheduledRef.current = null;
      const queued = streamingQueueRef.current;
      if (queued.size === 0) return;
      // Build a new messages array applying latest streaming updates
      const byId: Record<string, ChatMessage> = Object.create(null);
      const current = stateRef.current.messages;
      const next = current.map(m => {
        byId[m.id] = m;
        return m;
      });
      let changed = false;
      queued.forEach((val, key) => {
        if (byId[key]) {
          const idx = next.findIndex(x => x.id === key);
          if (idx !== -1) {
            // Replace with latest content reference to trigger minimal diff
            next[idx] = val;
            changed = true;
          }
        } else {
          next.push(val);
          changed = true;
        }
      });
      queued.clear();
      if (changed) {
        setMessages(next.length > maxMessages ? next.slice(-maxMessages) : next);
      }
      lastFlushTsRef.current = performance.now();
    };
    // Align with animation frame for smoother UI; fallback timer if RAF not available
    if (typeof window !== 'undefined' && 'requestAnimationFrame' in window) {
      flushScheduledRef.current = window.requestAnimationFrame(() => {
        doFlush();
      }) as unknown as number;
    } else {
      // Use globalThis for SSR safety
      const g: any = typeof globalThis !== 'undefined' ? globalThis : undefined;
      if (g && typeof g.setTimeout === 'function') {
        flushScheduledRef.current = g.setTimeout(doFlush, FLUSH_INTERVAL_MS) as unknown as number;
      } else {
        // Immediate flush as last resort
        doFlush();
      }
    }
  }, [maxMessages]);

  // Get or create client instance
  const getClient = useCallback(() => {
    if (!clientRef.current) {
      clientRef.current = singletonClient;
      
      // Set up message callback
      clientRef.current.onMessage((message: ChatMessage) => {
        // Ignore user messages that are broadcast back
        if (message.sender === 'user') {
          return;
        }
        // If this is a streaming update, coalesce updates within 50ms window
        const isStreaming = Boolean(message.metadata?.isStreaming && !message.metadata?.streamComplete);
        if (isStreaming) {
          streamingQueueRef.current.set(message.id, message);
          // Throttle to ~20fps to cut render pressure
          const now = typeof performance !== 'undefined' ? performance.now() : Date.now();
          if (now - lastFlushTsRef.current >= FLUSH_INTERVAL_MS) {
            scheduleFlush();
          } else if (flushScheduledRef.current === null) {
            scheduleFlush();
          }
        } else {
          // Non-streaming (or final) messages: commit immediately
          setMessages(prevMessages => {
            const existingIndex = prevMessages.findIndex(m => m.id === message.id);
            if (existingIndex >= 0) {
              const updatedMessages = [...prevMessages];
              updatedMessages[existingIndex] = { ...message };
              return updatedMessages.length > maxMessages ? updatedMessages.slice(-maxMessages) : updatedMessages;
            }
            const newMessages = [...prevMessages, message];
            return newMessages.length > maxMessages ? newMessages.slice(-maxMessages) : newMessages;
          });
        }

        // Heuristics: if a streaming assistant message arrives, set typing true until completed
        const streaming = message.metadata?.isStreaming && !message.metadata?.streamComplete;
        setIsTyping(Boolean(streaming));
      });
      
      // Set up status callback
  clientRef.current.onStatus(setConnectionStatus);

      // Set up typing callback from backend
      clientRef.current.onTyping((typing: boolean) => {
        setIsTyping(typing);
      });
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
        const history = await client.getMessageHistory(maxMessages, client.currentSession);
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
      if (process.env.NODE_ENV === 'development') {
        console.log('[useChatMessages] Connect called, current state:', {
          isConnected: client.isConnected,
          isConnecting: isConnectingRef.current,
          isInitialized: isInitializedRef.current
        });
      }
      
      // If already connected, still ensure this hook instance initializes once
      if (client.isConnected) {
        if (!isInitializedRef.current) {
          if (process.env.NODE_ENV === 'development') {
            console.log('[useChatMessages] Client already connected; running one-time initialize for this consumer');
          }
          await initialize();
          isInitializedRef.current = true;
        }
        return true;
      }

      if (isConnectingRef.current) return true;
      isConnectingRef.current = true;
      
      const success = await client.connectWebSocket();
      if (process.env.NODE_ENV === 'development') {
        console.log('[useChatMessages] Connect result:', success);
      }
      
      if (success && !isInitializedRef.current) {
        if (process.env.NODE_ENV === 'development') {
          console.log('[useChatMessages] Initializing after successful connection');
        }
        await initialize();
        isInitializedRef.current = true;
      }
      
      return success;
    } catch (error) {
      console.error('[useChatMessages] Failed to connect:', error);
      return false;
    } finally {
      isConnectingRef.current = false;
    }
  }, [getClient, initialize]);

  // Disconnect
  const disconnect = useCallback(() => {
    // Keep singleton connection alive across consumers; no-op here
  }, []);

  // Send message
  const sendMessage = useCallback(async (content: string, options: MessageOptions = {}) => {
    try {
      const client = getClient();
      
      // Immediately reflect that the assistant is working to provide instant feedback
      // This will be overridden by real typing/stream events from the backend
      setIsTyping(true);

      // Add user message immediately to UI
      const userMessage: ChatMessage = {
        id: `user_${Date.now()}_${Math.random().toString(36).substring(2)}`,
        content,
        sender: 'user',
        timestamp: new Date(),
        // Phase 2: Include attachments in user message
        attachments: options.attachments,
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
      // Reset typing state on error so the indicator doesn't get stuck
      setIsTyping(false);
    }
  }, [getClient, config, maxMessages]);

  // Send message to custom agent
  // Send message to custom agent - using main branch pattern
  const sendCustomAgentMessage = useCallback(async (content: string, agentName: string, options: MessageOptions = {}) => {
    try {
      const client = getClient();
      
      // Instant UI feedback
      setIsTyping(true);

      // Add user message immediately to UI
      const userMessage: ChatMessage = {
        id: `user_${Date.now()}_${Math.random().toString(36).substring(2)}`,
        content,
        sender: 'user',
        timestamp: new Date(),
        // Include attachments for custom agent as well
        attachments: options.attachments,
        metadata: {
          messageType: 'text',
          agentType: agentName as any
        }
      };
      
      setMessages(prev => {
        const newMessages = [...prev, userMessage];
        return newMessages.length > maxMessages ? newMessages.slice(-maxMessages) : newMessages;
      });
      
      // Send via existing chat client with custom agent type
      await client.sendMessage(content, {
        agentType: agentName as any,
        attachments: options.attachments
      });
    } catch (error) {
      console.error('Failed to send message to custom agent:', error);
      notificationService.error(`Failed to send message to ${agentName}`);
      setIsTyping(false);
    }
  }, [getClient, maxMessages]);

  // Stop streaming
  const stopStreaming = useCallback(async () => {
    try {
      const client = getClient();
      await client.stopStreaming();
      setIsTyping(false);
      notificationService.show('Streaming stopped', 'info');
    } catch (error) {
      console.error('Failed to stop streaming:', error);
      notificationService.error('Failed to stop streaming');
    }
  }, [getClient]);

  // Clear messages
  const clearMessages = useCallback(async () => {
    try {
      const client = getClient();
      await client.clearMessages();
      setMessages([]);
      
      // Reload message history to ensure UI is synchronized with backend
      if (persistence) {
        const history = await client.getMessageHistory(maxMessages);
        setMessages(history);
      }
    } catch (error) {
      console.error('Failed to clear messages:', error);
      notificationService.error('Failed to clear messages');
    }
  }, [getClient, persistence, maxMessages]);

  // Reload messages for a specific session
  const reloadMessages = useCallback(async (sessionId?: string) => {
    try {
      setIsLoading(true);
      const client = getClient();
      
      // If sessionId is provided, ensure the client's current session is updated
      if (sessionId) {
        client.setCurrentSession(sessionId);
      }
      
      const effectiveSessionId = sessionId || client.currentSession;
      const history = await client.getMessageHistory(maxMessages, effectiveSessionId);
      
      setMessages(history);
    } catch (error) {
      console.error('Failed to reload messages:', error);
      notificationService.error('Failed to reload messages');
    } finally {
      setIsLoading(false);
    }
  }, [getClient, maxMessages]);

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
    if (!autoScroll) return;
    try {
      const el = document.querySelector('[data-icui-chat-end]') as HTMLElement | null;
      (el || messagesEndRef.current)?.scrollIntoView({ behavior: 'smooth' });
    } catch {
      // no-op
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
  }, [autoConnect, connect]);

  // Computed values
  const isConnected = connectionStatus.connected;
  const hasMessages = messages.length > 0;

  return {
    // State
    messages,
    connectionStatus,
    config,
    isLoading,
    
    // Typing state
    isTyping,
    
    // Actions
    sendMessage,
    sendCustomAgentMessage,
    stopStreaming,
    clearMessages,
    updateConfig,
    connect,
    disconnect,
    reloadMessages,
    
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
