/**
 * ICUI Explorer with Multi-Select and Context Menus
 *
 * Phase 8 features:
 * - Multi-select with Shift/Ctrl support
 * - Right-click context menus
 * - Keyboard navigation
 * - Batch file operations
 */

import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { 
  RefreshCw,
  Lock,
  Unlock,
  Eye,
  EyeOff
} from "lucide-react";
import { backendService, ICUIFileNode } from '../../services';
import { getWorkspaceRoot } from '../../lib';
import { explorerPreferences } from '../../../lib/utils';
import { log } from '../../../services/frontend-logger';

const DEBUG_EXPLORER = import.meta.env?.VITE_DEBUG_EXPLORER === 'true';
import { Button } from '../ui/button';
import { ContextMenu } from '../ui/ContextMenu';
import { globalCommandRegistry } from '../../lib/commandRegistry';
import { useExplorerMultiSelect } from '../explorer/MultiSelectHandler';
// DnD MIME helpers now handled inside hooks
import { explorerFileOperations, FileOperationContext } from '../explorer/FileOperations';
import { 
  flattenVisibleTree,
  buildNodeMapByPath as buildMapUtil,
  createAnnotateWithExpansion,
  applyChildrenResults as applyChildrenResultsUtil,
  findNodeInTree as findNodeInTreeUtil,
} from '../explorer/utils';
import { ExplorerMenuExtensions } from '../explorer/ExplorerContextMenu';
import ExplorerTree from '../explorer/ExplorerTree';
import { useExplorerConnection } from '../explorer/useExplorerConnection';
import { useExplorerFsWatcher } from '../explorer/useExplorerFsWatcher';
import { useExplorerDnD } from '../explorer/useExplorerDnD';
import { useExplorerRename } from '../explorer/useExplorerRename';
import { useExplorerContextMenu } from '../explorer/useExplorerContextMenu';
import { useExplorerDropMove } from '../explorer/useExplorerDropMove';

interface ICUIExplorerProps {
  className?: string;
  onFileSelect?: (file: ICUIFileNode) => void;
  onFileDoubleClick?: (file: ICUIFileNode) => void;
  onFileCreate?: (path: string) => void;
  onFolderCreate?: (path: string) => void;
  onFileDelete?: (path: string) => void;
  onFileRename?: (oldPath: string, newPath: string) => void;
  extensions?: ExplorerMenuExtensions;
}


