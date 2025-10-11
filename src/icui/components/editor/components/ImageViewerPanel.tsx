/**
 * Image Viewer Panel Component
 * 
 * Displays image files in the editor with loading states,
 * error handling, and metadata display
 */

import React, { useState } from 'react';

interface ImageViewerPanelProps {
  filePath: string;
  fileName: string;
}

export const ImageViewerPanel: React.FC<ImageViewerPanelProps> = ({ filePath, fileName }) => {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [imageDimensions, setImageDimensions] = useState<{ width: number; height: number } | null>(null);

  const imageUrl = `/api/files/raw?path=${encodeURIComponent(filePath)}`;

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    setImageLoaded(true);
    setImageError(false);
    const img = e.currentTarget;
    setImageDimensions({ width: img.naturalWidth, height: img.naturalHeight });
  };

  const handleImageError = () => {
    setImageError(true);
    setImageLoaded(false);
  };

  return (
    <div className="h-full w-full flex flex-col" style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
      {/* Info Bar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b" style={{ borderColor: 'var(--icui-border)', backgroundColor: 'var(--icui-bg-secondary)' }}>
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
      <div className="flex-1 flex items-center justify-center p-8 overflow-auto">
        {!imageError ? (
          <div className="relative max-w-full max-h-full">
            <img 
              src={imageUrl}
              alt={fileName}
              className="max-w-full max-h-full object-contain"
              style={{ 
                imageRendering: 'auto',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                opacity: imageLoaded ? 1 : 0,
                transition: 'opacity 0.2s'
              }}
              onLoad={handleImageLoad}
              onError={handleImageError}
            />
            {!imageLoaded && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-8 h-8 border-2 rounded-full animate-spin" style={{ 
                  borderColor: 'var(--icui-border)',
                  borderTopColor: 'var(--icui-accent)'
                }} />
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
    </div>
  );
};
