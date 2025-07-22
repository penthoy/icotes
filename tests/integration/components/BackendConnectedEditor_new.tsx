/**
 * Backend-Connected Editor Component
 * 
 * Complete rewrite following the simpleeditor.tsx and direct backend API pattern.
 * This component provides reliable backend connectivity without complex state management,
 * similar to BackendConnectedExplorer and BackendConnectedTerminal.
 * 
 * Key Features:
 * - Direct backend API calls for file operations
 * - Multi-file tabs with backend synchronization
 * - Auto-save with debouncing
 * - Real-time file loading from backend
 * - CodeMirror 6 integration with syntax highlighting
 * - Theme detection and workspace root integration
 * - Error handling and connection status display
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  EditorView,
  keymap,
  lineNumbers,
  dropCursor,
  rectangularSelection,
  crosshairCursor,
} from "@codemirror/view";
import { EditorState, Extension } from "@codemirror/state";
import {
  defaultKeymap,
  history,
  historyKeymap,
  indentWithTab,
} from "@codemirror/commands";
import { searchKeymap, highlightSelectionMatches } from "@codemirror/search";
import {
  autocompletion,
  completionKeymap,
  closeBrackets,
  closeBracketsKeymap,
} from "@codemirror/autocomplete";
import {
  syntaxHighlighting,
  indentOnInput,
  bracketMatching,
  foldKeymap,
  foldGutter,
} from "@codemirror/language";
import { createICUISyntaxHighlighting, createICUIEnhancedEditorTheme, getLanguageExtension } from '../../../src/icui/utils/syntaxHighlighting';

// File interface (following ICUIEnhancedEditorPanel pattern)
interface EditorFile {
  id: string;
  name: string;
  language: string;
  content: string;
  modified: boolean;
  path?: string;
}

// Connection status interface (following simpleeditor pattern)
interface ConnectionStatus {
  connected: boolean;
  services?: any;
  timestamp?: number;
  error?: string;
}

// Notification system (following simpleeditor pattern)
class EditorNotificationService {
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

// Backend client for editor operations (following BackendConnectedExplorer pattern)
class EditorBackendClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = (import.meta as any).env?.VITE_API_URL || '';
  }

  async checkConnection(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      return response.ok;
    } catch (error) {
      return false;
    }
  }

  async readFile(path: string): Promise<string> {
    try {
      console.log('[BackendConnectedEditor-FIXED] Reading file:', path);
      const encodedPath = encodeURIComponent(path);
      const response = await fetch(`${this.baseUrl}/files/${encodedPath}/content`);
      
      if (!response.ok) {
        throw new Error(`Failed to read file: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.message || 'Failed to read file');
      }
      
      return result.data.content || '';
    } catch (error) {
      console.error('Failed to read file:', error);
      throw error;
    }
  }

  async writeFile(path: string, content: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/files`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path, content }),
      });

      if (!response.ok) {
        throw new Error(`Failed to write file: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      if (!result.success) {
        throw new Error(result.message || 'Failed to write file');
      }
    } catch (error) {
      console.error('Failed to write file:', error);
      throw error;
    }
  }

  async executeCode(code: string, language: string, filename?: string): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          code, 
          language,
          filename: filename || 'untitled'
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to execute code: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to execute code:', error);
      throw error;
    }
  }
}

interface BackendConnectedEditorProps {
  className?: string;
  files?: EditorFile[];
  activeFileId?: string;
  onFileChange?: (fileId: string, newContent: string) => void;
  onFileClose?: (fileId: string) => void;
  onFileCreate?: () => void;
  onFileSave?: (fileId: string) => void;
  onFileRun?: (fileId: string, content: string, language: string) => void;
  onFileActivate?: (fileId: string) => void;
  onFileReorder?: (fromIndex: number, toIndex: number) => void;
  autoSave?: boolean;
  autoSaveDelay?: number;
  workspaceRoot?: string;
}

const BackendConnectedEditor: React.FC<BackendConnectedEditorProps> = ({
  className = '',
  files: propFiles = [],
  activeFileId: propActiveFileId,
  onFileChange,
  onFileClose,
  onFileCreate,
  onFileSave,
  onFileRun,
  onFileActivate,
  onFileReorder,
  autoSave = true,
  autoSaveDelay = 1500,
  workspaceRoot
}) => {
  // State management (following simpleeditor pattern)
  const [files, setFiles] = useState<EditorFile[]>(propFiles.length > 0 ? propFiles : [
    {
      id: '1',
      name: 'welcome.js',
      language: 'javascript',
      content: '// Welcome to the JavaScript Code Editor!\n// Built with React, CodeMirror 6, and the ICUI Framework\n\nfunction welcome() {\n  console.log("Welcome to your code editor!");\n  console.log("Start coding and see the magic happen!");\n  return "Happy coding!";\n}\n\nwelcome();',
      modified: false,
      path: '/workspace/welcome.js'
    }
  ]);
  const [activeFileId, setActiveFileId] = useState<string>(propActiveFileId || files[0]?.id || '1');
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({ connected: false });
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Refs (following ICUIEnhancedEditorPanel pattern)
  const editorRef = useRef<HTMLDivElement>(null);
  const editorViewRef = useRef<EditorView | null>(null);
  const backendClient = useRef(new EditorBackendClient());
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Get workspace root from environment (following BackendConnectedExplorer pattern)
  const effectiveWorkspaceRoot = workspaceRoot || (import.meta as any).env?.VITE_WORKSPACE_ROOT || '/home/penthoy/ilaborcode/workspace';

  console.log('[BackendConnectedEditor-FIXED] Workspace root from env:', effectiveWorkspaceRoot);

  // Theme detection (following BackendConnectedTerminal pattern)
  useEffect(() => {
    const detectTheme = () => {
      const htmlElement = document.documentElement;
      const isDark = htmlElement.classList.contains('dark') || 
                     htmlElement.classList.contains('icui-theme-github-dark') ||
                     htmlElement.classList.contains('icui-theme-monokai') ||
                     htmlElement.classList.contains('icui-theme-one-dark');
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

  // Backend connection check (following simpleeditor pattern)
  const checkBackendConnection = useCallback(async () => {
    try {
      const isConnected = await backendClient.current.checkConnection();
      setConnectionStatus({
        connected: isConnected,
        timestamp: Date.now()
      });
      return isConnected;
    } catch (error) {
      setConnectionStatus({
        connected: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: Date.now()
      });
      return false;
    }
  }, []);

  // Initialize backend connection
  useEffect(() => {
    checkBackendConnection();
    const interval = setInterval(checkBackendConnection, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, [checkBackendConnection]);

  // Get language extension helper (following ICUIEnhancedEditorPanel pattern)
  const getLanguageFromExtension = useCallback((filename: string): string => {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'js':
      case 'jsx':
        return 'javascript';
      case 'ts':
      case 'tsx':
        return 'typescript';
      case 'py':
        return 'python';
      case 'html':
        return 'html';
      case 'css':
        return 'css';
      case 'json':
        return 'json';
      case 'md':
        return 'markdown';
      default:
        return 'text';
    }
  }, []);

  // Create editor extensions (following ICUIEnhancedEditorPanel pattern)
  const createExtensions = useCallback((language: string): Extension[] => {
    const extensions: Extension[] = [
      lineNumbers(),
      dropCursor(),
      indentOnInput(),
      bracketMatching(),
      closeBrackets(),
      autocompletion(),
      rectangularSelection(),
      crosshairCursor(),
      highlightSelectionMatches(),
      searchKeymap,
      history(),
      foldGutter(),
      keymap.of([
        ...closeBracketsKeymap,
        ...defaultKeymap,
        ...searchKeymap,
        ...historyKeymap,
        ...foldKeymap,
        ...completionKeymap,
        indentWithTab,
      ]),
      syntaxHighlighting(createICUISyntaxHighlighting()),
      createICUIEnhancedEditorTheme(isDarkTheme),
      EditorView.theme({
        '&': {
          height: '100%',
        },
        '.cm-scroller': {
          fontFamily: 'Menlo, Monaco, "Courier New", monospace',
          fontSize: '14px',
        },
        '.cm-focused': {
          outline: 'none',
        },
      }),
    ];

    // Add language-specific extension
    const langExtension = getLanguageExtension(language);
    if (langExtension) {
      extensions.push(langExtension);
    }

    return extensions;
  }, [isDarkTheme]);

  // Get current active file
  const activeFile = files.find(file => file.id === activeFileId);

  // Handle content changes with auto-save (following simpleeditor pattern)
  const handleContentChange = useCallback((newContent: string) => {
    if (!activeFile) return;

    // Update file content and mark as modified
    setFiles(prevFiles => 
      prevFiles.map(file => 
        file.id === activeFileId 
          ? { ...file, content: newContent, modified: true }
          : file
      )
    );

    // Call external handler
    onFileChange?.(activeFileId, newContent);

    // Cancel previous auto-save timer
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }

    // Set up debounced auto-save if enabled and connected
    if (autoSave && connectionStatus.connected && activeFile.path) {
      autoSaveTimerRef.current = setTimeout(async () => {
        try {
          await backendClient.current.writeFile(activeFile.path!, newContent);
          
          // Mark file as saved
          setFiles(prevFiles => 
            prevFiles.map(file => 
              file.id === activeFileId 
                ? { ...file, modified: false }
                : file
            )
          );
          
          EditorNotificationService.show(`Auto-saved ${activeFile.name}`, 'success');
        } catch (error) {
          console.error(`Failed to auto-save file ${activeFile.name}:`, error);
          EditorNotificationService.show(`Failed to auto-save ${activeFile.name}`, 'error');
        }
      }, autoSaveDelay);
    }
  }, [activeFile, activeFileId, onFileChange, autoSave, connectionStatus.connected, autoSaveDelay]);

  // Initialize CodeMirror editor (following ICUIEnhancedEditorPanel pattern)
  useEffect(() => {
    if (!editorRef.current || !activeFile) return;

    // Clean up existing editor
    if (editorViewRef.current) {
      editorViewRef.current.destroy();
      editorViewRef.current = null;
    }

    // Create new editor state
    const state = EditorState.create({
      doc: activeFile.content,
      extensions: createExtensions(activeFile.language),
    });

    // Create editor view
    const view = new EditorView({
      state,
      parent: editorRef.current,
      dispatch: (transaction) => {
        view.update([transaction]);
        
        if (transaction.docChanged) {
          const newContent = view.state.doc.toString();
          handleContentChange(newContent);
        }
      },
    });

    editorViewRef.current = view;

    // Focus the editor
    view.focus();

    return () => {
      if (editorViewRef.current) {
        editorViewRef.current.destroy();
        editorViewRef.current = null;
      }
    };
  }, [activeFile?.id, activeFile?.content, activeFile?.language, createExtensions, handleContentChange]);

  // File operations (following simpleeditor pattern)
  const handleSaveFile = useCallback(async (fileId: string) => {
    const file = files.find(f => f.id === fileId);
    if (!file || !file.path || !connectionStatus.connected) return;

    setIsLoading(true);
    try {
      await backendClient.current.writeFile(file.path, file.content);
      
      // Mark file as saved
      setFiles(prevFiles => 
        prevFiles.map(f => 
          f.id === fileId 
            ? { ...f, modified: false }
            : f
        )
      );
      
      EditorNotificationService.show(`Saved ${file.name}`, 'success');
      onFileSave?.(fileId);
    } catch (error) {
      console.error('Failed to save file:', error);
      EditorNotificationService.show(`Failed to save ${file.name}`, 'error');
    } finally {
      setIsLoading(false);
    }
  }, [files, connectionStatus.connected, onFileSave]);

  const handleRunFile = useCallback(async (fileId: string) => {
    const file = files.find(f => f.id === fileId);
    if (!file || !connectionStatus.connected) return;

    setIsLoading(true);
    try {
      const result = await backendClient.current.executeCode(file.content, file.language, file.name);
      EditorNotificationService.show(`Executed ${file.name}`, 'success');
      onFileRun?.(fileId, file.content, file.language);
      
      // You could emit the result to terminal or output panel here
      console.log('Execution result:', result);
    } catch (error) {
      console.error('Failed to execute file:', error);
      EditorNotificationService.show(`Failed to execute ${file.name}`, 'error');
    } finally {
      setIsLoading(false);
    }
  }, [files, connectionStatus.connected, onFileRun]);

  const handleCloseFile = useCallback((fileId: string) => {
    const file = files.find(f => f.id === fileId);
    if (!file) return;

    if (file.modified) {
      // In a real implementation, you'd show a confirmation dialog
      const shouldSave = window.confirm(`${file.name} has unsaved changes. Save before closing?`);
      if (shouldSave && connectionStatus.connected && file.path) {
        handleSaveFile(fileId);
      }
    }

    setFiles(prevFiles => prevFiles.filter(f => f.id !== fileId));
    
    // If closing active file, switch to another file
    if (fileId === activeFileId) {
      const remainingFiles = files.filter(f => f.id !== fileId);
      if (remainingFiles.length > 0) {
        setActiveFileId(remainingFiles[0].id);
      }
    }

    onFileClose?.(fileId);
  }, [files, activeFileId, connectionStatus.connected, onFileClose, handleSaveFile]);

  const handleActivateFile = useCallback((fileId: string) => {
    setActiveFileId(fileId);
    onFileActivate?.(fileId);
  }, [onFileActivate]);

  // Cleanup auto-save timer on unmount
  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, []);

  return (
    <div className={`backend-connected-editor-container h-full flex flex-col ${className}`}>
      {/* Connection Status Bar */}
      <div className="flex items-center justify-between p-2 border-b bg-gray-50 dark:bg-gray-800 text-sm">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div 
              className={`w-2 h-2 rounded-full ${
                connectionStatus.connected ? 'bg-green-500' : 'bg-red-500'
              }`}
            />
            <span className="text-xs">
              {connectionStatus.connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <span className="text-xs text-gray-500">
            Workspace: {effectiveWorkspaceRoot}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          {isLoading && (
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          )}
          <button
            onClick={checkBackendConnection}
            className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* File Tabs */}
      <div className="flex bg-gray-100 dark:bg-gray-700 border-b overflow-x-auto">
        {files.map((file) => (
          <div
            key={file.id}
            className={`flex items-center px-3 py-2 border-r cursor-pointer min-w-0 ${
              file.id === activeFileId
                ? 'bg-white dark:bg-gray-800 border-b-2 border-blue-500'
                : 'hover:bg-gray-50 dark:hover:bg-gray-600'
            }`}
            onClick={() => handleActivateFile(file.id)}
          >
            <span className="truncate text-sm">
              {file.name}
              {file.modified && <span className="text-orange-500 ml-1">•</span>}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleCloseFile(file.id);
              }}
              className="ml-2 text-gray-400 hover:text-red-500 text-xs"
            >
              ×
            </button>
          </div>
        ))}
        <button
          onClick={onFileCreate}
          className="px-3 py-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-sm"
          title="New File"
        >
          +
        </button>
      </div>

      {/* File Actions */}
      {activeFile && (
        <div className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 border-b">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium">{activeFile.name}</span>
            <span className="text-xs text-gray-500">({activeFile.language})</span>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => handleSaveFile(activeFile.id)}
              disabled={!activeFile.modified || !connectionStatus.connected || isLoading}
              className="px-3 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Save
            </button>
            <button
              onClick={() => handleRunFile(activeFile.id)}
              disabled={!connectionStatus.connected || isLoading}
              className="px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Run
            </button>
          </div>
        </div>
      )}

      {/* Editor Container */}
      <div className="flex-1 relative">
        {activeFile ? (
          <div 
            ref={editorRef} 
            className="h-full w-full"
            style={{ height: '100%' }}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <p className="text-lg mb-2">No file open</p>
              <button
                onClick={onFileCreate}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                Create New File
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BackendConnectedEditor;
