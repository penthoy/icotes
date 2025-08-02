/**
 * Simple Explorer Implementation
 * Based on BackendConnectedExplorer.tsx - A minimal, working file explorer for ICUI-ICPY integration
 * 
 * This component provides a simplified file explorer implementation that directly connects
 * to the ICPY backend via REST API, without the complexity of the full backend state
 * management system. It's designed to debug and test file system connectivity issues.
 * 
 * Features:
 * - Direct HTTP requests to ICPY backend file API
 * - Basic file/folder operations (create, delete, rename)
 * - Directory tree navigation
 * - Connection status monitoring
 * - Error handling and recovery
 * - Theme-aware styling (dark/light mode support)
 * - Minimal implementation for debugging
 * 
 * Usage:
 * - Access at /simple-explorer route
 * - Automatically loads root directory on mount
 * - Provides visual feedback for connection status
 * - Click to select files/folders
 * - Right-click for context menu operations
 * 
 * @see BackendConnectedExplorer.tsx - Original backend-connected implementation
 * @see ICUIExplorerPanel.tsx - Original reference implementation
 */

import React, { useState, useEffect, useCallback } from 'react';

// File/Folder interface
interface SimpleFileNode {
  id: string;
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: SimpleFileNode[];
  isExpanded?: boolean;
  size?: number;
  modified?: string;
}

// Connection status interface
interface ConnectionStatus {
  connected: boolean;
  services?: any;
  timestamp?: number;
  error?: string;
}

// Simple notification system
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

