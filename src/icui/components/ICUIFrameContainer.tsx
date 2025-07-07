/**
 * ICUI Framework - Frame Container Component
 * The foundational responsive frame that handles layout and border detection
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useICUIResponsive } from '../hooks/icui-use-responsive';
import { 
  ICUIFrameConfig, 
  ICUISize, 
  ICUIPosition, 
  ICUIBorder,
  ICUIResizeHandle 
} from '../types/icui-layout';

interface ICUIFrameContainerProps {
  /** Unique identifier for the frame */
  id: string;
  /** Configuration for the frame behavior */
  config?: Partial<ICUIFrameConfig>;
  /** Child components to render within the frame */
  children: React.ReactNode;
  /** CSS classes for styling */
  className?: string;
  /** Inline styles */
  style?: React.CSSProperties;
  /** Callback when frame is resized */
  onResize?: (size: ICUISize) => void;
  /** Callback when borders are detected */
  onBorderDetected?: (borders: ICUIBorder) => void;
}

const DEFAULT_CONFIG: ICUIFrameConfig = {
  id: 'icui-frame',
  responsive: true,
  borderDetection: true,
  minPanelSize: { width: 200, height: 100 },
  resizeHandleSize: 4,
  snapThreshold: 10,
};

/**
 * ICUI Frame Container - The foundational responsive frame component
 * Provides responsive layout with border detection and resize capabilities
 */
