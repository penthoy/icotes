/**
 * Chat Types - ICUI Framework
 * Type definitions for chat messaging system
 */

// Agent framework types
export type AgentType = 'openai' | 'crewai' | 'langchain' | 'langgraph';

// Message sender types
export type MessageSender = 'user' | 'ai' | 'system';

// Message types
export type MessageType = 'text' | 'code' | 'error' | 'system' | 'streaming';

// Agent status types
export type AgentStatus = 'idle' | 'busy' | 'error' | 'starting';

// Chat message interface
export interface ChatMessage {
  id: string;
  content: string;
  sender: MessageSender;
  timestamp: Date;
  metadata?: {
    agentId?: string;
    agentName?: string;
    agentType?: AgentType;
    messageType?: MessageType;
    workflowId?: string;
    taskId?: string;
    capabilities?: string[];
    context?: any;
    isStreaming?: boolean;
    streamComplete?: boolean;
  };
}

// Connection status interface
export interface ConnectionStatus {
  connected: boolean;
  agent?: {
    available: boolean;
    id?: string;
    name?: string;
    type?: AgentType;
    capabilities?: string[];
    status?: AgentStatus;
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

// Chat configuration interface
export interface ChatConfig {
  agentId: string;
  agentName: string;
  agentType?: AgentType;
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

// Message sending options
export interface MessageOptions {
  agentType?: AgentType;
  framework?: any;
  streaming?: boolean;
  context?: any;
}

// WebSocket message types
export interface WebSocketMessage {
  type: string;
  content?: string;
  sender?: MessageSender;
  timestamp?: string;
  sessionId?: string;
  options?: MessageOptions;
  [key: string]: any;
}

// Streaming message data
export interface StreamingMessageData {
  type: 'message_stream';
  id: string;
  chunk?: string;
  stream_start?: boolean;
  stream_chunk?: boolean;
  stream_end?: boolean;
  agentId?: string;
  agentName?: string;
  agentType?: AgentType;
  timestamp?: string;
  session_id?: string;
  metadata?: Record<string, any>;
}

// Chat event callbacks
export type ChatMessageCallback = (message: ChatMessage) => void;
export type ChatStatusCallback = (status: ConnectionStatus) => void;