// Explorer backend client
class ExplorerBackendClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = (import.meta as any).env?.VITE_API_URL || '';
  }

  async checkConnection(): Promise<ConnectionStatus> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      return {
        connected: true,
        services: data,
        timestamp: Date.now()
      };
    } catch (error) {
      return {
        connected: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: Date.now()
      };
    }
  }

  async getDirectoryContents(path: string = '/'): Promise<SimpleFileNode[]> {
    try {
      const encodedPath = encodeURIComponent(path);
      const response = await fetch(`${this.baseUrl}/files?path=${encodedPath}`);
      
      if (!response.ok) {
        throw new Error(`Failed to get directory contents: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      
      // Check if the response is successful and has data
      if (!result.success) {
        throw new Error(result.message || 'API request failed');
      }
      
      const fileList = result.data || [];
      
      // Convert backend response to SimpleFileNode format
      return fileList.map((item: any) => ({
        id: item.path,
        name: item.name,
        type: item.is_directory ? 'folder' : 'file',
        path: item.path,
        size: item.size,
        modified: item.modified_at ? new Date(item.modified_at * 1000).toISOString() : undefined,
        isExpanded: false,
        children: item.is_directory ? [] : undefined
      }));
    } catch (error) {
      console.error('Failed to get directory contents:', error);
      throw error;
    }
  }

  async createFile(path: string, content: string = ''): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/files`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path, content }),
      });

      if (!response.ok) {
        throw new Error(`Failed to create file: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error('Failed to create file:', error);
      throw error;
    }
  }

  async createDirectory(path: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/files`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path, type: 'directory' }),
      });

      if (!response.ok) {
        throw new Error(`Failed to create directory: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error('Failed to create directory:', error);
      throw error;
    }
  }

  async deleteFile(path: string): Promise<void> {
    try {
      const encodedPath = encodeURIComponent(path);
      const response = await fetch(`${this.baseUrl}/files?path=${encodedPath}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`Failed to delete file: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error('Failed to delete file:', error);
      throw error;
    }
  }

  async renameFile(oldPath: string, newPath: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/files`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ oldPath, newPath }),
      });

      if (!response.ok) {
        throw new Error(`Failed to rename file: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error('Failed to rename file:', error);
      throw error;
    }
  }
}

// Main SimpleExplorer component
const SimpleExplorer: React.FC = () => {
  const [files, setFiles] = useState<SimpleFileNode[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({ connected: false });
  const [loading, setLoading] = useState(false);
  const [currentPath, setCurrentPath] = useState<string>((import.meta as any).env?.VITE_WORKSPACE_ROOT || '/');
  const [newItemName, setNewItemName] = useState<string>('');
  const [showCreateForm, setShowCreateForm] = useState<'file' | 'folder' | null>(null);
  const [isDark, setIsDark] = useState(false);

  const backendClient = new ExplorerBackendClient();

  // Theme detection
  useEffect(() => {
    const checkTheme = () => {
      const isDarkMode = document.documentElement.classList.contains('dark') ||
                         document.body.classList.contains('dark') ||
                         window.matchMedia('(prefers-color-scheme: dark)').matches;
      setIsDark(isDarkMode);
    };

    checkTheme();
    
    // Watch for theme changes
    const observer = new MutationObserver(checkTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });

    return () => observer.disconnect();
  }, []);

  // Check connection status
  const checkConnection = useCallback(async () => {
    const status = await backendClient.checkConnection();
    setConnectionStatus(status);
    return status.connected;
  }, []);

  // Load directory contents
  const loadDirectory = useCallback(async (path: string = (import.meta as any).env?.VITE_WORKSPACE_ROOT || '/') => {
    setLoading(true);
    try {
      const isConnected = await checkConnection();
      if (!isConnected) {
        throw new Error('Backend not connected');
      }

      console.log('Loading directory:', path);
      const directoryContents = await backendClient.getDirectoryContents(path);
      console.log('Directory contents received:', directoryContents);
      setFiles(directoryContents);
      setCurrentPath(path);
    } catch (error) {
      console.error('Failed to load directory:', error);
      NotificationService.show(
        `Failed to load directory: ${error instanceof Error ? error.message : 'Unknown error'}`,
        'error'
      );
    } finally {
      setLoading(false);
    }
  }, [checkConnection]);

  // Initial load
  useEffect(() => {
    loadDirectory();
  }, []);

  // Handle file/folder selection
  const handleItemClick = useCallback((item: SimpleFileNode) => {
    setSelectedFile(item.id);
    
    if (item.type === 'folder') {
      loadDirectory(item.path);
    }
  }, [loadDirectory]);

  // Handle creating new files/folders
  const handleCreateItem = useCallback(async (type: 'file' | 'folder') => {
    if (!newItemName.trim()) {
      NotificationService.show('Please enter a name', 'warning');
      return;
    }

    const newPath = `${currentPath}/${newItemName.trim()}`;

    try {
      if (type === 'file') {
        await backendClient.createFile(newPath);
        NotificationService.show(`File "${newItemName}" created successfully`, 'success');
      } else {
        await backendClient.createDirectory(newPath);
        NotificationService.show(`Folder "${newItemName}" created successfully`, 'success');
      }
      
      // Refresh directory
      await loadDirectory();
      
      // Reset form
      setNewItemName('');
      setShowCreateForm(null);
    } catch (error) {
      NotificationService.show(
        `Failed to create ${type}: ${error instanceof Error ? error.message : 'Unknown error'}`,
        'error'
      );
    }
  }, [newItemName, currentPath, loadDirectory]);

  // Handle deleting items
  const handleDeleteItem = useCallback(async (item: SimpleFileNode) => {
    if (!confirm(`Are you sure you want to delete "${item.name}"?`)) {
      return;
    }

    try {
      await backendClient.deleteFile(item.path);
      NotificationService.show(`"${item.name}" deleted successfully`, 'success');
      
      // Refresh directory
      await loadDirectory();
    } catch (error) {
      NotificationService.show(
        `Failed to delete "${item.name}": ${error instanceof Error ? error.message : 'Unknown error'}`,
        'error'
      );
    }
  }, [loadDirectory]);

  // Navigate up one level
  const navigateUp = useCallback(() => {
    const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/';
    loadDirectory(parentPath);
  }, [currentPath, loadDirectory]);

  const themeClasses = isDark ? 'bg-gray-900 text-white' : 'bg-white text-gray-900';
  const panelClasses = isDark ? 'bg-gray-800 border-gray-700' : 'bg-gray-50 border-gray-300';
  const itemClasses = isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-100';
  const selectedClasses = isDark ? 'bg-gray-600' : 'bg-blue-100';
  const buttonClasses = isDark ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-gray-200 hover:bg-gray-300 text-gray-800';

  return (
    <div className={`min-h-screen p-4 ${themeClasses}`}>
      <div className="max-w-4xl mx-auto">
        <div className="mb-4">
          <h1 className="text-2xl font-bold mb-2">Simple Explorer</h1>
          
          <div className="flex items-center gap-4 mb-4">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${connectionStatus.connected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-sm">
                {connectionStatus.connected ? 'Connected' : 'Disconnected'}
                {connectionStatus.error && ` (${connectionStatus.error})`}
              </span>
            </div>
            <button
              onClick={() => loadDirectory()}
              disabled={loading}
              className={`px-3 py-1 rounded text-sm ${buttonClasses} disabled:opacity-50`}
            >
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>

        <div className={`border rounded-lg ${panelClasses}`}>
          {/* Path Navigation */}
          <div className="p-3 border-b border-gray-300 dark:border-gray-700">
            <div className="flex items-center gap-2">
              <button
                onClick={navigateUp}
                disabled={currentPath === '/' || loading}
                className={`px-2 py-1 rounded text-sm ${buttonClasses} disabled:opacity-50`}
              >
                ↑ Up
              </button>
              <span className="text-sm font-mono">{currentPath}</span>
            </div>
          </div>

          {/* Create New Item Form */}
          {showCreateForm && (
            <div className="p-3 border-b border-gray-300 dark:border-gray-700">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={newItemName}
                  onChange={(e) => setNewItemName(e.target.value)}
                  placeholder={`Enter ${showCreateForm} name`}
                  className={`flex-1 px-2 py-1 rounded border ${isDark ? 'bg-gray-700 border-gray-600' : 'bg-white border-gray-300'}`}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleCreateItem(showCreateForm);
                    } else if (e.key === 'Escape') {
                      setShowCreateForm(null);
                      setNewItemName('');
                    }
                  }}
                  autoFocus
                />
                <button
                  onClick={() => handleCreateItem(showCreateForm)}
                  className={`px-3 py-1 rounded text-sm ${buttonClasses}`}
                >
                  Create
                </button>
                <button
                  onClick={() => {
                    setShowCreateForm(null);
                    setNewItemName('');
                  }}
                  className={`px-3 py-1 rounded text-sm ${buttonClasses}`}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="p-3 border-b border-gray-300 dark:border-gray-700">
            <div className="flex gap-2">
              <button
                onClick={() => setShowCreateForm('file')}
                disabled={loading}
                className={`px-3 py-1 rounded text-sm ${buttonClasses} disabled:opacity-50`}
              >
                + New File
              </button>
              <button
                onClick={() => setShowCreateForm('folder')}
                disabled={loading}
                className={`px-3 py-1 rounded text-sm ${buttonClasses} disabled:opacity-50`}
              >
                + New Folder
              </button>
            </div>
          </div>

          {/* File List */}
          <div className="p-3">
            {loading && (
              <div className="text-center py-4 text-gray-500">
                Loading directory contents...
              </div>
            )}
            
            {!loading && files.length === 0 && (
              <div className="text-center py-4 text-gray-500">
                Directory is empty
              </div>
            )}

            {!loading && files.length > 0 && (
              <div className="space-y-1">
                {files.map((file) => (
                  <div
                    key={file.id}
                    className={`flex items-center gap-2 p-2 rounded cursor-pointer ${itemClasses} ${
                      selectedFile === file.id ? selectedClasses : ''
                    }`}
                    onClick={() => handleItemClick(file)}
                    onContextMenu={(e) => {
                      e.preventDefault();
                      if (confirm(`Delete "${file.name}"?`)) {
                        handleDeleteItem(file);
                      }
                    }}
                  >
                    <span className="text-lg">
                      {file.type === 'folder' ? '📁' : '📄'}
                    </span>
                    <span className="flex-1">{file.name}</span>
                    {file.size && (
                      <span className="text-xs text-gray-500">
                        {Math.round(file.size / 1024)}KB
                      </span>
                    )}
                    {file.modified && (
                      <span className="text-xs text-gray-500">
                        {new Date(file.modified).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Debug Information */}
        <div className="mt-4 text-xs text-gray-500 space-y-1">
          <div>Backend URL: {backendClient['baseUrl']}</div>
          <div>Workspace Root: {(import.meta as any).env?.VITE_WORKSPACE_ROOT || 'Not set'}</div>
          <div>Current Path: {currentPath}</div>
          <div>Files Count: {files.length}</div>
          <div>Selected: {selectedFile || 'None'}</div>
          <div>Connection: {connectionStatus.connected ? '✓' : '✗'}</div>
          {connectionStatus.timestamp && (
            <div>Last Check: {new Date(connectionStatus.timestamp).toLocaleTimeString()}</div>
          )}
        </div>

        {/* Instructions */}
        <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm">
          <h3 className="font-semibold mb-2">Instructions:</h3>
          <ul className="space-y-1 text-gray-600 dark:text-gray-300">
            <li>• Click on folders to navigate into them</li>
            <li>• Click on files to select them</li>
            <li>• Use "New File" and "New Folder" buttons to create items</li>
            <li>• Right-click on items to delete them</li>
            <li>• Use "Up" button to navigate to parent directory</li>
            <li>• Connection status shows backend connectivity</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default SimpleExplorer;
