import { useEffect } from 'react';
import { ICUI_FILE_LIST_MIME, isExplorerPayload } from '../../../lib/dnd';

export interface ExplorerRefItem {
  id: string;
  path: string;
  name: string;
  kind: 'file';
}

/**
 * useComposerDnd
 * Encapsulates drag-over/leave/drop events for the chat composer.
 * Calls back with either explorer references or OS files to upload.
 */
export function useComposerDnd(
  root: HTMLElement | null,
  opts: {
    setActive: (active: boolean) => void;
    onRefs: (refs: ExplorerRefItem[]) => void;
    onFiles: (files: File[]) => void;
  }
) {
  useEffect(() => {
    const el = root;
    if (!el) return;
    const handleDragOver = (e: DragEvent) => {
      if (!e.dataTransfer) return;
      const types = Array.from(e.dataTransfer.types);
      const hasExplorerPayload = types.includes(ICUI_FILE_LIST_MIME);
      const hasFiles = types.includes('Files');
      if (!hasExplorerPayload && !hasFiles) return;
      e.preventDefault();
      opts.setActive(true);
    };
    const handleDragLeave = (e: DragEvent) => {
      if (!(e.relatedTarget instanceof HTMLElement) || !el.contains(e.relatedTarget)) {
        opts.setActive(false);
      }
    };
    const handleDrop = (e: DragEvent) => {
      if (!e.dataTransfer) return;
      e.preventDefault();
      opts.setActive(false);
      // Explorer internal drags (file references)
      const raw = e.dataTransfer.getData(ICUI_FILE_LIST_MIME);
      if (raw) {
        try {
          const payload = JSON.parse(raw);
          if (!isExplorerPayload(payload)) return;
          const refs: ExplorerRefItem[] = payload.items
            .filter((item: any) => item.type === 'file')
            .map((item: any) => ({
              id: `explorer-${Date.now()}-${Math.random().toString(36).slice(2)}`,
              path: item.path,
              name: item.name,
              kind: 'file' as const,
            }));
          if (refs.length > 0) opts.onRefs(refs);
          return;
        } catch {
          // swallow
        }
      }
      // External OS file drops (actual uploads)
      const files = Array.from(e.dataTransfer.files || []);
      if (files.length > 0) {
        opts.onFiles(files);
      }
    };

    el.addEventListener('dragover', handleDragOver);
    el.addEventListener('dragleave', handleDragLeave);
    el.addEventListener('drop', handleDrop);
    return () => {
      el.removeEventListener('dragover', handleDragOver);
      el.removeEventListener('dragleave', handleDragLeave);
      el.removeEventListener('drop', handleDrop);
    };
  }, [root, opts]);
}

export default useComposerDnd;
