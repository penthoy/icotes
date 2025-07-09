/**
 * ICUI Test Enhanced - Demonstrating Enhanced Framework Components
 * This is a much smaller implementation using the new enhanced framework
 * Shows how the heavy lifting is now abstracted into the framework
 */

import React, { useState, useCallback } from 'react';
import { 
  ICUIEnhancedLayout,
  ICUIEnhancedEditorPanel,
  ICUIEnhancedTerminalPanel,
  ICUIExplorerPanel,
  ICUIChatPanel
} from '../../../src/icui';
import type { ICUILayoutConfig } from '../../../src/icui/components/ICUIEnhancedLayout';
import type { ICUIEnhancedPanel } from '../../../src/icui/components/ICUIEnhancedPanelArea';
import type { ICUIEditorFile } from '../../../src/icui/components/panels/ICUIEnhancedEditorPanel';
import type { ICUIPanelType } from '../../../src/icui/components/ICUIPanelSelector';

interface ICUITestEnhancedProps {
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

// Sample files for the editor
const sampleFiles: ICUIEditorFile[] = [
  {
    id: 'main-js',
    name: 'main.js',
    language: 'javascript',
    content: '// Enhanced ICUI Editor with Tabs!\n// Much cleaner implementation using the Framework\n\nfunction enhancedExample() {\n  console.log("Framework does the heavy lifting!");\n  return "Less code, more functionality";\n}\n\nenhancedExample();',
    modified: false,
  },
  {
    id: 'utils-py',
    name: 'utils.py',
    language: 'python',
    content: '# Python utilities\n\ndef hello_world():\n    """A simple hello world function"""\n    print("Hello from Python!")\n    return "success"\n\n# Enhanced with framework support\nif __name__ == "__main__":\n    hello_world()',
    modified: true,
  },
  {
    id: 'config-json',
    name: 'config.json',
    language: 'javascript',
    content: '{\n  "name": "icui-enhanced",\n  "version": "1.0.0",\n  "description": "Enhanced ICUI Framework Test",\n  "main": "main.js",\n  "features": {\n    "tabs": true,\n    "dragDrop": true,\n    "themes": true\n  }\n}',
    modified: false,
  },
];

// Default layout configuration
const defaultLayout: ICUILayoutConfig = {
  layoutMode: 'h-layout',
  areas: {
    left: { id: 'left', name: 'Explorer', panelIds: ['explorer'], activePanelId: 'explorer', size: 25, visible: true },
    center: { id: 'center', name: 'Editor', panelIds: ['editor'], activePanelId: 'editor', size: 50 },
    right: { id: 'right', name: 'Chat', panelIds: ['chat'], activePanelId: 'chat', size: 25, visible: true },
    bottom: { id: 'bottom', name: 'Terminal', panelIds: ['terminal'], activePanelId: 'terminal', size: 40 },
  },
  splitConfig: { 
    mainHorizontalSplit: 25, 
    rightVerticalSplit: 75, 
    centerVerticalSplit: 65 
  }
};

export const ICUITestEnhanced: React.FC<ICUITestEnhancedProps> = ({ className = '' }) => {
  const [layout, setLayout] = useState<ICUILayoutConfig>(defaultLayout);
  const [editorFiles, setEditorFiles] = useState<ICUIEditorFile[]>(sampleFiles);
  const [activeFileId, setActiveFileId] = useState<string>('main-js');
  const [currentTheme, setCurrentTheme] = useState<string>('github-dark');
  const [panels, setPanels] = useState<ICUIEnhancedPanel[]>([]);

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
      content: '// New file\nconsole.log("Hello from new file!");',
      modified: true,
    };
    setEditorFiles(prev => [...prev, newFile]);
    setActiveFileId(newFile.id);
  }, [editorFiles.length]);

  // Handle code execution
  const handleFileRun = useCallback((fileId: string, content: string, language: string) => {
    console.log(`Running ${language} code from ${fileId}:`, content);
    if (language === 'javascript') {
      try {
        eval(content);
      } catch (error) {
        console.error('Execution error:', error);
      }
    }
  }, []);

  // Handle file activation (tab switching)
  const handleFileActivate = useCallback((fileId: string) => {
    setActiveFileId(fileId);
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
    console.log(`Adding panel ${panelType.name} to area ${areaId}`);
    
    // Generate unique ID for the new panel
    const newPanelId = `${panelType.id}-${Date.now()}`;
    
    // Create panel content based on type
    let content: React.ReactNode;
    switch (panelType.id) {
      case 'explorer':
        content = <ICUIExplorerPanel className="h-full" />;
        break;
      case 'editor':
        // For editor panels, use placeholder content that will be updated by the effect
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
            autoSave={true}
            autoSaveDelay={1500}
            className="h-full"
          />
        );
        break;
      case 'terminal':
        content = <ICUIEnhancedTerminalPanel className="h-full" />;
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

  // Initialize panels on mount - ONLY ONCE
  React.useEffect(() => {
    const initialPanels: ICUIEnhancedPanel[] = [
      {
        id: 'explorer',
        type: 'explorer',
        title: 'Explorer',
        icon: '📁',
        closable: true,
        content: <ICUIExplorerPanel className="h-full" />
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
            autoSave={true}
            autoSaveDelay={1500}
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
        content: <ICUIEnhancedTerminalPanel className="h-full" />
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
  }, []); // Empty dependency array - only run once on mount

  // Update ALL editor panel content when files change without resetting entire panels array
  React.useEffect(() => {
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
              autoSave={true}
              autoSaveDelay={1500}
              className="h-full"
            />
          )
        };
      }
      return panel;
    }));
  }, [editorFiles, activeFileId, handleFileChange, handleFileClose, handleFileCreate, handleFileSave, handleFileRun, handleFileActivate]);

  // Panels are now managed by state instead of hardcoded array

  // Layout presets
  const createIDELayout = useCallback(() => {
    setLayout({
      layoutMode: 'standard',
      areas: {
        left: { id: 'left', name: 'Explorer', panelIds: ['explorer'], activePanelId: 'explorer', size: 25 },
        center: { id: 'center', name: 'Editor', panelIds: ['editor'], activePanelId: 'editor', size: 50 },
        right: { id: 'right', name: 'Chat', panelIds: ['chat'], activePanelId: 'chat', size: 25, visible: true },
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
        right: { id: 'right', name: 'Chat', panelIds: ['chat'], activePanelId: 'chat', size: 25, visible: true },
        bottom: { id: 'bottom', name: 'Terminal', panelIds: ['terminal'], activePanelId: 'terminal', size: 40 },
      },
      splitConfig: { 
        mainHorizontalSplit: 25, 
        rightVerticalSplit: 75, 
        centerVerticalSplit: 65 
      }
    });
  }, []);

  // Get current theme info
  const currentThemeInfo = THEME_OPTIONS.find(t => t.id === currentTheme) || THEME_OPTIONS[0];

  return (
    <div className={`icui-test-enhanced flex flex-col ${currentThemeInfo.class} ${className}`} style={{ height: '100vh', minHeight: '100vh', maxHeight: '100vh' }}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b shrink-0" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderColor: 'var(--icui-border-subtle)', color: 'var(--icui-text-primary)' }}>
        <h2 className="text-xl font-bold">ICUI Enhanced Framework Test</h2>
        <div className="flex items-center space-x-2">
          <button
            onClick={createHLayout}
            className="px-3 py-1 text-sm text-white rounded hover:opacity-80 transition-opacity"
            style={{ backgroundColor: 'var(--icui-warning)' }}
          >
            H Layout (Default)
          </button>

          <button
            onClick={createIDELayout}
            className="px-3 py-1 text-sm text-white rounded hover:opacity-80 transition-opacity"
            style={{ backgroundColor: 'var(--icui-accent)' }}
          >
            IDE Layout
          </button>

          <select
            value={currentTheme}
            onChange={(e) => setCurrentTheme(e.target.value)}
            className="px-3 py-1 text-sm rounded border"
            style={{ 
              backgroundColor: 'var(--icui-bg-primary)', 
              borderColor: 'var(--icui-border)', 
              color: 'var(--icui-text-primary)' 
            }}
          >
            {THEME_OPTIONS.map(theme => (
              <option key={theme.id} value={theme.id}>
                {theme.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Layout - Takes remaining height with proper constraints */}
      <div className="flex-1 min-h-0 max-h-full overflow-hidden">
        <ICUIEnhancedLayout
          panels={panels}
          layout={layout}
          onLayoutChange={setLayout}
          enableDragDrop={true}
          persistLayout={true}
          layoutKey="icui-test-enhanced"
          className="h-full w-full"
          availablePanelTypes={availablePanelTypes}
          onPanelAdd={handlePanelAdd}
          showPanelSelector={true}
        />
      </div>

      {/* Status */}
      <div className="p-2 border-t text-sm shrink-0" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderColor: 'var(--icui-border-subtle)', color: 'var(--icui-text-secondary)' }}>
        Active Files: {editorFiles.length} | 
        Modified: {editorFiles.filter(f => f.modified).length} | 
        Theme: {currentThemeInfo.name} | 
        Layout: Persistent
      </div>
    </div>
  );
};

export default ICUITestEnhanced;
