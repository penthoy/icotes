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
      
      // Debug logging to diagnose drag-drop issues
      if (import.meta.env.DEV) {
        console.log('[useComposerDnd] Drop event:', {
          types: Array.from(e.dataTransfer.types),
          items: e.dataTransfer.items ? Array.from(e.dataTransfer.items).map(i => ({ kind: i.kind, type: i.type })) : [],
          filesLength: e.dataTransfer.files?.length || 0
        });
      }
      
      // Explorer internal drags (file references)
      const raw = e.dataTransfer.getData(ICUI_FILE_LIST_MIME);
      if (import.meta.env.DEV) {
        console.log('[useComposerDnd] ICUI_FILE_LIST_MIME data:', raw ? `Found (${raw.length} chars)` : 'Not found');
      }
      
      if (raw) {
        try {
          const payload = JSON.parse(raw);
          if (!isExplorerPayload(payload)) {
            if (import.meta.env.DEV) {
              console.log('[useComposerDnd] Invalid payload structure');
            }
            return;
          }
          const refs: ExplorerRefItem[] = payload.items
            .filter((item: any) => item.type === 'file')
            .map((item: any) => ({
              id: `explorer-${Date.now()}-${Math.random().toString(36).slice(2)}`,
              path: item.path,
              name: item.name,
              kind: 'file' as const,
            }));
          if (import.meta.env.DEV) {
            console.log('[useComposerDnd] Explorer refs extracted:', refs);
          }
          if (refs.length > 0) opts.onRefs(refs);
          return;
        } catch (err) {
          if (import.meta.env.DEV) {
            console.error('[useComposerDnd] Failed to parse explorer payload:', err);
          }
        }
      }
      // External OS file drops (actual uploads)
      const files = Array.from(e.dataTransfer.files || []);
      if (files.length > 0) {
        if (import.meta.env.DEV) {
          console.log('[useComposerDnd] External files dropped:', files.map(f => f.name));
        }
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
