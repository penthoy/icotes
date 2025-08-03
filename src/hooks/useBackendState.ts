/**
 * Backend State Hook for ICUI-ICPY Integration
 * 
 * This hook provides a comprehensive interface for managing application state
 * synchronized with the ICPY backend. It handles connection status, workspace
 * state, files, terminals, and provides actions for backend operations.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { getWebSocketService, getBackendClient } from '../services';
import type { 
  ConnectionStatus, 
  WorkspaceState, 
  WorkspaceFile, 
  TerminalSession 
} from '../types/backend-types';
import type { ICUIEditorFile } from '../icui/components/panels/ICUIEditorPanel';

export interface BackendStateHook {
  // Connection state
  connectionStatus: ConnectionStatus;
  isConnected: boolean;
  
  // Workspace state
  workspaceState: WorkspaceState | null;
  files: ICUIEditorFile[];
  terminals: TerminalSession[];
  
  // Actions
  actions: {
    // Connection management
    connect: () => Promise<void>;
    disconnect: () => void;
    
    // Workspace operations
    fetchWorkspaceState: () => Promise<WorkspaceState>;
    updateWorkspaceState: (updates: Partial<WorkspaceState>) => Promise<void>;
    
    // File operations
    createFile: (path: string, content?: string) => Promise<ICUIEditorFile>;
    updateFile: (fileId: string, content: string) => Promise<void>;
    deleteFile: (fileId: string) => Promise<void>;
    saveFile: (fileId: string, content: string) => Promise<void>;
    openFile: (fileId: string) => Promise<void>;
    closeFile: (fileId: string) => Promise<void>;
    
    // Directory operations
    getDirectoryContents: (path: string) => Promise<any[]>;
    createDirectory: (path: string) => Promise<void>;
    getDirectoryTree: (path?: string) => Promise<any>;
    
    // Terminal operations
    createTerminal: (name?: string) => Promise<TerminalSession>;
    startTerminal: (terminalId: string) => Promise<void>;
    destroyTerminal: (terminalId: string) => Promise<void>;
    sendTerminalInput: (terminalId: string, input: string) => Promise<void>;
    
    // Code execution
    executeCode: (fileId: string, content: string, language: string) => Promise<void>;
  };
  
  // Error state
  error: string | null;
  clearError: () => void;
}

/**
 * Custom hook for backend state management
 */
