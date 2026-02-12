/**
 * Home (ICUI): Main application shell with header, layout, and footer.
 * - Uses ICUIBaseHeader as the single source of truth for top menus and theme switcher.
 * - Renders panels via ICUILayout (Explorer, Editor, Terminal, Chat, etc.).

 */

import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import {
  ICUIChat,
  ICUIChatHistory,
  ICUIEditor,
  ICUIExplorer,
  ICUILayout,
  ICUIPanelSelector,
  ICUITerminal,
  ICUIGitConnect,
  ICUIGit,
  ICUIPreview,
  ICUIHop,
  ICUIPanelArea,
  ICUIBasePanel,
  ICUILayoutPresetSelector,
  ICUIBaseHeader,
  ICUIBaseFooter,
} from '../icui/components';
import type { ICUIEditorRef } from '../icui/components/panels/ICUIEditor';
import type { ICUIPreviewRef } from '../icui/components/panels/ICUIPreview';
import { layoutConfigService } from '../icui/services/layoutConfigService';
import { useICUIResponsive } from '../icui/hooks/icui-use-responsive';
import { SaveLayoutDialog } from '../icui/components/dialogs/SaveLayoutDialog';
import { LoadLayoutDialog } from '../icui/components/dialogs/LoadLayoutDialog';
import { MobileLayoutSettingsDialog, type MobilePanelConfig } from '../icui/components/dialogs/MobileLayoutSettingsDialog';
import { ResetLayoutDialog } from '../icui/components/dialogs/ResetLayoutDialog';
import { layoutEventBus } from '../icui/services/layoutEventBus';
import { icuiBackendService } from '../icui/services/backend-service-impl';

import type { ICUILayoutConfig } from '../icui/components/ICUILayout';
import type { ICUIPanel } from '../icui/components/ICUIPanelArea';
import type { ICUIPanelType } from '../icui/components/ICUIPanelSelector';

// Editor file interface (compatible with ICUIEditor)
interface EditorFile {
  id: string;
  name: string;
  language: string;
  content: string;
  modified: boolean;
  path?: string;
}

interface HomeProps {
  className?: string;
}

// Available theme options
const THEME_OPTIONS = [
  { id: 'github-dark', name: 'GitHub Dark', class: 'icui-theme-github-dark' },
  { id: 'monokai', name: 'Monokai', class: 'icui-theme-monokai' },
  { id: 'one-dark', name: 'One Dark', class: 'icui-theme-one-dark' },
  { id: 'github-light', name: 'GitHub Light', class: 'icui-theme-github-light' },
  { id: 'vscode-light', name: 'VS Code Light', class: 'icui-theme-vscode-light' },
];

// Remove default files - let ICUIEditor handle file loading from backend

// Layout version - increment this when you want to force a layout reset
const LAYOUT_VERSION = 2;

// Default layout configuration
const defaultLayout: ICUILayoutConfig = {
  layoutMode: 'h-layout',
  areas: {
    left: { id: 'left', name: 'Explorer', panelIds: ['explorer', 'git'], activePanelId: 'explorer', size: 20, visible: true },
    center: { id: 'center', name: 'Editor', panelIds: ['editor', 'preview', 'hop', 'chat-history'], activePanelId: 'editor', size: 40 },
    right: { id: 'right', name: 'Assistant', panelIds: ['chat'], activePanelId: 'chat', size: 40, visible: true },
    bottom: { id: 'bottom', name: 'Terminal', panelIds: ['terminal'], activePanelId: 'terminal', size: 40 },
  },
  splitConfig: { 
    mainHorizontalSplit: 20, 
    // In h-layout, `rightVerticalSplit` is the % width of the center area within the (center+right) region.
    // Setting it to 50 makes the right sidebar ~50% by default.
    rightVerticalSplit: 50, 
    // In h-layout, `centerVerticalSplit` is the % height of the top (editor) region.
    // Increase this to move the divider down (more editor space).
    centerVerticalSplit: 70 
  }
};

