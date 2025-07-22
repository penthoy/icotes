/**
 * Integrated Home Component - Backend-Connected Application Interface
 * Cleaned up version of home.tsx prepared for ICPY integration
 * 
 * This component is ready for integration with:
 * - BackendConnectedExplorer (existing)
 * - BackendConnectedTerminal (existing)  
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

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { 
  ICUIEnhancedLayout,
  ICUIEnhancedEditorPanel,
  ICUIChatPanel
} from '../../src/icui';
import Layout from '../../src/components/Layout';
import BackendConnectedExplorer from './components/BackendConnectedExplorer';
import BackendConnectedTerminal from './components/BackendConnectedTerminal';

// Ensure we're importing the fixed explorer component
console.log('[IntegratedHome] Imported BackendConnectedExplorer from:', './components/BackendConnectedExplorer');

import type { ICUILayoutConfig } from '../../src/icui/components/ICUIEnhancedLayout';
import type { ICUIEnhancedPanel } from '../../src/icui/components/ICUIEnhancedPanelArea';
import type { ICUIEditorFile } from '../../src/icui/components/panels/ICUIEnhancedEditorPanel';
import type { ICUIPanelType } from '../../src/icui/components/ICUIPanelSelector';

interface IntegratedHomeProps {
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

// Default files for the editor
const defaultFiles: ICUIEditorFile[] = [
  {
    id: 'welcome-js',
    name: 'welcome.js',
    language: 'javascript',
    content: '// Welcome to the JavaScript Code Editor!\n// Built with React, CodeMirror 6, and the ICUI Framework\n\nfunction welcome() {\n  console.log("Welcome to your code editor!");\n  console.log("Start coding and see the magic happen!");\n  return "Happy coding!";\n}\n\nwelcome();',
    modified: false,
  },
  {
    id: 'example-py',
    name: 'example.py',
    language: 'python',
    content: '# Python Example\n# This editor supports multiple programming languages\n\ndef hello_world():\n    """A simple hello world function"""\n    print("Hello from Python!")\n    return "Success"\n\nif __name__ == "__main__":\n    result = hello_world()\n    print(f"Result: {result}")',
    modified: false,
  },
];

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

const IntegratedHome: React.FC<IntegratedHomeProps> = ({ className = '' }) => {
  // Get workspace root from environment - this will sync all panels to the same root directory
  const workspaceRoot = (import.meta as any).env?.VITE_WORKSPACE_ROOT as string | undefined;
  
  // Log workspace root for debugging
  useEffect(() => {
    console.log('[IntegratedHome] Workspace root from env:', workspaceRoot);
  }, [workspaceRoot]);

  // UI state - keeping it simple for now, ready for backend integration later
  const [layout, setLayout] = useState<ICUILayoutConfig>(defaultLayout);
  const [editorFiles, setEditorFiles] = useState<ICUIEditorFile[]>(defaultFiles);
  const [activeFileId, setActiveFileId] = useState<string>('welcome-js');
  const [currentTheme, setCurrentTheme] = useState<string>('github-dark');
  const [panels, setPanels] = useState<ICUIEnhancedPanel[]>([]);

  // Simple connection status for now - will be replaced with actual backend connection
  const isConnected = false;
  const connectionStatus = 'disconnected';

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

  // Handle file changes
  const handleFileChange = useCallback((fileId: string, newContent: string) => {
    setEditorFiles(prev => prev.map(file => 
      file.id === fileId 
        ? { ...file, content: newContent, modified: true }
        : file
    ));
  }, []);

  // Handle file close
  const handleFileClose = useCallback((fileId: string) => {
    setEditorFiles(prev => {
      const newFiles = prev.filter(file => file.id !== fileId);
      if (fileId === activeFileId && newFiles.length > 0) {
        setActiveFileId(newFiles[0].id);
      }
      return newFiles;
    });
  }, [activeFileId]);

  // Handle file save
  const handleFileSave = useCallback((fileId: string) => {
    setEditorFiles(prev => prev.map(file => 
      file.id === fileId 
        ? { ...file, modified: false }
        : file
    ));
  }, []);

  // Handle file creation
  const handleFileCreate = useCallback(() => {
    const newFile: ICUIEditorFile = {
      id: `new-file-${Date.now()}`,
      name: `untitled-${editorFiles.length + 1}.js`,
      language: 'javascript',
      content: '// New file\nconsole.log("New file created!");',
      modified: true,
    };
    setEditorFiles(prev => [...prev, newFile]);
    setActiveFileId(newFile.id);
  }, [editorFiles.length]);

  // Handle code execution
  const handleFileRun = useCallback((fileId: string, content: string, language: string) => {
    if (language === 'javascript') {
      try {
        // Execute JavaScript code
        eval(content);
      } catch (error) {
        console.error('Execution error:', error);
      }
    } else {
      // For other languages, we could implement backend execution
      console.log(`Code execution for ${language} not implemented yet`);
    }
  }, []);

  // Handle file activation (tab switching)
  const handleFileActivate = useCallback((fileId: string) => {
    setActiveFileId(fileId);
  }, []);

  // Handle file reordering
  const handleFileReorder = useCallback((fromIndex: number, toIndex: number) => {
    setEditorFiles(prev => {
      const newFiles = [...prev];
      const [movedFile] = newFiles.splice(fromIndex, 1);
      newFiles.splice(toIndex, 0, movedFile);
      return newFiles;
    });
  }, []);

  // Available panel types for the selector
  const availablePanelTypes: ICUIPanelType[] = [
    { id: 'explorer', name: 'Explorer', icon: '📁', description: 'File and folder browser' },
    { id: 'editor', name: 'Code Editor', icon: '📝', description: 'Code editor with syntax highlighting' },
    { id: 'terminal', name: 'Terminal', icon: '💻', description: 'Integrated terminal' },
    { id: 'chat', name: 'AI Assistant', icon: '🤖', description: 'AI-powered code assistant' },
    { id: 'output', name: 'Output', icon: '📤', description: 'Build and execution output' },
    { id: 'debug', name: 'Debug Console', icon: '🐛', description: 'Debug console and variables' },
  ];

  // Handle panel addition
  const handlePanelAdd = useCallback((panelType: ICUIPanelType, areaId: string) => {
    // Generate unique ID for the new panel
    const newPanelId = `${panelType.id}-${Date.now()}`;
    
    // Create panel content based on type
    let content: React.ReactNode;
    switch (panelType.id) {
      case 'explorer':
        content = (
          <BackendConnectedExplorer 
            className="h-full"
          />
        );
        break;
      case 'editor':
        content = (
          <ICUIEnhancedEditorPanel
            files={editorFiles}
            activeFileId={activeFileId}
            onFileChange={handleFileChange}
            onFileClose={handleFileClose}
            onFileCreate={handleFileCreate}
            onFileSave={handleFileSave}
            onFileRun={handleFileRun}
            onFileActivate={handleFileActivate}
            onFileReorder={handleFileReorder}
            autoSave={true}
            autoSaveDelay={1500}
            enableDragDrop={true}
            className="h-full"
          />
        );
        break;
      case 'terminal':
        content = (
          <BackendConnectedTerminal 
            className="h-full"
          />
        );
        break;
      case 'chat':
        content = <ICUIChatPanel className="h-full" />;
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
    const newPanel: ICUIEnhancedPanel = {
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
  }, [editorFiles, activeFileId, handleFileChange, handleFileClose, handleFileCreate, handleFileSave, handleFileRun, handleFileActivate]);

  // Initialize panels on mount
  useEffect(() => {
    const initialPanels: ICUIEnhancedPanel[] = [
      {
        id: 'explorer',
        type: 'explorer',
        title: 'Explorer',
        icon: '📁',
        closable: true,
        content: (
          <BackendConnectedExplorer 
            className="h-full"
          />
        )
      },
      {
        id: 'editor',
        type: 'editor',
        title: 'Code Editor',
        icon: '📝',
        closable: true,
        content: (
          <ICUIEnhancedEditorPanel
            files={editorFiles}
            activeFileId={activeFileId}
            onFileChange={handleFileChange}
            onFileClose={handleFileClose}
            onFileCreate={handleFileCreate}
            onFileSave={handleFileSave}
            onFileRun={handleFileRun}
            onFileActivate={handleFileActivate}
            onFileReorder={handleFileReorder}
            autoSave={true}
            autoSaveDelay={1500}
            enableDragDrop={true}
            className="h-full"
          />
        )
      },
      {
        id: 'terminal',
        type: 'terminal',
        title: 'Terminal',
        icon: '💻',
        closable: true,
        content: (
          <BackendConnectedTerminal 
            className="h-full"
          />
        )
      },
      {
        id: 'chat',
        type: 'chat',
        title: 'AI Assistant',
        icon: '🤖',
        closable: true,
        content: <ICUIChatPanel className="h-full" />
      },
    ];
    setPanels(initialPanels);
  }, []);

  // Update editor panel content when files change
  useEffect(() => {
    setPanels(prev => prev.map(panel => {
      if (panel.type === 'editor') {
        return {
          ...panel,
          content: (
            <ICUIEnhancedEditorPanel
              files={editorFiles}
              activeFileId={activeFileId}
              onFileChange={handleFileChange}
              onFileClose={handleFileClose}
              onFileCreate={handleFileCreate}
              onFileSave={handleFileSave}
              onFileRun={handleFileRun}
              onFileActivate={handleFileActivate}
              onFileReorder={handleFileReorder}
              autoSave={true}
              autoSaveDelay={1500}
              enableDragDrop={true}
              className="h-full"
            />
          )
        };
      }
      return panel;
    }));
  }, [editorFiles, activeFileId, handleFileChange, handleFileClose, handleFileCreate, handleFileSave, handleFileRun, handleFileActivate]);

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

  // Handle file actions
  const handleFileAction = useCallback((action: string, fileId?: string) => {
    switch (action) {
      case 'new':
        handleFileCreate();
        break;
      case 'open':
        // TODO: Implement file open dialog
        console.log('Open file dialog not implemented yet');
        break;
      case 'save':
        if (activeFileId) {
          handleFileSave(activeFileId);
        }
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
  }, [handleFileCreate, handleFileSave, activeFileId]);

  // Get current theme info
  const currentThemeInfo = THEME_OPTIONS.find(t => t.id === currentTheme) || THEME_OPTIONS[0];

  return (
    <Layout
      className={`home-container ${currentThemeInfo.class} ${className}`}
      appState={{
        currentTheme,
        availableThemes: THEME_OPTIONS,
        files: editorFiles.map(f => ({ id: f.id, name: f.name, modified: f.modified })),
        connectionStatus: 'connected', // TODO: Add real connection status
      }}
      onThemeChange={setCurrentTheme}
      onLayoutChange={handleLayoutChange}
      onFileAction={handleFileAction}
    >
      {/* Connection & Workspace Status Indicators */}
      <div className="fixed top-16 right-4 z-40 space-y-2">
        <div className={`px-3 py-1 rounded text-sm font-medium ${
          isConnected 
            ? 'bg-green-100 text-green-800 border border-green-200' 
            : 'bg-yellow-100 text-yellow-800 border border-yellow-200'
        }`}>
          {isConnected ? '🟢 Backend Connected' : '🟡 Local Mode'}
        </div>
        
        {/* Workspace Root Indicator */}
        {workspaceRoot && (
          <div className="px-3 py-1 rounded text-xs font-mono bg-blue-100 text-blue-800 border border-blue-200 max-w-xs truncate">
            📁 {workspaceRoot}
          </div>
        )}
      </div>

      {/* Main Layout */}
      <ICUIEnhancedLayout
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

export default IntegratedHome; 