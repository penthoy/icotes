/**
 * Home (ICUI): Main application shell with header, layout, and footer.
 * - Uses ICUIBaseHeader as the single source of truth for top menus and theme switcher.
 * - Renders panels via ICUILayout (Explorer, Editor, Terminal, Chat, etc.).

 */

import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { 
  ICUILayout,
  ICUIChat,
  ICUITerminal,
  ICUIEditor,
  ICUIChatHistory,
  ICUIExplorer,
  ICUIGit,
  ICUIPreview
} from '../icui';
import { ICUIHop } from '../icui/components/panels';
import type { ICUIEditorRef, ICUIPreviewRef } from '../icui';
import { globalCommandRegistry } from '../icui/lib/commandRegistry';
import ICUIBaseHeader from '../icui/components/ICUIBaseHeader';
import ICUIBaseFooter from '../icui/components/ICUIBaseFooter';

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

// Default layout configuration
const defaultLayout: ICUILayoutConfig = {
  layoutMode: 'h-layout',
  areas: {
    left: { id: 'left', name: 'Explorer', panelIds: ['explorer', 'git'], activePanelId: 'explorer', size: 20, visible: true },
    center: { id: 'center', name: 'Editor', panelIds: ['editor', 'preview', 'hop'], activePanelId: 'editor', size: 50 },
    right: { id: 'right', name: 'Assistant', panelIds: ['chat', 'chat-history'], activePanelId: 'chat', size: 30, visible: true },
    bottom: { id: 'bottom', name: 'Terminal', panelIds: ['terminal'], activePanelId: 'terminal', size: 40 },
  },
  splitConfig: { 
    mainHorizontalSplit: 25, 
    rightVerticalSplit: 75, 
    centerVerticalSplit: 65 
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
      if (process.env.NODE_ENV === 'development') {
        console.log('[Home] Handling preview for file:', filePath);
      }
      
      if (!previewRef.current) {
        console.error('[Home] Preview ref not available, waiting...');
        // Wait a bit for the component to mount
        await new Promise(resolve => setTimeout(resolve, 100));
        if (!previewRef.current) {
          console.error('[Home] Preview ref still not available after waiting');
          return;
        }
      }

      // Read the file content
      const response = await fetch(`/api/files/content?path=${encodeURIComponent(filePath)}`);
      if (!response.ok) {
        throw new Error(`Failed to read file: ${response.statusText}`);
      }
      
      const result = await response.json();
      const content = result.data.content;
      const fileName = filePath.split('/').pop() || 'file.html';

      // NEW: Also include local dependencies (CSS/JS/images) referenced by the HTML
      // so that simple multi-file snippets render properly in Preview.
      // This avoids asking the user to manually bundle files.
      let filesMap: Record<string, string> = { [fileName]: content };

      try {
        // Only attempt dependency collection for HTML
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

          // Fetch each asset from workspace and include with its original relative key
          await Promise.all(
            assetPaths.map(async (rel) => {
              const abs = toAbs(rel);
              if (!abs) return;
              try {
                const resp = await fetch(`/api/files/content?path=${encodeURIComponent(abs)}`);
                if (!resp.ok) return;
                const data = await resp.json();
                // Normalize leading './'
                const key = rel.replace(/^\.\//, '');
                filesMap[key] = data.data.content as string;
              } catch (e) {
                // Best-effort; missing assets will just 404 in preview server
                if (process.env.NODE_ENV === 'development') {
                  console.warn('[Home] Failed to include preview asset:', rel, e);
                }
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
    if (file.type === 'file' && editorRef.current) {
      // Single click opens file temporarily (will be replaced by next single click)
      editorRef.current.openFileTemporary(file.path);
      setCurrentFile(file);
    }
  }, []);

  // Handle file double-click from Explorer - VS Code-like permanent file opening
  const handleFileDoubleClick = useCallback((file: any) => {
    if (process.env.NODE_ENV === 'development') {
      console.log('[Home] handleFileDoubleClick called with file:', file.name, 'at path:', file.path);
    }
    if (file.type === 'file' && editorRef.current) {
      // Double click opens file permanently (will not be replaced by single clicks)
      editorRef.current.openFilePermanent(file.path);
      setCurrentFile(file);
    } else {
      console.warn('[Home] Cannot open file:', { isFile: file.type === 'file', hasEditorRef: !!editorRef.current });
    }
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

  // Register preview command for HTML files
  useEffect(() => {
    globalCommandRegistry.register({
      id: 'explorer.preview',
      label: 'Preview',
      description: 'Preview HTML file in Live Preview panel',
      icon: '👁️',
      category: 'explorer',
      handler: (context?: any) => {
        if (context && context.selectedFiles && context.selectedFiles.length > 0) {
          const selectedFile = context.selectedFiles[0];
          if (selectedFile.type === 'file' && selectedFile.path) {
            handlePreviewFile(selectedFile.path);
          }
        }
      }
    });

    // Cleanup on unmount
    return () => {
      globalCommandRegistry.unregister('explorer.preview');
    };
  }, [handlePreviewFile]);

  // Initialize Explorer file operations
  useEffect(() => {
    import('../icui/components/explorer/FileOperations').then(({ ExplorerFileOperations }) => {
      const fileOps = ExplorerFileOperations.getInstance();
      fileOps.registerCommands();
    }).catch(err => {
      console.error('Failed to initialize Explorer file operations:', err);
    });
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

  // Initialize panels on mount
  useEffect(() => {
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
  }, [createExplorerContent, createEditorContent, createTerminalContent, createChatContent, createGitContent, createPreviewContent, createChatHistoryContent]);

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
        center: { id: 'center', name: 'Editor', panelIds: ['editor', 'preview', 'hop'], activePanelId: 'editor', size: 50 },
        right: { id: 'right', name: 'Assistant', panelIds: ['chat', 'chat-history'], activePanelId: 'chat', size: 25, visible: true },
        bottom: { id: 'bottom', name: 'Terminal', panelIds: ['terminal'], activePanelId: 'terminal', size: 40 },
      },
      splitConfig: { 
        mainHorizontalSplit: 25, 
        rightVerticalSplit: 75, 
        centerVerticalSplit: 65 
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
          layoutKey="icotes"
          className="h-full w-full"
          availablePanelTypes={availablePanelTypes}
          onPanelAdd={handlePanelAdd}
          showPanelSelector={true}
        />
      </div>

      {/* Integrated Footer */}
      <ICUIBaseFooter
        connectionStatus={connectionStatus}
        statusText={currentFile?.name ? `File: ${currentFile.name}` : 'No file open'}
        className="flex-shrink-0"
      />
    </div>
  );
};

export default Home; 