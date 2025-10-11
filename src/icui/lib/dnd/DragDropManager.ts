/**
 * DragDropManager
 * Lightweight helper around HTML5 drag & drop + CustomEvents.
 *
 * Responsibilities:
 * - Provide helper to serialize & attach explorer file selections.
 * - Dispatch lifecycle DOM events (so other panels can listen without coupling).
 * - Offer minimal registry in case future panels want to expose virtual items.
 */

import {
  DragFileDescriptor,
  ExplorerDragPayload,
  DragStartDetail,
  ICUI_FILE_LIST_MIME,
  ICUI_DND_START_EVENT,
  ICUI_DND_END_EVENT,
  DragItemKind,
} from './types';

export interface DragSourceOptions {
  kind?: DragItemKind;
  source?: string; // e.g. 'explorer'
}

class DragDropManagerImpl {
  /** Serialize explorer selection and write to a DataTransfer */
  attachExplorerSelection(
    dataTransfer: DataTransfer,
    descriptors: DragFileDescriptor[],
    opts: DragSourceOptions = {}
  ): ExplorerDragPayload {
    const kind: DragItemKind = descriptors.length > 1
      ? 'explorer:multi'
      : descriptors[0].type === 'folder'
        ? 'explorer:folder'
        : 'explorer:file';

    const payload: ExplorerDragPayload = {
      kind: opts.kind ?? kind,
      paths: descriptors.map(d => d.path),
      items: descriptors,
      multi: descriptors.length > 1,
      ts: Date.now(),
    };

    try {
      // Set custom MIME type first
      dataTransfer.setData(ICUI_FILE_LIST_MIME, JSON.stringify(payload));
      // Provide human-readable fallback for environments inspecting dragged text
      dataTransfer.setData('text/plain', payload.paths.join('\n'));
      // IMPORTANT: Set effectAllowed to allow both copy and move operations
      dataTransfer.effectAllowed = 'copyMove';
      
      if (import.meta.env.DEV) {
        console.log('[DragDropManager] setData complete:', {
          customMime: ICUI_FILE_LIST_MIME,
          payloadSize: JSON.stringify(payload).length,
          effectAllowed: dataTransfer.effectAllowed,
          types: Array.from(dataTransfer.types ?? [])
        });
      }
    } catch (e) {
      // Non-fatal; log to console only (avoid polluting user UI)
      console.warn('[DragDropManager] Failed to set dataTransfer payload', e);
      if (import.meta.env.DEV) {
        console.error('[DragDropManager] setData error details:', e);
      }
    }
    return payload;
  }

  /** Dispatch global start event */
  dispatchStart(detail: DragStartDetail): void {
    window.dispatchEvent(new CustomEvent(ICUI_DND_START_EVENT, { detail }));
  }

  /** Dispatch global end event */
  dispatchEnd(detail: { ts: number; cancelled?: boolean }): void {
    window.dispatchEvent(new CustomEvent(ICUI_DND_END_EVENT, { detail }));
  }
}

export const DragDropManager = new DragDropManagerImpl();
