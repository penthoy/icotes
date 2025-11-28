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

      // Guard: if user is pasting into the chat composer we let the chat-specific
      // paste handler own the upload to avoid duplicate media uploads.
      try {
        const activeEl = document.activeElement as HTMLElement | null;
        if (activeEl && activeEl.closest('[data-chat-composer]')) {
          return; // chat component will process this paste
        }
      } catch { /* ignore DOM access errors */ }

      const items = Array.from(e.clipboardData.items);
      const files: File[] = [];
      items.forEach(it => {
        if (it.kind === 'file') {
          const f = it.getAsFile();
          if (f) files.push(f);
        }
      });

      if (files.length === 0) return;

      // If exactly one image file and not multi-file bulk case, defer to context-specific
      // handlers (e.g. chat) to prevent duplicate uploads.
      const imageFiles = files.filter(f => f.type.startsWith('image/'));
      if (files.length === 1 && imageFiles.length === 1) {
        return; // single image paste handled elsewhere
      }

      // Bulk / mixed-type paste: use global upload manager.
      if (files.length > 1) {
        setOpen(true);
      }
      uploadHook.addFiles(files);
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
