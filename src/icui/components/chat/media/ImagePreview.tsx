/**
 * ImagePreview Component
 * 
 * Displays images in chat messages with support for:
 * - File or URL-based images
 * - Metadata display (dimensions, size, name)
 * - Click to expand functionality
 * - Copy to clipboard
 * - Error handling and loading states
 * - Full accessibility support
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Copy, X, ZoomIn, AlertCircle, Loader2 } from 'lucide-react';

export interface ImagePreviewProps {
  /** Image source URL */
  src?: string;
  /** Image file object */
  file?: File;
  /** Alt text for accessibility */
  alt?: string;
  /** Additional CSS classes */
  className?: string;
  /** Maximum width for the preview */
  maxWidth?: number;
  /** Maximum height for the preview */
  maxHeight?: number;
  /** Show metadata (dimensions, size, etc.) */
  showMetadata?: boolean;
  /** Callback when image is clicked */
  onClick?: () => void;
}

interface ImageMetadata {
  width?: number;
  height?: number;
  size?: number;
  name?: string;
  type?: string;
}

export const ImagePreview: React.FC<ImagePreviewProps> = ({
  src,
  file,
  alt,
  className = '',
  maxWidth = 400,
  maxHeight = 300,
  showMetadata = true,
  onClick
}) => {
  const [imageUrl, setImageUrl] = useState<string | null>(src || null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [metadata, setMetadata] = useState<ImageMetadata>({});
  const imgRef = useRef<HTMLImageElement>(null);

  // Convert file to URL if file prop is provided
  useEffect(() => {
    if (file) {
      setIsLoading(true);
      setHasError(false);
      const url = URL.createObjectURL(file);
      setImageUrl(url);
      setMetadata({
        size: file.size,
        name: file.name,
        type: file.type
      });

      return () => {
        URL.revokeObjectURL(url);
      };
    }
  }, [file]);

  // Add this effect (outside the selected range) to react to src updates when no file is provided:
  useEffect(() => {
    if (!file && src) {
      setIsLoading(true);
      setHasError(false);
    }
  }, [file, src]);

  // Handle image load to get dimensions
  const handleImageLoad = useCallback(() => {
    setIsLoading(false);
    setHasError(false);

    if (imgRef.current) {
      setMetadata(prev => ({
        ...prev,
        width: imgRef.current!.naturalWidth,
        height: imgRef.current!.naturalHeight
      }));
    }
  }, []);

  // Handle image error
  const handleImageError = useCallback(() => {
    setIsLoading(false);
    setHasError(true);
  }, []);

  // Handle click to expand
  const handleClick = useCallback(() => {
    if (onClick) {
      onClick();
    } else {
      setIsExpanded(true);
    }
  }, [onClick]);

  // Handle escape key to close expanded view
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isExpanded) {
        setIsExpanded(false);
      }
    };

    if (isExpanded) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isExpanded]);

  // Copy image to clipboard
  const handleCopyImage = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();

    try {
      if (file) {
        // Copy file to clipboard
        await navigator.clipboard.write([
          new ClipboardItem({
            [file.type]: file
          })
        ]);
      } else if (imageUrl) {
        // Copy image URL to clipboard
        await navigator.clipboard.writeText(imageUrl);
      }
    } catch (error) {
      console.error('Failed to copy image:', error);
    }
  }, [file, imageUrl]);

  // Format file size
  const formatFileSize = useCallback((bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }, []);

  // Don't render if no image source
  if (!imageUrl && !src) {
    return null;
  }

  // Error state
  if (hasError) {
    return (
      <div 
        className={`flex items-center gap-2 p-3 border rounded ${className}`}
        style={{
          backgroundColor: 'var(--icui-bg-secondary)',
          borderColor: 'var(--icui-border-subtle)',
          color: 'var(--icui-text-secondary)'
        }}
      >
        <AlertCircle size={16} className="text-red-500" />
        <span className="text-sm">Failed to load image</span>
      </div>
    );
  }

  return (
    <>
      {/* Main image preview */}
      <div 
        className={`relative group cursor-pointer ${className}`}
        onClick={handleClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleClick();
          }
        }}
        aria-label={alt || 'Image preview - click to expand'}
      >
        {/* Loading state */}
        {isLoading && (
          <div 
            className="flex items-center justify-center border rounded"
            style={{
              width: maxWidth,
              height: maxHeight,
              backgroundColor: 'var(--icui-bg-secondary)',
              borderColor: 'var(--icui-border-subtle)'
            }}
          >
            <Loader2 size={24} className="animate-spin" style={{ color: 'var(--icui-text-secondary)' }} />
          </div>
        )}

        {/* Image */}
        <img
          ref={imgRef}
          src={imageUrl || src}
          alt={alt || metadata.name || 'Image'}
          className={`border rounded object-contain ${isLoading ? 'hidden' : 'block'}`}
          style={{
            maxWidth,
            maxHeight,
            borderColor: 'var(--icui-border-subtle)'
          }}
          onLoad={handleImageLoad}
          onError={handleImageError}
        />

        {/* Hover overlay */}
        <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all duration-200 rounded flex items-center justify-center">
          <ZoomIn 
            size={24} 
            className="text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200" 
          />
        </div>

        {/* Copy button */}
        <button
          onClick={handleCopyImage}
          className="absolute top-2 right-2 p-1 rounded bg-black bg-opacity-50 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200 hover:bg-opacity-70"
          title="Copy image"
          aria-label="Copy image to clipboard"
        >
          <Copy size={14} />
        </button>
      </div>

      {/* Metadata */}
      {showMetadata && (metadata.width || metadata.size || metadata.name) && (
        <div className="mt-2 text-xs" style={{ color: 'var(--icui-text-secondary)' }}>
          <div className="flex flex-wrap gap-3">
            {metadata.name && (
              <span className="font-medium">{metadata.name}</span>
            )}
            {metadata.width && metadata.height && (
              <span>{metadata.width} × {metadata.height}</span>
            )}
            {metadata.size && (
              <span>{formatFileSize(metadata.size)}</span>
            )}
            {metadata.type && (
              <span className="uppercase">{metadata.type.split('/')[1]}</span>
            )}
          </div>
        </div>
      )}

      {/* Expanded view modal */}
      {isExpanded && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-80"
          onClick={() => setIsExpanded(false)}
        >
          <div className="relative max-w-[90vw] max-h-[90vh]">
            <img
              src={imageUrl || src}
              alt={alt || metadata.name || 'Image'}
              className="max-w-full max-h-full object-contain"
            />
            <button
              onClick={() => setIsExpanded(false)}
              className="absolute top-4 right-4 p-2 rounded-full bg-black bg-opacity-50 text-white hover:bg-opacity-70 transition-colors"
              aria-label="Close expanded view"
            >
              <X size={20} />
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default ImagePreview; 