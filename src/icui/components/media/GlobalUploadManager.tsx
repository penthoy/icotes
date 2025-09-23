import React, { useCallback, useEffect, useState } from 'react';
import UploadWidget from './upload/UploadWidget';
import { useMediaUpload } from '../../hooks/useMediaUpload';
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
  // Dedicated hidden queue instance (autoStart true)
  const uploadHook = useMediaUpload({ autoStart: true });

  useEffect(() => {
    // Open widget only upon explicit request (multi-file drops from Explorer) or keyboard shortcut
    const onOpenReq = () => setOpen(true);
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
      // Only auto-open for multiple files to match new UX requirement
      if (files.length > 1) {
        setOpen(true);
        uploadHook.addFiles(files);
      } else if (files.length === 1) {
        uploadHook.addFiles(files); // single paste goes silently to queue
      }
    };
    window.addEventListener('icotes:open-upload-widget' as any, onOpenReq);
    window.addEventListener('keydown', handleKey);
    window.addEventListener('paste', handlePaste);
    return () => {
      window.removeEventListener('icotes:open-upload-widget' as any, onOpenReq);
      window.removeEventListener('keydown', handleKey);
      window.removeEventListener('paste', handlePaste);
    };
  }, [uploadHook]);

  return (
    <>
      <ExplorerDropProvider uploadApi={uploadHook} />
      <UploadWidget isOpen={open} onClose={() => setOpen(false)} externalQueue={uploadHook} panelMode initialPosition={{ x: 16, y: (typeof window !== 'undefined' ? window.innerHeight - 360 : 100) }} />
    </>
  );
}
