/**
 * ICUI Explorer Panel - Backend Connected Implementation
 * A file explorer panel that connects directly to the ICPY backend
 * Following the proven pattern from ICUIExplorer
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';

interface ICUIExplorerPanelProps {
  className?: string;
}

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

// Backend client for file operations
class ExplorerBackendClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = (import.meta as any).env?.VITE_API_URL || '';
  }

  async getDirectoryContents(path: string = '/'): Promise<FileNode[]> {
    try {
      const encodedPath = encodeURIComponent(path);
      const response = await fetch(`${this.baseUrl}/api/files?path=${encodedPath}`);
      
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
      const response = await fetch(`${this.baseUrl}/api/files`, {
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

  async deleteFile(path: string): Promise<void> {
    try {
      const encodedPath = encodeURIComponent(path);
      const response = await fetch(`${this.baseUrl}/api/files?path=${encodedPath}`, {
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

const ICUIExplorerPanel: React.FC<ICUIExplorerPanelProps> = ({ className = '' }) => {
  const [files, setFiles] = useState<FileNode[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPath, setCurrentPath] = useState<string>((import.meta as any).env?.VITE_WORKSPACE_ROOT || '/home/penthoy/ilaborcode/workspace');
  
  const backendClient = useRef(new ExplorerBackendClient());

  // Load directory contents
  const loadDirectory = useCallback(async (path: string) => {
    setLoading(true);
    setError(null);
    try {
      console.log('Loading directory:', path);
      const directoryContents = await backendClient.current.getDirectoryContents(path);
      console.log('Directory contents received:', directoryContents);
      setFiles(directoryContents);
      setCurrentPath(path);
    } catch (err) {
      console.error('Failed to load directory:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      setFiles([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadDirectory(currentPath);
  }, []);

  // Handle file/folder click
  const handleItemClick = useCallback((item: FileNode) => {
    setSelectedFile(item.id);
    
    if (item.type === 'folder') {
      loadDirectory(item.path);
    }
  }, [loadDirectory]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    loadDirectory(currentPath);
  }, [currentPath, loadDirectory]);

  // Handle create file
  const handleCreateFile = useCallback(async () => {
    const fileName = prompt('Enter file name:');
    if (!fileName) return;

    try {
      const newPath = `${currentPath}/${fileName}`.replace(/\/+/g, '/');
      await backendClient.current.createFile(newPath, '');
      await loadDirectory(currentPath);
    } catch (err) {
      console.error('Failed to create file:', err);
      setError(err instanceof Error ? err.message : 'Failed to create file');
    }
  }, [currentPath, loadDirectory]);

  // Handle delete file
  const handleDeleteFile = useCallback(async (item: FileNode) => {
    if (!confirm(`Are you sure you want to delete "${item.name}"?`)) {
      return;
    }

    try {
      await backendClient.current.deleteFile(item.path);
      await loadDirectory(currentPath);
    } catch (err) {
      console.error('Failed to delete file:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete file');
    }
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
              handleDeleteFile(node);
            }
          }}
        >
          <span className="mr-2 text-sm">
            {node.type === 'folder' ? '' : '📄'}
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
                handleDeleteFile(node);
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
    <div className={`icui-explorer-panel h-full flex flex-col ${className}`} style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)' }}>
      {/* Header */}
      <div className="flex items-center justify-between p-2 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)' }}>
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium" style={{ color: 'var(--icui-text-primary)' }}>Explorer</span>
          {loading && <span className="text-xs text-blue-500">Loading...</span>}
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={handleCreateFile}
            disabled={loading}
            className="text-xs px-2 py-1 rounded hover:opacity-80 transition-opacity disabled:opacity-50"
            style={{ backgroundColor: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-primary)' }}
            title="Create new file"
          >
            📄
          </button>
          <button
            onClick={handleRefresh}
            disabled={loading}
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

      {/* Current path display */}
      <div className="px-3 py-1 border-b text-xs" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)', color: 'var(--icui-text-muted)' }}>
        <span className="font-mono">{currentPath}</span>
      </div>

      {/* File tree */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-center text-sm text-gray-500">
            Loading directory contents...
          </div>
        ) : files.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-500">
            {error ? 'Failed to load directory' : 'Directory is empty'}
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
          <span className={loading ? 'text-blue-600' : error ? 'text-red-600' : 'text-green-600'}>
            {loading ? 'Loading...' : error ? 'Error' : 'Ready'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default ICUIExplorerPanel;
