/**
 * Simple file editor component with backend integration.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';

// File interface
interface SimpleFile {
  id: string;
  name: string;
  language: string;
  content: string;
  modified: boolean;
  path?: string;
}

// Connection status interface
interface ConnectionStatus {
  connected: boolean;
  services?: any;
  timestamp?: number;
  error?: string;
}

// Notification system
class NotificationService {
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

// Backend API client
class EditorBackendClient {
  private backendUrl: string;
  public baseUrl: string;

  constructor() {
    // Smart URL construction for Cloudflare tunnel compatibility
    const envBackendUrl = import.meta.env.VITE_BACKEND_URL as string | undefined;
    const envApiUrl = import.meta.env.VITE_API_URL as string | undefined;
    const primaryUrl = envBackendUrl || envApiUrl;
    
    // Check if we're accessing through a different domain than configured
    const currentHost = window.location.host;
    let envHost = '';
    
    // Safely extract host from environment URL
    if (primaryUrl && primaryUrl.trim() !== '') {
      try {
        envHost = new URL(primaryUrl).host;
      } catch (error) {
        console.warn('Invalid backend URL format:', primaryUrl);
        envHost = '';
      }
    }
    
    if (primaryUrl && primaryUrl.trim() !== '' && currentHost === envHost) {
      // Use configured URL from .env when domains match
      this.backendUrl = primaryUrl;
      this.baseUrl = primaryUrl;
    } else {
      // Use dynamic URL construction when domains don't match (e.g., Cloudflare tunnels)
      const protocol = window.location.protocol;
      const host = window.location.host;
      this.backendUrl = `${protocol}//${host}`;
      this.baseUrl = `${protocol}//${host}`;
    }
    
    console.log('SimpleEditor initialized with URL:', this.baseUrl);
    console.log('Current host:', currentHost, 'Env host:', envHost);
  }

  async listFiles(): Promise<SimpleFile[]> {
    try {
      // Use workspace directory for ICPY file operations
      const workspacePath = '/home/penthoy/ilaborcode/workspace';
      const response = await fetch(`${this.baseUrl}/api/files?path=${encodeURIComponent(workspacePath)}`);
      if (!response.ok) {
        throw new Error(`Failed to list files: ${response.statusText}`);
      }
      const data = await response.json();
      
      // Handle ICPY response format
      if (data.success && data.data) {
        // Convert ICPY file format to SimpleFile format
        return data.data
          .filter((file: any) => !file.is_directory) // Filter out directories
          .map((file: any, index: number) => ({
            id: file.path || `file_${index}`,
            name: file.name,
            language: this.getLanguageFromExtension(file.name),
            content: '', // Content will be loaded separately
            modified: false,
            path: file.path
          }));
      }
      return [];
    } catch (error) {
      throw error;
    }
  }

  private getLanguageFromExtension(filename: string): string {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'js': return 'javascript';
      case 'ts': return 'typescript';
      case 'py': return 'python';
      case 'html': return 'html';
      case 'css': return 'css';
      case 'json': return 'json';
      case 'md': return 'markdown';
      default: return 'text';
    }
  }

  async getFile(fileId: string): Promise<SimpleFile> {
    try {
      const response = await fetch(`${this.baseUrl}/api/files/content?path=${encodeURIComponent(fileId)}`);
      if (!response.ok) {
        throw new Error(`Failed to get file: ${response.statusText}`);
      }
      const data = await response.json();
      
      // Handle ICPY response format
      if (data.success && data.data) {
        const filename = fileId.split('/').pop() || 'untitled';
        return {
          id: fileId,
          name: filename,
          language: this.getLanguageFromExtension(filename),
          content: data.data.content || '',
          modified: false,
          path: fileId
        };
      }
      
      throw new Error('Invalid response format');
    } catch (error) {
      throw error;
    }
  }

  async saveFile(file: SimpleFile): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/files`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: file.path || file.name,
          content: file.content,
          encoding: 'utf-8',
          create_dirs: true
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to save file: ${response.statusText}`);
      }
      
      const data = await response.json();
      if (!data.success) {
        throw new Error(data.message || 'Save failed');
      }
    } catch (error) {
      throw error;
    }
  }

  async createFile(name: string, language: string = 'javascript'): Promise<SimpleFile> {
    try {
      // Add appropriate extension based on language
      const extension = this.getExtensionFromLanguage(language);
      const filename = name.includes('.') ? name : `${name}.${extension}`;
      const workspacePath = '/home/penthoy/ilaborcode/workspace';
      const filepath = `${workspacePath}/${filename}`;
      
      const response = await fetch(`${this.baseUrl}/api/files`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: filepath,
          content: `// New ${language} file: ${filename}\n\n`,
          encoding: 'utf-8',
          create_dirs: true
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to create file: ${response.statusText}`);
      }
      
      const data = await response.json();
      if (!data.success) {
        throw new Error(data.message || 'Create failed');
      }
      
      return {
        id: filepath,
        name: filename,
        language,
        content: `// New ${language} file: ${filename}\n\n`,
        modified: false,
        path: filepath
      };
    } catch (error) {
      throw error;
    }
  }

  private getExtensionFromLanguage(language: string): string {
    switch (language) {
      case 'javascript': return 'js';
      case 'typescript': return 'ts';
      case 'python': return 'py';
      case 'html': return 'html';
      case 'css': return 'css';
      case 'json': return 'json';
      case 'markdown': return 'md';
      default: return 'txt';
    }
  }

  async deleteFile(fileId: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/files?path=${encodeURIComponent(fileId)}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error(`Failed to delete file: ${response.statusText}`);
      }
      
      const data = await response.json();
      if (!data.success) {
        throw new Error(data.message || 'Delete failed');
      }
    } catch (error) {
      console.error('Error deleting file:', error);
      throw error;
    }
  }

  async executeCode(file: SimpleFile): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: file.content,
          language: file.language,
          file_path: file.path || file.name
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to execute code: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      throw error;
    }
  }

  async getConnectionStatus(): Promise<ConnectionStatus> {
    try {
      
      const response = await fetch(`${this.backendUrl}/health`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      return {
        connected: data.status === 'healthy',
        services: data.services || {},
        timestamp: data.timestamp
      };
    } catch (error) {
      return {
        connected: false,
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }
}

interface SimpleEditorProps {
  className?: string;
}

const SimpleEditor: React.FC<SimpleEditorProps> = ({ className = '' }) => {
  // State
  const [files, setFiles] = useState<SimpleFile[]>([]);
  const [activeFileId, setActiveFileId] = useState<string | null>(null);
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showLineNumbers, setShowLineNumbers] = useState(true);
  const [isConnected, setIsConnected] = useState(false);

  // Refs
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const backendClient = useRef(new EditorBackendClient());
  const autoSaveTimeout = useRef<NodeJS.Timeout | null>(null);

  // Get active file
  const activeFile = files.find(f => f.id === activeFileId) || null;

  // Theme detection
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

  // Check connection status
  const checkConnection = useCallback(async () => {
    try {
      const status = await backendClient.current.getConnectionStatus();
      setConnectionStatus(status);
      setIsConnected(status.connected);
    } catch (error) {
      setIsConnected(false);
      setConnectionStatus({ connected: false, error: error.message });
    }
  }, []);

  // Load files from backend
  const loadFiles = useCallback(async () => {
    if (!isConnected) return;
    
    setIsLoading(true);
    try {
      const loadedFiles = await backendClient.current.listFiles();
      
      // Load content for the first few files
      const filesWithContent = await Promise.all(
        loadedFiles.slice(0, 5).map(async (file) => {
          try {
            if (file.path) {
              const fileWithContent = await backendClient.current.getFile(file.path);
              return fileWithContent;
            }
            return file;
          } catch (error) {
            console.warn(`Failed to load content for ${file.name}:`, error);
            return file;
          }
        })
      );
      setFiles(filesWithContent);
      
      if (filesWithContent.length > 0 && !activeFileId) {
        setActiveFileId(filesWithContent[0].id);
      }
      
      NotificationService.show(`Loaded ${loadedFiles.length} files`, 'success');
    } catch (error) {
      NotificationService.show(`Failed to load files: ${error.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  }, [isConnected, activeFileId]);

  // Handle file activation (load content if not already loaded)
  const handleFileActivate = useCallback(async (fileId: string) => {
    const file = files.find(f => f.id === fileId);
    if (!file) return;
    
    setActiveFileId(fileId);
    
    // Load file content if not already loaded
    if (!file.content && file.path) {
      try {
        const fileWithContent = await backendClient.current.getFile(file.path);
        setFiles(prev => prev.map(f => 
          f.id === fileId ? { ...f, content: fileWithContent.content } : f
        ));
      } catch (error) {
        NotificationService.show(`Failed to load file content: ${error.message}`, 'error');
      }
    }
  }, [files]);

  // Auto-save functionality
  const debouncedSave = useCallback(async (file: SimpleFile) => {
    if (autoSaveTimeout.current) {
      clearTimeout(autoSaveTimeout.current);
    }

    autoSaveTimeout.current = setTimeout(async () => {
      try {
        await backendClient.current.saveFile(file);
        setFiles(prev => prev.map(f => 
          f.id === file.id ? { ...f, modified: false } : f
        ));
        NotificationService.show(`Auto-saved ${file.name}`, 'success');
      } catch (error) {
        NotificationService.show(`Auto-save failed: ${error.message}`, 'error');
      }
    }, 2000);
  }, []);

  // Handle content change
  const handleContentChange = useCallback((newContent: string) => {
    if (!activeFile) return;

    const updatedFile = { ...activeFile, content: newContent, modified: true };
    setFiles(prev => prev.map(f => 
      f.id === activeFile.id ? updatedFile : f
    ));

    // Trigger auto-save
    debouncedSave(updatedFile);
  }, [activeFile, debouncedSave]);

  // Handle manual save
  const handleSave = useCallback(async () => {
    if (!activeFile || !activeFile.modified) return;

    try {
      await backendClient.current.saveFile(activeFile);
      setFiles(prev => prev.map(f => 
        f.id === activeFile.id ? { ...f, modified: false } : f
      ));
      NotificationService.show(`Saved ${activeFile.name}`, 'success');
    } catch (error) {
      NotificationService.show(`Save failed: ${error.message}`, 'error');
    }
  }, [activeFile]);

  // Handle code execution
  const handleRun = useCallback(async () => {
    if (!activeFile) return;

    try {
      const result = await backendClient.current.executeCode(activeFile);
      NotificationService.show('Code executed successfully', 'success');
    } catch (error) {
      NotificationService.show(`Execution failed: ${error.message}`, 'error');
    }
  }, [activeFile]);

  // Handle file creation
  const handleCreateFile = useCallback(async () => {
    const fileName = prompt('Enter file name:');
    if (!fileName) return;

    const language = prompt('Enter language (javascript, typescript, python, etc.):', 'javascript') || 'javascript';

    try {
      const newFile = await backendClient.current.createFile(fileName, language);
      setFiles(prev => [...prev, newFile]);
      setActiveFileId(newFile.id);
      NotificationService.show(`Created ${fileName}`, 'success');
    } catch (error) {
      NotificationService.show(`Failed to create file: ${error.message}`, 'error');
    }
  }, []);

  // Handle file deletion
  const handleDeleteFile = useCallback(async (fileId: string) => {
    if (!confirm('Are you sure you want to delete this file?')) return;

    try {
      await backendClient.current.deleteFile(fileId);
      setFiles(prev => prev.filter(f => f.id !== fileId));
      
      if (activeFileId === fileId) {
        const remainingFiles = files.filter(f => f.id !== fileId);
        setActiveFileId(remainingFiles.length > 0 ? remainingFiles[0].id : null);
      }
      
      NotificationService.show('File deleted', 'success');
    } catch (error) {
      NotificationService.show(`Failed to delete file: ${error.message}`, 'error');
    }
  }, [activeFileId, files]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const isEditorFocused = textareaRef.current?.contains(document.activeElement);
      if (!isEditorFocused) return;

      // Ctrl+S for save
      if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        event.preventDefault();
        handleSave();
      }

      // Ctrl+Enter for run
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        handleRun();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleSave, handleRun]);

  // Initialize: check connection and load files
  useEffect(() => {
    const initializeEditor = async () => {
      await checkConnection();
    };
    
    initializeEditor();
  }, []);

  useEffect(() => {
    if (isConnected) {
      loadFiles();
    }
  }, [isConnected, loadFiles]);

  // Calculate line numbers
  const lineCount = activeFile ? activeFile.content.split('\n').length : 0;

  return (
    <div className={`simple-editor ${className}`}>
      {/* Header */}
      <div className="bg-blue-100 border-b p-2 text-sm">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-semibold">Simple Editor</div>
            <div className="text-xs text-gray-600">
              Direct REST API connection to ICPY backend
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`text-xs px-2 py-1 rounded ${
              isConnected ? 'bg-green-200 text-green-800' : 'bg-red-200 text-red-800'
            }`}>
              {isConnected ? 'Connected' : 'Disconnected'}
              {connectionStatus?.error && (
                <div className="text-xs mt-1 text-red-600">
                  {connectionStatus.error}
                </div>
              )}
            </div>
            <button
              onClick={checkConnection}
              className="text-xs px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* File Tabs */}
      <div className="flex items-center bg-gray-100 dark:bg-gray-800 border-b border-gray-300 dark:border-gray-600 overflow-x-auto">
        {files.map(file => (
          <div
            key={file.id}
            className={`flex items-center px-3 py-2 border-r border-gray-300 dark:border-gray-600 cursor-pointer min-w-0 ${
              file.id === activeFileId 
                ? 'bg-white dark:bg-gray-900 text-blue-600 dark:text-blue-400' 
                : 'hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
            onClick={() => handleFileActivate(file.id)}
          >
            <span className="text-sm truncate">
              {file.name}
              {file.modified && <span className="text-orange-500 ml-1">●</span>}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDeleteFile(file.id);
              }}
              className="ml-2 text-gray-400 hover:text-red-500 text-xs"
            >
              ×
            </button>
          </div>
        ))}
        <button
          onClick={handleCreateFile}
          className="px-3 py-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          title="Create new file"
        >
          +
        </button>
      </div>

      {/* Editor Controls */}
      {activeFile && (
        <div className="flex items-center justify-between px-4 py-2 bg-gray-100 dark:bg-gray-800 border-b border-gray-300 dark:border-gray-600">
          <div className="flex items-center space-x-3">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {activeFile.name}
            </span>
            <select
              value={activeFile.language}
              onChange={(e) => {
                const updatedFile = { ...activeFile, language: e.target.value, modified: true };
                setFiles(prev => prev.map(f => 
                  f.id === activeFile.id ? updatedFile : f
                ));
              }}
              className="text-xs px-2 py-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="javascript">JavaScript</option>
              <option value="typescript">TypeScript</option>
              <option value="python">Python</option>
              <option value="html">HTML</option>
              <option value="css">CSS</option>
              <option value="json">JSON</option>
              <option value="markdown">Markdown</option>
              <option value="text">Plain Text</option>
            </select>
            <button
              onClick={() => setShowLineNumbers(!showLineNumbers)}
              className="text-xs px-2 py-1 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-500 transition-colors"
            >
              {showLineNumbers ? 'Hide' : 'Show'} Lines
            </button>
          </div>
          
          <div className="flex items-center space-x-2">
            {activeFile.modified && (
              <span className="text-xs text-orange-600 dark:text-orange-400">
                Modified
              </span>
            )}
            <button
              onClick={handleSave}
              disabled={!activeFile.modified}
              className={`px-3 py-1 text-xs rounded transition-colors ${
                activeFile.modified 
                  ? 'bg-blue-500 hover:bg-blue-600 text-white' 
                  : 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
              }`}
            >
              Save
            </button>
            <button
              onClick={handleRun}
              className="px-3 py-1 text-xs bg-green-500 hover:bg-green-600 text-white rounded transition-colors"
            >
              Run
            </button>
          </div>
        </div>
      )}

      {/* Editor Area */}
      <div className="flex-1 flex min-h-0 overflow-hidden" style={{ height: '400px' }}>
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            Loading files...
          </div>
        ) : !activeFile ? (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            {files.length === 0 ? 'No files available. Create a new file to get started.' : 'Select a file to edit'}
          </div>
        ) : (
          <>
            {/* Line Numbers */}
            {showLineNumbers && (
              <div className="flex-shrink-0 bg-gray-50 dark:bg-gray-800 border-r border-gray-300 dark:border-gray-600 px-3 py-2">
                <div className="text-xs text-gray-500 dark:text-gray-400 font-mono leading-6">
                  {Array.from({ length: lineCount }, (_, i) => (
                    <div key={i + 1} className="text-right">
                      {i + 1}
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Text Area */}
            <div className="flex-1 min-w-0">
              <textarea
                ref={textareaRef}
                value={activeFile.content}
                onChange={(e) => handleContentChange(e.target.value)}
                className="w-full h-full p-2 font-mono text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border-none resize-none focus:outline-none leading-6"
                placeholder="Start typing your code here..."
                spellCheck={false}
                style={{ 
                  tabSize: 2,
                  minHeight: '100%',
                  outline: 'none',
                  border: 'none',
                }}
              />
            </div>
          </>
        )}
      </div>

      {/* Status Bar */}
      {activeFile && (
        <div className="flex items-center justify-between px-4 py-1 bg-gray-50 dark:bg-gray-800 border-t border-gray-300 dark:border-gray-600 text-xs text-gray-600 dark:text-gray-400">
          <div className="flex items-center space-x-4">
            <span>Lines: {lineCount}</span>
            <span>Characters: {activeFile.content.length}</span>
            <span>Language: {activeFile.language}</span>
            {activeFile.modified && (
              <span className="text-orange-500">● Modified</span>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <span>Ctrl+S to save</span>
            <span>•</span>
            <span>Ctrl+Enter to run</span>
            <span>•</span>
            <span>Auto-save: 2s</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default SimpleEditor;
