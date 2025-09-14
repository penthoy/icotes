import React, { useCallback, useEffect, useState } from 'react';
import UploadWidget from './upload/UploadWidget';
import { useMediaUpload } from '../../hooks/useMediaUpload';
import ChatDropZone from './ChatDropZone';
import ExplorerDropProvider from '../explorer/ExplorerDropProvider';

/**
 * GlobalUploadManager
 * Mount once near root. Provides:
 * - Global drag-over detection (any file dragged onto window surfaces upload UI)
 * - Keyboard shortcut (Ctrl+U) to open uploader
 * - Esc to close
 */
export default function GlobalUploadManager() {
  const [open, setOpen] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [dragTimer, setDragTimer] = useState<number | null>(null);
  // Dedicated hidden queue instance (autoStart true)
  const uploadHook = useMediaUpload({ autoStart: true });

  const resetDragState = useCallback(() => {
    setDragActive(false);
    if (dragTimer) window.clearTimeout(dragTimer);
    setDragTimer(null);
  }, [dragTimer]);

  useEffect(() => {
    const handleDragOver = (e: DragEvent) => {
      if (!e.dataTransfer) return;
      if (Array.from(e.dataTransfer.types).includes('Files')) {
        e.preventDefault();
        setDragActive(true);
        if (!open) setOpen(true);
        if (dragTimer) window.clearTimeout(dragTimer);
        setDragTimer(window.setTimeout(() => setDragActive(false), 1500));
      }
    };
    const handleDrop = (e: DragEvent) => {
      if (!e.dataTransfer) return;
      if (Array.from(e.dataTransfer.types).includes('Files')) {
        // Let underlying widget zone capture actual drop; just prevent navigation
        e.preventDefault();
        e.stopPropagation();
      }
      resetDragState();
    };
    const handleKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'u') {
        e.preventDefault();
        setOpen(o => !o);
      } else if (e.key === 'Escape') {
        setOpen(false);
      }
    };
    const handlePaste = (e: ClipboardEvent) => {
      if (!e.clipboardData) return;
      const items = Array.from(e.clipboardData.items);
      const files: File[] = [];
      items.forEach(it => {
        if (it.kind === 'file') {
          const f = it.getAsFile();
            if (f) files.push(f);
        }
      });
      if (files.length) {
        setOpen(true);
        uploadHook.addFiles(files);
      }
    };

    window.addEventListener('dragover', handleDragOver);
    window.addEventListener('drop', handleDrop);
    window.addEventListener('keydown', handleKey);
    window.addEventListener('paste', handlePaste);
    return () => {
      window.removeEventListener('dragover', handleDragOver);
      window.removeEventListener('drop', handleDrop);
      window.removeEventListener('keydown', handleKey);
      window.removeEventListener('paste', handlePaste);
    };
  }, [open, dragTimer, resetDragState]);

  return (
    <>
      <ExplorerDropProvider uploadApi={uploadHook} />
      <div className="relative" data-chat-input>
        <ChatDropZone uploadApi={uploadHook} />
      </div>
      {dragActive && !open && (
        <div className="fixed inset-0 pointer-events-none flex items-center justify-center z-40">
          <div className="bg-blue-600/70 text-white px-6 py-3 rounded shadow-lg text-lg font-medium">
            Drop over Explorer or Chat to upload…
          </div>
        </div>
      )}
      <UploadWidget isOpen={open} onClose={() => setOpen(false)} externalQueue={uploadHook} panelMode initialPosition={{ x: 16, y: (typeof window !== 'undefined' ? window.innerHeight - 360 : 100) }} />
    </>
  );
}
