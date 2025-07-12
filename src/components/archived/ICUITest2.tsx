/**
 * ICUI Framework Test Component - Phase 2
 * Demonstrates Base Panel Component and Panel System functionality
 */

import React, { useState } from 'react';
import { 
  ICUIBasePanel, 
  ICUIFrameContainer,
  ICUISplitPanel,
  useICUIPanels, 
  createPanel,
  ICUIPanelType 
} from '../../icui';

interface ICUITest2Props {
  className?: string;
}

/**
 * Test component for ICUI Framework Phase 2
 * Shows Base Panel Component (2.1), Panel Header System (2.2), and Panel Content Container (2.3)
 * Also demonstrates integration with split frames from Phase 1.2
 */
export const ICUITest2: React.FC<ICUITest2Props> = ({ className = '' }) => {
  const { panels, activePanel, actions } = useICUIPanels();
  const [selectedType, setSelectedType] = useState<ICUIPanelType>('editor');
  const [showInSplitFrame, setShowInSplitFrame] = useState(false);

  // Create a new panel
  const handleCreatePanel = () => {
    const config = createPanel(selectedType, {
      title: `New ${selectedType.charAt(0).toUpperCase() + selectedType.slice(1)} Panel`,
    });
    actions.create(config);
  };

  // Remove all panels
  const handleClearPanels = () => {
    panels.forEach(panel => actions.remove(panel.id));
  };

  // Create default demo panels for split frame
  const createDemoPanels = () => {
    const editorConfig = createPanel('editor', { title: 'Code Editor' });
    const terminalConfig = createPanel('terminal', { title: 'Terminal' });
    const explorerConfig = createPanel('explorer', { title: 'File Explorer' });
    
    actions.create(editorConfig);
    actions.create(terminalConfig);
    actions.create(explorerConfig);
  };

  // Panel content for split frame demo
  const renderPanelContent = (panel: any) => (
    <div className="space-y-2">
      <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
        <h4 className="font-medium mb-1">{panel.config.type.charAt(0).toUpperCase() + panel.config.type.slice(1)} Panel</h4>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Panel within split frame - drag the header to move, use resize handles to resize.
        </p>
      </div>
      <div className="text-xs text-gray-500">
        ID: {panel.id.split('-').pop()}<br />
        State: {panel.state}<br />
        Size: {panel.position.width} × {panel.position.height}
      </div>
    </div>
  );

  return (
    <div className={`icui-test2-container p-4 ${className}`} style={{ height: '100vh', position: 'relative' }}>
      <h2 className="text-xl font-bold mb-4">ICUI Framework Test - Phase 2 (v2.0.0)</h2>
      
      <div className="space-y-6">
        {/* Introduction */}
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded">
          <h3 className="text-lg font-semibold mb-2">Phase 2: Generic Panel Base Class</h3>
          <p className="text-sm text-blue-800 dark:text-blue-200">
            Testing base panel components with improved drag/drop, resizing, and integration with split frames.
            Click "Show in Split Frame" to see panels working within the Phase 1.2 split system.
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
              onClick={handleClearPanels}
              className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
              disabled={panels.length === 0}
            >
              Clear All
            </button>

            <button
              onClick={() => setShowInSplitFrame(!showInSplitFrame)}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
            >
              {showInSplitFrame ? 'Hide Split Frame' : 'Show in Split Frame'}
            </button>

            {showInSplitFrame && panels.length === 0 && (
              <button
                onClick={createDemoPanels}
                className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 transition-colors"
              >
                Create Demo Panels
              </button>
            )}
          </div>
          
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Active Panels: {panels.length} | Active Panel: {activePanel?.config.title || 'None'}
          </div>
        </div>

        {/* Split Frame Integration Demo */}
        {showInSplitFrame ? (
          <div className="h-96 border border-gray-300 dark:border-gray-600 rounded">
            <ICUIFrameContainer
              id="split-frame-demo"
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
                id="main-split"
                config={{
                  direction: 'horizontal',
                  initialSplit: 70,
                  minSize: 10,
                  collapsible: true,
                  resizable: true,
                  snapThreshold: 10,
                }}
                className="h-full"
                firstPanel={
                  /* Left Panel Container */
                  <div className="relative h-full bg-gray-100 dark:bg-gray-800">
                    <div className="p-2 text-sm font-medium bg-gray-200 dark:bg-gray-700">
                      Main Area - Drag panels here
                    </div>
                    <div className="relative h-full">
                      {panels.filter(p => p.config.type === 'editor').map((panel) => (
                        <ICUIBasePanel
                          key={panel.id}
                          panel={panel}
                          onStateChange={(state) => actions.setState(panel.id, state)}
                          onPositionChange={(position) => actions.setPosition(panel.id, position)}
                          onConfigChange={(config) => actions.update(panel.id, { config: { ...panel.config, ...config } })}
                          onClose={() => actions.remove(panel.id)}
                          headerProps={{ editable: true, showControls: true }}
                          contentProps={{ padding: true, scrollable: true }}
                        >
                          {renderPanelContent(panel)}
                        </ICUIBasePanel>
                      ))}
                    </div>
                  </div>
                }
                secondPanel={
                  /* Right Panel Container */
                  <ICUISplitPanel
                    id="right-split"
                    config={{
                      direction: 'vertical',
                      initialSplit: 50,
                      minSize: 10,
                      collapsible: true,
                      resizable: true,
                      snapThreshold: 10,
                    }}
                    className="h-full"
                    firstPanel={
                      /* Top Right */
                      <div className="relative h-full bg-blue-50 dark:bg-blue-900/20">
                        <div className="p-2 text-sm font-medium bg-blue-200 dark:bg-blue-800">
                          Explorer Area
                        </div>
                        <div className="relative h-full">
                          {panels.filter(p => p.config.type === 'explorer').map((panel) => (
                            <ICUIBasePanel
                              key={panel.id}
                              panel={panel}
                              onStateChange={(state) => actions.setState(panel.id, state)}
                              onPositionChange={(position) => actions.setPosition(panel.id, position)}
                              onConfigChange={(config) => actions.update(panel.id, { config: { ...panel.config, ...config } })}
                              onClose={() => actions.remove(panel.id)}
                              headerProps={{ editable: true, showControls: true }}
                              contentProps={{ padding: true, scrollable: true }}
                            >
                              {renderPanelContent(panel)}
                            </ICUIBasePanel>
                          ))}
                        </div>
                      </div>
                    }
                    secondPanel={
                      /* Bottom Right */
                      <div className="relative h-full bg-green-50 dark:bg-green-900/20">
                        <div className="p-2 text-sm font-medium bg-green-200 dark:bg-green-800">
                          Terminal Area
                        </div>
                        <div className="relative h-full">
                          {panels.filter(p => p.config.type === 'terminal').map((panel) => (
                            <ICUIBasePanel
                              key={panel.id}
                              panel={panel}
                              onStateChange={(state) => actions.setState(panel.id, state)}
                              onPositionChange={(position) => actions.setPosition(panel.id, position)}
                              onConfigChange={(config) => actions.update(panel.id, { config: { ...panel.config, ...config } })}
                              onClose={() => actions.remove(panel.id)}
                              headerProps={{ editable: true, showControls: true }}
                              contentProps={{ padding: true, scrollable: true }}
                            >
                              {renderPanelContent(panel)}
                            </ICUIBasePanel>
                          ))}
                        </div>
                      </div>
                    }
                  />
                }
              />
            </ICUIFrameContainer>
          </div>
        ) : (
          /* Regular Panel Demo */
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border border-gray-200 dark:border-gray-700 rounded">
              <h4 className="font-semibold mb-2">Step 2.1: Base Panel</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                Improved drag with mouse events, better resize handles
              </p>
              <div className="text-xs text-green-600 dark:text-green-400">✅ Fixed Dragging</div>
            </div>

            <div className="p-4 border border-gray-200 dark:border-gray-700 rounded">
              <h4 className="font-semibold mb-2">Step 2.2: Panel Header</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                Mouse-based dragging, improved controls
              </p>
              <div className="text-xs text-green-600 dark:text-green-400">✅ Fixed Dragging</div>
            </div>

            <div className="p-4 border border-gray-200 dark:border-gray-700 rounded">
              <h4 className="font-semibold mb-2">Step 2.3: Split Integration</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                Panels working within split frames
              </p>
              <div className="text-xs text-green-600 dark:text-green-400">✅ Integrated</div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="pt-4 border-t border-gray-200 dark:border-gray-600">
          <div className="flex justify-between items-center">
            <a 
              href="/icui-test" 
              className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
            >
              ← Phase 1 Tests
            </a>
            <div className="text-sm text-gray-500">
              Phase 2 - Generic Panel Base Class (Fixed Dragging)
            </div>
            <div className="px-4 py-2 bg-gray-300 text-gray-500 rounded cursor-not-allowed">
              Phase 3 Tests →
            </div>
          </div>
        </div>
      </div>

      {/* Render floating panels when not in split frame mode */}
      {!showInSplitFrame && panels.map((panel) => (
        <ICUIBasePanel
          key={panel.id}
          panel={panel}
          onStateChange={(state) => actions.setState(panel.id, state)}
          onPositionChange={(position) => actions.setPosition(panel.id, position)}
          onConfigChange={(config) => actions.update(panel.id, { config: { ...panel.config, ...config } })}
          onClose={() => actions.remove(panel.id)}
          headerProps={{ editable: true, showControls: true }}
          contentProps={{ padding: true, scrollable: true }}
        >
          <div className="space-y-4">
            <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded">
              <h4 className="font-medium mb-2">{panel.config.type.charAt(0).toUpperCase() + panel.config.type.slice(1)} Panel Content</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                This is a demo {panel.config.type} panel. You can:
              </p>
              <ul className="text-sm text-gray-600 dark:text-gray-400 list-disc list-inside space-y-1">
                <li>Drag the header to move the panel (fixed mouse dragging)</li>
                <li>Double-click the title to edit it</li>
                <li>Click the emoji icon to change the panel type</li>
                <li>Use the control buttons to minimize, maximize, or close</li>
                <li>Drag the resize handles to resize the panel (improved)</li>
              </ul>
            </div>
            
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded text-sm">
              <strong>Panel Info:</strong><br />
              ID: {panel.id}<br />
              State: {panel.state}<br />
              Position: {panel.position.x}, {panel.position.y}<br />
              Size: {panel.position.width} × {panel.position.height}<br />
              Z-Index: {panel.position.zIndex}
            </div>
            
            <button
              onClick={() => actions.clone(panel.id)}
              className="w-full px-3 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors text-sm"
            >
              Clone This Panel
            </button>
          </div>
        </ICUIBasePanel>
      ))}
    </div>
  );
};

export default ICUITest2;
