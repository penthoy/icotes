/**
 * Backend-Connected Explorer Panel
 * 
 * Updated to use direct backend API calls like simpleexplorer.tsx
 * This provides reliable backend connectivity without complex state management
 */

import React, { useState, useEffect, useCallback } from 'react';

interface FileNode {
  id: string;
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: FileNode[];
  isExpanded?: boolean; 
  size?: number;
  modified?: string;
}

interface BackendConnectedExplorerProps {
  className?: string;
  onFileSelect?: (file: FileNode) => void;
  onFileCreate?: (path: string) => void;
  onFolderCreate?: (path: string) => void;
  onFileDelete?: (path: string) => void;
  onFileRename?: (oldPath: string, newPath: string) => void;
}

// Backend client for file operations (following simpleexplorer.tsx pattern)
class ExplorerBackendClient {
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

  async getDirectoryContents(path: string = '/'): Promise<FileNode[]> {
    try {
      const encodedPath = encodeURIComponent(path);
      const response = await fetch(`${this.baseUrl}/files?path=${encodedPath}`);
      
      if (!response.ok) {
        throw new Error(`Failed to get directory contents: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.message || 'API request failed');
      }
      
      const fileList = result.data || [];
      
      // Convert backend response to FileNode format
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
}

const BackendConnectedExplorer: React.FC<BackendConnectedExplorerProps> = ({
  className = '',
  onFileSelect,
  onFileCreate,
  onFolderCreate,
  onFileDelete,
  onFileRename,
}) => {
  const [files, setFiles] = useState<FileNode[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [currentPath, setCurrentPath] = useState<string>((import.meta as any).env?.VITE_WORKSPACE_ROOT || '/home/penthoy/ilaborcode/workspace');
  const [lastLoadTime, setLastLoadTime] = useState(0);

  const backendClient = new ExplorerBackendClient();

  // Check connection status
  const checkConnection = useCallback(async () => {
    const connected = await backendClient.checkConnection();
    setIsConnected(connected);
    return connected;
  }, []);

  // Load directory contents
  const loadDirectory = useCallback(async (path: string = (import.meta as any).env?.VITE_WORKSPACE_ROOT || '/home/penthoy/ilaborcode/workspace') => {
    // Prevent rapid successive calls (debounce)
    const now = Date.now();
    if (now - lastLoadTime < 100) {
      return;
    }
    
    setLoading(true);
    setError(null);
    setLastLoadTime(now);
    
    try {
      const connected = await checkConnection();
      if (!connected) {
        throw new Error('Backend not connected');
      }

      console.log('Loading directory:', path);
      const directoryContents = await backendClient.getDirectoryContents(path);
      console.log('Directory contents received:', directoryContents);
      setFiles(directoryContents);
      setCurrentPath(path);
    } catch (err) {
      console.error('Failed to load directory:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [checkConnection, lastLoadTime]);

  // Initial load
  useEffect(() => {
    loadDirectory();
  }, []);

  // Handle file/folder selection
  const handleItemClick = useCallback((item: FileNode) => {
    setSelectedFile(item.id);
    onFileSelect?.(item);
    
    if (item.type === 'folder') {
      loadDirectory(item.path);
    }
  }, [loadDirectory, onFileSelect]);

  // Handle creating new files/folders
  const handleCreateFile = useCallback(async () => {
    if (!isConnected) return;
    
    const fileName = prompt('Enter file name:');
    if (!fileName?.trim()) return;

    const newPath = `${currentPath}/${fileName.trim()}`.replace(/\/+/g, '/');

    try {
      await backendClient.createFile(newPath);
      await loadDirectory(currentPath);
      onFileCreate?.(newPath);
    } catch (err) {
      console.error('Failed to create file:', err);
      setError(err instanceof Error ? err.message : 'Failed to create file');
    }
  }, [isConnected, currentPath, loadDirectory, onFileCreate]);

  const handleCreateFolder = useCallback(async () => {
    if (!isConnected) return;

    const folderName = prompt('Enter folder name:');
    if (!folderName?.trim()) return;

    const newPath = `${currentPath}/${folderName.trim()}`.replace(/\/+/g, '/');

    try {
      await backendClient.createDirectory(newPath);
      await loadDirectory(currentPath);
      onFolderCreate?.(newPath);
    } catch (err) {
      console.error('Failed to create folder:', err);
      setError(err instanceof Error ? err.message : 'Failed to create folder');
    }
  }, [isConnected, currentPath, loadDirectory, onFolderCreate]);

  // Handle deleting items
  const handleDeleteItem = useCallback(async (item: FileNode) => {
    if (!isConnected) return;

    if (!confirm(`Are you sure you want to delete "${item.name}"?`)) {
      return;
    }

    try {
      await backendClient.deleteFile(item.path);
      await loadDirectory(currentPath);
      onFileDelete?.(item.path);
    } catch (err) {
      console.error('Failed to delete item:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete item');
    }
  }, [isConnected, currentPath, loadDirectory, onFileDelete]);

  // Navigate up one level
  const navigateUp = useCallback(() => {
    const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/';
    loadDirectory(parentPath);
  }, [currentPath, loadDirectory]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    loadDirectory(currentPath);
  }, [currentPath, loadDirectory]);

  // Render file tree
  const renderFileTree = (nodes: FileNode[]) => {
    return nodes.map(node => (
      <div key={node.id}>
        <div
          className={`flex items-center py-1 px-2 cursor-pointer hover:opacity-80 transition-opacity group ${
            selectedFile === node.id ? 'opacity-100' : ''
          }`}
          style={{ 
            backgroundColor: selectedFile === node.id ? 'var(--icui-accent)' : 'transparent',
            color: 'var(--icui-text-primary)'
          }}
          onClick={() => handleItemClick(node)}
          onContextMenu={(e) => {
            e.preventDefault();
            if (node.type === 'file') {
              handleDeleteItem(node);
            }
          }}
        >
          <span className="mr-2 text-sm">
            {node.type === 'folder' ? '📁' : '📄'}
          </span>
          <span className="text-sm flex-1">{node.name}</span>
          {node.size && (
            <span className="text-xs text-gray-500 ml-2">
              {Math.round(node.size / 1024)}KB
            </span>
          )}
          {node.type === 'file' && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDeleteItem(node);
              }}
              className="ml-2 text-xs text-red-500 hover:text-red-700 opacity-0 group-hover:opacity-100"
              title="Delete file"
            >
              ×
            </button>
          )}
        </div>
      </div>
    ));
  };

  return (
    <div className={`backend-connected-explorer h-full flex flex-col ${className}`} style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)' }}>
      {/* Connection Status */}
      {!isConnected && (
        <div className="px-3 py-2 text-center text-sm text-yellow-600 bg-yellow-50 border-b">
          Not connected to backend
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between p-2 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)' }}>
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium" style={{ color: 'var(--icui-text-primary)' }}>Explorer</span>
          {loading && <span className="text-xs text-blue-500">Loading...</span>}
          <span className="text-xs px-2 py-1 rounded" style={{ backgroundColor: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-secondary)' }}>
            {currentPath}
          </span>
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={handleCreateFile}
            disabled={!isConnected}
            className="text-xs px-2 py-1 rounded hover:opacity-80 transition-opacity disabled:opacity-50"
            style={{ backgroundColor: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-primary)' }}
            title="Create new file"
          >
            📄
          </button>
          <button
            onClick={handleCreateFolder}
            disabled={!isConnected}
            className="text-xs px-2 py-1 rounded hover:opacity-80 transition-opacity disabled:opacity-50"
            style={{ backgroundColor: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-primary)' }}
            title="Create new folder"
          >
            📁
          </button>
          <button
            onClick={handleRefresh}
            disabled={!isConnected || loading}
            className="text-xs px-2 py-1 rounded hover:opacity-80 transition-opacity disabled:opacity-50"
            style={{ backgroundColor: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-primary)' }}
            title="Refresh"
          >
            🔄
          </button>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="px-3 py-2 text-sm text-red-600 bg-red-50 border-b">
          {error}
        </div>
      )}

      {/* File tree */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-center text-sm text-gray-500">
            Loading directory contents...
          </div>
        ) : files.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-500">
            {error ? 'Failed to load directory' : isConnected ? 'Directory is empty' : 'Connect to backend to view files'}
          </div>
        ) : (
          <div className="p-1">
            {renderFileTree(files)}
          </div>
        )}
      </div>

      {/* Status bar */}
      <div className="px-3 py-1 border-t text-xs" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderTopColor: 'var(--icui-border-subtle)', color: 'var(--icui-text-muted)' }}>
        <div className="flex items-center justify-between">
          <span>
            {selectedFile ? `Selected: ${files.find(f => f.id === selectedFile)?.name || 'Unknown'}` : `${files.length} items`}
          </span>
          <span className={isConnected ? 'text-green-600' : 'text-red-600'}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default BackendConnectedExplorer;
