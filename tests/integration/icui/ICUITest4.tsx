/**
 * ICUI Framework Test Component - Phase 4 (Specialized Panels)
 * Demonstrates specialized panel implementations working within the docking system
 */

import React, { useState, useCallback } from 'react';
import { 
  ICUIFrameContainer,
  ICUISplitPanel,
  ICUIPanelArea,
  useICUIPanels, 
  createPanel,
  ICUIPanelType,
  ICUIPanelInstance
} from '../../../src/icui';
import { FileData } from '../../../src/components/archived/FileTabs';
import ICUITerminalPanel from '../../../src/icui/components/panels/ICUITerminalPanel';
import CodeEditor, { SupportedLanguage } from '../../../src/components/archived/CodeEditor';
import FileExplorer from '../../../src/components/archived/FileExplorer';

interface ICUITest4Props {
  className?: string;
}

// Sample file data for the editor panel
const sampleFiles: FileData[] = [
  {
    id: 'app-tsx',
    name: 'App.tsx',
    content: `import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Home from './components/Home';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
    </Routes>
  );
}

export default App;`,
    isModified: false,
  },
  {
    id: 'main-py',
    name: 'main.py',
    content: `# Python script example
def hello_world():
    print("Hello, World!")
    return "success"

if __name__ == "__main__":
    hello_world()`,
    isModified: false,
  },
  {
    id: 'script-js',
    name: 'script.js',
    content: `// JavaScript example
function calculateSum(a, b) {
    return a + b;
}

console.log(calculateSum(5, 3));`,
    isModified: true,
  }
];

// Sample file explorer data
const sampleExplorerFiles = [
  {
    id: 'src',
    name: 'src',
    type: 'folder' as const,
    path: '/src',
    children: [
      {
        id: 'components',
        name: 'components',
        type: 'folder' as const,
        path: '/src/components',
        children: [
          { id: 'app-file', name: 'App.tsx', type: 'file' as const, path: '/src/components/App.tsx' },
          { id: 'home-file', name: 'Home.tsx', type: 'file' as const, path: '/src/components/Home.tsx' },
        ],
        isExpanded: true,
      },
      { id: 'main-file', name: 'main.tsx', type: 'file' as const, path: '/src/main.tsx' },
    ],
    isExpanded: true,
  },
  {
    id: 'public',
    name: 'public',
    type: 'folder' as const,
    path: '/public',
    children: [
      { id: 'index-file', name: 'index.html', type: 'file' as const, path: '/public/index.html' },
    ],
    isExpanded: false,
  },
  { id: 'package-file', name: 'package.json', type: 'file' as const, path: '/package.json' },
  { id: 'readme-file', name: 'README.md', type: 'file' as const, path: '/README.md' },
];

/**
 * Test component for ICUI Framework Phase 4
 * Shows specialized panel implementations working with docking system
 */
