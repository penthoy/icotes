import { useEffect } from 'react';

/**
 * useChatPaste
 * Handles image paste events for the chat composer area.
 *
 * Notes:
 * - Only stages image/* files to avoid generic clipboard interference.
 * - Consumers provide stage() and enqueue(files) callbacks.
 */
export function useChatPaste(
  stagePreview: (file: File) => void,
  enqueueUploads: (files: File[]) => void
) {
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      if (!e.clipboardData) return;
      // If a global handler already processed this, skip
      if ((e as any)._icuiGlobalPasteHandled) return;
      const items = Array.from(e.clipboardData.items);
      const files: File[] = [];
      for (const it of items) {
        if (it.kind !== 'file') continue;
        const f = it.getAsFile();
        if (f) files.push(f);
      }
      if (files.length === 0) return;
      const imageFiles = files.filter(f => f.type.startsWith('image/'));
      if (imageFiles.length === 0) return;
      imageFiles.forEach(stagePreview);
      enqueueUploads(imageFiles);
    };
    window.addEventListener('paste', onPaste);
    return () => window.removeEventListener('paste', onPaste);
  }, [stagePreview, enqueueUploads]);
}

export default useChatPaste;
