/**
 * ICUI Framework - Panel Area Component
 * Container that holds docked panels with tab support
 */

import React, { useState, useCallback, useRef } from 'react';
import { ICUIBasePanel } from './ICUIBasePanel';
import { ICUIPanelInstance } from '../types/icui-panel';

export interface ICUIPanelAreaProps {
  id: string;
  panels: ICUIPanelInstance[];
  activePanelId?: string;
  className?: string;
  style?: React.CSSProperties;
  onPanelActivate?: (panelId: string) => void;
  onPanelClose?: (panelId: string) => void;
  onPanelMove?: (panelId: string, targetAreaId: string) => void;
  onDrop?: (panelId: string, sourceAreaId: string) => void;
  allowDrop?: boolean;
}

/**
 * Panel Area Component
 * Holds multiple panels in a tabbed interface with drag-drop support
 */
export const ICUIPanelArea: React.FC<ICUIPanelAreaProps> = ({
  id,
  panels,
  activePanelId,
  className = '',
  style,
  onPanelActivate,
  onPanelClose,
  onPanelMove,
  onDrop,
  allowDrop = true,
}) => {
  const areaRef = useRef<HTMLDivElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [dragOverTab, setDragOverTab] = useState<string | null>(null);

  const activePanel = panels.find(p => p.id === activePanelId) || panels[0];

  // Handle tab click
  const handleTabClick = useCallback((panelId: string) => {
    if (onPanelActivate) {
      onPanelActivate(panelId);
    }
  }, [onPanelActivate]);

  // Handle tab close
  const handleTabClose = useCallback((panelId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    if (onPanelClose) {
      onPanelClose(panelId);
    }
  }, [onPanelClose]);

  // Handle drag start for tabs
  const handleTabDragStart = useCallback((event: React.DragEvent, panelId: string) => {
    event.dataTransfer.setData('text/plain', JSON.stringify({
      type: 'icui-panel',
      panelId,
      sourceAreaId: id,
    }));
    event.dataTransfer.effectAllowed = 'move';
    
    // Create drag image
    const dragElement = event.currentTarget as HTMLElement;
    const rect = dragElement.getBoundingClientRect();
    event.dataTransfer.setDragImage(dragElement, rect.width / 2, rect.height / 2);
  }, [id]);

  // Handle drag over
  const handleDragOver = useCallback((event: React.DragEvent) => {
    if (!allowDrop) return;

    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    
    try {
      const data = JSON.parse(event.dataTransfer.getData('text/plain'));
      if (data.type === 'icui-panel' && data.sourceAreaId !== id) {
        setIsDragOver(true);
      }
    } catch (e) {
      // Invalid drag data, ignore
    }
  }, [allowDrop, id]);

  // Handle drag leave
  const handleDragLeave = useCallback((event: React.DragEvent) => {
    // Only reset if leaving the entire area
    if (!areaRef.current?.contains(event.relatedTarget as Node)) {
      setIsDragOver(false);
      setDragOverTab(null);
    }
  }, []);

  // Handle drop
  const handleDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    setIsDragOver(false);
    setDragOverTab(null);

    if (!allowDrop || !onDrop) return;

    try {
      const data = JSON.parse(event.dataTransfer.getData('text/plain'));
      if (data.type === 'icui-panel' && data.sourceAreaId !== id) {
        onDrop(data.panelId, data.sourceAreaId);
      }
    } catch (e) {
      console.warn('Invalid drop data:', e);
    }
  }, [allowDrop, onDrop, id]);

  // Handle tab drag over
  const handleTabDragOver = useCallback((event: React.DragEvent, tabPanelId: string) => {
    event.preventDefault();
    setDragOverTab(tabPanelId);
  }, []);

  const areaClasses = [
    'icui-panel-area',
    isDragOver ? 'icui-area-drag-over' : '',
    panels.length === 0 ? 'icui-area-empty' : '',
    className,
  ].filter(Boolean).join(' ');

  if (panels.length === 0) {
    return (
      <div
        ref={areaRef}
        className={areaClasses}
        style={style}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="icui-area-empty-content">
          <div className="icui-empty-icon">📝</div>
          <div className="icui-empty-text">Drop panels here</div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={areaRef}
      className={areaClasses}
      style={style}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Tab Bar */}
      <div className="icui-panel-tabs">
        {panels.map((panel) => (
          <div
            key={panel.id}
            className={`icui-panel-tab ${panel.id === activePanel?.id ? 'active' : ''} ${
              dragOverTab === panel.id ? 'drag-over' : ''
            }`}
            onClick={() => handleTabClick(panel.id)}
            draggable={true}
            onDragStart={(e) => handleTabDragStart(e, panel.id)}
            onDragOver={(e) => handleTabDragOver(e, panel.id)}
            onDragLeave={() => setDragOverTab(null)}
          >
            <span className="icui-tab-icon">
              {panel.config.icon || '📄'}
            </span>
            <span className="icui-tab-title">
              {panel.config.title}
            </span>
            {panel.config.closable && (
              <button
                className="icui-tab-close"
                onClick={(e) => handleTabClose(panel.id, e)}
                title="Close"
              >
                ×
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Active Panel Content */}
      {activePanel && (
        <div className="icui-panel-content-area">
          <div className="icui-docked-panel-content">
            {/* Render panel content without the floating header */}
            <ICUIBasePanel
              panel={activePanel}
              onStateChange={() => {}} // Handled by parent
              onPositionChange={() => {}} // Not needed for docked panels
              onConfigChange={() => {}} // Handled by parent
              onClose={() => handleTabClose(activePanel.id, {} as any)}
              headerProps={{ editable: false, showControls: false }} // No header needed
              contentProps={{ padding: true, scrollable: true }}
              className="icui-docked-panel"
            >
              {/* Panel-specific content based on type */}
              <div className="icui-panel-type-content">
                {activePanel.config.type === 'editor' && (
                  <div className="icui-editor-content">
                    <div className="icui-editor-toolbar">
                      <span>📝 Code Editor</span>
                      <div className="icui-editor-actions">
                        <button className="icui-toolbar-btn">Format</button>
                        <button className="icui-toolbar-btn">Save</button>
                      </div>
                    </div>
                    <div className="icui-editor-area">
                      <div className="icui-code-editor">
                        {/* This would integrate with CodeMirror */}
                        <div className="icui-editor-placeholder">
                          <div className="icui-editor-lines">
                            <div className="icui-line"><span className="icui-line-number">1</span><span className="icui-code">// {activePanel.config.title}</span></div>
                            <div className="icui-line"><span className="icui-line-number">2</span><span className="icui-code">function example() {'{'}</span></div>
                            <div className="icui-line"><span className="icui-line-number">3</span><span className="icui-code">  console.log('Hello from {activePanel.config.title}');</span></div>
                            <div className="icui-line"><span className="icui-line-number">4</span><span className="icui-code">{'}'}</span></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                
                {activePanel.config.type === 'terminal' && (
                  <div className="icui-terminal-content">
                    <div className="icui-terminal-header">
                      <span>⌨️ Terminal</span>
                      <div className="icui-terminal-actions">
                        <button className="icui-toolbar-btn">Clear</button>
                        <button className="icui-toolbar-btn">Split</button>
                      </div>
                    </div>
                    <div className="icui-terminal-area">
                      <div className="icui-terminal-output">
                        <div className="icui-terminal-line">$ welcome to {activePanel.config.title}</div>
                        <div className="icui-terminal-line">$ npm start</div>
                        <div className="icui-terminal-line">Server started on port 3000...</div>
                        <div className="icui-terminal-line icui-terminal-cursor">$ <span className="icui-cursor">_</span></div>
                      </div>
                    </div>
                  </div>
                )}

                {activePanel.config.type === 'explorer' && (
                  <div className="icui-explorer-content">
                    <div className="icui-explorer-header">
                      <span>📁 File Explorer</span>
                      <div className="icui-explorer-actions">
                        <button className="icui-toolbar-btn">New File</button>
                        <button className="icui-toolbar-btn">New Folder</button>
                      </div>
                    </div>
                    <div className="icui-explorer-tree">
                      <div className="icui-tree-item icui-folder expanded">
                        <span className="icui-tree-icon">📂</span>
                        <span className="icui-tree-name">src</span>
                      </div>
                      <div className="icui-tree-item icui-file icui-nested">
                        <span className="icui-tree-icon">📄</span>
                        <span className="icui-tree-name">App.tsx</span>
                      </div>
                      <div className="icui-tree-item icui-file icui-nested">
                        <span className="icui-tree-icon">📄</span>
                        <span className="icui-tree-name">main.tsx</span>
                      </div>
                    </div>
                  </div>
                )}

                {['output', 'properties', 'timeline', 'inspector', 'custom'].includes(activePanel.config.type) && (
                  <div className="icui-generic-content">
                    <div className="icui-generic-header">
                      <span>{activePanel.config.icon || '📋'} {activePanel.config.title}</span>
                    </div>
                    <div className="icui-generic-body">
                      <p>Content for {activePanel.config.type} panel.</p>
                      <p>This panel is docked and can be dragged to other areas.</p>
                    </div>
                  </div>
                )}
              </div>
            </ICUIBasePanel>
          </div>
        </div>
      )}
    </div>
  );
};

export default ICUIPanelArea;