export const ICUITest4: React.FC<ICUITest4Props> = ({ className = '' }) => {
  const { panels, actions } = useICUIPanels();
  const [editorFiles, setEditorFiles] = useState<FileData[]>(sampleFiles);
  const [activeFileId, setActiveFileId] = useState<string>('app-tsx');
  const [theme, setTheme] = useState<'light' | 'dark'>('dark'); // Default to dark theme
  
  // Apply theme to document root on mount and theme change
  React.useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
  }, [theme]);

  // Panel area state - tracking which panels are in which areas
  const [panelAreas, setPanelAreas] = useState<{
    leftArea: string[];
    centerArea: string[];
    rightArea: string[];
    bottomArea: string[];
  }>({
    leftArea: [],
    centerArea: [],
    rightArea: [],
    bottomArea: [],
  });

  // Active panel per area
  const [activePanels, setActivePanels] = useState<{
    leftArea?: string;
    centerArea?: string;
    rightArea?: string;
    bottomArea?: string;
  }>({});

  // Create IDE-like demo layout with specialized panels
  const createIDELayout = useCallback(() => {
    // Clear existing panels
    panels.forEach(panel => actions.remove(panel.id));
    
    // Create specialized panels
    const explorerPanel = actions.create(createPanel('explorer', { 
      title: 'Explorer',
      closable: true,
      resizable: true 
    }));
    
    const editorPanel = actions.create(createPanel('editor', { 
      title: 'Editor',
      closable: false,
      resizable: true 
    }));
    
    const terminalPanel = actions.create(createPanel('terminal', { 
      title: 'Terminal',
      closable: true,
      resizable: true 
    }));
    
    // Assign to areas to create an IDE layout
    setPanelAreas({
      leftArea: [explorerPanel.id],
      centerArea: [editorPanel.id],
      rightArea: [],
      bottomArea: [terminalPanel.id],
    });
    
    // Set active panels
    setActivePanels({
      leftArea: explorerPanel.id,
      centerArea: editorPanel.id,
      rightArea: undefined,
      bottomArea: terminalPanel.id,
    });
  }, [panels, actions]);

  // Create multi-editor layout
  const createMultiEditorLayout = useCallback(() => {
    // Clear existing panels
    panels.forEach(panel => actions.remove(panel.id));
    
    // Create multiple editor panels
    const editor1Panel = actions.create(createPanel('editor', { 
      title: 'TypeScript Editor',
      closable: true,
      resizable: true 
    }));
    
    const editor2Panel = actions.create(createPanel('editor', { 
      title: 'Python Editor',
      closable: true,
      resizable: true 
    }));
    
    const explorerPanel = actions.create(createPanel('explorer', { 
      title: 'File Explorer',
      closable: true,
      resizable: true 
    }));
    
    const terminalPanel = actions.create(createPanel('terminal', { 
      title: 'Integrated Terminal',
      closable: true,
      resizable: true 
    }));
    
    // Assign to areas
    setPanelAreas({
      leftArea: [explorerPanel.id],
      centerArea: [editor1Panel.id, editor2Panel.id], // Multiple editors in tabs
      rightArea: [],
      bottomArea: [terminalPanel.id],
    });
    
    // Set active panels
    setActivePanels({
      leftArea: explorerPanel.id,
      centerArea: editor1Panel.id, // First editor active
      rightArea: undefined,
      bottomArea: terminalPanel.id,
    });
  }, [panels, actions]);

  // Handle panel activation within an area
  const handlePanelActivate = useCallback((areaId: string, panelId: string) => {
    setActivePanels(prev => ({
      ...prev,
      [areaId]: panelId,
    }));
  }, []);

  // Handle panel close
  const handlePanelClose = useCallback((areaId: string, panelId: string) => {
    // Remove from panel areas
    setPanelAreas(prev => ({
      ...prev,
      [areaId]: prev[areaId as keyof typeof prev].filter(id => id !== panelId),
    }));
    
    // Update active panel if this was active
    const areaName = areaId as keyof typeof activePanels;
    if (activePanels[areaName] === panelId) {
      const remainingPanels = panelAreas[areaName as keyof typeof panelAreas].filter(id => id !== panelId);
      setActivePanels(prev => ({
        ...prev,
        [areaId]: remainingPanels[0] || undefined,
      }));
    }
    
    // Remove panel
    actions.remove(panelId);
  }, [activePanels, panelAreas, actions]);

  // Handle panel drop between areas
  const handlePanelDrop = useCallback((targetAreaId: string, panelId: string, sourceAreaId: string) => {
    setPanelAreas(prev => {
      const newAreas = { ...prev };
      
      // Remove from source area
      const sourceKey = sourceAreaId as keyof typeof prev;
      newAreas[sourceKey] = prev[sourceKey].filter(id => id !== panelId);
      
      // Add to target area
      const targetKey = targetAreaId as keyof typeof prev;
      newAreas[targetKey] = [...prev[targetKey], panelId];
      
      return newAreas;
    });
    
    // Set as active in target area
    setActivePanels(prev => ({
      ...prev,
      [targetAreaId]: panelId,
    }));
  }, []);

  // Get panels for a specific area
  const getPanelsForArea = useCallback((areaId: string): ICUIPanelInstance[] => {
    const areaKey = areaId as keyof typeof panelAreas;
    const areaPanelIds = panelAreas[areaKey] || [];
    return areaPanelIds.map(id => panels.find(p => p.id === id)).filter(Boolean) as ICUIPanelInstance[];
  }, [panelAreas, panels]);

  // Clear all panels
  const handleClearAll = useCallback(() => {
    panels.forEach(panel => actions.remove(panel.id));
    setPanelAreas({
      leftArea: [],
      centerArea: [],
      rightArea: [],
      bottomArea: [],
    });
    setActivePanels({});
  }, [panels, actions]);

  // Handle editor file operations
  const handleFileChange = useCallback((fileId: string, content: string) => {
    setEditorFiles(prev =>
      prev.map(file =>
        file.id === fileId
          ? { ...file, content, isModified: file.content !== content }
          : file
      )
    );
  }, []);

  const handleFileSelect = useCallback((fileId: string) => {
    setActiveFileId(fileId);
  }, []);

  const handleFileClose = useCallback((fileId: string) => {
    if (editorFiles.length === 1) return; // Don't close the last file

    const fileIndex = editorFiles.findIndex(f => f.id === fileId);
    if (fileIndex === -1) return;

    const newFiles = editorFiles.filter(f => f.id !== fileId);
    setEditorFiles(newFiles);

    // If we closed the active file, switch to the adjacent file
    if (activeFileId === fileId) {
      const newActiveIndex = fileIndex > 0 ? fileIndex - 1 : 0;
      setActiveFileId(newFiles[newActiveIndex]?.id || newFiles[0]?.id);
    }
  }, [editorFiles, activeFileId]);

  const handleNewFile = useCallback(() => {
    const newFile: FileData = {
      id: `file-${Date.now()}`,
      name: 'untitled.js',
      content: '// New file\n',
      isModified: true,
    };
    setEditorFiles(prev => [...prev, newFile]);
    setActiveFileId(newFile.id);
  }, []);

  // Handle code execution
  const handleRunCode = useCallback((code: string, language: string) => {
    console.log(`Executing ${language} code:`, code);
    // TODO: Integrate with actual code execution
  }, []);

  // Handle file explorer operations
  const handleExplorerFileSelect = useCallback((filePath: string) => {
    console.log('Explorer file selected:', filePath);
    // TODO: Load file into editor
  }, []);

  // Helper function to determine language from filename
  const getLanguageFromFileName = useCallback((fileName: string): SupportedLanguage => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'js':
      case 'jsx':
        return 'javascript';
      case 'py':
        return 'python';
      case 'ts':
      case 'tsx':
        return 'javascript'; // TypeScript will be treated as JavaScript for now
      default:
        return 'javascript';
    }
  }, []);

  // Render specialized panel content
  const renderPanelContent = useCallback((panel: ICUIPanelInstance) => {
    switch (panel.config.type) {
      case 'terminal':
        return (
          <ICUITerminalPanel />
        );
      
      case 'editor':
        const activeFile = editorFiles.find(f => f.id === activeFileId);
        return (
          <div className="flex flex-col h-full">
            {/* File tabs */}
            <div className="flex items-center border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
              {editorFiles.map((file) => (
                <div
                  key={file.id}
                  className={`px-3 py-2 text-sm cursor-pointer border-r border-gray-200 dark:border-gray-700 ${
                    file.id === activeFileId
                      ? 'bg-white dark:bg-gray-900 text-blue-600 dark:text-blue-400'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                  onClick={() => setActiveFileId(file.id)}
                >
                  {file.name}
                  {file.isModified && <span className="ml-1 text-orange-500">●</span>}
                  <button 
                    className="ml-2 text-gray-400 hover:text-red-500"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleFileClose(file.id);
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}
              <button 
                className="px-2 py-1 text-xs bg-blue-500 text-white rounded mx-2 hover:bg-blue-600"
                onClick={handleNewFile}
              >
                +
              </button>
            </div>
            {/* Code Editor */}
            <div className="flex-1 relative overflow-hidden">
              {activeFile && (
                <CodeEditor
                  code={activeFile.content}
                  language={getLanguageFromFileName(activeFile.name)}
                  onCodeChange={(newCode) => handleFileChange(activeFile.id, newCode)}
                  theme={theme}
                />
              )}
            </div>
          </div>
        );
      
      case 'explorer':
        return (
          <div className="flex flex-col h-full">
            {/* Explorer header */}
            <div className="flex items-center justify-between p-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
              <span className="text-sm font-medium">EXPLORER</span>
              <div className="flex gap-1">
                <button 
                  className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600" 
                  title="New File"
                  onClick={() => console.log('Create new file')}
                >
                  📄
                </button>
                <button 
                  className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600" 
                  title="New Folder"
                  onClick={() => console.log('Create new folder')}
                >
                  📁
                </button>
              </div>
            </div>
            {/* File tree */}
            <div className="flex-1 p-2 text-sm overflow-y-auto">
              <FileExplorer
                files={sampleExplorerFiles}
                onFileSelect={handleExplorerFileSelect}
                onFileCreate={(path) => console.log('Create file at:', path)}
                onFolderCreate={(path) => console.log('Create folder at:', path)}
                onFileDelete={(path) => console.log('Delete file at:', path)}
                onFileRename={(oldPath, newName) => console.log('Rename file:', oldPath, 'to:', newName)}
              />
            </div>
          </div>
        );
      
      default:
        return (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <div className="text-2xl mb-2">📋</div>
              <div>Panel content for {panel.config.type}</div>
            </div>
          </div>
        );
    }
  }, [editorFiles, activeFileId, handleFileChange, handleFileClose, handleNewFile, handleExplorerFileSelect, getLanguageFromFileName, theme]);

  return (
    <div className={`icui-test4-container p-4 ${className}`} style={{ height: '100vh', position: 'relative' }}>
      <h2 className="text-xl font-bold mb-4">ICUI Framework Test - Phase 4 (Specialized Panels)</h2>
      
      <div className="space-y-6">
        {/* Introduction */}
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded">
          <h3 className="text-lg font-semibold mb-2">Phase 4: Specialized Panel Implementations</h3>
          <p className="text-sm text-blue-800 dark:text-blue-200">
            Testing specialized panels (Terminal, Editor, Explorer) integrated with the docking system.
            Each panel extends BasePanel with specific functionality and works seamlessly in the IDE layout.
          </p>
        </div>

        {/* Panel Controls */}
        <div className="p-4 border border-gray-200 dark:border-gray-700 rounded">
          <h3 className="text-lg font-semibold mb-3">Layout Presets</h3>
          
          <div className="flex items-center gap-4 mb-4 flex-wrap">
            <button
              onClick={createIDELayout}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
            >
              Create IDE Layout
            </button>
            
            <button
              onClick={createMultiEditorLayout}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
            >
              Multi-Editor Layout
            </button>
            
            <button
              onClick={handleClearAll}
              className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
              disabled={panels.length === 0}
            >
              Clear All
            </button>

            <button
              onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
              className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 transition-colors"
            >
              {theme === 'light' ? '🌙 Dark' : '☀️ Light'} Theme
            </button>
          </div>
          
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Active Panels: {panels.length} | 
            Left: {panelAreas.leftArea.length} | 
            Center: {panelAreas.centerArea.length} | 
            Right: {panelAreas.rightArea.length} | 
            Bottom: {panelAreas.bottomArea.length}
          </div>
        </div>

        {/* IDE Layout with Specialized Panels */}
        <div className="h-96 border border-gray-300 dark:border-gray-600 rounded">
          <ICUIFrameContainer
            id="specialized-demo"
            config={{
              responsive: true,
              borderDetection: true,
              minPanelSize: { width: 200, height: 100 },
              resizeHandleSize: 8,
              snapThreshold: 20,
            }}
            className="h-full"
          >
            <ICUISplitPanel
              id="main-vertical-split"
              config={{
                direction: 'vertical',
                initialSplit: 75,
                minSize: 20,
                collapsible: true,
                resizable: true,
                snapThreshold: 10,
              }}
              className="h-full"
              firstPanel={
                /* Top Section: Explorer + Editor + Right Panel */
                <ICUISplitPanel
                  id="top-horizontal-split"
                  config={{
                    direction: 'horizontal',
                    initialSplit: 25,
                    minSize: 15,
                    collapsible: true,
                    resizable: true,
                    snapThreshold: 10,
                  }}
                  className="h-full"
                  firstPanel={
                    /* Left Panel Area (Explorer) */
                    <ICUIPanelArea
                      id="leftArea"
                      panels={getPanelsForArea('leftArea')}
                      activePanelId={activePanels.leftArea}
                      onPanelActivate={(panelId) => handlePanelActivate('leftArea', panelId)}
                      onPanelClose={(panelId) => handlePanelClose('leftArea', panelId)}
                      onDrop={(panelId, sourceAreaId) => handlePanelDrop('leftArea', panelId, sourceAreaId)}
                      renderPanelContent={renderPanelContent}
                    />
                  }
                  secondPanel={
                    <ICUISplitPanel
                      id="center-right-split"
                      config={{
                        direction: 'horizontal',
                        initialSplit: 75,
                        minSize: 25,
                        collapsible: true,
                        resizable: true,
                        snapThreshold: 10,
                      }}
                      className="h-full"
                      firstPanel={
                        /* Center Panel Area (Editor) */
                        <ICUIPanelArea
                          id="centerArea"
                          panels={getPanelsForArea('centerArea')}
                          activePanelId={activePanels.centerArea}
                          onPanelActivate={(panelId) => handlePanelActivate('centerArea', panelId)}
                          onPanelClose={(panelId) => handlePanelClose('centerArea', panelId)}
                          onDrop={(panelId, sourceAreaId) => handlePanelDrop('centerArea', panelId, sourceAreaId)}
                          renderPanelContent={renderPanelContent}
                        />
                      }
                      secondPanel={
                        /* Right Panel Area */
                        <ICUIPanelArea
                          id="rightArea"
                          panels={getPanelsForArea('rightArea')}
                          activePanelId={activePanels.rightArea}
                          onPanelActivate={(panelId) => handlePanelActivate('rightArea', panelId)}
                          onPanelClose={(panelId) => handlePanelClose('rightArea', panelId)}
                          onDrop={(panelId, sourceAreaId) => handlePanelDrop('rightArea', panelId, sourceAreaId)}
                          renderPanelContent={renderPanelContent}
                        />
                      }
                    />
                  }
                />
              }
              secondPanel={
                /* Bottom Panel Area (Terminal/Output) */
                <ICUIPanelArea
                  id="bottomArea"
                  panels={getPanelsForArea('bottomArea')}
                  activePanelId={activePanels.bottomArea}
                  onPanelActivate={(panelId) => handlePanelActivate('bottomArea', panelId)}
                  onPanelClose={(panelId) => handlePanelClose('bottomArea', panelId)}
                  onDrop={(panelId, sourceAreaId) => handlePanelDrop('bottomArea', panelId, sourceAreaId)}
                  renderPanelContent={renderPanelContent}
                />
              }
            />
          </ICUIFrameContainer>
        </div>

        {/* Feature Status */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 border border-gray-200 dark:border-gray-700 rounded">
            <h4 className="font-semibold mb-2">Step 4.1: Terminal Panel</h4>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Specialized terminal with WebSocket connectivity
            </p>
            <div className="text-xs text-green-600 dark:text-green-400">✅ Implemented</div>
          </div>

          <div className="p-4 border border-gray-200 dark:border-gray-700 rounded">
            <h4 className="font-semibold mb-2">Step 4.2: Editor Panel</h4>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Code editor with tabs and language support
            </p>
            <div className="text-xs text-green-600 dark:text-green-400">✅ Implemented</div>
          </div>

          <div className="p-4 border border-gray-200 dark:border-gray-700 rounded">
            <h4 className="font-semibold mb-2">Step 4.3: Explorer Panel</h4>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              File explorer with operations
            </p>
            <div className="text-xs text-green-600 dark:text-green-400">✅ Implemented</div>
          </div>
        </div>

        {/* Navigation */}
        <div className="pt-4 border-t border-gray-200 dark:border-gray-600">
          <div className="flex justify-between items-center">
            <a 
              href="/icui-test3" 
              className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
            >
              ← Phase 3 Tests
            </a>
            <div className="text-sm text-gray-500">
              Phase 4 - Specialized Panel Implementations
            </div>
            <div className="px-4 py-2 bg-gray-300 text-gray-500 rounded cursor-not-allowed">
              Phase 5 Tests →
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ICUITest4;
