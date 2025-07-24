/**
 * ICUI Explorer Panel
 * 
 * Updated to use direct backend API calls like simpleexplorer.tsx
 * This provides reliable backend connectivity without complex state management
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useWebSocketService } from '../../contexts/BackendContext';

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

interface ICUIExplorerProps {
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
      const nodes = fileList.map((item: any) => ({
        id: item.path,
        name: item.name,
        type: item.is_directory ? 'folder' : 'file',
        path: item.path,
        size: item.size,
        modified: item.modified_at ? new Date(item.modified_at * 1000).toISOString() : undefined,
        isExpanded: false,
        children: item.is_directory ? [] : undefined
      }));

      // Sort: folders first, then files, both alphabetically
      return nodes.sort((a, b) => {
        // First sort by type (folders before files)
        if (a.type !== b.type) {
          return a.type === 'folder' ? -1 : 1;
        }
        // Then sort alphabetically by name (case-insensitive)
        return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
      });
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

const ICUIExplorer: React.FC<ICUIExplorerProps> = ({
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
  const lastLoadTimeRef = useRef(0);
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const loadDirectoryRef = useRef<(path?: string) => Promise<void>>();

  const backendClient = new ExplorerBackendClient();
  const webSocketService = useWebSocketService();

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
    if (now - lastLoadTimeRef.current < 100) {
      return;
    }
    
    setLoading(true);
    setError(null);
    lastLoadTimeRef.current = now;
    
    try {
      const connected = await checkConnection();
      if (!connected) {
        throw new Error('Backend not connected');
      }

      const directoryContents = await backendClient.getDirectoryContents(path);
      setFiles(directoryContents);
      setCurrentPath(path);
    } catch (err) {
      console.error('[ICUIExplorer] Failed to load directory:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [checkConnection]); // Remove lastLoadTime from dependencies to prevent infinite loop

  // Store loadDirectory in ref to avoid dependency issues
  useEffect(() => {
    loadDirectoryRef.current = loadDirectory;
  }, [loadDirectory]);

  // Initial load
  useEffect(() => {
    loadDirectory();
  }, []); // Remove loadDirectory from dependencies to prevent infinite loop

  // Real-time file system updates via WebSocket
  useEffect(() => {
    if (!webSocketService) {
      return;
    }

    const handleFileSystemEvent = (eventData: any) => {
      if (!eventData?.data) {
        return;
      }

      const { event, data } = eventData;
      const filePath = data.file_path || data.path;
      
      // Only react to changes in the current workspace
      if (!filePath || !filePath.startsWith(currentPath)) {
        return;
      }

      console.log('[ICUIExplorer] File system event:', event, 'for', filePath);

      switch (event) {
        case 'fs.file_created':
        case 'fs.file_deleted':
        case 'fs.file_moved':
          // Cancel any existing refresh timeout
          if (refreshTimeoutRef.current) {
            clearTimeout(refreshTimeoutRef.current);
          }
          // For these events, refresh the directory to ensure consistency
          // We debounce to avoid excessive refreshes
          refreshTimeoutRef.current = setTimeout(() => {
            if (loadDirectoryRef.current) {
              loadDirectoryRef.current(currentPath);
            }
            refreshTimeoutRef.current = null;
          }, 300);
          break;
        
        case 'fs.file_modified':
          // For file modifications, we don't need to refresh the explorer
          // since the structure hasn't changed
          break;
        
        default:
          console.debug('[ICUIExplorer] Unknown event type:', event);
      }
    };

    // Subscribe to filesystem events
    webSocketService.on('filesystem_event', handleFileSystemEvent);

    // Subscribe to filesystem events - only if connected
    const subscribeToEvents = () => {
      if (!webSocketService.isConnected()) {
        console.log('[ICUIExplorer] WebSocket not connected, waiting for connection...');
        return;
      }

      try {
        // Use the proper notification format for filesystem events
        webSocketService.notify('subscribe', { 
          topics: ['fs.file_created', 'fs.file_deleted', 'fs.file_moved'] 
        });
        console.log('[ICUIExplorer] Subscribed to filesystem events');
      } catch (error) {
        console.warn('[ICUIExplorer] Failed to subscribe to filesystem events:', error);
      }
    };

    // If already connected, subscribe immediately
    if (webSocketService.isConnected()) {
      subscribeToEvents();
    } else {
      // Wait for connection and then subscribe
      const handleConnected = () => {
        console.log('[ICUIExplorer] WebSocket connected, subscribing to events...');
        subscribeToEvents();
        webSocketService.off('connected', handleConnected);
      };
      webSocketService.on('connected', handleConnected);
    }

    return () => {
      // Clear any pending refresh timeout
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
        refreshTimeoutRef.current = null;
      }
      // Remove event listener
      webSocketService.off('filesystem_event', handleFileSystemEvent);
      
      // Unsubscribe from filesystem events
      if (webSocketService.isConnected()) {
        try {
          webSocketService.notify('unsubscribe', { 
            topics: ['fs.file_created', 'fs.file_deleted', 'fs.file_moved'] 
          });
        } catch (error) {
          console.warn('[ICUIExplorer] Failed to unsubscribe from filesystem events:', error);
        }
      }
    };
  }, [webSocketService, currentPath]); // Include currentPath to re-subscribe when directory changes

  // Helper function to find a node in the tree
  const findNodeInTree = useCallback((nodes: FileNode[], nodeId: string): FileNode | null => {
    for (const node of nodes) {
      if (node.id === nodeId) {
        return node;
      }
      if (node.children) {
        const found = findNodeInTree(node.children, nodeId);
        if (found) return found;
      }
    }
    return null;
  }, []);

  // Toggle folder expansion (VS Code-like behavior)
  const toggleFolderExpansion = useCallback(async (folder: FileNode) => {
    if (!isConnected) return;

    setFiles(currentFiles => {
      const updateFileTree = (nodes: FileNode[]): FileNode[] => {
        return nodes.map(node => {
          if (node.id === folder.id && node.type === 'folder') {
            if (node.isExpanded) {
              // Collapse folder
              return { ...node, isExpanded: false };
            } else {
              // Expand folder - we'll load children if not already loaded
              return { ...node, isExpanded: true };
            }
          }
          // Recursively update children if they exist
          if (node.children && node.children.length > 0) {
            return { ...node, children: updateFileTree(node.children) };
          }
          return node;
        });
      };

      const updatedFiles = updateFileTree(currentFiles);
      
      // Load children if folder is being expanded and doesn't have children yet
      const targetFolder = findNodeInTree(updatedFiles, folder.id);
      if (targetFolder && targetFolder.isExpanded && (!targetFolder.children || targetFolder.children.length === 0)) {
        // Load children asynchronously without affecting current state update
        (async () => {
          try {
            const children = await backendClient.getDirectoryContents(folder.path);
            
            // Update the specific folder with its children
            setFiles(prevFiles => {
              const updateWithChildren = (nodes: FileNode[]): FileNode[] => {
                return nodes.map(node => {
                  if (node.id === folder.id) {
                    return { ...node, children };
                  }
                  if (node.children && node.children.length > 0) {
                    return { ...node, children: updateWithChildren(node.children) };
                  }
                  return node;
                });
              };
              return updateWithChildren(prevFiles);
            });
          } catch (err) {
            console.error('Failed to load folder contents:', err);
            setError(err instanceof Error ? err.message : 'Failed to load folder contents');
          }
        })();
      }
      
      return updatedFiles;
    });
  }, [isConnected, findNodeInTree]);

  // Handle file/folder selection
  const handleItemClick = useCallback(async (item: FileNode) => {
    setSelectedFile(item.id);
    onFileSelect?.(item);
    
    if (item.type === 'folder') {
      // VS Code-like behavior: expand/collapse folder instead of navigating
      await toggleFolderExpansion(item);
    }
  }, [onFileSelect, toggleFolderExpansion]);

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

  // Render file tree with proper nesting and VS Code-like expand/collapse
  const renderFileTree = (nodes: FileNode[], level: number = 0) => {
    return nodes.map(node => (
      <div key={node.id}>
        <div
          className={`flex items-center py-1 cursor-pointer hover:opacity-80 transition-opacity group ${
            selectedFile === node.id ? 'opacity-100' : ''
          }`}
          style={{ 
            backgroundColor: selectedFile === node.id ? 'var(--icui-accent)' : 'transparent',
            color: 'var(--icui-text-primary)',
            paddingLeft: `${8 + level * 16}px`  // Indentation based on nesting level
          }}
          onClick={() => handleItemClick(node)}
          onContextMenu={(e) => {
            e.preventDefault();
            if (node.type === 'file') {
              handleDeleteItem(node);
            }
          }}
        >
          {/* Expand/collapse icon for folders */}
          {node.type === 'folder' && (
            <span className="mr-1 text-xs" style={{ width: '12px', textAlign: 'center' }}>
              {node.isExpanded ? 'v' : '>'}
            </span>
          )}
          {node.type === 'file' && (
            <span className="mr-1 text-xs" style={{ width: '12px' }}></span>
          )}
          
          {/* File/folder icon */}
          <span className="mr-2 text-sm">
            {node.type === 'folder' ? (node.isExpanded ? '📂' : '📁') : '📄'}
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
        
        {/* Render children if folder is expanded */}
        {node.type === 'folder' && node.isExpanded && node.children && (
          <div>
            {renderFileTree(node.children, level + 1)}
          </div>
        )}
      </div>
    ));
  };

  return (
    <div className={`icui-explorer h-full flex flex-col ${className}`} style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)' }}>
      {/* Header */}
      <div className="flex items-center justify-between p-2 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)' }}>
        <div className="flex items-center space-x-2">
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
    </div>
  );
};

export default ICUIExplorer;
