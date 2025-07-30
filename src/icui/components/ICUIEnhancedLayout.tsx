/**
 * ICUI Enhanced Layout Component
 * Provides IDE-like layout functionality extracted from ICUITest3/4
 * Handles resizable panels, docking areas, and layout persistence
 */

import React, { useState, useCallback, useEffect } from 'react';
import { ICUIFrameContainer } from './ICUIFrameContainer';
import { ICUISplitPanel } from './ICUISplitPanel';
import { ICUIEnhancedPanelArea, ICUIEnhancedPanel } from './ICUIEnhancedPanelArea';
import { ICUIPanelType } from './ICUIPanelSelector';

export interface ICUILayoutArea {
  id: string;
  name: string;
  panelIds: string[];
  activePanelId?: string;
  visible?: boolean;
  collapsible?: boolean;
  size?: number; // Percentage for split panels
}

export interface ICUILayoutConfig {
  layoutMode?: 'standard' | 'h-layout';
  areas: Record<string, ICUILayoutArea>;
  splitConfig?: {
    mainVerticalSplit?: number;
    mainHorizontalSplit?: number;
    rightVerticalSplit?: number;
    centerVerticalSplit?: number;
  };
}

export interface ICUIEnhancedLayoutProps {
  panels: ICUIEnhancedPanel[];
  layout: ICUILayoutConfig;
  onLayoutChange?: (layout: ICUILayoutConfig) => void;
  onPanelMove?: (panelId: string, targetAreaId: string, sourceAreaId: string) => void;
  onPanelClose?: (panelId: string) => void;
  onPanelActivate?: (panelId: string, areaId: string) => void;
  className?: string;
  enableDragDrop?: boolean;
  persistLayout?: boolean;
  layoutKey?: string;
  // New props for panel selector
  availablePanelTypes?: ICUIPanelType[];
  onPanelAdd?: (panelType: ICUIPanelType, areaId: string) => void;
  showPanelSelector?: boolean;
}

// Default layout configuration
const defaultLayout: ICUILayoutConfig = {
  areas: {
    left: { id: 'left', name: 'Left Sidebar', panelIds: [], size: 25, collapsible: true },
    center: { id: 'center', name: 'Main Area', panelIds: [], size: 50 },
    right: { id: 'right', name: 'Right Sidebar', panelIds: [], size: 25, collapsible: true, visible: false },
    bottom: { id: 'bottom', name: 'Bottom Panel', panelIds: [], size: 30, collapsible: true },
  },
  splitConfig: {
    mainVerticalSplit: 75,
    mainHorizontalSplit: 25,
    rightVerticalSplit: 75,
  }
};

