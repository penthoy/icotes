/**
 * ICUI Framework - Split Panel Component
 * Implements horizontal and vertical split functionality with resizable handles
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { 
  ICUISplitConfig, 
  ICUISplitPanelState, 
  ICUISplitHandle, 
  ICUISplitPanelProps,
  ICUISplitDirection 
} from '../types/icui-split';

const DEFAULT_SPLIT_CONFIG: ICUISplitConfig = {
  id: 'icui-split',
  direction: 'horizontal',
  initialSplit: 50,
  minSize: 2, // Very small minimum - just enough to grab the handle
  collapsible: true,
  resizable: true,
  snapThreshold: 10,
};

/**
 * ICUI Split Panel - Provides horizontal and vertical split functionality
 * Supports resizing, collapsing, and nested splits
 */
export const ICUISplitPanel: React.FC<ICUISplitPanelProps> = ({
  id,
  config = {},
  className = '',
  style = {},
  onSplitChange,
  onPanelCollapse,
  firstPanel,
  secondPanel,
}) => {
  const splitConfig = { ...DEFAULT_SPLIT_CONFIG, ...config, id };
  const containerRef = useRef<HTMLDivElement>(null);
  const handleRef = useRef<HTMLDivElement>(null);
  const lastSplitRef = useRef<number>(splitConfig.initialSplit);
  
  const [splitState, setSplitState] = useState<ICUISplitPanelState>({
    splitPercentage: splitConfig.initialSplit,
    isFirstPanelCollapsed: false,
    isSecondPanelCollapsed: false,
    isDragging: false,
    dragStartPosition: 0,
    dragStartSplit: splitConfig.initialSplit,
  });

  const [splitHandle, setSplitHandle] = useState<ICUISplitHandle>({
    id: `${splitConfig.id}-handle`,
    direction: splitConfig.direction,
    position: splitConfig.initialSplit,
    active: false,
    // Thinner handle for a sleeker look (can still be grabbed easily)
    size: 4,
  });

  /**
   * Calculate split position based on mouse/touch position
   */
  const calculateSplitFromPosition = useCallback((clientPosition: number): number => {
    if (!containerRef.current) return lastSplitRef.current;
    
    const rect = containerRef.current.getBoundingClientRect();
    const isHorizontal = splitConfig.direction === 'horizontal';
    const containerSize = isHorizontal ? rect.width : rect.height;
    const relativePosition = isHorizontal 
      ? clientPosition - rect.left 
      : clientPosition - rect.top;
    
    const percentage = (relativePosition / containerSize) * 100;
    
    // Apply minimum and maximum constraints
    const minPercentage = (splitConfig.minSize / containerSize) * 100;
    const maxPercentage = splitConfig.maxSize 
      ? ((containerSize - splitConfig.maxSize) / containerSize) * 100
      : 100 - minPercentage;
    
    return Math.max(minPercentage, Math.min(maxPercentage, percentage));
  }, [splitConfig.direction, splitConfig.minSize, splitConfig.maxSize]);

  /**
   * Handle mouse down on split handle
   */
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (!splitConfig.resizable) return;
    
    e.preventDefault();
    const clientPosition = splitConfig.direction === 'horizontal' ? e.clientX : e.clientY;
    
    setSplitState(prev => ({
      ...prev,
      isDragging: true,
      dragStartPosition: clientPosition,
      dragStartSplit: prev.splitPercentage,
    }));
    
    setSplitHandle(prev => ({ ...prev, active: true }));
  }, [splitConfig.resizable, splitConfig.direction]);

  /**
   * Handle mouse move during drag - simple and smooth
   */
  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!splitState.isDragging) return;
    
    const clientPosition = splitConfig.direction === 'horizontal' ? e.clientX : e.clientY;
    const newSplit = calculateSplitFromPosition(clientPosition);
    
    // Update ref for next calculation
    lastSplitRef.current = newSplit;
    
    // Immediate state update for smooth dragging
    setSplitState(prev => ({ ...prev, splitPercentage: newSplit }));
    setSplitHandle(prev => ({ ...prev, position: newSplit }));
    
    // Throttled external callback
    if (onSplitChange) {
      onSplitChange(newSplit);
    }
  }, [splitState.isDragging, splitConfig.direction, calculateSplitFromPosition, onSplitChange]);

  /**
   * Handle mouse up to end drag
   */
  const handleMouseUp = useCallback(() => {
    setSplitState(prev => ({ ...prev, isDragging: false }));
    setSplitHandle(prev => ({ ...prev, active: false }));
  }, []);

  /**
   * Handle double-click to reset split to 50%
   */
  const handleDoubleClick = useCallback(() => {
    const newSplit = 50;
    setSplitState(prev => ({ ...prev, splitPercentage: newSplit }));
    setSplitHandle(prev => ({ ...prev, position: newSplit }));
    onSplitChange?.(newSplit);
  }, [onSplitChange]);

  /**
   * Collapse/expand panels
   */
  const togglePanelCollapse = useCallback((panel: 'first' | 'second') => {
    setSplitState(prev => {
      const isFirstPanel = panel === 'first';
      const currentlyCollapsed = isFirstPanel 
        ? prev.isFirstPanelCollapsed 
        : prev.isSecondPanelCollapsed;
      
      const newState = {
        ...prev,
        isFirstPanelCollapsed: isFirstPanel ? !currentlyCollapsed : prev.isFirstPanelCollapsed,
        isSecondPanelCollapsed: !isFirstPanel ? !currentlyCollapsed : prev.isSecondPanelCollapsed,
      };
      
      onPanelCollapse?.(panel, !currentlyCollapsed);
      return newState;
    });
  }, [onPanelCollapse]);

  // Effect for mouse events during drag
  useEffect(() => {
    if (splitState.isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = splitConfig.direction === 'horizontal' ? 'col-resize' : 'row-resize';
      document.body.style.userSelect = 'none';

      // IMPORTANT: iframe-based content (like the browser's PDF viewer) can capture mouse events,
      // which makes divider dragging feel "stuck" or only work in one direction.
      // While resizing, we disable pointer events on iframes via a global body class.
      document.body.classList.add('icui-resize-dragging');
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';

        document.body.classList.remove('icui-resize-dragging');
      };
    }
  }, [splitState.isDragging, handleMouseMove, handleMouseUp, splitConfig.direction]);

  // Calculate panel sizes
  const firstPanelSize = splitState.isFirstPanelCollapsed ? 0 : splitState.splitPercentage;
  const secondPanelSize = splitState.isSecondPanelCollapsed ? 0 : (100 - splitState.splitPercentage);
  const handlePosition = splitState.splitPercentage;

  // Compute CSS classes
  const containerClasses = [
    'icui-split-panel',
    'relative',
    'w-full',
    'h-full',
    'overflow-hidden',
    splitConfig.direction === 'horizontal' ? 'flex flex-row' : 'flex flex-col',
    splitState.isDragging && 'select-none',
    className,
  ].filter(Boolean).join(' ');

  const handleClasses = [
    'icui-split-handle',
    'absolute',
    // Neutral border / handle colour that adapts to theme
    'bg-gray-200 dark:bg-gray-700',
    'hover:bg-blue-400 dark:hover:bg-blue-600',
    'transition-colors',
    'duration-200',
    splitConfig.direction === 'horizontal' ? 'cursor-col-resize' : 'cursor-row-resize',
    splitHandle.active && 'bg-blue-500 dark:bg-blue-600',
    !splitConfig.resizable && 'pointer-events-none opacity-50',
  ].filter(Boolean).join(' ');

  const firstPanelClasses = [
    'icui-split-first-panel',
    'overflow-hidden',
    // Only apply transitions when not dragging
    !splitState.isDragging && 'transition-all duration-300',
    splitState.isFirstPanelCollapsed && 'hidden',
  ].filter(Boolean).join(' ');

  const secondPanelClasses = [
    'icui-split-second-panel',
    'overflow-hidden',
    // Only apply transitions when not dragging
    !splitState.isDragging && 'transition-all duration-300',
    splitState.isSecondPanelCollapsed && 'hidden',
  ].filter(Boolean).join(' ');

  return (
    <div
      ref={containerRef}
      id={splitConfig.id}
      className={containerClasses}
      style={style}
      data-icui-split="true"
      data-icui-direction={splitConfig.direction}
    >
      {/* First Panel */}
      <div
        className={firstPanelClasses}
        style={{
          [splitConfig.direction === 'horizontal' ? 'width' : 'height']: `${firstPanelSize}%`,
        }}
      >
        {firstPanel}
      </div>

      {/* Split Handle */}
      {splitConfig.resizable && !splitState.isFirstPanelCollapsed && !splitState.isSecondPanelCollapsed && (
        <div
          ref={handleRef}
          className={handleClasses}
          style={{
            // Positioning & size
            [splitConfig.direction === 'horizontal' ? 'left' : 'top']: `${handlePosition}%`,
            [splitConfig.direction === 'horizontal' ? 'width' : 'height']: `${splitHandle.size}px`,
            [splitConfig.direction === 'horizontal' ? 'height' : 'width']: '100%',
            transform: splitConfig.direction === 'horizontal' 
              ? `translateX(-${splitHandle.size / 2}px)` 
              : `translateY(-${splitHandle.size / 2}px)`,
            // Use CSS variable so it adapts to any theme (Monokai, etc.)
            backgroundColor: 'var(--icui-border-subtle)',
            zIndex: 10,
          }}
          onMouseDown={handleMouseDown}
          onDoubleClick={handleDoubleClick}
          data-icui-handle={splitHandle.id}
          data-icui-direction={splitConfig.direction}
        >
          {/* Handle grip indicator */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className={`bg-gray-400 dark:bg-gray-500 ${
              splitConfig.direction === 'horizontal' 
                ? 'w-0.5 h-6' 
                : 'w-6 h-0.5'
            }`} />
          </div>
        </div>
      )}

      {/* Second Panel */}
      <div
        className={secondPanelClasses}
        style={{
          [splitConfig.direction === 'horizontal' ? 'width' : 'height']: `${secondPanelSize}%`,
        }}
      >
        {secondPanel}
      </div>

      {/* Collapse/Expand Controls */}
      {/* REMOVED: Arrow navigation buttons as requested */}
      {/* {splitConfig.collapsible && (
        <div className="icui-split-controls absolute top-2 right-2 flex gap-1 z-20">
          <button
            className="px-2 py-1 text-xs bg-gray-200 hover:bg-gray-300 rounded"
            onClick={() => togglePanelCollapse('first')}
            title="Toggle First Panel"
          >
            {splitState.isFirstPanelCollapsed ? '→' : '←'}
          </button>
          <button
            className="px-2 py-1 text-xs bg-gray-200 hover:bg-gray-300 rounded"
            onClick={() => togglePanelCollapse('second')}
            title="Toggle Second Panel"
          >
            {splitState.isSecondPanelCollapsed ? '←' : '→'}
          </button>
        </div>
      )} */}

      {/* Debug info removed for cleaner development experience */}
    </div>
  );
};

export default ICUISplitPanel;
