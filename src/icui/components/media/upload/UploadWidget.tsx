/**
 * UploadWidget - Phase 3 UI Component
 * 
 * Floating upload widget that provides drag-and-drop interface,
 * file selection, and upload progress management.
 */
import React, { useCallback, useState, useRef } from 'react';
import { useMediaUpload, UseMediaUploadReturn, UploadItem as UploadItemType } from '../../../hooks/useMediaUpload';
import UploadItem from './UploadItem';
import { X, Upload, FileText, Image, Plus } from 'lucide-react';

interface UploadWidgetProps {
  isOpen: boolean;
  onClose: () => void;
  onFilesUploaded?: (attachments: any[]) => void;
  maxFiles?: number;
  allowedTypes?: string[];
  className?: string;
  externalQueue?: UseMediaUploadReturn;
  panelMode?: boolean;
  initialPosition?: { x: number; y: number };
}

export default function UploadWidget({
  isOpen,
  onClose,
  onFilesUploaded,
  maxFiles = 10,
  allowedTypes = ['image/*', 'video/*', 'audio/*', '.pdf', '.txt', '.doc', '.docx'],
  className = '',
  externalQueue,
  panelMode = false,
  initialPosition = { x: 16, y: typeof window !== 'undefined' ? (window.innerHeight - 420) : 100 }
}: UploadWidgetProps) {
  const internal = useMediaUpload();
  const api = externalQueue || internal;
  const { queue, isUploading, addFiles, removeFile, clearCompleted, uploadAll } = api;
  const [minimized, setMinimized] = useState(false);
  const [pos, setPos] = useState(initialPosition);
  const dragging = useRef(false);
  const offset = useRef({ x: 0, y: 0 });
  
  const [isDragActive, setIsDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      addFiles(files);
    }
  }, [addFiles]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      addFiles(files);
    }
    // Reset input value to allow selecting the same file again
    e.target.value = '';
  }, [addFiles]);

  const handleUploadAll = useCallback(async () => {
    try {
      const results = await uploadAll();
      if (results.length > 0 && onFilesUploaded) {
        onFilesUploaded(results);
      }
    } catch (error) {
      console.error('Upload failed:', error);
    }
  }, [uploadAll, onFilesUploaded]);

  const handleSelectFiles = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const completedUploads = queue.filter(item => item.status === 'completed');
  const hasFiles = queue.length > 0;
  const canUpload = queue.some(item => item.status === 'pending') && !isUploading;

  if (!isOpen) return null;
  if (minimized) {
    return (
      <div style={{ position: 'fixed', left: pos.x, top: pos.y }} className="z-50">
        <button onClick={() => setMinimized(false)} className="bg-blue-600 text-white px-3 py-2 rounded shadow text-sm flex items-center gap-2">
          <Upload size={14} /> Uploads ({queue.filter(q=>q.status!=='completed').length})
        </button>
      </div>
    );
  }

  const containerClass = panelMode
    ? `fixed z-50 ${className}`
    : `fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 ${className}`;
  return (
    <div className={containerClass} style={panelMode ? { left: pos.x, top: pos.y, width: 480 } : undefined}>
      <div className={`bg-white rounded-lg shadow-xl ${panelMode ? 'w-full' : 'max-w-2xl w-full mx-4'} max-h-[80vh] flex flex-col select-none`}
           onMouseDown={(e) => {
             if (!panelMode) return;
             const header = (e.target as HTMLElement).closest('[data-upload-header]');
             if (header) {
               dragging.current = true;
               offset.current = { x: e.clientX - pos.x, y: e.clientY - pos.y };
             }
           }}
           onMouseMove={(e) => {
             if (panelMode && dragging.current) {
               setPos({ x: e.clientX - offset.current.x, y: e.clientY - offset.current.y });
             }
           }}
           onMouseUp={() => { dragging.current = false; }}
           onMouseLeave={() => { dragging.current = false; }}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b cursor-move" data-upload-header>
          <div className="flex items-center gap-2">
            <Upload size={20} />
            <h2 className="text-lg font-semibold">Upload Files</h2>
            <span className="text-sm text-gray-500">
              ({queue.length}/{maxFiles})
            </span>
          </div>
          <div className="flex gap-2 items-center">
            {panelMode && (
              <button onClick={() => setMinimized(true)} className="p-1 hover:bg-gray-100 rounded" title="Minimize">
                _
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-100 rounded"
              disabled={isUploading}
              aria-label="Close uploader"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Removed internal drop zone (now contextual chat/explorer). Provide add button only. */}
        <div className="px-4 pt-4 text-sm text-gray-500">
          <p className="mb-2">Use the contextual drop zones (Explorer folders or Chat prompt) to add files. You can also manually select files.</p>
          <button
            onClick={handleSelectFiles}
            className="inline-flex items-center gap-2 px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            disabled={isUploading || queue.length >= maxFiles}
          >
            <Plus size={14}/> Browse Files
          </button>
          <p className="mt-2 text-xs">Supports: {allowedTypes.join(', ')}</p>
        </div>

        {/* File List */}
        {hasFiles && (
          <div className="flex-1 overflow-y-auto px-4 pb-4">
            <div className="space-y-2">
              {queue.map((item) => (
                <UploadItem
                  key={item.id}
                  item={item}
                  onRemove={() => removeFile(item.id)}
                  disabled={isUploading}
                />
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between p-4 border-t bg-gray-50">
          <div className="flex gap-2">
            <button
              onClick={handleSelectFiles}
              className="flex items-center gap-2 px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
              disabled={isUploading || queue.length >= maxFiles}
            >
              <Plus size={16} />
              Add More
            </button>
            
            {completedUploads.length > 0 && (
              <button
                onClick={clearCompleted}
                className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
                disabled={isUploading}
              >
                Clear Completed
              </button>
            )}
          </div>

          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
              disabled={isUploading}
            >
              Cancel
            </button>
            
            {canUpload && (
              <button
                onClick={handleUploadAll}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                disabled={!canUpload}
              >
                Upload All
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={allowedTypes.join(',')}
        onChange={handleFileSelect}
        className="hidden"
      />
    </div>
  );
}
