/**
 * ICUI Layout Menu Test Page
 * 
 * Test page for the LayoutMenu component demonstrating all functionality
 * including layout templates, presets, custom layouts, panel creation,
 * and integration with the ICUILayoutStateManager.
 */

import React, { useState, useCallback } from 'react';
import { LayoutMenu } from '../menus/LayoutMenu';
import { ICUILayoutState } from '../../types/icui-layout-state';
import { notificationService } from '../../services/notificationService';
import '../../styles/LayoutMenu.css';

// Mock current layout for testing
const createMockLayout = (): ICUILayoutState => ({
  id: 'test-layout',
  name: 'Test Layout',
  type: 'default',
  version: '1.0.0',
  createdAt: new Date().toISOString(),
  modifiedAt: new Date().toISOString(),
  frameConfig: {
    id: 'main-frame',
    responsive: true,
    borderDetection: true,
    minPanelSize: { width: 200, height: 100 },
    resizeHandleSize: 8,
    snapThreshold: 20,
  },
  splitConfigs: {
    'main-split': {
      id: 'main-split',
      direction: 'horizontal',
      initialSplit: 50,
      minSize: 2,
      collapsible: true,
      resizable: true,
      snapThreshold: 10,
    },
  },
  panelStates: {
    'left-panel': {
      id: 'left-panel',
      type: 'explorer',
      visible: true,
      collapsed: false,
      size: { width: 300, height: 600 },
      position: { x: 0, y: 0 },
      splitParent: 'main-split',
      splitPosition: 25,
    },
    'right-panel': {
      id: 'right-panel',
      type: 'editor',
      visible: true,
      collapsed: false,
      size: { width: 900, height: 600 },
      position: { x: 300, y: 0 },
      splitParent: 'main-split',
      splitPosition: 75,
    },
  },
});