export const useBackendState = (): BackendStateHook => {
  // Services
  const wsService = useRef(getWebSocketService());
  const backendClient = useRef(getBackendClient());
  
  // State
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [workspaceState, setWorkspaceState] = useState<WorkspaceState | null>(null);
  const [files, setFiles] = useState<ICUIEditorFile[]>([]);
  const [terminals, setTerminals] = useState<TerminalSession[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  // Computed state
  const isConnected = connectionStatus === 'connected';
  
  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);
  
  /**
   * Handle errors with proper error state management
   */
  const handleError = useCallback((error: any, operation: string) => {
    const errorMessage = error?.message || `Failed to ${operation}`;
    console.error(`Backend operation failed [${operation}]:`, error);
    setError(errorMessage);
  }, []);
  
  /**
   * Convert WorkspaceFile to ICUIEditorFile
   */
  const convertToICUIFile = useCallback((workspaceFile: WorkspaceFile): ICUIEditorFile => {
    return {
      id: workspaceFile.id,
      name: workspaceFile.name,
      language: workspaceFile.language || 'javascript',
      content: workspaceFile.content || '',
      modified: workspaceFile.modified || false
    };
  }, []);
  
  /**
   * Connection management
   */
  const connect = useCallback(async () => {
    try {
      await wsService.current.connect();
      setConnectionStatus('connected');
    } catch (error) {
      handleError(error, 'connect to backend');
      setConnectionStatus('disconnected');
    }
  }, [handleError]);
  
  const disconnect = useCallback(() => {
    try {
      wsService.current.disconnect();
      setConnectionStatus('disconnected');
    } catch (error) {
      handleError(error, 'disconnect from backend');
    }
  }, [handleError]);
  
  /**
   * Workspace operations
   */
  const fetchWorkspaceState = useCallback(async (): Promise<WorkspaceState> => {
    try {
      const state = await backendClient.current.getWorkspaceState();
      setWorkspaceState(state);
      
      // Update files from workspace state
      if (state.files) {
        const icuiFiles = state.files.map(convertToICUIFile);
        setFiles(icuiFiles);
      }
      
      // Update terminals from workspace state
      if (state.terminals) {
        setTerminals(state.terminals);
      }
      
      return state;
    } catch (error) {
      handleError(error, 'fetch workspace state');
      throw error;
    }
  }, [convertToICUIFile, handleError]);
  
  const updateWorkspaceState = useCallback(async (updates: Partial<WorkspaceState>) => {
    try {
      const updatedState = await backendClient.current.updateWorkspace(updates);
      setWorkspaceState(updatedState);
    } catch (error) {
      handleError(error, 'update workspace state');
    }
  }, [handleError]);
  
  /**
   * File operations
   */
  const createFile = useCallback(async (path: string, content: string = ''): Promise<ICUIEditorFile> => {
    try {
      const workspaceFile = await backendClient.current.createFile(path, content);
      const icuiFile = convertToICUIFile(workspaceFile);
      
      setFiles(prev => [...prev, icuiFile]);
      return icuiFile;
    } catch (error) {
      handleError(error, 'create file');
      throw error;
    }
  }, [convertToICUIFile, handleError]);
  
  const updateFile = useCallback(async (fileId: string, content: string) => {
    try {
      await backendClient.current.updateFile(fileId, content);
      
      // Update local state
      setFiles(prev => prev.map(file => 
        file.id === fileId 
          ? { ...file, content, modified: true }
          : file
      ));
    } catch (error) {
      handleError(error, 'update file');
    }
  }, [handleError]);
  
  const deleteFile = useCallback(async (fileId: string) => {
    try {
      await backendClient.current.deleteFile(fileId);
      
      // Update local state
      setFiles(prev => prev.filter(file => file.id !== fileId));
    } catch (error) {
      handleError(error, 'delete file');
    }
  }, [handleError]);
  
  const saveFile = useCallback(async (fileId: string, content: string) => {
    try {
      await backendClient.current.saveFile(fileId, content);
      
      // Update local state
      setFiles(prev => prev.map(file => 
        file.id === fileId 
          ? { ...file, content, modified: false }
          : file
      ));
    } catch (error) {
      handleError(error, 'save file');
    }
  }, [handleError]);
  
  const openFile = useCallback(async (fileId: string) => {
    try {
      await backendClient.current.setActiveFile(fileId);
    } catch (error) {
      handleError(error, 'open file');
    }
  }, [handleError]);
  
  const closeFile = useCallback(async (fileId: string) => {
    try {
      await backendClient.current.closeFile(fileId);
      
      // Update local state
      setFiles(prev => prev.filter(file => file.id !== fileId));
    } catch (error) {
      handleError(error, 'close file');
    }
  }, [handleError]);
  
  /**
   * Terminal operations
   */
  
  /**
   * Load terminals from backend
   */
  const loadTerminals = useCallback(async () => {
    try {
      const backendTerminals = await backendClient.current.getTerminals();
      setTerminals(backendTerminals);
    } catch (error) {
      console.error('Failed to load terminals:', error);
      handleError(error, 'load terminals');
    }
  }, [handleError]);

  const createTerminal = useCallback(async (name?: string): Promise<TerminalSession> => {
    try {
      const terminal = await backendClient.current.createTerminal({ name });
      
      setTerminals(prev => {
        const newTerminals = [...prev, terminal];
        return newTerminals;
      });
      
      // Force a reload of terminals to ensure synchronization
      setTimeout(() => {
        loadTerminals();
      }, 100);
      
      return terminal;
    } catch (error) {
      console.error('Failed to create terminal:', error);
      handleError(error, 'create terminal');
      throw error;
    }
  }, [handleError, loadTerminals]);
  
  const startTerminal = useCallback(async (terminalId: string) => {
    try {
      await backendClient.current.startTerminal(terminalId);
      
      // Update local state - mark terminal as running
      setTerminals(prev => 
        prev.map(terminal => 
          terminal.id === terminalId 
            ? { ...terminal, status: 'running' }
            : terminal
        )
      );
      
      // Force a reload of terminals to ensure synchronization
      setTimeout(() => {
        loadTerminals();
      }, 100);
      
    } catch (error) {
      console.error('Failed to start terminal:', error);
      handleError(error, 'start terminal');
      throw error;
    }
  }, [handleError, loadTerminals]);
  
  const destroyTerminal = useCallback(async (terminalId: string) => {
    try {
      await backendClient.current.destroyTerminal(terminalId);
      
      // Update local state
      setTerminals(prev => prev.filter(terminal => terminal.id !== terminalId));
    } catch (error) {
      handleError(error, 'destroy terminal');
    }
  }, [handleError]);
  
  const sendTerminalInput = useCallback(async (terminalId: string, input: string) => {
    try {
      await backendClient.current.sendTerminalInput(terminalId, input);
    } catch (error) {
      handleError(error, 'send terminal input');
    }
  }, [handleError]);
  
  /**
   * Get directory contents
   */
  const getDirectoryContents = useCallback(async (path: string = '/'): Promise<any[]> => {
    try {
      const tree = await backendClient.current.getDirectoryTree(path);
      return tree.children || [];
    } catch (error) {
      handleError(error, 'get directory contents');
      return [];
    }
  }, [handleError]);

  /**
   * Create directory
   */
  const createDirectory = useCallback(async (path: string): Promise<void> => {
    try {
      await backendClient.current.createDirectory(path);
      // Re-fetch workspace state to reflect the new directory
      fetchWorkspaceState().catch(console.error);
    } catch (error) {
      handleError(error, 'create directory');
    }
  }, [handleError, fetchWorkspaceState]);

  /**
   * Get directory tree
   */
  const getDirectoryTree = useCallback(async (path: string = '/'): Promise<any> => {
    try {
      return await backendClient.current.getDirectoryTree(path);
    } catch (error) {
      handleError(error, 'get directory tree');
      return { files: [] };
    }
  }, [handleError]);

  /**
   * Code execution
   */
  const executeCode = useCallback(async (fileId: string, content: string, language: string) => {
    try {
      await backendClient.current.executeCode({
        file_id: fileId,
        content,
        language,
        environment: {
          timeout: '30000',
          memory_limit: '512'
        }
      });
    } catch (error) {
      handleError(error, 'execute code');
    }
  }, [handleError]);
  
  /**
   * WebSocket event handlers
   */
  useEffect(() => {
    const handleConnectionStatusChange = (status: ConnectionStatus) => {
      setConnectionStatus(status);
    };
    
    const handleWorkspaceEvent = (event: any) => {
      // Only re-fetch workspace state for specific events that actually change the workspace
      switch (event.type) {
        case 'workspace_activated':
        case 'workspace_created':
        case 'workspace_deleted':
          // Re-fetch workspace state to sync changes
          fetchWorkspaceState().catch(console.error);
          break;
        case 'file_created':
        case 'file_updated':
        case 'file_deleted':
          // Update local files state instead of re-fetching entire workspace
          if (event.data && event.data.file) {
            const fileData = event.data.file;
            switch (event.type) {
              case 'file_created':               setFiles(prev => [...prev, convertToICUIFile(fileData)]);
                break;
              case 'file_updated':               setFiles(prev => prev.map(file => 
                  file.id === fileData.id ? convertToICUIFile(fileData) : file
                ));
                break;
              case 'file_deleted':               setFiles(prev => prev.filter(file => file.id !== fileData.id));
                break;
            }
          }
          break;
        case 'terminal_created':
        case 'terminal_destroyed':
          // Update local terminals state instead of re-fetching entire workspace
          if (event.data && event.data.terminal) {
            const terminalData = event.data.terminal;
            switch (event.type) {
              case 'terminal_created':               setTerminals(prev => [...prev, terminalData]);
                break;
              case 'terminal_destroyed':               setTerminals(prev => prev.filter(terminal => terminal.id !== terminalData.id));
                break;
            }
          }
          break;
        default:
          break;
      }
    };
    
    // Register WebSocket event handlers
    wsService.current.on('connection_status', handleConnectionStatusChange);
    wsService.current.on('workspace_event', handleWorkspaceEvent);
    
    return () => {
      wsService.current.off('connection_status', handleConnectionStatusChange);
      wsService.current.off('workspace_event', handleWorkspaceEvent);
    };
  }, [fetchWorkspaceState, convertToICUIFile]);
  
  /**
   * Initialize workspace state on connection
   */
  useEffect(() => {
    if (isConnected && !workspaceState) {
      fetchWorkspaceState().catch(console.error);
    }
  }, [isConnected, workspaceState, fetchWorkspaceState]);

  /**
   * Load terminals on connection
   */
  useEffect(() => {
    if (isConnected) {
      loadTerminals().catch(console.error);
    }
  }, [isConnected, loadTerminals]);
  
  return {
    // Connection state
    connectionStatus,
    isConnected,
    
    // Workspace state
    workspaceState,
    files,
    terminals,
    
    // Actions
    actions: {
      connect,
      disconnect,
      fetchWorkspaceState,
      updateWorkspaceState,
      createFile,
      updateFile,
      deleteFile,
      saveFile,
      openFile,
      closeFile,
      getDirectoryContents,
      createDirectory,
      getDirectoryTree,
      createTerminal,
      startTerminal,
      destroyTerminal,
      sendTerminalInput,
      executeCode,
    },
    
    // Error state
    error,
    clearError,
  };
};