export const ICUIFrameContainer: React.FC<ICUIFrameContainerProps> = ({
  id,
  config = {},
  children,
  className = '',
  style = {},
  onResize,
  onBorderDetected,
}) => {
  const frameConfig = { ...DEFAULT_CONFIG, ...config, id };
  const { viewport, isMinBreakpoint } = useICUIResponsive();
  const frameRef = useRef<HTMLDivElement>(null);
  
  const [frameSize, setFrameSize] = useState<ICUISize>({
    width: 0,
    height: 0,
  });
  
  const [borders, setBorders] = useState<ICUIBorder>({
    top: false,
    right: false,
    bottom: false,
    left: false,
  });
  
  const [resizeHandles, setResizeHandles] = useState<ICUIResizeHandle[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [dragHandle, setDragHandle] = useState<ICUIResizeHandle | null>(null);

  /**
   * Detect borders based on frame position and viewport
   */
  const detectBorders = useCallback(() => {
    if (!frameRef.current || !frameConfig.borderDetection) return;
    
    const rect = frameRef.current.getBoundingClientRect();
    const threshold = frameConfig.snapThreshold;
    
    const newBorders: ICUIBorder = {
      top: rect.top <= threshold,
      right: Math.abs(rect.right - viewport.width) <= threshold,
      bottom: Math.abs(rect.bottom - viewport.height) <= threshold,
      left: rect.left <= threshold,
    };
    
    setBorders(newBorders);
    onBorderDetected?.(newBorders);
  }, [frameConfig.borderDetection, frameConfig.snapThreshold, viewport, onBorderDetected]);

  /**
   * Update frame size and trigger callbacks
   */
  const updateFrameSize = useCallback(() => {
    if (!frameRef.current) return;
    
    const rect = frameRef.current.getBoundingClientRect();
    const newSize: ICUISize = {
      width: rect.width,
      height: rect.height,
    };
    
    setFrameSize(newSize);
    onResize?.(newSize);
  }, [onResize]);

  /**
   * Generate resize handles based on detected borders
   */
  const generateResizeHandles = useCallback(() => {
    if (!frameRef.current) return;
    
    const rect = frameRef.current.getBoundingClientRect();
    const handles: ICUIResizeHandle[] = [];
    
    // Add vertical resize handle on the right if not at border
    if (!borders.right) {
      handles.push({
        id: `${frameConfig.id}-resize-right`,
        direction: 'vertical',
        position: { x: rect.width - frameConfig.resizeHandleSize / 2, y: 0 },
        active: false,
      });
    }
    
    // Add horizontal resize handle on the bottom if not at border
    if (!borders.bottom) {
      handles.push({
        id: `${frameConfig.id}-resize-bottom`,
        direction: 'horizontal',
        position: { x: 0, y: rect.height - frameConfig.resizeHandleSize / 2 },
        active: false,
      });
    }
    
    setResizeHandles(handles);
  }, [borders, frameConfig.id, frameConfig.resizeHandleSize]);

  /**
   * Handle mouse down on resize handle
   */
  const handleMouseDown = useCallback((handle: ICUIResizeHandle) => {
    setIsDragging(true);
    setDragHandle(handle);
    
    // Update handle state
    setResizeHandles(prev => 
      prev.map(h => ({ ...h, active: h.id === handle.id }))
    );
  }, []);

  /**
   * Handle mouse move during resize
   */
  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging || !dragHandle || !frameRef.current) return;
    
    const rect = frameRef.current.getBoundingClientRect();
    
    if (dragHandle.direction === 'vertical') {
      const newWidth = e.clientX - rect.left;
      if (newWidth >= frameConfig.minPanelSize.width) {
        frameRef.current.style.width = `${newWidth}px`;
      }
    } else {
      const newHeight = e.clientY - rect.top;
      if (newHeight >= frameConfig.minPanelSize.height) {
        frameRef.current.style.height = `${newHeight}px`;
      }
    }
  }, [isDragging, dragHandle, frameConfig.minPanelSize]);

  /**
   * Handle mouse up to end resize
   */
  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setDragHandle(null);
    
    // Reset handle states
    setResizeHandles(prev => 
      prev.map(h => ({ ...h, active: false }))
    );
    
    // Update frame size after resize
    updateFrameSize();
  }, [updateFrameSize]);

  // Effect for resize observer
  useEffect(() => {
    if (!frameRef.current) return;
    
    const resizeObserver = new ResizeObserver(() => {
      updateFrameSize();
      detectBorders();
      generateResizeHandles();
    });
    
    resizeObserver.observe(frameRef.current);
    
    return () => resizeObserver.disconnect();
  }, [updateFrameSize, detectBorders, generateResizeHandles]);

  // Effect for mouse events during drag
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // Effect for responsive changes
  useEffect(() => {
    if (frameConfig.responsive) {
      detectBorders();
      generateResizeHandles();
    }
  }, [viewport, detectBorders, generateResizeHandles, frameConfig.responsive]);

  // Compute frame classes
  const frameClasses = [
    'icui-frame-container',
    'relative',
    'w-full',
    'h-full',
    'overflow-hidden',
    borders.top && 'border-t-2',
    borders.right && 'border-r-2',
    borders.bottom && 'border-b-2',
    borders.left && 'border-l-2',
    'border-gray-300',
    'dark:border-gray-700',
    isDragging && 'select-none',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div
      ref={frameRef}
      id={frameConfig.id}
      className={frameClasses}
      style={{
        minWidth: frameConfig.minPanelSize.width,
        minHeight: frameConfig.minPanelSize.height,
        ...style,
      }}
      data-icui-frame="true"
      data-icui-responsive={frameConfig.responsive}
      data-icui-border-detection={frameConfig.borderDetection}
    >
      {/* Frame content */}
      <div className="icui-frame-content w-full h-full">
        {children}
      </div>
      
      {/* Resize handles */}
      {resizeHandles.map(handle => (
        <div
          key={handle.id}
          className={`
            icui-resize-handle
            absolute
            bg-blue-500
            opacity-0
            hover:opacity-100
            transition-opacity
            cursor-${handle.direction === 'vertical' ? 'col' : 'row'}-resize
            ${handle.active ? 'opacity-100 bg-blue-600' : ''}
            ${handle.direction === 'vertical' ? 'w-1 h-full' : 'w-full h-1'}
          `}
          style={{
            left: handle.position.x,
            top: handle.position.y,
            width: handle.direction === 'vertical' ? frameConfig.resizeHandleSize : '100%',
            height: handle.direction === 'horizontal' ? frameConfig.resizeHandleSize : '100%',
          }}
          onMouseDown={() => handleMouseDown(handle)}
          data-icui-handle={handle.id}
          data-icui-direction={handle.direction}
        />
      ))}
      
      {/* Debug info in development */}
      {process.env.NODE_ENV === 'development' && (
        <div className="icui-debug-info absolute top-2 right-2 bg-black bg-opacity-50 text-white text-xs p-2 rounded">
          <div>Frame: {frameConfig.id}</div>
          <div>Size: {frameSize.width}x{frameSize.height}</div>
          <div>Breakpoint: {viewport.width}px</div>
          <div>Borders: {Object.entries(borders).filter(([_, v]) => v).map(([k]) => k).join(', ') || 'none'}</div>
        </div>
      )}
    </div>
  );
};

export default ICUIFrameContainer;