export const ICUILayoutMenuTest: React.FC = () => {
  const [currentLayout, setCurrentLayout] = useState<ICUILayoutState>(createMockLayout());
  const [layoutHistory, setLayoutHistory] = useState<ICUILayoutState[]>([createMockLayout()]);
  const [panels, setPanels] = useState<Array<{ id: string; type: string; position: string }>>([
    { id: 'left-panel', type: 'explorer', position: 'left' },
    { id: 'right-panel', type: 'editor', position: 'right' }
  ]);

  /**
   * Handle layout change
   */
  const handleLayoutChange = useCallback((layout: ICUILayoutState) => {
    setCurrentLayout(layout);
    setLayoutHistory(prev => [...prev, layout]);
    notificationService.show(`Layout changed to: ${layout.name}`, 'success');
  }, []);

  /**
   * Handle layout reset
   */
  const handleLayoutReset = useCallback(() => {
    const defaultLayout = createMockLayout();
    setCurrentLayout(defaultLayout);
    setLayoutHistory(prev => [...prev, defaultLayout]);
    setPanels([
      { id: 'left-panel', type: 'explorer', position: 'left' },
      { id: 'right-panel', type: 'editor', position: 'right' }
    ]);
    notificationService.show('Layout reset to default', 'success');
  }, []);

  /**
   * Handle panel creation
   */
  const handlePanelCreate = useCallback((panelType: string, position: string = 'right') => {
    const newPanel = {
      id: `${panelType}-${Date.now()}`,
      type: panelType,
      position
    };
    
    setPanels(prev => [...prev, newPanel]);
    
    // Update current layout with new panel
    const updatedLayout: ICUILayoutState = {
      ...currentLayout,
      modifiedAt: new Date().toISOString(),
      panelStates: {
        ...currentLayout.panelStates,
        [newPanel.id]: {
          id: newPanel.id,
          type: panelType,
          visible: true,
          collapsed: false,
          size: { width: 400, height: 300 },
          position: { x: position === 'right' ? 600 : 0, y: 0 },
        }
      }
    };
    
    setCurrentLayout(updatedLayout);
    setLayoutHistory(prev => [...prev, updatedLayout]);
    notificationService.show(`Created ${panelType} panel`, 'success');
  }, [currentLayout]);

  /**
   * Handle layout save
   */
  const handleLayoutSave = useCallback((name: string, layout: ICUILayoutState) => {
    notificationService.show(`Custom layout "${name}" saved`, 'success');
  }, []);

  /**
   * Handle layout delete
   */
  const handleLayoutDelete = useCallback((presetId: string) => {
    notificationService.show(`Layout deleted: ${presetId}`, 'success');
  }, []);

  /**
   * Handle layout export
   */
  const handleLayoutExport = useCallback((layout: ICUILayoutState) => {
    // Simulate export by downloading JSON
    const dataStr = JSON.stringify(layout, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `${layout.name.toLowerCase().replace(/\s+/g, '-')}-layout.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    notificationService.show('Layout exported successfully', 'success');
  }, []);

  /**
   * Handle layout import
   */
  const handleLayoutImport = useCallback(() => {
    // Simulate import by creating file input
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
          try {
            const layoutData = JSON.parse(event.target?.result as string);
            const importedLayout: ICUILayoutState = {
              ...layoutData,
              id: `imported-${Date.now()}`,
              createdAt: new Date().toISOString(),
              modifiedAt: new Date().toISOString(),
            };
            
            setCurrentLayout(importedLayout);
            setLayoutHistory(prev => [...prev, importedLayout]);
            notificationService.show(`Layout imported: ${importedLayout.name}`, 'success');
          } catch (error) {
            notificationService.show('Failed to import layout: Invalid JSON', 'error');
          }
        };
        reader.readAsText(file);
      }
    };
    
    input.click();
  }, []);

  /**
   * Remove a panel
   */
  const handleRemovePanel = useCallback((panelId: string) => {
    setPanels(prev => prev.filter(p => p.id !== panelId));
    
    // Update current layout
    const updatedLayout: ICUILayoutState = {
      ...currentLayout,
      modifiedAt: new Date().toISOString(),
      panelStates: Object.fromEntries(
        Object.entries(currentLayout.panelStates).filter(([id]) => id !== panelId)
      )
    };
    
    setCurrentLayout(updatedLayout);
    setLayoutHistory(prev => [...prev, updatedLayout]);
    notificationService.show(`Panel removed: ${panelId}`, 'success');
  }, [currentLayout]);

  return (
    <div className="icui-layout-menu-test">
      <h1>ICUI Layout Menu Test</h1>
      
      <div className="test-layout">
        {/* Layout Menu */}
        <div className="test-section">
          <h2>Layout Menu</h2>
          <div className="layout-menu-container">
            <LayoutMenu
              currentLayout={currentLayout}
              onLayoutChange={handleLayoutChange}
              onLayoutReset={handleLayoutReset}
              onPanelCreate={handlePanelCreate}
              onLayoutSave={handleLayoutSave}
              onLayoutDelete={handleLayoutDelete}
              onLayoutExport={handleLayoutExport}
              onLayoutImport={handleLayoutImport}
            />
          </div>
        </div>

        {/* Current State Display */}
        <div className="test-section">
          <h2>Current Layout State</h2>
          
          <div className="state-info">
            <div className="info-item">
              <strong>Layout ID:</strong> {currentLayout.id}
            </div>
            
            <div className="info-item">
              <strong>Layout Name:</strong> {currentLayout.name}
            </div>
            
            <div className="info-item">
              <strong>Layout Type:</strong> {currentLayout.type}
            </div>
            
            <div className="info-item">
              <strong>Last Modified:</strong> {new Date(currentLayout.modifiedAt).toLocaleString()}
            </div>
            
            <div className="info-item">
              <strong>Panel Count:</strong> {Object.keys(currentLayout.panelStates).length}
            </div>
          </div>
        </div>

        {/* Current Panels */}
        <div className="test-section">
          <h2>Current Panels</h2>
          
          <div className="panels-list">
            {panels.map(panel => (
              <div key={panel.id} className="panel-item">
                <span className="panel-icon">
                  {panel.type === 'editor' && '📝'}
                  {panel.type === 'terminal' && '💻'}
                  {panel.type === 'explorer' && '📁'}
                  {panel.type === 'output' && '📄'}
                  {panel.type === 'browser' && '🌐'}
                  {panel.type === 'preview' && '👁️'}
                  {!['editor', 'terminal', 'explorer', 'output', 'browser', 'preview'].includes(panel.type) && '⚪'}
                </span>
                <span className="panel-info">
                  <span className="panel-name">{panel.type} ({panel.id})</span>
                  <span className="panel-position">Position: {panel.position}</span>
                </span>
                <button
                  className="panel-remove-btn"
                  onClick={() => handleRemovePanel(panel.id)}
                  title="Remove panel"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Layout History */}
        <div className="test-section">
          <h2>Layout History</h2>
          <p>Total changes: {layoutHistory.length}</p>
          
          <div className="history-list">
            {layoutHistory.slice(-5).reverse().map((layout, index) => (
              <div key={`${layout.id}-${layout.modifiedAt}`} className="history-item">
                <span className="history-index">{layoutHistory.length - index}</span>
                <span className="history-info">
                  <span className="history-name">{layout.name}</span>
                  <span className="history-time">{new Date(layout.modifiedAt).toLocaleTimeString()}</span>
                </span>
                <button
                  className="history-restore-btn"
                  onClick={() => handleLayoutChange(layout)}
                  title="Restore this layout"
                >
                  ↻
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      <style>{`
        .icui-layout-menu-test {
          padding: 20px;
          max-width: 1400px;
          margin: 0 auto;
          font-family: ui-sans-serif, system-ui, sans-serif;
        }

        .test-layout {
          display: grid;
          grid-template-columns: 350px 1fr;
          gap: 20px;
          margin-top: 20px;
        }

        .test-section {
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          padding: 16px;
          height: fit-content;
        }

        .test-section h2 {
          margin: 0 0 12px 0;
          font-size: 16px;
          font-weight: 600;
          color: #111827;
        }

        .layout-menu-container {
          display: inline-block;
        }

        .state-info {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .info-item {
          font-size: 14px;
          color: #374151;
          padding: 4px 0;
          border-bottom: 1px solid #e5e7eb;
        }

        .info-item:last-child {
          border-bottom: none;
        }

        .info-item strong {
          color: #111827;
          display: inline-block;
          width: 120px;
        }

        .panels-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .panel-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px;
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          background: white;
        }

        .panel-icon {
          font-size: 18px;
          width: 24px;
          text-align: center;
        }

        .panel-info {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .panel-name {
          font-weight: 500;
          color: #111827;
        }

        .panel-position {
          font-size: 12px;
          color: #6b7280;
        }

        .panel-remove-btn {
          background: transparent;
          border: none;
          color: #dc2626;
          cursor: pointer;
          padding: 4px;
          border-radius: 4px;
          font-size: 12px;
        }

        .panel-remove-btn:hover {
          background: #fef2f2;
        }

        .history-list {
          display: flex;
          flex-direction: column;
          gap: 6px;
          max-height: 300px;
          overflow-y: auto;
        }

        .history-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 8px 12px;
          border: 1px solid #e5e7eb;
          border-radius: 4px;
          background: white;
          font-size: 13px;
        }

        .history-index {
          background: #f3f4f6;
          color: #6b7280;
          padding: 2px 6px;
          border-radius: 3px;
          font-size: 11px;
          font-weight: 600;
          min-width: 20px;
          text-align: center;
        }

        .history-info {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .history-name {
          font-weight: 500;
          color: #111827;
        }

        .history-time {
          font-size: 11px;
          color: #9ca3af;
        }

        .history-restore-btn {
          background: transparent;
          border: none;
          color: #3b82f6;
          cursor: pointer;
          padding: 4px;
          border-radius: 4px;
          font-size: 14px;
        }

        .history-restore-btn:hover {
          background: #dbeafe;
        }

        /* Dark theme support */
        [data-theme="dark"] .test-section {
          background: #1f2937;
          border-color: #374151;
        }

        [data-theme="dark"] .test-section h2 {
          color: #f9fafb;
        }

        [data-theme="dark"] .info-item {
          color: #d1d5db;
          border-bottom-color: #374151;
        }

        [data-theme="dark"] .info-item strong {
          color: #f9fafb;
        }

        [data-theme="dark"] .panel-item,
        [data-theme="dark"] .history-item {
          background: #374151;
          border-color: #4b5563;
        }

        [data-theme="dark"] .panel-name,
        [data-theme="dark"] .history-name {
          color: #f9fafb;
        }

        [data-theme="dark"] .panel-position,
        [data-theme="dark"] .history-time {
          color: #9ca3af;
        }

        [data-theme="dark"] .history-index {
          background: #4b5563;
          color: #d1d5db;
        }

        @media (max-width: 1024px) {
          .test-layout {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
};

export default ICUILayoutMenuTest;
