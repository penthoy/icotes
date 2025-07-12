import React, { useState, useRef, useEffect, useCallback } from "react";
import { ChevronLeft, ChevronRight, Maximize2, Minimize2 } from "lucide-react";
import { Button } from "../ui/button";

interface ResizablePanelProps {
  children: React.ReactNode;
  initialWidth?: number;
  minWidth?: number;
  maxWidth?: number;
  className?: string;
  collapsible?: boolean;
  maximizable?: boolean;
  onCollapse?: (isCollapsed: boolean) => void;
  onMaximize?: (isMaximized: boolean) => void;
}

const ResizablePanel: React.FC<ResizablePanelProps> = ({
  children,
  initialWidth = 240,
  minWidth = 180,
  maxWidth = 400,
  className = "",
  collapsible = true,
  maximizable = true,
  onCollapse,
  onMaximize,
}) => {
  const [width, setWidth] = useState(initialWidth);
  const [isResizing, setIsResizing] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [preCollapseWidth, setPreCollapseWidth] = useState(initialWidth);
  const [preMaximizeWidth, setPreMaximizeWidth] = useState(initialWidth);
  const panelRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isResizing || isCollapsed || isMaximized) return;
    
    const newWidth = e.clientX;
    if (newWidth >= minWidth && newWidth <= maxWidth) {
      setWidth(newWidth);
    }
  }, [isResizing, isCollapsed, isMaximized, minWidth, maxWidth]);

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
  }, []);

  useEffect(() => {
    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "col-resize";
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
      setPreCollapseWidth(width);
      setWidth(0);
    } else {
      setWidth(preCollapseWidth);
    }
    setIsCollapsed(newCollapsed);
    onCollapse?.(newCollapsed);
  };

  const handleMaximize = () => {
    if (isCollapsed) return;
    
    const newMaximized = !isMaximized;
    if (newMaximized) {
      setPreMaximizeWidth(width);
      // Get parent container width to maximize to
      const parentWidth = panelRef.current?.parentElement?.clientWidth || window.innerWidth;
      setWidth(parentWidth * 0.8); // Use 80% of parent width for maximized state
    } else {
      setWidth(preMaximizeWidth);
    }
    setIsMaximized(newMaximized);
    onMaximize?.(newMaximized);
  };

  const currentWidth = isCollapsed ? 0 : width;

  return (
    <div
      ref={panelRef}
      className={`relative flex ${className} ${isCollapsed ? 'w-0 overflow-hidden' : ''}`}
      style={{ width: isCollapsed ? '0px' : `${width}px` }}
    >
      {!isCollapsed && (
        <div className="flex-1 min-w-0">
          {children}
        </div>
      )}
      
      {/* Resize Handle */}
      <div className="relative flex flex-col">
        {!isCollapsed && !isMaximized && (
          <div
            className="absolute top-0 -right-1 w-2 h-full bg-transparent hover:bg-accent-foreground/20 cursor-col-resize transition-colors z-10"
            onMouseDown={handleMouseDown}
          />
        )}
        
        {/* Control Buttons */}
        <div className="flex flex-col items-center gap-1 p-1 bg-muted/30 border-l border-border">
          {collapsible && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCollapse}
              className="h-6 w-6 p-0"
              title={isCollapsed ? "Expand panel" : "Collapse panel"}
            >
              {isCollapsed ? (
                <ChevronRight className="h-3 w-3" />
              ) : (
                <ChevronLeft className="h-3 w-3" />
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
    </div>
  );
};

export default ResizablePanel;
