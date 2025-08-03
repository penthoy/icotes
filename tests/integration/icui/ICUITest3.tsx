/**
 * ICUI Framework Test Component - Phase 3 (Docking System)
 * Demonstrates Panel Area Component and Docked Panel functionality
 */

import React, { useState, useCallback } from 'react';
import { 
  ICUIFrameContainer,
  ICUISplitPanel,
  useICUIPanels, 
  createPanel,
  ICUIPanelType,
  ICUIPanelInstance
} from '../../../src/icui';
import { ICUIPanelArea } from '../../../src/icui/components/archived/ICUIPanelArea_deprecated';

interface ICUITest3Props {
  className?: string;
}

/**
 * Test component for ICUI Framework Phase 3
 * Shows Panel Area (3.1), Docking System (3.2), and Enhanced Dragging (3.3)
 */
export const ICUITest3: React.FC<ICUITest3Props> = ({ className = '' }) => {
  const { panels, actions } = useICUIPanels();
  const [selectedType, setSelectedType] = useState<ICUIPanelType>('editor');
  
  // Panel area state - tracking which panels are in which areas
  const [panelAreas, setPanelAreas] = useState<{
    leftArea: string[];
    centerArea: string[];
    rightTopArea: string[];
    rightBottomArea: string[];
  }>({
    leftArea: [],
    centerArea: [],
    rightTopArea: [],
    rightBottomArea: [],
  });

  // Active panel per area
  const [activePanels, setActivePanels] = useState<{
    leftArea?: string;
    centerArea?: string;
    rightTopArea?: string;
    rightBottomArea?: string;
  }>({});

  // Create a new panel and add it to center area by default
  const handleCreatePanel = useCallback(() => {
    const config = createPanel(selectedType, {
      title: `${selectedType.charAt(0).toUpperCase() + selectedType.slice(1)} ${Date.now()}`,
    });
    const newPanel = actions.create(config);
    
    // Add to center area by default
    setPanelAreas(prev => ({
      ...prev,
      centerArea: [...prev.centerArea, newPanel.id],
    }));
    
    // Set as active panel in center area
    setActivePanels(prev => ({
      ...prev,
      centerArea: newPanel.id,
    }));
  }, [selectedType, actions]);

  // Create demo layout
  const createDemoLayout = useCallback(() => {
    // Clear existing panels
    panels.forEach(panel => actions.remove(panel.id));
    
    // Create demo panels
    const explorerPanel = actions.create(createPanel('explorer', { title: 'File Explorer' }));
    const editorPanel1 = actions.create(createPanel('editor', { title: 'App.tsx' }));
    const editorPanel2 = actions.create(createPanel('editor', { title: 'main.tsx' }));
    const terminalPanel = actions.create(createPanel('terminal', { title: 'Terminal' }));
    const outputPanel = actions.create(createPanel('output', { title: 'Output' }));
    
    // Assign to areas
    setPanelAreas({
      leftArea: [explorerPanel.id],
      centerArea: [editorPanel1.id, editorPanel2.id],
      rightTopArea: [outputPanel.id],
      rightBottomArea: [terminalPanel.id],
    });
    
    // Set active panels
    setActivePanels({
      leftArea: explorerPanel.id,
      centerArea: editorPanel1.id,
      rightTopArea: outputPanel.id,
      rightBottomArea: terminalPanel.id,
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
      rightTopArea: [],
      rightBottomArea: [],
    });
    setActivePanels({});
  }, [panels, actions]);

  return (
    <div className={`icui-test3-container p-4 ${className}`} style={{ height: '100vh', position: 'relative' }}>
      <h2 className="text-xl font-bold mb-4">ICUI Framework Test - Phase 3 (Docking System)</h2>
      
      <div className="space-y-6">
        {/* Introduction */}
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded">
          <h3 className="text-lg font-semibold mb-2">Phase 3: Panel Docking and Tabbing System</h3>
          <p className="text-sm text-green-800 dark:text-green-200">
            Testing docked panel areas with tabbed interfaces. Panels can be dragged between areas!
            This demonstrates the foundation for IDE-style docked panels.
          </p>
        </div>

        {/* Panel Controls */}
        <div className="p-4 border border-gray-200 dark:border-gray-700 rounded">
          <h3 className="text-lg font-semibold mb-3">Panel Controls</h3>
          
          <div className="flex items-center gap-4 mb-4 flex-wrap">
            <select 
              value={selectedType} 
              onChange={(e) => setSelectedType(e.target.value as ICUIPanelType)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800"
            >
              <option value="terminal">Terminal</option>
              <option value="editor">Editor</option>
              <option value="explorer">Explorer</option>
              <option value="output">Output</option>
              <option value="properties">Properties</option>
              <option value="timeline">Timeline</option>
              <option value="inspector">Inspector</option>
              <option value="custom">Custom</option>
            </select>
            
            <button
              onClick={handleCreatePanel}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
            >
              Create Panel
            </button>
            
            <button
              onClick={createDemoLayout}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
            >
              Create Demo Layout
            </button>
            
            <button
              onClick={handleClearAll}
              className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
              disabled={panels.length === 0}
            >
              Clear All
            </button>
          </div>
          
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Total Panels: {panels.length} | 
            Left: {panelAreas.leftArea.length} | 
            Center: {panelAreas.centerArea.length} | 
            Right Top: {panelAreas.rightTopArea.length} | 
            Right Bottom: {panelAreas.rightBottomArea.length}
          </div>
        </div>

        {/* Docked Panel Layout */}
        <div className="h-96 border border-gray-300 dark:border-gray-600 rounded">
          <ICUIFrameContainer
            id="docking-demo"
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
              id="main-horizontal-split"
              config={{
                direction: 'horizontal',
                initialSplit: 20,
                minSize: 15,
                collapsible: true,
                resizable: true,
                snapThreshold: 10,
              }}
              className="h-full"
              firstPanel={
                /* Left Panel Area */
                <ICUIPanelArea
                  id="leftArea"
                  panels={getPanelsForArea('leftArea')}
                  activePanelId={activePanels.leftArea}
                  onPanelActivate={(panelId) => handlePanelActivate('leftArea', panelId)}
                  onPanelClose={(panelId) => handlePanelClose('leftArea', panelId)}
                  onDrop={(panelId, sourceAreaId) => handlePanelDrop('leftArea', panelId, sourceAreaId)}
                />
              }
              secondPanel={
                <ICUISplitPanel
                  id="center-right-split"
                  config={{
                    direction: 'horizontal',
                    initialSplit: 70,
                    minSize: 30,
                    collapsible: true,
                    resizable: true,
                    snapThreshold: 10,
                  }}
                  className="h-full"
                  firstPanel={
                    /* Center Panel Area */
                    <ICUIPanelArea
                      id="centerArea"
                      panels={getPanelsForArea('centerArea')}
                      activePanelId={activePanels.centerArea}
                      onPanelActivate={(panelId) => handlePanelActivate('centerArea', panelId)}
                      onPanelClose={(panelId) => handlePanelClose('centerArea', panelId)}
                      onDrop={(panelId, sourceAreaId) => handlePanelDrop('centerArea', panelId, sourceAreaId)}
                    />
                  }
                  secondPanel={
                    /* Right Panel Area with vertical split */
                    <ICUISplitPanel
                      id="right-vertical-split"
                      config={{
                        direction: 'vertical',
                        initialSplit: 50,
                        minSize: 20,
                        collapsible: true,
                        resizable: true,
                        snapThreshold: 10,
                      }}
                      className="h-full"
                      firstPanel={
                        /* Right Top Panel Area */
                        <ICUIPanelArea
                          id="rightTopArea"
                          panels={getPanelsForArea('rightTopArea')}
                          activePanelId={activePanels.rightTopArea}
                          onPanelActivate={(panelId) => handlePanelActivate('rightTopArea', panelId)}
                          onPanelClose={(panelId) => handlePanelClose('rightTopArea', panelId)}
                          onDrop={(panelId, sourceAreaId) => handlePanelDrop('rightTopArea', panelId, sourceAreaId)}
                        />
                      }
                      secondPanel={
                        /* Right Bottom Panel Area */
                        <ICUIPanelArea
                          id="rightBottomArea"
                          panels={getPanelsForArea('rightBottomArea')}
                          activePanelId={activePanels.rightBottomArea}
                          onPanelActivate={(panelId) => handlePanelActivate('rightBottomArea', panelId)}
                          onPanelClose={(panelId) => handlePanelClose('rightBottomArea', panelId)}
                          onDrop={(panelId, sourceAreaId) => handlePanelDrop('rightBottomArea', panelId, sourceAreaId)}
                        />
                      }
                    />
                  }
                />
              }
            />
          </ICUIFrameContainer>
        </div>

        {/* Feature Status */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 border border-gray-200 dark:border-gray-700 rounded">
            <h4 className="font-semibold mb-2">Step 3.1: Panel Areas</h4>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Dockable containers with tab support
            </p>
            <div className="text-xs text-green-600 dark:text-green-400">✅ Implemented</div>
          </div>

          <div className="p-4 border border-gray-200 dark:border-gray-700 rounded">
            <h4 className="font-semibold mb-2">Step 3.2: Dock Manager</h4>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Panel-to-area assignment system
            </p>
            <div className="text-xs text-green-600 dark:text-green-400">✅ Basic Implementation</div>
          </div>

          <div className="p-4 border border-gray-200 dark:border-gray-700 rounded">
            <h4 className="font-semibold mb-2">Step 3.3: Enhanced Dragging</h4>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Drag panels between areas
            </p>
            <div className="text-xs text-green-600 dark:text-green-400">✅ Tab Dragging</div>
          </div>

          <div className="p-4 border border-gray-200 dark:border-gray-700 rounded">
            <h4 className="font-semibold mb-2">Step 3.4: Split Integration</h4>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Panel areas in split frames
            </p>
            <div className="text-xs text-green-600 dark:text-green-400">✅ Working</div>
          </div>
        </div>

        {/* Navigation */}
        <div className="pt-4 border-t border-gray-200 dark:border-gray-600">
          <div className="flex justify-between items-center">
            <a 
              href="/icui-test2" 
              className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
            >
              ← Phase 2 Tests
            </a>
            <div className="text-sm text-gray-500">
              Phase 3 - Panel Docking System (IDE Foundation)
            </div>
            <a 
              href="/icui-test4" 
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
            >
              Phase 4 Tests →
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ICUITest3;
