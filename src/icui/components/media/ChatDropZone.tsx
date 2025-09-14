import React, { useEffect, useRef, useState } from 'react';
import { useMediaUpload } from '../../hooks/useMediaUpload';

interface ChatDropZoneProps {
  selector?: string; // CSS selector for chat input container
  uploadApi: ReturnType<typeof useMediaUpload>;
}

/** ChatDropZone attaches drag/drop listeners to the chat prompt area only */
export function ChatDropZone({ selector = '[data-chat-input]', uploadApi }: ChatDropZoneProps) {
  const [active, setActive] = useState(false);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    const el = document.querySelector(selector) as HTMLElement | null;
    if (!el) return;
    el.dataset.dropScope = 'chat';

    const onDragOver = (e: DragEvent) => {
      if (!e.dataTransfer) return;
      if (Array.from(e.dataTransfer.types).includes('Files')) {
        e.preventDefault();
        e.stopPropagation();
        setActive(true);
        if (timerRef.current) window.clearTimeout(timerRef.current);
        timerRef.current = window.setTimeout(() => setActive(false), 1500);
      }
    };
  const onDrop = (e: DragEvent) => {
      if (!e.dataTransfer) return;
      if (Array.from(e.dataTransfer.types).includes('Files')) {
        e.preventDefault();
        e.stopPropagation();
        const files = Array.from(e.dataTransfer.files);
        uploadApi.addFiles(files, { context: 'chat' });
    console.log('[ChatDropZone] Added files via drop:', files.map(f=>f.name));
      }
      setActive(false);
    };
    el.addEventListener('dragover', onDragOver);
    el.addEventListener('drop', onDrop);
    return () => {
      el.removeEventListener('dragover', onDragOver);
      el.removeEventListener('drop', onDrop);
    };
  }, [selector, uploadApi]);

  return active ? (
    <div className="pointer-events-none absolute inset-0 rounded border-2 border-dashed border-blue-400 bg-blue-200/30 flex items-center justify-center text-blue-700 text-sm font-medium z-10">
      Drop to attach to chat
    </div>
  ) : null;
}

export default ChatDropZone;