/**
 * ICUI Tab Container Component
 * Provides draggable tab functionality extracted from ICUITest3/4
 * Handles tab management, drag/drop reordering, and panel switching
 */

import React, { useState, useCallback, useRef } from 'react';
import { ICUIPanelSelector, ICUIPanelType } from './ICUIPanelSelector';

export interface ICUITab {
  id: string;
  title: string;
  content: React.ReactNode;
  closable?: boolean;
  modified?: boolean;
  icon?: string;
}

export interface ICUITabContainerProps {
  tabs: ICUITab[];
  activeTabId: string;
  onTabActivate: (tabId: string) => void;
  onTabClose?: (tabId: string) => void;
  onTabReorder?: (fromIndex: number, toIndex: number) => void;
  onTabDrop?: (tabId: string, sourceAreaId: string) => void;
  areaId?: string;
  className?: string;
  enableDragDrop?: boolean;
  showAddButton?: boolean;
  onAddTab?: () => void;
  // New props for panel selector
  availablePanelTypes?: ICUIPanelType[];
  onPanelAdd?: (panelType: ICUIPanelType) => void;
  showPanelSelector?: boolean;
}

export const ICUITabContainer: React.FC<ICUITabContainerProps> = ({
  tabs,
  activeTabId,
  onTabActivate,
  onTabClose,
  onTabReorder,
  onTabDrop,
  areaId,
  className = '',
  enableDragDrop = false,
  availablePanelTypes,
  onPanelAdd,
  showPanelSelector = false,
}) => {
  const [draggedTab, setDraggedTab] = useState<string | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [hoveredTab, setHoveredTab] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const activeTab = tabs.find(tab => tab.id === activeTabId);

  // Drag and Drop Handlers
  const handleDragStart = useCallback((e: React.DragEvent, tab: ICUITab, index: number) => {
    if (!enableDragDrop) return;
    
    setDraggedTab(tab.id);
    e.dataTransfer.setData('application/icui-panel', tab.id); // For cross-area drops
    e.dataTransfer.setData('application/icui-tab', tab.id); // For tab reordering
    if (areaId) {
      e.dataTransfer.setData('application/icui-source-area', areaId);
    }
    e.dataTransfer.effectAllowed = 'move';
  }, [enableDragDrop, areaId]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    if (!enableDragDrop) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, [enableDragDrop]);

  const handleDrop = useCallback((e: React.DragEvent, targetIndex: number) => {
    if (!enableDragDrop) return;
    e.preventDefault();
    
    const tabId = e.dataTransfer.getData('application/icui-tab');
    const panelId = e.dataTransfer.getData('application/icui-panel');
    const sourceAreaId = e.dataTransfer.getData('application/icui-source-area');
    
    if (tabId && onTabReorder) {
      const draggedIndex = tabs.findIndex(tab => tab.id === tabId);
      if (draggedIndex !== -1 && draggedIndex !== targetIndex) {
        onTabReorder(draggedIndex, targetIndex);
      }
    } else if (panelId && onTabDrop && sourceAreaId) {
      onTabDrop(panelId, sourceAreaId);
    }
    
    setDraggedTab(null);
    setDragOverIndex(null);
  }, [enableDragDrop, tabs, onTabReorder, onTabDrop]);

  return (
    <div className={`icui-tab-container h-full flex flex-col ${className}`}>
      {/* Tab Bar */}
      <div className="flex items-center overflow-x-auto min-h-[40px]" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottom: '1px solid var(--icui-border-subtle)' }}>
        {tabs.map((tab, index) => (
          <div
            key={tab.id}
            className={`
              flex items-center gap-2 px-3 py-2 text-sm cursor-pointer border-r min-w-0 flex-shrink-0 max-w-[200px] select-none transition-all duration-200
              ${tab.id === activeTabId 
                ? 'border-b-2' 
                : ''
              }
            `}
            style={{
              backgroundColor: tab.id === activeTabId ? 'var(--icui-bg-secondary)' : 'var(--icui-bg-tertiary)',
              borderRightColor: 'var(--icui-border-subtle)',
              borderBottomColor: tab.id === activeTabId ? 'var(--icui-accent)' : 'transparent',
              color: tab.id === activeTabId ? 'var(--icui-text-primary)' : 'var(--icui-text-secondary)'
            }}
            onClick={() => onTabActivate(tab.id)}
            onMouseEnter={() => !dragOver && setHoveredTab(tab.id)}
            onMouseLeave={() => setHoveredTab(null)}
            onDragStart={(e) => handleDragStart(e, tab, index)}
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, index)}
            draggable={enableDragDrop}
          >
            {tab.icon && (
              <span className="text-sm flex-shrink-0">{tab.icon}</span>
            )}
            <span className="flex-1 truncate">{tab.title}</span>
            {tab.modified && <span className="ml-1 text-xs" style={{ color: 'var(--icui-warning)' }}>●</span>}
            {tab.closable && onTabClose && (
              <button
                className="ml-2 text-xs w-4 h-4 flex items-center justify-center rounded transition-all hover:opacity-80"
                style={{ 
                  color: 'var(--icui-text-secondary)',
                  backgroundColor: 'transparent'
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  onTabClose(tab.id);
                }}
                title="Close tab"
              >
                ×
              </button>
            )}
          </div>
        ))}

        {/* Panel Selector */}
        {showPanelSelector && availablePanelTypes && onPanelAdd && (
          <ICUIPanelSelector
            panelTypes={availablePanelTypes}
            onPanelSelect={onPanelAdd}
            className="mx-2"
            buttonClassName="h-8 px-2 py-1 text-xs border-r bg-blue-500 text-white hover:bg-blue-600"
            placeholder="Panel"
          />
        )}
      </div>

      {/* Tab Content */}
      <div className="flex-1 min-h-0 overflow-hidden" style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
        {activeTab ? activeTab.content : (
          <div className="h-full flex items-center justify-center" style={{ color: 'var(--icui-text-muted)' }}>
            No content available
          </div>
        )}
      </div>
    </div>
  );
};

export default ICUITabContainer;
