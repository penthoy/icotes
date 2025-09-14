/**
 * ImagePreview - Specialized image display component
 * 
 * Shows actual image preview with proper loading states and fallbacks.
 */
import React, { useState } from 'react';
import { Download, X, Maximize2, AlertCircle } from 'lucide-react';
import { MediaAttachment } from '../../services/mediaService';
import { mediaService } from '../../services/mediaService';

interface ImagePreviewProps {
  attachment: MediaAttachment;
  onRemove?: () => void;
  onDownload?: () => void;
  showRemoveButton?: boolean;
  size?: 'small' | 'medium' | 'large';
  className?: string;
}

export default function ImagePreview({
  attachment,
  onRemove,
  onDownload,
  showRemoveButton = false,
  size = 'medium',
  className = ''
}: ImagePreviewProps) {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [showFullSize, setShowFullSize] = useState(false);

  const sizeClasses = {
    small: 'w-16 h-16',
    medium: 'w-32 h-32',
    large: 'w-48 h-48'
  };

  const imageUrl = mediaService.getAttachmentUrl(attachment);
  const fileName = attachment.meta?.original_name || attachment.path.split('/').pop() || 'Image';

  const handleImageLoad = () => {
    setImageLoaded(true);
    setImageError(false);
  };

  const handleImageError = () => {
    setImageError(true);
    setImageLoaded(false);
  };

  const handleDownload = () => {
    if (onDownload) {
      onDownload();
    } else {
      // Default download behavior
      const link = document.createElement('a');
      link.href = imageUrl;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <>
      <div className={`relative border rounded-lg overflow-hidden bg-white ${className}`}>
        {/* Image Container */}
        <div className={`relative ${sizeClasses[size]} bg-gray-100 flex items-center justify-center`}>
          {!imageError ? (
            <>
              <img
                src={imageUrl}
                alt={fileName}
                className={`w-full h-full object-cover transition-opacity duration-200 ${
                  imageLoaded ? 'opacity-100' : 'opacity-0'
                }`}
                onLoad={handleImageLoad}
                onError={handleImageError}
              />
              {!imageLoaded && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-6 h-6 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center gap-2 p-4 text-gray-400">
              <AlertCircle size={20} />
              <span className="text-xs text-center">Failed to load image</span>
            </div>
          )}

          {/* Overlay Actions */}
          {imageLoaded && !imageError && (
            <div className="absolute inset-0 bg-black bg-opacity-0 hover:bg-opacity-20 transition-all duration-200 flex items-center justify-center opacity-0 hover:opacity-100">
              <div className="flex gap-2">
                <button
                  onClick={() => setShowFullSize(true)}
                  className="p-2 bg-white bg-opacity-90 hover:bg-opacity-100 rounded-full shadow-lg"
                  title="View full size"
                  aria-label="View full size"
                >
                  <Maximize2 size={16} />
                </button>
                <button
                  onClick={handleDownload}
                  className="p-2 bg-white bg-opacity-90 hover:bg-opacity-100 rounded-full shadow-lg"
                  title="Download image"
                  aria-label="Download image"
                >
                  <Download size={16} />
                </button>
              </div>
            </div>
          )}

          {/* Remove Button */}
          {showRemoveButton && onRemove && (
            <button
              onClick={onRemove}
              className="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full shadow-lg hover:bg-red-600"
              title="Remove image"
              aria-label="Remove image"
            >
              <X size={12} />
            </button>
          )}
        </div>

        {/* File Info */}
        <div className="p-2">
          <p className="text-sm font-medium text-gray-900 truncate" title={fileName}>
            {fileName}
          </p>
          <p className="text-xs text-gray-500">
            {formatFileSize(attachment.size)}
          </p>
          {attachment.meta?.dimensions && (
            <p className="text-xs text-gray-400">
              {attachment.meta.dimensions.width}×{attachment.meta.dimensions.height}
            </p>
          )}
        </div>
      </div>

      {/* Full Size Modal */}
      {showFullSize && imageLoaded && !imageError && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
          onClick={() => setShowFullSize(false)}
        >
          <div className="relative max-w-full max-h-full">
            <img
              src={imageUrl}
              alt={fileName}
              className="max-w-full max-h-full object-contain"
              onClick={(e) => e.stopPropagation()}
            />
            <button
              onClick={() => setShowFullSize(false)}
              className="absolute top-4 right-4 p-2 bg-black bg-opacity-50 text-white rounded-full hover:bg-opacity-75"
              title="Close"
              aria-label="Close"
            >
              <X size={20} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
