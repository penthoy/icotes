/**
 * ICUI Layout Component
 * Provides IDE-like layout functionality extracted from ICUITest3/4
 * Handles resizable panels, docking areas, and layout persistence
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { ICUIFrameContainer } from './ICUIFrameContainer';
import { ICUISplitPanel } from './ICUISplitPanel';
import { ICUIPanelArea, ICUIPanel } from './ICUIPanelArea';
import { ICUIPanelType } from './ICUIPanelSelector';

export interface ICUILayoutArea {
  id: string;
  name: string;
  width?: number | string;
  height?: number | string;
  minWidth?: number;
  minHeight?: number;
  panelIds: string[];
  size?: number;
  collapsible?: boolean;
  visible?: boolean;
  activePanelId?: string;
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

export interface ICUILayoutProps {
  panels: ICUIPanel[];
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

export const ICUILayout: React.FC<ICUILayoutProps> = ({
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

  // Add ref to track previous layout for change detection
  const prevLayoutRef = useRef<ICUILayoutConfig>(currentLayout);
  
  // Track the last layout prop we received to avoid re-processing same prop
  const lastLayoutPropRef = useRef<ICUILayoutConfig | null>(null);

  // Helper: sanitize a layout so that each area's activePanelId exists in its panelIds
  const sanitizeLayout = useCallback((cfg: ICUILayoutConfig): ICUILayoutConfig => {
    const sanitizedAreas: Record<string, ICUILayoutArea> = {};
    Object.keys(cfg.areas || {}).forEach((areaId) => {
      const area = cfg.areas[areaId];
      if (!area) return;
      let nextActive = area.activePanelId;
      if (nextActive && !area.panelIds.includes(nextActive)) {
        console.warn(
          `[LAYOUT-SANITIZE] Area "${areaId}": invalid activePanelId "${nextActive}" not in panelIds, correcting`,
          area.panelIds
        );
        nextActive = area.panelIds[0];
      }
      sanitizedAreas[areaId] = { ...area, activePanelId: nextActive };
    });
    return { ...cfg, areas: sanitizedAreas };
  }, []);
  
  // Log layout changes to detect cascading updates
  useEffect(() => {
    const prev = prevLayoutRef.current;
    const changedAreas: string[] = [];
    
    Object.keys(currentLayout.areas).forEach(areaId => {
      const prevArea = prev.areas[areaId];
      const currArea = currentLayout.areas[areaId];
      
      if (prevArea?.activePanelId !== currArea?.activePanelId) {
        changedAreas.push(`${areaId}: ${prevArea?.activePanelId || 'none'} -> ${currArea?.activePanelId || 'none'}`);
      }
    });
    
    if (changedAreas.length > 0) {
      console.log(`[LAYOUT-STATE-CHANGE] Active panels changed:`, changedAreas);
    }
    
    prevLayoutRef.current = currentLayout;
  }, [currentLayout]);

  // Load persisted layout on mount
  useEffect(() => {
    if (persistLayout && layoutKey) {
      const saved = localStorage.getItem(layoutKey);
      if (saved) {
        try {
          const parsedLayout = JSON.parse(saved);
          // Merge persisted layout with provided layout to ensure new panels are included
          const mergedAreas: Record<string, ICUILayoutArea> = {};
          
          Object.keys(layout?.areas || {}).forEach(areaId => {
            const providedArea = layout?.areas[areaId];
            const persistedArea = parsedLayout.areas?.[areaId];
            
            if (providedArea) {
              // Start with provided area as base
              mergedAreas[areaId] = { ...providedArea };
              
              // Merge persisted properties if they exist
              if (persistedArea) {
                // Preserve size/visibility preferences from persisted state
                if (persistedArea.size !== undefined) mergedAreas[areaId].size = persistedArea.size;
                if (persistedArea.visible !== undefined) mergedAreas[areaId].visible = persistedArea.visible;
                
                // CRITICAL FIX: Validate activePanelId exists in panelIds before using it
                if (persistedArea.activePanelId && 
                    providedArea.panelIds.includes(persistedArea.activePanelId)) {
                  mergedAreas[areaId].activePanelId = persistedArea.activePanelId;
                } else if (persistedArea.activePanelId) {
                  console.warn(
                    `[LAYOUT-LOAD] Ignoring invalid activePanelId "${persistedArea.activePanelId}" ` +
                    `for area "${areaId}". Panel not in panelIds:`, providedArea.panelIds
                  );
                  // Keep the provided activePanelId or use first panel as fallback
                  mergedAreas[areaId].activePanelId = providedArea.activePanelId || providedArea.panelIds[0];
                }
              }
            }
          });
          
          const mergedLayout = {
            ...parsedLayout,
            areas: mergedAreas,
          };
          // Final sanitation in case upstream state was corrupted
          const sanitized = sanitizeLayout(mergedLayout);
          lastLayoutPropRef.current = sanitized; // Track this as processed
          setCurrentLayout(sanitized);
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
  }, [persistLayout, layoutKey, sanitizeLayout]);

  // Update layout when prop changes (only if the prop itself changed, not our internal state)
  useEffect(() => {
    if (!layout) return;

    // Check if this is the same prop object we already processed
    if (lastLayoutPropRef.current && JSON.stringify(layout) === JSON.stringify(lastLayoutPropRef.current)) {
      return; // Already processed this prop value
    }

    // Check if the prop is different from our current state
    if (JSON.stringify(layout) === JSON.stringify(currentLayout)) {
      // Prop matches current state, just update our ref and skip
      lastLayoutPropRef.current = layout;
      return;
    }

    // New prop value that differs from current state - sanitize and apply
    const sanitized = sanitizeLayout(layout);

    // If sanitization yields the same structure we already hold, ignore
    if (JSON.stringify(sanitized) === JSON.stringify(currentLayout)) {
      console.log('[LAYOUT-PROP-IGNORE] Prop update sanitized to current layout, skipping');
      lastLayoutPropRef.current = layout;
      return;
    }

    console.log('[LAYOUT-PROP-SYNC] Applying layout prop update');
    lastLayoutPropRef.current = layout;
    setCurrentLayout(sanitized);
  }, [layout, sanitizeLayout]);

  // Save layout changes and call onLayoutChange
  const [isInitialized, setIsInitialized] = useState(false);
  useEffect(() => {
    if (!isInitialized) {
      setIsInitialized(true);
      return; // Don't call onLayoutChange during initialization
    }
    
    if (persistLayout && layoutKey) {
      localStorage.setItem(layoutKey, JSON.stringify(currentLayout));
    }
    
    // Always call onLayoutChange - let parent decide what to do
    // The prop-change effect will ignore echoes by checking lastLayoutPropRef
    onLayoutChange?.(currentLayout);
  }, [currentLayout, persistLayout, layoutKey, isInitialized, onLayoutChange]);

  // Get panels for a specific area
  const getPanelsForArea = useCallback((areaId: string): ICUIPanel[] => {
    const area = currentLayout.areas[areaId];
    if (!area) return [];
    
    return area.panelIds
      .map(id => panels.find(p => p.id === id))
      .filter(Boolean) as ICUIPanel[];
  }, [panels, currentLayout]);

  // Handle panel activation
  const handlePanelActivate = useCallback((areaId: string, panelId: string) => {
    // Trace activation intent for debugging oscillations
    console.log(`[LAYOUT-ACTIVATE-REQ] area=${areaId} panel=${panelId}`);
    console.log(`[SURGICAL-DEBUG] Layout handlePanelActivate called for area=${areaId}, panel=${panelId}`);
    setCurrentLayout(prev => {
      const area = prev.areas[areaId];
      if (!area) {
        console.warn(`[LAYOUT-ACTIVATE] Area not found: ${areaId}`);
        return prev;
      }
      if (area.activePanelId === panelId) {
        // No-op to prevent redundant updates and flicker
        console.log(`[SURGICAL-DEBUG] Layout activation ignored - already active: area=${areaId}, panel=${panelId}`);
        return prev;
      }
      
      // CRITICAL FIX: Validate panelId exists in area before activating
      if (!area.panelIds.includes(panelId)) {
        console.error(
          `[LAYOUT-ACTIVATE] Cannot activate panel "${panelId}" in area "${areaId}". ` +
          `Panel not found in panelIds:`, area.panelIds
        );
        return prev;
      }
      
      console.log(`[SURGICAL-DEBUG] Layout updating state: area=${areaId}, activePanelId=${panelId}`);
      return {
        ...prev,
        areas: {
          ...prev.areas,
          [areaId]: {
            ...area,
            activePanelId: panelId,
          }
        }
      };
    });
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
          <ICUIPanelArea
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
                <ICUIPanelArea
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
                  <ICUIPanelArea
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
              <ICUIPanelArea
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
              <ICUIPanelArea
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
                <ICUIPanelArea
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
                  <ICUIPanelArea
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
          <ICUIPanelArea
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

export default ICUILayout;