export const ICUIEnhancedLayout: React.FC<ICUIEnhancedLayoutProps> = ({
  panels,
  layout,
  onLayoutChange,
  onPanelMove,
  onPanelClose,
  onPanelActivate,
  className = '',
  enableDragDrop = true,
  persistLayout = true,
  layoutKey = 'icui-layout',
  // New props for panel selector
  availablePanelTypes,
  onPanelAdd,
  showPanelSelector = false,
}) => {
  const [currentLayout, setCurrentLayout] = useState<ICUILayoutConfig>(layout || defaultLayout);

  // Load persisted layout on mount
  useEffect(() => {
    if (persistLayout && layoutKey) {
      const saved = localStorage.getItem(layoutKey);
      if (saved) {
        try {
          const parsedLayout = JSON.parse(saved);
          // Merge persisted layout with provided layout to ensure new panels are included
          const mergedLayout = {
            ...parsedLayout,
            areas: {
              ...parsedLayout.areas,
              // Ensure areas from the provided layout are preserved
              ...(layout ? layout.areas : {}),
            }
          };
          setCurrentLayout(mergedLayout);
        } catch (error) {
          console.warn('Failed to load persisted layout:', error);
          setCurrentLayout(layout || defaultLayout);
        }
      } else {
        // No saved layout, use provided layout
        setCurrentLayout(layout || defaultLayout);
      }
    } else {
      setCurrentLayout(layout || defaultLayout);
    }
  }, [persistLayout, layoutKey]);

  // Update layout when prop changes (only if it's actually different)
  useEffect(() => {
    if (layout && JSON.stringify(layout) !== JSON.stringify(currentLayout)) {
      setCurrentLayout(layout);
    }
  }, [layout]);

  // Save layout changes and call onLayoutChange (only when user makes changes, not prop updates)
  const [isInitialized, setIsInitialized] = useState(false);
  useEffect(() => {
    if (!isInitialized) {
      setIsInitialized(true);
      return; // Don't call onLayoutChange during initialization
    }
    
    if (persistLayout && layoutKey) {
      localStorage.setItem(layoutKey, JSON.stringify(currentLayout));
    }
    // Call onLayoutChange only for user-initiated changes
    onLayoutChange?.(currentLayout);
  }, [currentLayout, persistLayout, layoutKey, isInitialized]);

  // Get panels for a specific area
  const getPanelsForArea = useCallback((areaId: string): ICUIEnhancedPanel[] => {
    const area = currentLayout.areas[areaId];
    if (!area) return [];
    
    return area.panelIds
      .map(id => panels.find(p => p.id === id))
      .filter(Boolean) as ICUIEnhancedPanel[];
  }, [panels, currentLayout]);

  // Handle panel activation
  const handlePanelActivate = useCallback((areaId: string, panelId: string) => {
    setCurrentLayout(prev => ({
      ...prev,
      areas: {
        ...prev.areas,
        [areaId]: {
          ...prev.areas[areaId],
          activePanelId: panelId,
        }
      }
    }));
    onPanelActivate?.(panelId, areaId);
  }, [onPanelActivate]);

  // Handle panel close
  const handlePanelClose = useCallback((areaId: string, panelId: string) => {
    setCurrentLayout(prev => {
      const area = prev.areas[areaId];
      const newPanelIds = area.panelIds.filter(id => id !== panelId);
      const newActivePanelId = area.activePanelId === panelId 
        ? newPanelIds[0] || undefined 
        : area.activePanelId;

      return {
        ...prev,
        areas: {
          ...prev.areas,
          [areaId]: {
            ...area,
            panelIds: newPanelIds,
            activePanelId: newActivePanelId,
          }
        }
      };
    });
    onPanelClose?.(panelId);
  }, [onPanelClose]);

  // Handle panel reordering within the same area
  const handlePanelReorder = useCallback((areaId: string, fromIndex: number, toIndex: number) => {
    setCurrentLayout(prev => {
      const area = prev.areas[areaId];
      if (!area) return prev;

      const newPanelIds = [...area.panelIds];
      const [movedPanel] = newPanelIds.splice(fromIndex, 1);
      newPanelIds.splice(toIndex, 0, movedPanel);

      return {
        ...prev,
        areas: {
          ...prev.areas,
          [areaId]: {
            ...area,
            panelIds: newPanelIds,
          }
        }
      };
    });
  }, []);

  // Handle panel drop between areas - FIXED: Add defensive checks to prevent infinite loops
  const handlePanelDrop = useCallback((targetAreaId: string, panelId: string, sourceAreaId: string) => {
    // Prevent drop if source and target are the same or if panel doesn't exist in source
    if (sourceAreaId === targetAreaId) {
      console.warn('Attempted to drop panel in the same area, ignoring:', { panelId, sourceAreaId, targetAreaId });
      return;
    }

    setCurrentLayout(prev => {
      const sourceArea = prev.areas[sourceAreaId];
      const targetArea = prev.areas[targetAreaId];

      // Validate areas exist
      if (!sourceArea || !targetArea) {
        console.warn('Invalid source or target area:', { sourceArea: !!sourceArea, targetArea: !!targetArea, sourceAreaId, targetAreaId });
        return prev; // Return unchanged if areas don't exist
      }

      // Validate panel exists in source area
      if (!sourceArea.panelIds.includes(panelId)) {
        console.warn('Panel not found in source area:', { panelId, sourceAreaId, panelIds: sourceArea.panelIds });
        return prev; // Return unchanged if panel not in source
      }

      // Prevent duplicate panel in target area
      if (targetArea.panelIds.includes(panelId)) {
        console.warn('Panel already exists in target area:', { panelId, targetAreaId, panelIds: targetArea.panelIds });
        return prev; // Return unchanged if panel already in target
      }

      return {
        ...prev,
        areas: {
          ...prev.areas,
          [sourceAreaId]: {
            ...sourceArea,
            panelIds: sourceArea.panelIds.filter(id => id !== panelId),
            // Update active panel if we're removing the active one
            activePanelId: sourceArea.activePanelId === panelId 
              ? sourceArea.panelIds.filter(id => id !== panelId)[0] || undefined
              : sourceArea.activePanelId,
          },
          [targetAreaId]: {
            ...targetArea,
            panelIds: [...targetArea.panelIds, panelId],
            activePanelId: panelId,
          }
        }
      };
    });
    onPanelMove?.(panelId, targetAreaId, sourceAreaId);
  }, [onPanelMove]);

  // Handle panel addition
  const handlePanelAdd = useCallback((panelType: ICUIPanelType, areaId: string) => {
    if (onPanelAdd) {
      onPanelAdd(panelType, areaId);
    }
  }, [onPanelAdd]);

  // Handle split changes
  const handleSplitChange = useCallback((splitName: string, value: number) => {
    setCurrentLayout(prev => ({
      ...prev,
      splitConfig: {
        ...prev.splitConfig,
        [splitName]: value,
      }
    }));
  }, []);

  const leftPanels = getPanelsForArea('left');
  const centerPanels = getPanelsForArea('center');
  const rightPanels = getPanelsForArea('right');
  const bottomPanels = getPanelsForArea('bottom');

  const leftArea = currentLayout.areas.left;
  const centerArea = currentLayout.areas.center;
  const rightArea = currentLayout.areas.right;
  const bottomArea = currentLayout.areas.bottom;

  // Render H-Layout structure
  const renderHLayout = () => (
    <ICUISplitPanel
      id="h-layout-main-split"
      config={{
        direction: 'horizontal',
        initialSplit: currentLayout.splitConfig?.mainHorizontalSplit || 20,
        minSize: 15,
        collapsible: true,
        resizable: true,
      }}
      className="h-full"
      onSplitChange={(split) => handleSplitChange('mainHorizontalSplit', split)}
      firstPanel={
        /* Left Panel Area - Full Height */
        leftArea.visible !== false ? (
          <ICUIEnhancedPanelArea
            id="left"
            panels={leftPanels}
            activePanelId={leftArea.activePanelId}
            onPanelActivate={(panelId) => handlePanelActivate('left', panelId)}
            onPanelClose={(panelId) => handlePanelClose('left', panelId)}
            onPanelDrop={(panelId, sourceAreaId) => handlePanelDrop('left', panelId, sourceAreaId)}
            onPanelReorder={(fromIndex, toIndex) => handlePanelReorder('left', fromIndex, toIndex)}
            allowDrop={enableDragDrop}
            enableDragDrop={enableDragDrop}
            emptyMessage="Drop explorer panels here"
            className="h-full"
            availablePanelTypes={availablePanelTypes}
            onPanelAdd={(panelType) => handlePanelAdd(panelType, 'left')}
            showPanelSelector={showPanelSelector}
          />
        ) : null
      }
      secondPanel={
        <ICUISplitPanel
          id="h-layout-center-right-split"
          config={{
            direction: 'horizontal',
            initialSplit: currentLayout.splitConfig?.rightVerticalSplit || 80,
            minSize: 15,
            collapsible: true,
            resizable: true,
          }}
          className="h-full"
          onSplitChange={(split) => handleSplitChange('rightVerticalSplit', split)}
          firstPanel={
            /* Center Area - Split Vertically between Editor and Terminal */
            <ICUISplitPanel
              id="h-layout-center-vertical-split"
              config={{
                direction: 'vertical',
                initialSplit: currentLayout.splitConfig?.centerVerticalSplit || 60,
                minSize: 20,
                collapsible: true,
                resizable: true,
              }}
              className="h-full"
              onSplitChange={(split) => handleSplitChange('centerVerticalSplit', split)}
              firstPanel={
                /* Editor Area */
                <ICUIEnhancedPanelArea
                  id="center"
                  panels={centerPanels}
                  activePanelId={centerArea.activePanelId}
                  onPanelActivate={(panelId) => handlePanelActivate('center', panelId)}
                  onPanelClose={(panelId) => handlePanelClose('center', panelId)}
                  onPanelDrop={(panelId, sourceAreaId) => handlePanelDrop('center', panelId, sourceAreaId)}
                  onPanelReorder={(fromIndex, toIndex) => handlePanelReorder('center', fromIndex, toIndex)}
                  allowDrop={enableDragDrop}
                  enableDragDrop={enableDragDrop}
                  emptyMessage="Drop editor panels here"
                  className="h-full"
                  availablePanelTypes={availablePanelTypes}
                  onPanelAdd={(panelType) => handlePanelAdd(panelType, 'center')}
                  showPanelSelector={showPanelSelector}
                />
              }
              secondPanel={
                /* Terminal Area */
                bottomArea.visible !== false ? (
                  <ICUIEnhancedPanelArea
                    id="bottom"
                    panels={bottomPanels}
                    activePanelId={bottomArea.activePanelId}
                    onPanelActivate={(panelId) => handlePanelActivate('bottom', panelId)}
                    onPanelClose={(panelId) => handlePanelClose('bottom', panelId)}
                    onPanelDrop={(panelId, sourceAreaId) => handlePanelDrop('bottom', panelId, sourceAreaId)}
                    onPanelReorder={(fromIndex, toIndex) => handlePanelReorder('bottom', fromIndex, toIndex)}
                    allowDrop={enableDragDrop}
                    enableDragDrop={enableDragDrop}
                    emptyMessage="Drop terminal/output panels here"
                    showWhenEmpty={true}
                    className="h-full"
                    availablePanelTypes={availablePanelTypes}
                    onPanelAdd={(panelType) => handlePanelAdd(panelType, 'bottom')}
                    showPanelSelector={showPanelSelector}
                  />
                ) : null
              }
            />
          }
          secondPanel={
            /* Right Panel Area - Full Height */
            rightArea.visible !== false ? (
              <ICUIEnhancedPanelArea
                id="right"
                panels={rightPanels}
                activePanelId={rightArea.activePanelId}
                onPanelActivate={(panelId) => handlePanelActivate('right', panelId)}
                onPanelClose={(panelId) => handlePanelClose('right', panelId)}
                onPanelDrop={(panelId, sourceAreaId) => handlePanelDrop('right', panelId, sourceAreaId)}
                onPanelReorder={(fromIndex, toIndex) => handlePanelReorder('right', fromIndex, toIndex)}
                allowDrop={enableDragDrop}
                enableDragDrop={enableDragDrop}
                emptyMessage="Drop utility panels here"
                showWhenEmpty={true}
                className="h-full"
                availablePanelTypes={availablePanelTypes}
                onPanelAdd={(panelType) => handlePanelAdd(panelType, 'right')}
                showPanelSelector={showPanelSelector}
              />
            ) : null
          }
        />
      }
    />
  );

  // Render Standard Layout structure
  const renderStandardLayout = () => (
    <ICUISplitPanel
      id="main-vertical-split"
      config={{
        direction: 'vertical',
        initialSplit: currentLayout.splitConfig?.mainVerticalSplit || 75,
        minSize: 20,
        collapsible: true,
        resizable: true,
      }}
      className="h-full"
      onSplitChange={(split) => handleSplitChange('mainVerticalSplit', split)}
      firstPanel={
        /* Top Section: Left + Center + Right */
        <ICUISplitPanel
          id="top-horizontal-split"
          config={{
            direction: 'horizontal',
            initialSplit: currentLayout.splitConfig?.mainHorizontalSplit || 25,
            minSize: 10,
            collapsible: true,
            resizable: true,
          }}
          className="h-full"
          onSplitChange={(split) => handleSplitChange('mainHorizontalSplit', split)}
          firstPanel={
            /* Left Panel Area */
            leftArea.visible !== false ? (
              <ICUIEnhancedPanelArea
                id="left"
                panels={leftPanels}
                activePanelId={leftArea.activePanelId}
                onPanelActivate={(panelId) => handlePanelActivate('left', panelId)}
                onPanelClose={(panelId) => handlePanelClose('left', panelId)}
                onPanelDrop={(panelId, sourceAreaId) => handlePanelDrop('left', panelId, sourceAreaId)}
                onPanelReorder={(fromIndex, toIndex) => handlePanelReorder('left', fromIndex, toIndex)}
                allowDrop={enableDragDrop}
                enableDragDrop={enableDragDrop}
                emptyMessage="Drop explorer panels here"
                className="h-full"
                availablePanelTypes={availablePanelTypes}
                onPanelAdd={(panelType) => handlePanelAdd(panelType, 'left')}
                showPanelSelector={showPanelSelector}
              />
            ) : null
          }
          secondPanel={
            <ICUISplitPanel
              id="center-right-split"
              config={{
                direction: 'horizontal',
                initialSplit: currentLayout.splitConfig?.rightVerticalSplit || 75,
                minSize: 20,
                collapsible: true,
                resizable: true,
              }}
              className="h-full"
              onSplitChange={(split) => handleSplitChange('rightVerticalSplit', split)}
              firstPanel={
                /* Center Panel Area */
                <ICUIEnhancedPanelArea
                  id="center"
                  panels={centerPanels}
                  activePanelId={centerArea.activePanelId}
                  onPanelActivate={(panelId) => handlePanelActivate('center', panelId)}
                  onPanelClose={(panelId) => handlePanelClose('center', panelId)}
                  onPanelDrop={(panelId, sourceAreaId) => handlePanelDrop('center', panelId, sourceAreaId)}
                  onPanelReorder={(fromIndex, toIndex) => handlePanelReorder('center', fromIndex, toIndex)}
                  allowDrop={enableDragDrop}
                  enableDragDrop={enableDragDrop}
                  emptyMessage="Drop editor panels here"
                  className="h-full"
                />
              }
              secondPanel={
                /* Right Panel Area */
                rightArea.visible !== false ? (
                  <ICUIEnhancedPanelArea
                    id="right"
                    panels={rightPanels}
                    activePanelId={rightArea.activePanelId}
                    onPanelActivate={(panelId) => handlePanelActivate('right', panelId)}
                    onPanelClose={(panelId) => handlePanelClose('right', panelId)}
                    onPanelDrop={(panelId, sourceAreaId) => handlePanelDrop('right', panelId, sourceAreaId)}
                    onPanelReorder={(fromIndex, toIndex) => handlePanelReorder('right', fromIndex, toIndex)}
                    allowDrop={enableDragDrop}
                    enableDragDrop={enableDragDrop}
                    emptyMessage="Drop utility panels here"
                    showWhenEmpty={true}
                    className="h-full"
                    availablePanelTypes={availablePanelTypes}
                    onPanelAdd={(panelType) => handlePanelAdd(panelType, 'right')}
                    showPanelSelector={showPanelSelector}
                  />
                ) : null
              }
            />
          }
        />
      }
      secondPanel={
        /* Bottom Panel Area */
        bottomArea.visible !== false ? (
          <ICUIEnhancedPanelArea
            id="bottom"
            panels={bottomPanels}
            activePanelId={bottomArea.activePanelId}
            onPanelActivate={(panelId) => handlePanelActivate('bottom', panelId)}
            onPanelClose={(panelId) => handlePanelClose('bottom', panelId)}
            onPanelDrop={(panelId, sourceAreaId) => handlePanelDrop('bottom', panelId, sourceAreaId)}
            onPanelReorder={(fromIndex, toIndex) => handlePanelReorder('bottom', fromIndex, toIndex)}
            allowDrop={enableDragDrop}
            enableDragDrop={enableDragDrop}
            emptyMessage="Drop terminal/output panels here"
            showWhenEmpty={true}
            className="h-full"
            availablePanelTypes={availablePanelTypes}
            onPanelAdd={(panelType) => handlePanelAdd(panelType, 'bottom')}
            showPanelSelector={showPanelSelector}
          />
        ) : null
      }
    />
  );

  return (
    <div className={`icui-enhanced-layout w-full h-full min-h-0 flex flex-col ${className}`}>
      <ICUIFrameContainer
        id="enhanced-layout-frame"
        config={{
          responsive: true,
          borderDetection: true,
          minPanelSize: { width: 200, height: 100 },
          resizeHandleSize: 6,
          snapThreshold: 20,
        }}
        className="w-full h-full flex-1"
      >
        {currentLayout.layoutMode === 'h-layout' ? renderHLayout() : renderStandardLayout()}
      </ICUIFrameContainer>
    </div>
  );
};

export default ICUIEnhancedLayout;
