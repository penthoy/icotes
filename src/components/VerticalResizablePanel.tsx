import React, { useState, useRef, useEffect } from "react";

interface VerticalResizablePanelProps {
  children: React.ReactNode;
  initialHeight?: number;
  minHeight?: number;
  maxHeight?: number;
  className?: string;
}

const VerticalResizablePanel: React.FC<VerticalResizablePanelProps> = ({
  children,
  initialHeight = 300,
  minHeight = 100,
  maxHeight = 600,
  className = "",
}) => {
  const [height, setHeight] = useState(initialHeight);
  const [isResizing, setIsResizing] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing || !panelRef.current) return;
      
      const panelRect = panelRef.current.getBoundingClientRect();
      const newHeight = panelRect.bottom - e.clientY;
      
      if (newHeight >= minHeight && newHeight <= maxHeight) {
        setHeight(newHeight);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

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
  }, [isResizing, minHeight, maxHeight]);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  return (
    <div
      ref={panelRef}
      className={`relative ${className}`}
      style={{ height: `${height}px` }}
    >
      {/* Resize handle at the top */}
      <div
        className="absolute top-0 left-0 right-0 h-1 bg-border hover:bg-accent-foreground/20 cursor-ns-resize transition-colors z-10"
        onMouseDown={handleMouseDown}
      />
      {children}
    </div>
  );
};

export default VerticalResizablePanel;
