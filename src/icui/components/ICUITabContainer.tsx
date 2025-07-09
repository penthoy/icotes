/**
 * ICUI Tab Container Component
 * Provides draggable tab functionality extracted from ICUITest3/4
 * Handles tab management, drag/drop reordering, and panel switching
 */

import React, { useState, useCallback, useRef } from 'react';

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
  onTabDrop?: (tabId: string, targetAreaId: string) => void;
  areaId?: string; // Source area ID for drag and drop
  className?: string;
  enableDragDrop?: boolean;
  showAddButton?: boolean;
  onAddTab?: () => void;
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
  enableDragDrop = true,
  showAddButton = false,
  onAddTab,
}) => {
  const [draggedTab, setDraggedTab] = useState<string | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const dragCounter = useRef(0);

  const activeTab = tabs.find(tab => tab.id === activeTabId);

  const handleTabClick = useCallback((tabId: string) => {
    onTabActivate(tabId);
  }, [onTabActivate]);

  const handleTabClose = useCallback((e: React.MouseEvent, tabId: string) => {
    e.stopPropagation();
    onTabClose?.(tabId);
  }, [onTabClose]);

  // Drag and Drop Handlers
  const handleDragStart = useCallback((e: React.DragEvent, tabId: string) => {
    if (!enableDragDrop) return;
    
    setDraggedTab(tabId);
    e.dataTransfer.setData('application/icui-panel', tabId); // For cross-area drops
    e.dataTransfer.setData('application/icui-tab', tabId); // For tab reordering
    if (areaId) {
      e.dataTransfer.setData('application/icui-source-area', areaId);
    }
    e.dataTransfer.effectAllowed = 'move';
    
    // Create custom drag image
    const dragTab = e.currentTarget as HTMLElement;
    const rect = dragTab.getBoundingClientRect();
    e.dataTransfer.setDragImage(dragTab, rect.width / 2, rect.height / 2);
  }, [enableDragDrop, areaId]);

  const handleDragEnd = useCallback(() => {
    setDraggedTab(null);
    setDragOverIndex(null);
    dragCounter.current = 0;
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, index: number) => {
    if (!enableDragDrop) return;
    
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverIndex(index);
  }, [enableDragDrop]);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    if (!enableDragDrop) return;
    
    e.preventDefault();
    dragCounter.current++;
  }, [enableDragDrop]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    if (!enableDragDrop) return;
    
    dragCounter.current--;
    if (dragCounter.current === 0) {
      setDragOverIndex(null);
    }
  }, [enableDragDrop]);

  const handleDrop = useCallback((e: React.DragEvent, targetIndex: number) => {
    if (!enableDragDrop) return;
    
    e.preventDefault();
    const draggedTabId = e.dataTransfer.getData('application/icui-tab');
    
    if (draggedTabId && draggedTabId !== tabs[targetIndex]?.id) {
      const fromIndex = tabs.findIndex(tab => tab.id === draggedTabId);
      if (fromIndex !== -1 && fromIndex !== targetIndex) {
        onTabReorder?.(fromIndex, targetIndex);
      }
    }
    
    setDraggedTab(null);
    setDragOverIndex(null);
    dragCounter.current = 0;
  }, [enableDragDrop, tabs, onTabReorder]);

  return (
    <div className={`icui-tab-container h-full flex flex-col ${className}`}>
      {/* Tab Headers */}
      <div className="flex items-center bg-gray-800 border-b border-gray-700 min-h-[32px] overflow-x-auto">
        <div className="flex items-center">
          {tabs.map((tab, index) => (
            <div
              key={tab.id}
              className={`
                relative flex items-center px-3 py-1 text-sm cursor-grab select-none
                border-r border-gray-700 min-w-[120px] max-w-[200px] transition-all duration-150
                ${tab.id === activeTabId 
                  ? 'bg-gray-900 text-white border-b-2 border-blue-500' 
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                }
                ${draggedTab === tab.id ? 'opacity-50 scale-95 transform cursor-grabbing' : ''}
                ${dragOverIndex === index ? 'border-l-2 border-blue-500 bg-blue-900/20' : ''}
                ${enableDragDrop ? 'hover:border-gray-500' : ''}
              `}
              draggable={enableDragDrop}
              onClick={() => handleTabClick(tab.id)}
              onDragStart={(e) => handleDragStart(e, tab.id)}
              onDragEnd={handleDragEnd}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragEnter={handleDragEnter}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, index)}
              title={enableDragDrop ? `${tab.title} (Drag to move between panels)` : tab.title}
            >
              {/* Drag Handle Indicator */}
              {enableDragDrop && (
                <span 
                  className="mr-2 text-white text-sm font-bold select-none hover:text-blue-300 transition-colors cursor-grab bg-gray-600 px-1 rounded"
                  title="Drag to move between panels"
                  style={{ textShadow: '0 1px 2px rgba(0,0,0,0.8)' }}
                >
                  ⋮⋮
                </span>
              )}
              
              {/* Tab Icon */}
              {tab.icon && (
                <span className="mr-2 text-xs">{tab.icon}</span>
              )}
              
              {/* Tab Title */}
              <span className="flex-1 truncate">
                {tab.title}
              </span>
              
              {/* Modified Indicator */}
              {tab.modified && (
                <span className="ml-1 text-orange-500 text-xs">●</span>
              )}
              
              {/* Close Button */}
              {tab.closable !== false && onTabClose && (
                <button
                  className="ml-2 text-gray-400 hover:text-red-500 text-xs w-4 h-4 flex items-center justify-center"
                  onClick={(e) => handleTabClose(e, tab.id)}
                  title="Close tab"
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>
        
        {/* Add Tab Button */}
        {showAddButton && onAddTab && (
          <button
            className="px-2 py-1 text-xs bg-blue-500 text-white rounded mx-2 hover:bg-blue-600"
            onClick={onAddTab}
            title="Add new tab"
          >
            +
          </button>
        )}
      </div>

      {/* Tab Content */}
      <div className="flex-1 min-h-0 overflow-hidden bg-black">
        {activeTab ? activeTab.content : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <div className="text-2xl mb-2">📄</div>
              <div>No active tab</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ICUITabContainer;
