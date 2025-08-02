/**
 * ICUI Framework - Base Panel Component
 * Generic panel component that can be inherited by any specific panel type
 */

import React, { useState, useRef, useCallback } from 'react';
import { 
  ICUIBasePanelProps, 
  ICUIPanelState, 
  ICUIPanelPosition 
} from '../types/icui-panel';
import { ICUIPanelHeader } from './ICUIPanelHeader';
import { ICUIPanelContent } from './ICUIPanelContent';

/**
 * Base Panel Component
 * Provides common functionality for all panel types
 */
export const ICUIBasePanel: React.FC<ICUIBasePanelProps> = ({
  panel,
  children,
  className = '',
  onStateChange,
  onPositionChange,
  onConfigChange,
  onClose,
  headerProps = {},
  contentProps = {},
}) => {
  const panelRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [isResizing, setIsResizing] = useState(false);
  const [resizeDirection, setResizeDirection] = useState<string>('');

  // Handle state changes
  const handleStateChange = useCallback((newState: ICUIPanelState) => {
    if (onStateChange) {
      onStateChange(newState);
    }
  }, [onStateChange]);

  // Handle mouse down for dragging (improved mouse event handling)
  const handleMouseDown = useCallback((event: React.MouseEvent) => {
    if (!panel.config.draggable || panel.state !== 'normal') return;
    
    // Prevent default browser drag behavior
    event.preventDefault();
    event.stopPropagation();
    
    const rect = panelRef.current?.getBoundingClientRect();
    if (rect) {
      const offsetX = event.clientX - rect.left;
      const offsetY = event.clientY - rect.top;
      
      setDragOffset({ x: offsetX, y: offsetY });
      setIsDragging(true);
      
      // Add CSS class to indicate dragging
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'move';
    }
  }, [panel.config.draggable, panel.state]);

  // Handle mouse down for resizing
  const handleResizeMouseDown = useCallback((event: React.MouseEvent, direction: string) => {
    if (!panel.config.resizable || panel.state !== 'normal') return;
    
    event.preventDefault();
    event.stopPropagation();
    setIsResizing(true);
    setResizeDirection(direction);
  }, [panel.config.resizable, panel.state]);

  // Handle mouse move for dragging and resizing (improved performance)
  const handleMouseMove = useCallback((event: MouseEvent) => {
    // Prevent default to avoid text selection during drag
    event.preventDefault();
    
    if (isDragging && onPositionChange) {
      requestAnimationFrame(() => {
        const newPosition: Partial<ICUIPanelPosition> = {
          x: Math.max(0, event.clientX - dragOffset.x),
          y: Math.max(0, event.clientY - dragOffset.y),
        };
        
        // Ensure panel stays within viewport bounds
        const viewport = {
          width: window.innerWidth,
          height: window.innerHeight,
        };
        
        newPosition.x = Math.min(viewport.width - 100, newPosition.x); // Keep at least 100px visible
        newPosition.y = Math.min(viewport.height - 40, newPosition.y); // Keep header visible
        
        onPositionChange({
          ...panel.position,
          ...newPosition,
        });
      });
    } else if (isResizing && onPositionChange) {
      requestAnimationFrame(() => {
        const rect = panelRef.current?.getBoundingClientRect();
        if (!rect) return;

        let newPosition = { ...panel.position };
        const minWidth = panel.config.minSize?.width || 200;
        const minHeight = panel.config.minSize?.height || 100;
        const maxWidth = panel.config.maxSize?.width || 1200;
        const maxHeight = panel.config.maxSize?.height || 800;

        switch (resizeDirection) {
          case 'se': // Southeast
            newPosition.width = Math.min(maxWidth, Math.max(minWidth, event.clientX - rect.left));
            newPosition.height = Math.min(maxHeight, Math.max(minHeight, event.clientY - rect.top));
            break;
          case 'sw': // Southwest
            const newWidth = Math.min(maxWidth, Math.max(minWidth, rect.right - event.clientX));
            newPosition.x = rect.right - newWidth;
            newPosition.width = newWidth;
            newPosition.height = Math.min(maxHeight, Math.max(minHeight, event.clientY - rect.top));
            break;
          case 'ne': // Northeast
            newPosition.width = Math.min(maxWidth, Math.max(minWidth, event.clientX - rect.left));
            const newHeight = Math.min(maxHeight, Math.max(minHeight, rect.bottom - event.clientY));
            newPosition.y = rect.bottom - newHeight;
            newPosition.height = newHeight;
            break;
          case 'nw': // Northwest
            const newW = Math.min(maxWidth, Math.max(minWidth, rect.right - event.clientX));
            const newH = Math.min(maxHeight, Math.max(minHeight, rect.bottom - event.clientY));
            newPosition.x = rect.right - newW;
            newPosition.y = rect.bottom - newH;
            newPosition.width = newW;
            newPosition.height = newH;
            break;
          case 'n': // North
            const northNewHeight = Math.min(maxHeight, Math.max(minHeight, rect.bottom - event.clientY));
            newPosition.y = rect.bottom - northNewHeight;
            newPosition.height = northNewHeight;
            break;
          case 's': // South
            newPosition.height = Math.min(maxHeight, Math.max(minHeight, event.clientY - rect.top));
            break;
          case 'w': // West
            const westNewWidth = Math.min(maxWidth, Math.max(minWidth, rect.right - event.clientX));
            newPosition.x = rect.right - westNewWidth;
            newPosition.width = westNewWidth;
            break;
          case 'e': // East
            newPosition.width = Math.min(maxWidth, Math.max(minWidth, event.clientX - rect.left));
            break;
        }

        onPositionChange(newPosition);
      });
    }
  }, [isDragging, isResizing, dragOffset, resizeDirection, onPositionChange, panel.position, panel.config.minSize, panel.config.maxSize]);

  // Handle mouse up (improved cleanup)
  const handleMouseUp = useCallback(() => {
    if (isDragging) {
      // Clean up drag state
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    }
    
    setIsDragging(false);
    setIsResizing(false);
    setResizeDirection('');
  }, [isDragging]);

  // Add/remove event listeners
  React.useEffect(() => {
    if (isDragging || isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, isResizing, handleMouseMove, handleMouseUp]);

  // Handle title change
  const handleTitleChange = useCallback((title: string) => {
    if (onConfigChange) {
      onConfigChange({ title });
    }
  }, [onConfigChange]);

  // Handle type change
  const handleTypeChange = useCallback((type: string) => {
    if (onConfigChange) {
      onConfigChange({ type: type as any });
    }
  }, [onConfigChange]);

  // Calculate panel styles
  const panelStyles: React.CSSProperties = {
    position: panel.state === 'maximized' ? 'fixed' : 'absolute',
    left: panel.state === 'maximized' ? 0 : panel.position.x,
    top: panel.state === 'maximized' ? 0 : panel.position.y,
    width: panel.state === 'maximized' ? '100vw' : panel.position.width,
    height: panel.state === 'maximized' ? '100vh' : panel.position.height,
    zIndex: panel.position.zIndex,
    visibility: panel.state === 'closed' ? 'hidden' : 'visible',
    opacity: isDragging ? 0.8 : 1,
    transition: isDragging ? 'none' : 'all 0.2s ease-in-out',
  };

  // Panel class names
  const panelClasses = [
    'icui-base-panel',
    `icui-panel-${panel.config.type}`,
    `icui-panel-${panel.state}`,
    panel.isActive ? 'icui-panel-active' : 'icui-panel-inactive',
    isDragging ? 'icui-panel-dragging' : '',
    className,
  ].filter(Boolean).join(' ');

  // Don't render if closed (unless it's being animated)
  if (panel.state === 'closed') {
    return null;
  }

  return (
    <div
      ref={panelRef}
      className={panelClasses}
      style={panelStyles}
      data-panel-id={panel.id}
      data-panel-type={panel.config.type}
    >
      {/* Panel Header */}
      <ICUIPanelHeader
        panel={panel}
        onStateChange={handleStateChange}
        onTitleChange={handleTitleChange}
        onTypeChange={handleTypeChange}
        onClose={onClose}
        onDragStart={handleMouseDown}
        {...headerProps}
      />
      
      {/* Panel Content */}
      {panel.state !== 'minimized' && (
        <ICUIPanelContent
          panel={panel}
          {...contentProps}
        >
          {children}
        </ICUIPanelContent>
      )}
      
      {/* Resize Handles */}
      {panel.config.resizable && panel.state === 'normal' && (
        <div className="icui-panel-resize-handles">
          {/* Corner handles */}
          <div 
            className="icui-resize-handle icui-resize-nw" 
            onMouseDown={(e) => handleResizeMouseDown(e, 'nw')}
            data-direction="nw" 
          />
          <div 
            className="icui-resize-handle icui-resize-ne" 
            onMouseDown={(e) => handleResizeMouseDown(e, 'ne')}
            data-direction="ne" 
          />
          <div 
            className="icui-resize-handle icui-resize-sw" 
            onMouseDown={(e) => handleResizeMouseDown(e, 'sw')}
            data-direction="sw" 
          />
          <div 
            className="icui-resize-handle icui-resize-se" 
            onMouseDown={(e) => handleResizeMouseDown(e, 'se')}
            data-direction="se" 
          />
          
          {/* Edge handles */}
          <div 
            className="icui-resize-handle icui-resize-n" 
            onMouseDown={(e) => handleResizeMouseDown(e, 'n')}
            data-direction="n" 
          />
          <div 
            className="icui-resize-handle icui-resize-s" 
            onMouseDown={(e) => handleResizeMouseDown(e, 's')}
            data-direction="s" 
          />
          <div 
            className="icui-resize-handle icui-resize-w" 
            onMouseDown={(e) => handleResizeMouseDown(e, 'w')}
            data-direction="w" 
          />
          <div 
            className="icui-resize-handle icui-resize-e" 
            onMouseDown={(e) => handleResizeMouseDown(e, 'e')}
            data-direction="e" 
          />
        </div>
      )}
    </div>
  );
};

export default ICUIBasePanel;
