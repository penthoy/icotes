/**
 * ICUI Enhanced Panel Area Component
 * Provides advanced panel area functionality extracted from ICUITest3/4
 * Handles panel docking, tab management, and drag/drop between areas
 */

import React, { useState, useCallback, useRef } from 'react';
import { ICUITabContainer, ICUITab } from './ICUITabContainer';

export interface ICUIEnhancedPanel {
  id: string;
  type: string;
  title: string;
  content: React.ReactNode;
  closable?: boolean;
  resizable?: boolean;
  modified?: boolean;
  icon?: string;
  config?: Record<string, any>;
}

export interface ICUIEnhancedPanelAreaProps {
  id: string;
  panels: ICUIEnhancedPanel[];
  activePanelId?: string;
  onPanelActivate?: (panelId: string) => void;
  onPanelClose?: (panelId: string) => void;
  onPanelDrop?: (panelId: string, sourceAreaId: string) => void;
  onPanelReorder?: (fromIndex: number, toIndex: number) => void;
  className?: string;
  allowDrop?: boolean;
  showWhenEmpty?: boolean;
  emptyMessage?: string;
  orientation?: 'horizontal' | 'vertical';
  enableDragDrop?: boolean; // Add this prop to control drag/drop behavior
}

export const ICUIEnhancedPanelArea: React.FC<ICUIEnhancedPanelAreaProps> = ({
  id,
  panels,
  activePanelId,
  onPanelActivate,
  onPanelClose,
  onPanelDrop,
  onPanelReorder,
  className = '',
  allowDrop = true,
  showWhenEmpty = true,
  emptyMessage = 'Drop panels here',
  orientation = 'horizontal',
  enableDragDrop = true, // Default to true
}) => {
  const [dragOver, setDragOver] = useState(false);
  const dragCounter = useRef(0);

  const activePanel = activePanelId ? panels.find(p => p.id === activePanelId) : panels[0];

  // Convert panels to tabs
  const tabs: ICUITab[] = panels.map(panel => ({
    id: panel.id,
    title: panel.title,
    content: panel.content,
    closable: panel.closable,
    modified: panel.modified,
    icon: panel.icon,
  }));

  // Handle tab operations
  const handleTabActivate = useCallback((tabId: string) => {
    onPanelActivate?.(tabId);
  }, [onPanelActivate]);

  const handleTabClose = useCallback((tabId: string) => {
    onPanelClose?.(tabId);
  }, [onPanelClose]);

  const handleTabReorder = useCallback((fromIndex: number, toIndex: number) => {
    onPanelReorder?.(fromIndex, toIndex);
  }, [onPanelReorder]);

  // Drag and drop handlers for external panels
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    if (!allowDrop) return;
    
    e.preventDefault();
    dragCounter.current++;
    setDragOver(true);
  }, [allowDrop]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    if (!allowDrop) return;
    
    dragCounter.current--;
    if (dragCounter.current === 0) {
      setDragOver(false);
    }
  }, [allowDrop]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    if (!allowDrop) return;
    
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, [allowDrop]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    if (!allowDrop) return;
    
    e.preventDefault();
    setDragOver(false);
    dragCounter.current = 0;

    const panelId = e.dataTransfer.getData('application/icui-panel');
    const sourceAreaId = e.dataTransfer.getData('application/icui-source-area');
    
    if (panelId && sourceAreaId && sourceAreaId !== id) {
      onPanelDrop?.(panelId, sourceAreaId);
    }
  }, [allowDrop, id, onPanelDrop]);

  // Render empty state
  if (panels.length === 0) {
    if (!showWhenEmpty) return null;
    
    return (
      <div
        className={`
          icui-enhanced-panel-area h-full flex items-center justify-center
          border-2 border-dashed transition-all duration-200
          ${dragOver 
            ? 'border-blue-500 bg-blue-900/20 border-solid shadow-lg' 
            : 'border-gray-600 bg-gray-900 hover:border-gray-500'
          }
          ${className}
        `}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <div className="text-center text-gray-500">
          <div className="text-2xl mb-2">📋</div>
          <div className="text-sm">{emptyMessage}</div>
          {allowDrop && (
            <div className="text-xs text-gray-600 mt-1">Drag tabs here</div>
          )}
        </div>
      </div>
    );
  }

  // Render with tabs if multiple panels OR if drag/drop is enabled (to show drag handles)
  if (panels.length > 1 || (enableDragDrop && panels.length === 1)) {
    return (
      <div
        className={`
          icui-enhanced-panel-area h-full transition-all duration-200
          ${dragOver ? 'ring-2 ring-blue-500 ring-opacity-50 bg-blue-900/10' : ''}
          ${className}
        `}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <ICUITabContainer
          tabs={tabs}
          activeTabId={activePanelId || panels[0]?.id || ''}
          onTabActivate={handleTabActivate}
          onTabClose={onPanelClose ? handleTabClose : undefined}
          onTabReorder={handleTabReorder}
          areaId={id}
          enableDragDrop={enableDragDrop}
          className="h-full"
        />
      </div>
    );
  }

  // Render single panel
  const singlePanel = panels[0];
  return (
    <div
      className={`
        icui-enhanced-panel-area h-full flex flex-col transition-all duration-200
        ${dragOver ? 'ring-2 ring-blue-500 ring-opacity-50 bg-blue-900/10' : ''}
        ${className}
      `}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Single Panel Header */}
      <div className="flex items-center justify-between px-3 py-1 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center space-x-2">
          {singlePanel.icon && (
            <span className="text-sm">{singlePanel.icon}</span>
          )}
          <span className="text-sm font-medium text-white">
            {singlePanel.title}
            {singlePanel.modified && <span className="ml-1 text-orange-500">●</span>}
          </span>
        </div>
        {singlePanel.closable && onPanelClose && (
          <button
            className="text-gray-400 hover:text-red-500 text-sm"
            onClick={() => onPanelClose(singlePanel.id)}
            title="Close panel"
          >
            ×
          </button>
        )}
      </div>

      {/* Single Panel Content */}
      <div className="flex-1 min-h-0 overflow-hidden bg-black">
        {singlePanel.content}
      </div>
    </div>
  );
};

export default ICUIEnhancedPanelArea;
