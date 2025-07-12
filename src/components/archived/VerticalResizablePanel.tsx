import React, { useState, useRef, useEffect, useCallback } from "react";
import { ChevronDown, ChevronUp, Maximize2, Minimize2 } from "lucide-react";
import { Button } from "../ui/button";

interface VerticalResizablePanelProps {
  children: React.ReactNode;
  initialHeight?: number;
  minHeight?: number;
  maxHeight?: number;
  className?: string;
  collapsible?: boolean;
  maximizable?: boolean;
  onCollapse?: (isCollapsed: boolean) => void;
  onMaximize?: (isMaximized: boolean) => void;
  onResize?: (height: number) => void;
}

const VerticalResizablePanel: React.FC<VerticalResizablePanelProps> = ({
  children,
  initialHeight = 300,
  minHeight = 100,
  maxHeight = 600,
  className = "",
  collapsible = true,
  maximizable = true,
  onCollapse,
  onMaximize,
  onResize,
}) => {
  const [height, setHeight] = useState(initialHeight);
  const [isResizing, setIsResizing] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [preCollapseHeight, setPreCollapseHeight] = useState(initialHeight);
  const [preMaximizeHeight, setPreMaximizeHeight] = useState(initialHeight);
  const panelRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isResizing || !panelRef.current || isCollapsed || isMaximized) return;
    
    const panelRect = panelRef.current.getBoundingClientRect();
    const newHeight = panelRect.bottom - e.clientY;
    
    if (newHeight >= minHeight && newHeight <= maxHeight) {
      setHeight(newHeight);
      onResize?.(newHeight);
    }
  }, [isResizing, isCollapsed, isMaximized, minHeight, maxHeight, onResize]);

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
  }, []);

  useEffect(() => {
    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "ns-resize";
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
    };
  }, [isResizing, handleMouseMove, handleMouseUp]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (isCollapsed || isMaximized) return;
    e.preventDefault();
    setIsResizing(true);
  };

  const handleCollapse = () => {
    if (isMaximized) return;
    
    const newCollapsed = !isCollapsed;
    if (newCollapsed) {
      setPreCollapseHeight(height);
      setHeight(0);
    } else {
      setHeight(preCollapseHeight);
    }
    setIsCollapsed(newCollapsed);
    onCollapse?.(newCollapsed);
  };

  const handleMaximize = () => {
    if (isCollapsed) return;
    
    const newMaximized = !isMaximized;
    if (newMaximized) {
      setPreMaximizeHeight(height);
      // Get parent container height to maximize to
      const parentHeight = panelRef.current?.parentElement?.clientHeight || window.innerHeight;
      setHeight(parentHeight * 0.8); // Use 80% of parent height for maximized state
    } else {
      setHeight(preMaximizeHeight);
    }
    setIsMaximized(newMaximized);
    onMaximize?.(newMaximized);
  };

  const currentHeight = isCollapsed ? 0 : height;

  return (
    <div
      ref={panelRef}
      className={`relative flex flex-col ${className} ${isCollapsed ? 'h-0 overflow-hidden' : ''}`}
      style={{ height: isCollapsed ? '0px' : `${height}px` }}
    >
      {/* Control Bar */}
      <div className="flex items-center justify-between p-1 bg-muted/30 border-b border-border flex-shrink-0">
        {!isCollapsed && !isMaximized && (
          <div
            className="absolute top-0 left-0 right-0 h-1 bg-border hover:bg-accent-foreground/20 cursor-ns-resize transition-colors z-10"
            onMouseDown={handleMouseDown}
          />
        )}
        
        <div className="flex items-center gap-1">
          {collapsible && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCollapse}
              className="h-6 w-6 p-0"
              title={isCollapsed ? "Expand panel" : "Collapse panel"}
            >
              {isCollapsed ? (
                <ChevronUp className="h-3 w-3" />
              ) : (
                <ChevronDown className="h-3 w-3" />
              )}
            </Button>
          )}
          
          {maximizable && !isCollapsed && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleMaximize}
              className="h-6 w-6 p-0"
              title={isMaximized ? "Restore panel" : "Maximize panel"}
            >
              {isMaximized ? (
                <Minimize2 className="h-3 w-3" />
              ) : (
                <Maximize2 className="h-3 w-3" />
              )}
            </Button>
          )}
        </div>
      </div>
      
      {!isCollapsed && (
        <div className="flex-1 min-h-0 overflow-hidden">
          {children}
        </div>
      )}
    </div>
  );
};

export default VerticalResizablePanel;