const ICUIExplorer: React.FC<ICUIExplorerProps> = ({
  className = '',
  onFileSelect,
  onFileDoubleClick,
  onFileCreate,
  onFolderCreate,
  onFileDelete,
  onFileRename,
  extensions,
}) => {
  // ---------- state ----------
  const [files, setFiles] = useState<ICUIFileNode[]>([]);
  const [selectedItems, setSelectedItems] = useState<ICUIFileNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const initialWorkspaceRoot = getWorkspaceRoot();
  // Start with local namespace for initial path
  const [currentPath, setCurrentPath] = useState<string>(`local:${initialWorkspaceRoot.startsWith('/') ? '' : '/'}${initialWorkspaceRoot}`.replace('local://', 'local:/'));
  const [isPathLocked, setIsPathLocked] = useState(true);
  const [editablePath, setEditablePath] = useState<string>('');
  const [showHiddenFiles, setShowHiddenFiles] = useState(explorerPreferences.getShowHiddenFiles());

  const [dragHoverId, setDragHoverId] = useState<string | null>(null);
  const [isRootDragHover, setIsRootDragHover] = useState(false);
  // Inline rename handled via hook
  // values wired from useExplorerRename below

  // ---------- refs ----------
  const lastLoadTimeRef = useRef(0);
  const loadDirectoryRef = useRef<(path: string, opts?: { force?: boolean }) => Promise<void>>();
  const expandedPathsRef = useRef<Set<string>>(new Set());
  // Track last hop signature (context + cwd) so we refresh when either changes
  const lastHopContextIdRef = useRef<string | null>(null);
  // local drag ref no longer used; managed inside useExplorerDropMove

  // ---------- derived ----------
  const flattenedFiles = useMemo(() => flattenVisibleTree(files), [files]);

  // Multi-select
  const {
    handleItemClick: handleMultiSelectClick,
    handleKeyboardNavigation,
    isSelected,
    getSelectedItems,
    clearSelection,
    selectAll,
  } = useExplorerMultiSelect(flattenedFiles, (_ids, items) => {
    setSelectedItems(items);
  });

  // Register file operation commands on mount
  useEffect(() => {
    explorerFileOperations.registerCommands();
    return () => explorerFileOperations.unregisterCommands();
  }, []);

  // Initial hop sessions fetch so context menu has data on first open
  useEffect(() => {
    if (!backendService) return;
    try {
      // Fire and forget. Cache used by context menu builder.
      (backendService as any).listHopSessions?.().catch(() => {});
    } catch (_) {
      /* ignore */
    }
  }, [backendService]);

  // Update command context when selection or path changes
  useEffect(() => {
    const ctx: FileOperationContext = {
      selectedFiles: selectedItems,
      currentPath,
      refreshDirectory: async () => {
        if (loadDirectoryRef.current) await loadDirectoryRef.current(currentPath, { force: true });
      },
      onFileCreate,
      onFolderCreate,
      onFileDelete,
      onFileRename,
    };
    globalCommandRegistry.updateContext(ctx);
  }, [selectedItems, currentPath, onFileCreate, onFolderCreate, onFileDelete, onFileRename]);

  // Connection check
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

  // Maps/annotation helpers
  const buildMap = useCallback((nodes: ICUIFileNode[]) => buildMapUtil(nodes), []);
  const annotateWithExpansion = useMemo(() => createAnnotateWithExpansion(expandedPathsRef.current), []);
  const applyChildrenResults = useCallback(
    (current: ICUIFileNode[], results: { path: string; children: ICUIFileNode[] }[], prevMap: Map<string, ICUIFileNode>) =>
      applyChildrenResultsUtil(current, results, prevMap, annotateWithExpansion),
    [annotateWithExpansion]
  );

  // DnD helpers
  const { getDragProps, isInternalExplorerDrag } = useExplorerDnD({ selectedItems, isSelected });
  const clearDragHoverState = useCallback(() => {
    setDragHoverId(null);
    setIsRootDragHover(false);
  }, []);

  const {
    renamingFileId,
    renameValue,
    renameInputRef,
    startRename,
    cancelRename,
    confirmRename,
    handleRenameKeyDown,
    setRenameValue,
  } = useExplorerRename({
    flattenedFiles,
    loadDirectoryRef,
    currentPath,
    onFileRename,
    setError,
  });

  const {
    contextMenu,
    showContextMenu,
    hideContextMenu,
    handleContextMenu,
    handleMenuItemClick,
  } = useExplorerContextMenu({
    currentPath,
    getSelectedItems,
    isSelected,
    handleMultiSelectClick,
    extensions,
    selectAll,
    clearSelection,
    setError: (msg) => setError(msg),
    startRename,
  });

  // Load directory
  const loadDirectory = useCallback(async (path: string = getWorkspaceRoot(), opts?: { force?: boolean }) => {
    const now = Date.now();
    if (!opts?.force && now - lastLoadTimeRef.current < 100) {
      return;
    }

    setLoading(true);
    setError(null);
    lastLoadTimeRef.current = now;

    try {
      const connected = await checkConnection();
      if (!connected) {
        if (DEBUG_EXPLORER) {
          console.debug('[ICUIExplorer][loadDirectory] abort (disconnected)', { path });
        }
        return; // connection watcher will retry
      }

  const directoryContents = await backendService.getDirectoryContents(path, showHiddenFiles);

      setFiles(prevFiles => {
        const prevMap = buildMap(prevFiles);
        if (expandedPathsRef.current.size === 0) {
          const seed = (nodes: ICUIFileNode[]) => {
            for (const n of nodes) {
              if (n.type === 'folder' && n.isExpanded) {
                expandedPathsRef.current.add(n.path);
              }
              if (n.children && n.children.length) seed(n.children as ICUIFileNode[]);
            }
          };
          seed(prevFiles);
        }
        const mergedFiles = annotateWithExpansion(directoryContents as ICUIFileNode[], prevMap);

        setTimeout(async () => {
          const collectExpandedPaths = (nodes: ICUIFileNode[], acc: string[] = []): string[] => {
            for (const n of nodes) {
              if (n.type === 'folder' && expandedPathsRef.current.has(n.path)) acc.push(n.path);
              if (n.children && n.children.length) collectExpandedPaths(n.children as ICUIFileNode[], acc);
            }
            return acc;
          };
          const all = collectExpandedPaths(mergedFiles);
          const setAll = new Set(all);
          const expandedPaths = all.filter(p => {
            const parts = p.split('/').filter(Boolean);
            let cur = '';
            for (let i = 0; i < parts.length - 1; i++) {
              cur += (i === 0 ? '' : '/') + parts[i];
              if (setAll.has(cur)) return false;
            }
            return true;
          });
          if (expandedPaths.length === 0) return;
          try {
            const results = await Promise.all(
              expandedPaths.map(async (p) => ({
                path: p,
                children: await backendService.getDirectoryContents(p, showHiddenFiles),
              }))
            );
            setFiles(currentFiles => applyChildrenResults(currentFiles, results, buildMap(currentFiles)));
          } catch (err) {
            console.warn('Failed to refresh expanded folders:', err);
          }
        }, 10);

        return mergedFiles;
      });

      setCurrentPath(path);
      setEditablePath(path);
      if (DEBUG_EXPLORER) {
        console.debug('[ICUIExplorer][loadDirectory] success', { count: directoryContents.length });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      if (message.toLowerCase().includes('backend not connected')) {
        log.debug('ICUIExplorer', 'Skipping directory error due to disconnected backend');
        return;
      }
      log.error('ICUIExplorer', 'Failed to load directory', { path, error: err }, err instanceof Error ? err : undefined);
      setError(message);
      if (DEBUG_EXPLORER) {
        console.debug('[ICUIExplorer][loadDirectory] error', { message });
      }
    } finally {
      setLoading(false);
      if (DEBUG_EXPLORER) {
        console.debug('[ICUIExplorer][loadDirectory] end', { path });
      }
    }
  }, [checkConnection, showHiddenFiles, buildMap, annotateWithExpansion, applyChildrenResults]);

  useEffect(() => { loadDirectoryRef.current = loadDirectory; }, [loadDirectory]);

  useExplorerConnection({ currentPath, loadDirectory, loadDirectoryRef, checkConnection, setIsConnected });

  useExplorerFsWatcher({ currentPath, onRefresh: () => {}, loadDirectoryRef });

  // Listen for hop context switches (remote/local) and refresh explorer root accordingly
  useEffect(() => {
    const handleHopStatus = (session: any) => {
      try {
  const contextId = session?.context_id || session?.contextId || 'local';
  const friendly = session?.credentialName || session?.credential_name;
        const cwd = session?.cwd || '';
        const signature = `${contextId}:${cwd}`;
        if (lastHopContextIdRef.current === signature) return; // nothing new
        lastHopContextIdRef.current = signature;

        let targetPath: string;
        if (contextId === 'local') {
          // Always reset to workspace root when returning to local per requirement
            targetPath = `local:${getWorkspaceRoot()}`;
        } else {
          // Remote: use reported cwd; fallback to '/'
          let remotePath = cwd && typeof cwd === 'string' ? cwd.trim() : '';
          if (!remotePath) remotePath = '/';
          // NOTE: If user entered '~' or '~/': backend does not expand; potential improvement.
          // Prefer friendly namespace label (credentialName) if present
          const nsLabel = (friendly && typeof friendly === 'string') ? friendly : contextId;
          targetPath = `${nsLabel}:${remotePath}`;
        }

        if (loadDirectoryRef.current) {
          loadDirectoryRef.current(targetPath, { force: true });
        } else {
          loadDirectory(targetPath, { force: true });
        }
      } catch (e) {
        if (DEBUG_EXPLORER) console.warn('[ICUIExplorer] Failed to handle hop_status', e);
      }
    };
    (backendService as any).on?.('hop_status', handleHopStatus);
    return () => { (backendService as any).off?.('hop_status', handleHopStatus); };
  }, [loadDirectory]);

  // Toggle folder expansion (VS Code-like behavior)
  const toggleFolderExpansion = useCallback(async (folder: ICUIFileNode) => {
    if (!isConnected) return;

    setFiles(currentFiles => {
      const updateFileTree = (nodes: ICUIFileNode[]): ICUIFileNode[] => {
        return nodes.map(node => {
          if (node.id === folder.id && node.type === 'folder') {
            if (node.isExpanded) {
              expandedPathsRef.current.delete(node.path);
              for (const p of Array.from(expandedPathsRef.current)) {
                if (p.startsWith(node.path + '/')) expandedPathsRef.current.delete(p);
              }
              return { ...node, isExpanded: false };
            } else {
              expandedPathsRef.current.add(node.path);
              return { ...node, isExpanded: true };
            }
          }
          if (node.children && node.children.length > 0) {
            return { ...node, children: updateFileTree(node.children) };
          }
          return node;
        });
      };

      const updatedFiles = updateFileTree(currentFiles);
      
  const targetFolder = findNodeInTreeUtil(updatedFiles, folder.id);
      if (targetFolder && targetFolder.isExpanded && (!targetFolder.children || targetFolder.children.length === 0)) {
        (async () => {
          try {
            const children = await backendService.getDirectoryContents(folder.path, showHiddenFiles);
            
            setFiles(prevFiles => {
              const updateWithChildren = (nodes: ICUIFileNode[]): ICUIFileNode[] => {
                return nodes.map(node => {
                  if (node.id === folder.id) {
                    const prevMap = buildMap(prevFiles);
                    return { ...node, children: annotateWithExpansion(children as ICUIFileNode[], prevMap, true) };
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
  }, [isConnected, annotateWithExpansion, buildMap]);

  // Handle file/folder selection with multi-select support
  const handleItemClick = useCallback(async (item: ICUIFileNode, event: React.MouseEvent) => {
    // Handle multi-select first
    handleMultiSelectClick(item, {
      ctrlKey: event.ctrlKey,
      shiftKey: event.shiftKey,
      metaKey: event.metaKey,
    });

    // If this is not a multi-select operation, handle folder expansion/navigation
    if (!event.ctrlKey && !event.shiftKey && !event.metaKey) {
      onFileSelect?.(item);
      
      if (item.type === 'folder') {
        if (isPathLocked) {
          await toggleFolderExpansion(item);
        } else {
          loadDirectory(item.path);
        }
      }
    }
  }, [handleMultiSelectClick, onFileSelect, toggleFolderExpansion, isPathLocked, loadDirectory]);

  // Handle file double-click for permanent opening
  const handleItemDoubleClick = useCallback((item: ICUIFileNode, event: React.MouseEvent) => {
    event.stopPropagation();
    if (item.type === 'file') {
      onFileDoubleClick?.(item);
    }
  }, [onFileDoubleClick]);

  // Handle right-click context menu
  // replaced by useExplorerContextMenu

  // Handle refresh
  const handleRefresh = useCallback(async () => {
    if (loadDirectoryRef.current) {
      await loadDirectoryRef.current(currentPath, { force: true });
    } else {
      await loadDirectory(currentPath, { force: true });
    }
  }, [currentPath, loadDirectory]);

  const { handleInternalDrop } = useExplorerDropMove({
    currentPath,
    isInternalExplorerDrag,
    handleRefresh,
    clearSelection,
    setError,
    clearDragHoverState,
  });

  const handleItemDragOver = useCallback((event: React.DragEvent, node: ICUIFileNode) => {
    if (!isInternalExplorerDrag(event)) return;
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = 'move';
    setDragHoverId(node.id);
  }, [isInternalExplorerDrag]);

  const handleItemDragLeave = useCallback((event: React.DragEvent, node: ICUIFileNode) => {
    if (!isInternalExplorerDrag(event)) return;
    const related = event.relatedTarget as Node | null;
    if (related && event.currentTarget.contains(related)) {
      return;
    }
    setDragHoverId(prev => (prev === node.id ? null : prev));
  }, [isInternalExplorerDrag]);

  const handleItemDrop = useCallback(async (event: React.DragEvent, node: ICUIFileNode) => {
    if (!isInternalExplorerDrag(event)) return;
    await handleInternalDrop(event, node);
  }, [handleInternalDrop, isInternalExplorerDrag]);

  const handleRootDragOver = useCallback((event: React.DragEvent) => {
    if (!isInternalExplorerDrag(event)) return;
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = 'move';
    setIsRootDragHover(true);
    setDragHoverId(null);
  }, [isInternalExplorerDrag]);

  const handleRootDragLeave = useCallback((event: React.DragEvent) => {
    if (!isInternalExplorerDrag(event)) return;
    const related = event.relatedTarget as Node | null;
    if (related && event.currentTarget.contains(related)) {
      return;
    }
    setIsRootDragHover(false);
  }, [isInternalExplorerDrag]);

  const handleRootDrop = useCallback(async (event: React.DragEvent) => {
    if (!isInternalExplorerDrag(event)) return;
    await handleInternalDrop(event, null);
  }, [handleInternalDrop, isInternalExplorerDrag]);

  // Handle toggle hidden files with immediate refresh
  const handleToggleHiddenFiles = useCallback(async () => {
    // Read current state directly from localStorage to avoid stale closure
    const currentState = explorerPreferences.getShowHiddenFiles();
    const newState = !currentState;
    
    // Update both localStorage and state
    explorerPreferences.setShowHiddenFiles(newState);
    setShowHiddenFiles(newState);
    
    // Immediately refresh with the new state (don't wait for state update)
    try {
      setLoading(true);
      setError(null);
      
      const connected = await checkConnection();
      if (!connected) {
        throw new Error('Backend not connected');
      }

      const directoryContents = await backendService.getDirectoryContents(currentPath, newState);
      
      setFiles(prevFiles => {
        const prevMap = buildMap(prevFiles);
        const mergedFiles = annotateWithExpansion(directoryContents as ICUIFileNode[], prevMap);
        
        // Refresh expanded folders with new hidden file setting
        setTimeout(async () => {
          const expandedPaths = Array.from(expandedPathsRef.current);
          if (expandedPaths.length === 0) return;
          try {
            const results = await Promise.all(
              expandedPaths.map(async (p) => ({
                path: p,
                children: await backendService.getDirectoryContents(p, newState),
              }))
            );
            setFiles(currentFiles => applyChildrenResults(currentFiles, results, buildMap(currentFiles)));
          } catch (err) {
            console.warn('Failed to refresh expanded folders:', err);
          }
        }, 10);

        return mergedFiles;
      });
    } catch (err) {
      log.error('ICUIEnhancedExplorer', 'Failed to refresh after toggling hidden files', { path: currentPath, error: err }, err instanceof Error ? err : undefined);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [currentPath, checkConnection, buildMap, annotateWithExpansion, applyChildrenResults]);
  // Sync editable path when currentPath changes externally
  // Handle keyboard navigation
  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    switch (event.key) {
      case 'ArrowUp':
        event.preventDefault();
        handleKeyboardNavigation('up', { 
          shiftKey: event.shiftKey,
          ctrlKey: event.ctrlKey 
        });
        break;
      case 'ArrowDown':
        event.preventDefault();
        handleKeyboardNavigation('down', { 
          shiftKey: event.shiftKey,
          ctrlKey: event.ctrlKey 
        });
        break;
      case 'Home':
        event.preventDefault();
        handleKeyboardNavigation('home', { 
          shiftKey: event.shiftKey,
          ctrlKey: event.ctrlKey 
        });
        break;
      case 'End':
        event.preventDefault();
        handleKeyboardNavigation('end', { 
          shiftKey: event.shiftKey,
          ctrlKey: event.ctrlKey 
        });
        break;
      case 'a':
        if (event.ctrlKey || event.metaKey) {
          event.preventDefault();
          selectAll();
        }
        break;
      case 'Escape':
        event.preventDefault();
        clearSelection();
        break;
      case 'F2':
        event.preventDefault();
        // Rename the first selected file
        if (selectedItems.length === 1) {
          startRename(selectedItems[0]);
        }
        break;
      default:
        break;
    }
  }, [handleKeyboardNavigation, selectAll, clearSelection, selectedItems, startRename]);

  // Render file tree via extracted component
  const renderFileTree = (nodes: ICUIFileNode[]) => (
    <ExplorerTree
      nodes={nodes}
      isPathLocked={isPathLocked}
      currentPath={currentPath}
      dragHoverId={dragHoverId}
      renamingFileId={renamingFileId}
      renameValue={renameValue}
      renameInputRef={renameInputRef}
      isSelected={isSelected}
      getDragProps={getDragProps}
      handleItemDragOver={handleItemDragOver}
      handleItemDragLeave={handleItemDragLeave}
      handleItemDrop={handleItemDrop}
      handleItemClick={handleItemClick}
      handleItemDoubleClick={handleItemDoubleClick}
      handleContextMenu={handleContextMenu}
      handleRenameKeyDown={handleRenameKeyDown}
      confirmRename={confirmRename}
      setRenameValue={setRenameValue}
      loadDirectory={loadDirectory}
    />
  );

  return (
    <div 
      className={`icui-enhanced-explorer h-full flex flex-col ${className}`} 
      style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)' }}
      onKeyDown={handleKeyDown}
      onContextMenu={(e) => handleContextMenu(e)}
      tabIndex={0}
    >
      {/* Header with selection info */}
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
              onChange={(e) => setEditablePath(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  if (editablePath.trim()) {
                    loadDirectory(editablePath.trim());
                  }
                } else if (e.key === 'Escape') {
                  setEditablePath(currentPath);
                }
              }}
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
            onClick={() => setIsPathLocked(!isPathLocked)}
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
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Connection status indicator */}
            {/* Status display - show connection status OR error, not both */}
      {error ? (
        <div className="px-3 py-2 text-sm border-b" style={{ 
          color: 'var(--icui-danger)', 
          backgroundColor: 'var(--icui-bg-tertiary)',
          borderBottomColor: 'var(--icui-border-subtle)'
        }}>
          {error}
        </div>
      ) : !isConnected ? (
        <div className="px-3 py-2 text-sm border-b" style={{ 
          color: 'var(--icui-warning)', 
          backgroundColor: 'var(--icui-bg-tertiary)',
          borderBottomColor: 'var(--icui-border-subtle)'
        }}>
          Backend not connected
        </div>
      ) : null}

      {/* File tree */}
      <div
        className={`flex-1 overflow-auto p-1 ${isRootDragHover ? 'ring-2 ring-blue-400 ring-offset-2 ring-offset-transparent' : ''}`}
        data-explorer-root
        data-current-path={currentPath}
        style={{ backgroundColor: 'var(--icui-bg-primary)' }}
        onDragOver={handleRootDragOver}
        onDragEnter={handleRootDragOver}
        onDragLeave={handleRootDragLeave}
        onDrop={handleRootDrop}
      >
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

      {/* Context Menu */}
      {contextMenu && (
        <ContextMenu
          schema={contextMenu.schema}
          context={contextMenu.context}
          visible={true}
          position={contextMenu.position}
          onClose={hideContextMenu}
          onItemClick={handleMenuItemClick}
        />
      )}
    </div>
  );
};

export default ICUIExplorer;
