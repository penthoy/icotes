/**
 * Backend-Connected Explorer Panel
 * 
 * This component extends the ICUIExplorerPanel to work with the ICPY backend
 * via the useBackendState hook. It replaces static file data with real backend
 * file system operations.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useBackendState } from '../../../src/hooks/useBackendState';
import { useBackendContext } from '../../../src/contexts/BackendContext';

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

const BackendConnectedExplorer: React.FC<BackendConnectedExplorerProps> = ({
  className = '',
  onFileSelect,
  onFileCreate,
  onFolderCreate,
  onFileDelete,
  onFileRename,
}) => {
  const { workspaceState, files, actions } = useBackendState();
  const { isConnected, connectionStatus } = useBackendContext();
  
  const [explorerFiles, setExplorerFiles] = useState<FileNode[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastLoadTime, setLastLoadTime] = useState(0); // Track last load time to prevent rapid reloads

  // Convert backend files to explorer format
  const convertBackendFilesToExplorer = useCallback((backendFiles: any[]): FileNode[] => {
    return backendFiles.map(file => ({
      id: file.id || file.path,
      name: file.name || file.path.split('/').pop() || 'Unknown',
      type: file.type || (file.isDirectory ? 'folder' : 'file'),
      path: file.path,
      isExpanded: false,
      size: file.size,
      modified: file.modified_at || file.lastModified,
    }));
  }, []);

  // Load directory contents from backend
  const loadDirectoryContents = useCallback(async (path: string = '/') => {
    if (!isConnected) return;
    
    // Prevent rapid successive calls (debounce)
    const now = Date.now();
    if (now - lastLoadTime < 100) { // 100ms debounce
      return;
    }
    
    setLoading(true);
    setError(null);
    setLastLoadTime(now);
    
    try {
      // Use the backend client to get directory contents
      const directoryContents = await actions.getDirectoryContents(path);
      const explorerNodes = convertBackendFilesToExplorer(directoryContents);
      setExplorerFiles(explorerNodes);
    } catch (err) {
      console.error('Failed to load directory contents:', err);
      setError(err instanceof Error ? err.message : 'Failed to load directory');
    } finally {
      setLoading(false);
    }
  }, [isConnected, actions, convertBackendFilesToExplorer, lastLoadTime]);

  // Load initial directory contents when connected
  useEffect(() => {
    if (isConnected && explorerFiles.length === 0) {
      loadDirectoryContents();
    }
  }, [isConnected]); // Remove loadDirectoryContents from dependencies to prevent infinite loops

  // Handle file/folder selection
  const handleItemClick = useCallback((item: FileNode) => {
    if (item.type === 'folder') {
      // Toggle folder expansion and load contents if needed
      setExplorerFiles(prev => {
        const updateNode = (nodes: FileNode[]): FileNode[] => {
          return nodes.map(node => {
            if (node.id === item.id && node.type === 'folder') {
              const newExpanded = !node.isExpanded;
              // Load folder contents if expanding
              if (newExpanded && !node.children) {
                loadDirectoryContents(item.path);
              }
              return { ...node, isExpanded: newExpanded };
            }
            if (node.children) {
              return { ...node, children: updateNode(node.children) };
            }
            return node;
          });
        };
        return updateNode(prev);
      });
    } else {
      // File selection
      setSelectedFile(item.id);
      onFileSelect?.(item);
    }
  }, [onFileSelect, loadDirectoryContents]);

  // Handle file creation
  const handleFileCreate = useCallback(async () => {
    if (!isConnected) return;
    
    const fileName = prompt('Enter file name:');
    if (!fileName) return;
    
    try {
      await actions.createFile(fileName, '');
      await loadDirectoryContents(); // Refresh directory
      onFileCreate?.(fileName);
    } catch (err) {
      console.error('Failed to create file:', err);
      setError('Failed to create file');
    }
  }, [isConnected, actions, loadDirectoryContents, onFileCreate]);

  // Handle folder creation
  const handleFolderCreate = useCallback(async () => {
    if (!isConnected) return;
    
    const folderName = prompt('Enter folder name:');
    if (!folderName) return;
    
    try {
      await actions.createDirectory(folderName);
      await loadDirectoryContents(); // Refresh directory
      onFolderCreate?.(folderName);
    } catch (err) {
      console.error('Failed to create folder:', err);
      setError('Failed to create folder');
    }
  }, [isConnected, actions, loadDirectoryContents, onFolderCreate]);

  // Handle file deletion
  const handleFileDelete = useCallback(async (file: FileNode) => {
    if (!isConnected) return;
    
    if (!confirm(`Are you sure you want to delete ${file.name}?`)) return;
    
    try {
      await actions.deleteFile(file.id);
      await loadDirectoryContents(); // Refresh directory
      onFileDelete?.(file.path);
    } catch (err) {
      console.error('Failed to delete file:', err);
      setError('Failed to delete file');
    }
  }, [isConnected, actions, loadDirectoryContents, onFileDelete]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    loadDirectoryContents();
  }, [loadDirectoryContents]);

  // Render file tree recursively
  const renderFileTree = (nodes: FileNode[], level: number = 0) => {
    return nodes.map(node => (
      <div key={node.id}>
        <div
          className={`flex items-center py-1 px-2 cursor-pointer hover:opacity-80 transition-opacity ${
            selectedFile === node.id ? 'opacity-100' : ''
          }`}
          style={{ 
            paddingLeft: `${(level * 16) + 8}px`,
            backgroundColor: selectedFile === node.id ? 'var(--icui-accent)' : 'transparent',
            color: 'var(--icui-text-primary)'
          }}
          onClick={() => handleItemClick(node)}
          onContextMenu={(e) => {
            e.preventDefault();
            // Future: Show context menu for file operations
          }}
        >
          <span className="mr-2 text-sm">
            {node.type === 'folder' ? (node.isExpanded ? '📂' : '📁') : '📄'}
          </span>
          <span className="text-sm flex-1">{node.name}</span>
          {node.type === 'file' && node.size && (
            <span className="text-xs text-gray-500 ml-2">
              {(node.size / 1024).toFixed(1)}KB
            </span>
          )}
          {node.type === 'file' && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleFileDelete(node);
              }}
              className="ml-2 text-xs text-red-500 hover:text-red-700 opacity-0 group-hover:opacity-100"
              title="Delete file"
            >
              ×
            </button>
          )}
        </div>
        {node.type === 'folder' && node.isExpanded && node.children && (
          <div>
            {renderFileTree(node.children, level + 1)}
          </div>
        )}
      </div>
    ));
  };

  // Connection status indicator
  const renderConnectionStatus = () => {
    if (!isConnected) {
      return (
        <div className="px-3 py-2 text-center text-sm text-yellow-600 bg-yellow-50 border-b">
          Not connected to backend
        </div>
      );
    }
    return null;
  };

  return (
    <div className={`backend-connected-explorer h-full flex flex-col ${className}`} style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)' }}>
      {/* Connection Status */}
      {renderConnectionStatus()}
      
      {/* Header */}
      <div className="flex items-center justify-between p-2 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)' }}>
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium" style={{ color: 'var(--icui-text-primary)' }}>
            Backend Explorer
          </span>
          {loading && <span className="text-xs text-blue-500">Loading...</span>}
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={handleFileCreate}
            disabled={!isConnected}
            className="text-xs px-2 py-1 rounded hover:opacity-80 transition-opacity disabled:opacity-50"
            style={{ backgroundColor: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-primary)' }}
            title="Create new file"
          >
            📄
          </button>
          <button
            onClick={handleFolderCreate}
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

      {/* Error Display */}
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
        ) : explorerFiles.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-500">
            {isConnected ? 'No files found' : 'Connect to backend to view files'}
          </div>
        ) : (
          <div className="p-1">
            {renderFileTree(explorerFiles)}
          </div>
        )}
      </div>

      {/* Status bar */}
      <div className="px-3 py-1 border-t text-xs" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderTopColor: 'var(--icui-border-subtle)', color: 'var(--icui-text-muted)' }}>
        <div className="flex items-center justify-between">
          <span>
            {selectedFile 
              ? `Selected: ${explorerFiles.find(f => f.id === selectedFile)?.name || 'Unknown'}` 
              : `${explorerFiles.length} items`
            }
          </span>
          <span className={`text-xs ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
            {connectionStatus}
          </span>
        </div>
      </div>
    </div>
  );
};

export default BackendConnectedExplorer;
