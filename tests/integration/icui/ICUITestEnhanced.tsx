/**
 * ICUI Test Enhanced - Demonstrating Enhanced Framework Components
 * This is a much smaller implementation using the new enhanced framework
 * Shows how the heavy lifting is now abstracted into the framework
 */

import React, { useState, useCallback } from 'react';
import { 
  ICUIEnhancedLayout,
  ICUIEnhancedEditorPanel,
  ICUITerminalPanel,
  ICUIExplorerPanel,
  ICUIChatPanel
} from '../../../src/icui';
import type { ICUILayoutConfig } from '../../../src/icui/components/ICUIEnhancedLayout';
import type { ICUIEnhancedPanel } from '../../../src/icui/components/ICUIEnhancedPanelArea';
import type { ICUIEditorFile } from '../../../src/icui/components/panels/ICUIEnhancedEditorPanel';

interface ICUITestEnhancedProps {
  className?: string;
}

// Sample editor files
const sampleFiles: ICUIEditorFile[] = [
  {
    id: 'main-js',
    name: 'main.js',
    content: `// Enhanced ICUI Editor with Tabs!
// Much cleaner implementation using the framework

function enhancedExample() {
  console.log("Framework does the heavy lifting!");
  return "Less code, more functionality";
}

enhancedExample();`,
    language: 'javascript',
    modified: false,
  },
  {
    id: 'utils-py',
    name: 'utils.py',
    content: `# Python utilities
# Multi-file support built into the framework

def calculate_sum(a, b):
    """Calculate sum of two numbers"""
    return a + b

def main():
    result = calculate_sum(5, 3)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()`,
    language: 'python',
    modified: true,
  },
  {
    id: 'config-json',
    name: 'config.json',
    content: `{
  "name": "icui-enhanced-test",
  "version": "1.0.0",
  "description": "Testing enhanced ICUI framework with multiple files",
  "features": [
    "tab-switching",
    "drag-and-drop",
    "auto-save",
    "syntax-highlighting"
  ],
  "theme": "dark"
}`,
    language: 'javascript',
    modified: false,
  }
];

// Default layout configuration - H Layout as default
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
    centerVerticalSplit: 65,
  }
};

export const ICUITestEnhanced: React.FC<ICUITestEnhancedProps> = ({ className = '' }) => {
  const [layout, setLayout] = useState<ICUILayoutConfig>(defaultLayout);
  const [editorFiles, setEditorFiles] = useState<ICUIEditorFile[]>(sampleFiles);
  const [activeFileId, setActiveFileId] = useState<string>('main-js');
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');

  // Handle file changes
  const handleFileChange = useCallback((fileId: string, content: string) => {
    setEditorFiles(prev => prev.map(f => 
      f.id === fileId ? { ...f, content, modified: true } : f
    ));
  }, []);

  // Handle file save
  const handleFileSave = useCallback((fileId: string) => {
    setEditorFiles(prev => prev.map(f => 
      f.id === fileId ? { ...f, modified: false } : f
    ));
    console.log('File saved:', fileId);
  }, []);

  // Handle file close
  const handleFileClose = useCallback((fileId: string) => {
    setEditorFiles(prev => {
      const newFiles = prev.filter(f => f.id !== fileId);
      if (fileId === activeFileId && newFiles.length > 0) {
        setActiveFileId(newFiles[0].id);
      }
      return newFiles;
    });
  }, [activeFileId]);

  // Handle new file creation
  const handleFileCreate = useCallback(() => {
    const newFile: ICUIEditorFile = {
      id: `file-${Date.now()}`,
      name: `untitled-${editorFiles.length + 1}.js`,
      content: '// New file\nconsole.log("Hello from new file!");',
      language: 'javascript',
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

  // Create panels using the enhanced framework
  const panels: ICUIEnhancedPanel[] = [
    {
      id: 'explorer',
      type: 'explorer',
      title: 'Explorer',
      icon: '📁',
      closable: false,
      content: <ICUIExplorerPanel className="h-full" />
    },
    {
      id: 'editor',
      type: 'editor',
      title: 'Code Editor',
      icon: '📝',
      closable: false,
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
          theme={theme}
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
      content: <ICUITerminalPanel className="h-full" />
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

  return (
    <div className={`icui-test-enhanced flex flex-col ${className}`} style={{ height: '100vh', minHeight: '100vh' }}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 shrink-0">
        <h2 className="text-xl font-bold">ICUI Enhanced Framework Test</h2>
        <div className="flex items-center space-x-2">
          <button
            onClick={createHLayout}
            className="px-3 py-1 text-sm bg-orange-500 text-black rounded hover:bg-orange-600"
          >
            H Layout (Default)
          </button>

          <button
            onClick={createIDELayout}
            className="px-3 py-1 text-sm bg-blue-500 text-black rounded hover:bg-blue-600"
          >
            IDE Layout
          </button>

          <button
            onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            className="px-3 py-1 text-sm bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
        </div>
      </div>

      {/* Layout - Takes remaining height */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <ICUIEnhancedLayout
          panels={panels}
          layout={layout}
          onLayoutChange={setLayout}
          enableDragDrop={true}
          persistLayout={true}
          layoutKey="icui-test-enhanced"
          className="h-full w-full"
        />
      </div>

      {/* Status */}
      <div className="p-2 bg-gray-100 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 text-sm text-gray-600 dark:text-gray-400 shrink-0">
        Active Files: {editorFiles.length} | 
        Modified: {editorFiles.filter(f => f.modified).length} | 
        Theme: {theme} | 
        Layout: Persistent
      </div>
    </div>
  );
};

export default ICUITestEnhanced;
