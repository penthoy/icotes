/**
 * UploadItem - Individual file upload item display
 * 
 * Shows file info, upload progress, and status for each file in the upload queue.
 */
import React from 'react';
import { File, Image, Video, Music, X, Check, AlertCircle } from 'lucide-react';
import { UploadItem as UploadItemData } from '../../../hooks/useMediaUpload';

interface UploadItemProps {
  item: UploadItemData;
  onRemove: () => void;
  disabled?: boolean;
}

export default function UploadItem({ item, onRemove, disabled }: UploadItemProps) {
  const { file, status, progress, error } = item;

  const getFileIcon = () => {
    if (file.type.startsWith('image/')) {
      return <Image size={16} className="text-blue-500" />;
    }
    if (file.type.startsWith('video/')) {
      return <Video size={16} className="text-purple-500" />;
    }
    if (file.type.startsWith('audio/')) {
      return <Music size={16} className="text-green-500" />;
    }
    return <File size={16} className="text-gray-500" />;
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return <Check size={16} className="text-green-500" />;
      case 'error':
        return <AlertCircle size={16} className="text-red-500" />;
      default:
        return null;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusColor = () => {
    switch (status) {
      case 'completed':
        return 'text-green-600';
      case 'error':
        return 'text-red-600';
      case 'uploading':
        return 'text-blue-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className="flex items-center gap-3 p-3 bg-white border rounded-lg hover:bg-gray-50">
      {/* File Icon */}
      <div className="flex-shrink-0">
        {getFileIcon()}
      </div>

      {/* File Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-gray-900 truncate">
            {file.name}
          </p>
          {getStatusIcon()}
        </div>
        
        <div className="flex items-center gap-2 mt-1">
          <p className="text-xs text-gray-500">
            {formatFileSize(file.size)}
          </p>
          <span className="text-xs text-gray-400">•</span>
          <p className={`text-xs ${getStatusColor()}`}>
            {status === 'uploading' ? `${progress}%` : status}
          </p>
        </div>

        {/* Progress Bar */}
        {status === 'uploading' && (
          <div className="mt-2">
            <div className="w-full bg-gray-200 rounded-full h-1">
              <div
                className="bg-blue-500 h-1 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <p className="text-xs text-red-600 mt-1">
            {error}
          </p>
        )}
      </div>

      {/* Remove Button */}
      <button
        onClick={onRemove}
        className="flex-shrink-0 p-1 text-gray-400 hover:text-red-500 rounded"
        disabled={disabled || status === 'uploading'}
        title="Remove file"
        aria-label="Remove file"
      >
        <X size={16} />
      </button>
    </div>
  );
}
