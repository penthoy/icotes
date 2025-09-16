import React, { useEffect, useRef, useState } from 'react';
import { useMediaUpload } from '../../hooks/useMediaUpload';

interface ChatDropZoneProps {
  selector?: string; // CSS selector for chat input container (fallback)
  uploadApi: ReturnType<typeof useMediaUpload>;
  onFilesStaged?: (files: File[]) => void; // immediate preview staging
}

/** ChatDropZone attaches drag/drop listeners to the chat prompt area only */
export function ChatDropZone({ selector = '[data-chat-input]', uploadApi, onFilesStaged }: ChatDropZoneProps) {
  const [active, setActive] = useState(false);
  const leaveCounter = useRef(0);

  useEffect(() => {
  const el = document.querySelector(selector) as HTMLElement | null;
    if (!el) return;
    el.dataset.dropScope = 'chat';

    const isFileDrag = (e: DragEvent) => !!e.dataTransfer && Array.from(e.dataTransfer.types).includes('Files');

    const activate = () => {
      if (!active) setActive(true);
    };
    const deactivate = () => {
      leaveCounter.current = 0;
      setActive(false);
    };

    const onDragEnter = (e: DragEvent) => {
      if (!isFileDrag(e)) return;
      e.preventDefault();
      e.stopPropagation();
      leaveCounter.current += 1;
      activate();
    };

    const onDragOver = (e: DragEvent) => {
      if (!isFileDrag(e)) return;
      e.preventDefault();
      e.stopPropagation();
  // Fallback: if dragenter missed (some browsers), ensure active
  if (!active) activate();
    };

    const onDragLeave = (e: DragEvent) => {
      if (!isFileDrag(e)) return;
      e.preventDefault();
      e.stopPropagation();
      leaveCounter.current -= 1;
      if (leaveCounter.current <= 0) deactivate();
    };

    const onDrop = (e: DragEvent) => {
      if (!isFileDrag(e)) return;
      e.preventDefault();
      e.stopPropagation();
      const files = Array.from(e.dataTransfer!.files);
      if (files.length) {
        onFilesStaged?.(files);
        uploadApi.addFiles(files, { context: 'chat' });
      }
      deactivate();
    };

  el.addEventListener('dragenter', onDragEnter);
  el.addEventListener('dragover', onDragOver);
  el.addEventListener('dragleave', onDragLeave);
  el.addEventListener('drop', onDrop);
    return () => {
      el.removeEventListener('dragenter', onDragEnter);
      el.removeEventListener('dragover', onDragOver);
      el.removeEventListener('dragleave', onDragLeave);
      el.removeEventListener('drop', onDrop);
    };
  }, [selector, uploadApi, onFilesStaged, active]);

  return active ? (
    <div className="pointer-events-none absolute inset-0 rounded-md border-2 border-dashed border-blue-400/70 bg-blue-500/10 flex items-center justify-center text-blue-600 dark:text-blue-300 text-xs font-medium z-10">
      Drop files to attach
    </div>
  ) : null;
}

export default ChatDropZone;