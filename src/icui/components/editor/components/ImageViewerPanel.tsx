/**
 * Image Viewer Panel Component
 * 
 * Displays image files in the editor with loading states,
 * error handling, metadata display, and interactive zoom/pan tools.
 * 
 * Features:
 * - Zoom tool (default): Click to zoom in, scroll wheel to zoom in/out
 * - Pan tool: Click and drag to pan around the image
 * - Toolbar with zoom controls and tool selection
 * 
 * Future extension points:
 * - Crop tool: Select area for cropping
 * - Annotate tool: Add text/arrows/shapes
 * - Measure tool: Measure distances in pixels
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';

/** Available tools for the image viewer */
type ImageViewerTool = 'zoom' | 'pan';
// Future tools: 'crop' | 'annotate' | 'measure'

interface ImageViewerPanelProps {
  filePath: string;
  fileName: string;
}

/** Zoom constraints and step values */
const ZOOM_CONFIG = {
  MIN: 0.1,      // 10% minimum
  MAX: 10,       // 1000% maximum
  DEFAULT: 1,    // 100% default (fit to view will override)
  STEP: 0.25,    // 25% increment for button clicks
  WHEEL_STEP: 0.1 // 10% increment for wheel scroll
};

export const ImageViewerPanel: React.FC<ImageViewerPanelProps> = ({ filePath, fileName }) => {
  // Image loading state
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [imageDimensions, setImageDimensions] = useState<{ width: number; height: number } | null>(null);

  // Zoom and pan state
  const [zoom, setZoom] = useState(ZOOM_CONFIG.DEFAULT);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [activeTool, setActiveTool] = useState<ImageViewerTool>('pan');
  
  // Panning interaction state
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  
  // Refs for DOM elements
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  const imageUrl = `/api/files/raw?path=${encodeURIComponent(filePath)}`;

  /**
   * Clamp zoom value within allowed range
   */
  const clampZoom = useCallback((value: number): number => {
    return Math.max(ZOOM_CONFIG.MIN, Math.min(ZOOM_CONFIG.MAX, value));
  }, []);

  /**
   * Handle image load - calculate initial zoom to fit image in view
   */
  const handleImageLoad = useCallback((e: React.SyntheticEvent<HTMLImageElement>) => {
    setImageLoaded(true);
    setImageError(false);
    const img = e.currentTarget;
    setImageDimensions({ width: img.naturalWidth, height: img.naturalHeight });
    
    // Calculate fit-to-view zoom if container available
    if (containerRef.current) {
      const container = containerRef.current;
      const containerWidth = container.clientWidth - 32; // Account for padding
      const containerHeight = container.clientHeight - 32;
      
      const fitZoom = Math.min(
        containerWidth / img.naturalWidth,
        containerHeight / img.naturalHeight,
        1 // Don't zoom in beyond 100% for fit
      );
      
      setZoom(clampZoom(fitZoom));
      setPan({ x: 0, y: 0 }); // Center the image
    }
  }, [clampZoom]);

  /**
   * Handle image load error
   */
  const handleImageError = useCallback(() => {
    setImageError(true);
    setImageLoaded(false);
  }, []);

  /**
   * Handle mouse wheel for zooming
   */
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -ZOOM_CONFIG.WHEEL_STEP : ZOOM_CONFIG.WHEEL_STEP;
    setZoom(prev => clampZoom(prev + delta));
  }, [clampZoom]);

  /**
   * Handle mouse down for pan/zoom interaction
   */
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (activeTool === 'pan') {
      // Start panning
      setIsPanning(true);
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
      e.preventDefault();
    } else if (activeTool === 'zoom') {
      // Click to zoom in, shift+click to zoom out
      const delta = e.shiftKey ? -ZOOM_CONFIG.STEP : ZOOM_CONFIG.STEP;
      setZoom(prev => clampZoom(prev + delta));
    }
  }, [activeTool, pan.x, pan.y, clampZoom]);

  /**
   * Handle mouse move for panning
   */
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isPanning) {
      setPan({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y
      });
    }
  }, [isPanning, panStart]);

  /**
   * Handle mouse up to end panning
   */
  const handleMouseUp = useCallback(() => {
    setIsPanning(false);
  }, []);

  /**
   * Reset zoom and pan to fit image in view
   */
  const handleResetView = useCallback(() => {
    if (containerRef.current && imageDimensions) {
      const container = containerRef.current;
      const containerWidth = container.clientWidth - 32;
      const containerHeight = container.clientHeight - 32;
      
      const fitZoom = Math.min(
        containerWidth / imageDimensions.width,
        containerHeight / imageDimensions.height,
        1
      );
      
      setZoom(clampZoom(fitZoom));
      setPan({ x: 0, y: 0 });
    }
  }, [imageDimensions, clampZoom]);

  /**
   * Zoom to 100% (actual size)
   */
  const handleActualSize = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  /**
   * Increment zoom by step
   */
  const handleZoomIn = useCallback(() => {
    setZoom(prev => clampZoom(prev + ZOOM_CONFIG.STEP));
  }, [clampZoom]);

  /**
   * Decrement zoom by step
   */
  const handleZoomOut = useCallback(() => {
    setZoom(prev => clampZoom(prev - ZOOM_CONFIG.STEP));
  }, [clampZoom]);

  // Stop panning if mouse leaves the container
  useEffect(() => {
    const handleGlobalMouseUp = () => setIsPanning(false);
    window.addEventListener('mouseup', handleGlobalMouseUp);
    return () => window.removeEventListener('mouseup', handleGlobalMouseUp);
  }, []);

  /**
   * Get cursor style based on active tool
   */
  const getCursor = (): string => {
    if (activeTool === 'pan') {
      return isPanning ? 'grabbing' : 'grab';
    }
    return 'zoom-in';
  };

  /**
   * Format zoom percentage for display
   */
  const formatZoomPercent = (value: number): string => {
    return `${Math.round(value * 100)}%`;
  };

  return (
    <div className="h-full w-full flex flex-col" style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
      {/* Info Bar */}
      <div 
        className="flex items-center gap-2 px-4 py-2 border-b" 
        style={{ borderColor: 'var(--icui-border)', backgroundColor: 'var(--icui-bg-secondary)' }}
      >
        <span className="text-sm font-medium" style={{ color: 'var(--icui-text-primary)' }}>
          {fileName}
        </span>
        {imageDimensions && (
          <span className="text-xs" style={{ color: 'var(--icui-text-secondary)' }}>
            {imageDimensions.width} × {imageDimensions.height}
          </span>
        )}
      </div>

      {/* Image Display Area */}
      <div 
        ref={containerRef}
        className="flex-1 flex items-center justify-center overflow-hidden relative"
        style={{ 
          cursor: getCursor(),
          backgroundColor: 'var(--icui-bg-tertiary)'
        }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {!imageError ? (
          <div 
            className="relative"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: 'center center',
              transition: isPanning ? 'none' : 'transform 0.1s ease-out'
            }}
          >
            <img 
              ref={imageRef}
              src={imageUrl}
              alt={fileName}
              draggable={false}
              style={{ 
                imageRendering: zoom > 2 ? 'pixelated' : 'auto',
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
                opacity: imageLoaded ? 1 : 0,
                transition: 'opacity 0.2s',
                userSelect: 'none'
              }}
              onLoad={handleImageLoad}
              onError={handleImageError}
            />
            {!imageLoaded && (
              <div className="absolute inset-0 flex items-center justify-center" style={{ minWidth: 100, minHeight: 100 }}>
                <div 
                  className="w-8 h-8 border-2 rounded-full animate-spin" 
                  style={{ 
                    borderColor: 'var(--icui-border)',
                    borderTopColor: 'var(--icui-accent)'
                  }} 
                />
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 p-8" style={{ color: 'var(--icui-text-secondary)' }}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span className="text-sm">Failed to load image: {fileName}</span>
            <span className="text-xs">The file may be corrupted or in an unsupported format</span>
          </div>
        )}
      </div>

      {/* Bottom Toolbar */}
      {imageLoaded && (
        <div 
          className="flex items-center justify-between px-4 py-2 border-t gap-4"
          style={{ 
            borderColor: 'var(--icui-border)', 
            backgroundColor: 'var(--icui-bg-secondary)' 
          }}
        >
          {/* Tool Selection - Left Side */}
          <div className="flex items-center gap-1">
            {/* Zoom Tool Button */}
            <button
              onClick={() => setActiveTool('zoom')}
              className="icui-toolbar-btn flex items-center justify-center"
              style={{
                width: 32,
                height: 32,
                backgroundColor: activeTool === 'zoom' ? 'var(--icui-accent)' : 'var(--icui-bg-tertiary)',
                color: activeTool === 'zoom' ? 'white' : 'var(--icui-text-primary)'
              }}
              title="Zoom Tool (Click to zoom in, Shift+Click to zoom out)"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                <line x1="11" y1="8" x2="11" y2="14"/>
                <line x1="8" y1="11" x2="14" y2="11"/>
              </svg>
            </button>
            
            {/* Pan/Hand Tool Button */}
            <button
              onClick={() => setActiveTool('pan')}
              className="icui-toolbar-btn flex items-center justify-center"
              style={{
                width: 32,
                height: 32,
                backgroundColor: activeTool === 'pan' ? 'var(--icui-accent)' : 'var(--icui-bg-tertiary)',
                color: activeTool === 'pan' ? 'white' : 'var(--icui-text-primary)'
              }}
              title="Pan Tool (Click and drag to move image)"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 11V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v0"/>
                <path d="M14 10V4a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v2"/>
                <path d="M10 10.5V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v8"/>
                <path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/>
              </svg>
            </button>
            
            {/* Divider */}
            <div 
              className="w-px h-6 mx-2" 
              style={{ backgroundColor: 'var(--icui-border)' }} 
            />
            
            {/* Future Tools Placeholder - uncomment to add
            <button
              disabled
              className="icui-toolbar-btn flex items-center justify-center opacity-40"
              style={{ width: 32, height: 32 }}
              title="Crop Tool (Coming soon)"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M6.13 1L6 16a2 2 0 0 0 2 2h15"/>
                <path d="M1 6.13L16 6a2 2 0 0 1 2 2v15"/>
              </svg>
            </button>
            */}
          </div>

          {/* Zoom Controls - Center/Right */}
          <div className="flex items-center gap-2">
            {/* Zoom Out Button */}
            <button
              onClick={handleZoomOut}
              disabled={zoom <= ZOOM_CONFIG.MIN}
              className="icui-toolbar-btn flex items-center justify-center disabled:opacity-40"
              style={{ width: 28, height: 28 }}
              title="Zoom Out"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
            </button>
            
            {/* Zoom Percentage Display */}
            <span 
              className="text-xs font-mono min-w-[50px] text-center select-none"
              style={{ color: 'var(--icui-text-primary)' }}
              title="Current zoom level"
            >
              {formatZoomPercent(zoom)}
            </span>
            
            {/* Zoom In Button */}
            <button
              onClick={handleZoomIn}
              disabled={zoom >= ZOOM_CONFIG.MAX}
              className="icui-toolbar-btn flex items-center justify-center disabled:opacity-40"
              style={{ width: 28, height: 28 }}
              title="Zoom In"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19"/>
                <line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
            </button>
            
            {/* Divider */}
            <div 
              className="w-px h-6 mx-1" 
              style={{ backgroundColor: 'var(--icui-border)' }} 
            />
            
            {/* Reset/Fit to View Button */}
            <button
              onClick={handleResetView}
              className="icui-toolbar-btn px-2 py-1 text-xs"
              title="Fit to View"
            >
              Fit
            </button>
            
            {/* Actual Size Button */}
            <button
              onClick={handleActualSize}
              className="icui-toolbar-btn px-2 py-1 text-xs"
              title="Actual Size (100%)"
            >
              100%
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
