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
import { backendService, ICUIFileNode, useTheme } from '../../services';
import { getWorkspaceRoot } from '../../lib';
import { explorerPreferences } from '../../../lib/utils';
import { log } from '../../../services/frontend-logger';

const DEBUG_EXPLORER = import.meta.env?.VITE_DEBUG_EXPLORER === 'true';
import { Button } from '../ui/button';
import { ContextMenu, useContextMenu } from '../ui/ContextMenu';
import { globalCommandRegistry } from '../../lib/commandRegistry';
import { useExplorerMultiSelect } from '../explorer/MultiSelectHandler';
import { ICUI_FILE_LIST_MIME, isExplorerPayload, useExplorerFileDrag } from '../../lib/dnd';
import { explorerFileOperations, FileOperationContext } from '../explorer/FileOperations';
import { createExplorerContextMenu, handleExplorerContextMenuClick, ExplorerMenuContext, ExplorerMenuExtensions } from '../explorer/ExplorerContextMenu';
import { getParentDirectoryPath, isDescendantPath, joinPathSegments, normalizeDirPath } from '../explorer/pathUtils';
import { planExplorerMoveOperations } from '../explorer/movePlanner';

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
  const [files, setFiles] = useState<ICUIFileNode[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [selectedItems, setSelectedItems] = useState<ICUIFileNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  // Initialize with workspace root
  const initialWorkspaceRoot = getWorkspaceRoot();
  
  const [currentPath, setCurrentPath] = useState<string>(initialWorkspaceRoot);
  const [isPathLocked, setIsPathLocked] = useState(true);
  const [editablePath, setEditablePath] = useState<string>('');
  const [showHiddenFiles, setShowHiddenFiles] = useState(explorerPreferences.getShowHiddenFiles());
  
  const lastLoadTimeRef = useRef(0);
  const refreshTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const loadDirectoryRef = useRef<(path?: string, opts?: { force?: boolean }) => Promise<void>>();
  const statusHandlerRef = useRef<((payload: any) => Promise<void>) | null>(null);
  const expandedPathsRef = useRef<Set<string>>(new Set());
  
  // Inline rename state
  const [renamingFileId, setRenamingFileId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const renameInputRef = useRef<HTMLInputElement>(null);
  const [dragHoverId, setDragHoverId] = useState<string | null>(null);
  const [isRootDragHover, setIsRootDragHover] = useState(false);
  const dragOperationRef = useRef(false);

  const { contextMenu, showContextMenu, hideContextMenu } = useContextMenu();

  // Flatten the file tree to include all visible files (including those in expanded folders)
  const flattenedFiles = useMemo(() => {
    const result: ICUIFileNode[] = [];
    const stack: ICUIFileNode[] = [...files];
    
    while (stack.length > 0) {
      const node = stack.pop()!;
      result.push(node);
      
      if (node.type === 'folder' && node.isExpanded && node.children) {
        for (let i = node.children.length - 1; i >= 0; i--) {
          stack.push(node.children[i] as ICUIFileNode);
        }
      }
    }
    
    return result;
  }, [files]);

  // Multi-select functionality
  const {
    handleItemClick: handleMultiSelectClick,
    handleKeyboardNavigation,
    isSelected,
    getSelectionCount,
    getSelectedItems,
    getSelectedIds,
    clearSelection,
    selectAll,
  } = useExplorerMultiSelect(flattenedFiles, (selectedIds, selectedItems) => {
    setSelectedIds(selectedIds);
    setSelectedItems(selectedItems);
  });

  // Drag support (foundation – reuses current multi-selection logic)
  const { getDragProps } = useExplorerFileDrag({
    getSelection: () => selectedItems.map(f => ({ path: f.path, name: f.name, type: f.type })),
    isItemSelected: (id: string) => isSelected(id),
    toDescriptor: (node: ICUIFileNode) => ({ path: node.path, name: node.name, type: node.type })
  });

  const isInternalExplorerDrag = useCallback((event: React.DragEvent | DragEvent) => {
    const types = event.dataTransfer?.types;
    if (!types) return false;
    return Array.from(types).includes(ICUI_FILE_LIST_MIME);
  }, []);

  const clearDragHoverState = useCallback(() => {
    setDragHoverId(null);
    setIsRootDragHover(false);
  }, []);

  // Register file operations commands
  useEffect(() => {
    explorerFileOperations.registerCommands();
    
    return () => {
      explorerFileOperations.unregisterCommands();
    };
  }, []);

  

  // Check connection status using centralized service
  const checkConnection = useCallback(async () => {
    try {
      const status = await backendService.getConnectionStatus();
      const connected = status.connected;
      setIsConnected(connected);
      if (!connected) {
        setError(null); // Clear error when just disconnected, show connection status instead
      }
      return connected;
    } catch (error) {
      console.error('Connection check failed:', error);
      setIsConnected(false);
      return false;
    }
  }, []);

  // Build a map of previous nodes by path for quick lookup
  const buildNodeMapByPath = useCallback((nodes: ICUIFileNode[], map: Map<string, ICUIFileNode> = new Map()): Map<string, ICUIFileNode> => {
    for (const n of nodes) {
      map.set(n.path, n);
      if (n.children && n.children.length > 0) buildNodeMapByPath(n.children as ICUIFileNode[], map);
    }
    return map;
  }, []);

  // Annotate a tree with expansion flags from expandedPathsRef and optionally reuse previous children
  const annotateWithExpansion = useCallback((nodes: ICUIFileNode[], prevMap?: Map<string, ICUIFileNode>, preferNewChildren: boolean = false): ICUIFileNode[] => {
    const prev = prevMap || new Map<string, ICUIFileNode>();
    const annotate = (list: ICUIFileNode[]): ICUIFileNode[] =>
      list.map(node => {
        if (node.type === 'folder') {
          const shouldExpand = expandedPathsRef.current.has(node.path);
          const prevNode = prev.get(node.path);
          const rawChildren = preferNewChildren
            ? (node.children as ICUIFileNode[] | undefined)
            : ((node.children as ICUIFileNode[] | undefined) ?? (shouldExpand ? (prevNode?.children as ICUIFileNode[] | undefined) : undefined));
          const children = rawChildren ? annotate(rawChildren as ICUIFileNode[]) : rawChildren;
          return { ...node, isExpanded: shouldExpand, children } as ICUIFileNode;
        }
        return node;
      });
    return annotate(nodes);
  }, []);

  // Apply children fetch results, keeping expansion flags for nested folders
  const applyChildrenResults = useCallback((current: ICUIFileNode[], results: { path: string; children: ICUIFileNode[] }[], prevMap: Map<string, ICUIFileNode>): ICUIFileNode[] => {
    const byPath = new Map(results.map(r => [r.path, r.children] as const));
    const apply = (nodes: ICUIFileNode[]): ICUIFileNode[] =>
      nodes.map(node => {
        if (node.type === 'folder') {
          const replacedChildren = byPath.has(node.path) ? (byPath.get(node.path) as ICUIFileNode[]) : (node.children as ICUIFileNode[] | undefined);
          const annotated = replacedChildren ? annotateWithExpansion(replacedChildren, prevMap, true) : replacedChildren;
          const deepApplied = annotated ? apply(annotated) : annotated;
          return {
            ...node,
            children: deepApplied,
          } as ICUIFileNode;
        }
        return node;
      });
    return apply(current);
  }, [annotateWithExpansion]);

  // Load directory contents using centralized service
  const loadDirectory = useCallback(async (path: string = getWorkspaceRoot(), opts?: { force?: boolean }) => {
    const now = Date.now();
    if (!opts?.force && now - lastLoadTimeRef.current < 100) {
      if (DEBUG_EXPLORER) {
        console.debug('[ICUIExplorer][loadDirectory] throttled', { path, last: lastLoadTimeRef.current, now });
      }
      return;
    }
    
    if (DEBUG_EXPLORER) {
      console.debug('[ICUIExplorer][loadDirectory] start', { path, force: opts?.force });
    }
    setLoading(true);
    // Don't clear an existing error if we're still disconnected; otherwise clear so UI can update
    setError(prev => (isConnected ? null : prev));
    lastLoadTimeRef.current = now;
    
    try {
      const connected = await checkConnection();
      if (!connected) {
        if (DEBUG_EXPLORER) {
          console.debug('[ICUIExplorer][loadDirectory] abort (disconnected)', { path });
        }
        // Gracefully exit without flagging an error; connection watcher will retry refresh
        return;
      }

      const directoryContents = await backendService.getDirectoryContents(path, showHiddenFiles);
      
      setFiles(prevFiles => {
        const prevMap = buildNodeMapByPath(prevFiles);
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
            setFiles(currentFiles => applyChildrenResults(currentFiles, results, buildNodeMapByPath(currentFiles)));
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
      // Suppress transient not-connected errors (should be handled above but defensive)
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
  }, [checkConnection, showHiddenFiles, buildNodeMapByPath, annotateWithExpansion, applyChildrenResults]);

  useEffect(() => {
    loadDirectoryRef.current = loadDirectory;
  }, [loadDirectory]);

  // Connection monitoring + initial load (listener first to avoid missing early events)
  useEffect(() => {
    let mounted = true;
    if (DEBUG_EXPLORER) {
      console.debug('[ICUIExplorer][mount] effect start', { currentPath });
    }
    const handleConnectionChange = (payload: any) => {
      if (!mounted) return;
      const connected = payload.status === 'connected';
      setIsConnected(connected);
      if (DEBUG_EXPLORER) {
        console.debug('[ICUIExplorer][event] connection_status_changed', { connected });
      }
      if (connected) {
        setError(null);
        // Perform (or re-perform) directory load now that we're connected
        loadDirectoryRef.current ? loadDirectoryRef.current(currentPath, { force: true }) : loadDirectory(currentPath, { force: true });
      }
    };

    backendService.on('connection_status_changed', handleConnectionChange);

    // Kick off connection check AFTER listener is attached so we don't miss the first event
    (async () => {
      const status = await checkConnection();
      if (DEBUG_EXPLORER) {
        console.debug('[ICUIExplorer][mount] initial checkConnection result', { status });
      }
      if (status) {
        // If already connected, load immediately
        loadDirectory(currentPath, { force: true });
      } else {
        // Not yet connected: calling getConnectionStatus() again will trigger ensureInitialized -> connection attempt
        try {
          if (DEBUG_EXPLORER) {
            console.debug('[ICUIExplorer][mount] triggering second status call to start connection');
          }
          await backendService.getConnectionStatus();
        } catch {/* ignore */}
      }
    })();

    return () => {
      mounted = false;
      backendService.off('connection_status_changed', handleConnectionChange);
      if (DEBUG_EXPLORER) {
        console.debug('[ICUIExplorer][unmount] cleanup');
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPath]);

  // Real-time file system updates via WebSocket (mirror working ICUIExplorer watcher)
  useEffect(() => {
    if (!backendService) {
      return;
    }

    const handleFileSystemEvent = (eventData: any) => {
  log.debug('ICUIExplorer', '[EXPL] filesystem_event received', { event: eventData?.event, data: eventData?.data });
      if (!eventData?.data) {
        return;
      }

      const { event, data } = eventData;
      const paths = [eventData.path, data.file_path, data.path, data.dir_path, data.src_path, data.dest_path].filter(
        (p): p is string => typeof p === 'string' && p.length > 0
      );

      switch (event) {
        case 'fs.file_created':
        case 'fs.directory_created':
        case 'fs.file_deleted':
        case 'fs.file_moved':
        case 'fs.file_copied': {
          if (refreshTimeoutRef.current) {
            clearTimeout(refreshTimeoutRef.current);
          }
          // Debounce structural refreshes
          refreshTimeoutRef.current = setTimeout(() => {
            log.debug('ICUIExplorer', '[EXPL] triggering debounced refresh', { currentPath, paths });
            if (loadDirectoryRef.current) {
              loadDirectoryRef.current(currentPath);
            }
            refreshTimeoutRef.current = null;
          }, 300);
          break;
        }
        case 'fs.file_modified': {
          // Non-structural; ignore for tree refresh
          log.debug('ICUIExplorer', '[EXPL] modification event ignored for tree', { paths });
          break;
        }
        default: {
          log.debug('ICUIExplorer', '[EXPL] unknown filesystem_event', { event });
        }
      }
    };

    backendService.on('filesystem_event', handleFileSystemEvent);

    const topics = ['fs.file_created', 'fs.directory_created', 'fs.file_deleted', 'fs.file_moved', 'fs.file_copied', 'fs.file_modified'];

    const subscribeToEvents = async () => {
      try {
        const status = await backendService.getConnectionStatus();
        if (!status.connected) return;
  log.info('ICUIExplorer', '[EXPL] Subscribing to fs topics');
        await backendService.notify('subscribe', { topics });
      } catch (error) {
  log.warn('ICUIExplorer', 'Failed to subscribe to filesystem events', { error });
      }
    };

    const initConnection = async () => {
      try {
        const status = await backendService.getConnectionStatus();
        if (status.connected) {
          log.info('ICUIExplorer', '[EXPL] Initializing subscription on connected');
          await subscribeToEvents();
        } else {
          statusHandlerRef.current = async (payload: any) => {
            if (payload?.status === 'connected') {
              log.info('ICUIExplorer', '[EXPL] Connected, subscribing + refreshing');
              await subscribeToEvents();
              if (loadDirectoryRef.current) {
                loadDirectoryRef.current(currentPath);
              }
              if (statusHandlerRef.current) {
                backendService.off('connection_status_changed', statusHandlerRef.current);
                statusHandlerRef.current = null;
              }
            }
          };
          backendService.on('connection_status_changed', statusHandlerRef.current);
        }
      } catch (error) {
  console.error('[ICUIExplorer] Error initializing connection:', error);
      }
    };

    initConnection();

    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
        refreshTimeoutRef.current = null;
      }
      backendService.off('filesystem_event', handleFileSystemEvent);
      if (statusHandlerRef.current) {
        backendService.off('connection_status_changed', statusHandlerRef.current);
        statusHandlerRef.current = null;
      }
      const cleanup = async () => {
        try {
          const status = await backendService.getConnectionStatus();
          if (status.connected) {
            log.info('ICUIExplorer', '[EXPL] Unsubscribing from fs topics');
            await backendService.notify('unsubscribe', { topics });
          }
        } catch (error) {
          log.warn('ICUIExplorer', 'Failed to unsubscribe from filesystem events', { error });
        }
      };
      cleanup();
    };
  }, [currentPath]);

  // Helper function to find a node in the tree
  const findNodeInTree = useCallback((nodes: ICUIFileNode[], nodeId: string): ICUIFileNode | null => {
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
      
      const targetFolder = findNodeInTree(updatedFiles, folder.id);
      if (targetFolder && targetFolder.isExpanded && (!targetFolder.children || targetFolder.children.length === 0)) {
        (async () => {
          try {
            const children = await backendService.getDirectoryContents(folder.path, showHiddenFiles);
            
            setFiles(prevFiles => {
              const updateWithChildren = (nodes: ICUIFileNode[]): ICUIFileNode[] => {
                return nodes.map(node => {
                  if (node.id === folder.id) {
                    const prevMap = buildNodeMapByPath(prevFiles);
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
  }, [isConnected, findNodeInTree, annotateWithExpansion, buildNodeMapByPath]);

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
  const handleContextMenu = useCallback((event: React.MouseEvent, clickedFile?: ICUIFileNode) => {
    event.preventDefault();
    event.stopPropagation();

    // If right-clicked on an unselected item, select it first
    if (clickedFile && !isSelected(clickedFile.id)) {
      handleMultiSelectClick(clickedFile, { ctrlKey: false, shiftKey: false, metaKey: false });
    }

    const currentSelection = clickedFile && !isSelected(clickedFile.id) 
      ? [clickedFile] 
      : getSelectedItems();

    const menuContext: ExplorerMenuContext = {
      panelType: 'explorer',
      selectedFiles: currentSelection,
      currentPath,
      clickedFile,
      canPaste: explorerFileOperations.canPaste(),
      isMultiSelect: true,
      selectedItems: currentSelection,
      // Provide folder path for creation commands: if right-click on folder, create inside it
      targetDirectoryPath: clickedFile && clickedFile.type === 'folder' ? clickedFile.path : currentPath,
    } as any;

    const schema = createExplorerContextMenu(menuContext, extensions);
    showContextMenu(event, schema, menuContext);
  }, [isSelected, handleMultiSelectClick, getSelectedItems, currentPath, showContextMenu]);

  // Handle refresh
  const handleRefresh = useCallback(async () => {
    if (loadDirectoryRef.current) {
      await loadDirectoryRef.current(currentPath, { force: true });
    } else {
      await loadDirectory(currentPath, { force: true });
    }
  }, [currentPath, loadDirectory]);

  const handleInternalDrop = useCallback(async (event: React.DragEvent, targetNode?: ICUIFileNode | null) => {
    if (!isInternalExplorerDrag(event)) return;

    event.preventDefault();
    event.stopPropagation();

    const traceId = (event.dataTransfer as any)._icuiTraceId || `drop-${Date.now().toString(36)}`;
    try {
      log.info('ExplorerDnD', '[DND][drop:init]', {
        traceId,
        targetNode: targetNode ? { path: targetNode.path, type: targetNode.type } : null,
        currentPath,
      });
    } catch {}

    const transfer = event.dataTransfer;
    const rawPayload = transfer?.getData(ICUI_FILE_LIST_MIME);
    if (!rawPayload) {
      clearDragHoverState();
      return;
    }

    let payload: unknown;
    try {
      payload = JSON.parse(rawPayload);
    } catch (parseError) {
      console.error('ICUIEnhancedExplorer', 'Failed to parse drag payload', parseError);
      clearDragHoverState();
      return;
    }

    if (!isExplorerPayload(payload)) {
      clearDragHoverState();
      return;
    }

    const destinationDirRaw = targetNode
      ? (targetNode.type === 'folder' ? targetNode.path : getParentDirectoryPath(targetNode.path))
      : currentPath;
    const destinationDir = normalizeDirPath(destinationDirRaw);

    const descriptors = payload.items ?? payload.paths.map((path: string, index: number) => ({
      path,
      name: path.split('/').pop() || `item-${index}`,
      type: 'file' as const,
    }));

    type PlannedDescriptor = {
      sourcePath: string;
      name: string;
      type: 'file' | 'folder';
      depth: number;
    };

    let plannedOperations: { source: string; destination: string }[] = [];
    let skipped: string[] = [];
    try {
      const planning = planExplorerMoveOperations({ descriptors, destinationDir });
      plannedOperations = planning.operations;
      skipped = planning.skipped;
      log.info('ExplorerDnD', '[DND][drop:plan]', {
        traceId,
        destinationDir,
        operations: plannedOperations,
        skipped,
      });
    } catch (planError) {
      log.error('ExplorerDnD', '[DND][drop:plan:error]', { traceId, error: planError });
      setError(planError instanceof Error ? planError.message : 'Failed to plan move');
      clearDragHoverState();
      return;
    }

    if (plannedOperations.length === 0) {
      clearDragHoverState();
      return;
    }

    dragOperationRef.current = true;
    try {
      log.info('ExplorerDnD', '[DND][drop:validate:start]', { traceId, destinationDir });
      const directorySnapshot = await backendService.getDirectoryContents(destinationDir, true).catch(() => [] as ICUIFileNode[]);
      const existingNames = new Set(directorySnapshot.map(node => node.name));

      for (const op of plannedOperations) {
        const basename = op.destination.split('/').pop() || '';
        if (existingNames.has(basename)) {
          log.warn('ExplorerDnD', '[DND][drop:validate:conflict]', { traceId, basename });
          throw new Error(`Cannot move “${basename}”: destination already contains an item with the same name.`);
        }
      }

      for (const op of plannedOperations) {
        log.info('ExplorerDnD', '[DND][drop:execute]', { traceId, op });
        await backendService.moveFile(op.source, op.destination);
      }

      await handleRefresh();
      clearSelection();
      setError(null);
      log.info('ExplorerDnD', '[DND][drop:complete]', { traceId, moved: plannedOperations.length, skipped });
    } catch (error) {
      console.error('ICUIEnhancedExplorer', 'Failed to move selection', error);
      log.error('ExplorerDnD', '[DND][drop:failure]', { traceId, error });
      setError(error instanceof Error ? error.message : 'Failed to move files');
    } finally {
      dragOperationRef.current = false;
      clearDragHoverState();
    }

    if (skipped.length > 0) {
      log.warn('ICUIEnhancedExplorer', 'Skipped moving some paths due to invalid targets', { traceId, skipped });
    }
  }, [isInternalExplorerDrag, currentPath, clearDragHoverState, backendService, handleRefresh, clearSelection]);

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
        const prevMap = buildNodeMapByPath(prevFiles);
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
            setFiles(currentFiles => applyChildrenResults(currentFiles, results, buildNodeMapByPath(currentFiles)));
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
  }, [currentPath, checkConnection, buildNodeMapByPath, annotateWithExpansion, applyChildrenResults]);

  // Inline rename functions
  const startRename = useCallback((file: ICUIFileNode) => {
    setRenamingFileId(file.path);
    setRenameValue(file.name);
    // Focus the input after state update
    setTimeout(() => {
      if (renameInputRef.current) {
        renameInputRef.current.focus();
        renameInputRef.current.select();
      }
    }, 0);
  }, []);

  const cancelRename = useCallback(() => {
    setRenamingFileId(null);
    setRenameValue('');
  }, []);

  const confirmRename = useCallback(async () => {
    if (!renamingFileId || !renameValue.trim()) {
      cancelRename();
      return;
    }

    const file = flattenedFiles.find(f => f.path === renamingFileId);
    if (!file || renameValue.trim() === file.name) {
      cancelRename();
      return;
    }

    try {
      // Build destination path safely using shared path helpers
      const parentPath = getParentDirectoryPath(file.path);
      const newPath = joinPathSegments(parentPath, renameValue.trim());

      // No-op if paths are identical after normalization
      if (newPath === file.path) {
        cancelRename();
        return;
      }

      // Prefer server-side move operation to preserve metadata and handle directories atomically
      await backendService.moveFile(file.path, newPath);

      // Refresh directory and notify parent
      await loadDirectoryRef.current?.(currentPath, { force: true });
      onFileRename?.(file.path, newPath);
      
      log.info('ICUIEnhancedExplorer', 'Renamed file inline', { oldPath: file.path, newPath });
    } catch (error) {
      log.error('ICUIEnhancedExplorer', 'Failed to rename file inline', { oldPath: renamingFileId, newName: renameValue, error });
      setError(error instanceof Error ? error.message : 'Failed to rename file');
    } finally {
      cancelRename();
    }
  }, [renamingFileId, renameValue, flattenedFiles, cancelRename, currentPath, onFileRename]);

  const handleRenameKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      confirmRename();
    } else if (event.key === 'Escape') {
      event.preventDefault();
      cancelRename();
    }
  }, [confirmRename, cancelRename]);

  // Handle context menu item clicks
  const handleMenuItemClick = useCallback((item: any) => {
    const clickedFolder = selectedItems.length === 1 && selectedItems[0].type === 'folder' ? selectedItems[0] : undefined;
    const menuContext: ExplorerMenuContext = {
      panelType: 'explorer',
      selectedFiles: selectedItems,
      currentPath,
      canPaste: explorerFileOperations.canPaste(),
      isMultiSelect: true,
      selectedItems,
      targetDirectoryPath: clickedFolder ? clickedFolder.path : currentPath,
    } as any;

    handleExplorerContextMenuClick(item, menuContext, {
      selectAll,
      clearSelection,
    });

    // Handle rename command with inline editing
    if (item.commandId === 'explorer.rename' && selectedItems.length === 1) {
      startRename(selectedItems[0]);
      return;
    }

    // If it has a commandId, execute it through the command registry
    if (item.commandId) {
      globalCommandRegistry.execute(item.commandId, menuContext).catch(error => {
        console.error('Failed to execute command:', error);
        setError(error.message);
      });
    }
  }, [selectedItems, currentPath, selectAll, clearSelection, startRename]);

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

  // Get file icon based on file extension
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

  // Render file tree with multi-select support
  const renderFileTree = (nodes: ICUIFileNode[], level: number = 0) => {
    const items = [];
    
    // Add "..." (parent directory) navigation at the top level when unlocked
    if (level === 0 && !isPathLocked && currentPath !== '/') {
      const navigateToParent = () => {
        const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/';
        loadDirectory(parentPath);
      };

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
    
    // Add regular file/folder items with multi-select support + drag support
    items.push(...nodes.map(node => {
      const dragProps = getDragProps(node);
      const isDragTarget = dragHoverId === node.id;
      return (
        <div key={node.id} className="select-none" data-path={node.path} data-type={node.type}>
          <div
            className={`flex items-center cursor-pointer py-1 px-2 rounded-sm group transition-colors ${isDragTarget ? 'ring-2 ring-blue-400 ring-offset-1 ring-offset-transparent' : ''}`}
            style={{
              paddingLeft: `${level * 16 + 8}px`,
              backgroundColor: isSelected(node.id) ? 'var(--icui-bg-tertiary)' : 'transparent',
              color: 'var(--icui-text-primary)'
            }}
            {...dragProps}
            onDragOver={(e) => handleItemDragOver(e, node)}
            onDragEnter={(e) => handleItemDragOver(e, node)}
            onDragLeave={(e) => handleItemDragLeave(e, node)}
            onDrop={(e) => handleItemDrop(e, node)}
            onClick={(e) => handleItemClick(node, e)}
            onDoubleClick={(e) => handleItemDoubleClick(node, e)}
            onContextMenu={(e) => handleContextMenu(e, node)}
            onMouseEnter={(e) => {
              if (!isSelected(node.id)) {
                e.currentTarget.style.backgroundColor = 'var(--icui-bg-secondary)';
              }
            }}
            onMouseLeave={(e) => {
              if (!isSelected(node.id)) {
                e.currentTarget.style.backgroundColor = 'transparent';
              }
            }}
          >
            {node.type === 'folder' ? (
              <div className="flex items-center flex-1 min-w-0">
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
                {renamingFileId === node.path ? (
                  <input
                    ref={renameInputRef}
                    type="text"
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onKeyDown={handleRenameKeyDown}
                    onBlur={confirmRename}
                    className="text-sm bg-transparent border border-blue-500 rounded px-1 py-0 flex-1 min-w-0 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    style={{ color: 'var(--icui-text-primary)' }}
                  />
                ) : (
                  <span className="text-sm truncate" style={{ color: 'var(--icui-text-primary)' }}>{node.name}</span>
                )}
              </div>
            ) : (
              <div className="flex items-center flex-1 min-w-0">
                <span className="mr-3 text-sm">{getFileIcon(node.name)}</span>
                {renamingFileId === node.path ? (
                  <input
                    ref={renameInputRef}
                    type="text"
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onKeyDown={handleRenameKeyDown}
                    onBlur={confirmRename}
                    className="text-sm bg-transparent border border-blue-500 rounded px-1 py-0 flex-1 min-w-0 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    style={{ color: 'var(--icui-text-primary)' }}
                  />
                ) : (
                  <span className="text-sm truncate" style={{ color: 'var(--icui-text-primary)' }}>{node.name}</span>
                )}
              </div>
            )}
          </div>
          {isPathLocked && node.type === 'folder' && node.isExpanded && node.children && (
            <div>
              {renderFileTree(node.children, level + 1)}
            </div>
          )}
        </div>
      );
    }));

    return items;
  };

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
