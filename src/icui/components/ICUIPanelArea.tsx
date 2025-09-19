/**
 * ICUI Enhanced Panel Area Component
 * Provides advance}) => {
  const [dragOver, setDragOver] = useState(false);
  const [isDragging, setIsDragging] = useState(false); // Track if a drag is in progress
  const dragCounter = useRef(0);

  // Stable local active tab state to avoid ping-pong with fallback logic
  const [localActiveTabId, setLocalActiveTabId] = useState<string>(() => {
    return activePanelId || panels[0]?.id || '';
  });

  // Keep local active tab in sync with prop changes, but don't override unnecessarily
  useEffect(() => {
    if (activePanelId && activePanelId !== localActiveTabId && !isDragging) {
      setLocalActiveTabId(activePanelId);
    }
  }, [activePanelId, localActiveTabId, isDragging]);nctionality extracted from ICUITest3/4
 * Handles panel docking, tab management, and drag/drop between areas
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { ICUITabContainer, ICUITab } from './ICUITabContainer';
import { ICUIPanelType } from './ICUIPanelSelector';

export interface ICUIPanel {
  id: string;
  type: string;
  title: string;
  content: React.ReactNode;
  closable?: boolean;
  resizable?: boolean;
  modified?: boolean;
  icon?: string;
  status?: 'connected' | 'disconnected';
  config?: Record<string, any>;
}

export interface ICUIPanelAreaProps {
  id: string;
  panels: ICUIPanel[];
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
  // New props for panel selector
  availablePanelTypes?: ICUIPanelType[];
  onPanelAdd?: (panelType: ICUIPanelType) => void;
  showPanelSelector?: boolean;
}

export const ICUIPanelArea: React.FC<ICUIPanelAreaProps> = ({
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
  // New props for panel selector
  availablePanelTypes,
  onPanelAdd,
  showPanelSelector = false,
}) => {
  const [dragOver, setDragOver] = useState(false);
  const [isDragging, setIsDragging] = useState(false); // Track if a drag is in progress
  const dragCounter = useRef(0);

  // Stable local active tab state to avoid ping-pong with fallback logic
  const [localActiveTabId, setLocalActiveTabId] = useState<string>(() => {
    return activePanelId || panels[0]?.id || '';
  });

  // Keep local active tab in sync with prop changes, but don't override unnecessarily
  useEffect(() => {
    if (activePanelId && activePanelId !== localActiveTabId) {
      setLocalActiveTabId(activePanelId);
    }
  }, [activePanelId]);

  // When panels change (reorder/add/remove), ensure the active tab still exists
  useEffect(() => {
    // If current active tab no longer exists, select a sensible default
    const exists = panels.some(p => p.id === localActiveTabId);
    if (!exists) {
      const next = (activePanelId && panels.some(p => p.id === activePanelId))
        ? activePanelId
        : (panels[0]?.id || '');
      if (next !== localActiveTabId) {
        setLocalActiveTabId(next);
        // Inform parent if we auto-selected a new tab
        if (next && next !== activePanelId) {
          onPanelActivate?.(next);
        }
      }
    }
  }, [panels]);

  // Detect newly added panel and auto-activate it to avoid ping-pong on creation
  const prevPanelIdsRef = useRef<string[]>([]);
  useEffect(() => {
    const prevIds = prevPanelIdsRef.current;
    const currentIds = panels.map(p => p.id);
    // Compute added ids
    const added = currentIds.filter(id => !prevIds.includes(id));

    if (added.length === 1) {
      const newId = added[0];
      // Only auto-activate if parent hasn't explicitly set a different active
      if (!activePanelId || activePanelId === newId) {
        if (localActiveTabId !== newId) {
          setLocalActiveTabId(newId);
          // Do not notify parent here to avoid ping-pong; parent layout will update via panel addition logic
        }
      }
    }

    prevPanelIdsRef.current = currentIds;
  }, [panels, activePanelId]);

  // Add global dragend listener to clear dragging state if drag is cancelled
  useEffect(() => {
    const handleDragEnd = () => {
      setIsDragging(false);
    };

    document.addEventListener('dragend', handleDragEnd);
    return () => {
      document.removeEventListener('dragend', handleDragEnd);
    };
  }, []);

  const activePanel = (localActiveTabId ? panels.find(p => p.id === localActiveTabId) : panels[0]);

  // Convert panels to tabs
  const tabs: ICUITab[] = panels.map(panel => ({
    id: panel.id,
    title: panel.title,
    content: panel.content,
    closable: panel.closable,
    modified: panel.modified,
    icon: panel.icon,
    status: panel.status,
  }));

  // Handle tab operations
  const handleTabActivate = useCallback((tabId: string) => {
    if (tabId === localActiveTabId) return; // No-op to prevent redundant updates
    // Optimistically update local active state to avoid visual flicker
    setLocalActiveTabId(tabId);
    onPanelActivate?.(tabId);
  }, [onPanelActivate, localActiveTabId]);

  const handleTabClose = useCallback((tabId: string) => {
    onPanelClose?.(tabId);
  }, [onPanelClose]);

  const handleTabReorder = useCallback((fromIndex: number, toIndex: number) => {
    onPanelReorder?.(fromIndex, toIndex);
  }, [onPanelReorder]);

  // Drag and drop handlers for external panels - FIXED: Add throttling to prevent excessive events
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    if (!allowDrop) return;
    
    e.preventDefault();
    dragCounter.current++;
    if (!dragOver) {
      setDragOver(true);
      setIsDragging(true); // Mark that we're in a drag operation
    }
  }, [allowDrop, dragOver]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    if (!allowDrop) return;
    
    dragCounter.current--;
    if (dragCounter.current <= 0) {
      dragCounter.current = 0; // Ensure it doesn't go negative
      setDragOver(false);
      // Don't clear isDragging here - wait for drop or dragend
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
    setIsDragging(false); // Clear dragging state
    dragCounter.current = 0;

    const panelId = e.dataTransfer.getData('application/icui-panel');
    const sourceAreaId = e.dataTransfer.getData('application/icui-source-area');
    
    // FIXED: Add defensive checks to prevent infinite loops
    if (panelId && sourceAreaId && sourceAreaId !== id) {
      // Additional check: ensure we don't already have this panel
      const panelExists = panels.some(panel => panel.id === panelId);
      if (panelExists) {
        console.warn('Panel already exists in target area, ignoring drop:', { panelId, sourceAreaId, targetAreaId: id });
        return;
      }
      
      // Only set active tab locally after drop is complete, not during drag
      // This prevents rapid tab switching during drag operations
      setTimeout(() => {
        setLocalActiveTabId(panelId);
      }, 50); // Small delay to ensure drop completes first
      
      // Dropping panel in different area
      onPanelDrop?.(panelId, sourceAreaId);
    } else if (sourceAreaId === id) {
      // Ignoring drop in same area
    }
  }, [allowDrop, id, onPanelDrop, panels]);

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
          activeTabId={localActiveTabId}
          onTabActivate={handleTabActivate}
          onTabClose={onPanelClose ? handleTabClose : undefined}
          onTabReorder={handleTabReorder}
          areaId={id}
          enableDragDrop={enableDragDrop}
          className="h-full"
          availablePanelTypes={availablePanelTypes}
          onPanelAdd={onPanelAdd}
          showPanelSelector={showPanelSelector}
          isDragging={isDragging} // Pass drag state to prevent activation during drag
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
      <div className="flex items-center justify-between px-3 py-1 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)', color: 'var(--icui-text-primary)' }}>
        <div className="flex items-center space-x-2">
          {singlePanel.icon && (
            <span className="text-sm">{singlePanel.icon}</span>
          )}
          <span className="text-sm font-medium">
            {singlePanel.title}
            {singlePanel.modified && <span className="ml-1" style={{ color: 'var(--icui-warning)' }}>●</span>}
            {singlePanel.status === 'connected' && <span className="ml-1 text-green-500">●</span>}
            {singlePanel.status === 'disconnected' && <span className="ml-1 text-red-500">●</span>}
          </span>
        </div>
        {singlePanel.closable && onPanelClose && (
          <button
            className="text-sm hover:opacity-80 transition-opacity"
            style={{ color: 'var(--icui-text-secondary)' }}
            onClick={() => onPanelClose(singlePanel.id)}
            title="Close panel"
          >
            ×
          </button>
        )}
      </div>

      {/* Single Panel Content */}
      <div className="flex-1 min-h-0 overflow-hidden" style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
        {singlePanel.content}
      </div>
    </div>
  );
};

export default ICUIPanelArea;
