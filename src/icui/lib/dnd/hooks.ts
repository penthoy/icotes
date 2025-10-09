import { useCallback } from 'react';
import { DragDropManager } from './DragDropManager';
import { DragFileDescriptor, DragStartDetail } from './types';
// NOTE: frontend-logger lives higher in the tree; use relative path from icui/lib
import { log } from '../../../services/frontend-logger';

/**
 * useExplorerFileDrag
 * Returns helper to spread onto explorer row elements to enable dragging.
 * Keeps logic isolated so ICUIExplorer stays lean & future panels can reuse.
 */
export function useExplorerFileDrag(params: {
  getSelection: () => DragFileDescriptor[];     // returns current multi-selection
  isItemSelected: (id: string) => boolean;      // selection predicate for click origin
  toDescriptor: (node: any) => DragFileDescriptor; // convert raw explorer node
}) {
  const { getSelection, isItemSelected, toDescriptor } = params;

  const getDragProps = useCallback((node: any) => {
    return {
      draggable: true,
      onDragStart: (e: React.DragEvent) => {
        const dt = e.dataTransfer;
        const baseDescriptor = toDescriptor(node);
        // If the origin node is in selection, drag all selected items; else single
        const selection = isItemSelected(node.id) ? getSelection() : [baseDescriptor];
        const traceId = `dnd-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`;
        (dt as any)._icuiTraceId = traceId; // attach for later debugging
        
        if (import.meta.env.DEV) {
          console.log('[useExplorerFileDrag] Drag start:', {
            traceId,
            origin: baseDescriptor.path,
            count: selection.length,
            selection: selection.map(s => s.path),
          });
        }
        
        try {
          log.info('ExplorerDnD', '[DND][start] selection prepared', {
            traceId,
            origin: baseDescriptor.path,
            count: selection.length,
            selection: selection.map(s => s.path),
          });
        } catch {}
        const payload = DragDropManager.attachExplorerSelection(dt, selection);
        
        if (import.meta.env.DEV) {
          console.log('[useExplorerFileDrag] Payload attached:', payload);
          console.log('[useExplorerFileDrag] DataTransfer types after attach:', Array.from(dt.types));
        }
        
        const detail: DragStartDetail = { ...payload, source: 'explorer' };
        DragDropManager.dispatchStart(detail);
      },
      onDragEnd: (_e: React.DragEvent) => {
        // Future: pass cancellation flag when we add ESC abort detection
        DragDropManager.dispatchEnd({ ts: Date.now() });
      }
    } as const;
  }, [getSelection, isItemSelected, toDescriptor]);

  return { getDragProps };
}
