/**
 * Backend Communication Types
 * 
 * TypeScript interfaces for communication between ICUI frontend and ICPY backend.
 * These types define the structure of messages, responses, and state objects
 * used in WebSocket and HTTP communication.
 */

// Connection and WebSocket types
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface WebSocketMessage {
  id?: string;
  type: string;
  payload?: any;
  timestamp?: number;
}

export interface JsonRpcRequest {
  jsonrpc: '2.0';
  method: string;
  params?: any;
  id?: string | number;
}

export interface JsonRpcResponse {
  jsonrpc: '2.0';
  result?: any;
  error?: {
    code: number;
    message: string;
    data?: any;
  };
  id?: string | number;
}

export interface JsonRpcNotification {
  jsonrpc: '2.0';
  method: string;
  params?: any;
}

// Workspace State Types
export interface WorkspaceState {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  last_accessed: string;
  files: WorkspaceFile[];
  panels: WorkspacePanel[];
  terminals: WorkspaceTerminal[];
  layout: WorkspaceLayout;
  preferences: WorkspacePreferences;
  statistics: WorkspaceStatistics;
}

export interface WorkspaceFile {
  id: string;
  name: string;
  path: string;
  content?: string;
  language: string;
  modified: boolean;
  created_at: string;
  last_modified: string;
  size: number;
  is_active: boolean;
}

export interface WorkspacePanel {
  id: string;
  type: 'editor' | 'terminal' | 'explorer' | 'chat' | 'output' | 'debug';
  title: string;
  position: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  is_active: boolean;
  config: Record<string, any>;
}

export interface WorkspaceTerminal {
  id: string;
  name: string;
  command: string;
  cwd: string;
  env: Record<string, string>;
  created_at: string;
  last_used: string;
  is_active: boolean;
  session_id?: string;
  status: 'running' | 'stopped' | 'error';
}

export interface WorkspaceLayout {
  id: string;
  name: string;
  panels: WorkspacePanel[];
  created_at: string;
  is_default: boolean;
}

export interface WorkspacePreferences {
  theme: string;
  font_size: number;
  font_family: string;
  tab_size: number;
  word_wrap: boolean;
  line_numbers: boolean;
  auto_save: boolean;
  auto_save_delay: number;
}

export interface WorkspaceStatistics {
  files_count: number;
  terminals_count: number;
  panels_count: number;
  total_characters: number;
  total_lines: number;
  last_updated: string;
}

// File System Types
export interface FileSystemEvent {
  type: 'created' | 'modified' | 'deleted' | 'moved' | 'renamed';
  path: string;
  new_path?: string;
  timestamp: string;
  size?: number;
  is_directory: boolean;
}

export interface FileInfo {
  path: string;
  name: string;
  size: number;
  type: string;
  extension: string;
  is_directory: boolean;
  is_binary: boolean;
  permissions: string;
  created_at: string;
  modified_at: string;
  accessed_at: string;
}

export interface DirectoryTree {
  path: string;
  name: string;
  type: 'directory' | 'file';
  children?: DirectoryTree[];
  size?: number;
  modified_at: string;
}

export interface FileSearchResult {
  path: string;
  name: string;
  type: string;
  size: number;
  matches: number;
  snippet?: string;
  line_number?: number;
}

// Terminal Types
export interface TerminalSession {
  id: string;
  name: string;
  command: string;
  cwd: string;
  env: Record<string, string>;
  created_at: string;
  last_used: string;
  is_active: boolean;
  pid?: number;
  status: 'running' | 'stopped' | 'error';
}

export interface TerminalConfig {
  name?: string;
  command?: string;
  cwd?: string;
  env?: Record<string, string>;
  rows?: number;
  cols?: number;
}

export interface TerminalOutput {
  session_id: string;
  data: string;
  timestamp: string;
  type: 'stdout' | 'stderr';
}

export interface TerminalInput {
  session_id: string;
  data: string;
  timestamp: string;
}

// Code Execution Types
export interface CodeExecutionRequest {
  file_id: string;
  content: string;
  language: string;
  working_directory?: string;
  environment?: Record<string, string>;
}

export interface CodeExecutionResult {
  success: boolean;
  output: string;
  error?: string;
  execution_time: number;
  exit_code?: number;
}

// Event Types
export interface BackendEvent {
  type: string;
  data: any;
  timestamp: string;
  source: string;
}

export interface WorkspaceEvent extends BackendEvent {
  workspace_id: string;
}

export interface FileEvent extends BackendEvent {
  file_path: string;
  file_id?: string;
}

export interface TerminalEvent extends BackendEvent {
  terminal_id: string;
  session_id?: string;
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}

export interface ApiError {
  code: number;
  message: string;
  details?: any;
}

// Service Configuration Types
export interface BackendConfig {
  websocket_url: string;
  http_base_url: string;
  reconnect_attempts: number;
  reconnect_delay: number;
  request_timeout: number;
  heartbeat_interval: number;
  enable_logging?: boolean;
  auto_connect?: boolean;
}

// Event Handler Types
export type EventHandler<T = any> = (data: T) => void;
export type EventHandlerMap = Map<string, EventHandler[]>;

// Request/Response Correlation Types
export interface PendingRequest {
  id: string;
  method: string;
  timestamp: number;
  resolve: (value: any) => void;
  reject: (error: any) => void;
  timeout?: NodeJS.Timeout;
}

// Connection Recovery Types
export interface ConnectionRecovery {
  last_message_id?: string;
  subscription_topics: string[];
  pending_requests: PendingRequest[];
  connection_timestamp: number;
}

// Statistics Types
export interface ConnectionStatistics {
  messages_sent: number;
  messages_received: number;
  reconnect_count: number;
  last_reconnect: string;
  uptime: number;
  latency: number;
}
