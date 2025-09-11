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
  ICUIGit
} from '../icui';
import type { ICUIEditorRef } from '../icui';
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
    left: { id: 'left', name: 'Explorer', panelIds: ['explorer', 'git'], activePanelId: 'explorer', size: 25, visible: true },
    center: { id: 'center', name: 'Editor', panelIds: ['editor'], activePanelId: 'editor', size: 50 },
    right: { id: 'right', name: 'Assistant', panelIds: ['chat'], activePanelId: 'chat', size: 25, visible: true },
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

  // Menu state for integrated menus
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const [currentFile, setCurrentFile] = useState<any>(null);
  // Git repo gating removed; ICUIGit handles its own connect logic

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
    console.log('[Home] handleFileDoubleClick called with file:', file.name, 'at path:', file.path);
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
    if (status.error) {
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
    { id: 'chat', name: 'AI Assistant', icon: '🤖', description: 'AI-powered code assistant' },
    { id: 'chat-history', name: 'Chat History', icon: '💬', description: 'Manage chat sessions and history' },
    { id: 'git', name: 'Source Control', icon: '🌿', description: 'Git source control management' },
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

  const chatInstance = useMemo(() => (
    <ICUIChat 
      className="h-full" 
      key="main-chat-instance"
    />
  ), []);

  const chatHistoryInstance = useMemo(() => (
    <ICUIChatHistory 
      className="h-full" 
      key="main-chat-history-instance"
    />
  ), []);

  const gitInstance = useMemo(() => (
    <ICUIGit 
      className="h-full"
      onFileSelect={handleFileSelect}
      onFileOpen={handleFileDoubleClick}
      onOpenDiffPatch={(path) => {
        console.log('[Home] onOpenDiffPatch called, editorRef.current:', !!editorRef.current);
        if (editorRef.current?.openDiffPatch) {
          editorRef.current.openDiffPatch(path);
        } else {
          console.warn('[Home] Editor ref or openDiffPatch method not available');
        }
      }}
    />
  ), [handleFileSelect, handleFileDoubleClick]);

  const createExplorerContent = useCallback(() => explorerInstance, [explorerInstance]);
  const createEditorContent = useCallback(() => editorInstance, [editorInstance]);
  const createTerminalContent = useCallback(() => terminalInstance, [terminalInstance]);
  const createChatContent = useCallback(() => chatInstance, [chatInstance]);
  const createChatHistoryContent = useCallback(() => chatHistoryInstance, [chatHistoryInstance]);
  const createGitContent = useCallback(() => {
    // Always show main Git panel (connect disabled)
    return gitInstance;
  }, [gitInstance]);

  // Handle panel addition
  const handlePanelAdd = useCallback((panelType: ICUIPanelType, areaId: string) => {
    // Generate unique ID for the new panel - use stable IDs for chat panels
    const newPanelId = panelType.id === 'chat' || panelType.id === 'chat-history' 
      ? `${panelType.id}-main` 
      : `${panelType.id}-${Date.now()}`;
    
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
        title: 'Code Editor',
        icon: '📝',
        closable: true,
        content: createEditorContent()
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
        title: 'AI Assistant',
        icon: '🤖',
        closable: true,
        content: createChatContent()
      },
    ];
    setPanels(initialPanels);
  }, [createExplorerContent, createEditorContent, createTerminalContent, createChatContent, createGitContent]);

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
        center: { id: 'center', name: 'Editor', panelIds: ['editor'], activePanelId: 'editor', size: 50 },
        right: { id: 'right', name: 'Assistant', panelIds: ['chat'], activePanelId: 'chat', size: 25, visible: true },
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