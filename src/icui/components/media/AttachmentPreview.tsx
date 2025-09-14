/**
 * AttachmentPreview - Display component for media attachments
 * 
 * Renders different previews based on file type (image, audio, file)
 * with download and removal capabilities.
 */
import React from 'react';
import { Download, X, File, Image as ImageIcon, Music, Video, FileText } from 'lucide-react';
import { MediaAttachment } from '../../services/mediaService';

interface AttachmentPreviewProps {
  attachment: MediaAttachment;
  onRemove?: () => void;
  onDownload?: () => void;
  showRemoveButton?: boolean;
  compact?: boolean;
  className?: string;
}

export default function AttachmentPreview({
  attachment,
  onRemove,
  onDownload,
  showRemoveButton = false,
  compact = false,
  className = ''
}: AttachmentPreviewProps) {
  const { kind, mime, size, meta } = attachment;

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = () => {
    switch (kind) {
      case 'image':
        return <ImageIcon size={16} className="text-blue-500" />;
      case 'audio':
        return <Music size={16} className="text-green-500" />;
      default:
        if (mime.startsWith('video/')) {
          return <Video size={16} className="text-purple-500" />;
        }
        if (mime.includes('pdf')) {
          return <FileText size={16} className="text-red-500" />;
        }
        return <File size={16} className="text-gray-500" />;
    }
  };

  const getFileName = () => {
    return meta?.original_name || attachment.path.split('/').pop() || 'Unknown file';
  };

  if (compact) {
    return (
      <div className={`inline-flex items-center gap-2 px-2 py-1 bg-gray-100 rounded text-sm ${className}`}>
        {getFileIcon()}
        <span className="truncate max-w-32">{getFileName()}</span>
        {showRemoveButton && onRemove && (
          <button
            onClick={onRemove}
            className="p-0.5 hover:bg-gray-200 rounded"
            title="Remove attachment"
          >
            <X size={12} />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className={`border rounded-lg p-3 bg-white hover:bg-gray-50 ${className}`}>
      <div className="flex items-start gap-3">
        {/* Preview Area */}
        <div className="flex-shrink-0">
          {kind === 'image' ? (
            <div className="w-16 h-16 bg-gray-100 rounded flex items-center justify-center overflow-hidden">
              {/* TODO: Add actual image preview when we have the URL */}
              <ImageIcon size={24} className="text-gray-400" />
            </div>
          ) : (
            <div className="w-16 h-16 bg-gray-100 rounded flex items-center justify-center">
              {getFileIcon()}
            </div>
          )}
        </div>

        {/* File Info */}
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-900 truncate">
            {getFileName()}
          </p>
          <div className="flex items-center gap-2 mt-1 text-sm text-gray-500">
            <span>{formatFileSize(size)}</span>
            <span>•</span>
            <span className="capitalize">{kind}</span>
          </div>
          {meta?.duration && (
            <p className="text-xs text-gray-400 mt-1">
              Duration: {meta.duration}s
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex-shrink-0 flex gap-1">
          {onDownload && (
            <button
              onClick={onDownload}
              className="p-2 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded"
              title="Download file"
              aria-label="Download file"
            >
              <Download size={16} />
            </button>
          )}
          
          {showRemoveButton && onRemove && (
            <button
              onClick={onRemove}
              className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
              title="Remove attachment"
              aria-label="Remove attachment"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
