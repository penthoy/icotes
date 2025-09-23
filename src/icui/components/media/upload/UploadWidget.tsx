/**
 * UploadWidget - Phase 3 UI Component
 * 
 * Floating upload widget that provides drag-and-drop interface,
 * file selection, and upload progress management.
 */
import React, { useCallback, useState, useRef } from 'react';
import { useMediaUpload, UseMediaUploadReturn, UploadItem as UploadItemType } from '../../../hooks/useMediaUpload';
import UploadItem from './UploadItem';
import { X, Upload } from 'lucide-react';

// Constants
const DEFAULT_WIDGET_HEIGHT = 420;

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
  initialPosition = { x: 16, y: typeof window !== 'undefined' ? (window.innerHeight - DEFAULT_WIDGET_HEIGHT) : 100 }
}: UploadWidgetProps) {
  const internal = useMediaUpload();
  const api = externalQueue || internal;
  const { queue, isUploading, addFiles, removeFile, clearCompleted, uploadAll } = api;
  const [minimized, setMinimized] = useState(false);
  const [pos, setPos] = useState(initialPosition);
  const dragging = useRef(false);
  const offset = useRef({ x: 0, y: 0 });
  
  const [isDragActive, setIsDragActive] = useState(false);

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
  <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-xl ${panelMode ? 'w-full' : 'max-w-2xl w-full mx-4'} max-h-[80vh] flex flex-col select-none border border-gray-200 dark:border-gray-700`}
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
  <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 cursor-move" data-upload-header>
          <div className="flex items-center gap-2">
            <Upload size={20} className="text-gray-700 dark:text-gray-200" />
            <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Upload Files</h2>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              ({queue.length}/{maxFiles})
            </span>
          </div>
          <div className="flex gap-2 items-center">
            {panelMode && (
              <button onClick={() => setMinimized(true)} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-gray-600 dark:text-gray-300" title="Minimize">
                _
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-gray-600 dark:text-gray-300"
              disabled={isUploading}
              aria-label="Close uploader"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Guidance only; files are added via Explorer drop or paste. */}
        <div className="px-4 pt-4 text-sm text-gray-500 dark:text-gray-400">
          <p className="mb-2">This panel appears when you add multiple files. Drag-and-drop into the Explorer to stage uploads. Single-file drops upload silently.</p>
          <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">Allowed: {allowedTypes.join(', ')}</p>
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
  <div className="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
          <div className="flex gap-2">
            {/* No manual add; files come from context actions */}
            {completedUploads.length > 0 && (
              <button
                onClick={clearCompleted}
                className="px-3 py-1 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-gray-100"
                disabled={isUploading}
              >
                Clear Completed
              </button>
            )}
          </div>

          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-gray-100"
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

      {/* No file input (selection via OS dialog is removed per new spec) */}
    </div>
  );
}
