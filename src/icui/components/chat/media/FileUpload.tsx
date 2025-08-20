/**
 * FileUpload Component
 * 
 * Handles file uploads in chat with support for:
 * - Drag and drop interface
 * - File type validation and size limits
 * - File preview system
 * - Multiple file selection
 * - Progress indicators
 * - Error handling
 */

import React, { useState, useCallback, useRef, DragEvent } from 'react';
import { Upload, X, File, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import ImagePreview from './ImagePreview';

export interface FileUploadProps {
  /** Accepted file types (MIME types or extensions) */
  accept?: string;
  /** Maximum file size in bytes */
  maxSize?: number;
  /** Maximum number of files */
  maxFiles?: number;
  /** Allow multiple file selection */
  multiple?: boolean;
  /** Callback when files are selected/dropped */
  onFilesSelected?: (files: File[]) => void;
  /** Callback when files are uploaded */
  onFilesUploaded?: (files: File[]) => void;
  /** Callback for upload progress */
  onUploadProgress?: (progress: number) => void;
  /** Additional CSS classes */
  className?: string;
  /** Disabled state */
  disabled?: boolean;
}

interface FileItem {
  file: File;
  id: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
}

const DEFAULT_MAX_SIZE = 10 * 1024 * 1024; // 10MB
const DEFAULT_MAX_FILES = 5;

export const FileUpload: React.FC<FileUploadProps> = ({
  accept = '*/*',
  maxSize = DEFAULT_MAX_SIZE,
  maxFiles = DEFAULT_MAX_FILES,
  multiple = true,
  onFilesSelected,
  onFilesUploaded,
  onUploadProgress,
  className = '',
  disabled = false
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Validate file type
  const isValidFileType = useCallback((file: File): boolean => {
    if (accept === '*/*') return true;
    
    const acceptedTypes = accept.split(',').map(type => type.trim());
    
    return acceptedTypes.some(type => {
      if (type.startsWith('.')) {
        // Extension check
        return file.name.toLowerCase().endsWith(type.toLowerCase());
      } else {
        // MIME type check
        return file.type.match(type.replace('*', '.*'));
      }
    });
  }, [accept]);

  // Validate file size
  const isValidFileSize = useCallback((file: File): boolean => {
    return file.size <= maxSize;
  }, [maxSize]);

  // Process selected files
  const processFiles = useCallback((selectedFiles: FileList | File[]) => {
    const fileArray = Array.from(selectedFiles);
    const validFiles: FileItem[] = [];
    const errors: string[] = [];

    // Check total file count
    if (files.length + fileArray.length > maxFiles) {
      errors.push(`Maximum ${maxFiles} files allowed`);
      return;
    }

    fileArray.forEach((file, index) => {
      const id = `${Date.now()}_${index}_${Math.random().toString(36).substr(2, 9)}`;

      // Validate file type
      if (!isValidFileType(file)) {
        errors.push(`${file.name}: Invalid file type`);
        return;
      }

      // Validate file size
      if (!isValidFileSize(file)) {
        errors.push(`${file.name}: File too large (max ${formatFileSize(maxSize)})`);
        return;
      }

      validFiles.push({
        file,
        id,
        status: 'pending',
        progress: 0
      });
    });

    if (errors.length > 0) {
      console.error('File validation errors:', errors);
      // You could show these errors in a toast/notification
      return;
    }

    setFiles(prev => [...prev, ...validFiles]);
    
    if (onFilesSelected) {
      onFilesSelected(validFiles.map(item => item.file));
    }
  }, [files.length, maxFiles, isValidFileType, isValidFileSize, maxSize, onFilesSelected]);

  // Handle file input change
  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (selectedFiles && selectedFiles.length > 0) {
      processFiles(selectedFiles);
    }
    // Reset input value to allow selecting the same file again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [processFiles]);

  // Handle drag over
  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragOver(true);
    }
  }, [disabled]);

  // Handle drag leave
  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  // Handle drop
  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    if (disabled) return;

    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles && droppedFiles.length > 0) {
      processFiles(droppedFiles);
    }
  }, [disabled, processFiles]);

  // Remove file
  const removeFile = useCallback((id: string) => {
    setFiles(prev => prev.filter(item => item.id !== id));
  }, []);

  // Format file size
  const formatFileSize = useCallback((bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }, []);

  // Get file icon
  const getFileIcon = useCallback((file: File): string => {
    const type = file.type;
    if (type.startsWith('image/')) return '🖼️';
    if (type.startsWith('video/')) return '🎥';
    if (type.startsWith('audio/')) return '🎵';
    if (type.includes('pdf')) return '📄';
    if (type.includes('text')) return '📝';
    if (type.includes('zip') || type.includes('rar')) return '📦';
    return '📁';
  }, []);

  // Simulate upload (replace with actual upload logic)
  const handleUpload = useCallback(async () => {
    if (files.length === 0 || isUploading) return;

    setIsUploading(true);

    try {
      for (const fileItem of files) {
        if (fileItem.status !== 'pending') continue;

        // Update status to uploading
        setFiles(prev => prev.map(item => 
          item.id === fileItem.id 
            ? { ...item, status: 'uploading', progress: 0 }
            : item
        ));

        // Simulate upload progress
        for (let progress = 0; progress <= 100; progress += 10) {
          await new Promise(resolve => setTimeout(resolve, 100));
          
          setFiles(prev => prev.map(item => 
            item.id === fileItem.id 
              ? { ...item, progress }
              : item
          ));

          if (onUploadProgress) {
            onUploadProgress(progress);
          }
        }

        // Mark as success
        setFiles(prev => prev.map(item => 
          item.id === fileItem.id 
            ? { ...item, status: 'success', progress: 100 }
            : item
        ));
      }

      if (onFilesUploaded) {
        onFilesUploaded(files.map(item => item.file));
      }
    } catch (error) {
      console.error('Upload failed:', error);
      // Mark files as error
      setFiles(prev => prev.map(item => 
        item.status === 'uploading' 
          ? { ...item, status: 'error', error: 'Upload failed' }
          : item
      ));
    } finally {
      setIsUploading(false);
    }
  }, [files, isUploading, onUploadProgress, onFilesUploaded]);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Drop zone */}
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-6 text-center transition-all duration-200
          ${isDragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-gray-400'}
        `}
        style={{
          backgroundColor: isDragOver ? 'var(--icui-accent-subtle)' : 'var(--icui-bg-secondary)',
          borderColor: isDragOver ? 'var(--icui-accent)' : 'var(--icui-border-subtle)',
          color: 'var(--icui-text-primary)'
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleFileInputChange}
          className="hidden"
          disabled={disabled}
        />

        <Upload size={48} className="mx-auto mb-4 opacity-50" />
        
        <div className="space-y-2">
          <p className="text-lg font-medium">
            {isDragOver ? 'Drop files here' : 'Drop files or click to upload'}
          </p>
          <p className="text-sm opacity-70">
            {accept !== '*/*' && `Accepted: ${accept}`}
            {maxSize < DEFAULT_MAX_SIZE && ` • Max size: ${formatFileSize(maxSize)}`}
            {maxFiles < DEFAULT_MAX_FILES && ` • Max files: ${maxFiles}`}
          </p>
        </div>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="font-medium" style={{ color: 'var(--icui-text-primary)' }}>
              Selected Files ({files.length})
            </h4>
            {files.some(f => f.status === 'pending') && (
              <button
                onClick={handleUpload}
                disabled={isUploading}
                className="px-3 py-1 text-sm rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isUploading ? 'Uploading...' : 'Upload All'}
              </button>
            )}
          </div>

          <div className="space-y-2">
            {files.map((fileItem) => (
              <div
                key={fileItem.id}
                className="flex items-center gap-3 p-3 border rounded"
                style={{
                  backgroundColor: 'var(--icui-bg-secondary)',
                  borderColor: 'var(--icui-border-subtle)'
                }}
              >
                {/* File preview */}
                <div className="flex-shrink-0">
                  {fileItem.file.type.startsWith('image/') ? (
                    <ImagePreview
                      file={fileItem.file}
                      maxWidth={40}
                      maxHeight={40}
                      showMetadata={false}
                    />
                  ) : (
                    <div className="w-10 h-10 flex items-center justify-center">
                      <span className="text-2xl">{getFileIcon(fileItem.file)}</span>
                    </div>
                  )}
                </div>

                {/* File info */}
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate" style={{ color: 'var(--icui-text-primary)' }}>
                    {fileItem.file.name}
                  </p>
                  <p className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
                    {formatFileSize(fileItem.file.size)}
                  </p>
                  
                  {/* Progress bar */}
                  {fileItem.status === 'uploading' && (
                    <div className="mt-1">
                      <div 
                        className="h-1 rounded-full overflow-hidden"
                        style={{ backgroundColor: 'var(--icui-bg-tertiary)' }}
                      >
                        <div 
                          className="h-full bg-blue-500 transition-all duration-300"
                          style={{ width: `${fileItem.progress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Error message */}
                  {fileItem.status === 'error' && fileItem.error && (
                    <p className="text-sm text-red-500 mt-1">{fileItem.error}</p>
                  )}
                </div>

                {/* Status icon */}
                <div className="flex-shrink-0">
                  {fileItem.status === 'pending' && (
                    <File size={16} style={{ color: 'var(--icui-text-secondary)' }} />
                  )}
                  {fileItem.status === 'uploading' && (
                    <Loader2 size={16} className="animate-spin text-blue-500" />
                  )}
                  {fileItem.status === 'success' && (
                    <CheckCircle size={16} className="text-green-500" />
                  )}
                  {fileItem.status === 'error' && (
                    <AlertCircle size={16} className="text-red-500" />
                  )}
                </div>

                {/* Remove button */}
                <button
                  onClick={() => removeFile(fileItem.id)}
                  className="flex-shrink-0 p-1 rounded hover:bg-red-100 text-red-500"
                  title="Remove file"
                  disabled={fileItem.status === 'uploading'}
                >
                  <X size={16} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUpload; 