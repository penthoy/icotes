/**
 * Services Module Index
 * 
 * Central export file for all ICUI-ICPY integration services.
 * Provides easy access to WebSocket service, HTTP client, and utility functions.
 */

export { WebSocketService, getWebSocketService, resetWebSocketService } from './websocket-service';
export { BackendClient, getBackendClient, resetBackendClient } from './backend-client';

// Re-export types for convenience
export type {
  ConnectionStatus,
  WebSocketMessage,
  JsonRpcRequest,
  JsonRpcResponse,
  JsonRpcNotification,
  EventHandler,
  EventHandlerMap,
  PendingRequest,
  ConnectionRecovery,
  ConnectionStatistics,
  BackendConfig,
  WorkspaceState,
  WorkspaceFile,
  WorkspacePanel,
  WorkspaceTerminal,
  WorkspaceLayout,
  WorkspacePreferences,
  WorkspaceStatistics,
  FileSystemEvent,
  FileInfo,
  DirectoryTree,
  FileSearchResult,
  TerminalSession,
  TerminalConfig,
  TerminalOutput,
  TerminalInput,
  CodeExecutionRequest,
  CodeExecutionResult,
  BackendEvent,
  WorkspaceEvent,
  FileEvent,
  TerminalEvent,
  ApiResponse,
  ApiError
} from '../types/backend-types';
