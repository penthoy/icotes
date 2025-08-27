/**
 * ICUI Explorer Panel
 * 
 * Updated to use centralized backend service and workspace utilities.
 * This eliminates code duplication and provides consistent behavior.
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { 
  ChevronDown, 
  ChevronRight, 
  FileText, 
  FolderOpen, 
  Folder, 
  Plus, 
  MoreVertical,
  RefreshCw,
  Lock,
  Unlock,
  MoreHorizontal,
  Eye,
  EyeOff
} from "lucide-react";
import { backendService, ICUIFileNode, useTheme } from '../services';
import { getWorkspaceRoot } from '../lib';
import { explorerPreferences } from '../../lib/utils';
import { log } from '../../services/frontend-logger';
import { Button } from './ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';

interface FileNode extends ICUIFileNode {} // For backward compatibility

interface ICUIExplorerProps {
  className?: string;
  onFileSelect?: (file: FileNode) => void;
  onFileDoubleClick?: (file: FileNode) => void;
  onFileCreate?: (path: string) => void;
  onFolderCreate?: (path: string) => void;
  onFileDelete?: (path: string) => void;
  onFileRename?: (oldPath: string, newPath: string) => void;
}

const ICUIExplorer: React.FC<ICUIExplorerProps> = ({
  className = '',
  onFileSelect,
  onFileDoubleClick,
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
  
  // Initialize with workspace root
  const initialWorkspaceRoot = getWorkspaceRoot();
  
  const [currentPath, setCurrentPath] = useState<string>(initialWorkspaceRoot);
  const [isPathLocked, setIsPathLocked] = useState(true); // New state for path lock
  const [editablePath, setEditablePath] = useState<string>(''); // State for editable path
  const [showHiddenFiles, setShowHiddenFiles] = useState(explorerPreferences.getShowHiddenFiles()); // Show hidden files toggle
  const lastLoadTimeRef = useRef(0);
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const loadDirectoryRef = useRef<(path?: string) => Promise<void>>();

  const { theme } = useTheme();

  // Check connection status using centralized service
  const checkConnection = useCallback(async () => {
    try {
      const status = await backendService.getConnectionStatus();
      const connected = status.connected;
      setIsConnected(connected);
      return connected;
    } catch (error) {
      console.error('Connection check failed:', error);
      setIsConnected(false);
      return false;
    }
  }, []);

  // Build a map of previous nodes by path for quick lookup
  const buildNodeMapByPath = useCallback((nodes: FileNode[], map: Map<string, FileNode> = new Map()): Map<string, FileNode> => {
    for (const n of nodes) {
      map.set(n.path, n);
      if (n.children && n.children.length > 0) buildNodeMapByPath(n.children as FileNode[], map);
    }
    return map;
  }, []);

  // Merge new directory listing with previous state to preserve expanded folders
  const mergeTreePreserveExpanded = useCallback((prev: FileNode[], next: FileNode[]): FileNode[] => {
    if (!prev || prev.length === 0) return next;
    const prevMap = buildNodeMapByPath(prev);
    const mergeLevel = (nodes: FileNode[]): FileNode[] => nodes.map(node => {
      const prevNode = prevMap.get(node.path);
      if (node.type === 'folder') {
        const isExpanded = Boolean(prevNode?.isExpanded);
        // Keep existing children for expanded folders (they'll be refreshed separately)
        const children = isExpanded ? (prevNode?.children || node.children) : node.children;
        return { ...node, isExpanded, children } as FileNode;
      }
      return node;
    });
    return mergeLevel(next);
  }, [buildNodeMapByPath]);

  // Load directory contents using centralized service
  const loadDirectory = useCallback(async (path: string = getWorkspaceRoot()) => {
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

      const directoryContents = await backendService.getDirectoryContents(path, showHiddenFiles);
      
      // Instead of merging at setState time, we'll refresh expanded folders after setting the new data
      setFiles(prevFiles => {
        const prevMap = buildNodeMapByPath(prevFiles);
        const mergedFiles = (directoryContents as FileNode[]).map(node => {
          const prevNode = prevMap.get(node.path);
          if (node.type === 'folder' && prevNode?.isExpanded) {
            return { ...node, isExpanded: true, children: prevNode.children };
          }
          return node;
        });
        
        // After state is updated, refresh contents of all expanded folders (any depth)
        const collectExpanded = (nodes: FileNode[], acc: FileNode[] = []): FileNode[] => {
          for (const n of nodes) {
            if (n.type === 'folder' && n.isExpanded) acc.push(n);
            if (n.children && n.children.length > 0) collectExpanded(n.children as FileNode[], acc);
          }
          return acc;
        };
        setTimeout(async () => {
          const expanded = collectExpanded(mergedFiles);
          if (expanded.length === 0) return;
          try {
            const results = await Promise.all(
              expanded.map(async (folder) => ({
                path: folder.path,
                children: await backendService.getDirectoryContents(folder.path, showHiddenFiles),
              }))
            );
            setFiles(currentFiles => {
              const apply = (nodes: FileNode[]): FileNode[] =>
                nodes.map(node => {
                  const match = results.find(r => r.path === node.path);
                  const nextChildren = node.children ? apply(node.children as FileNode[]) : node.children;
                  if (match) return { ...node, children: match.children };
                  return node.children ? { ...node, children: nextChildren } : node;
                });
              return apply(currentFiles);
            });
          } catch (err) {
            console.warn('Failed to refresh expanded folders:', err);
          }
        }, 10);
        
        return mergedFiles;
      });
      
      setCurrentPath(path);
      // Always update editable path when current path changes (both locked and unlocked modes)
      setEditablePath(path);
    } catch (err) {
      log.error('ICUIExplorer', 'Failed to load directory', { path, error: err }, err instanceof Error ? err : undefined);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [checkConnection, showHiddenFiles, isPathLocked, buildNodeMapByPath]); // Add showHiddenFiles to dependencies  // Store loadDirectory in ref to avoid dependency issues
  useEffect(() => {
    loadDirectoryRef.current = loadDirectory;
  }, [loadDirectory]);

  // Initial load
  useEffect(() => {
    loadDirectory();
  }, []); // Remove loadDirectory from dependencies to prevent infinite loop

  // Real-time file system updates via WebSocket
  useEffect(() => {
    if (!backendService) {
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

      // File system event received for workspace path: ${filePath}

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
          // Unknown event type received
      }
    };

    // Subscribe to filesystem events
    backendService.on('filesystem_event', handleFileSystemEvent);

    // Subscribe to filesystem events - only if connected
    const subscribeToEvents = async () => {
      try {
        const status = await backendService.getConnectionStatus();
        if (!status.connected) {
          // console.log('[ICUIExplorer] Backend not connected, waiting for connection...');
          return;
        }

        // console.log('[ICUIExplorer] Subscribing to filesystem events...');
        await backendService.notify('subscribe', { 
          topics: ['fs.file_created', 'fs.file_deleted', 'fs.file_moved'] 
        });
        // console.log('[ICUIExplorer] Successfully subscribed to filesystem events');
      } catch (error) {
        console.error('[ICUIExplorer] Failed to subscribe to filesystem events:', error);
        log.warn('ICUIExplorer', 'Failed to subscribe to filesystem events', { error });
      }
    };

    // If already connected, subscribe immediately
    const initConnection = async () => {
      try {
        const status = await backendService.getConnectionStatus();
        
        if (status.connected) {
          await subscribeToEvents();
        } else {
          // Wait for connection and then subscribe
          const handleConnected = async () => {
            await subscribeToEvents();
            backendService.off('connected', handleConnected);
          };

          backendService.on('connected', handleConnected);
        }
      } catch (error) {
        console.error('[ICUIExplorer] Error initializing connection:', error);
      }
    };

    initConnection();

    return () => {
      // Clear any pending refresh timeout
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
        refreshTimeoutRef.current = null;
      }
      // Remove event listener
      backendService.off('filesystem_event', handleFileSystemEvent);
      
      // Unsubscribe from filesystem events
      const cleanup = async () => {
        try {
          const status = await backendService.getConnectionStatus();
          if (status.connected) {
            await backendService.notify('unsubscribe', { 
              topics: ['fs.file_created', 'fs.file_deleted', 'fs.file_moved'] 
            });
          }
        } catch (error) {
          log.warn('ICUIExplorer', 'Failed to unsubscribe from filesystem events', { error });
        }
      };
      cleanup();
    };
  }, [currentPath]); // Include currentPath to re-subscribe when directory changes

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
            const children = await backendService.getDirectoryContents(folder.path, showHiddenFiles);
            
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
      if (isPathLocked) {
        // Locked mode: VS Code-like behavior: expand/collapse folder
        await toggleFolderExpansion(item);
      } else {
        // Unlocked mode: navigate into the folder
        loadDirectory(item.path);
      }
    }
  }, [onFileSelect, toggleFolderExpansion, isPathLocked, loadDirectory]);

  // Handle file double-click for permanent opening
  const handleItemDoubleClick = useCallback((item: FileNode) => {
    if (item.type === 'file') {
      onFileDoubleClick?.(item);
    }
  }, [onFileDoubleClick]);

  // Handle creating new files/folders
  const handleCreateFile = useCallback(async () => {
    if (!isConnected) return;
    
    const fileName = prompt('Enter file name:');
    if (!fileName?.trim()) return;

    const newPath = `${currentPath}/${fileName.trim()}`.replace(/\/+/g, '/');

    try {
      await backendService.createFile(newPath);
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
      await backendService.createDirectory(newPath);
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
      await backendService.deleteFile(item.path);
      await loadDirectory(currentPath);
      onFileDelete?.(item.path);
    } catch (err) {
      console.error('Failed to delete item:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete item');
    }
  }, [isConnected, currentPath, loadDirectory, onFileDelete]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    loadDirectory(currentPath);
  }, [currentPath, loadDirectory]);

  // Handle toggle hidden files
  const handleToggleHiddenFiles = useCallback(() => {
    // Read current state directly from localStorage to avoid stale closure
    const currentState = explorerPreferences.getShowHiddenFiles();
    const newState = !currentState;
    
    // Update both localStorage and state
    explorerPreferences.setShowHiddenFiles(newState);
    setShowHiddenFiles(newState);
    
    // Refresh directory to show/hide files immediately with the new state
    backendService.getDirectoryContents(currentPath, newState).then(directoryContents => {
      setFiles(prevFiles => {
        const prevMap = buildNodeMapByPath(prevFiles);
        const mergedFiles = (directoryContents as FileNode[]).map(node => {
          const prevNode = prevMap.get(node.path);
          if (node.type === 'folder' && prevNode?.isExpanded) {
            return { ...node, isExpanded: true, children: prevNode.children };
          }
          return node;
        });
        
        const collectExpanded = (nodes: FileNode[], acc: FileNode[] = []): FileNode[] => {
          for (const n of nodes) {
            if (n.type === 'folder' && n.isExpanded) acc.push(n);
            if (n.children && n.children.length > 0) collectExpanded(n.children as FileNode[], acc);
          }
          return acc;
        };
        setTimeout(async () => {
          const expanded = collectExpanded(mergedFiles);
          if (expanded.length === 0) return;
          try {
            const results = await Promise.all(
              expanded.map(async (folder) => ({
                path: folder.path,
                children: await backendService.getDirectoryContents(folder.path, newState),
              }))
            );
            setFiles(currentFiles => {
              const apply = (nodes: FileNode[]): FileNode[] =>
                nodes.map(node => {
                  const match = results.find(r => r.path === node.path);
                  const nextChildren = node.children ? apply(node.children as FileNode[]) : node.children;
                  if (match) return { ...node, children: match.children };
                  return node.children ? { ...node, children: nextChildren } : node;
                });
              return apply(currentFiles);
            });
          } catch (err) {
            console.warn('Failed to refresh expanded folders:', err);
          }
        }, 10);
        
        return mergedFiles;
      });
    }).catch(err => {
      console.error('Failed to refresh directory:', err);
      setError(err instanceof Error ? err.message : 'Failed to refresh directory');
    });
  }, [currentPath, buildNodeMapByPath]);

  // Handle path lock toggle
  const togglePathLock = useCallback(() => {
    if (isPathLocked) {
      // Unlocking: set editable path to current path
      setEditablePath(currentPath);
      setIsPathLocked(false);
    } else {
      // Locking: navigate to the editable path if it's different
      if (editablePath !== currentPath && editablePath.trim()) {
        loadDirectory(editablePath.trim());
      }
      setIsPathLocked(true);
    }
  }, [isPathLocked, currentPath, editablePath, loadDirectory]);

  // Handle path input change
  const handlePathChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setEditablePath(event.target.value);
  }, []);

  // Handle path input key press
  const handlePathKeyPress = useCallback((event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      if (editablePath.trim()) {
        loadDirectory(editablePath.trim());
      }
    } else if (event.key === 'Escape') {
      setEditablePath(currentPath);
    }
  }, [editablePath, currentPath, loadDirectory]);

  // Navigate up one level (when unlocked)
  const navigateToParent = useCallback(() => {
    const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/';
    loadDirectory(parentPath);
  }, [currentPath, loadDirectory]);

  // Handle folder navigation (when unlocked)
  const handleFolderNavigation = useCallback((folderPath: string) => {
    if (!isPathLocked) {
      loadDirectory(folderPath);
    }
  }, [isPathLocked, loadDirectory]);

  // Get file icon based on file extension (similar to archived FileExplorer)
  const getFileIcon = useCallback((fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'js':
      case 'jsx':
      case 'ts':
      case 'tsx':
        return '📄';
      case 'json':
        return '📋';
      case 'md':
        return '📝';
      case 'css':
        return '🎨';
      case 'html':
        return '🌐';
      case 'py':
        return '🐍';
      default:
        return '📄';
    }
  }, []);

  // Render file tree with proper nesting and VS Code-like expand/collapse or navigation mode
  const renderFileTree = (nodes: FileNode[], level: number = 0) => {
    const items = [];
    
    // Add "..." (parent directory) navigation at the top level when unlocked
    if (level === 0 && !isPathLocked && currentPath !== '/') {
      items.push(
        <div key="parent-nav" className="select-none">
          <div
            className="flex items-center cursor-pointer py-1 px-2 rounded-sm group transition-colors hover:bg-opacity-50"
            style={{ 
              paddingLeft: `${level * 16 + 8}px`,
              backgroundColor: 'transparent',
              color: 'var(--icui-text-secondary)'
            }}
            onClick={navigateToParent}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--icui-bg-secondary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            <span className="text-sm font-mono mr-2" style={{ color: 'var(--icui-text-secondary)' }}>📁</span>
            <span className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>...</span>
          </div>
        </div>
      );
    }
    
    // Add regular file/folder items
    items.push(...nodes.map(node => (
      <div key={node.id} className="select-none">
        <div
          className={`flex items-center cursor-pointer py-1 px-2 rounded-sm group transition-colors`}
          style={{ 
            paddingLeft: `${level * 16 + 8}px`,
            backgroundColor: selectedFile === node.id ? 'var(--icui-bg-tertiary)' : 'transparent',
            color: 'var(--icui-text-primary)'
          }}
          onMouseEnter={(e) => {
            if (selectedFile !== node.id) {
              e.currentTarget.style.backgroundColor = 'var(--icui-bg-secondary)';
            }
          }}
          onMouseLeave={(e) => {
            if (selectedFile !== node.id) {
              e.currentTarget.style.backgroundColor = 'transparent';
            }
          }}
        >
          {node.type === 'folder' ? (
            <div 
              className="flex items-center flex-1 min-w-0"
              onClick={() => handleItemClick(node)}
            >
              {isPathLocked && (
                <>
                  {node.isExpanded ? (
                    <ChevronDown className="h-4 w-4 mr-1" style={{ color: 'var(--icui-text-secondary)' }} />
                  ) : (
                    <ChevronRight className="h-4 w-4 mr-1" style={{ color: 'var(--icui-text-secondary)' }} />
                  )}
                </>
              )}
              {isPathLocked && node.isExpanded ? (
                <FolderOpen className="h-4 w-4 mr-2" style={{ color: 'var(--icui-accent)' }} />
              ) : (
                <Folder className="h-4 w-4 mr-2" style={{ color: 'var(--icui-accent)' }} />
              )}
              <span className="text-sm truncate" style={{ color: 'var(--icui-text-primary)' }}>{node.name}</span>
            </div>
          ) : (
            <div 
              className="flex items-center flex-1 min-w-0"
              onClick={() => handleItemClick(node)}
              onDoubleClick={() => handleItemDoubleClick(node)}
            >
              <span className="mr-3 text-sm">{getFileIcon(node.name)}</span>
              <span className="text-sm truncate" style={{ color: 'var(--icui-text-primary)' }}>{node.name}</span>
            </div>
          )}
          
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ 
                  backgroundColor: 'transparent',
                  color: 'var(--icui-text-secondary)',
                  border: 'none'
                }}
              >
                <MoreVertical className="h-3 w-3" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent 
              align="end"
              style={{ 
                backgroundColor: 'var(--icui-bg-secondary)',
                borderColor: 'var(--icui-border)',
                color: 'var(--icui-text-primary)'
              }}
            >
              {node.type === 'folder' && (
                <>
                  <DropdownMenuItem 
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCreateFile();
                    }}
                    style={{ 
                      color: 'var(--icui-text-primary)',
                      backgroundColor: 'transparent'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = 'var(--icui-bg-tertiary)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                  >
                    <FileText className="h-4 w-4 mr-2" style={{ color: 'var(--icui-text-secondary)' }} />
                    New File
                  </DropdownMenuItem>
                  <DropdownMenuItem 
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCreateFolder();
                    }}
                    style={{ 
                      color: 'var(--icui-text-primary)',
                      backgroundColor: 'transparent'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = 'var(--icui-bg-tertiary)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                  >
                    <Folder className="h-4 w-4 mr-2" style={{ color: 'var(--icui-text-secondary)' }} />
                    New Folder
                  </DropdownMenuItem>
                </>
              )}
              <DropdownMenuItem 
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteItem(node);
                }}
                style={{ 
                  color: 'var(--icui-danger)',
                  backgroundColor: 'transparent'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--icui-bg-tertiary)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        
        {/* Render children if folder is expanded (only in locked mode) */}
        {isPathLocked && node.type === 'folder' && node.isExpanded && node.children && (
          <div>
            {renderFileTree(node.children, level + 1)}
          </div>
        )}
      </div>
    )));

    return items;
  };

  return (
    <div className={`icui-explorer h-full flex flex-col ${className}`} style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)' }}>
      {/* Header */}
      <div className="flex items-center justify-between p-2 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)' }}>
        <div className="flex items-center space-x-2 flex-1 min-w-0">
          {isPathLocked ? (
            <span className="text-xs px-2 py-1 rounded truncate flex-1" style={{ 
              backgroundColor: 'var(--icui-bg-tertiary)', 
              color: 'var(--icui-text-secondary)',
              border: '1px solid var(--icui-border-subtle)'
            }}>
              {currentPath}
            </span>
          ) : (
            <input
              type="text"
              value={editablePath}
              onChange={handlePathChange}
              onKeyDown={handlePathKeyPress}
              className="text-xs px-2 py-1 rounded truncate flex-1 outline-none"
              style={{ 
                backgroundColor: 'var(--icui-bg-primary)', 
                color: 'var(--icui-text-primary)',
                border: '1px solid var(--icui-accent)'
              }}
              placeholder="Enter path..."
              autoFocus
            />
          )}
        </div>
        <div className="flex items-center gap-1 ml-2">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 hover:opacity-80 transition-opacity"
            onClick={togglePathLock}
            title={isPathLocked ? "Unlock path navigation" : "Lock path and apply changes"}
            style={{ 
              backgroundColor: 'transparent',
              color: isPathLocked ? 'var(--icui-text-secondary)' : 'var(--icui-accent)',
              border: 'none'
            }}
          >
            {isPathLocked ? (
              <Lock className="h-3 w-3" />
            ) : (
              <Unlock className="h-3 w-3" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 hover:opacity-80 transition-opacity"
            onClick={handleToggleHiddenFiles}
            title={showHiddenFiles ? "Hide hidden files" : "Show hidden files (.env, .gitignore, etc.)"}
            style={{ 
              backgroundColor: 'transparent',
              color: showHiddenFiles ? 'var(--icui-accent)' : 'var(--icui-text-secondary)',
              border: 'none'
            }}
          >
            {showHiddenFiles ? (
              <Eye className="h-3 w-3" />
            ) : (
              <EyeOff className="h-3 w-3" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 hover:opacity-80 transition-opacity"
            onClick={handleRefresh}
            disabled={!isConnected || loading}
            title="Refresh"
            style={{ 
              backgroundColor: 'transparent',
              color: 'var(--icui-text-secondary)',
              border: 'none'
            }}
          >
            <RefreshCw className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {/* Connection status indicator */}
      {!isConnected && (
        <div className="px-3 py-2 text-sm border-b" style={{ 
          color: 'var(--icui-warning)', 
          backgroundColor: 'var(--icui-bg-tertiary)',
          borderBottomColor: 'var(--icui-border-subtle)'
        }}>
          Backend not connected
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="px-3 py-2 text-sm border-b" style={{ 
          color: 'var(--icui-danger)', 
          backgroundColor: 'var(--icui-bg-tertiary)',
          borderBottomColor: 'var(--icui-border-subtle)'
        }}>
          {error}
        </div>
      )}

      {/* File tree */}
      <div className="flex-1 overflow-auto p-1" style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
        {loading ? (
          <div className="p-4 text-center text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
            Loading directory contents...
          </div>
        ) : files.length === 0 ? (
          <div className="p-4 text-center text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
            {error ? 'Failed to load directory' : isConnected ? 'Directory is empty' : 'Connect to backend to view files'}
          </div>
        ) : (
          <div>
            {renderFileTree(files)}
          </div>
        )}
      </div>
    </div>
  );
};

export default ICUIExplorer;