const Home: React.FC<HomeProps> = ({ className = '' }) => {
  // Get workspace root from environment - this will sync all panels to the same root directory
  const workspaceRoot = (import.meta as any).env?.VITE_WORKSPACE_ROOT as string | undefined;
  // UI state - keeping it simple for now, ready for backend integration later
  const [layout, setLayout] = useState<ICUILayoutConfig>(defaultLayout);
  // Remove local file management - let ICUIEditor handle its own files
  const [currentTheme, setCurrentTheme] = useState<string>('github-dark');
  const [panels, setPanels] = useState<ICUIPanel[]>([]);
  
  // Dialog state for Phase 2
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [loadDialogOpen, setLoadDialogOpen] = useState(false);
  const [mobileSettingsOpen, setMobileSettingsOpen] = useState(false);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [currentLayoutId, setCurrentLayoutId] = useState<string>('H');
  
    const getLayoutFileBaseFromPath = useCallback((path: string): string | null => {
      const fileName = path.split('/').pop();
      if (!fileName) return null;
      return fileName.replace(/\.ya?ml$/i, '');
    }, []);
  
  // Responsive detection for mobile layout
  const responsive = useICUIResponsive();
  const isMobile = responsive.viewport.isMobile;

  // Real connection status from ICUIEditor
  const [editorConnectionStatus, setEditorConnectionStatus] = useState<{connected: boolean; error?: string; timestamp?: number}>({ connected: false });
  const isConnected = editorConnectionStatus.connected;
  const connectionStatus: 'connected' | 'disconnected' | 'connecting' | 'error' = 
    editorConnectionStatus.connected ? 'connected' : 
    editorConnectionStatus.error ? 'error' : 'disconnected';

  // Editor ref for imperative control (e.g., opening files from Explorer)
  const editorRef = useRef<ICUIEditorRef>(null);
  
  // Preview ref for imperative control (e.g., previewing HTML files from Explorer)
  const previewRef = useRef<ICUIPreviewRef>(null);

  // Menu state for integrated menus
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const [currentFile, setCurrentFile] = useState<any>(null);
  // Git repo gating removed; ICUIGit handles its own connect logic

  // Handle HTML file preview from Explorer context menu
  const handlePreviewFile = useCallback(async (filePath: string) => {
    try {
      if (!previewRef.current) {
        // Wait briefly for component to mount
        await new Promise(resolve => setTimeout(resolve, 100));
        if (!previewRef.current) {
          return;
        }
      }

      // Read file content
      const nsMatch = filePath.match(/^([^:]+):\/(.*)$/);
      const nsParam = nsMatch ? `&namespace=${encodeURIComponent(nsMatch[1])}` : '';
      const rawPath = nsMatch ? `/${nsMatch[2]}` : filePath;
      const response = await fetch(`/api/files/content?path=${encodeURIComponent(rawPath)}${nsParam}`);
      if (!response.ok) {
        throw new Error(`Failed to read file: ${response.statusText}`);
      }
      
      const result = await response.json();
      const content = result.data.content;
      const fileName = filePath.split('/').pop() || 'file.html';

      // Include local dependencies (CSS/JS/images) for HTML files
      let filesMap: Record<string, string> = { [fileName]: content };

      try {
        if (/\.html?$/i.test(fileName)) {
          const dirPath = filePath.slice(0, Math.max(0, filePath.lastIndexOf('/')));
          const parser = new DOMParser();
          const doc = parser.parseFromString(content, 'text/html');

          const collectAttr = (selector: string, attr: string) =>
            Array.from(doc.querySelectorAll(selector))
              .map((el) => (el as Element).getAttribute(attr) || '')
              .filter((v) => v && !v.startsWith('http://') && !v.startsWith('https://') && !v.startsWith('//') && !v.startsWith('data:'));

          const cssHrefs = collectAttr('link[rel="stylesheet"][href]', 'href');
          const jsSrcs = collectAttr('script[src]', 'src');
          const imgSrcs = collectAttr('img[src]', 'src');
          const assetPaths = Array.from(new Set([...cssHrefs, ...jsSrcs, ...imgSrcs]));

          const toAbs = (relPath: string) => {
            try {
              const base = 'file://' + dirPath.replace(/\\/g, '/') + '/';
              return new URL(relPath, base).pathname;
            } catch {
              return null;
            }
          };

          await Promise.all(
            assetPaths.map(async (rel) => {
              const abs = toAbs(rel);
              if (!abs) return;
              try {
                const resp = await fetch(`/api/files/content?path=${encodeURIComponent(abs)}${nsParam}`);
                if (!resp.ok) return;
                const data = await resp.json();
                const key = rel.replace(/^\.\//, '');
                filesMap[key] = data.data.content as string;
              } catch {
                // Silently skip missing assets
              }
            })
          );
        }
      } catch (depErr) {
        // Non-fatal: proceed with base HTML if dependency parsing fails
        if (process.env.NODE_ENV === 'development') {
          console.warn('[Home] Dependency collection failed for preview:', depErr);
        }
      }
      
      // Create a preview with the file content
      await previewRef.current.createPreview(filesMap);
      
      if (process.env.NODE_ENV === 'development') {
        console.log('[Home] Preview created successfully for:', fileName);
      }
    } catch (error) {
      console.error('[Home] Error previewing file:', error);
    }
  }, []);

  // Handle file selection from Explorer - VS Code-like temporary file opening
  const handleFileSelect = useCallback((file: any) => {
    if (file.type !== 'file') return;

    // Track current file for status bar, even if editor isn't mounted (mobile).
    setCurrentFile(file);

    // Single click opens file temporarily (will be replaced by next single click)
    if (editorRef.current) {
      editorRef.current.openFileTemporary(file.path);
      return;
    }

    // Mobile layout often unmounts the editor when not active.
    // Persist the intent so the editor can open it when it mounts.
    try {
      sessionStorage.setItem(
        'icui-pending-open-file',
        JSON.stringify({ path: file.path, mode: 'temporary', ts: Date.now() })
      );
    } catch {
      // ignore
    }
  }, []);

  // Handle file double-click from Explorer - VS Code-like permanent file opening
  const handleFileDoubleClick = useCallback((file: any) => {
    if (process.env.NODE_ENV === 'development') {
      console.log('[Home] handleFileDoubleClick called with file:', file.name, 'at path:', file.path);
    }

    if (file.type !== 'file') return;

    setCurrentFile(file);

    // Double click opens file permanently (will not be replaced by single clicks)
    if (editorRef.current) {
      editorRef.current.openFilePermanent(file.path);
      return;
    }

    try {
      sessionStorage.setItem(
        'icui-pending-open-file',
        JSON.stringify({ path: file.path, mode: 'permanent', ts: Date.now() })
      );
    } catch {
      // ignore
    }

    console.warn('[Home] Editor not mounted; queued file open for when editor tab is activated');
  }, []);

  const handleTogglePanel = useCallback((panelType: string) => {
    setPanels(prev => {
      const panelExists = prev.some(p => p.type === panelType);
      if (panelExists) {
        // Remove panel
        return prev.filter(p => p.type !== panelType);
      } else {
        // Add panel - create a basic panel structure
        const newPanel: ICUIPanel = {
          id: `${panelType.toLowerCase()}-${Date.now()}`,
          type: panelType,
          title: panelType,
          content: <div>Panel content for {panelType}</div>,
          closable: true,
          resizable: true,
          config: {}
        };
        return [...prev, newPanel];
      }
    });
  }, []);

  // Menu action handlers for integrated menu bar
  const handleMenuItemClick = useCallback((menuId: string, itemId: string) => {
    switch (menuId) {
      case 'file':
        switch (itemId) {
          case 'new':
            // Trigger file creation through callback
            break;
          case 'open':
            // Trigger file open dialog
            break;
          case 'save':
            // Trigger save current file
            break;
          case 'save-all':
            // Trigger save all files
            break;
          case 'refresh':
            // Trigger explorer refresh through layout change
            setLayout(prev => ({
              ...prev,
              areas: {
                ...prev.areas,
                left: {
                  ...prev.areas.left,
                  refreshTrigger: Date.now()
                }
              }
            }));
            break;
        }
        break;
      case 'layout':
        switch (itemId) {
          case 'h-layout':
            layoutEventBus.emitLayoutSwitch('H');
            break;
          case 'ide-layout':
            layoutEventBus.emitLayoutSwitch('IDE');
            break;
          case 'mobile-layout':
            layoutEventBus.emitLayoutSwitch('mobile');
            break;
          case 'save-custom':
            setSaveDialogOpen(true);
            break;
          case 'load-custom':
            setLoadDialogOpen(true);
            break;
          case 'mobile-settings':
            setMobileSettingsOpen(true);
            break;
          case 'reset-layout':
            setResetDialogOpen(true);
            break;
          case 'toggle-explorer':
            handleTogglePanel('Explorer');
            break;
          case 'toggle-terminal':
            handleTogglePanel('Terminal');
            break;
          case 'toggle-search':
            handleTogglePanel('Search');
            break;
          case 'toggle-debug':
            handleTogglePanel('Debug');
            break;
        }
        break;
    }
  }, [handleTogglePanel, setLayout]);

  // Handle layout reset with factory defaults
  const handleResetLayout = useCallback(async () => {
    try {
      // Load the factory default H.yaml layout
      const result = await layoutConfigService.loadBuiltinLayout('H');
      if (result.ok && result.layout) {
        setLayout(result.layout);
        setCurrentLayoutId('H');
        localStorage.removeItem(`icotes-v${LAYOUT_VERSION}`);
        localStorage.setItem('icui-last-layout-file', 'H');
        localStorage.setItem('icui-last-layout-id', 'H');
      } else {
        console.error('Failed to load H.yaml:', result.errors);
        // Fallback to hardcoded default
        setLayout(defaultLayout);
      }
    } catch (error) {
      console.error('Error resetting layout:', error);
      setLayout(defaultLayout);
    }
  }, []);

  // Apply theme classes to document element for proper theme detection
  useEffect(() => {
    const htmlElement = document.documentElement;

    // Remove any previously applied theme classes
    THEME_OPTIONS.forEach((theme) => {
      htmlElement.classList.remove(theme.class);
    });

    // Add the new theme class
    const themeClass = THEME_OPTIONS.find((t) => t.id === currentTheme)?.class;
    if (themeClass) {
      htmlElement.classList.add(themeClass);
    }

    // Toggle the dark class for Tailwind utilities
    if (currentTheme.includes('dark')) {
      htmlElement.classList.add('dark');
    } else {
      htmlElement.classList.remove('dark');
    }

    // Cleanup on component unmount
    return () => {
      THEME_OPTIONS.forEach((theme) => {
        htmlElement.classList.remove(theme.class);
      });
      htmlElement.classList.remove('dark');
    };
  }, [currentTheme]);

  // Note: explorer.preview command is now registered in ExplorerFileOperations
  // (removed duplicate registration to avoid conflicts)

  // Handle icui:openFile event from chat thumbnails
  useEffect(() => {
    const handleOpenFile = (e: any) => {
      const path = e?.detail?.path;
      if (typeof path === 'string' && editorRef.current) {
        editorRef.current.openFilePermanent(path);
      }
    };
    window.addEventListener('icui:openFile', handleOpenFile as any);
    return () => {
      window.removeEventListener('icui:openFile', handleOpenFile as any);
    };
  }, []);

  // Initialize Explorer file operations
  useEffect(() => {
    import('../icui/components/explorer/FileOperations').then(({ ExplorerFileOperations }) => {
      const fileOps = ExplorerFileOperations.getInstance();
      fileOps.registerCommands();
    }).catch(err => {
      console.error('Failed to initialize Explorer file operations:', err);
    });
  }, []);
  
  // Subscribe to layout event bus (Phase 3)
  useEffect(() => {
    const handleLayoutSwitch = async (layoutId: string) => {
      try {
        const filePath = `${layoutConfigService.layoutDir}/${layoutId}.yaml`;
        const result = await layoutConfigService.loadFromFile(filePath);
        if (result.ok && result.layout) {
          setLayout(result.layout);
          setCurrentLayoutId(layoutId);
        }
      } catch (error) {
        console.error('Failed to switch layout:', error);
      }
    };
    
    const handlePanelActivate = ({ areaId, panelId }: { areaId: string; panelId: string }) => {
      setLayout(prev => ({
        ...prev,
        areas: {
          ...prev.areas,
          [areaId]: {
            ...prev.areas[areaId],
            activePanelId: panelId,
          }
        }
      }));
    };
    
    const handleAreaToggle = ({ areaId, visible }: { areaId: string; visible: boolean }) => {
      setLayout(prev => ({
        ...prev,
        areas: {
          ...prev.areas,
          [areaId]: {
            ...prev.areas[areaId],
            visible,
          }
        }
      }));
    };
    
    const handleSplitUpdate = ({ splitKey, percentage }: { splitKey: string; percentage: number }) => {
      setLayout(prev => ({
        ...prev,
        splitConfig: {
          ...prev.splitConfig,
          [splitKey]: percentage,
        }
      }));
    };

    const handleAreaResize = ({ areaId, size }: { areaId: string; size: number }) => {
      setLayout(prev => {
        const area = prev.areas?.[areaId];
        if (!area) return prev;
        return {
          ...prev,
          areas: {
            ...prev.areas,
            [areaId]: {
              ...area,
              size,
            }
          }
        };
      });
    };

    const handlePanelAddEvent = ({ panelType, areaId, index }: { panelType: string; areaId: string; index?: number }) => {
      // Minimal implementation: move an existing base panel (id === panelType) into the target area.
      // If we don't already have a panel instance for that id, we can't safely materialize content here.
      setLayout(prev => {
        const targetArea = prev.areas?.[areaId];
        if (!targetArea) return prev;

        const panelId = panelType;
        const nextAreas: Record<string, any> = { ...prev.areas };

        // Remove from all areas first (avoid duplicates)
        for (const [aid, a] of Object.entries(nextAreas)) {
          if (!a?.panelIds) continue;
          if (a.panelIds.includes(panelId)) {
            const filtered = a.panelIds.filter((pid: string) => pid !== panelId);
            nextAreas[aid] = {
              ...a,
              panelIds: filtered,
              activePanelId: a.activePanelId === panelId ? (filtered[0] ?? a.activePanelId) : a.activePanelId,
            };
          }
        }

        const targetPanelIds = nextAreas[areaId]?.panelIds ? [...nextAreas[areaId].panelIds] : [];
        if (!targetPanelIds.includes(panelId)) {
          if (typeof index === 'number' && index >= 0 && index <= targetPanelIds.length) {
            targetPanelIds.splice(index, 0, panelId);
          } else {
            targetPanelIds.push(panelId);
          }
        }

        nextAreas[areaId] = {
          ...nextAreas[areaId],
          panelIds: targetPanelIds,
          activePanelId: panelId,
          // If the target area is currently hidden, make it visible when adding a panel.
          ...(Object.prototype.hasOwnProperty.call(nextAreas[areaId], 'visible') ? { visible: true } : {}),
        };

        return {
          ...prev,
          areas: nextAreas,
        };
      });
    };

    const handlePanelRemoveEvent = ({ panelId }: { panelId: string }) => {
      setLayout(prev => {
        const nextAreas: Record<string, any> = { ...prev.areas };
        for (const [aid, a] of Object.entries(nextAreas)) {
          if (!a?.panelIds) continue;
          if (a.panelIds.includes(panelId)) {
            const filtered = a.panelIds.filter((pid: string) => pid !== panelId);
            nextAreas[aid] = {
              ...a,
              panelIds: filtered,
              activePanelId: a.activePanelId === panelId ? (filtered[0] ?? a.activePanelId) : a.activePanelId,
            };
          }
        }
        return { ...prev, areas: nextAreas };
      });

      // If this was a dynamically-created panel, also remove the instance.
      const builtInIds = new Set(['explorer', 'git', 'editor', 'preview', 'hop', 'terminal', 'chat', 'chat-history']);
      if (!builtInIds.has(panelId)) {
        setPanels(prev => prev.filter(p => p.id !== panelId));
      }
    };
    
    layoutEventBus.on('layout:switch', handleLayoutSwitch);
    layoutEventBus.on('layout:panel:activate', handlePanelActivate);
    layoutEventBus.on('layout:area:toggle', handleAreaToggle);
    layoutEventBus.on('layout:split:update', handleSplitUpdate);
    layoutEventBus.on('layout:area:resize', handleAreaResize);
    layoutEventBus.on('layout:panel:add', handlePanelAddEvent);
    layoutEventBus.on('layout:panel:remove', handlePanelRemoveEvent);
    
    return () => {
      layoutEventBus.off('layout:switch', handleLayoutSwitch);
      layoutEventBus.off('layout:panel:activate', handlePanelActivate);
      layoutEventBus.off('layout:area:toggle', handleAreaToggle);
      layoutEventBus.off('layout:split:update', handleSplitUpdate);
      layoutEventBus.off('layout:area:resize', handleAreaResize);
      layoutEventBus.off('layout:panel:add', handlePanelAddEvent);
      layoutEventBus.off('layout:panel:remove', handlePanelRemoveEvent);
    };
  }, []);

  // Bridge backend WebSocket layout events to layoutEventBus (Phase 3 - Agent Control)
  useEffect(() => {
    const handleBackendLayoutEvent = ({ action, data }: { action: string; data: any }) => {
      switch (action) {
        case 'switch':
          layoutEventBus.emitLayoutSwitch(data.name);
          break;
        case 'activate_panel':
          layoutEventBus.emitPanelActivate(data.areaId, data.panelId);
          break;
        case 'toggle_area':
          layoutEventBus.emitAreaToggle(data.areaId, data.visible);
          break;
        case 'resize_area':
          layoutEventBus.emitAreaResize(data.areaId, data.size);
          break;
        case 'add_panel':
          // Agent debug sidecar disabled for now
          if (data?.panelType === 'agent-debug') break;
          layoutEventBus.emitPanelAdd(data.panelType, data.areaId);
          break;
        case 'remove_panel':
          layoutEventBus.emitPanelRemove(data.panelId);
          break;
        case 'set_split':
          layoutEventBus.emitSplitUpdate(data.splitKey, data.percentage);
          break;
        default:
          console.warn('[Home] Unknown layout action from backend:', action);
      }
    };

    icuiBackendService.on('layout_event', handleBackendLayoutEvent);
    
    return () => {
      icuiBackendService.off('layout_event', handleBackendLayoutEvent);
    };
  }, []);

  // Handle connection status changes from ICUIEditor
  const handleConnectionStatusChange = useCallback((status: {connected: boolean; error?: string; timestamp?: number}) => {
    // Reduced debug: Only log connection errors, not routine status changes
    if (status.error && process.env.NODE_ENV === 'development') {
      console.log('Home received connection error:', status.error);
    }
    setEditorConnectionStatus(status);
  }, []);

  // Reduced debug: Only log connection status in development mode
  useEffect(() => {
    if (process.env.NODE_ENV === 'development' && editorConnectionStatus.error) {
      console.log('Connection error:', editorConnectionStatus.error);
    }
  }, [editorConnectionStatus]);

  // Remove local file management handlers - let ICUIEditor handle its own files
  // These are kept for potential future use but do nothing now

  // Available panel types for the selector
  const availablePanelTypes: ICUIPanelType[] = [
    { id: 'explorer', name: 'Explorer', icon: '📁', description: 'File and folder browser' },
    { id: 'editor', name: 'Code Editor', icon: '📝', description: 'Code editor with syntax highlighting' },
    { id: 'terminal', name: 'Terminal', icon: '💻', description: 'Integrated terminal' },
    { id: 'chat', name: 'Chat', icon: '🤖', description: 'AI-powered code assistant' },
    { id: 'chat-history', name: 'Chat History', icon: '💬', description: 'Manage chat sessions and history' },
    { id: 'git', name: 'Source Control', icon: '🌿', description: 'Git source control management' },
    { id: 'preview', name: 'Live Preview', icon: '🖥️', description: 'Live preview for web applications' },
    { id: 'hop', name: 'Hop', icon: '📡', description: 'SSH Hop controller' },
  ];

  // Stable panel instances to prevent recreation on layout changes
  const explorerInstance = useMemo(() => (
    <ICUIExplorer 
      onFileSelect={handleFileSelect}
      onFileDoubleClick={handleFileDoubleClick}
    />
  ), [handleFileSelect, handleFileDoubleClick]);

  const editorInstance = useMemo(() => (
    <ICUIEditor
      ref={editorRef}
      autoSave={true}
      autoSaveDelay={1500}
      workspaceRoot={workspaceRoot}
      onConnectionStatusChange={handleConnectionStatusChange}
      className="h-full"
    />
  ), [workspaceRoot, handleConnectionStatusChange]);

  const terminalInstance = useMemo(() => (
    <ICUITerminal 
      className="h-full"
    />
  ), []);

  const gitInstance = useMemo(() => (
    <ICUIGit 
      className="h-full"
      onFileSelect={handleFileSelect}
      onFileOpen={handleFileDoubleClick}
      onOpenDiffPatch={(path) => {
        if (process.env.NODE_ENV === 'development') {
          console.log('[Home] onOpenDiffPatch called, editorRef.current:', !!editorRef.current);
        }
        if (editorRef.current?.openDiffPatch) {
          editorRef.current.openDiffPatch(path);
        } else {
          console.warn('[Home] Editor ref or openDiffPatch method not available');
        }
      }}
    />
  ), [handleFileSelect, handleFileDoubleClick]);

  const previewInstance = useMemo(() => (
    <ICUIPreview
      ref={previewRef}
      className="h-full"
      autoRefresh={true}
      refreshDelay={1000}
    />
  ), []);

  const createExplorerContent = useCallback(() => explorerInstance, [explorerInstance]);
  const createEditorContent = useCallback(() => editorInstance, [editorInstance]);
  const createTerminalContent = useCallback(() => terminalInstance, [terminalInstance]);
  // Create unique Chat instances for each panel to avoid connection conflicts
  const createChatContent = useCallback(() => (
    <ICUIChat 
      className="h-full" 
      key={`chat-${Date.now()}-${Math.random()}`}
    />
  ), []);
  // Create unique Chat History instances for each panel
  const createChatHistoryContent = useCallback(() => (
    <ICUIChatHistory 
      className="h-full" 
      key={`chat-history-${Date.now()}-${Math.random()}`}
    />
  ), []);
  const createGitContent = useCallback(() => {
    // Always show main Git panel (connect disabled)
    return gitInstance;
  }, [gitInstance]);
  const hopInstance = useMemo(() => (<ICUIHop />), []);
  const createPreviewContent = useCallback(() => previewInstance, [previewInstance]);

  // Handle panel addition
  const handlePanelAdd = useCallback((panelType: ICUIPanelType, areaId: string) => {
    // Generate unique ID for the new panel - create truly unique IDs for all panels
    const newPanelId = `${panelType.id}-${Date.now()}-${Math.random().toString(36).substring(2)}`;
    
    // Create panel content based on type using memoized creators
    let content: React.ReactNode;
    switch (panelType.id) {
      case 'explorer':
        content = createExplorerContent();
        break;
      case 'editor':
        content = createEditorContent();
        break;
      case 'terminal':
        content = createTerminalContent();
        break;
      case 'chat':
        content = createChatContent();
        break;
      case 'chat-history':
        content = createChatHistoryContent();
        break;
      case 'git':
        content = createGitContent();
        break;
      case 'preview':
        content = createPreviewContent();
        break;
      case 'hop':
        content = hopInstance;
        break;
      default:
        content = <div className="h-full p-4" style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)' }}>Custom Panel: {panelType.name}</div>;
    }
    
    // Create new panel
    const newPanel: ICUIPanel = {
      id: newPanelId,
      type: panelType.id,
      title: panelType.name,
      icon: panelType.icon,
      closable: true,
      content
    };
    
    // Add panel to state
    setPanels(prev => [...prev, newPanel]);
    
    // Update layout to include the new panel in the specified area
    setLayout(prev => ({
      ...prev,
      areas: {
        ...prev.areas,
        [areaId]: {
          ...prev.areas[areaId],
          panelIds: [...prev.areas[areaId].panelIds, newPanelId],
          activePanelId: newPanelId
        }
      }
    }));
  }, [createExplorerContent, createEditorContent, createTerminalContent, createChatContent, createGitContent]);

  // Initialize panels on mount (run once)
  useEffect(() => {
    // Phase 4/5: Load initial layout based on device type and last-used preference
    const loadInitialLayout = async () => {
      try {
        // Phase 4/5: Device-aware layout loading with auto-healing
        const resolveMobilePanelIds = async (): Promise<string[]> => {
          // Prefer mobile_settings.yaml enabled+order.
          try {
            const settingsPath = `${layoutConfigService.layoutDir}/mobile_settings.yaml`;
            const settingsResult = await layoutConfigService.loadFromFile(settingsPath);
            const panels = settingsResult.ok && settingsResult.layout ? (settingsResult.layout.panels || []) : [];
            if (Array.isArray(panels) && panels.length > 0) {
              const enabledIds = panels
                .filter((p: any) => (p?.enabled ?? p?.config?.enabled) === true)
                .map((p: any) => p.id)
                .filter((id: any) => typeof id === 'string');
              if (enabledIds.length > 0) return enabledIds;
            }
          } catch {
            // ignore
          }

          // Fall back to defaults.
          return ['editor', 'preview', 'hop', 'chat-history'];
        };
        
        // 1. Check device type
        if (isMobile) {
          const mobilePath = `${layoutConfigService.layoutDir}/mobile.yaml`;
          const result = await layoutConfigService.loadFromFile(mobilePath);
          if (result.ok && result.layout) {
            const mobileArea = result.layout.areas?.main || result.layout.areas?.center;
            const panelIds = mobileArea?.panelIds || [];
            if (panelIds.length === 0) {
              // Auto-heal: empty mobile.yaml from user edit/corruption
              const repairedPanelIds = await resolveMobilePanelIds();
              const repairedLayout: ICUILayoutConfig = {
                name: 'Mobile',
                id: 'mobile',
                version: 1,
                deviceTarget: 'mobile',
                layoutMode: 'mobile',
                areas: {
                  main: {
                    id: 'main',
                    name: 'Main',
                    panelIds: repairedPanelIds,
                    activePanelId: repairedPanelIds[0],
                    size: 100,
                    visible: true,
                  },
                },
                splitConfig: {},
              };
              setLayout(repairedLayout);
              setCurrentLayoutId('mobile');
              try {
                await layoutConfigService.saveToFile(repairedLayout, mobilePath);
              } catch (e) {
                console.warn('Failed to persist repaired mobile layout:', e);
              }
              return;
            }
            setLayout(result.layout);
            setCurrentLayoutId('mobile');
            return;
          } else {
            console.warn('Failed to load mobile layout:', result.errors);
          }
        }
        
        // 2. Check localStorage for last-used layout (prefer filename base)
        const lastUsedRaw = localStorage.getItem('icui-last-layout-file') || localStorage.getItem('icui-last-layout-id');
        const mapLegacyToFileBase = (value: string) => {
          if (value === 'default-h') return 'H';
          if (value === 'default-ide') return 'IDE';
          if (value === 'mobile') return 'mobile';
          return value;
        };

        if (lastUsedRaw) {
          const lastUsedFileBase = mapLegacyToFileBase(lastUsedRaw);
          try {
            const result = await layoutConfigService.loadFromFile(`${layoutConfigService.layoutDir}/${lastUsedFileBase}.yaml`);
            if (result.ok && result.layout) {
              setLayout(result.layout);
              setCurrentLayoutId(lastUsedFileBase);
              localStorage.setItem('icui-last-layout-file', lastUsedFileBase);
              localStorage.setItem('icui-last-layout-id', lastUsedFileBase);
              return;
            }
          } catch {
            // Fall through to default
          }
        }
        
        // 3. Fallback to default H layout
        const result = await layoutConfigService.loadFromFile(`${layoutConfigService.layoutDir}/H.yaml`);
        if (result.ok && result.layout) {
          setLayout(result.layout);
          setCurrentLayoutId('H');
          localStorage.setItem('icui-last-layout-file', 'H');
          localStorage.setItem('icui-last-layout-id', 'H');
        }
      } catch (error) {
        console.warn('Failed to load YAML layout, using hardcoded default:', error);
        // Final fallback: use hardcoded defaultLayout
      }
    };
    
    loadInitialLayout();
    
    const initialPanels: ICUIPanel[] = [
      {
        id: 'explorer',
        type: 'explorer',
        title: 'Explorer',
        icon: '📁',
        closable: true,
        content: createExplorerContent()
      },
      {
        id: 'git',
        type: 'git', 
        title: 'Source Control',
        icon: '🌿',
        closable: true,
        content: createGitContent()
      },
      {
        id: 'editor',
        type: 'editor',
        title: 'Editor',
        icon: '📝',
        closable: true,
        content: createEditorContent()
      },
      {
        id: 'preview',
        type: 'preview',
        title: 'Live Preview',
        icon: '🖥️',
        closable: true,
        content: createPreviewContent()
      },
      {
        id: 'hop',
        type: 'hop',
        title: 'Hop',
        icon: '📡',
        closable: true,
        content: hopInstance
      },
      {
        id: 'terminal',
        type: 'terminal',
        title: 'Terminal',
        icon: '💻',
        closable: true,
        content: createTerminalContent()
      },
      {
        id: 'chat',
        type: 'chat',
        title: 'Chat',
        icon: '🤖',
        closable: true,
        content: createChatContent()
      },
      {
        id: 'chat-history',
        type: 'chat-history',
        title: 'Chat History',
        icon: '💬',
        closable: true,
        content: createChatHistoryContent()
      },
    ];
    setPanels(initialPanels);
  // We intentionally avoid dependencies here to prevent re-initialization loops
  // Panel content creators are memoized and their current instances are captured at mount
  }, []);

  // Remove editor panel update effect since ICUIEditor manages its own files

  // Layout presets
  const createIDELayout = useCallback(() => {
    setLayout({
      layoutMode: 'standard',
      areas: {
        left: { id: 'left', name: 'Explorer', panelIds: ['explorer', 'git'], activePanelId: 'explorer', size: 25 },
        center: { id: 'center', name: 'Editor', panelIds: ['editor'], activePanelId: 'editor', size: 50 },
        right: { id: 'right', name: 'Assistant', panelIds: ['chat'], activePanelId: 'chat', size: 25, visible: true },
        bottom: { id: 'bottom', name: 'Terminal', panelIds: ['terminal'], activePanelId: 'terminal', size: 30 },
      },
      splitConfig: { mainVerticalSplit: 70, mainHorizontalSplit: 25, rightVerticalSplit: 75 }
    });
  }, []);

  const createHLayout = useCallback(() => {
    setLayout({
      layoutMode: 'h-layout',
      areas: {
        left: { id: 'left', name: 'Explorer', panelIds: ['explorer', 'git'], activePanelId: 'explorer', size: 25, visible: true },
        center: { id: 'center', name: 'Editor', panelIds: ['editor', 'preview', 'hop'], activePanelId: 'editor', size: 40 },
        right: { id: 'right', name: 'Assistant', panelIds: ['chat', 'chat-history'], activePanelId: 'chat-history', size: 40, visible: true },
        bottom: { id: 'bottom', name: 'Terminal', panelIds: ['terminal'], activePanelId: 'terminal', size: 40 },
      },
      splitConfig: { 
        mainHorizontalSplit: 25, 
        rightVerticalSplit: 60, 
        centerVerticalSplit: 70 
      }
    });
  }, []);

  // Handle layout changes
  const handleLayoutChange = useCallback((layoutId: string) => {
    switch (layoutId) {
      case 'h-layout':
        createHLayout();
        break;
      case 'ide-layout':
        createIDELayout();
        break;
      case 'reset':
        setLayout(defaultLayout);
        break;
    }
  }, [createHLayout, createIDELayout]);

  // Handle file actions - simplified since ICUIEditor manages files
  const handleFileAction = useCallback((action: string, fileId?: string) => {
    switch (action) {
      case 'new':
        // TODO: Implement file creation dialog or delegate to editor
        break;
      case 'open':
        // TODO: Implement file open dialog
        break;
      case 'save':
        // TODO: Implement save action or delegate to editor
        break;
      case 'save-as':
        // TODO: Implement save as dialog
        break;
      case 'exit':
        // TODO: Implement exit confirmation
        break;
    }
  }, []);

  // Get current theme info
  const currentThemeInfo = THEME_OPTIONS.find(t => t.id === currentTheme) || THEME_OPTIONS[0];

  // Handle layout loading from dialog
  const handleLayoutLoad = useCallback(
    (newLayout: ICUILayoutConfig, sourcePath: string) => {
      setLayout(newLayout);

      const fileBase = getLayoutFileBaseFromPath(sourcePath);
      if (fileBase) {
        setCurrentLayoutId(fileBase);
        localStorage.setItem('icui-last-layout-file', fileBase);
        // Back-compat: older builds used this key.
        localStorage.setItem('icui-last-layout-id', fileBase);
        return;
      }

      // Fallback to layout.id if we can't infer file base
      if (newLayout.id) {
        setCurrentLayoutId(newLayout.id);
        localStorage.setItem('icui-last-layout-id', newLayout.id);
      }
    },
    [getLayoutFileBaseFromPath]
  );
  
  // Persist layout ID changes
  useEffect(() => {
    if (currentLayoutId) {
      localStorage.setItem('icui-last-layout-file', currentLayoutId);
      // Back-compat: keep the old key updated.
      localStorage.setItem('icui-last-layout-id', currentLayoutId);
    }
  }, [currentLayoutId]);

  // Mobile panel configuration state
  const [mobilePanelConfig, setMobilePanelConfig] = useState<MobilePanelConfig[]>([]);

  const ALL_MOBILE_PANELS: MobilePanelConfig[] = [
    { id: 'chat', type: 'chat', title: 'Chat', icon: '💬', enabled: false },
    { id: 'chat-history', type: 'chat-history', title: 'Chat History', icon: '📜', enabled: false },
    { id: 'explorer', type: 'explorer', title: 'Explorer', icon: '📁', enabled: false },
    { id: 'hop', type: 'hop', title: 'Hop', icon: '🔌', enabled: false },
    { id: 'editor', type: 'editor', title: 'Editor', icon: '📝', enabled: false },
    { id: 'terminal', type: 'terminal', title: 'Terminal', icon: '⌨️', enabled: false },
    { id: 'git', type: 'git', title: 'Git', icon: '🌿', enabled: false },
    { id: 'preview', type: 'preview', title: 'Preview', icon: '👁️', enabled: false },
  ];

  const DEFAULT_MOBILE_ENABLED_PANEL_IDS = ['editor', 'preview', 'hop', 'chat-history'];
  
  // Load mobile panel configuration from mobile_settings.yaml on mount
  useEffect(() => {
    const loadMobileSettings = async () => {
      try {
        const settingsPath = `${layoutConfigService.layoutDir}/mobile_settings.yaml`;
        const result = await layoutConfigService.loadFromFile(settingsPath);
        
        if (!(result.ok && result.layout)) {
          throw new Error('Settings file not found');
        }

        // Extract panel configuration from settings
        const panels = Array.isArray(result.layout.panels) ? result.layout.panels : [];
        if (panels.length === 0) {
          throw new Error('Settings file invalid or empty');
        }

        // Build config from settings file panel order
        const configPanels = panels
          .map((p: any) => {
            const basePanel = ALL_MOBILE_PANELS.find(ap => ap.id === p.id);
            const enabledRaw = p?.enabled ?? p?.config?.enabled;
            return basePanel ? { ...basePanel, enabled: enabledRaw === true } : null;
          })
          .filter(Boolean) as MobilePanelConfig[];

        // Add any missing panels at the end (disabled)
        const usedIds = new Set(configPanels.map(p => p.id));
        const missingPanels = ALL_MOBILE_PANELS.filter(p => !usedIds.has(p.id));

        // If everything is disabled (common when schema mismatches), apply defaults.
        const merged = [...configPanels, ...missingPanels];
        const enabledCount = merged.filter(p => p.enabled).length;
        if (enabledCount === 0) {
          setMobilePanelConfig(
            merged.map(p => ({ ...p, enabled: DEFAULT_MOBILE_ENABLED_PANEL_IDS.includes(p.id) }))
          );
        } else {
          setMobilePanelConfig(merged);
        }
      } catch (error) {
        // Fallback to loading from disk mobile.yaml (not from current in-memory layout).
        let enabledPanelIds: string[] = [];
        try {
          const mobilePath = `${layoutConfigService.layoutDir}/mobile.yaml`;
          const mobileResult = await layoutConfigService.loadFromFile(mobilePath);
          const mobileLayout = mobileResult.ok ? mobileResult.layout : undefined;
          const mobileArea = mobileLayout?.areas?.main || mobileLayout?.areas?.center;
          enabledPanelIds = mobileArea?.panelIds || [];
        } catch {
          enabledPanelIds = [];
        }

        if (enabledPanelIds.length === 0) {
          enabledPanelIds = DEFAULT_MOBILE_ENABLED_PANEL_IDS;
        }

        const sortedPanels = ALL_MOBILE_PANELS
          .map(panel => ({
            ...panel,
            enabled: enabledPanelIds.includes(panel.id),
          }))
          .sort((a, b) => {
            const aIndex = enabledPanelIds.indexOf(a.id);
            const bIndex = enabledPanelIds.indexOf(b.id);
            if (aIndex === -1 && bIndex === -1) return 0;
            if (aIndex === -1) return 1;
            if (bIndex === -1) return -1;
            return aIndex - bIndex;
          });

        setMobilePanelConfig(sortedPanels);
      }
    };
    
    loadMobileSettings();
  }, []);

  // Handle mobile settings save
  const handleMobileSettingsSave = useCallback(async (panels: MobilePanelConfig[]) => {
    if (!panels || panels.length === 0) {
      console.warn('Refusing to save empty mobile panel list');
      return;
    }

    // Ensure at least one panel is enabled to avoid a blank mobile UI.
    let nextPanels = panels;
    let enabledPanels = nextPanels.filter(p => p.enabled);
    if (enabledPanels.length === 0) {
      const defaultId = nextPanels.find(p => p.id === 'editor')?.id || nextPanels[0].id;
      nextPanels = nextPanels.map(p => ({ ...p, enabled: p.id === defaultId }));
      enabledPanels = nextPanels.filter(p => p.enabled);
    }

    const panelIds = enabledPanels.map(p => p.id);
    const activePanelId = panelIds[0];
    
    // Save mobile_settings.yaml with panel order and enabled state
    const mobileSettings: ICUILayoutConfig = {
      name: 'Mobile Settings',
      id: 'mobile-settings',
      version: 1,
      description: 'Mobile layout panel configuration',
      panels: nextPanels.map(p => ({
        id: p.id,
        type: p.type,
        title: p.title,
        icon: p.icon,
        // Back-compat: older code expected top-level enabled.
        enabled: p.enabled,
        config: { enabled: p.enabled },
      })),
      areas: {},
      splitConfig: {},
    };
    
    // Update mobile.yaml with enabled panels
    const mobileLayout: ICUILayoutConfig = {
      name: 'Mobile',
      id: 'mobile',
      version: 1,
      deviceTarget: 'mobile',
      layoutMode: 'mobile',
      areas: {
        main: {
          id: 'main',
          name: 'Main',
          panelIds,
          activePanelId,
          size: 100,
          visible: true,
        },
      },
      splitConfig: {},
    };
    
    try {
      // Save settings file
      await layoutConfigService.saveToFile(mobileSettings, `${layoutConfigService.layoutDir}/mobile_settings.yaml`);
      
      // Save layout file
      await layoutConfigService.saveToFile(mobileLayout, `${layoutConfigService.layoutDir}/mobile.yaml`);
      
      // Update local state
      setMobilePanelConfig(nextPanels);
      
      // If currently on mobile layout, reload it
      if (layout.layoutMode === 'mobile') {
        setLayout(mobileLayout);
      }
      
      // Mobile settings saved successfully
    } catch (error) {
      console.error('[MOBILE-SETTINGS] Failed to save mobile layout:', error);
    }
  }, [layout]);

  // Debug logging for connection status
  // console.log('Home render - editorConnectionStatus:', editorConnectionStatus);
  // console.log('Home render - connectionStatus:', connectionStatus);

  return (
    <div className={`flex flex-col h-screen bg-background text-foreground ${className}`}>
      {/* Integrated Header with Menu Bar and Logo */}
      <ICUIBaseHeader
        logo={{
          src: '/logo.svg',
          alt: 'ICOTES Logo',
          className: 'h-5 w-auto'
        }}
        currentTheme={currentTheme}
        availableThemes={THEME_OPTIONS}
        onThemeChange={setCurrentTheme}
        onMenuItemClick={handleMenuItemClick}
        className="flex-shrink-0"
      />

      {/* Main content area */}
      <div className="flex-1 flex overflow-hidden">
        <ICUILayout
          panels={panels}
          layout={layout}
          onLayoutChange={setLayout}
          enableDragDrop={true}
          persistLayout={true}
          layoutKey={`icotes-v${LAYOUT_VERSION}`}
          className="h-full w-full"
          availablePanelTypes={availablePanelTypes}
          onPanelAdd={handlePanelAdd}
          showPanelSelector={true}
          onOpenMobileSettings={() => setMobileSettingsOpen(true)}
        />
      </div>

      {/* Integrated Footer */}
      <ICUIBaseFooter
        connectionStatus={connectionStatus}
        statusText={currentFile?.name ? `File: ${currentFile.name}` : 'No file open'}
        className="flex-shrink-0"
      />
      
      {/* Layout Management Dialogs */}
      <SaveLayoutDialog
        open={saveDialogOpen}
        onOpenChange={setSaveDialogOpen}
        currentLayout={layout}
      />
      <LoadLayoutDialog
        open={loadDialogOpen}
        onOpenChange={setLoadDialogOpen}
        onLayoutLoad={handleLayoutLoad}
      />
      <MobileLayoutSettingsDialog
        open={mobileSettingsOpen}
        onClose={() => setMobileSettingsOpen(false)}
        availablePanels={mobilePanelConfig}
        onSave={handleMobileSettingsSave}
      />
      <ResetLayoutDialog
        open={resetDialogOpen}
        onOpenChange={setResetDialogOpen}
        onConfirm={handleResetLayout}
        layoutName="H Layout"
      />
    </div>
  );
};

export default Home; 