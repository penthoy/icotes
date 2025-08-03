/**
 * Integrated Home Component - Backend-Connected Application Interface
 * Cleaned up version of home.tsx prepared for ICPY integration
 * 
 * This component is ready for integration with:
 * - ICUIExplorer (existing)
 * - ICUITerminal (existing)  
 * - Simple editor components for now (to be enhanced later)
 * - Backend state synchronization (hooks ready)
 * 
 * Key Changes from Original home.tsx:
 * - Prepared for backend state management (hooks ready but graceful fallback)
 * - Uses existing integration components where available
 * - Simplified structure ready for ICPY backend connection
 * - Added workspace synchronization with WORKSPACE_ROOT from .env
 * - Clean error handling and connection status display
 */

import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { 
  ICUILayout,
  ICUIChat
} from '../icui';
import Layout from './Layout';
import ICUIExplorer from '../icui/components/ICUIExplorer';
import ICUITerminal from '../icui/components/ICUITerminal';
import ICUIEditor, { ICUIEditorRef } from '../icui/components/ICUIEditor';

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
    left: { id: 'left', name: 'Explorer', panelIds: ['explorer'], activePanelId: 'explorer', size: 25, visible: true },
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

  // Handle file selection from Explorer - VS Code-like temporary file opening
  const handleFileSelect = useCallback((file: any) => {
    if (file.type === 'file' && editorRef.current) {
      // Single click opens file temporarily (will be replaced by next single click)
      editorRef.current.openFileTemporary(file.path);
    }
  }, []);

  // Handle file double-click from Explorer - VS Code-like permanent file opening
  const handleFileDoubleClick = useCallback((file: any) => {
    if (file.type === 'file' && editorRef.current) {
      // Double click opens file permanently (will not be replaced by single clicks)
      editorRef.current.openFilePermanent(file.path);
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

  // Handle connection status changes from ICUIEditor
  const handleConnectionStatusChange = useCallback((status: {connected: boolean; error?: string; timestamp?: number}) => {
    console.log('Home received connection status change:', status);
    console.log('Updating editorConnectionStatus to:', status);
    setEditorConnectionStatus(status);
  }, []);

  // Debug: Log when connectionStatus derived value changes
  useEffect(() => {
    console.log('connectionStatus derived value changed to:', connectionStatus);
  }, [connectionStatus]);

  // Remove local file management handlers - let ICUIEditor handle its own files
  // These are kept for potential future use but do nothing now

  // Available panel types for the selector
  const availablePanelTypes: ICUIPanelType[] = [
    { id: 'explorer', name: 'Explorer', icon: '📁', description: 'File and folder browser' },
    { id: 'editor', name: 'Code Editor', icon: '📝', description: 'Code editor with syntax highlighting' },
    { id: 'terminal', name: 'Terminal', icon: '💻', description: 'Integrated terminal' },
    { id: 'chat', name: 'AI Assistant', icon: '🤖', description: 'AI-powered code assistant' },
    { id: 'output', name: 'Output', icon: '📤', description: 'Build and execution output' },
    { id: 'debug', name: 'Debug Console', icon: '🐛', description: 'Debug console and variables' },
  ];

  // Stable panel instances to prevent recreation on layout changes
  const explorerInstance = useMemo(() => (
    <ICUIExplorer 
      className="h-full"
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
    <ICUIChat className="h-full" />
  ), []);

  // Memoized panel content creators to prevent recreation on layout changes
  const createExplorerContent = useCallback(() => explorerInstance, [explorerInstance]);
  const createEditorContent = useCallback(() => editorInstance, [editorInstance]);
  const createTerminalContent = useCallback(() => terminalInstance, [terminalInstance]);
  const createChatContent = useCallback(() => chatInstance, [chatInstance]);

  // Handle panel addition
  const handlePanelAdd = useCallback((panelType: ICUIPanelType, areaId: string) => {
    // Generate unique ID for the new panel
    const newPanelId = `${panelType.id}-${Date.now()}`;
    
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
      case 'output':
        content = <div className="h-full p-4" style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)' }}>Output Panel - Build and execution output will appear here</div>;
        break;
      case 'debug':
        content = <div className="h-full p-4" style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)' }}>Debug Console - Debug information and variables will appear here</div>;
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
  }, [createExplorerContent, createEditorContent, createTerminalContent, createChatContent]);

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
  }, [createExplorerContent, createEditorContent, createTerminalContent, createChatContent]);

  // Remove editor panel update effect since ICUIEditor manages its own files

  // Layout presets
  const createIDELayout = useCallback(() => {
    setLayout({
      layoutMode: 'standard',
      areas: {
        left: { id: 'left', name: 'Explorer', panelIds: ['explorer'], activePanelId: 'explorer', size: 25 },
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
        left: { id: 'left', name: 'Explorer', panelIds: ['explorer'], activePanelId: 'explorer', size: 25, visible: true },
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
        console.log('File creation delegated to ICUIEditor');
        break;
      case 'open':
        // TODO: Implement file open dialog
        console.log('Open file dialog not implemented yet');
        break;
      case 'save':
        // TODO: Implement save action or delegate to editor
        console.log('Save action delegated to ICUIEditor');
        break;
      case 'save-as':
        // TODO: Implement save as dialog
        console.log('Save as dialog not implemented yet');
        break;
      case 'exit':
        // TODO: Implement exit confirmation
        console.log('Exit confirmation not implemented yet');
        break;
    }
  }, []);

  // Get current theme info
  const currentThemeInfo = THEME_OPTIONS.find(t => t.id === currentTheme) || THEME_OPTIONS[0];

  // Debug logging for connection status
  // console.log('Home render - editorConnectionStatus:', editorConnectionStatus);
  // console.log('Home render - connectionStatus:', connectionStatus);

  return (
    <Layout
      className={`home-container ${currentThemeInfo.class} ${className}`}
      appState={{
        currentTheme,
        availableThemes: THEME_OPTIONS,
        files: [], // ICUIEditor manages its own files now
        connectionStatus: connectionStatus, // Now uses real connection status from editor
      }}
      onThemeChange={setCurrentTheme}
      onLayoutChange={handleLayoutChange}
      onFileAction={handleFileAction}
    >
      {/* Main Layout */}
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
    </Layout>
  );
};

export default Home; 